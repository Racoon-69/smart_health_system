from healthcare import create_app
from healthcare.extensions import db
from healthcare.models import User


def test_security_headers_and_protected_dashboard(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Send alert now" in response.data or b"Sign in to alert" in response.data
    assert b"/symptom-checker" in response.data
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


def test_registration_minimum_password_length(client):
    res_short = client.post(
        "/register",
        data={
            "full_name": "Test User",
            "email": "shortpass@example.com",
            "password": "1234567",
            "confirm_password": "1234567",
            "accept_terms": "y",
        },
    )
    assert b"Field must be between 8 and 128 characters long." in res_short.data

    res_valid = client.post(
        "/register",
        data={
            "full_name": "Test User",
            "email": "validpass@example.com",
            "password": "12345678",
            "confirm_password": "12345678",
            "accept_terms": "y",
        },
        follow_redirects=True,
    )
    assert b"Your private patient account is ready." in res_valid.data


def test_patient_logout_clears_session_and_redirects_to_login(app, client):
    # Perform login
    client.post("/login", data={"email": "patient@example.com", "password": "DemoPatient!2026"})
    
    # Verify user is authenticated
    dashboard_res = client.get("/dashboard")
    assert dashboard_res.status_code == 200

    # Perform logout
    logout_res = client.post("/logout", follow_redirects=True)
    assert logout_res.status_code == 200
    assert b"You have been signed out securely." in logout_res.data
    assert b"Patient Sign In" in logout_res.data

    # Verify protected route now redirects to login
    protected_res = client.get("/dashboard")
    assert protected_res.status_code == 302
    assert "/login" in protected_res.location

    # Verify UserSession is_active is False in DB
    with app.app_context():
        from healthcare.models import UserSession, User
        user = db.session.scalar(db.select(User).where(User.email == "patient@example.com"))
        session_rec = db.session.scalar(db.select(UserSession).where(UserSession.user_id == user.id))
        if session_rec:
            assert session_rec.is_active is False

