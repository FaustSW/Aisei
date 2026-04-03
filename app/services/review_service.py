"""
review_service.py

Owns the end-to-end review workflow for a user.

Primary responsibilities:
    - Select the next card for the user to review (via queue_service).
    - Build a display-ready payload for the template / frontend.
    - Process submitted ratings (Again / Hard / Good / Easy).
    - Update ReviewState scheduling fields via scheduler_adapter.
    - Update app-owned counters on ReviewState (repetitions, lapses, streak).
    - Log review events to ReviewLog.
"""

from __future__ import annotations

from typing import Optional

from app.db import get_session
from app.models.generated_card import GeneratedCard
from app.models.review_log import ReviewLog
from app.models.review_state import ReviewState
from app.models.user import User
from app.models.vocab import Vocab
from app.services.generation_service import ensure_generated_card_for_review_state
from app.services.queue_service import (
    get_next_review_state,
    get_queue_bucket,
    get_simulated_now,
)
from app.services.scheduler_adapter import SchedulerAdapter


_scheduler = SchedulerAdapter()


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

    # Some ReviewStates will not have an active GeneratedCard yet
    # (for example, seeded/non-generation flows), so these fields
    # intentionally remain None in that case.
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

    If the next ReviewState has no GeneratedCard yet, attempt lazy generation
    using the logged-in user's saved OpenAI API key.
    """
    db_session = get_session()
    try:
        user = db_session.get(User, user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")

        review_state = get_next_review_state(db_session, user_id)
        if review_state is None:
            return None

        if review_state.current_generated_card_id is None:
            try:
                ensure_generated_card_for_review_state(
                    db_session=db_session,
                    username=user.username,
                    review_state=review_state,
                )
                db_session.refresh(review_state)
            except Exception as e:
                # For now, fail soft. The card can still render term/gloss even if
                # AI generation is unavailable or the user's OpenAI key is missing.
                print(
                    f"[review_service] lazy generation failed for "
                    f"user={user.username!r}, review_state_id={review_state.id}: {e}"
                )

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


def _update_app_counters(review_state: ReviewState, rating: int, was_review: bool) -> None:
    """
    Update app-owned counters that live on ReviewState.

    These are not owned by the scheduler adapter.
    """
    review_state.repetitions += 1

    # A lapse happens when a card was in the Review queue before this rating
    # but got moved out of Review after the scheduler ran (i.e., it was demoted
    # to Relearning because the user pressed Again).
    if rating == 1 and was_review and get_queue_bucket(review_state) != "review":
        review_state.lapses += 1

    # Success streak tracks consecutive Good/Easy ratings.
    # Used by regeneration logic to decide when to generate a new sentence.
    if rating in (3, 4):
        review_state.success_streak += 1
    else:
        review_state.success_streak = 0
