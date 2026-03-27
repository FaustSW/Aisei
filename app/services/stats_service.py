"""
stats_service.py

Computes user-facing progress metrics from ReviewLog and ReviewState data.

Current responsibilities:
- Count first ratings selected today per card (not every re-review)
- Count cards in New / Learning / Review buckets due today
- Apply the user's daily new-card cap to the remaining available New count
- Count unique cards reviewed today
- Compute current / max streak for today
- Count cards due right now
"""

from __future__ import annotations

from sqlmodel import select, col

from app.db import get_session
from app.models.review_log import ReviewLog
from app.models.review_state import ReviewState
from app.services.queue_service import (
    as_utc,
    cap_new_cards_for_today,
    count_introduced_new_cards_today,
    get_queue_bucket,
    get_simulated_now,
    get_today_review_counts_by_state,
    get_today_window,
)
from app.services.settings_service import get_daily_new_limit


def get_session_stats(user_id: int) -> dict:
    """
    Compute review stats for the current simulated day (UTC).

    Returns:
        A dict containing:
            - total_reviewed: number of distinct cards first reviewed today
            - counts: first-rating counts for again / hard / good / easy
            - current_streak: current streak of first-review good/easy ratings
            - max_streak: highest first-review good/easy streak reached today
            - cards_due: number of cards due right now
            - new_cards: remaining new cards available today after applying the daily cap
            - learning_cards: learning cards due today
            - review_cards: review cards due today
            - daily_new_limit: user's configured daily new-card limit
    """
    db_session = get_session()
    try:
        now = get_simulated_now()
        today_start, tomorrow_start = get_today_window(now)
        daily_new_limit = get_daily_new_limit(user_id, db_session=db_session)

        all_states = db_session.exec(
            select(ReviewState).where(ReviewState.user_id == user_id)
        ).all()

        due_today_states = []
        cards_due = 0

        for rs in all_states:
            due = as_utc(rs.due_date)
            if due is None:
                continue

            if due < tomorrow_start:
                due_today_states.append(rs)

            if due <= now:
                cards_due += 1

        today_review_counts = get_today_review_counts_by_state(
            db_session=db_session,
            user_id=user_id,
            today_start=today_start,
            today_end=tomorrow_start,
        )
        introduced_today_count = count_introduced_new_cards_today(
            all_states=all_states,
            today_review_counts=today_review_counts,
        )
        remaining_new_slots = max(0, daily_new_limit - introduced_today_count)

        new_cards = [rs for rs in due_today_states if get_queue_bucket(rs) == "new"]
        learning_cards = [rs for rs in due_today_states if get_queue_bucket(rs) == "learning"]
        review_cards = [rs for rs in due_today_states if get_queue_bucket(rs) == "review"]

        available_new_cards = cap_new_cards_for_today(
            db_session=db_session,
            new_cards=new_cards,
            remaining_new_slots=remaining_new_slots,
        )

        reviews = db_session.exec(
            select(ReviewLog)
            .where(ReviewLog.user_id == user_id)
            .where(col(ReviewLog.reviewed_at) >= today_start)
            .where(col(ReviewLog.reviewed_at) < tomorrow_start)
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
            "new_cards": len(available_new_cards),
            "learning_cards": len(learning_cards),
            "review_cards": len(review_cards),
            "daily_new_limit": daily_new_limit,
        }
    finally:
        db_session.close()
