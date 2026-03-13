"""
App Package

Top-level application package. Contains all server-side code
organized into sub-packages:

    blueprints/  - Flask route definitions (auth, review, stats, themes)
    models/      - SQLModel database schema (User, Vocab, ReviewState, etc.)
    services/    - Business logic (review loop, scheduling, queue, stats, auth)
    clients/     - Thin wrappers around external APIs (GPT, ElevenLabs)
    templates/   - Jinja2 HTML templates
    static/      - CSS, JS, and other static assets

The Flask app itself is created in app.py at the project root,
not in this __init__.py. This file just marks the directory as
a Python package so imports like `from app.models.user import User` work.
"""