from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from database import db
from middleware.role_guard import role_required
from models import Project, ProjectMember, Task, User
from utils.helpers import api_error, current_user, json_body
from utils.validators import as_id, clean_text


projects_bp = Blueprint("projects", __name__)


def visible_projects(user):
    if user.role == "Admin":
        return Project.query.order_by(Project.created_at.desc()).all()
    project_ids = [membership.project_id for membership in user.memberships]
    return Project.query.filter(Project.id.in_(project_ids)).order_by(Project.created_at.desc()).all()


def ensure_member(project_id, user_id):
    """Make sure this user is a member of the project (used when a task is assigned to them)."""
    if not ProjectMember.query.filter_by(project_id=project_id, user_id=user_id).first():
        db.session.add(ProjectMember(project_id=project_id, user_id=user_id))


@projects_bp.get("/projects")
@jwt_required()
def get_projects():
    projects = visible_projects(current_user())
    return jsonify([project.to_dict(include_members=True) for project in projects])


@projects_bp.get("/projects/<int:project_id>")
@jwt_required()
def get_project(project_id):
    user = current_user()
    project = db.get_or_404(Project, project_id)
    if user.role != "Admin" and not ProjectMember.query.filter_by(project_id=project_id, user_id=user.id).first():
        return api_error("Project not found.", 404)
    return jsonify(project.to_dict(include_members=True, include_tasks=True))


@projects_bp.post("/projects")
@role_required("Admin")
def create_project():
    data = json_body()
    title, error = clean_text(data.get("title"), "Title", 160)
    if error:
        return api_error(error)
    description, error = clean_text(data.get("description"), "Description", 5000, required=False)
    if error:
        return api_error(error)

    members = data.get("members", [])
    if not isinstance(members, list):
        return api_error("Members must be a list of user ids.")

    me = current_user()
    project = Project(title=title, description=description, created_by=me.id)
    db.session.add(project)
    db.session.flush()
    db.session.add(ProjectMember(project_id=project.id, user_id=me.id))
    for raw in members:
        user_id = as_id(raw)
        if user_id and user_id != me.id and db.session.get(User, user_id):
            ensure_member(project.id, user_id)
    db.session.commit()
    return jsonify(project.to_dict(include_members=True)), 201


@projects_bp.put("/projects/<int:project_id>")
@role_required("Admin")
def update_project(project_id):
    project = db.get_or_404(Project, project_id)
    data = json_body()
    if "title" in data:
        title, error = clean_text(data["title"], "Title", 160)
        if error:
            return api_error(error)
        project.title = title
    if "description" in data:
        description, error = clean_text(data["description"], "Description", 5000, required=False)
        if error:
            return api_error(error)
        project.description = description
    db.session.commit()
    return jsonify(project.to_dict(include_members=True))


@projects_bp.delete("/projects/<int:project_id>")
@role_required("Admin")
def delete_project(project_id):
    project = db.get_or_404(Project, project_id)
    db.session.delete(project)
    db.session.commit()
    return jsonify({"message": "Project deleted"})


@projects_bp.post("/projects/<int:project_id>/members")
@role_required("Admin")
def add_member(project_id):
    db.get_or_404(Project, project_id)
    user_id = as_id(json_body().get("user_id"))
    if not user_id or not db.session.get(User, user_id):
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
    # Someone who is no longer on the project should not keep tasks from it
    Task.query.filter_by(project_id=project_id, assigned_to=user_id).update({"assigned_to": None})
    db.session.commit()
    return jsonify({"message": "Member removed"})
