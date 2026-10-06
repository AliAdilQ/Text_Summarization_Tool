from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Regexp


class LoginForm(FlaskForm):
    identifier = StringField("Email or username", validators=[DataRequired(), Length(max=254)])
    password = PasswordField("Password", validators=[DataRequired(), Length(max=128)])
    remember = BooleanField("Keep me signed in")
    submit = SubmitField("Sign in")


class RegisterForm(FlaskForm):
    username = StringField(
        "Username",
        validators=[
            DataRequired(),
            Length(min=3, max=32),
            Regexp(r"^[A-Za-z0-9_]+$", message="Use letters, numbers, and underscores."),
        ],
    )
    email = StringField("Email address", validators=[DataRequired(), Email(), Length(max=254)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=128)])
    confirm_password = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
    submit = SubmitField("Create account")


class ProfileForm(FlaskForm):
    username = StringField(
        "Username", validators=[DataRequired(), Length(min=3, max=32), Regexp(r"^[A-Za-z0-9_]+$")]
    )
    email = StringField("Email address", validators=[DataRequired(), Email(), Length(max=254)])
    submit = SubmitField("Save changes")
