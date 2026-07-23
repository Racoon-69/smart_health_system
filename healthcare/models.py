"""Normalized domain model for patients, care teams, scheduling, and auditability."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from flask_login import UserMixin
from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .extensions import db

password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserRole(str, enum.Enum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    ADMIN = "admin"


class AppointmentStatus(str, enum.Enum):
    BOOKED = "Booked"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"
    NO_SHOW = "No show"


class PaymentStatus(str, enum.Enum):
    PENDING = "Pending"
    PAID = "Paid"
    FAILED = "Failed"
    REFUNDED = "Refunded"


class ConversationStatus(str, enum.Enum):
    OPEN = "Open"
    ANSWERED = "Answered"
    CLOSED = "Closed"


class EmergencyAlertStatus(str, enum.Enum):
    PENDING = "Pending"
    SENT = "Sent"
    PARTIAL = "Partial"
    FAILED = "Failed"


class AlertRecipientType(str, enum.Enum):
    DOCTOR = "doctor"
    FAMILY = "family"


hospital_departments = Table(
    "hospital_departments",
    db.metadata,
    db.Column("hospital_id", ForeignKey("hospitals.id", ondelete="CASCADE"), primary_key=True),
    db.Column("department_id", ForeignKey("departments.id", ondelete="CASCADE"), primary_key=True),
)
hospital_conditions = Table(
    "hospital_conditions",
    db.metadata,
    db.Column("hospital_id", ForeignKey("hospitals.id", ondelete="CASCADE"), primary_key=True),
    db.Column("condition_id", ForeignKey("conditions.id", ondelete="CASCADE"), primary_key=True),
)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class User(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid.uuid4()), index=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, length=20), default=UserRole.PATIENT, index=True
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    email_verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    failed_login_count: Mapped[int] = mapped_column(default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    patient_profile: Mapped["PatientProfile | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    doctor_profile: Mapped["DoctorProfile | None"] = relationship(back_populates="user", uselist=False)
    ai_conversations: Mapped[list["AIConversation"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    login_activities: Mapped[list["LoginActivity"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    user_sessions: Mapped[list["UserSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def set_password(self, password: str) -> None:
        self.password_hash = password_hasher.hash(password)

    def check_password(self, password: str) -> bool:
        try:
            valid = password_hasher.verify(self.password_hash, password)
            if valid and password_hasher.check_needs_rehash(self.password_hash):
                self.set_password(password)
            return valid
        except (VerifyMismatchError, InvalidHashError):
            return False

    @property
    def name(self) -> str:
        if self.patient_profile:
            return self.patient_profile.full_name
        if self.doctor_profile:
            return self.doctor_profile.display_name
        return self.email.split("@", 1)[0]


class PatientProfile(TimestampMixin, db.Model):
    __tablename__ = "patient_profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    gender: Mapped[str | None] = mapped_column(String(40))
    phone: Mapped[str | None] = mapped_column(String(30))
    city: Mapped[str | None] = mapped_column(String(80))
    emergency_contact: Mapped[str | None] = mapped_column(String(120))
    family_contact_name: Mapped[str | None] = mapped_column(String(120))
    family_contact_phone: Mapped[str | None] = mapped_column(String(30))
    family_contact_relationship: Mapped[str | None] = mapped_column(String(60))
    medical_conditions: Mapped[str | None] = mapped_column(Text)
    allergies: Mapped[str | None] = mapped_column(Text)
    current_medications: Mapped[str | None] = mapped_column(Text)
    user: Mapped[User] = relationship(back_populates="patient_profile")

    @property
    def age(self) -> int | None:
        if not self.date_of_birth:
            return None
        today = date.today()
        return (
            today.year
            - self.date_of_birth.year
            - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        )


class Department(TimestampMixin, db.Model):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)


class Condition(TimestampMixin, db.Model):
    __tablename__ = "conditions"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    specialist_title: Mapped[str | None] = mapped_column(String(100))
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"))
    department: Mapped[Department | None] = relationship()


class Hospital(TimestampMixin, db.Model):
    __tablename__ = "hospitals"
    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid.uuid4()), index=True)
    name: Mapped[str] = mapped_column(String(180), unique=True, nullable=False)
    address: Mapped[str] = mapped_column(String(250), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(254))
    rating: Mapped[Decimal] = mapped_column(Numeric(2, 1), default=Decimal("4.0"))
    opening_hours: Mapped[str | None] = mapped_column(String(120))
    emergency_available: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False, index=True)
    departments_rel: Mapped[list[Department]] = relationship(secondary=hospital_departments, lazy="selectin")
    conditions_rel: Mapped[list[Condition]] = relationship(secondary=hospital_conditions, lazy="selectin")
    doctors: Mapped[list["DoctorProfile"]] = relationship(back_populates="hospital")

    @property
    def departments(self) -> str:
        return ", ".join(item.name for item in self.departments_rel)

    @property
    def diseases_treated(self) -> str:
        return ", ".join(item.name for item in self.conditions_rel)


class DoctorProfile(TimestampMixin, db.Model):
    __tablename__ = "doctor_profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), unique=True)
    display_name: Mapped[str] = mapped_column(String(140), nullable=False)
    hospital_id: Mapped[int] = mapped_column(ForeignKey("hospitals.id"), nullable=False, index=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), nullable=False, index=True)
    experience_years: Mapped[int] = mapped_column(default=0)
    qualification: Mapped[str | None] = mapped_column(String(200))
    sms_phone: Mapped[str | None] = mapped_column(String(30))
    available_days: Mapped[str | None] = mapped_column(String(100))
    available_time: Mapped[str | None] = mapped_column(String(100))
    consultation_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    bio: Mapped[str | None] = mapped_column(Text)
    rating: Mapped[Decimal] = mapped_column(Numeric(2, 1), default=Decimal("4.0"))
    license_number: Mapped[str | None] = mapped_column(String(100), unique=True)
    is_verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    user: Mapped[User | None] = relationship(back_populates="doctor_profile")
    hospital: Mapped[Hospital] = relationship(back_populates="doctors")
    department: Mapped[Department] = relationship()

    @property
    def name(self) -> str:
        return self.display_name

    @property
    def specialty(self) -> str:
        return self.department.name

    @property
    def experience(self) -> int:
        return self.experience_years

    @property
    def hospital_name(self) -> str:
        return self.hospital.name


class AppointmentSlot(TimestampMixin, db.Model):
    __tablename__ = "appointment_slots"
    __table_args__ = (
        UniqueConstraint("hospital_id", "doctor_id", "slot_date", "slot_time", name="uq_slot_identity"),
        CheckConstraint("booked_count >= 0 AND booked_count <= capacity", name="ck_slot_capacity"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    hospital_id: Mapped[int] = mapped_column(ForeignKey("hospitals.id"), nullable=False)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctor_profiles.id"), nullable=False)
    slot_date: Mapped[date] = mapped_column(Date, nullable=False)
    slot_time: Mapped[str] = mapped_column(String(20), nullable=False)
    capacity: Mapped[int] = mapped_column(default=3, nullable=False)
    booked_count: Mapped[int] = mapped_column(default=0, nullable=False)


class Appointment(TimestampMixin, db.Model):
    __tablename__ = "appointments"
    __table_args__ = (
        Index("ix_appointment_schedule", "hospital_id", "doctor_id", "appointment_date", "appointment_time"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid.uuid4()), index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    hospital_id: Mapped[int] = mapped_column(ForeignKey("hospitals.id"), nullable=False)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctor_profiles.id"), nullable=False, index=True)
    appointment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    appointment_time: Mapped[str] = mapped_column(String(20), nullable=False)
    disease: Mapped[str] = mapped_column(String(180), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus, native_enum=False, length=30), default=AppointmentStatus.BOOKED, index=True
    )
    cancellation_reason: Mapped[str | None] = mapped_column(String(500))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    patient: Mapped[User] = relationship(foreign_keys=[patient_id])
    hospital: Mapped[Hospital] = relationship()
    doctor: Mapped[DoctorProfile] = relationship()
    payment: Mapped["Payment | None"] = relationship(
        back_populates="appointment", cascade="all, delete-orphan", uselist=False
    )

    @property
    def patient_name(self) -> str:
        return self.patient.name

    @property
    def age(self) -> int | None:
        return self.patient.patient_profile.age if self.patient.patient_profile else None

    @property
    def gender(self) -> str:
        return self.patient.patient_profile.gender if self.patient.patient_profile else ""

    @property
    def phone(self) -> str:
        return self.patient.patient_profile.phone if self.patient.patient_profile else ""

    @property
    def email(self) -> str:
        return self.patient.email

    @property
    def hospital_name(self) -> str:
        return self.hospital.name

    @property
    def doctor_name(self) -> str:
        return self.doctor.name

    @property
    def specialty(self) -> str:
        return self.doctor.specialty

    @property
    def payment_status(self) -> str:
        return self.payment.status.value if self.payment else "Pending"

    @property
    def payment_method(self) -> str:
        return self.payment.method if self.payment else ""

    @property
    def amount(self):
        return self.payment.amount if self.payment else 0


class Payment(TimestampMixin, db.Model):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid.uuid4()))
    appointment_id: Mapped[int] = mapped_column(
        ForeignKey("appointments.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    method: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    provider_reference: Mapped[str | None] = mapped_column(String(150))
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, native_enum=False, length=30), default=PaymentStatus.PENDING, index=True
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    appointment: Mapped[Appointment] = relationship(back_populates="payment")

    @property
    def transaction_id(self) -> str | None:
        return self.provider_reference


class ReportAnalysis(TimestampMixin, db.Model):
    __tablename__ = "report_analyses"
    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid.uuid4()), index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    original_filename: Mapped[str | None] = mapped_column(String(255))
    storage_key: Mapped[str | None] = mapped_column(String(100), unique=True)
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False)
    detected_condition: Mapped[str] = mapped_column(String(120), nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False)
    matched_keywords: Mapped[list] = mapped_column(db.JSON, default=list)
    result_payload: Mapped[dict] = mapped_column(db.JSON, nullable=False)
    patient: Mapped[User] = relationship()

    @property
    def patient_name(self) -> str:
        return self.patient.name

    @property
    def filename(self) -> str:
        return self.original_filename or "Manual entry"

    @property
    def keywords(self) -> str:
        return ", ".join(self.matched_keywords or [])

    @property
    def recommendation(self) -> dict:
        return self.result_payload


class PhotoAnalysis(TimestampMixin, db.Model):
    __tablename__ = "photo_analyses"
    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid.uuid4()), index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    observations: Mapped[list] = mapped_column(db.JSON, default=list)
    detected_condition: Mapped[str] = mapped_column(String(150), nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    redness: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    dark_spots: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    patient: Mapped[User] = relationship()

    @property
    def patient_name(self) -> str:
        return self.patient.name

    @property
    def filename(self) -> str:
        return self.original_filename


class Conversation(TimestampMixin, db.Model):
    __tablename__ = "conversations"
    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid.uuid4()), index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctor_profiles.id"), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(180), default="Health question")
    status: Mapped[ConversationStatus] = mapped_column(
        Enum(ConversationStatus, native_enum=False, length=30), default=ConversationStatus.OPEN, index=True
    )
    patient: Mapped[User] = relationship(foreign_keys=[patient_id])
    doctor: Mapped[DoctorProfile] = relationship()
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )


class Message(TimestampMixin, db.Model):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sender_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    sender_role: Mapped[str] = mapped_column(String(20), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    conversation: Mapped[Conversation] = relationship(back_populates="messages")
    sender: Mapped[User | None] = relationship()


class AIConversation(TimestampMixin, db.Model):
    """A patient-owned conversation with the educational AI assistant."""

    __tablename__ = "ai_conversations"
    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid.uuid4()), index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    report_analysis_id: Mapped[int | None] = mapped_column(ForeignKey("report_analyses.id", ondelete="SET NULL"))
    title: Mapped[str] = mapped_column(String(180), default="Health question", nullable=False)
    patient: Mapped[User] = relationship(back_populates="ai_conversations")
    report_analysis: Mapped["ReportAnalysis | None"] = relationship()
    messages: Mapped[list["AIMessage"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="AIMessage.created_at"
    )


class AIMessage(TimestampMixin, db.Model):
    __tablename__ = "ai_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("ai_conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sender_role: Mapped[str] = mapped_column(String(20), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    conversation: Mapped[AIConversation] = relationship(back_populates="messages")


class EmergencyAlert(TimestampMixin, db.Model):
    __tablename__ = "emergency_alerts"
    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid.uuid4()), index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctor_profiles.id"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    category: Mapped[str | None] = mapped_column(String(80))
    idempotency_key: Mapped[str] = mapped_column(String(140), unique=True, nullable=False)
    status: Mapped[EmergencyAlertStatus] = mapped_column(
        Enum(EmergencyAlertStatus, native_enum=False, length=20), default=EmergencyAlertStatus.PENDING, nullable=False
    )
    patient: Mapped[User] = relationship()
    doctor: Mapped[DoctorProfile] = relationship()
    deliveries: Mapped[list["EmergencyAlertDelivery"]] = relationship(
        back_populates="alert", cascade="all, delete-orphan", order_by="EmergencyAlertDelivery.id"
    )


class EmergencyAlertDelivery(TimestampMixin, db.Model):
    __tablename__ = "emergency_alert_deliveries"
    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("emergency_alerts.id", ondelete="CASCADE"), nullable=False, index=True)
    recipient_type: Mapped[AlertRecipientType] = mapped_column(
        Enum(AlertRecipientType, native_enum=False, length=20), nullable=False
    )
    recipient_name: Mapped[str] = mapped_column(String(120), nullable=False)
    recipient_phone: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[EmergencyAlertStatus] = mapped_column(
        Enum(EmergencyAlertStatus, native_enum=False, length=20), default=EmergencyAlertStatus.PENDING, nullable=False
    )
    provider_message_id: Mapped[str | None] = mapped_column(String(150))
    error_message: Mapped[str | None] = mapped_column(String(300))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    alert: Mapped[EmergencyAlert] = relationship(back_populates="deliveries")


class LoginActivity(db.Model):
    """Auditable sign-in outcome record; passwords are never stored here."""

    __tablename__ = "login_activities"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    email: Mapped[str] = mapped_column(String(254), nullable=False, index=True)
    succeeded: Mapped[bool] = mapped_column(nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(300))
    user: Mapped[User | None] = relationship(back_populates="login_activities")


class UserSession(TimestampMixin, db.Model):
    """Active user session details recorded during successful login."""

    __tablename__ = "user_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_token: Mapped[str] = mapped_column(String(64), unique=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    email_entered: Mapped[str] = mapped_column(String(254), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(300))
    logged_in_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    user: Mapped[User] = relationship(back_populates="user_sessions")


class ConsentRecord(TimestampMixin, db.Model):
    __tablename__ = "consent_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    consent_type: Mapped[str] = mapped_column(String(80), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(30), nullable=False)
    granted: Mapped[bool] = mapped_column(nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user: Mapped[User] = relationship()


class AuditEvent(db.Model):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(80))
    outcome: Mapped[str] = mapped_column(String(30), default="success")
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(300))
    details: Mapped[dict] = mapped_column(db.JSON, default=dict)
    actor: Mapped[User | None] = relationship()
