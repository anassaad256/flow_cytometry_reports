"""Tests for the FastAPI endpoints."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api import app
from tests.conftest import make_adequate_acute_input


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_panels(client):
    resp = client.get("/api/panels")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_panel_schema(client):
    resp = client.get("/api/panel/PANEL_ACUTE_LEUKEMIA/schema")
    assert resp.status_code == 200
    data = resp.json()
    assert data["panel_id"] == "PANEL_ACUTE_LEUKEMIA"


def test_panel_schema_not_found(client):
    resp = client.get("/api/panel/NONEXISTENT/schema")
    assert resp.status_code == 404


def test_enums(client):
    resp = client.get("/api/enums")
    assert resp.status_code == 200
    data = resp.json()
    assert "marker_states" in data


def test_generate_adequate(client):
    case_dict = make_adequate_acute_input()
    resp = client.post("/api/generate", json=case_dict)
    assert resp.status_code == 200
    data = resp.json()
    assert "general" in data
    assert "main_line" in data
    assert "comment" in data
    assert len(data["comment"]) > 0, "Comment lines must be populated"


def test_generate_inadequate(client):
    case_dict = {
        "specimen_type": "Bone marrow aspirate",
        "clinical_data": "AML",
        "adequacy_status": "ADEQUACY_INADEQUATE",
        "inadequate_reason": "INADEQUATE_LOW_CELLULAR_EVENTS",
    }
    resp = client.post("/api/generate", json=case_dict)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["main_line"]) >= 1
