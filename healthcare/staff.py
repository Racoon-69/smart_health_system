"""Role-scoped doctor and administrator operations."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import func, select

from .extensions import db
from .models import (
    Appointment,
    AppointmentStatus,
    AuditEvent,
    Conversation,
    ConversationStatus,
    Department,
    DoctorProfile,
    Hospital,
    Message,
    Payment,
    PaymentStatus,
    UserRole,
)
from .security import audit, clean_text, role_required
from .services import cancel_appointment_record, doctor_search, hospital_search


def _conversation_view(conversation: Conversation):
    patient = next((m for m in conversation.messages if m.sender_role == "patient"), None)
    bot = next((m for m in conversation.messages if m.sender_role == "bot"), None)
    replies = [m for m in conversation.messages if m.sender_role == "doctor"]
    return SimpleNamespace(
        id=conversation.public_id,
        patient_name=conversation.patient.name,
        doctor_name=conversation.doctor.name,
        specialty=conversation.doctor.specialty,
        message=patient.body if patient else "",
        bot_reply=bot.body if bot else "",
        doctor_reply=replies[-1].body if replies else None,
        status=conversation.status.value,
        created_at=conversation.created_at.strftime("%Y-%m-%d %H:%M"),
    )


def _appointment_scope():
    query = select(Appointment)
    if current_user.role == UserRole.DOCTOR:
        query = query.where(Appointment.doctor_id == current_user.doctor_profile.id)
    return query


def _conversation_scope():
    query = select(Conversation)
    if current_user.role == UserRole.DOCTOR:
        query = query.where(Conversation.doctor_id == current_user.doctor_profile.id)
    return query


def register_staff_routes(app):
    @app.route("/doctor-admin/dashboard")
    @role_required(UserRole.DOCTOR, UserRole.ADMIN)
    def doctor_admin_dashboard():
        base = _appointment_scope().subquery()

        def count(status=None, today=False):
            q = select(func.count()).select_from(base)
            if status:
                q = q.where(base.c.status == status)
            if today:
                q = q.where(base.c.appointment_date == date.today())
            return db.session.scalar(q) or 0

        appointment_items = list(
            db.session.scalars(_appointment_scope().order_by(Appointment.created_at.desc()).limit(12))
        )
        conversations = list(
            db.session.scalars(_conversation_scope().order_by(Conversation.updated_at.desc()).limit(8))
        )
        payment_query = select(func.count()).select_from(Payment).join(Appointment)
        if current_user.role == UserRole.DOCTOR:
            payment_query = payment_query.where(Appointment.doctor_id == current_user.doctor_profile.id)
        stats = {
            "total": count(),
            "today": count(today=True),
            "cancelled": count(AppointmentStatus.CANCELLED),
            "completed": count(AppointmentStatus.COMPLETED),
            "pending": db.session.scalar(payment_query.where(Payment.status == PaymentStatus.PENDING)) or 0,
            "paid": db.session.scalar(payment_query.where(Payment.status == PaymentStatus.PAID)) or 0,
        }
        audit("staff.dashboard_view", "dashboard")
        db.session.commit()
        return render_template(
            "doctor_admin_dashboard.html",
            stats=stats,
            appointments=appointment_items,
            chats=[_conversation_view(c) for c in conversations],
            doctors=doctor_search(),
            hospitals=hospital_search(),
        )

    @app.route("/doctor-admin/appointments")
    @role_required(UserRole.DOCTOR, UserRole.ADMIN)
    def doctor_admin_appointments():
        query = _appointment_scope()
        filters = {
            "date": request.args.get("date", ""),
            "doctor_id": request.args.get("doctor_id", ""),
            "hospital_id": request.args.get("hospital_id", ""),
            "status": request.args.get("status", ""),
        }
        if filters["date"]:
            try:
                query = query.where(Appointment.appointment_date == date.fromisoformat(filters["date"]))
            except ValueError:
                flash("Invalid date filter.", "danger")
        if filters["doctor_id"].isdigit() and current_user.role == UserRole.ADMIN:
            query = query.where(Appointment.doctor_id == int(filters["doctor_id"]))
        if filters["hospital_id"].isdigit():
            query = query.where(Appointment.hospital_id == int(filters["hospital_id"]))
        if filters["status"] in {item.value for item in AppointmentStatus}:
            query = query.where(Appointment.status == AppointmentStatus(filters["status"]))
        items = list(
            db.session.scalars(query.order_by(Appointment.appointment_date.desc(), Appointment.appointment_time))
        )
        return render_template(
            "admin_appointments.html", appointments=items, doctors=doctor_search(), hospitals=hospital_search()
        )

    @app.post("/doctor-admin/update-appointment/<id>")
    @role_required(UserRole.DOCTOR, UserRole.ADMIN)
    def update_appointment(id):
        appointment = db.session.scalar(select(Appointment).where(Appointment.public_id == id))
        if not appointment:
            abort(404)
        if current_user.role == UserRole.DOCTOR and appointment.doctor_id != current_user.doctor_profile.id:
            abort(403)
        try:
            new_status = AppointmentStatus(request.form.get("status", ""))
            if new_status == AppointmentStatus.CANCELLED and appointment.status == AppointmentStatus.BOOKED:
                cancel_appointment_record(appointment, "Cancelled by care team")
            elif new_status == AppointmentStatus.COMPLETED:
                if appointment.appointment_date > date.today():
                    raise ValueError("A future appointment cannot be marked completed.")
                if appointment.status != AppointmentStatus.BOOKED:
                    raise ValueError("Only booked appointments can be completed.")
                appointment.status = new_status
            elif new_status != appointment.status:
                raise ValueError("That status transition is not allowed.")
            audit(
                "appointment.status_update", "appointment", appointment.public_id, details={"status": new_status.value}
            )
            db.session.commit()
            flash("Appointment status updated.", "success")
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "danger")
        return redirect(request.referrer or url_for("doctor_admin_appointments"))

    @app.route("/doctor-admin/chats")
    @role_required(UserRole.DOCTOR, UserRole.ADMIN)
    def doctor_admin_chats():
        conversations = list(db.session.scalars(_conversation_scope().order_by(Conversation.updated_at.desc())))
        return render_template("admin_chats.html", chats=[_conversation_view(c) for c in conversations])

    @app.post("/doctor-admin/reply-chat/<id>")
    @role_required(UserRole.DOCTOR, UserRole.ADMIN)
    def reply_chat(id):
        conversation = db.session.scalar(select(Conversation).where(Conversation.public_id == id))
        if not conversation:
            abort(404)
        if current_user.role == UserRole.DOCTOR and conversation.doctor_id != current_user.doctor_profile.id:
            abort(403)
        try:
            body = clean_text(request.form.get("doctor_reply"), 3000, required=True)
            sender_id = current_user.id
            conversation.messages.append(Message(sender_id=sender_id, sender_role="doctor", body=body))
            conversation.status = ConversationStatus.ANSWERED
            audit("chat.doctor_reply", "conversation", conversation.public_id)
            db.session.commit()
            flash("Clinical reply saved and audited.", "success")
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "danger")
        return redirect(request.referrer or url_for("doctor_admin_chats"))

    @app.route("/doctor-admin/slots")
    @role_required(UserRole.DOCTOR, UserRole.ADMIN)
    def doctor_admin_slots():
        return redirect(url_for("slot_availability"))

    @app.route("/staff/directory", methods=["GET", "POST"])
    @role_required(UserRole.ADMIN)
    def staff_directory():
        departments = list(db.session.scalars(select(Department).order_by(Department.name)))
        if request.method == "POST":
            action = request.form.get("action")
            try:
                if action == "hospital":
                    department_ids = [int(value) for value in request.form.getlist("department_ids") if value.isdigit()]
                    selected_departments = list(
                        db.session.scalars(select(Department).where(Department.id.in_(department_ids)))
                    )
                    hospital = Hospital(
                        name=clean_text(request.form.get("name"), 180, required=True),
                        address=clean_text(request.form.get("address"), 250, required=True),
                        city=clean_text(request.form.get("city"), 100, required=True),
                        phone=clean_text(request.form.get("phone"), 40),
                        email=clean_text(request.form.get("email"), 254),
                        opening_hours=clean_text(request.form.get("opening_hours"), 120),
                        emergency_available=bool(request.form.get("emergency_available")),
                        departments_rel=selected_departments,
                    )
                    db.session.add(hospital)
                    db.session.flush()
                    audit("hospital.create", "hospital", hospital.public_id)
                elif action == "doctor":
                    hospital_id = int(request.form.get("hospital_id", ""))
                    department_id = int(request.form.get("department_id", ""))
                    hospital = db.session.get(Hospital, hospital_id)
                    department = db.session.get(Department, department_id)
                    if not hospital or not department:
                        raise ValueError("Choose a valid hospital and department.")
                    if department not in hospital.departments_rel:
                        hospital.departments_rel.append(department)
                    doctor = DoctorProfile(
                        display_name=clean_text(request.form.get("name"), 140, required=True),
                        hospital=hospital,
                        department=department,
                        qualification=clean_text(request.form.get("qualification"), 200),
                        consultation_fee=request.form.get("consultation_fee") or 0,
                        available_days=clean_text(request.form.get("available_days"), 100),
                        available_time=clean_text(request.form.get("available_time"), 100),
                        is_verified=False,
                    )
                    db.session.add(doctor)
                    db.session.flush()
                    audit("doctor.create", "doctor_profile", doctor.public_id)
                else:
                    raise ValueError("Unknown directory action.")
                db.session.commit()
                flash("Directory record created.", "success")
                return redirect(url_for("staff_directory"))
            except (ValueError, TypeError) as exc:
                db.session.rollback()
                flash(str(exc), "danger")
        all_hospitals = list(db.session.scalars(select(Hospital).order_by(Hospital.name)))
        all_doctors = list(db.session.scalars(select(DoctorProfile).order_by(DoctorProfile.display_name)))
        return render_template(
            "staff_directory.html", hospitals=all_hospitals, doctors=all_doctors, departments=departments
        )

    @app.post("/staff/hospital/<id>/toggle")
    @role_required(UserRole.ADMIN)
    def toggle_hospital(id):
        hospital = db.session.scalar(select(Hospital).where(Hospital.public_id == id))
        if not hospital:
            abort(404)
        hospital.is_active = not hospital.is_active
        audit("hospital.toggle_active", "hospital", id, details={"active": hospital.is_active})
        db.session.commit()
        return redirect(url_for("staff_directory"))

    @app.post("/staff/doctor/<id>/toggle")
    @role_required(UserRole.ADMIN)
    def toggle_doctor(id):
        doctor = db.session.scalar(select(DoctorProfile).where(DoctorProfile.public_id == id))
        if not doctor:
            abort(404)
        doctor.is_active = not doctor.is_active
        audit("doctor.toggle_active", "doctor_profile", id, details={"active": doctor.is_active})
        db.session.commit()
        return redirect(url_for("staff_directory"))

    @app.route("/staff/audit-log")
    @role_required(UserRole.ADMIN)
    def audit_log():
        events = list(db.session.scalars(select(AuditEvent).order_by(AuditEvent.occurred_at.desc()).limit(250)))
        return render_template("audit_log.html", events=events)
