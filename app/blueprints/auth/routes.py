# app/blueprints/auth/routes.py

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

from app.services.auth_service import (
    authenticate_user,
    create_user as create_user_account,
    delete_user as delete_user_account,
    get_profiles_list,
)

auth_bp = Blueprint("auth", __name__, template_folder="templates")


@auth_bp.route("/")
def index():
    profiles = get_profiles_list()
    return render_template("login.html", profiles_json=json.dumps(profiles))


@auth_bp.route("/login", methods=["POST"])
def login():
    """Validate credentials and set session."""
    data = request.get_json(force=True)
    username = data.get("username", "")
    password = data.get("password", "")

    try:
        user = authenticate_user(username=username, password=password)
    except ValueError as e:
        message = str(e)
        status = 404 if message == "User not found" else 400
        return jsonify({"error": message}), status

    session["user_id"] = user.id
    session["user"] = user.username
    return jsonify({"ok": True, "user_id": user.id, "username": user.username})


@auth_bp.route("/create_user", methods=["POST"])
def create_user():
    """Create a new user in the DB, seed their review states, return profile JSON."""
    data = request.get_json(force=True)

    try:
        profile = create_user_account(
            display_name=data.get("name", ""),
            username=data.get("username", ""),
            password=data.get("password", ""),
            avatar=data.get("avatar", "avatar-1"),
        )
    except ValueError as e:
        message = str(e)
        status = 409 if message == "Username already exists" else 400
        return jsonify({"error": message}), status

    return jsonify({
        "ok": True,
        "profile": profile,
    })


@auth_bp.route("/delete_user", methods=["POST"])
def delete_user():
    """Remove a user and all their review states."""
    data = request.get_json(force=True)
    user_id = data.get("user_id")

    if user_id is None:
        return jsonify({"error": "user_id is required"}), 400

    try:
        delete_user_account(int(user_id))
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

    return jsonify({"ok": True})


@auth_bp.route("/go_to_review")
def go_to_review():
    if "user_id" not in session:
        return redirect(url_for("auth.index"))
    return redirect(url_for("review.generate_cards"))


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.index"))