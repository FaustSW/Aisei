"""
auth_service.py

Centralizes authentication and profile-management logic.

Responsibilities:
- Load login profile metadata for the frontend
- Validate username/password pairs
- Create new users and seed their initial ReviewState rows
- Delete users and all user-owned review data

Future expansion:
- Replace plaintext passwords with hashing + verification
- Add password policy / validation rules
"""

from __future__ import annotations

from sqlmodel import select

from app.db import get_session
from app.models.generated_card import GeneratedCard
from app.models.review_log import ReviewLog
from app.models.review_state import ReviewState
from app.models.user import User
from app.models.user_settings import UserSettings
from app.models.vocab import Vocab
from app.services.scheduler_adapter import SchedulerAdapter
from app.services.settings_service import create_default_user_settings


_scheduler = SchedulerAdapter()


def get_profiles_list() -> list[dict]:
    """Load all users from DB and return frontend-safe profile metadata."""
    db = get_session()
    try:
        users = db.exec(select(User)).all()
        return [
            {
                "id": u.id,
                "name": u.display_name,
                "username": u.username,
                "avatar": u.avatar,
                "initials": u.initials,
            }
            for u in users
        ]
    finally:
        db.close()


def authenticate_user(username: str, password: str) -> User:
    """
    Validate a username/password pair and return the matching User.

    Password storage is still plaintext for now and should be replaced with
    proper hashing later.
    """
    username = username.strip()
    password = password.strip()

    if not username:
        raise ValueError("Username is required")
    if not password:
        raise ValueError("Password is required")

    db = get_session()
    try:
        user = db.exec(select(User).where(User.username == username)).first()

        if user is None:
            raise ValueError("User not found")
        if user.password_hash != password:
            raise ValueError("Incorrect password")

        return user
    finally:
        db.close()


def create_user(
    display_name: str,
    username: str,
    password: str,
    avatar: str = "avatar-1",
) -> dict:
    """Create a new user, seed their review states, and return profile metadata."""
    display_name = display_name.strip()
    username = username.strip()
    password = password.strip()

    if not username or not display_name or not password:
        raise ValueError("All fields are required")

    db = get_session()
    try:
        existing = db.exec(select(User).where(User.username == username)).first()
        if existing:
            raise ValueError("Username already exists")

        user = User(
            username=username,
            display_name=display_name,
            password_hash=password,  # plaintext for now
            avatar=avatar,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        create_default_user_settings(user.id, db_session=db)
        _seed_review_states(db, user.id)

        return {
            "id": user.id,
            "name": user.display_name,
            "username": user.username,
            "avatar": user.avatar,
            "initials": user.initials,
        }
    finally:
        db.close()


def delete_user(user_id: int) -> None:
    """
    Delete a user and all user-owned review data.

    Deletion order matters:
    - ReviewLog rows first
    - GeneratedCard rows next
    - ReviewState rows next
    - UserSettings row next
    - User row last
    """
    db = get_session()
    try:
        user = db.get(User, user_id)
        if user is None:
            raise ValueError("User not found")

        states = db.exec(select(ReviewState).where(ReviewState.user_id == user_id)).all()
        
        # Collect ReviewState IDs first so GeneratedCard rows can be deleted
        # before their parent ReviewState rows are removed.
        state_ids = [rs.id for rs in states if rs.id is not None]

        logs = db.exec(select(ReviewLog).where(ReviewLog.user_id == user_id)).all()
        for log in logs:
            db.delete(log)

        if state_ids:
            generated_cards = db.exec(select(GeneratedCard).where(GeneratedCard.review_state_id.in_(state_ids))).all()
            for generated_card in generated_cards:
                db.delete(generated_card)

        for rs in states:
            db.delete(rs)

        manual_vocabs = db.exec(
            select(Vocab)
            .where(Vocab.user_id == user_id)
            .where(Vocab.source == "manual")
        ).all()
        for vocab in manual_vocabs:
            db.delete(vocab)

        user_settings = db.exec(select(UserSettings).where(UserSettings.user_id == user_id)).first()
        if user_settings is not None:
            db.delete(user_settings)

        db.delete(user)
        db.commit()
    finally:
        db.close()


def _seed_review_states(db, user_id: int) -> None:
    """Create a ReviewState for every vocab item for this new user."""
    vocabs = db.exec(select(Vocab).where(Vocab.source == "seed")).all()
    for vocab in vocabs:
        rs = ReviewState(user_id=user_id, vocab_id=vocab.id)
        _scheduler.initialize_new_card(rs)
        db.add(rs)
    db.commit()