from __future__ import annotations

from unittest.mock import Mock, patch

from sqlalchemy import select

from healthcare.extensions import db
from healthcare.models import (
    Conversation,
    DoctorProfile,
    EmergencyAlert,
    EmergencyAlertDelivery,
    EmergencyAlertStatus,
    User,
)
from healthcare.services import send_emergency_sms


def login_patient(client):
    response = client.post(
        "/login", data={"email": "patient@example.com", "password": "DemoPatient!2026"}, follow_redirects=True
    )
    assert response.status_code == 200


def test_emergency_alert_sends_to_doctor_and_family_once(client, app):
    with app.app_context():
        patient = db.session.scalar(select(User).where(User.email == "patient@example.com"))
        doctor = db.session.scalar(select(DoctorProfile).where(DoctorProfile.is_active.is_(True)))
        assert patient and patient.patient_profile and doctor
        patient.patient_profile.family_contact_name = "Rita"
        patient.patient_profile.family_contact_phone = "+977 9800000001"
        patient.patient_profile.family_contact_relationship = "Mother"
        doctor.sms_phone = "+977 9800000002"
        db.session.query(EmergencyAlertDelivery).delete()
        db.session.query(EmergencyAlert).delete()
        db.session.commit()
        doctor_id = doctor.id

    login_patient(client)
    response = client.post(
        "/emergency-alert",
        data={
            "event_id": "fainting-event-1",
            "doctor_id": str(doctor_id),
            "source": "symptom-checker",
            "category": "fainting",
        },
    )
    assert response.status_code == 201
    payload = response.get_json()
    assert payload["status"] == EmergencyAlertStatus.SENT.value
    assert payload["delivered"] == 2

    with app.app_context():
        alert = db.session.scalar(select(EmergencyAlert).where(EmergencyAlert.idempotency_key.like("%fainting-event-1")))
        assert alert and len(alert.deliveries) == 2
        assert {delivery.recipient_type.value for delivery in alert.deliveries} == {"doctor", "family"}

    duplicate = client.post(
        "/emergency-alert",
        data={"event_id": "fainting-event-1", "doctor_id": str(doctor_id)},
    )
    assert duplicate.status_code == 200
    assert duplicate.get_json()["duplicate"] is True


def test_emergency_alert_requires_configured_recipients(client, app):
    with app.app_context():
        patient = db.session.scalar(select(User).where(User.email == "patient@example.com"))
        doctor = db.session.scalar(select(DoctorProfile).where(DoctorProfile.is_active.is_(True)))
        assert patient and patient.patient_profile and doctor
        patient.patient_profile.family_contact_phone = None
        doctor.sms_phone = None
        db.session.commit()
        doctor_id = doctor.id

    login_patient(client)
    response = client.post(
        "/emergency-alert", data={"event_id": "missing-contact-event", "doctor_id": str(doctor_id)}
    )
    assert response.status_code == 400
    assert "Configure both" in response.get_json()["error"]


def test_twilio_provider_sends_live_sms_request(app):
    provider_message = Mock(sid="SM123")
    provider_client = Mock()
    provider_client.messages.create.return_value = provider_message
    with app.app_context(), patch("healthcare.services.Client", return_value=provider_client) as client_factory:
        app.config.update(
            SMS_ENABLED=True,
            SMS_PROVIDER="twilio",
            SMS_FROM="+15551234567",
            TWILIO_ACCOUNT_SID="AC123",
            TWILIO_AUTH_TOKEN="token",
        )
        result = send_emergency_sms(
            phone="+977 9800000001",
            recipient_name="Rita",
            patient_name="Patient",
            category="fainting",
        )

    assert result["status"] == "sent"
    assert result["provider_message_id"] == "SM123"
    client_factory.assert_called_once_with("AC123", "token")
    provider_client.messages.create.assert_called_once_with(
        body="Smart Health urgent alert (fainting): Patient may need immediate assistance. "
        "Please contact them and local emergency services.",
        from_="+15551234567",
        to="+9779800000001",
    )


def test_home_button_sends_immediately_using_latest_doctor(client, app):
    app.config.update(SMS_ENABLED=True, SMS_PROVIDER="mock")
    with app.app_context():
        patient = db.session.scalar(select(User).where(User.email == "patient@example.com"))
        doctor = db.session.scalar(select(DoctorProfile).where(DoctorProfile.is_active.is_(True)))
        assert patient and patient.patient_profile and doctor
        patient.patient_profile.family_contact_phone = "+977 9800000001"
        doctor.sms_phone = "+977 9800000002"
        db.session.query(EmergencyAlertDelivery).delete()
        db.session.query(EmergencyAlert).delete()
        db.session.query(Conversation).delete()
        db.session.add(Conversation(patient_id=patient.id, doctor_id=doctor.id))
        db.session.commit()

    login_patient(client)
    response = client.post(
        "/emergency-alert", data={"source": "home", "category": "manual emergency"}
    )
    assert response.status_code == 201
    assert response.get_json()["delivered"] == 2


def test_critical_report_creates_alert_and_result_guidance(client, app):
    app.config.update(SMS_ENABLED=True, SMS_PROVIDER="mock")
    with app.app_context():
        patient = db.session.scalar(select(User).where(User.email == "patient@example.com"))
        doctor = db.session.scalar(select(DoctorProfile).where(DoctorProfile.is_active.is_(True)))
        assert patient and patient.patient_profile and doctor
        patient.patient_profile.family_contact_phone = "+977 9800000001"
        doctor.sms_phone = "+977 9800000002"
        db.session.query(EmergencyAlertDelivery).delete()
        db.session.query(EmergencyAlert).delete()
        db.session.query(Conversation).delete()
        db.session.add(Conversation(patient_id=patient.id, doctor_id=doctor.id))
        db.session.commit()

    login_patient(client)
    response = client.post("/upload-report", data={"report_text": "chest pain and sweating"})
    assert response.status_code == 302
    with app.app_context():
        alert = db.session.scalar(select(EmergencyAlert).where(EmergencyAlert.source == "critical-report"))
        assert alert and alert.status == EmergencyAlertStatus.SENT
