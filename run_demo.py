"""
run_demo.py

One-click demo launcher. Wipes and re-seeds the database every time
so you always start with a clean slate.

Usage:
    python run_demo.py
"""

import subprocess
import sys
import os
import threading
import webbrowser
import time

# Make sure we're running from the project root regardless of where
# the user calls "python run.py" from
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def install_dependencies():
    """Install packages from requirements.txt if not already installed."""
    print("Checking dependencies...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--quiet"],
        )
        print("Dependencies are installed.")
    except subprocess.CalledProcessError:
        print("Warning: Could not install some dependencies. The app may not work correctly.")


def setup_database():
    """Create tables and seed default data. Deletes any existing DB to start fresh."""
    db_path = os.path.join("data", "app.db")

    if os.path.exists(db_path):
        os.remove(db_path)
        print("Removed old database.")

    os.makedirs("data", exist_ok=True)
    from app.db import init_db
    init_db()

    print("Seeding default data...")
    from scripts.seed_db import seed_default_user, seed_vocab, seed_review_states, seed_generated_cards
    seed_default_user()
    seed_vocab()
    seed_review_states()
    seed_generated_cards()
    print("Database seeded.")


def open_browser():
    """Wait for the server to start, then open the browser."""
    time.sleep(1.5)
    webbrowser.open("http://127.0.0.1:5000")


def start_app():
    """Start the Flask development server."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("app_module", os.path.join(os.path.dirname(__file__), "app.py"))
    app_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app_module)
    flask_app = app_module.app

    print("\nStarting app at http://127.0.0.1:5000")
    print("Press Ctrl+C to stop.\n")
    flask_app.run(debug=False, port=5000)


if __name__ == "__main__":
    install_dependencies()
    setup_database()

    # Open the browser in a background thread so it doesn't block the server
    threading.Thread(target=open_browser, daemon=True).start()

    start_app()
