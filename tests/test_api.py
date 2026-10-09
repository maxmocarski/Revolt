import pytest
from fastapi.testclient import TestClient

import main

JPEG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"


@pytest.fixture
def client():
    return TestClient(main.app)


@pytest.fixture
def model(monkeypatch):
    """Replace the model server. Set .reply to a dict, or to an exception to raise."""
    class FakeModel:
        reply = {"item": "Kingston RAM", "category": "ram", "text_lines": ["8GB PC4-2666V SODIMM"]}
        calls = []

    async def fake_ollama_json(model_name, prompt_text, images_b64=None):
        FakeModel.calls.append({"model": model_name, "prompt": prompt_text, "images": images_b64})
        if isinstance(FakeModel.reply, Exception):
            raise FakeModel.reply
        return FakeModel.reply

    monkeypatch.setattr(main, "ollama_json", fake_ollama_json)
    FakeModel.calls = []
    return FakeModel


def scan(client, files=None):
    return client.post("/api/scan", files=files or {"file": ("photo.jpg", JPEG, "image/jpeg")})


def test_scan_returns_enriched_result_and_is_counted(client, model):
    before = client.get("/api/analytics").json()["total_scans"]
    response = scan(client)
    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "ram"
    assert body["specs"]["Type"] == "DDR4"
    assert len(model.calls[0]["images"]) == 1
    assert client.get("/api/analytics").json()["total_scans"] == before + 1


def test_model_server_down_gives_503_not_a_made_up_result(client, model):
    model.reply = main.ModelError("Couldn't reach the AI model server.")
    response = scan(client)
    assert response.status_code == 503
    assert response.json()["detail"] == "Couldn't reach the AI model server."


def test_unusable_model_answer_gives_502(client, model):
    model.reply = ["not", "an", "object"]
    assert scan(client).status_code == 502


def test_failed_scans_are_not_counted(client, model):
    before = client.get("/api/analytics").json()["total_scans"]
    model.reply = main.ModelError("down")
    scan(client)
    assert client.get("/api/analytics").json()["total_scans"] == before


def test_upload_checks(client, model, monkeypatch):
    assert scan(client, {"file": ("notes.txt", b"hello", "text/plain")}).status_code == 415
    assert scan(client, {"file": ("empty.jpg", b"", "image/jpeg")}).status_code == 400
    monkeypatch.setattr(main, "MAX_IMAGE_BYTES", 5)
    assert scan(client).status_code == 413


def test_multi_angle_limits(client, model):
    files = [("files", (f"a{i}.jpg", JPEG, "image/jpeg")) for i in range(3)]
    assert client.post("/api/scan-multi", files=files).status_code == 200
    assert len(model.calls[0]["images"]) == 3
    files.append(("files", ("a4.jpg", JPEG, "image/jpeg")))
    assert client.post("/api/scan-multi", files=files).status_code == 400


def test_double_check_sends_only_model_observations(client, model):
    first = scan(client).json()
    model.calls.clear()
    response = client.post("/api/double-check", json=first)
    assert response.status_code == 200
    prompt = model.calls[0]["prompt"]
    assert "Reuse it if it still works" not in prompt          # curated guidance isn't sent for "review"
    assert model.calls[0]["images"] is None


def test_double_check_failure_returns_original_flagged(client, model):
    model.reply = main.ModelError("down")
    data = {"item": "x", "category": "ram", "ai_hazards": []}
    body = client.post("/api/double-check", json=data).json()
    assert body["double_check_failed"] is True
    assert body["item"] == "x"


def test_analytics_merges_old_free_text_categories(client):
    main.log_scan_analytics("old scan", "Memory (RAM)", "single", 0)
    breakdown = client.get("/api/analytics").json()["category_breakdown"]
    assert "Memory (RAM)" not in breakdown
    assert breakdown["RAM (memory)"] >= 1


def test_index_and_vendored_icons_are_served(client):
    assert "ReVolt" in client.get("/").text
    assert client.get("/static/vendor/fontawesome/css/solid.min.css").status_code == 200
    assert client.get("/static/vendor/fontawesome/webfonts/fa-solid-900.woff2").status_code == 200


def test_only_listed_image_types_are_accepted(client, model):
    assert scan(client, {"file": ("photo.png", JPEG, "image/png")}).status_code == 200
    assert scan(client, {"file": ("photo.heic", JPEG, "image/heic")}).status_code == 415


def test_static_files_work_from_any_working_directory(client, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    assert "ReVolt" in client.get("/").text
