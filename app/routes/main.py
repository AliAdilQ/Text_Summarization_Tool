from flask import Blueprint, jsonify, render_template

bp = Blueprint("main", __name__)


@bp.get("/")
def home():
    return render_template("home.html")


@bp.get("/about")
def about():
    return render_template("about.html")


@bp.get("/health")
def health():
    return jsonify(status="ok")
