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
from app.services.stats_service import get_session_stats

stats_bp = Blueprint('stats', __name__, template_folder='templates')


@stats_bp.route('/', methods=['GET'])
def stats():
    """Render the stats page."""

    # temporary user_id until auth session is wired
    user_id = 1

    stats_data = get_session_stats(user_id)

    return render_template(
        "stats.html",
        cards_due=stats_data["cards_due"]
    )
