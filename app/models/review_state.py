"""
Database Model: ReviewState

Persistent scheduler state for a (user, vocab) pair.

This is the source of truth for SM-2 scheduling. It lives as long
as the user is studying that vocab item and survives card regeneration.

Fields (SM-2, owned by scheduler_adapter):
    scheduler_state - SM-2 state value (1=Learning, 2=Review, 3=Relearning)
    learning_step   - current position in the learning/relearning step sequence
    ease_factor     - SM-2 ease multiplier (starts at 2.5)
    interval        - days until next review (0 while in learning steps)
    due_date        - when this card is next due for review (UTC)

Fields (app-owned, updated by review_service):
    repetitions    - total number of reviews completed
    lapses         - times a Review-state card was rated Again
    success_streak - consecutive Good/Easy ratings (drives regeneration)

Fields (linking):
    current_generated_card_id - points to the active GeneratedCard (nullable)

Relationships:
    User        > many ReviewState  (one per vocab item being studied)
    Vocab       > many ReviewState  (one per user studying it)
    ReviewState > many GeneratedCard (one active at a time)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import SQLModel, Field


class ReviewState(SQLModel, table=True):
    """
    Scheduling state for one user studying one vocab item.

    SM-2 fields are managed exclusively by scheduler_adapter.
    App-owned counters (repetitions, lapses, success_streak) are
    managed by review_service. Both are persisted here.
    """

    __tablename__ = "review_state"

    id:      Optional[int] = Field(default=None, primary_key=True)
    user_id: int           = Field(foreign_key="user.id",  index=True)
    vocab_id: int          = Field(foreign_key="vocab.id", index=True)

    # SM-2 scheduling fields (owned by scheduler_adapter)
    scheduler_state: int            = Field(default=1)
    learning_step:   Optional[int]  = Field(default=0)
    ease_factor:     float          = Field(default=2.5)
    interval:        int            = Field(default=0)
    due_date:        Optional[datetime] = Field(default=None, index=True)

    # App-owned counters (owned by review_service)
    repetitions:     int = Field(default=0)
    lapses:          int = Field(default=0)
    success_streak:  int = Field(default=0)

    # Points to the currently active GeneratedCard (nullable until first generation)
    current_generated_card_id: Optional[int] = Field(default=None, foreign_key="generated_card.id")
