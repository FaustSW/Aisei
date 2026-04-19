"""
Database Model: UserSettings

Persistent per-user application preferences.

Current settings:
    daily_new_limit - max number of new cards allowed in the static daily queue
    tts_voice_id    - selected ElevenLabs voice for word/sentence playback

Future settings to add here:
    - theme selection
    - additional audio preferences
    - review UI preferences
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import SQLModel, Field


DEFAULT_TTS_VOICE_ID = "U9jmr7kY6mMqS39kfA01"


class UserSettings(SQLModel, table=True):
    """
    Persistent per-user settings for the review experience.

    This table is intentionally small for now, but it is the long-term home
    for user-specific app preferences that should survive across sessions.
    """

    __tablename__ = "user_settings"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True, index=True)

    daily_new_limit: int = Field(default=20)
    tts_voice_id: str = Field(default=DEFAULT_TTS_VOICE_ID)