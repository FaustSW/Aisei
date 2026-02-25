"""
seed_db.py

Populates the vocab table from data/seed_vocab.json.
Skips any vocab items that already exist (matched by term)
so it's safe to run multiple times.

Usage:
    python -m scripts.seed_db
"""

import json
import os
import sys

# Add project root to path so "from app..." imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import select

from app.db import get_session
from app.models.vocab import Vocab

SEED_FILE = os.path.join("data", "seed_vocab.json")


def seed_vocab():
    """Read seed_vocab.json and insert any missing vocab records."""
    with open(SEED_FILE, "r") as f:
        entries = json.load(f)

    session = get_session()
    added = 0

    try:
        for entry in entries:
            # Skip if this term already exists in the database
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


if __name__ == "__main__":
    seed_vocab()
