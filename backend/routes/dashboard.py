from collections import Counter, defaultdict
from datetime import date

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from models import Project, Task
from routes.projects import visible_projects
from routes.tasks import scoped_tasks
from utils.helpers import current_user


dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/dashboard/stats")
@jwt_required()
def stats():
    user = current_user()
    tasks = scoped_tasks(user).all()
    projects = visible_projects(user)
    today = date.today()

    status_counts = Counter(task.status for task in tasks)
    priority_counts = Counter(task.priority for task in tasks)
    project_counts = {project.title: Task.query.filter_by(project_id=project.id).count() for project in projects}
    completed_by_day = defaultdict(int)
    for task in tasks:
        if task.completed_at:
            completed_by_day[task.completed_at.date().isoformat()] += 1

    return jsonify(
        {
            "cards": {
                "total_tasks": len(tasks),
                "completed_tasks": status_counts.get("Completed", 0),
                "pending_tasks": status_counts.get("Pending", 0),
                "overdue_tasks": sum(1 for task in tasks if task.due_date and task.due_date < today and task.status != "Completed"),
                "active_projects": len(projects),
            },
            "status_distribution": dict(status_counts),
            "priority_distribution": dict(priority_counts),
            "tasks_per_project": project_counts,
            "completed_over_time": dict(sorted(completed_by_day.items())),
            "recent_tasks": [task.to_dict() for task in tasks[:6]],
        }
    )
