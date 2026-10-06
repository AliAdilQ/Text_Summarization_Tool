"""Application factory and centralized error/security handling."""

import os
import secrets
from pathlib import Path

import click
from flask import Flask, flash, jsonify, render_template, request
from flask_login import current_user, logout_user
from flask_wtf.csrf import CSRFError

from app.extensions import csrf, db, login_manager
from app.services.summarizer import SummarizerService
from config import Config


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    if not app.config["SECRET_KEY"]:
        if app.config["ENVIRONMENT"] == "production":
            raise RuntimeError("Set SECRET_KEY before running in production.")
        secret_path = Path(app.instance_path) / ".development-secret"
        try:
            with secret_path.open("x", encoding="utf-8") as secret_file:
                secret_file.write(secrets.token_hex(32))
            os.chmod(secret_path, 0o600)
        except FileExistsError:
            pass
        app.config["SECRET_KEY"] = secret_path.read_text(encoding="utf-8").strip()
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Sign in to access your workspace."
    login_manager.login_message_category = "info"
    app.extensions["summarizer"] = SummarizerService(
        app.config["MODEL_NAME"],
        app.config["SUMMARIZER_BACKEND"],
        app.config["MODEL_ALLOW_DOWNLOAD"],
    )

    from app.models import User
    from app.routes import admin, auth, main, summarizer, user

    for blueprint in (main.bp, auth.bp, summarizer.bp, user.bp, admin.bp):
        app.register_blueprint(blueprint)

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except (ValueError, TypeError):
            return None

    @app.before_request
    def reject_deactivated_session():
        if not current_user.is_anonymous and not current_user.active:
            logout_user()
            flash("This account has been deactivated. Contact your administrator.", "warning")

    @app.after_request
    def security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'self'; base-uri 'self'; form-action 'self'"
        )
        if current_user.is_authenticated:
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        if request.path.startswith("/api/"):
            return jsonify(error="Your session expired. Refresh the page and try again."), 400
        return render_template(
            "errors/error.html",
            code=400,
            title="Let's refresh that session",
            message="Your form session expired. Reload the page and try again.",
        ), 400

    def error_page(error):
        code = error.code
        titles = {
            403: "This space is restricted",
            404: "A little off the page",
            413: "That text is a little too long",
            500: "Something interrupted the flow",
        }
        messages = {
            403: "You don't have permission to access this page.",
            404: "The page you're looking for may have moved or no longer exists.",
            413: "Use fewer than 50,000 characters and try again.",
            500: "We couldn't complete your request. Please try again in a moment.",
        }
        if code == 500:
            db.session.rollback()
        if request.path.startswith("/api/"):
            return jsonify(error=messages[code]), code
        return render_template(
            "errors/error.html", code=code, title=titles[code], message=messages[code]
        ), code

    for status in (403, 404, 413, 500):
        app.register_error_handler(status, error_page)

    @app.cli.command("init-db")
    def init_db_command():
        db.create_all()
        click.echo("Database tables are ready.")

    @app.cli.command("seed")
    def seed_command():
        from app.services.seed import seed_database

        click.echo(seed_database())

    @app.cli.command("download-model")
    def download_model_command():
        service = SummarizerService(app.config["MODEL_NAME"], "transformer", True)
        click.echo(f"Downloading and checking {service.model_name}…")
        if service.load_model() is None:
            raise click.ClickException(
                "Model could not be downloaded. Check network access, disk space, and available memory."
            )
        click.echo("Model cached. Restart the app to use abstractive summaries.")

    with app.app_context():
        db.create_all()
    return app
