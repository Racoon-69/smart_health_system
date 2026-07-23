"""Validated authentication and profile forms."""

from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import BooleanField, DateField, EmailField, PasswordField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional


class LoginForm(FlaskForm):
    email = EmailField("Email", validators=[DataRequired(), Email(), Length(max=254)])
    password = PasswordField("Password", validators=[DataRequired(), Length(max=128)])
    remember = BooleanField("Keep me signed in on this device")
    submit = SubmitField("Sign in")


class RegistrationForm(FlaskForm):
    full_name = StringField("Full name", validators=[DataRequired(), Length(min=2, max=120)])
    email = EmailField("Email", validators=[DataRequired(), Email(), Length(max=254)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=128)])
    confirm_password = PasswordField("Confirm password", validators=[DataRequired(), EqualTo("password")])
    account_type = SelectField("Account type", choices=[("patient", "Patient"), ("doctor", "Doctor / Healthcare Professional")], default="patient")
    accept_terms = BooleanField("I accept the privacy notice and medical disclaimer", validators=[DataRequired()])
    submit = SubmitField("Create secure account")


class ProfileForm(FlaskForm):
    full_name = StringField("Full name", validators=[DataRequired(), Length(max=120)])
    date_of_birth = DateField("Date of birth", validators=[Optional()])
    gender = StringField("Gender", validators=[Optional(), Length(max=40)])
    phone = StringField("Phone", validators=[Optional(), Length(max=30)])
    city = StringField("City", validators=[Optional(), Length(max=80)])
    emergency_contact = StringField("Emergency contact", validators=[Optional(), Length(max=120)])
    family_contact_name = StringField("Family contact name", validators=[Optional(), Length(max=120)])
    family_contact_phone = StringField("Family contact phone", validators=[Optional(), Length(max=30)])
    family_contact_relationship = StringField("Relationship", validators=[Optional(), Length(max=60)])
    medical_conditions = TextAreaField("Existing conditions", validators=[Optional(), Length(max=2000)])
    allergies = TextAreaField("Allergies", validators=[Optional(), Length(max=2000)])
    current_medications = TextAreaField("Current medications", validators=[Optional(), Length(max=2000)])
    submit = SubmitField("Save profile")
