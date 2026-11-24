import os
import secrets
import sys
from pathlib import Path

from flask import Flask, jsonify, render_template
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config, is_production
from database import db
from models import User
from routes.auth import auth_bp
from routes.dashboard import dashboard_bp
from routes.projects import projects_bp
from routes.tasks import tasks_bp
from routes.users import users_bp


jwt = JWTManager()

# The password the app used to publish in its README and on the login page. It must never stay in use.
PUBLISHED_ADMIN_PASSWORD = "Admin@12345"
PUBLISHED_MEMBER_PASSWORD = "Member@12345"
ADMIN_EMAIL = "admin@taskpilot.dev"


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Behind a host's proxy (Render, Railway...) set TRUST_PROXY=1 so rate limits see the visitor, not the proxy.
    proxies = os.getenv("TRUST_PROXY", "")
    if proxies.isdigit() and int(proxies) > 0:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=int(proxies), x_proto=int(proxies), x_host=int(proxies))

    # The pages and the API are served by this same app, so no cross-site access is needed. CORS is only switched on
    # when CORS_ORIGINS names the sites that may call the API from elsewhere (comma separated).
    origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip() and o.strip() != "*"]
    if origins:
        CORS(app, origins=origins)

    Path(app.root_path, "database").mkdir(exist_ok=True)
    db.init_app(app)
    jwt.init_app(app)

    @jwt.user_lookup_loader
    def load_user(_header, payload):
        try:
            return db.session.get(User, int(payload["sub"]))
        except (TypeError, ValueError, KeyError):
            return None

    @jwt.user_lookup_error_loader
    def missing_user(_header, _payload):
        return jsonify({"error": "This account no longer exists. Please sign in again."}), 401

    @jwt.expired_token_loader
    def expired(_header, _payload):
        return jsonify({"error": "Your session has expired. Please sign in again."}), 401

    @jwt.invalid_token_loader
    def invalid(_reason):
        return jsonify({"error": "Please sign in again."}), 401

    @jwt.unauthorized_loader
    def unauthorized(_reason):
        return jsonify({"error": "Please sign in to continue."}), 401

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        if response.mimetype == "application/json":
            response.headers["Cache-Control"] = "no-store"
        if is_production():
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response

    @app.errorhandler(HTTPException)
    def http_error(error):
        # API clients get JSON; page requests that miss get the plain status page
        from flask import request

        if request.accept_mimetypes.best == "application/json" or request.path.startswith(("/api", "/tasks", "/projects", "/users")):
            return jsonify({"error": error.description or error.name}), error.code
        return error

    @app.errorhandler(Exception)
    def unexpected(error):
        app.logger.exception("Unhandled error")
        return jsonify({"error": "Something went wrong on our side. Please try again."}), 500

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
        demo = app.config["DEMO_MODE"]
        return render_template(
            "login.html",
            demo=demo,
            demo_email=app.config["DEMO_MEMBER_EMAIL"],
            demo_password=app.config["DEMO_MEMBER_PASSWORD"] if demo else "",
        )

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
        seed_accounts(app)

    return app


def _random_password():
    return secrets.token_urlsafe(24)


def seed_accounts(app):
    """Make sure the accounts the app needs exist, and that no account is left with a published password.

    Admin:  ADMIN_PASSWORD sets the first admin's password. Without it, development uses a fixed local password (printed
            once on first run) while production refuses to start with the old published password still in place.
    Member: the shared demo Member exists only when DEMO_MODE=1; otherwise a leftover demo account is locked
            by giving it a random password."""
    configured = os.getenv("ADMIN_PASSWORD", "")
    admin = User.query.filter_by(email=ADMIN_EMAIL).first()

    if not admin:
        if configured:
            password = configured
        elif is_production():
            print(f"[taskpilot] No admin account yet. Set ADMIN_PASSWORD to create {ADMIN_EMAIL} on the next start.", file=sys.stderr)
            password = None
        else:
            password = PUBLISHED_ADMIN_PASSWORD
            print(f"[taskpilot] Development admin created: {ADMIN_EMAIL} / {password}  (set ADMIN_PASSWORD to choose another)", file=sys.stderr)
        if password:
            admin = User(name="TaskPilot Admin", email=ADMIN_EMAIL, role="Admin")
            admin.set_password(password)
            db.session.add(admin)
    elif admin.check_password(PUBLISHED_ADMIN_PASSWORD) and is_production():
        if not configured or configured == PUBLISHED_ADMIN_PASSWORD:
            raise RuntimeError(
                f"The admin account {ADMIN_EMAIL} still uses the published default password. "
                "Set ADMIN_PASSWORD to a new strong password and restart: it will replace the old one."
            )
        admin.set_password(configured)

    member = User.query.filter_by(email=app.config["DEMO_MEMBER_EMAIL"]).first()
    if app.config["DEMO_MODE"]:
        if not member:
            member = User(name="Demo Member", email=app.config["DEMO_MEMBER_EMAIL"], role="Member")
            db.session.add(member)
        member.set_password(app.config["DEMO_MEMBER_PASSWORD"])
    elif member and member.check_password(PUBLISHED_MEMBER_PASSWORD):
        member.set_password(_random_password())

    db.session.commit()


app = create_app()


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG") == "1")
