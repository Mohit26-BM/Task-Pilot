import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, render_template
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from config import Config
from database import db
from models import User
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.projects import projects_bp
from routes.tasks import tasks_bp
from routes.users import users_bp


load_dotenv()
jwt = JWTManager()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    origins = os.getenv("CORS_ORIGINS", "*")
    CORS(app, origins=origins)

    Path(app.root_path, "database").mkdir(exist_ok=True)
    db.init_app(app)
    jwt.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(users_bp)

    @app.route("/")
    def root():
        return render_template("landing.html")

    @app.route("/login")
    def login_page():
        return render_template("login.html",
            admin_pwd=os.getenv("ADMIN_PASSWORD", "Admin@12345"))

    @app.route("/signup")
    def signup_page():
        return render_template("signup.html")

    @app.route("/dashboard")
    def dashboard_page():
        return render_template("dashboard.html")

    @app.route("/projects-view")
    def projects_page():
        return render_template("projects.html")

    @app.route("/projects-view/<int:project_id>")
    def project_details_page(project_id):
        return render_template("project_details.html", project_id=project_id)

    @app.route("/tasks-view")
    def tasks_page():
        return render_template("tasks.html")

    @app.route("/users-view")
    def users_page():
        return render_template("users.html")

    @app.route("/profile")
    def profile_page():
        return render_template("profile.html")

    with app.app_context():
        db.create_all()
        seed_demo_accounts()

    return app


def seed_demo_accounts():
    changed = False
    if not User.query.filter_by(email="admin@taskpilot.dev").first():
        admin = User(name="TaskPilot Admin", email="admin@taskpilot.dev", role="Admin")
        admin.set_password(os.getenv("ADMIN_PASSWORD", "Admin@12345"))
        db.session.add(admin)
        changed = True
    if not User.query.filter_by(email="member@taskpilot.dev").first():
        member = User(name="Demo Member", email="member@taskpilot.dev", role="Member")
        member.set_password("Member@12345")
        db.session.add(member)
        changed = True
    if changed:
        db.session.commit()


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
