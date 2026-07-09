"""Transactional scheduling, private upload, and query services."""

from __future__ import annotations

import io
import uuid
from datetime import date
from pathlib import Path

from flask import current_app
from PIL import Image, UnidentifiedImageError
from pypdf import PdfReader
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from .extensions import db
from .models import (
    Appointment,
    AppointmentSlot,
    AppointmentStatus,
    Condition,
    Department,
    DoctorProfile,
    Hospital,
    Payment,
    PaymentStatus,
    utcnow,
)

TIME_SLOTS = ["09:00 AM", "10:00 AM", "11:00 AM", "01:00 PM", "02:00 PM", "03:00 PM", "05:00 PM"]
SLOT_CAPACITY = 3
PAYMENT_METHODS = ["Cash at hospital", "eSewa", "Khalti", "Card", "Bank transfer"]


def hospital_search(term: str = "", city: str = "") -> list[Hospital]:
    query = select(Hospital).where(Hospital.is_active.is_(True))
    if term:
        like = f"%{term.strip().lower()}%"
        query = (
            query.outerjoin(Hospital.departments_rel)
            .outerjoin(Hospital.conditions_rel)
            .where(
                or_(
                    func.lower(Hospital.name).like(like),
                    func.lower(Department.name).like(like),
                    func.lower(Condition.name).like(like),
                )
            )
        )
    if city:
        query = query.where(func.lower(Hospital.city).like(f"%{city.strip().lower()}%"))
    return list(db.session.scalars(query.distinct().order_by(Hospital.rating.desc(), Hospital.name)))


def doctor_search(specialty: str = "", hospital_id: int | None = None) -> list[DoctorProfile]:
    query = select(DoctorProfile).where(DoctorProfile.is_active.is_(True)).join(DoctorProfile.department)
    if specialty:
        query = query.where(func.lower(Department.name).like(f"%{specialty.strip().lower()}%"))
    if hospital_id:
        query = query.where(DoctorProfile.hospital_id == hospital_id)
    return list(db.session.scalars(query.order_by(DoctorProfile.rating.desc(), DoctorProfile.display_name)))


def slot_details(hospital_id: int, doctor_id: int, selected_date: date) -> list[dict]:
    counts = {
        slot.slot_time: slot.booked_count
        for slot in db.session.scalars(
            select(AppointmentSlot).where(
                AppointmentSlot.hospital_id == hospital_id,
                AppointmentSlot.doctor_id == doctor_id,
                AppointmentSlot.slot_date == selected_date,
            )
        )
    }
    result = []
    for time in TIME_SLOTS:
        booked = counts.get(time, 0)
        remaining = max(SLOT_CAPACITY - booked, 0)
        label = (
            "Full"
            if remaining == 0
            else "Empty and available"
            if booked == 0
            else f"Only {remaining} slot{'s' if remaining != 1 else ''} remaining"
        )
        result.append(
            {
                "time": time,
                "booked": booked,
                "remaining": remaining,
                "full": remaining == 0,
                "label": label,
                "level": "danger" if remaining == 0 else "warning" if remaining == 1 else "success",
            }
        )
    return result


def reserve_appointment(
    *,
    patient_id: int,
    hospital_id: int,
    doctor_id: int,
    appointment_date: date,
    appointment_time: str,
    disease: str,
    reason: str,
    payment_method: str,
    provider_reference: str | None,
) -> Appointment:
    if appointment_date < date.today() or appointment_time not in TIME_SLOTS:
        raise ValueError("Choose a valid future appointment date and time.")
    doctor = db.session.get(DoctorProfile, doctor_id)
    if not doctor or not doctor.is_active or doctor.hospital_id != hospital_id:
        raise ValueError("The selected doctor is not available at that hospital.")
    if payment_method not in PAYMENT_METHODS:
        raise ValueError("Choose a valid payment method.")
    if payment_method != "Cash at hospital" and not provider_reference:
        raise ValueError("A provider reference is required for a digital demo payment.")
    duplicate = db.session.scalar(
        select(Appointment.id).where(
            Appointment.patient_id == patient_id,
            Appointment.appointment_date == appointment_date,
            Appointment.appointment_time == appointment_time,
            Appointment.status == AppointmentStatus.BOOKED,
        )
    )
    if duplicate:
        raise ValueError("You already have an active appointment at this date and time.")

    # PostgreSQL locks this aggregate row, making capacity enforcement atomic.
    slot = db.session.scalar(
        select(AppointmentSlot)
        .where(
            AppointmentSlot.hospital_id == hospital_id,
            AppointmentSlot.doctor_id == doctor_id,
            AppointmentSlot.slot_date == appointment_date,
            AppointmentSlot.slot_time == appointment_time,
        )
        .with_for_update()
    )
    if slot is None:
        # A savepoint resolves the rare first-booking race on the unique slot identity.
        try:
            with db.session.begin_nested():
                candidate = AppointmentSlot(
                    hospital_id=hospital_id,
                    doctor_id=doctor_id,
                    slot_date=appointment_date,
                    slot_time=appointment_time,
                    capacity=SLOT_CAPACITY,
                    booked_count=0,
                )
                db.session.add(candidate)
                db.session.flush()
            slot = candidate
        except IntegrityError:
            slot = db.session.scalar(
                select(AppointmentSlot)
                .where(
                    AppointmentSlot.hospital_id == hospital_id,
                    AppointmentSlot.doctor_id == doctor_id,
                    AppointmentSlot.slot_date == appointment_date,
                    AppointmentSlot.slot_time == appointment_time,
                )
                .with_for_update()
            )
        if slot is None:
            raise RuntimeError("Unable to establish appointment slot capacity.")
    if slot.booked_count >= slot.capacity:
        raise ValueError("This appointment slot is full. Please choose another time.")
    slot.booked_count += 1

    appointment = Appointment(
        patient_id=patient_id,
        hospital_id=hospital_id,
        doctor_id=doctor_id,
        appointment_date=appointment_date,
        appointment_time=appointment_time,
        disease=disease,
        reason=reason,
        status=AppointmentStatus.BOOKED,
    )
    db.session.add(appointment)
    db.session.flush()
    paid = payment_method != "Cash at hospital"
    appointment.payment = Payment(
        method=payment_method,
        amount=doctor.consultation_fee,
        provider_reference=provider_reference or None,
        status=PaymentStatus.PAID if paid else PaymentStatus.PENDING,
        paid_at=utcnow() if paid else None,
    )
    return appointment


