def test_health_returns_200_alive(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "alive"


def test_ready_returns_200_when_dependencies_up(client):
    resp = client.get("/ready")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


def test_metrics_exposes_prometheus_text_format(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "civicpulse_http_requests_total" in resp.text


def test_request_id_header_is_propagated(client):
    resp = client.get("/health", headers={"X-Request-ID": "test-request-123"})
    assert resp.headers["X-Request-ID"] == "test-request-123"


def test_request_id_generated_when_absent(client):
    resp = client.get("/health")
    assert resp.headers["X-Request-ID"]
