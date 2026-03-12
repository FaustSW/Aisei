"""
queue_utils.py

Shared app-side queue classification helpers.

Important:
These helpers define the user-facing queue buckets used by the app for:
- progress counts
- queue prioritization
- future daily queue construction

They do NOT rely directly on the SM-2 library's raw state enum for bucket
classification. Instead, they derive buckets from app-visible fields on
ReviewState.
"""

from __future__ import annotations

from app.models.review_state import ReviewState


def get_queue_bucket(review_state: ReviewState) -> str:
    """
    Derive the app-side queue bucket for a ReviewState.

    Buckets:
        - "new": never reviewed yet
        - "learning": seen before, but not yet in long-interval review
        - "review": graduated into long-interval review
    """
    if review_state.repetitions == 0:
        return "new"

    if review_state.interval and review_state.interval > 0:
        return "review"

    return "learning"


def is_new_card(review_state: ReviewState) -> bool:
    return get_queue_bucket(review_state) == "new"


def is_learning_card(review_state: ReviewState) -> bool:
    return get_queue_bucket(review_state) == "learning"


def is_review_card(review_state: ReviewState) -> bool:
    return get_queue_bucket(review_state) == "review"


def get_queue_priority(review_state: ReviewState) -> int:
    """
    Lower number = higher priority.

    Current priority:
        0 -> learning / relearning
        1 -> review
        2 -> new

    This is the current temporary priority rule for next-card selection.
    """
    bucket = get_queue_bucket(review_state)

    if bucket == "learning":
        return 0
    if bucket == "review":
        return 1
    return 2