"""
Statistics Blueprint

Handles progress and performance endpoints.
Stats are computed by stats_service; this blueprint only
requests and presents them.

Routes:
    GET /stats/stats — render the stats page
"""

from flask import Blueprint, render_template, request, jsonify

stats_bp = Blueprint('stats', __name__, template_folder='templates')


@stats_bp.route('/stats', methods=['GET'])
def stats():
    """Render the stats page."""
    return render_template('stats.html')
