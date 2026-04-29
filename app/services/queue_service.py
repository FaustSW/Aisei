"""
queue_service.py

Owns app-side queue classification and next-card selection.

Responsibilities:
- Classify ReviewState objects into app-visible queue buckets.
- Select the next ReviewState for review using the hybrid queue policy.
- Build the deterministic static daily queue for new + review cards.
- Provide shared time helpers for simulated-time-aware review logic.
- Evenly distribute capped new cards among review cards when possible.
- Track how many new cards were already introduced today.
- Persist a per-session static queue snapshot for the active day.

Current queue policy:
1. Learning / relearning cards due right now
2. Static daily queue (new + review due today or earlier)
3. Next learning / relearning card due later today
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional

from flask import session as flask_session
from sqlmodel import select, col

from app.models.review_log import ReviewLog
from app.models.review_state import ReviewState
from app.models.vocab import Vocab
from app.services.settings_service import get_daily_new_limit


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


def get_today_window(now: datetime) -> tuple[datetime, datetime]:
    """Return [today_start, tomorrow_start) in UTC for the provided datetime."""
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_start = today_start + timedelta(days=1)
    return today_start, tomorrow_start


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
        - "learning": learning or relearning steps
        - "review": graduated into long-interval review
    """
    if review_state.repetitions == 0:
        return "new"

    if review_state.scheduler_state == 2:
        return "review"

    return "learning"


def is_due_now(review_state: ReviewState, now: datetime) -> bool:
    """True if this card's due_date is at or before the current time."""
    due = as_utc(review_state.due_date)
    return due is not None and due <= now


def is_due_later_today(
    review_state: ReviewState,
    now: datetime,
    today_end: datetime,
) -> bool:
    """True if this card is due after now but before the end of today."""
    due = as_utc(review_state.due_date)
    return due is not None and now < due <= today_end


def is_due_on_or_before_today(review_state: ReviewState, today_date) -> bool:
    """
    Day-based due check for static new/review queue.
    Ignores time-of-day entirely.
    """
    due = as_utc(review_state.due_date)
    return due is not None and due.date() <= today_date


def sort_new_cards_by_curriculum(db_session, review_states: list[ReviewState]) -> list[ReviewState]:
    """
    Return new-card ReviewStates in introduction order.

    Manual cards come first, ordered by Vocab.created_at. Seed cards then follow
    the fixed curriculum order from Vocab.intro_index.
    """
    vocab_ids = [rs.vocab_id for rs in review_states]
    vocab_map = {
        vocab.id: vocab
        for vocab in db_session.exec(
            select(Vocab).where(Vocab.id.in_(vocab_ids))
        ).all()
    } if vocab_ids else {}

    def new_sort_key(rs: ReviewState):
        vocab = vocab_map.get(rs.vocab_id)
        is_manual = bool(vocab and vocab.source == "manual")
        created_at = as_utc(vocab.created_at) if vocab else None
        intro_index = vocab.intro_index if vocab and vocab.intro_index is not None else 10**9

        if is_manual:
            return (0, created_at or datetime.max.replace(tzinfo=timezone.utc), rs.id)

        return (1, intro_index, rs.id)

    return sorted(review_states, key=new_sort_key)


def get_today_review_counts_by_state(db_session, user_id: int, today_start: datetime, today_end: datetime) -> dict[int, int]:
    """
    Return a mapping of review_state_id -> number of review log entries today.
    """
    reviews = db_session.exec(
        select(ReviewLog)
        .where(ReviewLog.user_id == user_id)
        .where(col(ReviewLog.reviewed_at) >= today_start)
        .where(col(ReviewLog.reviewed_at) < today_end)
    ).all()

    counts: dict[int, int] = {}
    for review in reviews:
        counts[review.review_state_id] = counts.get(review.review_state_id, 0) + 1
    return counts


