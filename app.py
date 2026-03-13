"""
app.py

Flask application entrypoint.

Creates the Flask app instance, registers all blueprints, and
sets configuration (secret key, template/static paths).

Run directly with `python app.py` for development, or use
`run_demo.py` for a full wipe-and-seed demo launch.
"""

from flask import Flask, jsonify
from app.blueprints.auth import auth_bp
from app.blueprints.review import review_bp
from app.blueprints.stats import stats_bp
from app.blueprints.themes import themes_bp

app = Flask(__name__,
            template_folder="app/templates",
            static_folder="app/static")

app.secret_key = 'dev-secret-key-change-in-production'  # Required for sessions/flash

app.register_blueprint(auth_bp)
app.register_blueprint(review_bp, url_prefix='/review')
app.register_blueprint(stats_bp, url_prefix='/stats')
app.register_blueprint(themes_bp)


@app.route('/api/health')
def health():
    return jsonify({"status": "ok"})


if __name__ == '__main__':
    app.run(debug=True)
