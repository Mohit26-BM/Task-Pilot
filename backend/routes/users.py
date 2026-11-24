from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from database import db
from middleware.role_guard import role_required
from models import ProjectMember, User
from utils.helpers import api_error, current_user, json_body
from utils.validators import ROLES, clean_text, password_strength_errors


users_bp = Blueprint("users", __name__)


@users_bp.get("/users")
@role_required("Admin")
def get_users():
    return jsonify([user.to_dict() for user in User.query.order_by(User.created_at.desc()).all()])


@users_bp.get("/users/options")
@jwt_required()
def user_options():
    """People that can be picked in a dropdown: just id and name. Admins see everyone; a member only sees the people
    they share a project with (and themselves), not the whole user list with emails."""
    user = current_user()
    query = User.query.order_by(User.name.asc())
    if user.role != "Admin":
        project_ids = [m.project_id for m in user.memberships]
        mates = {m.user_id for m in ProjectMember.query.filter(ProjectMember.project_id.in_(project_ids)).all()} if project_ids else set()
        mates.add(user.id)
        query = query.filter(User.id.in_(mates))
    return jsonify([{"id": u.id, "name": u.name} for u in query.all()])


@users_bp.put("/users/<int:user_id>")
@role_required("Admin")
def update_user(user_id):
    user = db.get_or_404(User, user_id)
    data = json_body()
    if "name" in data:
        name, error = clean_text(data["name"], "Name", 80)
        if error:
            return api_error(error)
        user.name = name
    if "role" in data:
        if data["role"] not in ROLES:
            return api_error("Invalid role.")
        # The app must always have someone who can manage it
        if user.role == "Admin" and data["role"] != "Admin" and User.query.filter_by(role="Admin").count() <= 1:
            return api_error("There must always be at least one Admin. Make someone else an Admin first.")
        user.role = data["role"]
    db.session.commit()
    return jsonify(user.to_dict())


@users_bp.put("/profile")
@jwt_required()
def update_profile():
    user = current_user()
    data = json_body()
    if "name" in data:
        name, error = clean_text(data["name"], "Name", 80)
        if error:
            return api_error(error)
        user.name = name
    if data.get("password"):
        # Changing the password needs the current one, so a borrowed or stolen session cannot lock the owner out.
        current = data.get("current_password")
        if not isinstance(current, str) or not user.check_password(current):
            return api_error("Enter your current password to set a new one.", 403)
        strength_errors = password_strength_errors(data["password"])
        if strength_errors:
            return api_error(f"Password must include {', '.join(strength_errors)}.")
        user.set_password(data["password"])
    db.session.commit()
    return jsonify(user.to_dict())
