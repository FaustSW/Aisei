"""
Authentication Blueprint

Handles user authentication and profile management endpoints.
All business logic is delegated to auth_service.

Routes:
    GET  /             - render login page with profiles from DB
    POST /login        - authenticate user, set session
    POST /create_user  - create new user, seed review states, return profile
    POST /delete_user  - remove user and all user-owned review data
    GET  /go_to_review - redirect to review page (requires session)
    GET  /logout       - clear session, redirect to login
"""
import json, keyring

from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify

from app.services.auth_service import (
    authenticate_user,
    create_user as create_user_account,
    delete_user as delete_user_account,
    get_profiles_list,
)


APP_ID = "SeniorCapstone_Anki"
auth_bp = Blueprint("auth", __name__, template_folder="templates")


@auth_bp.route("/")
def index():
    session.clear()  # Clear any existing session on landing at the login page
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

    elevenlabs_key = keyring.get_password(APP_ID, f"{user.username}_elevenlabs")
    openai_key = keyring.get_password(APP_ID, f"{user.username}_openai")

    # We only consider "has_keys" True if both are present
    has_keys = bool(elevenlabs_key and openai_key)

    return jsonify({
        "ok": True, 
        "user_id": user.id, 
        "username": user.username,
        "has_keys": has_keys  
    })

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
    """Remove a user and all user-owned review data."""
    data = request.get_json(force=True)
    user_id = data.get("user_id")

    if user_id is None:
        return jsonify({"error": "user_id is required"}), 400

    try:
        delete_user_account(int(user_id))
    except ValueError as e:
        return jsonify({"error": str(e)}), 404

    return jsonify({"ok": True})

@auth_bp.route("/save_api_keys", methods=["POST"])
def save_api_keys():
    data = request.get_json(force=True)
    openai = data.get("openai_key", "").strip()
    eleven = data.get("elevenlabs_key", "").strip()
    
    username = session.get("user")
    
    try:
        # Only save if the string isn't empty
        if openai:
            keyring.set_password(APP_ID, f"{username}_openai", openai)
        if eleven:
            keyring.set_password(APP_ID, f"{username}_elevenlabs", eleven)
            
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@auth_bp.route("/go_to_review")
def go_to_review():
    if "user_id" not in session:
        return redirect(url_for("auth.index"))
    return redirect(url_for("review.generate_cards"))


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.index"))