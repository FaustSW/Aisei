"""
Database Model: User

A registered account in the system.

Fields:
    id            - primary key
    username      - unique login/display name
    display_name  - friendly name shown on profile badge
    password_hash - password storage field (currently plaintext; hashing planned)
    avatar        - CSS class for avatar color (e.g. "avatar-1")
    created_at    - account creation timestamp (UTC)

This model only stores identity and auth data.
Learning state is tracked per-user through ReviewState records.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlmodel import SQLModel, Field


def utcnow() -> datetime:
    """Return the current time in UTC with timezone info attached."""
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    """
    A registered user account.

    Stores identity and auth credentials. Learning state
    is tracked per-user through ReviewState records, not here.
    """

    __tablename__ = "user"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    display_name: str = Field(default="")
    password_hash: str
    avatar: str = Field(default="avatar-1")
    created_at: datetime = Field(default_factory=utcnow)

    @property
    def initials(self) -> str:
        """Derive initials from display_name (e.g. 'Demo User' -> 'DU')."""
        parts = self.display_name.strip().split()
        if not parts:
            return self.username[:2].upper()
        return "".join(word[0] for word in parts).upper()[:2]