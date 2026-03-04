from flask import Flask, render_template, request, jsonify
from app.blueprints.login.auth import auth_bp   # Import the authentication blueprint
from app.blueprints.review.review import review_bp # Import the review blueprint
from app.blueprints.stats.stats import stats_bp # Import the stats blueprint
from app.blueprints.base.api import api_bp # Import the API blueprint

# from core_logic import AnkiGenerator # Assuming this is your main class/function

app = Flask(__name__,
            template_folder="app/templates",
            static_folder="app/static")

app.register_blueprint(auth_bp)  # Register the authentication blueprint
app.register_blueprint(review_bp, url_prefix='/review') # Register the review blueprint
app.register_blueprint(stats_bp, url_prefix='/stats') # Register the stats blueprint
app.register_blueprint(api_bp) # Register the API blueprint

if __name__ == '__main__':
    app.run(debug=True)