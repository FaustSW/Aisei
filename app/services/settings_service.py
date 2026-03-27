"""
settings_service.py

Owns persistent user-specific application settings.

Current responsibilities:
- Create a default settings row for new users
- Load a user's settings, creating them if missing
- Read/update the daily new card limit

Future settings should also be managed here so the rest of the app can stay
decoupled from storage details.
"""

from __future__ import annotations

from app.db import get_session
from app.models.user_settings import UserSettings

DEFAULT_DAILY_NEW_LIMIT = 20
MIN_DAILY_NEW_LIMIT = 0
MAX_DAILY_NEW_LIMIT = 999


def clamp_daily_new_limit(value: int) -> int:
    """Clamp the daily new-card limit to a safe integer range."""
    return max(MIN_DAILY_NEW_LIMIT, min(MAX_DAILY_NEW_LIMIT, int(value)))


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
            )
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