def count_introduced_new_cards_today(
    all_states: list[ReviewState],
    today_review_counts: dict[int, int],
) -> int:
    """
    Count cards that were introduced for the first time today.

    A card qualifies if:
    - it has at least one review log entry today
    - its total repetitions equals the number of review logs it has today

    That means all of its reviews ever happened today, so it must have been
    introduced today.
    """
    introduced_count = 0

    for rs in all_states:
        reviews_today = today_review_counts.get(rs.id, 0)
        if reviews_today > 0 and rs.repetitions == reviews_today:
            introduced_count += 1

    return introduced_count


def cap_new_cards_for_today(
    db_session,
    new_cards: list[ReviewState],
    remaining_new_slots: int,
) -> list[ReviewState]:
    """
    Sort due new cards in curriculum order and cap them to remaining slots.
    """
    if remaining_new_slots <= 0:
        return []

    sorted_new_cards = sort_new_cards_by_curriculum(db_session, new_cards)
    return sorted_new_cards[:remaining_new_slots]


def distribute_new_cards_among_reviews(
    review_cards: list[ReviewState],
    new_cards: list[ReviewState],
) -> list[ReviewState]:
    """
    Evenly distribute new cards among review cards using review gaps.

    The ideal layout is:
        gap0, new0, gap1, new1, ..., newN-1, gapN

    When there are enough reviews, this naturally pads the front and back with
    reviews. If there are too few reviews, some gaps become empty, which is the
    most even fallback possible.
    """
    if not review_cards:
        return new_cards
    if not new_cards:
        return review_cards

    gap_count = len(new_cards) + 1
    base_reviews_per_gap = len(review_cards) // gap_count
    extra_reviews = len(review_cards) % gap_count

    gaps: list[list[ReviewState]] = []
    start = 0

    for gap_index in range(gap_count):
        gap_size = base_reviews_per_gap + (1 if gap_index < extra_reviews else 0)
        gaps.append(review_cards[start:start + gap_size])
        start += gap_size

    queue: list[ReviewState] = []

    for gap_index, gap in enumerate(gaps):
        queue.extend(gap)
        if gap_index < len(new_cards):
            queue.append(new_cards[gap_index])

    return queue


def _static_queue_session_key(user_id: int) -> str:
    """Return the Flask-session key used for this user's static daily queue."""
    return f"static_daily_queue_user_{user_id}"


def invalidate_static_daily_queue(user_id: int) -> None:
    """Delete the cached static daily queue for this user from Flask session."""
    flask_session.pop(_static_queue_session_key(user_id), None)


def _load_static_daily_queue_snapshot(user_id: int) -> dict | None:
    """Load the cached static daily queue snapshot for this user."""
    return flask_session.get(_static_queue_session_key(user_id))


def _save_static_daily_queue_snapshot(
    user_id: int,
    today_date,
    daily_new_limit: int,
    ordered_ids: list[int],
) -> None:
    """Persist today's ordered static queue ids in Flask session."""
    flask_session[_static_queue_session_key(user_id)] = {
        "user_id": user_id,
        "queue_date": today_date.isoformat(),
        "daily_new_limit": daily_new_limit,
        "ordered_ids": ordered_ids,
    }
    flask_session.modified = True


def _is_static_queue_snapshot_valid(
    snapshot: dict | None,
    user_id: int,
    today_date,
    daily_new_limit: int,
) -> bool:
    """Return True if the cached snapshot matches the active user/day/limit."""
    return (
        isinstance(snapshot, dict)
        and snapshot.get("user_id") == user_id
        and snapshot.get("queue_date") == today_date.isoformat()
        and snapshot.get("daily_new_limit") == daily_new_limit
        and isinstance(snapshot.get("ordered_ids"), list)
    )


def _is_static_queue_eligible(review_state: ReviewState, today_date) -> bool:
    """
    Return True if a ReviewState still belongs in today's static queue.

    Only cards currently in the new/review buckets and due on or before today
    remain eligible for the stored static order.
    """
    bucket = get_queue_bucket(review_state)
    return bucket in ("new", "review") and is_due_on_or_before_today(review_state, today_date)


