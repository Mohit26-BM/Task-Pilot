from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from database import db
from middleware.role_guard import role_required
from models import Project, ProjectMember, Task, User
from routes.projects import ensure_member
from utils.helpers import api_error, current_user, json_body
from utils.validators import (
    TASK_PRIORITIES,
    TASK_STATUSES,
    TASK_TYPES,
    as_id,
    clean_text,
    like_escape,
    parse_date,
)


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
    status = request.args.get("status")
    priority = request.args.get("priority")
    project_id = request.args.get("project_id")
    search = request.args.get("search")
    query = scoped_tasks(current_user())
    if status:
        query = query.filter_by(status=status)
    if priority:
        query = query.filter_by(priority=priority)
    if project_id:
        pid = as_id(project_id)
        if not pid:
            return api_error("project_id must be a number.")
        query = query.filter_by(project_id=pid)
    if search:
        query = query.filter(Task.title.ilike(f"%{like_escape(search[:100])}%", escape="\\"))
    return jsonify([task.to_dict() for task in query.all()])


@tasks_bp.post("/tasks")
@role_required("Admin")
def create_task():
    data = json_body()
    title, error = clean_text(data.get("title"), "Title", 180)
    if error:
        return api_error(error)
    description, error = clean_text(data.get("description"), "Description", 5000, required=False)
    if error:
        return api_error(error)
    due_date, error = parse_date(data.get("due_date"))
    if error:
        return api_error(error)

    project_id = as_id(data.get("project_id"))
    if not project_id:
        return api_error("Missing required field(s): project_id")
    if not db.session.get(Project, project_id):
        return api_error("Project not found.", 404)

    assignee_id = None
    if data.get("assigned_to"):
        assignee_id = as_id(data["assigned_to"])
        if not assignee_id or not db.session.get(User, assignee_id):
            return api_error("Assignee not found.", 404)

    task = Task(
        title=title,
        description=description,
        status=data["status"] if data.get("status") in TASK_STATUSES else "Pending",
        priority=data["priority"] if data.get("priority") in TASK_PRIORITIES else "Medium",
        due_date=due_date,
        assigned_to=assignee_id,
        project_id=project_id,
        task_type=data["task_type"] if data.get("task_type") in TASK_TYPES else "Feature",
    )
    if task.status == "Completed":
        task.completed_at = datetime.utcnow()
    db.session.add(task)
    if assignee_id:
        ensure_member(project_id, assignee_id)  # whoever gets a task is part of its project, so they can see it
    db.session.commit()
    return jsonify(task.to_dict()), 201


@tasks_bp.put("/tasks/<int:task_id>")
@jwt_required()
def update_task(task_id):
    user = current_user()
    task = db.get_or_404(Task, task_id)
    data = json_body()

    if user.role == "Member":
        can_touch = task.assigned_to == user.id or ProjectMember.query.filter_by(project_id=task.project_id, user_id=user.id).first()
        if not can_touch:
            return api_error("Task not found.", 404)
        if set(data.keys()) - {"status"}:
            return api_error("Members can only update task status.", 403)

    if "status" in data and data["status"] not in TASK_STATUSES:
        return api_error("Invalid task status.")

    if user.role == "Admin":
        # Check everything an Admin sent before changing anything, so a bad field cannot leave half an edit behind.
        if "title" in data:
            title, error = clean_text(data["title"], "Title", 180)
            if error:
                return api_error(error)
            task.title = title
        if "description" in data:
            description, error = clean_text(data["description"], "Description", 5000, required=False)
            if error:
                return api_error(error)
            task.description = description
        due_date = None
        if "due_date" in data:
            due_date, error = parse_date(data.get("due_date"))
            if error:
                db.session.rollback()
                return api_error(error)
            task.due_date = due_date
        if "project_id" in data:
            new_project = as_id(data["project_id"])
            if not new_project or not db.session.get(Project, new_project):
                db.session.rollback()
                return api_error("Project not found.", 404)
            task.project_id = new_project
        if "assigned_to" in data:
            if data["assigned_to"]:
                assignee_id = as_id(data["assigned_to"])
                if not assignee_id or not db.session.get(User, assignee_id):
                    db.session.rollback()
                    return api_error("Assignee not found.", 404)
                task.assigned_to = assignee_id
            else:
                task.assigned_to = None
        if "priority" in data and data["priority"] in TASK_PRIORITIES:
            task.priority = data["priority"]
        if "task_type" in data and data["task_type"] in TASK_TYPES:
            task.task_type = data["task_type"]
        # An assigned person is always a member of the task's project (also after the task moves to another project)
        if task.assigned_to:
            ensure_member(task.project_id, task.assigned_to)

    if "status" in data:
        task.status = data["status"]
        if task.status == "Completed":
            task.completed_at = task.completed_at or datetime.utcnow()
        else:
            task.completed_at = None

    db.session.commit()
    return jsonify(task.to_dict())


@tasks_bp.delete("/tasks/<int:task_id>")
@role_required("Admin")
def delete_task(task_id):
    task = db.get_or_404(Task, task_id)
    db.session.delete(task)
    db.session.commit()
    return jsonify({"message": "Task deleted"})
