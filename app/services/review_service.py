"""
review_service.py

Owns the end-to-end "review loop" workflow for a user.

Primary responsibilities:
    - Select the next card to review (earliest due date).
    - Prepare a display-ready card payload for the template.
    - Process a submitted rating (Again/Hard/Good/Easy).
    - Update the card's scheduling state via scheduler_adapter.
    - Update app-owned counters (repetitions, lapses, success_streak).
    - Log review events to ReviewLog for stats.

This is the orchestration layer for reviewing. It coordinates
models + scheduler + (eventually) generation, but does not
implement their internals.

Architectural position:
    Blueprint (review.py) -> review_service -> scheduler_adapter (SM-2)
                                            -> models (Card, Vocab, ReviewLog)
                                            -> generation_service (future, for AI sentences)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import select, col

from app.db import get_session
from app.models.card import Card
from app.models.vocab import Vocab
from app.models.review_log import ReviewLog
from app.services.scheduler_adapter import SchedulerAdapter


# Single shared scheduler instance for the app.
# Created once here so every call to review_service uses the same config.
_scheduler = SchedulerAdapter()


# ------------------------------------------------------------------
# Core review loop
# ------------------------------------------------------------------

def get_next_card(user_id: int) -> Optional[dict]:
    """
    Return the next card for this user to review, or None if nothing is due.

    Returns a dict with everything the template needs to render a card:
        {
            "card_id": int,
            "vocab_id": int,
            "term": str,
            "english_gloss": str,
            "sentence": str or None,
            "translation": str or None,
            "audio_path": str or None,
        }
    """
    session = get_session()
    try:
        card = _get_due_card(session, user_id)

        if card is None:
            return None

        # Look up the vocab item for this card
        vocab = session.get(Vocab, card.vocab_id)

        return {
            "card_id": card.id,
            "vocab_id": card.vocab_id,
            "term": vocab.term,
            "english_gloss": vocab.english_gloss,
            "sentence": card.sentence_cached,
            "translation": card.translation_cached,
            "audio_path": card.audio_path,
        }
    finally:
        session.close()


def process_review(user_id: int, card_id: int, rating: int) -> dict:
    """
    Process a user's rating for a card and return the updated state.

    Loads the card, verifies ownership, runs the rating through
    scheduler_adapter, updates app-owned counters, logs to ReviewLog,
    and commits everything in one transaction.

    rating: int in {1, 2, 3, 4} -> Again, Hard, Good, Easy.

    Returns a dict with card_id, rating, new_interval,
    new_due_date (ISO string), and success_streak.
    """
    if rating not in (1, 2, 3, 4):
        raise ValueError(f"Invalid rating: {rating!r} (expected 1-4)")

    session = get_session()
    try:
        # Load card and verify ownership
        card = session.get(Card, card_id)
        if card is None:
            raise ValueError(f"Card {card_id} not found")
        if card.user_id != user_id:
            raise ValueError(f"Card {card_id} does not belong to user {user_id}")

        # Run through the SM-2 scheduler (mutates card in place)
        _scheduler.apply_review(card, rating)

        # Update app-owned counters
        _update_app_counters(card, rating)

        # Stamp the update time
        card.updated_at = datetime.now(timezone.utc)

        # Log the review event
        log_entry = ReviewLog(
            user_id=user_id,
            card_id=card.id,
            vocab_id=card.vocab_id,
            rating=rating,
        )
        session.add(log_entry)

        # Commit card updates and the log entry together
        session.add(card)
        session.commit()

        return {
            "card_id": card.id,
            "rating": rating,
            "new_interval": card.interval,
            "new_due_date": card.due_date.isoformat(),
            "success_streak": card.success_streak,
        }
    finally:
        session.close()


# ------------------------------------------------------------------
# Card selection
# ------------------------------------------------------------------

def _get_due_card(session, user_id: int) -> Optional[Card]:
    """
    Return the user's card with the earliest due_date that is at or before now.
    Returns None if nothing is due.
    """
    now = datetime.now(timezone.utc)
    statement = (
        select(Card)
        .where(Card.user_id == user_id)
        .where(col(Card.due_date) <= now)
        .order_by(col(Card.due_date).asc())
        .limit(1)
    )
    return session.exec(statement).first()


# ------------------------------------------------------------------
# App-owned counter updates
# ------------------------------------------------------------------

def _update_app_counters(card: Card, rating: int) -> None:
    """
    Update the counters that live on Card but aren't touched by
    the scheduler_adapter (repetitions, lapses, success_streak).
    """
    card.repetitions += 1

    # A lapse is when a Review-state card gets an Again rating.
    # After the scheduler runs, a lapsed card moves to Relearning (3),
    # so we check the post-review state.
    if rating == 1 and card.scheduler_state == 3:
        card.lapses += 1

    # Success streak tracks consecutive Good/Easy reviews for regeneration logic
    if rating in (3, 4):
        card.success_streak += 1
    else:
        card.success_streak = 0
