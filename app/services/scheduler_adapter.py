"""
scheduler_adapter.py

Translation layer between our ReviewState model and the anki-sm-2 library.

Architecture:
    review_service -> scheduler_adapter -> SM-2 library (black box)

Responsibilities:
    - Translate ReviewState scheduling fields <-> SM2Card
    - Pass ratings through the scheduler
    - Apply updated SM-2 values back onto ReviewState (mutate in place)
    - Preview the next interval / due timing for each rating option

Important note:
The anki-sm-2 library has no separate "New" state. New cards begin in
State.Learning with step 0. We therefore treat the library's state as
scheduler-owned internal data and infer user-facing queue buckets elsewhere
from repetitions + interval.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional

from anki_sm_2 import (
    Scheduler as SM2Scheduler,
    Card as SM2Card,
    Rating as SM2Rating,
    State as SM2State,
)

from app.models.review_state import ReviewState


class SchedulerAdapter:
    RATING_MAP = {
        1: SM2Rating.Again,
        2: SM2Rating.Hard,
        3: SM2Rating.Good,
        4: SM2Rating.Easy,
    }

    def __init__(self) -> None:
        self._scheduler = SM2Scheduler()

    def initialize_new_card(self, card: ReviewState) -> ReviewState:
        """
        Populate a ReviewState's scheduler-owned fields with initial SM-2 state.

        New cards in this library begin in Learning state at step 0 and are
        immediately due.
        """
        sm2_card = SM2Card()
        self._write_sm2_to_card(sm2_card, card)
        return card

    def apply_review(
        self,
        card: ReviewState,
        rating: int,
        review_datetime: Optional[datetime] = None,
    ) -> ReviewState:
        """
        Run a review through the SM-2 scheduler and update the ReviewState.

        Mutates card in place. Caller is responsible for app-owned counters
        and persistence.
        """
        if rating not in self.RATING_MAP:
            raise ValueError(f"Invalid rating: {rating!r} (expected 1-4)")

        review_datetime = self._ensure_utc(review_datetime)

        sm2_card = self._read_card_to_sm2(card)
        updated_sm2, _log = self._scheduler.review_card(
            sm2_card,
            self.RATING_MAP[rating],
            review_datetime=review_datetime,
        )
        self._write_sm2_to_card(updated_sm2, card)
        return card

    def preview_review_options(
        self,
        card: ReviewState,
        review_datetime: Optional[datetime] = None,
    ) -> dict[str, dict]:
        """
        Simulate all 4 rating options for the given ReviewState without mutating it.

        Returns:
            {
                "1": {"label": "< 1m", "due_date": "...", "interval": 0, "scheduler_state": 1},
                "2": {"label": "6m",   "due_date": "...", "interval": 0, "scheduler_state": 1},
                "3": {"label": "10m",  "due_date": "...", "interval": 0, "scheduler_state": 1},
                "4": {"label": "4d",   "due_date": "...", "interval": 4, "scheduler_state": 2},
            }
        """
        review_datetime = self._ensure_utc(review_datetime)
        base_sm2 = self._read_card_to_sm2(card)

        previews: dict[str, dict] = {}

        for rating_value, sm2_rating in self.RATING_MAP.items():
            preview_sm2, _log = self._scheduler.review_card(
                base_sm2,
                sm2_rating,
                review_datetime=review_datetime,
            )

            due_dt = self._ensure_utc(preview_sm2.due)
            previews[str(rating_value)] = {
                "label": self._format_preview_label(preview_sm2, review_datetime),
                "due_date": due_dt.isoformat(),
                "interval": preview_sm2.current_interval if preview_sm2.current_interval is not None else 0,
                "scheduler_state": int(preview_sm2.state.value),
            }

        return previews

    def _read_card_to_sm2(self, card: ReviewState) -> SM2Card:
        """
        ReviewState -> SM2Card object.

        scheduler_state stores the library's raw state values:
            1 = Learning
            2 = Review
            3 = Relearning
        """
        state_value = card.scheduler_state or int(SM2State.Learning.value)

        return SM2Card(
            state=SM2State(state_value),
            step=card.learning_step,
            ease=card.ease_factor,
            due=self._ensure_utc(card.due_date),
            current_interval=card.interval,
        )

    def _write_sm2_to_card(self, sm2_card: SM2Card, card: ReviewState) -> None:
        """
        SM2Card -> ReviewState scheduler-owned fields (mutates in place).
        """
        card.scheduler_state = int(sm2_card.state.value)
        card.learning_step = sm2_card.step
        card.ease_factor = sm2_card.ease
        card.due_date = self._ensure_utc(sm2_card.due)
        card.interval = sm2_card.current_interval if sm2_card.current_interval is not None else 0

    def _format_preview_label(self, sm2_card: SM2Card, review_datetime: datetime) -> str:
        """
        Format a user-facing interval label for a simulated rating result.

        Learning / relearning results are shown in minutes / hours.
        Review results are shown in days.
        """
        due_dt = self._ensure_utc(sm2_card.due)
        delta = due_dt - review_datetime

        # Review state -> day-based interval label
        if sm2_card.state == SM2State.Review and sm2_card.current_interval is not None:
            return self._format_days(sm2_card.current_interval)

        total_seconds = max(0, int(delta.total_seconds()))

        if total_seconds < 60:
            return "< 1m"

        minutes = total_seconds // 60
        if minutes < 60:
            return f"{minutes}m"

        hours = minutes // 60
        if hours < 24:
            return f"{hours}h"

        days = round(total_seconds / 86400)
        return self._format_days(max(1, days))

    @staticmethod
    def _format_days(days: int) -> str:
        if days < 30:
            return f"{days}d"
        if days < 365:
            months = round(days / 30)
            return f"{months}mo"
        years = round(days / 365)
        return f"{years}y"

    @staticmethod
    def _ensure_utc(dt: datetime | None) -> datetime:
        if dt is None:
            return datetime.now(timezone.utc)
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)