def cancel_appointment_record(appointment: Appointment, reason: str = "Cancelled by patient") -> None:
    if appointment.status != AppointmentStatus.BOOKED:
        raise ValueError("Only an active booked appointment can be cancelled.")
    slot = db.session.scalar(
        select(AppointmentSlot)
        .where(
            AppointmentSlot.hospital_id == appointment.hospital_id,
            AppointmentSlot.doctor_id == appointment.doctor_id,
            AppointmentSlot.slot_date == appointment.appointment_date,
            AppointmentSlot.slot_time == appointment.appointment_time,
        )
        .with_for_update()
    )
    if slot:
        slot.booked_count = max(0, slot.booked_count - 1)
    appointment.status = AppointmentStatus.CANCELLED
    appointment.cancellation_reason = reason[:500]
    appointment.cancelled_at = utcnow()
    if appointment.payment and appointment.payment.status == PaymentStatus.PAID:
        appointment.payment.status = PaymentStatus.REFUNDED
        appointment.payment.refunded_at = utcnow()


def _read_limited(upload, limit: int) -> bytes:
    data = upload.stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError("The file is larger than the configured upload limit.")
    if not data:
        raise ValueError("The selected file is empty.")
    return data


def process_report_upload(upload) -> tuple[str, str, str]:
    original = (upload.filename or "")[:255]
    suffix = Path(original).suffix.lower()
    if suffix not in {".pdf", ".txt"}:
        raise ValueError("Only PDF and TXT reports are supported.")
    data = _read_limited(upload, current_app.config["MAX_CONTENT_LENGTH"])
    key = f"{uuid.uuid4().hex}{suffix}"
    destination = Path(current_app.config["PRIVATE_UPLOAD_ROOT"], "reports", key)
    if suffix == ".pdf":
        if not data.startswith(b"%PDF-"):
            raise ValueError("The file signature is not a valid PDF.")
        try:
            reader = PdfReader(io.BytesIO(data), strict=False)
            if len(reader.pages) > 100:
                raise ValueError("Reports are limited to 100 pages.")
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError("The PDF could not be safely parsed.") from exc
    else:
        if b"\x00" in data:
            raise ValueError("The TXT file contains invalid binary content.")
        text = data.decode("utf-8", errors="strict")
    if not text.strip():
        raise ValueError("No readable text was found in the report.")
    destination.write_bytes(data)
    return original, key, text[: current_app.config["REPORT_TEXT_LIMIT"]]


def process_photo_upload(upload) -> tuple[str, str, Path]:
    original = (upload.filename or "")[:255]
    if Path(original).suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise ValueError("Use a JPG, PNG, or WEBP image.")
    data = _read_limited(upload, current_app.config["MAX_CONTENT_LENGTH"])
    try:
        image = Image.open(io.BytesIO(data))
        image.verify()
        image = Image.open(io.BytesIO(data)).convert("RGB")
        if image.width * image.height > 25_000_000:
            raise ValueError("Image dimensions are too large.")
        image.thumbnail((2400, 2400))
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("The file signature is not a supported image.") from exc
    key = f"{uuid.uuid4().hex}.jpg"
    destination = Path(current_app.config["PRIVATE_UPLOAD_ROOT"], "photos", key)
    image.save(destination, "JPEG", quality=90, optimize=True)  # rewrite strips metadata and embedded payloads
    return original, key, destination
