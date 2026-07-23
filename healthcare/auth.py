"""Account registration, authentication, session lifecycle, and profiles."""

from __future__ import annotations

from datetime import timedelta, timezone
from urllib.parse import urljoin, urlparse

from flask import abort, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func, select

from .extensions import db, limiter, login_manager
from .forms import LoginForm, ProfileForm, RegistrationForm
from .models import ConsentRecord, Department, DoctorProfile, Hospital, LoginActivity, PatientProfile, User, UserRole, UserSession, utcnow
from .security import PHONE_RE, audit, clean_text


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id)) if user_id.isdigit() else None


def _safe_next(target: str | None) -> bool:
    if not target:
        return False
    base = urlparse(request.host_url)
    candidate = urlparse(urljoin(request.host_url, target))
    return candidate.scheme in {"http", "https"} and base.netloc == candidate.netloc


def register_auth_routes(app):
    @app.route("/register", methods=["GET", "POST"])
    @limiter.limit("5 per hour")
    def register():
        if not current_app.config.get("ALLOW_SELF_REGISTRATION"):
            abort(404)
        if current_user.is_authenticated:
            if current_user.role in {UserRole.DOCTOR, UserRole.ADMIN}:
                return redirect(url_for("doctor_admin_dashboard"))
            return redirect(url_for("dashboard"))
        
        target_role = request.args.get("role", "patient")
        if target_role not in {"patient", "doctor"}:
            target_role = "patient"
        
        form = RegistrationForm()
        if not form.account_type.data and target_role in {"patient", "doctor"}:
            form.account_type.data = target_role

        if form.validate_on_submit():
            email = form.email.data.strip().lower()
            if db.session.scalar(select(User).where(func.lower(User.email) == email)):
                flash("An account with that email already exists. Please sign in instead.", "warning")
            else:
                account_type = form.account_type.data or request.form.get("account_type") or target_role or "patient"
                is_doctor = account_type == "doctor"
                role = UserRole.DOCTOR if is_doctor else UserRole.PATIENT
                user = User(email=email, role=role, email_verified=True)
                user.set_password(form.password.data)
                
                if is_doctor:
                    default_hospital = db.session.scalar(select(Hospital).order_by(Hospital.id))
                    default_department = db.session.scalar(select(Department).order_by(Department.id))
                    user.doctor_profile = DoctorProfile(
                        display_name=clean_text(form.full_name.data, 120, required=True),
                        hospital=default_hospital,
                        department=default_department,
                        qualification="MD Internal Medicine",
                        experience_years=5,
                        available_days="Sun-Fri",
                        available_time="09:00 AM-05:00 PM",
                        consultation_fee=1000,
                        bio="Medical practitioner registered on SmartHealth.",
                        is_verified=True,
                        license_number=f"DOC-{utcnow().strftime('%Y%m%d%H%M%S')}",
                    )
                else:
                    user.patient_profile = PatientProfile(full_name=clean_text(form.full_name.data, 120, required=True))

                db.session.add(user)
                db.session.flush()
                db.session.add(
                    ConsentRecord(
                        user_id=user.id,
                        consent_type="privacy_and_medical_disclaimer",
                        policy_version="1.0",
                        granted=True,
                        ip_address=request.access_route[0] if request.access_route else request.remote_addr,
                    )
                )
                audit("account.register", "user", user.public_id)
                db.session.commit()
                login_user(user)
                session.permanent = True
                if is_doctor:
                    flash("Your doctor account has been created successfully. Welcome to your Doctor Workspace!", "success")
                    return redirect(url_for("doctor_admin_dashboard"))
                flash("Your private patient account is ready.", "success")
                return redirect(url_for("profile"))
        return render_template("register.html", form=form, target_role=target_role)

    @app.route("/login", methods=["GET", "POST"])
    @limiter.limit("10 per minute")
    def login():
        if current_user.is_authenticated:
            if current_user.role in {UserRole.DOCTOR, UserRole.ADMIN}:
                return redirect(url_for("doctor_admin_dashboard"))
            return redirect(url_for("dashboard"))
        
        target_role = request.args.get("role", "patient")
        form = LoginForm()
        if form.validate_on_submit():
            email = form.email.data.strip().lower()
            user = db.session.scalar(select(User).where(func.lower(User.email) == email))
            now = utcnow()
            locked = False
            if user and user.locked_until:
                locked_until = (
                    user.locked_until if user.locked_until.tzinfo else user.locked_until.replace(tzinfo=timezone.utc)
                )
                locked = locked_until > now
            if user and user.is_active and not locked and user.check_password(form.password.data):
                user.failed_login_count = 0
                user.locked_until = None
                ip_addr = request.access_route[0] if request.access_route else (request.remote_addr or "")
                ua_str = (request.user_agent.string or "")[:300] if request.user_agent else ""
                db.session.add(
                    LoginActivity(
                        user=user,
                        email=email,
                        succeeded=True,
                        ip_address=ip_addr,
                        user_agent=ua_str,
                    )
                )
                db.session.add(
                    UserSession(
                        user=user,
                        email_entered=email,
                        ip_address=ip_addr,
                        user_agent=ua_str,
                        logged_in_at=now,
                        is_active=True,
                    )
                )
                audit("account.login", "user", user.public_id)
                db.session.commit()
                session.clear()
                login_user(user, remember=form.remember.data, fresh=True)
                session.permanent = True
                destination = request.args.get("next")
                if user.role in {UserRole.DOCTOR, UserRole.ADMIN}:
                    flash(f"Welcome back, {user.name}! Accessing Doctor Workspace.", "success")
                    return redirect(url_for("doctor_admin_dashboard"))
                return redirect(destination if _safe_next(destination) else url_for("dashboard"))
            if user:
                if not locked:
                    user.failed_login_count += 1
                    if user.failed_login_count >= 5:
                        user.locked_until = now + timedelta(minutes=15)
                        user.failed_login_count = 0
                audit("account.login_failed", "user", user.public_id, outcome="failure")
            db.session.add(
                LoginActivity(
                    user=user,
                    email=email,
                    succeeded=False,
                    ip_address=request.access_route[0] if request.access_route else (request.remote_addr or ""),
                    user_agent=(request.user_agent.string or "")[:300] if request.user_agent else "",
                )
            )
            db.session.commit()
            flash("Sign-in failed. Check your credentials or wait if the account is temporarily locked.", "danger")
        return render_template("login.html", form=form, target_role=target_role)

    @app.post("/logout")
    @login_required
    def logout():
        audit("account.logout", "user", current_user.public_id)
        db.session.commit()
        logout_user()
        session.clear()
        flash("You have been signed out securely.", "info")
        return redirect(url_for("index"))

    @app.route("/profile", methods=["GET", "POST"])
    @login_required
    def profile():
        if current_user.role != UserRole.PATIENT:
            return redirect(url_for("doctor_admin_dashboard"))
        profile = current_user.patient_profile or PatientProfile(user=current_user, full_name=current_user.name)
        form = ProfileForm(obj=profile)
        if form.validate_on_submit():
            if any(
                value and not PHONE_RE.match(value)
                for value in (form.phone.data, form.family_contact_phone.data)
            ):
                flash("Enter a valid phone number.", "danger")
            else:
                form.populate_obj(profile)
                for field in (
                    "full_name",
                    "gender",
                    "phone",
                    "city",
                    "emergency_contact",
                    "family_contact_name",
                    "family_contact_phone",
                    "family_contact_relationship",
                ):
                    value = getattr(profile, field)
                    if value:
                        setattr(profile, field, clean_text(value, 120 if field != "phone" else 30))
                db.session.add(profile)
                audit("profile.update", "patient_profile", profile.id)
                db.session.commit()
                flash("Profile updated.", "success")
                return redirect(url_for("profile"))
        return render_template("profile.html", form=form)

    @app.post("/account/change-password")
    @login_required
    @limiter.limit("5 per hour")
    def change_password():
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirmation = request.form.get("confirm_password", "")
        if not current_user.check_password(current_password):
            flash("The current password is incorrect.", "danger")
        elif len(new_password) < 8 or len(new_password) > 128:
            flash("New passwords must be 8–128 characters.", "danger")
        elif new_password != confirmation:
            flash("New password confirmation does not match.", "danger")
        else:
            current_user.set_password(new_password)
            audit("account.password_changed", "user", current_user.public_id)
            db.session.commit()
            flash(
                "Password changed. Other long-lived sessions should be revoked by the identity provider in a full deployment.",
                "success",
            )
        return redirect(url_for("profile"))

    @app.route("/doctor-admin")
    def doctor_admin():
        if current_user.is_authenticated and current_user.role in {UserRole.DOCTOR, UserRole.ADMIN}:
            return redirect(url_for("doctor_admin_dashboard"))
        return redirect(url_for("login", next=url_for("doctor_admin_dashboard")))
