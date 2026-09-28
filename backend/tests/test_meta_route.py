VALID_PAYLOAD = {
    "text": "Garbage has not been collected in our street for over a week now.",
    "location": "Liaquatabad, Karachi",
}


def test_providers_reports_active_provider(client):
    body = client.get("/api/meta/providers").json()
    assert body["active_provider"] == "simulated"
    assert "triage_cache_hit_rate" in body


def test_providers_records_recent_outcomes(client):
    client.post("/api/complaints", json=VALID_PAYLOAD)
    body = client.get("/api/meta/providers").json()
    assert len(body["recent_outcomes"]) >= 1
    assert body["recent_outcomes"][0]["provider"]


def test_providers_outcomes_capped_at_20(client):
    for _ in range(25):
        client.post(
            "/api/complaints",
            json={**VALID_PAYLOAD, "location": f"Street {_}"},
        )
    body = client.get("/api/meta/providers").json()
    assert len(body["recent_outcomes"]) <= 20
