from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from database import db
from middleware.role_guard import role_required
from models import User
from utils.helpers import api_error, current_user
from utils.validators import ROLES, password_strength_errors


users_bp = Blueprint("users", __name__)


@users_bp.get("/users")
@role_required("Admin")
def get_users():
    return jsonify([user.to_dict() for user in User.query.order_by(User.created_at.desc()).all()])


@users_bp.get("/users/options")
@jwt_required()
def user_options():
    return jsonify([user.to_dict() for user in User.query.order_by(User.name.asc()).all()])


@users_bp.put("/users/<int:user_id>")
@role_required("Admin")
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json() or {}
    if "name" in data and data["name"].strip():
        user.name = data["name"].strip()
    if "role" in data:
        if data["role"] not in ROLES:
            return api_error("Invalid role.")
        user.role = data["role"]
    db.session.commit()
    return jsonify(user.to_dict())


@users_bp.put("/profile")
@jwt_required()
def update_profile():
    user = current_user()
    data = request.get_json() or {}
    if "name" in data and data["name"].strip():
        user.name = data["name"].strip()
    if data.get("password"):
        strength_errors = password_strength_errors(data["password"])
        if strength_errors:
            return api_error(f"Password must include {', '.join(strength_errors)}.")
        user.set_password(data["password"])
    db.session.commit()
    return jsonify(user.to_dict())
