"""
manual_vocab_service.py

Creates user-entered vocab cards for the review flow.

Manual vocab is stored directly in the database. It does not modify seed JSON
and does not use intro_index. Queue priority is handled by queue_service.
"""

from __future__ import annotations

from sqlmodel import select

from app.db import get_session
from app.models.generated_card import GeneratedCard
from app.models.review_state import ReviewState
from app.models.user import User
from app.models.vocab import Vocab
from app.services.generation_service import generate_manual_card_content
from app.services.queue_service import invalidate_static_daily_queue
from app.services.scheduler_adapter import SchedulerAdapter


_scheduler = SchedulerAdapter()


def create_manual_vocab_card(
    user_id: int,
    term: str,
    english_gloss: str | None = None,
    sentence: str | None = None,
    translation: str | None = None,
) -> dict:
    """
    Create a manual vocab item and make it available as a new card.
    """
    term = str(term or "").strip()
    english_gloss = str(english_gloss or "").strip()
    sentence = str(sentence or "").strip()
    translation = str(translation or "").strip()

    if not term:
        raise ValueError("Vocab term is required")

    db = get_session()
    try:
        user = db.get(User, user_id)
        if user is None:
            raise ValueError(f"User {user_id} not found")
        
        candidate_vocabs = db.exec(
            select(Vocab).where(
                (Vocab.source == "seed") | (Vocab.user_id == user_id)
            )
        ).all()

        matching_vocab_ids = [
            vocab.id
            for vocab in candidate_vocabs
            if vocab.id is not None and vocab.term.strip().casefold() == term.casefold()
        ]

        if matching_vocab_ids:
            existing_state = db.exec(
                select(ReviewState)
                .where(ReviewState.user_id == user_id)
                .where(ReviewState.vocab_id.in_(matching_vocab_ids))
            ).first()

            if existing_state is not None:
                raise ValueError("This vocab item is already in your review queue")

        completed_content = generate_manual_card_content(
            username=user.username,
            term=term,
            english_gloss=english_gloss,
            sentence=sentence,
            translation=translation,
        )

        vocab = Vocab(
            user_id=user_id,
            term=term,
            english_gloss=completed_content["english_gloss"],
            intro_index=None,
            source="manual",
        )
        db.add(vocab)
        db.flush()

        review_state = ReviewState(user_id=user_id, vocab_id=vocab.id)
        _scheduler.initialize_new_card(review_state)
        db.add(review_state)
        db.flush()

        generated_card = GeneratedCard(
            review_state_id=review_state.id,
            term_snapshot=vocab.term,
            english_gloss_snapshot=completed_content["english_gloss"],
            sentence=completed_content["sentence"],
            translation=completed_content["translation"],
            generation_number=1,
        )
        db.add(generated_card)
        db.flush()

        review_state.current_generated_card_id = generated_card.id
        db.add(review_state)

        db.commit()
        db.refresh(review_state)
        db.refresh(vocab)
        db.refresh(generated_card)

        invalidate_static_daily_queue(user_id)

        return {
            "review_state_id": review_state.id,
            "vocab_id": vocab.id,
            "generated_card_id": generated_card.id,
            "term": vocab.term,
            "english_gloss": completed_content["english_gloss"],
            "sentence": generated_card.sentence,
            "translation": generated_card.translation,
        }
    finally:
        db.close()