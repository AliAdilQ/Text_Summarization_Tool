from flask import current_app
from flask_wtf import FlaskForm
from wtforms import SelectField, TextAreaField
from wtforms.validators import DataRequired, ValidationError

from app.services.summarizer import word_count


class SummarizerForm(FlaskForm):
    text = TextAreaField(
        "Original text", validators=[DataRequired(message="Paste some text to get started.")]
    )
    length = SelectField(
        "Summary length",
        choices=[("short", "Short"), ("medium", "Medium"), ("long", "Long")],
        default="medium",
    )

    def validate_text(self, field):
        if len(field.data) > current_app.config["MAX_TEXT_CHARACTERS"]:
            raise ValidationError("Keep your text under 50,000 characters.")
        if word_count(field.data) < current_app.config["MIN_TEXT_WORDS"]:
            raise ValidationError("Add at least 30 words so there is enough context to summarize.")
