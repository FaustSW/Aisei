"""
stats_service.py

Computes user-facing progress metrics from ReviewLog and ReviewState data.

Current responsibilities:
- Count first ratings selected today per card (not every re-review)
- Count cards in New / Learning / Review buckets due today
- Count unique cards reviewed today
- Compute current / max streak for today
- Count cards due right now

Important queue note:
For the New / Learning / Review display on the review page, we count cards
due by the end of the current simulated day. This is closer to how Anki-style
queue counts are usually presented than counting only cards due at this exact second.

It SHOULD NOT:
- Handle HTTP requests, sessions, or template rendering.
- Perform scheduling updates or review workflow logic (review_service handles that).
- Call external APIs or trigger content generation.

Architectural Position:

Blueprint (review / stats endpoints) → stats_service → models (ReviewState, ReviewLog)
                                                      → queue_service (bucket classification, time helpers)
"""

from __future__ import annotations

from datetime import timedelta

from sqlmodel import select, col

from app.db import get_session
from app.models.review_log import ReviewLog
from app.models.review_state import ReviewState
from app.services.queue_service import (
    as_utc,
    get_queue_bucket,
    get_simulated_now,
)


def get_session_stats(user_id: int) -> dict:
    """
    Compute review stats for the current simulated day (UTC).

    Returns:
        {
            "total_reviewed": int,
            "counts": {
                "again": int,
                "hard": int,
                "good": int,
                "easy": int,
            },
            "current_streak": int,
            "max_streak": int,
            "cards_due": int,
            "new_cards": int,
            "learning_cards": int,
            "review_cards": int,
        }
    """
    db_session = get_session()
    try:
        now = get_simulated_now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        all_states = db_session.exec(
            select(ReviewState).where(ReviewState.user_id == user_id)
        ).all()

        due_today_states = []
        cards_due = 0

        for rs in all_states:
            due = as_utc(rs.due_date)
            if due is None:
                continue

            if due <= today_end:
                due_today_states.append(rs)

            if due <= now:
                cards_due += 1

        new_cards = [rs for rs in due_today_states if get_queue_bucket(rs) == "new"]
        learning_cards = [rs for rs in due_today_states if get_queue_bucket(rs) == "learning"]
        review_cards = [rs for rs in due_today_states if get_queue_bucket(rs) == "review"]

        reviews = db_session.exec(
            select(ReviewLog)
            .where(ReviewLog.user_id == user_id)
            .where(col(ReviewLog.reviewed_at) >= today_start)
            .where(col(ReviewLog.reviewed_at) < today_end)
            .order_by(col(ReviewLog.reviewed_at).asc())
        ).all()

        counts = {"again": 0, "hard": 0, "good": 0, "easy": 0}
        rating_map = {1: "again", 2: "hard", 3: "good", 4: "easy"}

        current_streak = 0
        max_streak = 0
        seen_review_state_ids = set()

        # Only count each card's first review of the day toward the progress bar
        # and streak. Re-reviews of the same card (e.g., learning steps) are
        # intentionally skipped so the numbers match how many distinct cards
        # the user has worked through today.
        for review in reviews:
            is_first_review_today = review.review_state_id not in seen_review_state_ids
            if is_first_review_today:
                seen_review_state_ids.add(review.review_state_id)

                name = rating_map.get(review.rating)
                if name:
                    counts[name] += 1

                if review.rating in (3, 4):
                    current_streak += 1
                    if current_streak > max_streak:
                        max_streak = current_streak
                else:
                    current_streak = 0

        return {
            "total_reviewed": len(seen_review_state_ids),
            "counts": counts,
            "current_streak": current_streak,
            "max_streak": max_streak,
            "cards_due": cards_due,
            "new_cards": len(new_cards),
            "learning_cards": len(learning_cards),
            "review_cards": len(review_cards),
        }
    finally:
        db_session.close()
