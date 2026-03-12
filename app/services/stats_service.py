# app/services/stats_service.py

"""
stats_service.py

Computes user-facing progress metrics from ReviewLog and ReviewState data.

Current responsibilities:
- Count ratings selected today
- Count cards in New / Learning / Review buckets
- Count total reviewed today
- Compute current / max streak for today
- Count cards due right now

Important queue note:
For the New / Learning / Review display on the review page, we count cards
due by the end of the current simulated day. This is closer to how Anki-style
queue counts are usually presented than counting only cards due at this exact second.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional

from flask import session as flask_session
from sqlmodel import select, col

from app.db import get_session
from app.models.review_log import ReviewLog
from app.models.review_state import ReviewState
from app.services.queue_service import get_queue_bucket


def get_simulated_now() -> datetime:
    """Return simulated time if active, otherwise real current UTC time."""
    sim = flask_session.get("simulated_time")
    if sim:
        dt = datetime.fromisoformat(sim)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    return datetime.now(timezone.utc)


def _as_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Normalize datetimes to timezone-aware UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


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
            due = _as_utc(rs.due_date)
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

        for review in reviews:
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
            "total_reviewed": len(reviews),
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