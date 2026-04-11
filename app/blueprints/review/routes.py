"""
Review Blueprint

Handles the interactive review experience and simulated time controls.
Card selection and scheduling are delegated to review_service.

Routes:
    GET  /review/                      - load the review page with the next due card
    POST /review/rate                  - process a rating and return next card + stats
    POST /review/set_daily_new_limit   - persist and apply the user's new-card limit
    POST /review/start_sim_time        - enable simulated time at current UTC
    POST /review/adjust_sim_time       - shift simulated time by a day delta
    POST /review/reset_sim_time        - disable simulated time, return to real time
    GET  /review/check_sim_time        - report whether simulated time is active
"""

from datetime import datetime, timezone, timedelta

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for

from app.services.queue_service import invalidate_static_daily_queue
from app.services.review_service import get_next_card, process_review
from app.services.settings_service import (
    get_daily_new_limit,
    update_daily_new_limit,
)
from app.services.stats_service import get_session_stats
from app.services.generation_service import (
    handle_audio_generation
)


review_bp = Blueprint("review", __name__, template_folder="templates")


@review_bp.route("/", methods=["GET"])
def generate_cards():
    """Load the review page with the next due card."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.index"))

    card = get_next_card(user_id)
    stats = get_session_stats(user_id)
    daily_new_limit = get_daily_new_limit(user_id)

    return render_template(
        "review.html",
        card=card,
        stats=stats,
        daily_new_limit=daily_new_limit,
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

# Currently testing ElevenLabs integration through a dedicated route
# This should run when the audio button in the card area is pressed
@review_bp.route("/generate_audio", methods=["POST"])
def generate_audio():
    """Receives text from JS, calls generation service, returns audio URL."""
    username = session.get("user")
    if not username:
        return jsonify({"error": "User not authenticated"}), 401

    data = request.get_json(force=True)
    text = data.get("text")
    voice_id = data.get("voice_id")

    if not text:
        return jsonify({"error": "No text provided"}), 400

    try:
        # Link to your Generation Service
        from app.services.generation_service import handle_audio_generation
        
        # This function (built in previous step) triggers the ElevenLabsClient
        audio_url = handle_audio_generation(
            username=username,
            text=text,
            voice_id=voice_id
        )

        return jsonify({
            "success": True,
            "audio_url": audio_url
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@review_bp.route("/go_to_stats", methods=["GET"])
def go_to_stats():
    return redirect(url_for("stats.stats"))
