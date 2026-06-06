from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from database import db
from middleware.role_guard import role_required
from models import Project, ProjectMember, User
from utils.helpers import api_error, current_user
from utils.validators import require_fields


projects_bp = Blueprint("projects", __name__)


def visible_projects(user):
    if user.role == "Admin":
        return Project.query.order_by(Project.created_at.desc()).all()
    project_ids = [membership.project_id for membership in user.memberships]
    return Project.query.filter(Project.id.in_(project_ids)).order_by(Project.created_at.desc()).all()


@projects_bp.get("/projects")
@jwt_required()
def get_projects():
    user = current_user()
    projects = visible_projects(user)
    return jsonify([project.to_dict(include_members=True) for project in projects])


@projects_bp.get("/projects/<int:project_id>")
@jwt_required()
def get_project(project_id):
    user = current_user()
    project = Project.query.get_or_404(project_id)
    if user.role != "Admin" and not ProjectMember.query.filter_by(project_id=project_id, user_id=user.id).first():
        return api_error("Project not found.", 404)
    return jsonify(project.to_dict(include_members=True, include_tasks=True))


@projects_bp.post("/projects")
@role_required("Admin")
def create_project():
    data = request.get_json() or {}
    error = require_fields(data, ["title"])
    if error:
        return api_error(error)
    project = Project(
        title=data["title"].strip(),
        description=(data.get("description") or "").strip(),
        created_by=current_user().id,
    )
    db.session.add(project)
    db.session.flush()
    db.session.add(ProjectMember(project_id=project.id, user_id=current_user().id))
    for user_id in data.get("members", []):
        if User.query.get(user_id) and user_id != current_user().id:
            db.session.add(ProjectMember(project_id=project.id, user_id=user_id))
    db.session.commit()
    return jsonify(project.to_dict(include_members=True)), 201


@projects_bp.put("/projects/<int:project_id>")
@role_required("Admin")
def update_project(project_id):
    project = Project.query.get_or_404(project_id)
    data = request.get_json() or {}
    if "title" in data and data["title"].strip():
        project.title = data["title"].strip()
    if "description" in data:
        project.description = data["description"].strip()
    db.session.commit()
    return jsonify(project.to_dict(include_members=True))


@projects_bp.delete("/projects/<int:project_id>")
@role_required("Admin")
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    db.session.delete(project)
    db.session.commit()
    return jsonify({"message": "Project deleted"})


@projects_bp.post("/projects/<int:project_id>/members")
@role_required("Admin")
def add_member(project_id):
    Project.query.get_or_404(project_id)
    data = request.get_json() or {}
    user_id = data.get("user_id")
    if not User.query.get(user_id):
        return api_error("User not found.", 404)
    if ProjectMember.query.filter_by(project_id=project_id, user_id=user_id).first():
        return api_error("User is already a project member.", 409)
    db.session.add(ProjectMember(project_id=project_id, user_id=user_id))
    db.session.commit()
    return jsonify({"message": "Member added"})


@projects_bp.delete("/projects/<int:project_id>/members/<int:user_id>")
@role_required("Admin")
def remove_member(project_id, user_id):
    membership = ProjectMember.query.filter_by(project_id=project_id, user_id=user_id).first_or_404()
    db.session.delete(membership)
    db.session.commit()
    return jsonify({"message": "Member removed"})
