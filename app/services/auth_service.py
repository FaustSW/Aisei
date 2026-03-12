# app/services/auth_service.py

"""
auth_service.py

Centralizes application authentication and profile-management logic.

Current scope:
- Load login profile metadata
- Validate username/password pairs
- Create new users
- Seed initial ReviewState rows for new users
- Delete users and their review data

Future expansion:
- Replace plaintext passwords with hashing + verification
- Add password policy / validation rules
"""

from __future__ import annotations

from sqlmodel import select

from app.db import get_session
from app.models.review_state import ReviewState
from app.models.user import User
from app.models.vocab import Vocab
from app.services.scheduler_adapter import SchedulerAdapter


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
    """Remove a user and all of their ReviewState rows."""
    db = get_session()
    try:
        user = db.get(User, user_id)
        if user is None:
            raise ValueError("User not found")

        states = db.exec(select(ReviewState).where(ReviewState.user_id == user_id)).all()
        for rs in states:
            db.delete(rs)

        db.delete(user)
        db.commit()
    finally:
        db.close()


def _seed_review_states(db, user_id: int) -> None:
    """Create a ReviewState for every vocab item for this new user."""
    vocabs = db.exec(select(Vocab)).all()
    for vocab in vocabs:
        rs = ReviewState(user_id=user_id, vocab_id=vocab.id)
        _scheduler.initialize_new_card(rs)
        db.add(rs)
    db.commit()