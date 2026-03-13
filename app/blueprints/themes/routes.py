"""
Themes Blueprint

Serves theme data so the frontend can switch color schemes.

Routes:
    GET  /api/themes         — list all available themes
    GET  /api/theme/<id>     — get a single theme's CSS class
    POST /api/save-theme     — acknowledge a theme choice (no DB persistence yet)

Theme definitions live in themes.json next to this file.
"""

import json
import os
from flask import Blueprint, request, jsonify

themes_bp = Blueprint('themes', __name__)

# Load theme definitions once at import time from the adjacent JSON file.
_themes_path = os.path.join(os.path.dirname(__file__), 'themes.json')
with open(_themes_path, 'r') as f:
    themes = json.load(f)

DEFAULT_THEME = 'light'


@themes_bp.route('/api/themes', methods=['GET'])
def get_themes():
    """Return a list of all available themes (id + display name)."""
    theme_list = [
        {'id': key, 'name': data['name']}
        for key, data in themes.items()
    ]
    return jsonify(theme_list)


@themes_bp.route('/api/theme/<theme_id>', methods=['GET'])
def get_theme(theme_id):
    """Return a single theme's data by ID, or 404 if not found."""
    if theme_id in themes:
        return jsonify(themes[theme_id])
    return jsonify({'error': 'Theme not found'}), 404


@themes_bp.route('/api/save-theme', methods=['POST'])
def save_theme():
    """Acknowledge a theme selection. Validates the ID but does not persist to DB."""
    data = request.json
    theme_id = data.get('theme_id')
    if theme_id in themes:
        return jsonify({'success': True, 'theme': theme_id})
    return jsonify({'success': False, 'error': 'Invalid theme'}), 400
