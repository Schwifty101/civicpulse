VALID_PAYLOAD = {
    "text": "Streetlight has been broken for a week, area is very dark at night.",
    "location": "Sector I-8, Islamabad",
}


def test_stats_cache_hit_then_invalidated_on_write(client):
    first = client.get("/api/stats")
    assert first.headers["X-Cache"] == "MISS"

    second = client.get("/api/stats")
    assert second.headers["X-Cache"] == "HIT"

    client.post("/api/complaints", json=VALID_PAYLOAD)

    third = client.get("/api/stats")
    assert third.headers["X-Cache"] == "MISS"  # invalidated by the write, not left to expire


def test_stats_reflects_new_complaint_immediately(client):
    client.post("/api/complaints", json=VALID_PAYLOAD)
    body = client.get("/api/stats").json()
    assert body["total"] >= 1
