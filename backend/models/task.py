from datetime import date, datetime

from database import db


class Task(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(40), nullable=False, default="Pending")
    priority = db.Column(db.String(40), nullable=False, default="Medium")
    due_date = db.Column(db.Date, nullable=True)
    assigned_to = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)
    task_type = db.Column(db.String(40), nullable=False, default="Feature")
    completed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        is_overdue = bool(self.due_date and self.due_date < date.today() and self.status != "Completed")
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description or "",
            "status": self.status,
            "priority": self.priority,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "assigned_to": self.assigned_to,
            "assignee_name": self.assignee.name if self.assignee else "Unassigned",
            "project_id": self.project_id,
            "project_title": self.project.title if self.project else None,
            "task_type": self.task_type,
            "is_overdue": is_overdue,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat(),
        }
