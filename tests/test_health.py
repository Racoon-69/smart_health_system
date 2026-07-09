def test_health_checks(client):
    assert client.get("/health/live").get_json() == {"status": "ok"}
    assert client.get("/health/ready").get_json() == {"status": "ready"}
