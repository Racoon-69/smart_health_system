"""Idempotent reference and demonstration data."""

from __future__ import annotations

import os
from datetime import date, timedelta
from decimal import Decimal

from flask import current_app
from sqlalchemy import select

from utils.health_rules import DISEASES

from .extensions import db
from .models import (
    Appointment,
    AppointmentSlot,
    AppointmentStatus,
    Condition,
    ConsentRecord,
    Conversation,
    ConversationStatus,
    Department,
    DoctorProfile,
    Hospital,
    Message,
    PatientProfile,
    Payment,
    PaymentStatus,
    User,
    UserRole,
)

DEPARTMENT_NAMES = [
    "Cardiology",
    "Dermatology",
    "Endocrinology",
    "Pulmonology",
    "Gastroenterology",
    "Neurology",
    "General Medicine",
    "Nephrology",
    "ENT",
    "Orthopedics",
]

HOSPITAL_DATA = [
    (
        "City General Hospital",
        "New Road",
        "Kathmandu",
        "01-4441000",
        "info@citygeneral.demo",
        ["General Medicine", "Cardiology", "Nephrology", "Orthopedics"],
        ["infection", "hypertension", "heart", "kidney", "anemia"],
        Decimal("4.6"),
        "24 hours",
        True,
    ),
    (
        "Smart Care Medical Center",
        "Lazimpat",
        "Kathmandu",
        "01-4422000",
        "hello@smartcare.demo",
        ["General Medicine", "Neurology", "ENT", "Gastroenterology"],
        ["migraine", "gastric", "infection", "allergy"],
        Decimal("4.5"),
        "07:00 AM-08:00 PM",
        True,
    ),
    (
        "LifeLine Hospital",
        "Lakeside",
        "Pokhara",
        "061-530900",
        "care@lifeline.demo",
        ["Pulmonology", "General Medicine", "Nephrology", "Orthopedics"],
        ["asthma", "infection", "kidney", "anemia"],
        Decimal("4.4"),
        "24 hours",
        True,
    ),
    (
        "Green Valley Health Clinic",
        "Jawalakhel",
        "Lalitpur",
        "01-5522200",
        "contact@greenvalley.demo",
        ["General Medicine", "Gastroenterology", "ENT"],
        ["gastric", "infection", "allergy"],
        Decimal("4.2"),
        "08:00 AM-07:00 PM",
        False,
    ),
    (
        "National Heart and Diabetes Center",
        "Maharajgunj",
        "Kathmandu",
        "01-4419000",
        "desk@nhdc.demo",
        ["Cardiology", "Endocrinology", "Nephrology"],
        ["diabetes", "hypertension", "heart", "thyroid", "kidney"],
        Decimal("4.8"),
        "24 hours",
        True,
    ),
    (
        "Skin and Allergy Care Hospital",
        "Baneshwor",
        "Kathmandu",
        "01-5902233",
        "skin@allergycare.demo",
        ["Dermatology", "General Medicine"],
        ["skin", "allergy"],
        Decimal("4.7"),
        "08:00 AM-06:00 PM",
        False,
    ),
]
DOCTOR_DATA = [
    (
        "Dr. Asha Sharma",
        "asha@smarthealth.com",
        "Endocrinology",
        4,
        12,
        "MD, Endocrinology",
        "Sun-Fri",
        "09:00 AM-03:00 PM",
        1200,
        "Diabetes and thyroid care with a prevention-first approach.",
        Decimal("4.9"),
    ),
    (
        "Dr. Raj Karki",
        "raj@smarthealth.com",
        "Cardiology",
        4,
        15,
        "MD, DM Cardiology",
        "Sun-Thu",
        "10:00 AM-05:00 PM",
        1500,
        "Blood pressure and cardiovascular risk specialist.",
        Decimal("4.8"),
    ),
    (
        "Dr. Neha Singh",
        "neha@smarthealth.com",
        "Dermatology",
        5,
        9,
        "MD Dermatology",
        "Sun-Fri",
        "09:00 AM-04:00 PM",
        1000,
        "Skin, allergy, rash, and wound assessment.",
        Decimal("4.8"),
    ),
    (
        "Dr. Binod Thapa",
        "binod@smarthealth.com",
        "Pulmonology",
        2,
        11,
        "MD Pulmonology",
        "Sun-Fri",
        "09:00 AM-03:00 PM",
        1100,
        "Asthma and respiratory health specialist.",
        Decimal("4.7"),
    ),
    (
        "Dr. Suman Adhikari",
        "suman@smarthealth.com",
        "Gastroenterology",
        1,
        10,
        "MD Gastroenterology",
        "Mon-Sat",
        "10:00 AM-05:00 PM",
        1100,
        "Digestive and liver care.",
        Decimal("4.6"),
    ),
    (
        "Dr. Rina Joshi",
        "rina@smarthealth.com",
        "General Medicine",
        0,
        8,
        "MD Internal Medicine",
        "Sun-Fri",
        "09:00 AM-05:00 PM",
        800,
        "First-contact adult care.",
        Decimal("4.7"),
    ),
    (
        "Dr. Prakash Rai",
        "prakash@smarthealth.com",
        "Neurology",
        1,
        13,
        "MD, DM Neurology",
        "Sun-Thu",
        "01:00 PM-05:00 PM",
        1400,
        "Headache and neurological symptom evaluation.",
        Decimal("4.7"),
    ),
    (
        "Dr. Maya Gurung",
        "maya@smarthealth.com",
        "Nephrology",
        0,
        10,
        "MD Nephrology",
        "Mon-Fri",
        "10:00 AM-03:00 PM",
        1300,
        "Kidney health and long-term renal care.",
        Decimal("4.6"),
    ),
]


