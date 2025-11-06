import subprocess
from pathlib import Path

import json

import app as nets_app


def test_normalize_submission_add_success():
    data = {
        "id": "bravo-net",
        "category": "bhn",
        "name": "Bravo Net",
        "description": "Weekly meetup.",
        "start_local": "13:00",
        "duration_min": "45",
        "rrule": "FREQ=WEEKLY;BYDAY=TU",
        "time_zone": "America/Chicago",
    }

    record, errors = nets_app.normalize_submission(data, ["alpha-net"], "America/New_York")

    assert errors == {}
    assert record["id"] == "bravo-net"
    assert record["duration_min"] == 45
    assert record["time_zone"] == "America/Chicago"
    assert record["mode"] == "add"


def test_normalize_submission_rejects_duplicate_id():
    data = {
        "id": "alpha-net",
        "category": "bhn",
        "name": "Duplicate",
        "description": "Dupe.",
        "start_local": "09:00",
        "duration_min": "30",
        "rrule": "FREQ=WEEKLY;BYDAY=FR",
        "time_zone": "America/New_York",
    }

    record, errors = nets_app.normalize_submission(data, ["alpha-net"], "America/New_York")

    assert record == {}
    assert "id" in errors
    assert "already exists" in errors["id"]


def test_build_json_preview_handles_multiline_and_special_chars():
    record = {
        "id": "gamma-net",
        "category": "general",
        "name": "Gamma Net",
        "description": "Details line 1.\nDetails line 2.",
        "start_local": "18:30",
        "duration_min": 90,
        "rrule": "FREQ=MONTHLY;BYDAY=MO;BYSETPOS=1",
        "time_zone": "Europe/London",
        "optional": {"echolink": "node:1234", "notes": "Line one\nLine two"},
        "custom": [("dtmf_code", "73#")],
    }

    entry = nets_app.record_to_entry(record)
    snippet = nets_app.build_json_preview(entry)
    parsed = json.loads(snippet)

    assert parsed["id"] == "gamma-net"
    assert parsed["description"] == "Details line 1.\nDetails line 2."
    assert parsed["echolink"] == "node:1234"
    assert parsed["notes"] == "Line one\nLine two"
    assert parsed["dtmf_code"] == "73#"


def test_write_pending_file_appends_new_entry(sample_repo):
    record, errors = nets_app.normalize_submission(
        {
            "id": "delta-net",
            "category": "bhn",
            "name": "Delta Net",
            "description": "Delta description.",
            "start_local": "15:00",
            "duration_min": "30",
            "rrule": "FREQ=WEEKLY;BYDAY=WE",
            "time_zone": "America/New_York",
        },
        ["alpha-net"],
        "America/New_York",
    )
    assert not errors
    pending_path = nets_app.write_pending_file(
        nets_app.record_to_entry(record),
        sample_repo["nets_file"],
        sample_repo["root"],
        current_user="tester",
        metadata={"note": "Initial draft"},
    )

    assert pending_path.parent == sample_repo["pending_dir"]
    data = json.loads(pending_path.read_text(encoding="utf-8"))
    assert len(data["nets"]) == 2
    assert any(net["id"] == "delta-net" for net in data["nets"])
    meta = nets_app.load_pending_metadata(nets_app.pending_metadata_path(pending_path))
    assert meta["submitted_by"] == "tester"
    assert meta["note"] == "Initial draft"


def test_promote_pending_file_replaces_nets_file(sample_repo):
    record, errors = nets_app.normalize_submission(
        {
            "id": "echo-net",
            "category": "general",
            "name": "Echo Net",
            "description": "Echo description.",
            "start_local": "19:45",
            "duration_min": "50",
            "rrule": "FREQ=WEEKLY;BYDAY=TH",
            "time_zone": "America/New_York",
        },
        ["alpha-net"],
        "America/New_York",
    )
    assert not errors
    pending_path = nets_app.write_pending_file(
        nets_app.record_to_entry(record),
        sample_repo["nets_file"],
        sample_repo["root"],
        current_user="reviewer",
        metadata={"note": "Ready for publish"},
    )
    meta_path = nets_app.pending_metadata_path(pending_path)
    assert meta_path.exists()

    pending_entries = nets_app.list_pending_files(sample_repo["root"])
    assert len(pending_entries) == 1
    key = pending_entries[0]["key"]

    result = nets_app.promote_pending_file(key, sample_repo["root"], sample_repo["nets_file"], current_user="publisher")

    assert result["message"] == "Pending file promoted"
    nets_data = json.loads(sample_repo["nets_file"].read_text(encoding="utf-8"))
    assert any(net["id"] == "echo-net" for net in nets_data["nets"])

    backups = sorted(sample_repo["root"].glob("nets.backup.*.json"))
    assert backups, "Expected a timestamped backup file"
    assert not pending_path.exists()
    assert not meta_path.exists()


