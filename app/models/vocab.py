"""
Database Model: Vocab

A single Spanish vocabulary item.

Seeded vocab is global curriculum content shared across users. Manual vocab is
runtime content entered through the app and stored directly in the database.

Fields:
    id            - primary key
    term          - Spanish word or phrase (e.g., "ser"), unique
    english_gloss - short English meaning (e.g., "to be")
    intro_index   - seeded curriculum order; null for manual vocab
    source        - "seed" or "manual"
    created_at    - vocab creation timestamp (UTC)

User-specific learning state lives in ReviewState, not here.
Table name is "vocab" to match ReviewState's foreign_key="vocab.id".
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import SQLModel, Field


def utcnow() -> datetime:
    """Return the current time in UTC with timezone info attached."""
    return datetime.now(timezone.utc)


class Vocab(SQLModel, table=True):
    """
    A single vocabulary item.

    Seed vocab uses intro_index to determine curriculum order. Manual vocab
    leaves intro_index empty and is ordered by created_at when entering the
    new-card queue.
    """

    __tablename__ = "vocab"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    term: str
    english_gloss: str
    intro_index: Optional[int] = Field(default=None, unique=True)
    source: str = Field(default="seed", index=True)
    created_at: datetime = Field(default_factory=utcnow, index=True)