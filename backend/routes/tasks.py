from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from database import db
from middleware.role_guard import role_required
from models import Project, ProjectMember, Task, User
from utils.helpers import api_error, current_user
from utils.validators import TASK_PRIORITIES, TASK_STATUSES, TASK_TYPES, parse_date, require_fields


tasks_bp = Blueprint("tasks", __name__)


def scoped_tasks(user):
    query = Task.query
    if user.role == "Member":
        member_project_ids = [membership.project_id for membership in user.memberships]
        query = query.filter((Task.assigned_to == user.id) | (Task.project_id.in_(member_project_ids)))
    return query.order_by(Task.created_at.desc())


@tasks_bp.get("/tasks")
@jwt_required()
def get_tasks():
    user = current_user()
    status = request.args.get("status")
    priority = request.args.get("priority")
    project_id = request.args.get("project_id")
    search = request.args.get("search")
    query = scoped_tasks(user)
    if status:
        query = query.filter_by(status=status)
    if priority:
        query = query.filter_by(priority=priority)
    if project_id:
        query = query.filter_by(project_id=project_id)
    if search:
        query = query.filter(Task.title.ilike(f"%{search}%"))
    return jsonify([task.to_dict() for task in query.all()])


@tasks_bp.post("/tasks")
@role_required("Admin")
def create_task():
    data = request.get_json() or {}
    error = require_fields(data, ["title", "project_id"])
    if error:
        return api_error(error)
    if not Project.query.get(data["project_id"]):
        return api_error("Project not found.", 404)
    if data.get("assigned_to") and not User.query.get(data["assigned_to"]):
        return api_error("Assignee not found.", 404)

    task = Task(
        title=data["title"].strip(),
        description=(data.get("description") or "").strip(),
        status=data.get("status", "Pending") if data.get("status") in TASK_STATUSES else "Pending",
        priority=data.get("priority", "Medium") if data.get("priority") in TASK_PRIORITIES else "Medium",
        due_date=parse_date(data.get("due_date")),
        assigned_to=data.get("assigned_to") or None,
        project_id=data["project_id"],
        task_type=data.get("task_type", "Feature") if data.get("task_type") in TASK_TYPES else "Feature",
    )
    if task.status == "Completed":
        task.completed_at = datetime.utcnow()
    db.session.add(task)
    db.session.commit()
    return jsonify(task.to_dict()), 201


@tasks_bp.put("/tasks/<int:task_id>")
@jwt_required()
def update_task(task_id):
    user = current_user()
    task = Task.query.get_or_404(task_id)
    data = request.get_json() or {}

    if user.role == "Member":
        can_touch = task.assigned_to == user.id or ProjectMember.query.filter_by(project_id=task.project_id, user_id=user.id).first()
        if not can_touch:
            return api_error("Task not found.", 404)
        if set(data.keys()) - {"status"}:
            return api_error("Members can only update task status.", 403)

    for field in ["title", "description"]:
        if field in data and user.role == "Admin":
            setattr(task, field, (data[field] or "").strip())
    if "status" in data:
        if data["status"] not in TASK_STATUSES:
            return api_error("Invalid task status.")
        task.status = data["status"]
        task.completed_at = datetime.utcnow() if task.status == "Completed" and not task.completed_at else task.completed_at
        if task.status != "Completed":
            task.completed_at = None
    if user.role == "Admin":
        if "priority" in data and data["priority"] in TASK_PRIORITIES:
            task.priority = data["priority"]
        if "task_type" in data and data["task_type"] in TASK_TYPES:
            task.task_type = data["task_type"]
        if "due_date" in data:
            task.due_date = parse_date(data.get("due_date"))
        if "assigned_to" in data:
            if data["assigned_to"] and not User.query.get(data["assigned_to"]):
                return api_error("Assignee not found.", 404)
            task.assigned_to = data["assigned_to"] or None
        if "project_id" in data and Project.query.get(data["project_id"]):
            task.project_id = data["project_id"]

    db.session.commit()
    return jsonify(task.to_dict())


@tasks_bp.delete("/tasks/<int:task_id>")
@role_required("Admin")
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    return jsonify({"message": "Task deleted"})
