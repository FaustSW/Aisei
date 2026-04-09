"""
stats_service.py

Computes user-facing progress metrics from ReviewLog and ReviewState data.

Current responsibilities:
- Count first ratings selected today per card (not every re-review)
- Count cards in New / Learning / Review buckets due today
- Apply the user's daily new-card cap to the remaining available New count
- Count unique cards reviewed today
- Compute current / max streak for today
- Count cards due right now
- Compute long-term progression metrics (all-time reviews, mastered cards,
  daily streaks, weekly review history, accuracy rate)
"""

from __future__ import annotations

from datetime import timedelta, date

from sqlmodel import select, col

from app.db import get_session
from app.models.review_log import ReviewLog
from app.models.review_state import ReviewState
from app.services.queue_service import (
    as_utc,
    cap_new_cards_for_today,
    count_introduced_new_cards_today,
    get_queue_bucket,
    get_simulated_now,
    get_today_review_counts_by_state,
    get_today_window,
)
from app.services.settings_service import get_daily_new_limit


def get_session_stats(user_id: int) -> dict:
    """
    Compute review stats for the current simulated day (UTC).

    Returns:
        A dict containing:
            - total_reviewed: number of distinct cards first reviewed today
            - counts: first-rating counts for again / hard / good / easy
            - current_streak: current streak of first-review good/easy ratings
            - max_streak: highest first-review good/easy streak reached today
            - cards_due: number of cards due right now
            - new_cards: remaining new cards available today after applying the daily cap
            - learning_cards: learning cards due today
            - review_cards: review cards due today
            - daily_new_limit: user's configured daily new-card limit
    """
    db_session = get_session()
    try:
        now = get_simulated_now()
        today_start, tomorrow_start = get_today_window(now)
        daily_new_limit = get_daily_new_limit(user_id, db_session=db_session)

        all_states = db_session.exec(
            select(ReviewState).where(ReviewState.user_id == user_id)
        ).all()

        due_today_states = []
        cards_due = 0

        for rs in all_states:
            due = as_utc(rs.due_date)
            if due is None:
                continue

            if due < tomorrow_start:
                due_today_states.append(rs)

            if due <= now:
                cards_due += 1

        today_review_counts = get_today_review_counts_by_state(
            db_session=db_session,
            user_id=user_id,
            today_start=today_start,
            today_end=tomorrow_start,
        )
        introduced_today_count = count_introduced_new_cards_today(
            all_states=all_states,
            today_review_counts=today_review_counts,
        )
        remaining_new_slots = max(0, daily_new_limit - introduced_today_count)

        new_cards = [rs for rs in due_today_states if get_queue_bucket(rs) == "new"]
        learning_cards = [rs for rs in due_today_states if get_queue_bucket(rs) == "learning"]
        review_cards = [rs for rs in due_today_states if get_queue_bucket(rs) == "review"]

        available_new_cards = cap_new_cards_for_today(
            db_session=db_session,
            new_cards=new_cards,
            remaining_new_slots=remaining_new_slots,
        )

        reviews = db_session.exec(
            select(ReviewLog)
            .where(ReviewLog.user_id == user_id)
            .where(col(ReviewLog.reviewed_at) >= today_start)
            .where(col(ReviewLog.reviewed_at) < tomorrow_start)
            .order_by(col(ReviewLog.reviewed_at).asc())
        ).all()

        counts = {"again": 0, "hard": 0, "good": 0, "easy": 0}
        rating_map = {1: "again", 2: "hard", 3: "good", 4: "easy"}

        current_streak = 0
        max_streak = 0
        seen_review_state_ids = set()
        latest_ratings: dict[int, int] = {}

        for review in reviews:
            is_first_review_today = review.review_state_id not in seen_review_state_ids
            if is_first_review_today:
                seen_review_state_ids.add(review.review_state_id)

                if review.rating in (3, 4):
                    current_streak += 1
                    if current_streak > max_streak:
                        max_streak = current_streak
                else:
                    current_streak = 0

            # Always overwrite so only the most recent rating per card is counted
            latest_ratings[review.review_state_id] = review.rating

        for rating in latest_ratings.values():
            name = rating_map.get(rating)
            if name:
                counts[name] += 1

        return {
            "total_reviewed": len(seen_review_state_ids),
            "counts": counts,
            "current_streak": current_streak,
            "max_streak": max_streak,
            "cards_due": cards_due,
            "new_cards": len(available_new_cards),
            "learning_cards": len(learning_cards),
            "review_cards": len(review_cards),
            "daily_new_limit": daily_new_limit,
            "today_accuracy": (
                round(
                    sum(1 for r in latest_ratings.values() if r in (3, 4))
                    / len(latest_ratings)
                    * 100
                )
                if latest_ratings
                else None
            ),
        }
    finally:
        db_session.close()


