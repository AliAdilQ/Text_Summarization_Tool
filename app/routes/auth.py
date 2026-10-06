from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.forms.auth import LoginForm, RegisterForm
from app.models import User
from app.models.user import utcnow
from app.utils import safe_next

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("user.dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        identifier = form.identifier.data.strip().lower()
        user = db.session.scalar(
            db.select(User).where(or_(User.username == identifier, User.email == identifier))
        )
        if user and user.check_password(form.password.data) and user.active:
            login_user(user, remember=form.remember.data)
            user.last_login = utcnow()
            db.session.commit()
            flash(f"Welcome back, {user.username}.", "success")
            return redirect(
                safe_next(request.args.get("next"))
                or url_for("admin.dashboard" if user.is_admin else "user.dashboard")
            )
        form.password.errors.append(
            "We couldn't sign you in. Check your credentials or account status."
        )
    return render_template("auth/login.html", form=form)


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("user.dashboard"))
    form = RegisterForm()
    if form.validate_on_submit():
        username, email = form.username.data.strip().lower(), form.email.data.strip().lower()
        if db.session.scalar(
            db.select(User).where(or_(User.username == username, User.email == email))
        ):
            form.email.errors.append("That username or email is already registered.")
        else:
            user = User(username=username, email=email)
            user.set_password(form.password.data)
            db.session.add(user)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                form.email.errors.append("That username or email is already registered.")
            else:
                login_user(user)
                flash(
                    "Your workspace is ready. Let's make room for the important ideas.", "success"
                )
                return redirect(url_for("user.dashboard"))
    return render_template("auth/register.html", form=form)


@bp.post("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("main.home"))
