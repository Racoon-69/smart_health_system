from healthcare import create_app
from healthcare.extensions import db
from healthcare.models import User


def test_security_headers_and_protected_dashboard(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert client.get("/dashboard").status_code == 302


def test_patient_cannot_open_staff_workspace(patient_client):
    assert patient_client.get("/doctor-admin/dashboard").status_code == 403


def test_admin_can_open_audit_log(client):
    client.post("/login", data={"email": "admin@smarthealth.com", "password": "ChangeMe!Admin2026"})
    assert client.get("/staff/audit-log").status_code == 200


def test_account_lockout_after_failed_attempts(app, client):
    for _ in range(5):
        client.post("/login", data={"email": "asha@smarthealth.com", "password": "wrong-password"})
    with app.app_context():
        user = db.session.scalar(db.select(User).where(User.email == "asha@smarthealth.com"))
        assert user.locked_until is not None


def test_csrf_rejects_unprotected_post(tmp_path):
    app = create_app(
        "testing",
        {
            "AUTO_CREATE_DB": False,
            "WTF_CSRF_ENABLED": True,
            "PRIVATE_UPLOAD_ROOT": str(tmp_path),
        },
    )
    response = app.test_client().post("/login", data={"email": "patient@example.com", "password": "DemoPatient!2026"})
    assert response.status_code == 400
