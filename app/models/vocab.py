"""
Database Model: Vocab

A single Spanish vocabulary item from the seeded dataset.
This is global content - shared across all users, not user-specific.

Fields:
    id            - primary key
    term          - Spanish word or phrase (e.g., "ser"), unique
    english_gloss - short English meaning (e.g., "to be")
    intro_index   - position in the learning sequence, unique

User-specific learning state lives in ReviewState, not here.
Table name is "vocab" to match ReviewState's foreign_key="vocab.id".
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import SQLModel, Field


class Vocab(SQLModel, table=True):
    """
    A single vocabulary item from the seeded dataset.

    One Vocab can have many ReviewStates (one per user studying it).
    The intro_index determines when this item enters a user's
    study rotation via the progression system.
    """

    __tablename__ = "vocab"

    id: Optional[int] = Field(default=None, primary_key=True)
    term: str = Field(unique=True)            # Spanish word, e.g. "casa"
    english_gloss: str                         # English meaning, e.g. "house"
    intro_index: int = Field(unique=True)      # Position in learning sequence