def test_api_save_and_promote_flow(client, sample_repo):
    payload = {
        "id": "foxtrot-net",
        "category": "general",
        "name": "Foxtrot Net",
        "description": "Foxtrot description.",
        "start_local": "20:00",
        "duration_min": "60",
        "rrule": "FREQ=WEEKLY;BYDAY=FR",
        "time_zone": "America/Los_Angeles",
        "submission_note": "QA check",
    }

    response = client.post("/api/save", json=payload, headers={"X-Forwarded-User": "reviewer"})
    assert response.status_code == 200
    body = response.get_json()
    assert body["mode"] == "add"
    assert body["net_id"] == "foxtrot-net"
    assert body["submitted_by"] == "reviewer"
    assert body["submission_note"] == "QA check"

    pending_response = client.get("/api/pending")
    assert pending_response.status_code == 200
    pending_body = pending_response.get_json()
    assert pending_body["pending_files"]
    entry = pending_body["pending_files"][0]
    key = entry["key"]
    assert entry["submitted_by"] == "reviewer"
    assert entry["note"] == "QA check"

    forbidden = client.post(
        "/api/pending/promote",
        json={"key": key},
        headers={"X-Forwarded-User": "reviewer"},
    )
    assert forbidden.status_code == 403

    promote_response = client.post(
        "/api/pending/promote",
        json={"key": key},
        headers={"X-Forwarded-User": "publisher"},
    )
    assert promote_response.status_code == 200
    result = promote_response.get_json()
    assert result["promoted"]
    assert result["user"] == "publisher"

    nets_data = json.loads(sample_repo["nets_file"].read_text(encoding="utf-8"))
    assert any(net["id"] == "foxtrot-net" for net in nets_data["nets"])
    assert not list(sample_repo["pending_dir"].glob("nets.pending.*.json"))


def test_api_promote_commit_flow(client, sample_repo):
    payload = {
        "id": "golf-net",
        "category": "bhn",
        "name": "Golf Net",
        "description": "Golf description.",
        "start_local": "21:00",
        "duration_min": "45",
        "rrule": "FREQ=WEEKLY;BYDAY=SA",
        "time_zone": "America/New_York",
        "submission_note": "Ready for live",
    }

    save_response = client.post("/api/save", json=payload, headers={"X-Forwarded-User": "reviewer"})
    assert save_response.status_code == 200

    pending_response = client.get("/api/pending")
    assert pending_response.status_code == 200
    pending_body = pending_response.get_json()
    assert pending_body["pending_files"]
    key = pending_body["pending_files"][0]["key"]

    promote_response = client.post(
        "/api/pending/promote_commit",
        json={"key": key},
        headers={"X-Forwarded-User": "publisher"},
    )
    assert promote_response.status_code == 200
    body = promote_response.get_json()
    assert body["commit"]["hash"]
    assert body["commit"]["message"].startswith("Publish nets helper")

    nets_data = json.loads(sample_repo["nets_file"].read_text(encoding="utf-8"))
    assert any(net["id"] == "golf-net" for net in nets_data["nets"])

    log = subprocess.run(
        ["git", "log", "--oneline", "-1"],
        cwd=sample_repo["root"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Publish nets helper" in log.stdout

    assert not list(sample_repo["pending_dir"].glob("nets.pending.*.json"))


def test_public_suggest_creates_pending(client, sample_repo):
    payload = {
        "name": "Example Public Net",
        "description": "Public submission description.",
        "category": "bhn",
        "start_local": "19:00",
        "duration_min": "60",
        "rrule": "FREQ=WEEKLY;BYDAY=TU",
        "time_zone": "America/New_York",
        "allstar": "12345",
        "contact_name": "Alice",
        "contact_email": "alice@example.com",
        "additional_info": "Runs on Zoom too.",
    }

    response = client.post(
        "/api/public/suggest",
        json=payload,
        headers={"X-Forwarded-For": "203.0.113.10"},
    )
    assert response.status_code == 202
    body = response.get_json()
    assert body["generated_id"].startswith("example-public-net")

    pending_entries = nets_app.list_pending_files(sample_repo["root"])
    assert len(pending_entries) == 1
    pending_path = Path(pending_entries[0]["path"])
    assert pending_path.exists()
    meta = nets_app.load_pending_metadata(nets_app.pending_metadata_path(pending_path))
    assert meta["submitted_via"] == "public_form"
    assert meta["contact_email"] == "alice@example.com"
    assert "Zoom" in meta.get("note", "")
