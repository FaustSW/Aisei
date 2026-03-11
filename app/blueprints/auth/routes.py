"""
Authentication Blueprint

Handles user authentication endpoints.

Routes:
    GET  /             — render login page with profiles from DB
    POST /login        — authenticate user, set session
    POST /create_user  — create new user in DB, seed review states
    POST /delete_user  — remove user and their data
    GET  /go_to_review — redirect to review page
"""
import json

from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from sqlmodel import select

from app.db import get_session
from app.models.user import User
from app.models.vocab import Vocab
from app.models.review_state import ReviewState
from app.services.scheduler_adapter import SchedulerAdapter

auth_bp = Blueprint('auth', __name__, template_folder='templates')
_scheduler = SchedulerAdapter()


def _get_profiles_list():
    """Load all users from DB and return as a list of dicts for the frontend."""
    db = get_session()
    try:
        users = db.exec(select(User)).all()
        return [
            {
                "id": u.id,
                "name": u.display_name,
                "username": u.username,
                "password": u.password_hash,  # plaintext for now
                "avatar": u.avatar,
                "initials": u.initials,
            }
            for u in users
        ]
    finally:
        db.close()


@auth_bp.route('/')
def index():
    profiles = _get_profiles_list()
    return render_template('login.html', profiles_json=json.dumps(profiles))


@auth_bp.route('/login', methods=['POST'])
def login():
    """Find user by username, set session."""
    data = request.get_json(force=True)
    username = data.get('username', '').strip()

    if not username:
        return jsonify({"error": "Username is required"}), 400

    db = get_session()
    try:
        user = db.exec(select(User).where(User.username == username)).first()

        if user is None:
            return jsonify({"error": "User not found"}), 404

        session['user_id'] = user.id
        session['user'] = user.username
        return jsonify({"ok": True, "user_id": user.id, "username": user.username})
    finally:
        db.close()


@auth_bp.route('/create_user', methods=['POST'])
def create_user():
    """Create a new user in the DB, seed their review states, return profile JSON."""
    data = request.get_json(force=True)
    display_name = data.get('name', '').strip()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    avatar = data.get('avatar', 'avatar-1')

    if not username or not display_name or not password:
        return jsonify({"error": "All fields are required"}), 400

    db = get_session()
    try:
        existing = db.exec(select(User).where(User.username == username)).first()
        if existing:
            return jsonify({"error": "Username already exists"}), 409

        user = User(
            username=username,
            display_name=display_name,
            password_hash=password,  # plaintext for now
            avatar=avatar,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Seed review states for the new user
        _seed_review_states(db, user.id)

        return jsonify({
            "ok": True,
            "profile": {
                "id": user.id,
                "name": user.display_name,
                "username": user.username,
                "password": user.password_hash,
                "avatar": user.avatar,
                "initials": user.initials,
            }
        })
    finally:
        db.close()


@auth_bp.route('/delete_user', methods=['POST'])
def delete_user():
    """Remove a user and all their review states."""
    data = request.get_json(force=True)
    user_id = data.get('user_id')

    if user_id is None:
        return jsonify({"error": "user_id is required"}), 400

    db = get_session()
    try:
        user = db.get(User, user_id)
        if user is None:
            return jsonify({"error": "User not found"}), 404

        # Delete review states
        states = db.exec(select(ReviewState).where(ReviewState.user_id == user_id)).all()
        for rs in states:
            db.delete(rs)

        db.delete(user)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()


@auth_bp.route('/go_to_review')
def go_to_review():
    if 'user_id' not in session:
        return redirect(url_for('auth.index'))
    return redirect(url_for('review.generate_cards'))


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.index'))


def _seed_review_states(db, user_id: int):
    """Create a ReviewState for every vocab item for this new user."""
    vocabs = db.exec(select(Vocab)).all()
    for vocab in vocabs:
        rs = ReviewState(user_id=user_id, vocab_id=vocab.id)
        _scheduler.initialize_new_card(rs)
        db.add(rs)
    db.commit()