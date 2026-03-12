# app/services/queue_service.py

"""
queue_service.py

Owns app-side queue classification and next-card selection.

Responsibilities:
- Classify ReviewState objects into app-visible queue buckets.
- Select the next ReviewState for review using the hybrid queue policy.
- Build the deterministic static daily queue for new + review cards.

Current queue policy:
1. Learning / relearning cards due right now
2. Static daily queue for new + review cards due today or earlier
3. Next learning / relearning card due later today
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional

from flask import session as flask_session
from sqlmodel import select

from app.models.review_state import ReviewState
from app.models.vocab import Vocab


def get_simulated_now() -> datetime:
    """
    Return the active simulated time if one is stored in the Flask session.
    Otherwise return the real current UTC time.
    """
    sim = flask_session.get("simulated_time")
    if sim:
        dt = datetime.fromisoformat(sim)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    return datetime.now(timezone.utc)


def as_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Normalize datetimes to timezone-aware UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def get_queue_bucket(review_state: ReviewState) -> str:
    """
    Derive the app-side queue bucket for a ReviewState.

    Buckets:
        - "new": never reviewed yet
        - "learning": seen before, but not yet in long-interval review
        - "review": graduated into long-interval review
    """
    if review_state.repetitions == 0:
        return "new"

    if review_state.interval and review_state.interval > 0:
        return "review"

    return "learning"


def is_due_now(review_state: ReviewState, now: datetime) -> bool:
    due = as_utc(review_state.due_date)
    return due is not None and due <= now


def is_due_later_today(
    review_state: ReviewState,
    now: datetime,
    today_end: datetime,
) -> bool:
    due = as_utc(review_state.due_date)
    return due is not None and now < due <= today_end


def is_due_on_or_before_today(review_state: ReviewState, today_date) -> bool:
    """
    Day-based due check for static new/review queue.
    Ignores time-of-day entirely.
    """
    due = as_utc(review_state.due_date)
    return due is not None and due.date() <= today_date


def get_next_review_state(db_session, user_id: int) -> Optional[ReviewState]:
    """
    Hybrid queue selection:

    1. Learning/relearning due now
    2. Static daily queue (new + review due today or earlier, day-based only)
    3. Next learning/relearning due later today
    """
    now = get_simulated_now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    today_date = now.date()

    all_states = db_session.exec(
        select(ReviewState).where(ReviewState.user_id == user_id)
    ).all()

    learning_cards = [rs for rs in all_states if get_queue_bucket(rs) == "learning"]
    static_cards = [rs for rs in all_states if get_queue_bucket(rs) in ("new", "review")]

    learning_due_now = [rs for rs in learning_cards if is_due_now(rs, now)]
    if learning_due_now:
        learning_due_now.sort(key=lambda rs: (as_utc(rs.due_date) or now, rs.id))
        return learning_due_now[0]

    static_due_today = [
        rs for rs in static_cards
        if is_due_on_or_before_today(rs, today_date)
    ]
    if static_due_today:
        static_queue = build_static_daily_queue(
            db_session=db_session,
            review_states=static_due_today,
            today_date=today_date,
        )
        if static_queue:
            return static_queue[0]

    learning_due_later_today = [
        rs for rs in learning_cards
        if is_due_later_today(rs, now, today_end)
    ]
    if learning_due_later_today:
        learning_due_later_today.sort(
            key=lambda rs: (as_utc(rs.due_date) or today_end, rs.id)
        )
        return learning_due_later_today[0]

    return None


def build_static_daily_queue(
    db_session,
    review_states: list[ReviewState],
    today_date,
) -> list[ReviewState]:
    """
    Build a deterministic static daily queue for new + review cards.

    Current implementation:
    - Reviews sorted by due day, then id
    - New cards sorted by vocab.intro_index, then id
    - Interleave review and new cards 1:1
    - Start with whichever side has the earlier first candidate
      (reviews win ties)

    Important:
    This queue is day-based. Time-of-day is ignored for static queue cards.
    """
    review_cards = [rs for rs in review_states if get_queue_bucket(rs) == "review"]
    new_cards = [rs for rs in review_states if get_queue_bucket(rs) == "new"]

    review_cards.sort(
        key=lambda rs: (
            (as_utc(rs.due_date).date() if as_utc(rs.due_date) else datetime.max.date()),
            rs.id,
        )
    )

    vocab_ids = [rs.vocab_id for rs in new_cards]
    vocab_map = {
        vocab.id: vocab
        for vocab in db_session.exec(
            select(Vocab).where(Vocab.id.in_(vocab_ids))
        ).all()
    } if vocab_ids else {}

    def new_sort_key(rs: ReviewState):
        vocab = vocab_map.get(rs.vocab_id)
        intro_index = vocab.intro_index if vocab and vocab.intro_index is not None else 10**9
        return (intro_index, rs.id)

    new_cards.sort(key=new_sort_key)

    if not review_cards:
        return new_cards
    if not new_cards:
        return review_cards

    first_review_day = (
        as_utc(review_cards[0].due_date).date()
        if as_utc(review_cards[0].due_date)
        else datetime.max.date()
    )
    first_new_day = today_date

    start_with_review = first_review_day <= first_new_day

    queue: list[ReviewState] = []
    i = 0
    j = 0
    turn_review = start_with_review

    while i < len(review_cards) or j < len(new_cards):
        if turn_review:
            if i < len(review_cards):
                queue.append(review_cards[i])
                i += 1
            elif j < len(new_cards):
                queue.append(new_cards[j])
                j += 1
        else:
            if j < len(new_cards):
                queue.append(new_cards[j])
                j += 1
            elif i < len(review_cards):
                queue.append(review_cards[i])
                i += 1

        turn_review = not turn_review

    return queue