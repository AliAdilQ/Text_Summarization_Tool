from app.extensions import db
from app.models.user import utcnow


class Summary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    title = db.Column(db.String(120), nullable=False)
    original_text = db.Column(db.Text, nullable=False)
    summarized_text = db.Column(db.Text, nullable=False)
    summary_length = db.Column(db.String(10), nullable=False)
    original_word_count = db.Column(db.Integer, nullable=False)
    summary_word_count = db.Column(db.Integer, nullable=False)
    compression_ratio = db.Column(db.Float, nullable=False)
    processing_time = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(30), nullable=False, default="extractive")
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)
    seed_key = db.Column(db.String(50), unique=True)
    user = db.relationship("User", back_populates="summaries")