def _slug(value: str) -> str:
    return value.lower().replace("/", "-").replace(" ", "-")


def seed_database(include_demo: bool | None = None) -> None:
    departments = {}
    for name in DEPARTMENT_NAMES:
        item = db.session.scalar(select(Department).where(Department.name == name))
        if not item:
            item = Department(name=name, slug=_slug(name), description=f"Clinical services related to {name}.")
            db.session.add(item)
        departments[name] = item
    db.session.flush()
    conditions = {}
    for key, profile in DISEASES.items():
        item = db.session.scalar(select(Condition).where(Condition.slug == key))
        if not item:
            item = Condition(
                name=profile["name"],
                slug=key,
                description=profile["description"],
                specialist_title=profile["specialist"],
                department=departments.get(profile["department"]),
            )
            db.session.add(item)
        conditions[key] = item
    db.session.flush()
    if include_demo is None:
        include_demo = current_app.config.get("SEED_DEMO_DATA", False)
    if not include_demo:
        db.session.commit()
        return
    hospitals = []
    for name, address, city, phone, email, deps, conds, rating, hours, emergency in HOSPITAL_DATA:
        item = db.session.scalar(select(Hospital).where(Hospital.name == name))
        if not item:
            item = Hospital(
                name=name,
                address=address,
                city=city,
                phone=phone,
                email=email,
                rating=rating,
                opening_hours=hours,
                emergency_available=emergency,
                departments_rel=[departments[x] for x in deps],
                conditions_rel=[conditions[x] for x in conds],
            )
            db.session.add(item)
        hospitals.append(item)
    db.session.flush()
    demo_password = os.getenv("DEMO_PASSWORD", "DemoPatient!2026")
    admin_password = os.getenv("ADMIN_BOOTSTRAP_PASSWORD", "ChangeMe!Admin2026")
    patient = db.session.scalar(select(User).where(User.email == "patient@example.com"))
    if not patient:
        patient = User(email="patient@example.com", role=UserRole.PATIENT, email_verified=True)
        patient.set_password(demo_password)
        patient.patient_profile = PatientProfile(
            full_name="Demo Patient",
            date_of_birth=date(1998, 4, 12),
            gender="Other",
            phone="+977 9800000000",
            city="Kathmandu",
            family_contact_name="Rita Sharma",
            family_contact_phone="+977 9800000001",
            family_contact_relationship="Mother",
        )
        db.session.add(patient)
    admin = db.session.scalar(select(User).where(User.email == "admin@smarthealth.com"))
    if not admin:
        admin = User(email="admin@smarthealth.com", role=UserRole.ADMIN, email_verified=True)
        admin.set_password(admin_password)
        db.session.add(admin)
    db.session.flush()
    doctors = []
    for name, email, dep, hospital_index, exp, qual, days, times, fee, bio, rating in DOCTOR_DATA:
        profile = db.session.scalar(select(DoctorProfile).where(DoctorProfile.display_name == name))
        if not profile:
            user = User(email=email, role=UserRole.DOCTOR, email_verified=True)
            user.set_password(demo_password)
            db.session.add(user)
            db.session.flush()
            profile = DoctorProfile(
                user=user,
                display_name=name,
                department=departments[dep],
                hospital=hospitals[hospital_index],
                experience_years=exp,
                qualification=qual,
                available_days=days,
                available_time=times,
                consultation_fee=fee,
                bio=bio,
                rating=rating,
                is_verified=True,
                license_number=f"DEMO-{len(doctors) + 1001}",
                sms_phone="+977 9800000002",
            )
            db.session.add(profile)
        doctors.append(profile)
    db.session.flush()
    if not db.session.scalar(select(Appointment).limit(1)):
        day = date.today() + timedelta(days=2)
        slot = AppointmentSlot(
            hospital_id=hospitals[4].id,
            doctor_id=doctors[0].id,
            slot_date=day,
            slot_time="10:00 AM",
            booked_count=1,
            capacity=3,
        )
        db.session.add(slot)
        appt = Appointment(
            patient=patient,
            hospital=hospitals[4],
            doctor=doctors[0],
            appointment_date=day,
            appointment_time="10:00 AM",
            disease="Diabetes",
            reason="Review glucose results",
            status=AppointmentStatus.BOOKED,
        )
        appt.payment = Payment(
            method="eSewa",
            amount=doctors[0].consultation_fee,
            provider_reference="DEMO-SEED-001",
            status=PaymentStatus.PAID,
        )
        db.session.add(appt)
    if not db.session.scalar(select(Conversation).limit(1)):
        conversation = Conversation(
            patient=patient, doctor=doctors[0], subject="Unusual thirst", status=ConversationStatus.ANSWERED
        )
        conversation.messages = [
            Message(sender_id=patient.id, sender_role="patient", body="I feel unusually thirsty and tired."),
            Message(
                sender_id=None,
                sender_role="bot",
                body="This may be related to Diabetes. Monitor symptoms and consult a doctor. Educational guidance only.",
            ),
            Message(
                sender_id=doctors[0].user_id,
                sender_role="doctor",
                body="Please bring any recent glucose reports to your appointment.",
            ),
        ]
        db.session.add(conversation)
    if not db.session.scalar(select(ConsentRecord).where(ConsentRecord.user_id == patient.id)):
        db.session.add(
            ConsentRecord(
                user_id=patient.id, consent_type="privacy_and_medical_disclaimer", policy_version="1.0", granted=True
            )
        )
    db.session.commit()