def get_long_term_stats(user_id: int) -> dict:
    
    db_session = get_session()
    try:
        now = get_simulated_now()
        today_start, tomorrow_start = get_today_window(now)

        all_logs = db_session.exec(
            select(ReviewLog)
            .where(ReviewLog.user_id == user_id)
            .order_by(col(ReviewLog.reviewed_at).asc())
        ).all()

        all_states = db_session.exec(
            select(ReviewState).where(ReviewState.user_id == user_id)
        ).all()

        total_reviews = len(all_logs)

        # Cards that have graduated into spaced-repetition Review state
        total_mastered = sum(1 for rs in all_states if rs.scheduler_state == 2)
        total_lapses = sum(rs.lapses for rs in all_states)

        # Accuracy: share of Good/Easy ratings across all review events
        if total_reviews > 0:
            good_easy_count = sum(1 for log in all_logs if log.rating in (3, 4))
            accuracy_rate = round(good_easy_count / total_reviews * 100)
        else:
            accuracy_rate = 0

        # Build a set of UTC dates that have at least one review
        review_dates: set = set()
        for log in all_logs:
            reviewed_at = as_utc(log.reviewed_at)
            if reviewed_at:
                review_dates.add(reviewed_at.date())

        # Current daily streak: consecutive days ending today (or yesterday if today has no reviews)
        today_date = today_start.date()
        current_daily_streak = 0
        check_date = today_date
        while check_date in review_dates:
            current_daily_streak += 1
            check_date -= timedelta(days=1)

        # Longest ever daily streak
        if review_dates:
            sorted_dates = sorted(review_dates)
            longest_daily_streak = 1
            run = 1
            for i in range(1, len(sorted_dates)):
                if sorted_dates[i] == sorted_dates[i - 1] + timedelta(days=1):
                    run += 1
                    if run > longest_daily_streak:
                        longest_daily_streak = run
                else:
                    run = 1
        else:
            longest_daily_streak = 0

        # Weekly review counts: 8 consecutive 7-day buckets ending at tomorrow_start
        # (so today's reviews are included in the most recent bucket)
        weekly_counts = []
        for week_offset in range(7, -1, -1):
            bucket_end = tomorrow_start - timedelta(weeks=week_offset)
            bucket_start = bucket_end - timedelta(weeks=1)
            count = sum(
                1 for log in all_logs
                if bucket_start <= as_utc(log.reviewed_at) < bucket_end
            )
            weekly_counts.append(count)

        # Average daily reviews over the last 30 days
        thirty_days_ago = today_start - timedelta(days=30)
        recent_count = sum(
            1 for log in all_logs
            if as_utc(log.reviewed_at) >= thirty_days_ago
        )
        avg_daily_30 = round(recent_count / 30, 1)

        return {
            "total_reviews": total_reviews,
            "total_mastered": total_mastered,
            "current_daily_streak": current_daily_streak,
            "longest_daily_streak": longest_daily_streak,
            "weekly_counts": weekly_counts,
            "avg_daily_30": avg_daily_30,
            "total_lapses": total_lapses,
            "accuracy_rate": accuracy_rate,
        }
    finally:
        db_session.close()


