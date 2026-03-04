from flask import Blueprint, jsonify

api_bp = Blueprint("api_bp", __name__)

@api_bp.get("/api/health")
def health():
    return jsonify({"status": "ok"})