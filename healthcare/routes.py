"""Patient and public routes with record-level ownership checks."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from flask import abort, current_app, flash, jsonify, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required
from sqlalchemy import func, select, text

from utils.chatbot import bot_reply
from utils.health_rules import DISEASES, analyze_text
from utils.photo_analyzer import analyze_photo

from .extensions import csrf, db, limiter
from .models import (
    Appointment,
    AppointmentStatus,
    Conversation,
    ConversationStatus,
    DoctorProfile,
    Hospital,
    Message,
    PaymentStatus,
    PhotoAnalysis,
    ReportAnalysis,
    UserRole,
)
from .security import audit, clean_text, owns_patient_record
from .services import (
    PAYMENT_METHODS,
    SLOT_CAPACITY,
    TIME_SLOTS,
    cancel_appointment_record,
    doctor_search,
    hospital_search,
    process_photo_upload,
    process_report_upload,
    reserve_appointment,
    slot_details,
)


def _recommendations(profile: dict):
    return hospital_search(profile["department"])[:3], doctor_search(profile["department"])[:4]


def _conversation_view(conversation: Conversation):
    patient_message = next((m for m in conversation.messages if m.sender_role == "patient"), None)
    bot_message = next((m for m in conversation.messages if m.sender_role == "bot"), None)
    doctor_messages = [m for m in conversation.messages if m.sender_role == "doctor"]
    return SimpleNamespace(
        id=conversation.public_id,
        patient_name=conversation.patient.name,
        doctor_name=conversation.doctor.name,
        specialty=conversation.doctor.specialty,
        doctor_id=conversation.doctor_id,
        message=patient_message.body if patient_message else "",
        bot_reply=bot_message.body if bot_message else "",
        doctor_reply=doctor_messages[-1].body if doctor_messages else None,
        status=conversation.status.value,
        created_at=conversation.created_at.strftime("%Y-%m-%d %H:%M"),
    )


def register_public_routes(app):
    @app.context_processor
    def template_globals():
        return {
            "disease_rules": DISEASES,
            "time_slots": TIME_SLOTS,
            "slot_capacity": SLOT_CAPACITY,
            "payment_methods": PAYMENT_METHODS,
            "today": date.today().isoformat(),
            "current_year": datetime.now().year,
            "UserRole": UserRole,
        }

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.get("/health/live")
    @csrf.exempt
    def health_live():
        return jsonify({"status": "ok"})

    @app.get("/health/ready")
    @csrf.exempt
    def health_ready():
        try:
            db.session.execute(text("SELECT 1"))
            return jsonify({"status": "ready"})
        except Exception:
            db.session.rollback()
            return jsonify({"status": "unavailable"}), 503

    @app.route("/dashboard")
    @login_required
    def dashboard():
        if current_user.role in {UserRole.DOCTOR, UserRole.ADMIN}:
            return redirect(url_for("doctor_admin_dashboard"))
        appointments = list(
            db.session.scalars(
                select(Appointment)
                .where(Appointment.patient_id == current_user.id)
                .order_by(Appointment.created_at.desc())
                .limit(5)
            )
        )
        conversations = list(
            db.session.scalars(
                select(Conversation)
                .where(Conversation.patient_id == current_user.id)
                .order_by(Conversation.updated_at.desc())
                .limit(5)
            )
        )
        counts = {
            "hospitals": db.session.scalar(
                select(func.count()).select_from(Hospital).where(Hospital.is_active.is_(True))
            ),
            "doctors": db.session.scalar(
                select(func.count()).select_from(DoctorProfile).where(DoctorProfile.is_active.is_(True))
            ),
            "appointments": db.session.scalar(
                select(func.count()).select_from(Appointment).where(Appointment.patient_id == current_user.id)
            ),
            "reports": db.session.scalar(
                select(func.count()).select_from(ReportAnalysis).where(ReportAnalysis.patient_id == current_user.id)
            ),
        }
        return render_template(
            "dashboard.html",
            counts=counts,
            appointments=appointments,
            chats=[_conversation_view(c) for c in conversations],
        )

    @app.route("/upload-report", methods=["GET", "POST"])
    @login_required
    @limiter.limit("12 per hour")
    def upload_report():
        if current_user.role != UserRole.PATIENT:
            abort(403)
        if request.method == "POST":
            manual = request.form.get("report_text", "").strip()
            upload = request.files.get("report_file")
            original, storage_key, extracted = "Manual entry", None, manual
            try:
                if upload and upload.filename:
                    original, storage_key, extracted = process_report_upload(upload)
                if not extracted.strip():
                    raise ValueError("Upload a report or paste report text.")
                if len(extracted) > current_app.config["REPORT_TEXT_LIMIT"]:
                    raise ValueError("Report text exceeds the analysis limit.")
                result = analyze_text(extracted)
                profile = result["profile"]
                analysis = ReportAnalysis(
                    patient_id=current_user.id,
                    original_filename=original,
                    storage_key=storage_key,
                    extracted_text=extracted,
                    detected_condition=profile["name"],
                    confidence=result["confidence"],
                    matched_keywords=result["keywords"],
                    result_payload=profile,
                )
                db.session.add(analysis)
                db.session.flush()
                audit("report.analyze", "report_analysis", analysis.public_id)
                db.session.commit()
                return redirect(url_for("report_result", id=analysis.public_id))
            except ValueError as exc:
                db.session.rollback()
                flash(str(exc), "danger")
        return render_template("report_upload.html")

    @app.route("/report-result/<id>")
    @login_required
    def report_result(id):
        analysis = db.session.scalar(select(ReportAnalysis).where(ReportAnalysis.public_id == id))
        if not analysis:
            abort(404)
        if not owns_patient_record(analysis.patient_id):
            abort(403)
        profile = analysis.result_payload
        hospitals, doctors = _recommendations(profile)
        audit("report.view", "report_analysis", analysis.public_id)
        db.session.commit()
        return render_template(
            "report_result.html", analysis=analysis, profile=profile, hospitals=hospitals, doctors=doctors
        )

    @app.route("/symptom-checker", methods=["GET", "POST"])
    @csrf.exempt
    @limiter.limit("30 per hour")
    def symptom_checker():
        result = None
        hospitals = []
        doctors = []
        if request.method == "POST":
            required = ["age", "gender", "main_symptom", "duration", "severity"]
            if not all(request.form.get(item, "").strip() for item in required):
                flash("Complete all required symptom fields.", "warning")
            else:
                try:
                    age = int(request.form["age"])
                    if not 0 < age < 125:
                        raise ValueError
                    combined = " ".join(
                        clean_text(request.form.get(x), 2000) for x in ["main_symptom", "other_symptoms", "conditions"]
                    )
                    result = analyze_text(combined)
                    result["severity"] = request.form["severity"]
                    result["emergency"] = result["emergency"] or request.form["severity"] == "Severe"
                    hospitals, doctors = _recommendations(result["profile"])
                except ValueError:
                    flash("Enter a valid age and concise symptom description.", "danger")
        return render_template("symptom_checker.html", result=result, hospitals=hospitals, doctors=doctors)

    @app.route("/photo-analysis", methods=["GET", "POST"])
    @login_required
    @limiter.limit("12 per hour")
    def photo_analysis():
        if current_user.role != UserRole.PATIENT:
            abort(403)
        if request.method == "POST":
            upload = request.files.get("photo")
            if not upload or not upload.filename:
                flash("Choose a photo to analyze.", "warning")
            else:
                try:
                    original, storage_key, path = process_photo_upload(upload)
                    result = analyze_photo(path)
                    analysis = PhotoAnalysis(
                        patient_id=current_user.id,
                        original_filename=original,
                        storage_key=storage_key,
                        observations=result["observations"],
                        detected_condition=result["condition"],
                        recommendation=result["recommendation"],
                        redness=Decimal(str(result["redness"])),
                        dark_spots=Decimal(str(result["dark_spots"])),
                    )
                    db.session.add(analysis)
                    db.session.flush()
                    audit("photo.analyze", "photo_analysis", analysis.public_id)
                    db.session.commit()
                    return redirect(url_for("photo_result", id=analysis.public_id))
                except ValueError as exc:
                    db.session.rollback()
                    flash(str(exc), "danger")
        return render_template("photo_analysis.html")

    @app.route("/photo-result/<id>")
    @login_required
    def photo_result(id):
        analysis = db.session.scalar(select(PhotoAnalysis).where(PhotoAnalysis.public_id == id))
        if not analysis:
            abort(404)
        if not owns_patient_record(analysis.patient_id):
            abort(403)
        result = {
            "observations": analysis.observations,
            "condition": analysis.detected_condition,
            "recommendation": analysis.recommendation,
            "redness": analysis.redness,
            "dark_spots": analysis.dark_spots,
            "specialist": "Dermatologist",
            "warnings": ["Spreading redness", "Pus or fever", "Severe pain", "Rapid swelling", "Breathing difficulty"],
        }
        return render_template(
            "photo_result.html",
            analysis=analysis,
            result=result,
            hospitals=hospital_search("Dermatology")[:3],
            doctors=doctor_search("Dermatology")[:4],
        )

    @app.route("/private/photo/<id>")
    @login_required
    def private_photo(id):
        analysis = db.session.scalar(select(PhotoAnalysis).where(PhotoAnalysis.public_id == id))
        if not analysis:
            abort(404)
        if not owns_patient_record(analysis.patient_id):
            abort(403)
        path = Path(current_app.config["PRIVATE_UPLOAD_ROOT"], "photos", analysis.storage_key)
        if not path.is_file():
            abort(404)
        audit("photo.file_view", "photo_analysis", analysis.public_id)
        db.session.commit()
        return send_file(path, mimetype="image/jpeg", conditional=True, max_age=0)

    @app.route("/hospitals")
    def hospitals():
        disease = request.args.get("disease", "").strip()
        department = request.args.get("department", "").strip()
        city = request.args.get("city", "").strip()
        return render_template(
            "hospitals.html",
            hospitals=hospital_search(disease or department, city),
            disease=disease,
            department=department,
            city=city,
        )

    @app.route("/doctors")
    def doctors():
        specialty = request.args.get("specialty", "").strip()
        hospital_id = request.args.get("hospital_id", "")
        parsed = int(hospital_id) if hospital_id.isdigit() else None
        return render_template(
            "doctors.html",
            doctors=doctor_search(specialty, parsed),
            hospitals=hospital_search(),
            specialty=specialty,
            hospital_id=hospital_id,
        )

    @app.route("/book-appointment", methods=["GET", "POST"])
    @login_required
    @limiter.limit("20 per hour")
    def book_appointment():
        if current_user.role != UserRole.PATIENT:
            abort(403)
        hospitals_list = hospital_search()
        doctors_list = doctor_search()
        prefill = {
            "hospital_id": request.args.get("hospital_id", ""),
            "doctor_id": request.args.get("doctor_id", ""),
            "disease": request.args.get("disease", ""),
        }
        if request.method == "POST":
            try:
                selected_date = date.fromisoformat(request.form.get("appointment_date", ""))
                hospital_id = int(request.form.get("hospital_id", ""))
                doctor_id = int(request.form.get("doctor_id", ""))
                disease = clean_text(request.form.get("disease"), 180, required=True)
                reason = clean_text(request.form.get("reason"), 2000)
                appointment = reserve_appointment(
                    patient_id=current_user.id,
                    hospital_id=hospital_id,
                    doctor_id=doctor_id,
                    appointment_date=selected_date,
                    appointment_time=request.form.get("appointment_time", ""),
                    disease=disease,
                    reason=reason,
                    payment_method=request.form.get("payment_method", ""),
                    provider_reference=clean_text(request.form.get("transaction_id"), 150),
                )
                db.session.flush()
                audit("appointment.book", "appointment", appointment.public_id)
                db.session.commit()
                flash("Appointment booked. Any displayed payment is a simulation only.", "success")
                return redirect(url_for("appointments"))
            except (ValueError, TypeError) as exc:
                db.session.rollback()
                flash(str(exc) or "Invalid appointment details.", "danger")
        return render_template(
            "book_appointment.html",
            hospitals=hospitals_list,
            doctors=doctors_list,
            prefill=prefill,
            patient=current_user.patient_profile,
        )

    @app.route("/appointments")
    @login_required
    def appointments():
        if current_user.role != UserRole.PATIENT:
            return redirect(url_for("doctor_admin_appointments"))
        items = list(
            db.session.scalars(
                select(Appointment)
                .where(Appointment.patient_id == current_user.id)
                .order_by(Appointment.created_at.desc())
            )
        )
        return render_template("appointments.html", appointments=items)

    @app.post("/cancel-appointment/<id>")
    @login_required
    def cancel_appointment(id):
        appointment = db.session.scalar(select(Appointment).where(Appointment.public_id == id))
        if not appointment:
            abort(404)
        if appointment.patient_id != current_user.id and current_user.role != UserRole.ADMIN:
            abort(403)
        try:
            cancel_appointment_record(
                appointment, clean_text(request.form.get("reason"), 500) or "Cancelled by patient"
            )
            audit("appointment.cancel", "appointment", appointment.public_id)
            db.session.commit()
            flash("Appointment cancelled and its capacity released. Paid demo records were marked refunded.", "success")
        except ValueError as exc:
            db.session.rollback()
            flash(str(exc), "danger")
        return redirect(url_for("appointments"))

    @app.route("/payment/<id>", methods=["GET", "POST"])
    @login_required
    def payment(id):
        appointment = db.session.scalar(select(Appointment).where(Appointment.public_id == id))
        if not appointment:
            abort(404)
        if appointment.patient_id != current_user.id and current_user.role != UserRole.ADMIN:
            abort(403)
        if request.method == "POST":
            method = request.form.get("payment_method", "")
            reference = clean_text(request.form.get("transaction_id"), 150)
            if method not in PAYMENT_METHODS or (method != "Cash at hospital" and not reference):
                flash("Digital demo payments require a provider reference.", "danger")
            elif appointment.status == AppointmentStatus.CANCELLED:
                flash("Payment cannot be changed for a cancelled appointment.", "danger")
            else:
                appointment.payment.method = method
                appointment.payment.provider_reference = reference or None
                appointment.payment.status = (
                    PaymentStatus.PENDING if method == "Cash at hospital" else PaymentStatus.PAID
                )
                audit("payment.demo_update", "payment", appointment.payment.public_id)
                db.session.commit()
                flash("Demo payment record updated. No money was processed.", "success")
                return redirect(url_for("appointments"))
        return render_template("payment.html", appointment=appointment)

    @app.route("/chat", methods=["GET", "POST"])
    @login_required
    @limiter.limit("30 per hour")
    def chat():
        if current_user.role != UserRole.PATIENT:
            return redirect(url_for("doctor_admin_chats"))
        if request.method == "POST":
            try:
                doctor_id = int(request.form.get("doctor_id", ""))
                doctor = db.session.get(DoctorProfile, doctor_id)
                message_text = clean_text(request.form.get("message"), 3000, required=True)
                if not doctor or not doctor.is_active:
                    raise ValueError("Choose an available doctor.")
                conversation = Conversation(
                    patient_id=current_user.id,
                    doctor_id=doctor.id,
                    subject=message_text[:120],
                    status=ConversationStatus.OPEN,
                )
                conversation.messages = [
                    Message(sender_id=current_user.id, sender_role="patient", body=message_text),
                    Message(sender_id=None, sender_role="bot", body=bot_reply(message_text)),
                ]
                db.session.add(conversation)
                db.session.flush()
                audit("chat.create", "conversation", conversation.public_id)
                db.session.commit()
                flash("Message sent. Automated safety guidance is shown while awaiting a clinician.", "success")
                return redirect(url_for("chat"))
            except (ValueError, TypeError) as exc:
                db.session.rollback()
                flash(str(exc), "danger")
        conversations = list(
            db.session.scalars(
                select(Conversation).where(Conversation.patient_id == current_user.id).order_by(Conversation.created_at)
            )
        )
        return render_template(
            "chat.html", doctors=doctor_search(), chats=[_conversation_view(c) for c in conversations]
        )

    @app.route("/slot-availability")
    def slot_availability():
        hospital_id = request.args.get("hospital_id", "")
        doctor_id = request.args.get("doctor_id", "")
        selected = request.args.get("date", date.today().isoformat())
        slots = []
        try:
            selected_date = date.fromisoformat(selected)
            if hospital_id.isdigit() and doctor_id.isdigit():
                slots = slot_details(int(hospital_id), int(doctor_id), selected_date)
        except ValueError:
            selected = date.today().isoformat()
            flash("Choose a valid date.", "danger")
        return render_template(
            "slot_availability.html",
            hospitals=hospital_search(),
            doctors=doctor_search(hospital_id=int(hospital_id) if hospital_id.isdigit() else None),
            slots=slots,
            hospital_id=hospital_id,
            doctor_id=doctor_id,
            selected_date=selected,
        )

    @app.get("/api/check-slots")
    @limiter.limit("60 per minute")
    def api_check_slots():
        try:
            hospital_id = int(request.args["hospital_id"])
            doctor_id = int(request.args["doctor_id"])
            selected = date.fromisoformat(request.args["date"])
        except (KeyError, ValueError):
            return jsonify({"error": "Valid hospital_id, doctor_id, and date are required."}), 400
        return jsonify({"capacity": SLOT_CAPACITY, "slots": slot_details(hospital_id, doctor_id, selected)})

    @app.get("/api/doctors-by-hospital/<int:hospital_id>")
    def api_doctors_by_hospital(hospital_id):
        return jsonify(
            [
                {
                    "id": d.id,
                    "name": d.name,
                    "specialty": d.specialty,
                    "hospital_id": d.hospital_id,
                    "consultation_fee": float(d.consultation_fee),
                }
                for d in doctor_search(hospital_id=hospital_id)
            ]
        )

    @app.get("/api/hospitals-by-disease")
    def api_hospitals_by_disease():
        return jsonify(
            [
                {"id": h.id, "name": h.name, "city": h.city, "rating": float(h.rating)}
                for h in hospital_search(request.args.get("disease", ""), request.args.get("city", ""))
            ]
        )

    @app.post("/api/bot-reply")
    @csrf.exempt
    @limiter.limit("30 per minute")
    def api_bot_reply():
        data = request.get_json(silent=True) or {}
        message = clean_text(data.get("message"), 3000)
        if not message:
            return jsonify({"error": "message is required"}), 400
        return jsonify({"reply": bot_reply(message)})

    @app.route("/report")
    def old_report():
        return redirect(url_for("upload_report"))

    @app.route("/symptoms")
    def old_symptoms():
        return redirect(url_for("symptom_checker"))

    @app.route("/photo")
    def old_photo():
        return redirect(url_for("photo_analysis"))

    @app.route("/appointment")
    def old_appointment():
        return redirect(url_for("book_appointment"))