def get_period_stats(user_id: int, period: str) -> dict:
    """
    Return per-week rating distribution, avg cards/day, and session count
    for the requested time window.

    period values:
        '1m'  – last 30 days  (4 complete weeks + partial current week)
        '3m'  – last 90 days  (12 complete weeks + partial current week)
        'all' – every week since the user's first review

    Returns a dict with:
        weeks        - list of {label, again, hard, good, easy} (oldest first)
        avg_per_day  - average reviews per calendar day in the window
        sessions     - number of distinct days that had at least one review
    """
    db_session = get_session()
    try:
        now = get_simulated_now()
        today_start, tomorrow_start = get_today_window(now)

        all_logs = db_session.exec(
            select(ReviewLog)
            .where(ReviewLog.user_id == user_id)
            .order_by(col(ReviewLog.reviewed_at).asc())
        ).all()

        if not all_logs:
            return {"weeks": [], "avg_per_day": 0, "sessions": 0}

        if period == "1m":
            window_days = 30
            window_start = today_start - timedelta(days=window_days - 1)
        elif period == "3m":
            window_days = 90
            window_start = today_start - timedelta(days=window_days - 1)
        else:
            # All time – start from the day of the earliest review
            first_log_dt = as_utc(all_logs[0].reviewed_at)
            first_day_start = first_log_dt.replace(
                hour=0, minute=0, second=0, microsecond=0
            ) if first_log_dt else today_start
            window_start = first_day_start
            window_days = max((today_start - window_start).days + 1, 1)

        # Filter logs to the window
        window_logs = [
            log for log in all_logs
            if as_utc(log.reviewed_at) >= window_start
        ]

        # Snap back to the Sunday on or before window_start so every bucket
        # begins on Sunday.  Python weekday(): Mon=0 … Sun=6.
        days_since_sunday = (window_start.weekday() + 1) % 7
        first_sunday = window_start - timedelta(days=days_since_sunday)

        # Build Sunday-aligned week buckets up to (but not including) tomorrow.
        week_boundaries = []
        cursor = first_sunday
        while cursor < tomorrow_start:
            week_end = cursor + timedelta(weeks=1)
            week_boundaries.append((cursor, min(week_end, tomorrow_start)))
            cursor = week_end

        rating_map = {1: "again", 2: "hard", 3: "good", 4: "easy"}

        def _fmt_day(dt) -> str:
            """Return e.g. 'Apr 5' from a datetime."""
            return f"{dt.strftime('%b')} {dt.day}"

        # Deduplicate: keep only the last rating per (card, calendar day).
        # window_logs is ordered by reviewed_at ascending, so later entries
        # overwrite earlier ones, leaving the final outcome for each card-day.
        last_rating_per_card_day: dict[tuple, int] = {}
        for log in window_logs:
            dt = as_utc(log.reviewed_at)
            if dt:
                key = (log.review_state_id, dt.date())
                last_rating_per_card_day[key] = log.rating

        weeks = []
        for bucket_start, bucket_end in week_boundaries:
            # Last calendar day of the bucket (bucket_end is exclusive midnight)
            last_day = bucket_end - timedelta(days=1)
            bucket_label = f"{_fmt_day(bucket_start)} – {_fmt_day(last_day)}"
            bucket_start_date = bucket_start.date()
            bucket_end_date = bucket_end.date()
            counts = {"again": 0, "hard": 0, "good": 0, "easy": 0}
            for (rs_id, log_date), rating in last_rating_per_card_day.items():
                if bucket_start_date <= log_date < bucket_end_date:
                    name = rating_map.get(rating)
                    if name:
                        counts[name] += 1
            weeks.append({"label": bucket_label, **counts})

        # Sessions = distinct calendar days within window that had a review
        review_dates: set[date] = set()
        for log in window_logs:
            dt = as_utc(log.reviewed_at)
            if dt:
                review_dates.add(dt.date())
        sessions = len(review_dates)

        total_in_window = sum(
            w["again"] + w["hard"] + w["good"] + w["easy"] for w in weeks
        )
        avg_per_day = round(total_in_window / window_days, 1)

        return {
            "weeks": weeks,
            "avg_per_day": avg_per_day,
            "sessions": sessions,
        }
    finally:
        db_session.close()
