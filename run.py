"""
run.py

Standard launcher. Preserves the existing database across runs.

If no database exists yet, creates one and seeds it with default data.
If a database already exists, starts the app without modifying it.

Usage:
    python run.py
"""

import os
import subprocess
import sys
import threading
import time
import webbrowser

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
    """Create tables and seed default data only if the database does not exist."""
    db_path = os.path.join("data", "app.db")

    os.makedirs("data", exist_ok=True)
    from app.db import init_db
    init_db()

    if os.path.getsize(db_path) == 0 or not _has_users():
        print("No existing data found. Seeding default data...")
        from scripts.seed_db import seed_default_user, seed_vocab, seed_review_states

        seed_default_user()
        seed_vocab()
        seed_review_states()
        print("Database seeded.")
    else:
        print("Existing database found. Skipping seed.")


def _has_users():
    """Return True if the user table has at least one row."""
    try:
        from sqlmodel import select
        from app.db import get_session
        from app.models.user import User

        session = get_session()
        try:
            return session.exec(select(User)).first() is not None
        finally:
            session.close()
    except Exception:
        return False


def open_browser():
    """Wait for the server to start, then open the browser."""
    time.sleep(1.5)
    webbrowser.open("http://127.0.0.1:5000")


def start_app():
    """Start the Flask development server."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "app_module",
        os.path.join(os.path.dirname(__file__), "app.py"),
    )
    app_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app_module)
    flask_app = app_module.app

    print("\nStarting app at http://127.0.0.1:5000")
    print("Press Ctrl+C to stop.\n")
    flask_app.run(debug=False, port=5000)


if __name__ == "__main__":
    install_dependencies()
    setup_database()

    threading.Thread(target=open_browser, daemon=True).start()

    start_app()
