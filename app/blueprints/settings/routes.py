"""
Themes Blueprint

Serves theme data so the frontend can switch color schemes.

Routes:
    GET  /api/themes       - list all available themes
    GET  /api/theme/<id>   - get a single theme object (name + class)
    POST /api/save-theme   - acknowledge a theme choice (no DB persistence yet)

Theme definitions live in themes.json next to this file.
"""

from datetime import datetime, timezone, timedelta
import json
import os
from flask import Blueprint, request, jsonify, session

from app.services.queue_service import invalidate_static_daily_queue
from app.services.settings_service import update_daily_new_limit

settings_bp = Blueprint('themes', __name__)

# Load theme definitions once at import time from the adjacent JSON file.
_themes_path = os.path.join(os.path.dirname(__file__), 'themes.json')
with open(_themes_path, 'r', encoding='utf-8') as f:
    themes = json.load(f)

DEFAULT_THEME = 'light'


@settings_bp.route('/themes', methods=['GET'])
def get_themes():
    """Return a list of all available themes (id + display name)."""
    theme_list = [
        {'id': key, 'name': data['name']}
        for key, data in themes.items()
    ]
    return jsonify(theme_list)


@settings_bp.route('/theme/<theme_id>', methods=['GET'])
def get_theme(theme_id):
    """Return a single theme's data by ID, or 404 if not found."""
    if theme_id in themes:
        return jsonify(themes[theme_id])
    return jsonify({'error': 'Theme not found'}), 404


@settings_bp.route('/save-theme', methods=['POST'])
def save_theme():
    """Acknowledge a theme selection. Validates the ID but does not persist to DB."""
    data = request.json
    theme_id = data.get('theme_id')
    if theme_id in themes:
        return jsonify({'success': True, 'theme': theme_id})
    return jsonify({'success': False, 'error': 'Invalid theme'}), 400


@settings_bp.route("/set_daily_new_limit", methods=["POST"])
def set_daily_new_limit():
    """Persist a user's daily new-card limit and return refreshed page state."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json(force=True)
    raw_limit = data.get("daily_new_limit")

    if raw_limit is None:
        return jsonify({"error": "daily_new_limit is required"}), 400

    try:
        settings = update_daily_new_limit(user_id, int(raw_limit))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    invalidate_static_daily_queue(user_id)

    return jsonify({
        "ok": True,
        "daily_new_limit": settings.daily_new_limit,
    })


@settings_bp.route("/start_sim_time", methods=["POST"])
def start_sim_time():
    """Start simulated time at the current real UTC time."""
    user_id = session.get("user_id")
    now = datetime.now(timezone.utc)
    session["simulated_time"] = now.isoformat()

    if user_id:
        invalidate_static_daily_queue(user_id)

    return jsonify({
        "active": True,
        "sim_time": now.isoformat(),
    })


@settings_bp.route("/adjust_sim_time", methods=["POST"])
def adjust_sim_time():
    """Move simulated time forward or backward by a whole-number day delta."""
    user_id = session.get("user_id")
    data = request.get_json(force=True)
    days_delta = int(data.get("days_delta", 0))

    sim_time = session.get("simulated_time")
    if sim_time:
        new_time = datetime.fromisoformat(sim_time) + timedelta(days=days_delta)
    else:
        new_time = datetime.now(timezone.utc) + timedelta(days=days_delta)

    session["simulated_time"] = new_time.isoformat()

    if user_id:
        invalidate_static_daily_queue(user_id)

    return jsonify({
        "active": True,
        "sim_time": new_time.isoformat(),
    })


@settings_bp.route("/reset_sim_time", methods=["POST"])
def reset_sim_time():
    """Disable simulated time and return to real time."""
    user_id = session.get("user_id")
    session.pop("simulated_time", None)

    if user_id:
        invalidate_static_daily_queue(user_id)

    return jsonify({
        "active": False,
        "sim_time": None,
    })


@settings_bp.route("/check_sim_time", methods=["GET"])
def check_sim_time():
    """Return whether simulated time is currently active."""
    sim_time = session.get("simulated_time")
    return jsonify({
        "active": bool(sim_time),
        "sim_time": sim_time,
    })