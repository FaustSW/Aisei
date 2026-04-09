"""
Statistics Blueprint

Handles the stats page route.

Routes:
    GET /stats/         - render the stats page (requires login)
    GET /stats/history  - return per-period rating distribution data (JSON)
"""

from flask import Blueprint, render_template, redirect, url_for, session, request, jsonify

from app.services.stats_service import get_session_stats, get_long_term_stats, get_period_stats

stats_bp = Blueprint('stats', __name__, template_folder='templates')


@stats_bp.route('/', methods=['GET'])
def stats():
    """Render the stats page. Requires an active login session."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("auth.index"))

    session_stats = get_session_stats(user_id)
    long_term = get_long_term_stats(user_id)

    return render_template(
        "stats.html",
        stats=session_stats,
        long_term=long_term,
    )


@stats_bp.route('/history', methods=['GET'])
def history():
    """Return per-week rating distribution for a given time period (JSON)."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    period = request.args.get("period", "1m")
    if period not in ("1m", "3m", "all"):
        return jsonify({"error": "Invalid period"}), 400

    data = get_period_stats(user_id, period)
    return jsonify(data)
