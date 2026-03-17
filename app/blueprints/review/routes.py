"""
Review Blueprint

Handles the interactive review experience and simulated time controls.
Card selection and scheduling are delegated to review_service.

Routes:
    GET  /review/                - load the review page with the next due card
    POST /review/rate            - process a rating and return next card + stats
    POST /review/start_sim_time  - enable simulated time at current UTC
    POST /review/adjust_sim_time - shift simulated time by a day delta
    POST /review/reset_sim_time  - disable simulated time, return to real time
    GET  /review/check_sim_time  - report whether simulated time is active
"""

from datetime import datetime, timezone, timedelta

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for

from app.services.review_service import get_next_card, process_review
from app.services.stats_service import get_session_stats


review_bp = Blueprint("review", __name__, template_folder="templates")


@review_bp.route("/", methods=["GET"])
def generate_cards():
    """Load the review page with the next due card."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.index"))

    card = get_next_card(user_id)
    stats = get_session_stats(user_id)

    return render_template(
        "review.html",
        card=card,
        stats=stats,
    )


@review_bp.route("/rate", methods=["POST"])
def rate_card():
    """Process a rating and return the next card plus updated stats."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json(force=True)
    review_state_id = data.get("review_state_id")
    rating = data.get("rating")

    if review_state_id is None or rating is None:
        return jsonify({"error": "review_state_id and rating are required"}), 400

    try:
        rating = int(rating)
        result = process_review(user_id, int(review_state_id), rating)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    next_card = get_next_card(user_id)
    stats = get_session_stats(user_id)

    return jsonify({
        "result": result,
        "next_card": next_card,
        "stats": stats,
    })


@review_bp.route("/start_sim_time", methods=["POST"])
def start_sim_time():
    """Start simulated time at the current real UTC time."""
    now = datetime.now(timezone.utc)
    session["simulated_time"] = now.isoformat()
    return jsonify({
        "active": True,
        "sim_time": now.isoformat(),
    })


@review_bp.route("/adjust_sim_time", methods=["POST"])
def adjust_sim_time():
    """Move simulated time forward or backward by a whole-number day delta."""
    data = request.get_json(force=True)
    days_delta = int(data.get("days_delta", 0))

    sim_time = session.get("simulated_time")
    if sim_time:
        new_time = datetime.fromisoformat(sim_time) + timedelta(days=days_delta)
    else:
        new_time = datetime.now(timezone.utc) + timedelta(days=days_delta)

    session["simulated_time"] = new_time.isoformat()

    return jsonify({
        "active": True,
        "sim_time": new_time.isoformat(),
    })


@review_bp.route("/reset_sim_time", methods=["POST"])
def reset_sim_time():
    """Disable simulated time and return to real time."""
    session.pop("simulated_time", None)
    return jsonify({
        "active": False,
        "sim_time": None,
    })


@review_bp.route("/check_sim_time", methods=["GET"])
def check_sim_time():
    """Return whether simulated time is currently active."""
    sim_time = session.get("simulated_time")
    return jsonify({
        "active": bool(sim_time),
        "sim_time": sim_time,
    })

@review_bp.route("/go_to_review")
def go_to_review():
    return redirect(url_for("stats.stats"))
