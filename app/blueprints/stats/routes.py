"""
Statistics Blueprint

Handles the stats page route.

Current behavior:
- Renders the stats template placeholder.

Future behavior:
- Will request computed metrics from stats_service and present them.

Routes:
    GET /stats/stats - render the stats page
"""

from flask import Blueprint, render_template

stats_bp = Blueprint('stats', __name__, template_folder='templates')


@stats_bp.route('/stats', methods=['GET'])
def stats():
    """Render the stats page."""
    return render_template('stats.html')
