"""
review_service.py

Owns the end-to-end review workflow for a user.

Primary responsibilities:
    - Select the next card for the user to review.
    - Build a display-ready payload for the template / frontend.
    - Process submitted ratings (Again / Hard / Good / Easy).
    - Update ReviewState scheduling fields via scheduler_adapter.
    - Update app-owned counters on ReviewState.
    - Log review events to ReviewLog.

Queue policy:
    - Learning / relearning cards are handled as a dynamic timed queue.
    - New + review cards are handled as a deterministic static daily queue.
    - Learning uses full due timestamp.
    - New + review use due day only.
    - If any learning card is due now, it takes precedence.
    - Otherwise, serve the next card from the static daily queue.
    - If the static daily queue is empty, fall back to the next learning
      card due later today.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional

from flask import session as flask_session
from sqlmodel import select

from app.db import get_session
from app.models.generated_card import GeneratedCard
from app.models.review_log import ReviewLog
from app.models.review_state import ReviewState
from app.models.vocab import Vocab
from app.services.queue_utils import get_queue_bucket
from app.services.scheduler_adapter import SchedulerAdapter


_scheduler = SchedulerAdapter()


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


def _as_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Normalize datetimes to timezone-aware UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _is_due_now(review_state: ReviewState, now: datetime) -> bool:
    due = _as_utc(review_state.due_date)
    return due is not None and due <= now


def _is_due_later_today(review_state: ReviewState, now: datetime, today_end: datetime) -> bool:
    due = _as_utc(review_state.due_date)
    return due is not None and now < due <= today_end


def _is_due_on_or_before_today(review_state: ReviewState, today_date) -> bool:
    """
    Day-based due check for static new/review queue.
    Ignores time-of-day entirely.
    """
    due = _as_utc(review_state.due_date)
    return due is not None and due.date() <= today_date


def _build_card_payload(db_session, review_state: ReviewState) -> dict:
    """
    Build the full frontend payload for a ReviewState, including preview labels
    for all rating buttons.
    """
    vocab = db_session.get(Vocab, review_state.vocab_id)
    if vocab is None:
        raise ValueError(f"Vocab {review_state.vocab_id} not found")

    sentence = None
    translation = None
    audio_path = None

    if review_state.current_generated_card_id is not None:
        generated_card = db_session.get(
            GeneratedCard,
            review_state.current_generated_card_id,
        )
        if generated_card is not None:
            sentence = generated_card.sentence
            translation = generated_card.translation
            audio_path = generated_card.tts_audio_path

    previews = _scheduler.preview_review_options(
        review_state,
        review_datetime=get_simulated_now(),
    )

    return {
        "review_state_id": review_state.id,
        "vocab_id": review_state.vocab_id,
        "term": vocab.term,
        "english_gloss": vocab.english_gloss,
        "sentence": sentence,
        "translation": translation,
        "audio_path": audio_path,
        "preview_intervals": previews,
    }


def get_next_card(user_id: int) -> Optional[dict]:
    """
    Return the next card for this user to review, or None if nothing is
    available now or later today.
    """
    db_session = get_session()
    try:
        review_state = _get_next_review_state(db_session, user_id)
        if review_state is None:
            return None

        return _build_card_payload(db_session, review_state)
    finally:
        db_session.close()


def process_review(user_id: int, review_state_id: int, rating: int) -> dict:
    """
    Process a user's rating for a ReviewState and return updated metadata.

    rating: int in {1, 2, 3, 4} -> Again, Hard, Good, Easy.
    """
    if rating not in (1, 2, 3, 4):
        raise ValueError(f"Invalid rating: {rating!r} (expected 1-4)")

    db_session = get_session()
    try:
        review_state = db_session.get(ReviewState, review_state_id)
        if review_state is None:
            raise ValueError(f"ReviewState {review_state_id} not found")
        if review_state.user_id != user_id:
            raise ValueError(
                f"ReviewState {review_state_id} does not belong to user {user_id}"
            )

        was_review = get_queue_bucket(review_state) == "review"
        review_now = get_simulated_now()

        _scheduler.apply_review(review_state, rating, review_datetime=review_now)
        _update_app_counters(review_state, rating, was_review)

        log_entry = ReviewLog(
            user_id=user_id,
            review_state_id=review_state.id,
            vocab_id=review_state.vocab_id,
            rating=rating,
            reviewed_at=review_now,
        )
        db_session.add(log_entry)

        db_session.add(review_state)
        db_session.commit()

        return {
            "review_state_id": review_state.id,
            "rating": rating,
            "new_interval": review_state.interval,
            "new_due_date": review_state.due_date.isoformat() if review_state.due_date else None,
            "success_streak": review_state.success_streak,
            "queue_bucket": get_queue_bucket(review_state),
            "scheduler_state": review_state.scheduler_state,
        }
    finally:
        db_session.close()


def _get_next_review_state(db_session, user_id: int) -> Optional[ReviewState]:
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

    # 1. Learning / relearning due right now
    learning_due_now = [
        rs for rs in learning_cards
        if _is_due_now(rs, now)
    ]
    if learning_due_now:
        learning_due_now.sort(key=lambda rs: (_as_utc(rs.due_date) or now, rs.id))
        return learning_due_now[0]

    # 2. Static daily queue for new + review due today or earlier
    static_due_today = [
        rs for rs in static_cards
        if _is_due_on_or_before_today(rs, today_date)
    ]
    if static_due_today:
        static_queue = _build_static_daily_queue(db_session, static_due_today)
        if static_queue:
            return static_queue[0]

    # 3. If nothing else is available, grab the next learning card due later today
    learning_due_later_today = [
        rs for rs in learning_cards
        if _is_due_later_today(rs, now, today_end)
    ]
    if learning_due_later_today:
        learning_due_later_today.sort(
            key=lambda rs: (_as_utc(rs.due_date) or today_end, rs.id)
        )
        return learning_due_later_today[0]

    return None


def _build_static_daily_queue(db_session, review_states: list[ReviewState]) -> list[ReviewState]:
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
            (_as_utc(rs.due_date).date() if _as_utc(rs.due_date) else datetime.max.date()),
            rs.id,
        )
    )

    def new_sort_key(rs: ReviewState):
        vocab = db_session.get(Vocab, rs.vocab_id)
        intro_index = vocab.intro_index if vocab and vocab.intro_index is not None else 10**9
        return (intro_index, rs.id)

    new_cards.sort(key=new_sort_key)

    if not review_cards:
        return new_cards
    if not new_cards:
        return review_cards

    first_review_day = _as_utc(review_cards[0].due_date).date() if _as_utc(review_cards[0].due_date) else datetime.max.date()

    # New cards are conceptually "today" queue items, so use today's day bucket.
    first_new_day = get_simulated_now().date()

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


def _update_app_counters(review_state: ReviewState, rating: int, was_review: bool) -> None:
    """
    Update app-owned counters that live on ReviewState.

    These are not owned by the scheduler adapter.
    """
    review_state.repetitions += 1

    # A lapse is when a previously graduated review card gets Again and
    # falls out of long-interval review.
    if rating == 1 and was_review and get_queue_bucket(review_state) != "review":
        review_state.lapses += 1

    if rating in (3, 4):
        review_state.success_streak += 1
    else:
        review_state.success_streak = 0