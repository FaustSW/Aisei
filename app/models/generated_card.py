"""
Database Model: GeneratedCard

A single generated display artifact for a ReviewState.

Stores the sentence, translation, and audio path that the user
sees during review. Demo seed scripts may create initial GeneratedCard
rows; generation_service is intended to create them dynamically once
AI integration is wired.

A ReviewState can have many GeneratedCards over its lifetime
(one per regeneration cycle). The active one is tracked via
ReviewState.current_generated_card_id.

Fields:
    id                     - primary key
    review_state_id        - foreign key to the parent ReviewState
    term_snapshot          - Spanish term at the time of generation
    english_gloss_snapshot - English meaning at the time of generation
    sentence               - generated Spanish example sentence (nullable)
    translation            - English translation of the sentence (nullable)
    tts_audio_path         - file path to generated TTS audio (nullable)
    generation_number      - which generation cycle produced this card (1-based)
    created_at             - when this card was generated (UTC)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import SQLModel, Field


def utcnow() -> datetime:
    """Return the current time in UTC with timezone info attached."""
    return datetime.now(timezone.utc)


class GeneratedCard(SQLModel, table=True):
    """
    One generated sentence/translation/audio bundle.

    Linked to a ReviewState. The ReviewState's current_generated_card_id
    field determines which GeneratedCard is shown during reviews.
    """

    __tablename__ = "generated_card"

    id:              Optional[int] = Field(default=None, primary_key=True)
    review_state_id: int           = Field(foreign_key="review_state.id", index=True)

    # Snapshots of what the user saw (denormalized from Vocab at generation time)
    term_snapshot:         str
    english_gloss_snapshot: str

    # Generated content (empty until generation_service is wired)
    sentence:      Optional[str] = Field(default=None)
    translation:   Optional[str] = Field(default=None)
    tts_audio_path: Optional[str] = Field(default=None)

    generation_number: int = Field(default=1)
    created_at: datetime   = Field(default_factory=utcnow)
