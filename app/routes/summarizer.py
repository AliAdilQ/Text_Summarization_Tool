from flask import Blueprint, current_app, jsonify, render_template, request, url_for
from flask_login import current_user
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.forms.summarizer import SummarizerForm
from app.models import Summary

bp = Blueprint("summarizer", __name__)


@bp.get("/summarizer")
def workspace():
    return render_template("summarizer.html", form=SummarizerForm())


@bp.post("/api/summarize")
def generate():
    if not request.is_json:
        return jsonify(error="Send a JSON request with text and length."), 400
    data = request.get_json(silent=True)
    if (
        not isinstance(data, dict)
        or not isinstance(data.get("text"), str)
        or not isinstance(data.get("length", "medium"), str)
    ):
        return jsonify(error="Provide text and a valid summary length."), 400
    # CSRFProtect validates the X-CSRFToken header before this route executes.
    form = SummarizerForm(
        data={"text": data["text"], "length": data.get("length", "medium")}, meta={"csrf": False}
    )
    if not form.validate():
        return jsonify(error=next(iter(form.errors.values()))[0], errors=form.errors), 422
    try:
        result = current_app.extensions["summarizer"].summarize(form.text.data, form.length.data)
    except ValueError as error:
        return jsonify(error=str(error)), 422
    payload = result.to_dict()
    payload["saved"] = False
    if current_user.is_authenticated:
        summary = Summary(
            user_id=current_user.id,
            title=" ".join(form.text.data.split()[:9])[:117].rstrip(".,:;") + "…",
            original_text=form.text.data.strip(),
            summarized_text=result.summary,
            summary_length=result.length,
            original_word_count=result.original_word_count,
            summary_word_count=result.summary_word_count,
            compression_ratio=result.compression_ratio,
            processing_time=result.processing_time,
            method=result.method,
        )
        db.session.add(summary)
        try:
            db.session.commit()
        except SQLAlchemyError:
            db.session.rollback()
            current_app.logger.exception("Could not save summary")
            payload["notice"] += (
                " Your summary was generated but couldn't be saved. Copy or download it now."
            )
        else:
            payload.update(
                saved=True,
                id=summary.id,
                detail_url=url_for("user.summary_detail", summary_id=summary.id),
            )
    return jsonify(payload)