def get_next_review_state(db_session, user_id: int) -> Optional[ReviewState]:
    """
    Hybrid queue selection:

    1. Learning/relearning due now
    2. Static daily queue (new + review due today or earlier, day-based only)
    3. Next learning/relearning due later today
    """
    now = get_simulated_now()
    today_start, tomorrow_start = get_today_window(now)
    today_date = now.date()
    daily_new_limit = get_daily_new_limit(user_id, db_session=db_session)

    all_states = db_session.exec(
        select(ReviewState).where(ReviewState.user_id == user_id)
    ).all()

    learning_cards = [rs for rs in all_states if get_queue_bucket(rs) == "learning"]
    static_cards = [rs for rs in all_states if get_queue_bucket(rs) in ("new", "review")]

    learning_due_now = [rs for rs in learning_cards if is_due_now(rs, now)]
    if learning_due_now:
        learning_due_now.sort(key=lambda rs: (as_utc(rs.due_date) or now, rs.id))
        return learning_due_now[0]

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

    static_due_today = [
        rs for rs in static_cards
        if is_due_on_or_before_today(rs, today_date)
    ]

    if static_due_today:
        snapshot = _load_static_daily_queue_snapshot(user_id)

        if not _is_static_queue_snapshot_valid(
            snapshot=snapshot,
            user_id=user_id,
            today_date=today_date,
            daily_new_limit=daily_new_limit,
        ):
            static_queue = build_static_daily_queue(
                db_session=db_session,
                review_states=static_due_today,
                remaining_new_slots=remaining_new_slots,
            )
            ordered_ids = [rs.id for rs in static_queue if rs.id is not None]
            _save_static_daily_queue_snapshot(
                user_id=user_id,
                today_date=today_date,
                daily_new_limit=daily_new_limit,
                ordered_ids=ordered_ids,
            )
            snapshot = _load_static_daily_queue_snapshot(user_id)

        ordered_ids = snapshot.get("ordered_ids", []) if snapshot else []
        state_by_id = {
            rs.id: rs
            for rs in static_due_today
            if rs.id is not None
        }

        for review_state_id in ordered_ids:
            rs = state_by_id.get(review_state_id)
            if rs is not None and _is_static_queue_eligible(rs, today_date):
                return rs

    learning_due_later_today = [
        rs for rs in learning_cards
        if is_due_later_today(rs, now, tomorrow_start)
    ]
    if learning_due_later_today:
        learning_due_later_today.sort(
            key=lambda rs: (as_utc(rs.due_date) or tomorrow_start, rs.id)
        )
        return learning_due_later_today[0]

    return None


def build_static_daily_queue(
    db_session,
    review_states: list[ReviewState],
    remaining_new_slots: int,
) -> list[ReviewState]:
    """
    Build a deterministic static daily queue for new + review cards.

    Policy:
    - Reviews sorted by due day, then id
    - New cards sorted by vocab.intro_index, then id
    - New cards capped by remaining new slots for today
    - Capped new cards distributed as evenly as possible among reviews
    - If possible, the front and back of the queue are padded with reviews
    """
    review_cards = [rs for rs in review_states if get_queue_bucket(rs) == "review"]
    new_cards = [rs for rs in review_states if get_queue_bucket(rs) == "new"]

    review_cards.sort(
        key=lambda rs: (
            (as_utc(rs.due_date).date() if as_utc(rs.due_date) else datetime.max.date()),
            rs.id,
        )
    )

    new_cards = cap_new_cards_for_today(
        db_session=db_session,
        new_cards=new_cards,
        remaining_new_slots=remaining_new_slots,
    )

    if not review_cards:
        return new_cards
    if not new_cards:
        return review_cards

    return distribute_new_cards_among_reviews(review_cards, new_cards)