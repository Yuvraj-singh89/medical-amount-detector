"""
Test FastAPI Endpoints
Tests all API routes (health, individual step endpoints, end-to-end pipeline, and image upload).
"""

import os
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

SAMPLE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "samples")


def test_health_check():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"


def test_api_step1_extract():
    payload = {"text": "Total: INR 1200 | Paid: 1000 | Due: 200 | Discount: 10%"}
    res = client.post("/api/v1/step1-extract", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "raw_tokens" in data
    assert "1200" in data["raw_tokens"]
    assert data["currency_hint"] == "INR"


def test_api_step2_normalize():
    payload = {"raw_tokens": ["1200", "1000", "200", "10%"]}
    res = client.post("/api/v1/step2-normalize", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["normalized_amounts"] == [1200, 1000, 200]


def test_api_step3_classify():
    payload = {
        "normalized_amounts": [1200, 1000, 200],
        "context_text": "Total: INR 1200 | Paid: 1000 | Due: 200"
    }
    res = client.post("/api/v1/step3-classify", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert len(data["amounts"]) == 3
    types = [a["type"] for a in data["amounts"]]
    assert "total_bill" in types
    assert "paid" in types
    assert "due" in types


def test_api_process_text_full():
    payload = {"text": "Total: INR 1200 | Paid: 1000 | Due: 200 | Discount: 10%"}
    res = client.post("/api/v1/process-text", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["currency"] == "INR"
    assert len(data["amounts"]) == 3


def test_api_process_image_clean():
    img_path = os.path.join(SAMPLE_DIR, "sample_clean.png")
    if os.path.exists(img_path):
        with open(img_path, "rb") as f:
            res = client.post(
                "/api/v1/process-image",
                files={"file": ("sample_clean.png", f, "image/png")}
            )
        assert res.status_code == 200
        data = res.json()
        assert data.get("status") in ["ok", "no_amounts_found"]


def test_api_process_image_guardrail():
    img_path = os.path.join(SAMPLE_DIR, "sample_empty.png")
    if os.path.exists(img_path):
        with open(img_path, "rb") as f:
            res = client.post(
                "/api/v1/process-image",
                files={"file": ("sample_empty.png", f, "image/png")}
            )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "no_amounts_found"
