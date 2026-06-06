from datetime import datetime

from database import db


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    tasks = db.relationship("Task", backref="project", cascade="all, delete-orphan", lazy=True)
    members = db.relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")

    def to_dict(self, include_members=False, include_tasks=False):
        completed = sum(1 for t in self.tasks if t.status == "Completed")
        data = {
            "id": self.id,
            "title": self.title,
            "description": self.description or "",
            "created_by": self.created_by,
            "creator_name": self.creator.name if self.creator else None,
            "created_at": self.created_at.isoformat(),
            "task_count": len(self.tasks),
            "completed_task_count": completed,
            "member_count": len(self.members),
        }
        if include_members:
            data["members"] = [membership.user.to_dict() for membership in self.members if membership.user]
        if include_tasks:
            data["tasks"] = [task.to_dict() for task in self.tasks]
        return data
