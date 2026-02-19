"""
scheduler_adapter.py

Translation layer between our Card model and the anki-sm-2 library.

Architecture:
    review_service -> scheduler_adapter -> SM-2 library (black box)

Responsibilities:
    - Translate Card scheduling fields <-> SM2Card
    - Pass rating through the scheduler
    - Apply updated SM-2 values back onto Card (mutate in place)
    - Return the Card (caller persists)

"""

from __future__ import annotations

from datetime import datetime, timezone

from anki_sm_2 import (
    Scheduler as SM2Scheduler,
    Card as SM2Card,
    Rating as SM2Rating,
    State as SM2State,
)

# Adjust if your project layout differs
from models.card import Card


class SchedulerAdapter:

    RATING_MAP = {
        1: SM2Rating.Again,
        2: SM2Rating.Hard,
        3: SM2Rating.Good,
        4: SM2Rating.Easy,
    }

    def __init__(self) -> None:
        """
        Single shared scheduler instance with Anki's default config.

        Defaults (from Anki docs):
            learning_steps:      (1 min, 10 min)
            graduating_interval: 1 day
            easy_interval:       4 days
            relearning_steps:    (10 min,)
            starting_ease:       2.5
            easy_bonus:          1.3
            hard_interval:       1.2

        If you need to tweak any of these, this __init__ is the
        one and only place to do it.
        """
        self._scheduler = SM2Scheduler()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def initialize_new_card(self, card: Card) -> Card:
        """
        Populate a Card's scheduling fields with initial SM-2 state.

        Call this when creating a new card for a user (e.g., when a new
        vocab item is introduced via progression_service).

        Mutates card in place. Returns it for convenience.
        """
        sm2_card = SM2Card()
        self._write_sm2_to_card(sm2_card, card)
        return card

    def apply_review(self, card: Card, rating: int) -> Card:
        """
        Run a review through the SM-2 scheduler and update the Card.

        Args:
            card:   Card model instance with current scheduling state.
            rating: int in {1, 2, 3, 4} -> Again, Hard, Good, Easy.

        Mutates card in place. Returns it for convenience.
        Caller is responsible for updating app-owned fields
        (repetitions, lapses, success_streak) and persisting.
        """
        if rating not in self.RATING_MAP:
            raise ValueError(f"Invalid rating: {rating!r} (expected 1-4)")

        sm2_card = self._read_card_to_sm2(card)
        updated_sm2, _log = self._scheduler.review_card(
            sm2_card, self.RATING_MAP[rating]
        )
        self._write_sm2_to_card(updated_sm2, card)
        return card

    # ------------------------------------------------------------------
    # Translation helpers
    # ------------------------------------------------------------------

    def _read_card_to_sm2(self, card: Card) -> SM2Card:
        """Card model -> SM2Card object."""
        return SM2Card(
            state=SM2State(card.scheduler_state or 1),
            step=card.learning_step,
            ease=card.ease_factor,
            due=self._ensure_utc(card.due_date),
            current_interval=card.interval,
        )

    def _write_sm2_to_card(self, sm2_card: SM2Card, card: Card) -> None:
        """
        SM2Card -> Card model scheduling fields (mutates in place).

        Only touches the 5 fields the SM-2 library owns.
        Does NOT touch: repetitions, lapses, success_streak.
        Those are app-owned counters updated by review_service.
        """
        card.scheduler_state = int(sm2_card.state.value)
        card.learning_step = sm2_card.step
        card.ease_factor = sm2_card.ease
        card.due_date = self._ensure_utc(sm2_card.due)
        card.interval = sm2_card.current_interval

    @staticmethod
    def _ensure_utc(dt: datetime) -> datetime:
        """
        Guarantee a timezone-aware UTC datetime.

        The SM-2 library returns aware datetimes, but if a naive
        datetime leaks in from the DB or tests, this prevents
        silent miscalculation of intervals and due dates.
        """
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
