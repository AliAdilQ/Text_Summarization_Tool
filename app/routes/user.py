from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.forms.auth import ProfileForm
from app.models import Summary, User
from app.utils import download_response

bp = Blueprint("user", __name__, url_prefix="/workspace")


def owned_summary(summary_id):
    summary = db.session.scalar(
        db.select(Summary).where(Summary.id == summary_id, Summary.user_id == current_user.id)
    )
    if summary is None:
        abort(404)
    return summary


@bp.get("")
@login_required
def dashboard():
    stats = db.session.execute(
        db.select(
            func.count(Summary.id),
            func.coalesce(func.sum(Summary.original_word_count - Summary.summary_word_count), 0),
            func.coalesce(func.avg(Summary.compression_ratio), 0),
        ).where(Summary.user_id == current_user.id)
    ).one()
    recent = db.session.scalars(
        db.select(Summary)
        .where(Summary.user_id == current_user.id)
        .order_by(Summary.created_at.desc())
        .limit(4)
    ).all()
    return render_template("user/dashboard.html", stats=stats, recent=recent)


@bp.get("/history")
@login_required
def history():
    query = db.select(Summary).where(Summary.user_id == current_user.id)
    search = request.args.get("q", "").strip()[:120]
    length = request.args.get("length", "")
    if search:
        query = query.where(
            or_(
                Summary.title.contains(search, autoescape=True),
                Summary.summarized_text.contains(search, autoescape=True),
            )
        )
    if length in {"short", "medium", "long"}:
        query = query.where(Summary.summary_length == length)
    pagination = db.paginate(
        query.order_by(Summary.created_at.desc()), per_page=8, max_per_page=8, error_out=False
    )
    return render_template("user/history.html", pagination=pagination, search=search, length=length)


@bp.get("/summaries/<int:summary_id>")
@login_required
def summary_detail(summary_id):
    return render_template("user/summary_detail.html", summary=owned_summary(summary_id))


@bp.get("/summaries/<int:summary_id>/download")
@login_required
def download(summary_id):
    return download_response(owned_summary(summary_id))


@bp.post("/summaries/<int:summary_id>/delete")
@login_required
def delete(summary_id):
    db.session.delete(owned_summary(summary_id))
    db.session.commit()
    flash("Summary deleted.", "success")
    return redirect(url_for("user.history"))


@bp.post("/history/clear")
@login_required
def clear_history():
    db.session.execute(db.delete(Summary).where(Summary.user_id == current_user.id))
    db.session.commit()
    flash("Your history has been cleared.", "success")
    return redirect(url_for("user.history"))


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        username, email = form.username.data.strip().lower(), form.email.data.strip().lower()
        existing = db.session.scalar(
            db.select(User).where(
                User.id != current_user.id, or_(User.username == username, User.email == email)
            )
        )
        if existing:
            form.email.errors.append("That username or email is already in use.")
        else:
            current_user.username, current_user.email = username, email
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                form.email.errors.append("That username or email is already in use.")
            else:
                flash("Profile updated.", "success")
                return redirect(url_for("user.profile"))
    return render_template("user/profile.html", form=form)
