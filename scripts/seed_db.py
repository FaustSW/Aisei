"""
seed_db.py

Populates the database with:
    1. A default "Demo User" account
    2. Vocab items from data/seed_vocab.json
    3. ReviewStates for every (user, vocab) pair
    4. Optionally pre-generates GeneratedCards for a specific user

Safe to run multiple times - skips anything that already exists.

Usage:
    python -m scripts.seed_db
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import select

from app.db import get_session, init_db
from app.models.review_state import ReviewState
from app.models.user import User
from app.models.vocab import Vocab
from app.services.generation_service import ensure_generated_card_for_review_state
from app.services.scheduler_adapter import SchedulerAdapter
from app.services.settings_service import create_default_user_settings

SEED_VOCAB_FILE = os.path.join("data", "seed_vocab.json")

_scheduler = SchedulerAdapter()


def seed_default_user():
    """Create the default Demo User and settings if they don't already exist."""
    session = get_session()
    try:
        existing = session.exec(select(User).where(User.username == "demo_user")).first()
        if existing:
            create_default_user_settings(existing.id, db_session=session)
            print("Default user already exists.")
            return

        user = User(
            username="demo_user",
            display_name="Demo User",
            password_hash="123",
            avatar="avatar-1",
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        create_default_user_settings(user.id, db_session=session)

        print("Created default user: Demo User (demo_user)")
    finally:
        session.close()


def seed_vocab():
    """Read seed_vocab.json and insert any missing vocab records."""
    with open(SEED_VOCAB_FILE, "r") as f:
        entries = json.load(f)

    session = get_session()
    added = 0

    try:
        for entry in entries:
            existing = session.exec(select(Vocab).where(Vocab.term == entry["term"])).first()
            if existing:
                continue

            vocab = Vocab(
                term=entry["term"],
                english_gloss=entry["english_gloss"],
                intro_index=entry["intro_index"],
            )
            session.add(vocab)
            added += 1

        session.commit()
        print(f"Seeded {added} vocab items ({len(entries) - added} already existed).")
    finally:
        session.close()


def seed_review_states():
    """
    For every (user, vocab) pair, create a ReviewState if one doesn't
    already exist. Initializes SM-2 scheduling state so cards are
    immediately due.
    """
    session = get_session()
    added = 0

    try:
        users = session.exec(select(User)).all()
        vocabs = session.exec(select(Vocab)).all()

        if not users:
            print("No users found. Run seed_default_user() first.")
            return

        for user in users:
            for vocab in vocabs:
                existing = session.exec(
                    select(ReviewState)
                    .where(ReviewState.user_id == user.id)
                    .where(ReviewState.vocab_id == vocab.id)
                ).first()

                if existing:
                    continue

                card = ReviewState(user_id=user.id, vocab_id=vocab.id)
                _scheduler.initialize_new_card(card)
                session.add(card)
                added += 1

        session.commit()
        print(f"Seeded {added} review states.")
    finally:
        session.close()


def seed_generated_cards(username: str = "demo_user", limit: int | None = None):
    """
    Optionally pre-generate GeneratedCards for one user using their saved OpenAI key.

    This is not called automatically by run_demo.py anymore, because doing GPT
    generation on every DB wipe is expensive and requires that user's key to
    already exist in keyring.
    """
    session = get_session()
    added = 0

    try:
        user = session.exec(select(User).where(User.username == username)).first()
        if user is None:
            print(f"No user found for pre-generation: {username}")
            return

        review_states = session.exec(
            select(ReviewState).where(ReviewState.user_id == user.id)
        ).all()

        for rs in review_states:
            if limit is not None and added >= limit:
                break

            if rs.current_generated_card_id is not None:
                continue

            try:
                generated = ensure_generated_card_for_review_state(
                    db_session=session,
                    username=user.username,
                    review_state=rs,
                )
                if generated is not None:
                    added += 1
                    print(
                        f"Generated card {added}"
                        f" for vocab_id={rs.vocab_id}, review_state_id={rs.id}"
                    )
            except Exception as e:
                print(
                    f"Failed to pre-generate card for "
                    f"review_state_id={rs.id}, vocab_id={rs.vocab_id}: {e}"
                )

        print(f"Pre-generated {added} generated cards for user {username}.")
    finally:
        session.close()


if __name__ == "__main__":
    init_db()
    seed_default_user()
    seed_vocab()
    seed_review_states()