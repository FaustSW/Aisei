"""
Database Model: ReviewLog

A single review event, recorded for stats and auditing.

Fields:
    id              - primary key
    user_id         - foreign key to User
    review_state_id - foreign key to ReviewState
    vocab_id        - foreign key to Vocab (denormalized for easier stats queries)
    rating          - user rating value (1=Again, 2=Hard, 3=Good, 4=Easy)
    reviewed_at     - timestamp of when the review happened (UTC)

This table does not affect scheduling. The scheduler only reads/writes
the ReviewState model. ReviewLog is append-only - review_service creates
entries, stats_service reads them for metrics.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import SQLModel, Field


def utcnow() -> datetime:
    """Return the current time in UTC with timezone info attached."""
    return datetime.now(timezone.utc)


class ReviewLog(SQLModel, table=True):
    """
    A single review event record.

    One review = one row. Append-only during normal use.
    Used by stats_service for metrics, not by the scheduler.
    """

    __tablename__ = "review_log"

    id: Optional[int] = Field(default=None, primary_key=True)

    user_id:         int = Field(foreign_key="user.id",          index=True)
    review_state_id: int = Field(foreign_key="review_state.id",  index=True)
    vocab_id:        int = Field(foreign_key="vocab.id",         index=True)

    rating: int  # 1=Again, 2=Hard, 3=Good, 4=Easy

    reviewed_at: datetime = Field(default_factory=utcnow, index=True)
