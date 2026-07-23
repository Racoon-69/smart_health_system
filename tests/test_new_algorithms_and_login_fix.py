import pytest
from utils.health_rules import analyze_text
from utils.hospital_matcher import recommend_hospitals_content_based, recommend_doctors_content_based
from utils.chatbot import bot_reply
from utils.appointment_utils import check_slot
from utils.photo_analyzer import analyze_photo


def test_login_without_user_agent_header_does_not_500(client):
    """Ensure POST /login handles requests missing User-Agent without a 500 Internal Server Error."""
    # Test client sending POST to /login with empty/no User-Agent
    response = client.post(
        "/login",
        data={"email": "patient@example.com", "password": "wrongpassword"},
        headers={"User-Agent": ""},
    )
    assert response.status_code != 500
    assert response.status_code in {200, 302, 400}


def test_login_data_stored_in_relatable_tables(app, client):
    """Verify login data (attempts and active sessions) is stored in relatable database tables."""
    from healthcare.extensions import db
    from healthcare.models import LoginActivity, UserSession, User

    # Perform login attempt
    client.post("/login", data={"email": "patient@example.com", "password": "DemoPatient!2026"})

    with app.app_context():
        # Retrieve user
        user = db.session.scalar(db.select(User).where(User.email == "patient@example.com"))
        assert user is not None

        # Verify relatable LoginActivity table record
        activity = db.session.scalar(db.select(LoginActivity).where(LoginActivity.user_id == user.id))
        assert activity is not None
        assert activity.email == "patient@example.com"
        assert activity.succeeded is True
        assert activity.user.id == user.id

        # Verify relatable UserSession table record
        session_rec = db.session.scalar(db.select(UserSession).where(UserSession.user_id == user.id))
        assert session_rec is not None
        assert session_rec.email_entered == "patient@example.com"
        assert session_rec.user.id == user.id


def test_disease_prediction_random_forest():
    """Verify Disease Prediction uses Random Forest Classifier."""
    res = analyze_text("patient has high blood sugar, thirst, and elevated glucose")
    assert res["model_used"] == "Random Forest Classifier"
    assert res["key"] == "diabetes"
    assert "rf_probability" in res


def test_hospital_and_doctor_content_based_filtering(app):
    """Verify Content-Based Filtering for hospital and doctor recommendations."""
    with app.app_context():
        hospitals = recommend_hospitals_content_based("Cardiology heart blood pressure", "Kathmandu")
        assert isinstance(hospitals, list)
        doctors = recommend_doctors_content_based("Endocrinologist", "")
        assert isinstance(doctors, list)


def test_simple_nlp_chatbot():
    """Verify Simple NLP Chatbot intent recognition and replies."""
    greeting = bot_reply("hello")
    assert "Smart Health Assistant" in greeting

    symptom_reply = bot_reply("I have a severe headache and fever")
    assert "NLP Analysis" in symptom_reply or "URGENT" in symptom_reply


def test_fcfs_appointment_scheduling(app):
    """Verify FCFS (First-Come, First-Served) scheduling metadata."""
    with app.app_context():
        # Check slot info using FCFS rules
        slot_info = check_slot(1, 1, "2026-08-01", "09:00 AM")
        assert slot_info["scheduling_algorithm"] == "First-Come, First-Served (FCFS)"


def test_photo_analyzer_ann_neural_network(tmp_path):
    """Verify Deep Learning Artificial Neural Network (ANN) photo analysis."""
    from PIL import Image
    
    img_path = tmp_path / "test_skin.jpg"
    img = Image.new("RGB", (100, 100), color=(200, 50, 50))
    img.save(img_path)

    result = analyze_photo(img_path)
    assert "Artificial Neural Network" in result["model_architecture"]
    assert "ann_confidence" in result
    assert result["condition"] in [
        "Wound/infection possibility",
        "Skin irritation / rash / allergy",
        "Bruise/dark spot",
        "Normal/unclear",
    ]
