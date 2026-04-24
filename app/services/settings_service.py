"""
settings_service.py

Owns persistent user-specific application settings.

Current responsibilities:
- Create a default settings row for new users
- Load a user's settings, creating them if missing
- Read/update the daily new card limit
- Read/update the selected ElevenLabs voice

Future settings should also be managed here so the rest of the app can stay
decoupled from storage details.
"""

from __future__ import annotations

from app.clients.elevenlabs_client import ElevenLabsClient
from app.db import get_session
from app.models.user_settings import UserSettings, DEFAULT_TTS_VOICE_ID

DEFAULT_DAILY_NEW_LIMIT = 20
MIN_DAILY_NEW_LIMIT = 0
MAX_DAILY_NEW_LIMIT = 999


def clamp_daily_new_limit(value: int) -> int:
    """Clamp the daily new-card limit to a safe integer range."""
    return max(MIN_DAILY_NEW_LIMIT, min(MAX_DAILY_NEW_LIMIT, int(value)))


def validate_tts_voice_id(voice_id: str | None) -> str:
    """Normalize a selected ElevenLabs voice ID and return a safe persisted value."""
    if not voice_id:
        return DEFAULT_TTS_VOICE_ID

    return str(voice_id).strip()


def get_or_create_user_settings(user_id: int, db_session=None) -> UserSettings:
    """
    Return the settings row for a user, creating a default row if missing.

    If db_session is provided, the caller owns commit/close behavior.
    Otherwise this function opens and closes its own session.
    """
    owns_session = db_session is None
    db = db_session or get_session()

    try:
        settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
        if settings is None:
            settings = UserSettings(
                user_id=user_id,
                daily_new_limit=DEFAULT_DAILY_NEW_LIMIT,
                tts_voice_id=DEFAULT_TTS_VOICE_ID,
            )
            db.add(settings)
            db.commit()
            db.refresh(settings)

        if not settings.tts_voice_id:
            settings.tts_voice_id = DEFAULT_TTS_VOICE_ID
            db.add(settings)
            db.commit()
            db.refresh(settings)

        return settings
    finally:
        if owns_session:
            db.close()


def create_default_user_settings(user_id: int, db_session=None) -> UserSettings:
    """
    Ensure a default settings row exists for a new user and return it.
    """
    return get_or_create_user_settings(user_id, db_session=db_session)


def get_daily_new_limit(user_id: int, db_session=None) -> int:
    """Load the user's persisted daily new-card limit."""
    settings = get_or_create_user_settings(user_id, db_session=db_session)
    return clamp_daily_new_limit(settings.daily_new_limit)


def update_daily_new_limit(user_id: int, new_limit: int, db_session=None) -> UserSettings:
    """
    Persist a new daily new-card limit for the user and return updated settings.
    """
    owns_session = db_session is None
    db = db_session or get_session()

    try:
        settings = get_or_create_user_settings(user_id, db_session=db)
        settings.daily_new_limit = clamp_daily_new_limit(new_limit)
        db.add(settings)
        db.commit()
        db.refresh(settings)
        return settings
    finally:
        if owns_session:
            db.close()


def get_tts_voice_id(user_id: int, db_session=None) -> str:
    """Load the user's persisted ElevenLabs voice selection."""
    settings = get_or_create_user_settings(user_id, db_session=db_session)
    return validate_tts_voice_id(settings.tts_voice_id)


def update_tts_voice_id(user_id: int, voice_id: str, db_session=None) -> UserSettings:
    """
    Persist a new ElevenLabs voice selection for the user and return updated settings.
    """
    owns_session = db_session is None
    db = db_session or get_session()

    try:
        settings = get_or_create_user_settings(user_id, db_session=db)
        settings.tts_voice_id = validate_tts_voice_id(voice_id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
        return settings
    finally:
        if owns_session:
            db.close()

MIN_VOICE_SPEED = 0.7
MAX_VOICE_SPEED = 1.2
DEFAULT_VOICE_SPEED = 1.0


def validate_tts_voice_speed(speed: float) -> float:
    """Clamp and validate a voice speed value to the allowed range."""
    try:
        speed = float(speed)
    except (TypeError, ValueError):
        return DEFAULT_VOICE_SPEED

    if not (MIN_VOICE_SPEED <= speed <= MAX_VOICE_SPEED):
        raise ValueError(
            f"voice_speed must be between {MIN_VOICE_SPEED} and {MAX_VOICE_SPEED}"
        )

    return round(speed, 2)

def update_tts_voice_speed(user_id: int, speed: float, db_session=None) -> UserSettings:
    """
    Persist a new TTS playback speed for the user and return updated settings.
    """
    owns_session = db_session is None
    db = db_session or get_session()

    try:
        settings = get_or_create_user_settings(user_id, db_session=db)
        settings.tts_voice_speed = validate_tts_voice_speed(speed)
        db.add(settings)
        db.commit()
        db.refresh(settings)
        return settings
    finally:
        if owns_session:
            db.close()