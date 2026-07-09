from __future__ import annotations

import pytest

from healthcare import create_app


@pytest.fixture(scope="session")
def app(tmp_path_factory):
    upload_root = tmp_path_factory.mktemp("private_uploads")
    app = create_app("testing", {"PRIVATE_UPLOAD_ROOT": str(upload_root)})
    yield app


@pytest.fixture()
def client(app):
    client = app.test_client()
    yield client
    client.post("/logout")


@pytest.fixture()
def patient_client(client):
    response = client.post(
        "/login", data={"email": "patient@example.com", "password": "DemoPatient!2026"}, follow_redirects=True
    )
    assert response.status_code == 200
    return client
