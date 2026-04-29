"""
stats_service.py

Computes user-facing progress metrics from ReviewLog and ReviewState data.

Current responsibilities:
- Count all rating presses today (every difficulty selection, not just the most recent per card)
- Count cards in New / Learning / Review buckets due today
- Apply the user's daily new-card cap to the remaining available New count
- Count unique cards reviewed today
- Compute current / max streak for today
- Count cards due right now
- Compute long-term progression metrics (all-time reviews, mastered cards,
  daily streaks, weekly review history, accuracy rate)
- Return per-week rating distribution for configurable time windows
- Forecast future due cards per day for the next N days
- Break down current card pool by maturity (new / learning / young / mature)
- Compute retention rates by maturity and time period

Known limitation:
    ReviewLog does not snapshot the card's interval or scheduler_state at
    the time of each review. The retention table uses the card's current
    interval to classify young vs mature, which is an approximation.
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


# Anki uses 21 days as the threshold between young and mature cards.
# Cards with interval >= 21 are considered mature (well-learned).
YOUNG_MATURE_THRESHOLD_DAYS = 21


def get_session_stats(user_id: int) -> dict:
    """
    Compute review stats for the current simulated day (UTC).

    Returns:
        A dict containing:
            - total_reviewed: number of distinct cards first reviewed today
            - counts: cumulative counts for each rating (again/hard/good/easy);
                       every rating press is counted, not just the most recent per card
            - current_streak: current streak of good/easy ratings on the first
                               review of each card today
            - max_streak: highest such streak reached today
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

            # Track first rating per card (used for accuracy calculation only)
            if review.review_state_id not in latest_ratings:
                latest_ratings[review.review_state_id] = review.rating

            # Increment the count for every rating selected so the distribution
            # bar reflects all difficulty choices, not just the last one per card
            name = rating_map.get(review.rating)
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

        weeks = []
        for bucket_start, bucket_end in week_boundaries:
            # Last calendar day of the bucket (bucket_end is exclusive midnight)
            last_day = bucket_end - timedelta(days=1)
            bucket_label = f"{_fmt_day(bucket_start)} – {_fmt_day(last_day)}"
            counts = {"again": 0, "hard": 0, "good": 0, "easy": 0}
            for log in window_logs:
                dt = as_utc(log.reviewed_at)
                if dt and bucket_start <= dt < bucket_end:
                    name = rating_map.get(log.rating)
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


def _classify_maturity(review_state: ReviewState) -> str:
    """
    Classify a ReviewState into a maturity bucket based on its current state.

    Buckets:
        new      — never reviewed (repetitions == 0)
        learning — in learning or relearning steps (scheduler_state 1 or 3)
        young    — graduated to review, interval < 21 days
        mature   — graduated to review, interval >= 21 days
    """
    if review_state.repetitions == 0:
        return "new"

    if review_state.scheduler_state in (1, 3):
        return "learning"

    if review_state.interval >= YOUNG_MATURE_THRESHOLD_DAYS:
        return "mature"

    return "young"


def get_card_type_distribution(user_id: int) -> dict:
    """
    Count cards in each maturity bucket for the card types pie chart.

    Returns:
        A dict containing:
            - new      — cards never reviewed
            - learning — cards in learning or relearning steps
            - young    — reviewed cards with interval < 21 days
            - mature   — reviewed cards with interval >= 21 days
            - total    — sum of all buckets
    """
    db_session = get_session()
    try:
        all_states = db_session.exec(
            select(ReviewState).where(ReviewState.user_id == user_id)
        ).all()

        counts = {"new": 0, "learning": 0, "young": 0, "mature": 0}

        for rs in all_states:
            bucket = _classify_maturity(rs)
            counts[bucket] += 1

        counts["total"] = sum(counts.values())
        return counts
    finally:
        db_session.close()


