from datetime import timedelta

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import func, or_

from app.extensions import db
from app.models import Summary, User
from app.models.user import utcnow
from app.utils import admin_required, download_response

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.get("")
@admin_required
def dashboard():
    today = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    counts = db.session.execute(
        db.select(
            func.count(Summary.id),
            func.coalesce(func.avg(Summary.compression_ratio), 0),
            func.coalesce(func.avg(Summary.processing_time), 0),
        )
    ).one()
    user_count = db.session.scalar(db.select(func.count(User.id)))
    today_count = db.session.scalar(
        db.select(func.count(Summary.id)).where(Summary.created_at >= today)
    )
    days = [today - timedelta(days=offset) for offset in range(6, -1, -1)]
    recent_counts = dict(
        db.session.execute(
            db.select(func.date(Summary.created_at), func.count(Summary.id))
            .where(Summary.created_at >= days[0])
            .group_by(func.date(Summary.created_at))
        ).all()
    )
    distribution = dict(
        db.session.execute(
            db.select(Summary.summary_length, func.count(Summary.id)).group_by(
                Summary.summary_length
            )
        ).all()
    )
    active = db.session.execute(
        db.select(User.username, func.count(Summary.id).label("total"))
        .join(Summary)
        .group_by(User.id)
        .order_by(func.count(Summary.id).desc())
        .limit(5)
    ).all()
    charts = {
        "days": [day.strftime("%a") for day in days],
        "activity": [recent_counts.get(day.strftime("%Y-%m-%d"), 0) for day in days],
        "lengths": [distribution.get(length, 0) for length in ("short", "medium", "long")],
        "users": [row[0] for row in active],
        "user_counts": [row[1] for row in active],
    }
    recent = db.session.scalars(
        db.select(Summary)
        .options(db.joinedload(Summary.user))
        .order_by(Summary.created_at.desc())
        .limit(5)
    ).all()
    return render_template(
        "admin/dashboard.html",
        counts=counts,
        user_count=user_count,
        today_count=today_count,
        charts=charts,
        recent=recent,
    )


@bp.get("/users")
@admin_required
def users():
    search = request.args.get("q", "").strip()[:120]
    query = db.select(User).options(db.selectinload(User.summaries))
    if search:
        query = query.where(
            or_(
                User.username.contains(search, autoescape=True),
                User.email.contains(search, autoescape=True),
            )
        )
    pagination = db.paginate(query.order_by(User.created_at.desc()), per_page=10, error_out=False)
    return render_template("admin/users.html", pagination=pagination, search=search)


@bp.get("/users/<int:user_id>")
@admin_required
def user_detail(user_id):
    user = db.get_or_404(User, user_id)
    recent = db.session.scalars(
        db.select(Summary)
        .where(Summary.user_id == user.id)
        .order_by(Summary.created_at.desc())
        .limit(5)
    ).all()
    return render_template("admin/user_detail.html", member=user, recent=recent)


@bp.post("/users/<int:user_id>/<action>")
@admin_required
def update_user(user_id, action):
    if action not in {"role", "status", "delete"}:
        abort(404)
    user = db.get_or_404(User, user_id)
    if user.id == current_user.id:
        flash(
            "You can't change your own administrative access or delete your account here.",
            "warning",
        )
    elif user.is_admin and action == "delete":
        flash("Demote this administrator before deleting their account.", "warning")
    elif (
        user.is_admin
        and (action == "role" or (action == "status" and user.active))
        and db.session.scalar(
            db.select(func.count(User.id)).where(User.is_admin.is_(True), User.active.is_(True))
        )
        <= 1
    ):
        flash("Keep at least one active administrator.", "warning")
    else:
        if action == "role":
            user.is_admin = not user.is_admin
        elif action == "status":
            user.active = not user.active
        else:
            db.session.delete(user)
        db.session.commit()
        flash("User account updated.", "success")
        return redirect(
            url_for("admin.users")
            if action == "delete"
            else url_for("admin.user_detail", user_id=user_id)
        )
    return redirect(url_for("admin.user_detail", user_id=user_id))


@bp.get("/summaries")
@admin_required
def summaries():
    query = db.select(Summary).options(db.joinedload(Summary.user))
    search = request.args.get("q", "").strip()[:120]
    length, user_id = request.args.get("length", ""), request.args.get("user_id", type=int)
    if search:
        query = query.where(
            or_(
                Summary.title.contains(search, autoescape=True),
                Summary.summarized_text.contains(search, autoescape=True),
            )
        )
    if length in {"short", "medium", "long"}:
        query = query.where(Summary.summary_length == length)
    if user_id:
        query = query.where(Summary.user_id == user_id)
    pagination = db.paginate(
        query.order_by(Summary.created_at.desc()), per_page=10, error_out=False
    )
    users = db.session.scalars(db.select(User).order_by(User.username)).all()
    stats = db.session.execute(
        db.select(
            func.count(Summary.id),
            func.coalesce(func.avg(Summary.compression_ratio), 0),
            func.coalesce(func.avg(Summary.processing_time), 0),
        )
    ).one()
    return render_template(
        "admin/summaries.html",
        pagination=pagination,
        search=search,
        length=length,
        users=users,
        selected_user=user_id,
        stats=stats,
    )


@bp.get("/summaries/<int:summary_id>")
@admin_required
def summary_detail(summary_id):
    return render_template("admin/summary_detail.html", summary=db.get_or_404(Summary, summary_id))


@bp.get("/summaries/<int:summary_id>/download")
@admin_required
def download(summary_id):
    return download_response(db.get_or_404(Summary, summary_id))


@bp.post("/summaries/<int:summary_id>/delete")
@admin_required
def delete_summary(summary_id):
    db.session.delete(db.get_or_404(Summary, summary_id))
    db.session.commit()
    flash("Summary deleted.", "success")
    return redirect(url_for("admin.summaries"))
