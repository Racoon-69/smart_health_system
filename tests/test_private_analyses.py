from io import BytesIO

from PIL import Image

from healthcare.extensions import db
from healthcare.models import PatientProfile, PhotoAnalysis, ReportAnalysis, User, UserRole


def test_report_photo_are_private_and_signature_validated(app, patient_client):
    response = patient_client.post(
        "/upload-report", data={"report_text": "HbA1c glucose blood sugar insulin thirst"}, follow_redirects=True
    )
    assert b"Diabetes" in response.data
    image = BytesIO()
    Image.new("RGB", (80, 80), (210, 45, 45)).save(image, "PNG")
    image.seek(0)
    response = patient_client.post(
        "/photo-analysis",
        data={"photo": (image, "skin.png")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert b"Photo support result" in response.data
    with app.app_context():
        report = db.session.scalar(db.select(ReportAnalysis).order_by(ReportAnalysis.id.desc()))
        photo = db.session.scalar(db.select(PhotoAnalysis).order_by(PhotoAnalysis.id.desc()))
        report_id, photo_id = report.public_id, photo.public_id
        other = User(email="privacy-test@example.com", role=UserRole.PATIENT, email_verified=True)
        other.set_password("PrivacyPatient!2026")
        other.patient_profile = PatientProfile(full_name="Privacy Test")
        db.session.add(other)
        db.session.commit()
    patient_client.post("/logout")
    patient_client.post("/login", data={"email": "privacy-test@example.com", "password": "PrivacyPatient!2026"})
    assert patient_client.get(f"/report-result/{report_id}").status_code == 403
    assert patient_client.get(f"/photo-result/{photo_id}").status_code == 403
    assert patient_client.get(f"/private/photo/{photo_id}").status_code == 403


def test_fake_image_rejected(patient_client):
    response = patient_client.post(
        "/photo-analysis",
        data={"photo": (BytesIO(b"not an image"), "fake.png")},
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert b"not a supported image" in response.data