def get_future_due_forecast(user_id: int, days: int = 30) -> dict:
    """
    For each of the next N days, count how many cards will be due.

    Also counts the backlog — cards already overdue before today.

    Returns:
        A dict containing:
            - backlog        — number of cards due before today
            - daily_forecast — list of dicts, one per day, each with
                               "date" (ISO string) and "count" (int)
            - total          — backlog + sum of all forecasted counts
            - avg_per_day    — average daily due count over the forecast window
            - due_tomorrow   — count for tomorrow specifically
    """
    db_session = get_session()
    try:
        now = get_simulated_now()
        today_start, _ = get_today_window(now)
        today_date = today_start.date()

        all_states = db_session.exec(
            select(ReviewState).where(ReviewState.user_id == user_id)
        ).all()

        backlog = 0
        day_counts: dict[str, int] = {}

        for rs in all_states:
            due = as_utc(rs.due_date)
            if due is None:
                continue

            due_date = due.date()

            if due_date < today_date:
                backlog += 1
            elif due_date <= today_date + timedelta(days=days):
                key = due_date.isoformat()
                day_counts[key] = day_counts.get(key, 0) + 1

        daily_forecast = []
        for offset in range(days + 1):
            forecast_date = today_date + timedelta(days=offset)
            key = forecast_date.isoformat()
            daily_forecast.append({
                "date": key,
                "count": day_counts.get(key, 0),
            })

        forecast_total = sum(d["count"] for d in daily_forecast)
        total = backlog + forecast_total
        avg_per_day = round(forecast_total / max(days, 1), 1)

        tomorrow_date = (today_date + timedelta(days=1)).isoformat()
        due_tomorrow = day_counts.get(tomorrow_date, 0)

        return {
            "backlog": backlog,
            "daily_forecast": daily_forecast,
            "total": total,
            "avg_per_day": avg_per_day,
            "due_tomorrow": due_tomorrow,
        }
    finally:
        db_session.close()


def get_retention_stats(user_id: int) -> dict:
    """
    Pass rate of reviewed cards, broken down by maturity and time period.

    A "pass" is a rating of Good (3) or Easy (4). Only reviews of cards
    that currently have interval >= 1 day are included, matching Anki's
    retention table behavior.

    Uses the card's current interval to classify as young (< 21 days) or
    mature (>= 21 days). This is an approximation — the card's interval
    at the time of the review may have been different.

    Returns a dict with a key for each time period (today, yesterday,
    last_week, last_month). Each period contains:
        - young  — pass rate percentage for young cards, or None if no data
        - mature — pass rate percentage for mature cards, or None if no data
        - total  — pass rate percentage across both, or None if no data
        - count  — total number of reviews in this period for eligible cards
    """
    db_session = get_session()
    try:
        now = get_simulated_now()
        today_start, tomorrow_start = get_today_window(now)

        all_states = db_session.exec(
            select(ReviewState).where(ReviewState.user_id == user_id)
        ).all()

        # Only include cards that have graduated to review (interval >= 1)
        eligible_state_ids = set()
        state_maturity: dict[int, str] = {}
        for rs in all_states:
            if rs.interval is not None and rs.interval >= 1 and rs.id is not None:
                eligible_state_ids.add(rs.id)
                if rs.interval >= YOUNG_MATURE_THRESHOLD_DAYS:
                    state_maturity[rs.id] = "mature"
                else:
                    state_maturity[rs.id] = "young"

        all_logs = db_session.exec(
            select(ReviewLog)
            .where(ReviewLog.user_id == user_id)
            .order_by(col(ReviewLog.reviewed_at).asc())
        ).all()

        eligible_logs = [
            log for log in all_logs
            if log.review_state_id in eligible_state_ids
        ]

        periods = {
            "today": (today_start, tomorrow_start),
            "yesterday": (today_start - timedelta(days=1), today_start),
            "last_week": (today_start - timedelta(days=7), tomorrow_start),
            "last_month": (today_start - timedelta(days=30), tomorrow_start),
        }

        results = {}

        for period_name, (start, end) in periods.items():
            young_pass = 0
            young_total = 0
            mature_pass = 0
            mature_total = 0

            for log in eligible_logs:
                reviewed_at = as_utc(log.reviewed_at)
                if reviewed_at is None:
                    continue
                if not (start <= reviewed_at < end):
                    continue

                maturity = state_maturity.get(log.review_state_id)
                if maturity is None:
                    continue

                is_pass = log.rating in (3, 4)

                if maturity == "young":
                    young_total += 1
                    if is_pass:
                        young_pass += 1
                else:
                    mature_total += 1
                    if is_pass:
                        mature_pass += 1

            combined_total = young_total + mature_total
            combined_pass = young_pass + mature_pass

            results[period_name] = {
                "young": round(young_pass / young_total * 100) if young_total > 0 else None,
                "mature": round(mature_pass / mature_total * 100) if mature_total > 0 else None,
                "total": round(combined_pass / combined_total * 100) if combined_total > 0 else None,
                "count": combined_total,
            }

        return results
    finally:
        db_session.close()
