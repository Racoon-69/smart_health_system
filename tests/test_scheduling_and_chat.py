from datetime import date, timedelta

from healthcare.extensions import db
from healthcare.models import AIConversation, Appointment, AppointmentSlot, LoginActivity, PaymentStatus


def test_booking_duplicate_cancel_and_refund(app, patient_client):
    future = (date.today() + timedelta(days=9)).isoformat()
    payload = {
        "hospital_id": "5",
        "doctor_id": "1",
        "appointment_date": future,
        "appointment_time": "09:00 AM",
        "disease": "Diabetes",
        "reason": "Automated test booking",
        "payment_method": "eSewa",
        "transaction_id": "TEST-001",
    }
    response = patient_client.post("/book-appointment", data=payload, follow_redirects=True)
    assert b"Appointment booked" in response.data
    response = patient_client.post("/book-appointment", data=payload, follow_redirects=True)
    assert b"already have an active appointment" in response.data
    with app.app_context():
        appointment = db.session.scalar(db.select(Appointment).where(Appointment.reason == "Automated test booking"))
        public_id = appointment.public_id
    response = patient_client.post(f"/cancel-appointment/{public_id}", follow_redirects=True)
    assert b"capacity released" in response.data
    with app.app_context():
        appointment = db.session.scalar(db.select(Appointment).where(Appointment.public_id == public_id))
        slot = db.session.scalar(
            db.select(AppointmentSlot).where(
                AppointmentSlot.slot_date == date.fromisoformat(future), AppointmentSlot.slot_time == "09:00 AM"
            )
        )
        assert appointment.payment.status == PaymentStatus.REFUNDED
        assert slot.booked_count == 0


def test_emergency_bot_language(patient_client):
    response = patient_client.post(
        "/chat", data={"doctor_id": "1", "message": "chest pain and difficulty breathing"}, follow_redirects=True
    )
    assert b"urgent medical attention" in response.data
    assert b"definitely have" not in response.data


def test_ai_chat_is_persisted_separately(app, patient_client):
    response = patient_client.post("/ai-chat", data={"message": "How can I prepare for a doctor visit?"})
    assert response.status_code == 302
    with app.app_context():
        conversation = db.session.scalar(db.select(AIConversation))
        assert conversation is not None
        assert [message.sender_role for message in conversation.messages] == ["patient", "ai"]


def test_ai_chat_can_accept_a_text_report(app, patient_client):
    from io import BytesIO

    response = patient_client.post(
        "/ai-chat",
        data={
            "message": "What should I ask my doctor?",
            "report_file": (BytesIO(b"Fasting blood glucose 152 mg/dL"), "lab-report.txt"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 302
    with app.app_context():
        conversation = db.session.scalar(
            db.select(AIConversation).where(AIConversation.report_analysis_id.is_not(None))
        )
        assert conversation.report_analysis.original_filename == "lab-report.txt"
        assert "educational feedback" in conversation.messages[-1].body


def test_login_activity_is_saved(app, client):
    response = client.post("/login", data={"email": "patient@example.com", "password": "DemoPatient!2026"})
    assert response.status_code == 302
    with app.app_context():
        activity = db.session.scalar(db.select(LoginActivity).where(LoginActivity.succeeded.is_(True)))
        assert activity.email == "patient@example.com"


def test_slot_api_rejects_bad_input(client):
    assert client.get("/api/check-slots?hospital_id=x").status_code == 400
