"""
Flask app that helps trusted editors draft additions to _data/nets.yml.
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import yaml
from flask import Flask, jsonify, render_template, request

BASE_DIR = Path(__file__).resolve().parent

DEFAULT_TIME_ZONES = [
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "America/Phoenix",
    "America/Anchorage",
    "Pacific/Honolulu",
    "Europe/London",
    "Europe/Dublin",
    "Europe/Berlin",
    "Europe/Paris",
    "UTC",
    "Australia/Sydney",
    "Australia/Melbourne",
    "Australia/Brisbane",
    "Australia/Adelaide",
    "Australia/Darwin",
    "Australia/Perth",
    "Australia/Hobart",
]

OPTIONAL_FIELD_KEYS = [
    "location",
    "mode",
    "dmr_system",
    "dmr_tg",
    "allstar",
    "echolink",
    "frequency",
    "DStar",
    "peanut",
    "zoom",
    "notes",
]

ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_\-]*$")
PENDING_NAME_PATTERN = re.compile(r"^nets\.pending\.(\d{8})_(\d{6})\.yml$")


def load_help_texts_file() -> Tuple[Dict[str, str], Dict[str, str]]:
    path = BASE_DIR / "help_texts.json"
    try:
        with path.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except FileNotFoundError:
        return {}, {}
    except json.JSONDecodeError:
        return {}, {}

    help_texts: Dict[str, str] = {}
    help_labels: Dict[str, str] = {}

    if isinstance(raw, dict):
        for key, value in raw.items():
            if not isinstance(value, dict):
                continue
            text = value.get("help")
            label = value.get("label")
            if isinstance(text, str) and text.strip():
                help_texts[key] = text.strip()
            if isinstance(label, str) and label.strip():
                help_labels[key] = label.strip()

    return help_texts, help_labels


HELP_TEXTS, HELP_LABELS = load_help_texts_file()


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.update(load_config())

    @app.get("/")
    def index():
        source_key = request.args.get("source")
        context = load_context(app.config, source_key)
        return render_template("index.html", **context)

    @app.post("/api/preview")
    def api_preview():
        data = request.get_json(force=True, silent=True) or {}
        source_key = data.get("source_key") or request.args.get("source")
        context = load_context(app.config, source_key)
        normalized, errors = normalize_submission(data, context["existing_ids"], context["default_time_zone"])
        if errors:
            return jsonify({"errors": errors}), 400
        snippet = build_yaml_snippet(normalized)
        return jsonify({"snippet": snippet})

    @app.post("/api/save")
    def api_save():
        data = request.get_json(force=True, silent=True) or {}
        source_key = data.get("source_key") or request.args.get("source")
        context = load_context(app.config, source_key)
        normalized, errors = normalize_submission(data, context["existing_ids"], context["default_time_zone"])
        if errors:
            return jsonify({"errors": errors}), 400

        snippet = build_yaml_snippet(normalized)
        pending_path = write_pending_file(
            snippet,
            app.config["NETS_FILE"],
            app.config["OUTPUT_DIR"],
            context["working_file"],
        )

        return jsonify(
            {
                "message": "Pending file created",
                "pending_path": str(pending_path),
                "snippet": snippet,
                "active_source": context["active_source_key"],
            }
        )

    @app.get("/api/pending")
    def api_pending():
        source_key = request.args.get("source")
        context = load_context(app.config, source_key)
        return jsonify(
            {
                "active_source": context["active_source_key"],
                "options": context["source_options"],
                "pending_files": context["pending_files"],
            }
        )

    @app.delete("/api/pending")
    def api_pending_delete():
        payload = request.get_json(force=True, silent=True) or {}
        mode = payload.get("mode")
        output_dir: Path = app.config["OUTPUT_DIR"]

        if mode == "all":
            deleted = delete_all_pending(output_dir)
        elif mode == "single":
            key = payload.get("key")
            if not isinstance(key, str):
                return jsonify({"error": "Specify which pending file to delete."}), 400
            try:
                deleted = delete_single_pending(output_dir, key)
            except FileNotFoundError:
                return jsonify({"error": "Pending file not found."}), 404
        else:
            return jsonify({"error": "Unsupported delete mode."}), 400

        return jsonify({"deleted": deleted})

    return app


def load_config() -> Dict[str, Path]:
    repo_root = BASE_DIR.parent

    nets_env = os.environ.get("BHN_NETS_FILE")
    if nets_env:
        nets_file = Path(nets_env).expanduser()
    else:
        nets_file = repo_root / "_data" / "nets.yml"

    output_env = os.environ.get("BHN_NETS_OUTPUT_DIR")
    if output_env:
        output_dir = Path(output_env).expanduser()
    else:
        output_dir = repo_root / "_data"

    nets_file = nets_file.resolve(strict=False)
    output_dir = output_dir.resolve(strict=False)

    return {
        "NETS_FILE": nets_file,
        "OUTPUT_DIR": output_dir,
    }


def load_context(config: Dict, source_key: Optional[str] = None) -> Dict:
    nets_file: Path = config["NETS_FILE"]
    output_dir: Path = config["OUTPUT_DIR"]
    pending_files = list_pending_files(output_dir)
    pending_file = find_latest_pending_file(output_dir)
    source_map: Dict[str, Path] = {"nets": nets_file}
    for entry in pending_files:
        source_map[entry["key"]] = Path(entry["path"])

    if source_key and source_key in source_map:
        working_file = source_map[source_key]
        active_source_key = source_key
    elif pending_file:
        working_file = pending_file
        active_source_key = f"pending:{pending_file.name}"
    else:
        working_file = nets_file
        active_source_key = "nets"
    default_time_zone = "America/New_York"
    categories: List[str] = []
    existing_ids: List[str] = []

    if working_file.exists():
        try:
            with working_file.open("r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
        except yaml.YAMLError:
            data = {}
        default_time_zone = data.get("time_zone", default_time_zone)
        nets = data.get("nets", []) or []
        for net in nets:
            if isinstance(net, dict):
                cat = net.get("category")
                if cat and cat not in categories:
                    categories.append(cat)
                net_id = net.get("id")
                if net_id:
                    existing_ids.append(str(net_id))

    categories.sort()
    if not categories:
        categories = ["bhn", "disability", "general"]
    time_zones = DEFAULT_TIME_ZONES.copy()
    if default_time_zone not in time_zones:
        time_zones.insert(0, default_time_zone)

    source_options = build_source_options(pending_files, nets_file, active_source_key)

    return {
        "categories": categories,
        "default_time_zone": default_time_zone,
        "existing_ids": existing_ids,
        "time_zones": time_zones,
        "nets_file": working_file,
        "working_file": working_file,
        "pending_file": pending_file,
        "pending_files": pending_files,
        "active_source_key": active_source_key,
        "source_options": source_options,
        "canonical_file": nets_file,
        "pending_context": {
            "has_pending": bool(pending_files),
            "active_source": active_source_key,
            "options": source_options,
        },
        "help_texts": HELP_TEXTS,
        "help_labels": HELP_LABELS,
    }


def find_latest_pending_file(output_dir: Path) -> Optional[Path]:
    pending_dir = output_dir / "pending"
    if not pending_dir.is_dir():
        return None

    candidates = sorted(
        (path for path in pending_dir.glob("nets.pending.*.yml") if path.is_file()),
        key=lambda p: p.name,
        reverse=True,
    )
    if not candidates:
        return None
    return candidates[0]


def list_pending_files(output_dir: Path) -> List[Dict[str, str]]:
    pending_dir = output_dir / "pending"
    if not pending_dir.is_dir():
        return []

    entries: List[Dict[str, str]] = []
    for path in sorted(
        (p for p in pending_dir.glob("nets.pending.*.yml") if p.is_file()),
        key=lambda p: p.name,
        reverse=True,
    ):
        label, iso_timestamp = pending_label_from_name(path.name)
        entries.append(
            {
                "key": f"pending:{path.name}",
                "name": path.name,
                "path": str(path),
                "label": label,
                "created_at": iso_timestamp or "",
            }
        )
    return entries


def pending_label_from_name(filename: str) -> Tuple[str, Optional[str]]:
    match = PENDING_NAME_PATTERN.match(filename)
    if not match:
        return filename, None
    date_part, time_part = match.groups()
    try:
        dt = datetime.strptime(f"{date_part}{time_part}", "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return filename, None
    label = dt.astimezone(timezone.utc).strftime("Created %Y-%m-%d %H:%M:%S UTC")
    return label, dt.isoformat()


def build_source_options(pending_files: List[Dict[str, str]], nets_file: Path, active_key: str) -> List[Dict[str, str]]:
    options: List[Dict[str, str]] = []
    for entry in pending_files:
        options.append(
            {
                "key": entry["key"],
                "label": f"{entry['label']} ({entry['name']})",
                "name": entry["name"],
                "is_pending": True,
                "active": entry["key"] == active_key,
            }
        )

    options.append(
        {
            "key": "nets",
            "label": f"Start fresh from {nets_file.name}",
            "name": nets_file.name,
            "is_pending": False,
            "active": active_key == "nets",
        }
    )
    return options


def delete_all_pending(output_dir: Path) -> List[str]:
    deleted: List[str] = []
    for entry in list_pending_files(output_dir):
        path = Path(entry["path"])
        try:
            path.unlink()
            deleted.append(entry["name"])
        except FileNotFoundError:
            continue
    return deleted


def delete_single_pending(output_dir: Path, key: str) -> List[str]:
    pending_files = {entry["key"]: entry for entry in list_pending_files(output_dir)}
    if key not in pending_files:
        raise FileNotFoundError(key)
    path = Path(pending_files[key]["path"])
    path.unlink()
    return [pending_files[key]["name"]]


def normalize_submission(
    data: Dict,
    existing_ids: Iterable[str],
    default_time_zone: str,
) -> Tuple[Dict, Dict[str, str]]:
    errors: Dict[str, str] = {}

    net_id = (data.get("id") or "").strip()
    existing_lower = {str(e).lower() for e in existing_ids}
    if not net_id:
        errors["id"] = "ID is required."
    elif not ID_PATTERN.match(net_id):
        errors["id"] = "Use letters, numbers, hyphen, or underscore."
    elif net_id.lower() in existing_lower:
        errors["id"] = "This ID already exists (case-insensitive)."

    name = (data.get("name") or "").strip()
    if not name:
        errors["name"] = "Name is required."

    category = (data.get("category") or "").strip()
    new_category = (data.get("newCategory") or "").strip()
    if category == "__new__":
        if not new_category:
            errors["newCategory"] = "Enter the new category name."
        else:
            category = new_category
    if not category:
        errors["category"] = "Choose a category."

    description = sanitize_multiline(data.get("description"))
    if not description:
        errors["description"] = "Description is required."

    start_local = (data.get("start_local") or "").strip()
    if not start_local:
        errors["start_local"] = "Start time is required."
    elif not re.match(r"^\d{2}:\d{2}$", start_local):
        errors["start_local"] = "Use HH:MM format (24-hour)."

    duration = (data.get("duration_min") or "").strip()
    duration_min = None
    if not duration:
        errors["duration_min"] = "Duration is required."
    else:
        try:
            duration_min = int(duration)
            if duration_min <= 0:
                errors["duration_min"] = "Duration must be greater than zero."
        except ValueError:
            errors["duration_min"] = "Duration must be a number."

    rrule = (data.get("rrule") or "").strip()
    if not rrule:
        errors["rrule"] = "RRULE is required."

    time_zone = (data.get("time_zone") or "").strip()
    if time_zone == "__custom__":
        time_zone = (data.get("custom_time_zone") or "").strip()

    optional_fields = {}
    for key in OPTIONAL_FIELD_KEYS:
        value = sanitize_optional(data.get(key))
        if value:
            optional_fields[key] = value

    custom_fields = []
    for entry in data.get("custom_fields", []):
        if not isinstance(entry, dict):
            continue
        key = (entry.get("key") or "").strip()
        value = sanitize_optional(entry.get("value"))
        if key and value:
            if not re.match(r"^[A-Za-z0-9_:\-]+$", key):
                errors.setdefault("custom_fields", "Custom keys may only contain letters, numbers, dash, underscore, or colon.")
                continue
            if key in OPTIONAL_FIELD_KEYS:
                continue
            custom_fields.append((key, value))

    if errors:
        return {}, errors

    record = {
        "id": net_id,
        "category": category,
        "name": name,
        "description": description,
        "start_local": start_local,
        "duration_min": duration_min,
        "rrule": rrule,
        "time_zone": time_zone if time_zone else "",
        "optional": optional_fields,
        "custom": custom_fields,
    }

    if not record["time_zone"] and default_time_zone:
        record["time_zone"] = ""

    return record, {}


def sanitize_optional(value) -> str:
    if value is None:
        return ""
    return sanitize_multiline(value)


def sanitize_multiline(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if "\n" in text:
        text = "\n".join(line.rstrip() for line in text.splitlines())
    return text


def build_yaml_snippet(record: Dict) -> str:
    lines: List[str] = []
    push = lines.append

    push(f"  - id: {quote_value(record['id'])}")
    push(f"    category: {quote_value(record['category'])}")
    push(f"    name: {quote_value(record['name'])}")
    push(f"    description: {quote_value(record['description'])}")

    optional = record.get("optional", {})
    if optional.get("location"):
        push(f"    location: {quote_value(optional['location'])}")

    push(f"    start_local: {quote_value(record['start_local'])}")

    tz = record.get("time_zone")
    if tz:
        push(f"    time_zone: {quote_value(tz)}")

    push(f"    duration_min: {record['duration_min']}")
    push(f"    rrule: {quote_value(record['rrule'])}")

    for key in OPTIONAL_FIELD_KEYS:
        if key in optional and key != "location":
            push(f"    {key}: {quote_value(optional[key])}")

    for key, value in record.get("custom", []):
        push(f"    {key}: {quote_value(value)}")

    snippet = "\n".join(lines)
    return snippet


def quote_value(value: str) -> str:
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if not text:
        return '""'
    escaped = text.replace('"', r"\"")
    if "\n" in escaped:
        indented = "\n      ".join(escaped.split("\n"))
        return f'|\n      {indented}'
    if re.search(r"[:#\[\]{}]", escaped):
        return f'"{escaped}"'
    return f'"{escaped}"'


def write_pending_file(snippet: str, nets_file: Path, output_dir: Path, source_file: Optional[Path] = None) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    pending_dir = output_dir / "pending"
    pending_dir.mkdir(parents=True, exist_ok=True)
    pending_name = f"nets.pending.{timestamp}.yml"
    pending_path = pending_dir / pending_name
    tmp_path = pending_path.with_suffix(pending_path.suffix + ".tmp")

    base_file = source_file or nets_file
    original_text = base_file.read_text(encoding="utf-8")
    if not original_text.endswith("\n"):
        original_text += "\n"

    new_content = f"{original_text.rstrip()}\n\n{snippet}\n"

    with tmp_path.open("w", encoding="utf-8") as fh:
        fh.write(new_content)
    os.replace(tmp_path, pending_path)

    return pending_path


if __name__ == "__main__":
    application = create_app()
    application.run(debug=True)
