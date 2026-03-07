"""
seed_db.py

Populates the database with:
    1. A default "Demo User" account
    2. Vocab items from data/seed_vocab.json
    3. ReviewStates for every (user, vocab) pair

Safe to run multiple times — skips anything that already exists.

Usage:
    python -m scripts.seed_db
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import select

from app.db import get_session, init_db
from app.models.vocab import Vocab
from app.models.user import User
from app.models.review_state import ReviewState
from app.services.scheduler_adapter import SchedulerAdapter

SEED_FILE = os.path.join("data", "seed_vocab.json")

_scheduler = SchedulerAdapter()


def seed_default_user():
    """Create the default Demo User if it doesn't already exist."""
    session = get_session()
    try:
        existing = session.exec(select(User).where(User.username == "demo_user")).first()
        if existing:
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
        print("Created default user: Demo User (demo_user)")
    finally:
        session.close()


def seed_vocab():
    """Read seed_vocab.json and insert any missing vocab records."""
    with open(SEED_FILE, "r") as f:
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


if __name__ == "__main__":
    init_db()
    seed_default_user()
    seed_vocab()
    seed_review_states()
