"""
Unit tests for Flask Web Demo (demo/app.py).
"""

import pytest
from demo.app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_index_route(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Autocomplete &amp; Spell Correction" in response.data or b"Autocomplete & Spell Correction" in response.data
    assert b"searchInput" in response.data


def test_suggest_route_prefix(client):
    response = client.get("/suggest?q=data&k=5")
    assert response.status_code == 200
    data = response.get_json()
    assert data["query"] == "data"
    assert "latency_us" in data
    assert len(data["suggestions"]) > 0
    words = [item["word"] for item in data["suggestions"]]
    assert "data" in words or any("data" in w for w in words)


def test_suggest_route_typo_fallback(client):
    response = client.get("/suggest?q=algoritm&k=5")
    assert response.status_code == 200
    data = response.get_json()
    assert data["fell_back"] is True
    assert data["did_you_mean"] == "algorithm"
    assert len(data["corrections"]) >= 1


def test_select_route(client):
    # Check initial frequency
    resp_before = client.get("/suggest?q=algorithm&k=1")
    f_before = resp_before.get_json()["suggestions"][0]["freq"]

    # Select to boost
    resp_select = client.post("/select", json={"word": "algorithm"})
    assert resp_select.status_code == 200
    data = resp_select.get_json()
    assert data["success"] is True
    assert data["word"] == "algorithm"
    assert data["new_freq"] == f_before + 500

    # Missing word parameter
    resp_invalid = client.post("/select", json={})
    assert resp_invalid.status_code == 400


def test_stats_route(client):
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ready"
    assert data["vocabulary_size"] >= 50_000
