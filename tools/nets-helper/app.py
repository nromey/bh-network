"""
Flask app that helps trusted editors draft additions to _data/nets.yml.
"""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
import json
import hashlib
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

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

BASE_FIELD_KEYS = [
    "id",
    "category",
    "name",
    "description",
    "start_local",
    "duration_min",
    "rrule",
    "time_zone",
]

CONNECTION_FIELD_MAP = {
    "allstar": ["allstar"],
    "echolink": ["echolink"],
    "dmr": ["dmr_system", "dmr_tg"],
    "dstar": ["DStar"],
    "hf": ["frequency", "mode"],
}

ENTRY_BLOCK_TEMPLATE = r"(?ms)^  - id:\s*{id}\s*\n(?:^(?!  - id:).*[\r]?\n?)*"


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


def load_roles_file(path: Path) -> Dict[str, set]:
    try:
        with path.open("r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
    except FileNotFoundError:
        return {}
    except yaml.YAMLError:
        return {}

    roles: Dict[str, set] = {}
    if isinstance(raw, dict):
        for role, users in raw.items():
            if not isinstance(role, str):
                continue
            if isinstance(users, list):
                roles[role] = {str(u) for u in users if isinstance(u, str)}
    return roles


def determine_user_roles(roles_data: Dict[str, Iterable[str]], user: Optional[str]) -> set:
    if not user:
        return set()
    user_roles = set()
    for role, members in roles_data.items():
        if isinstance(members, Iterable) and user in members:
            user_roles.add(role)
    return user_roles


def user_can_promote(roles_data: Dict[str, Iterable[str]], user: Optional[str]) -> bool:
    return "publishers" in determine_user_roles(roles_data, user)


def get_current_user(app: Flask) -> Optional[str]:
    forwarded = request.headers.get("X-Forwarded-User")
    if forwarded:
        return forwarded.strip()
    environ_user = request.environ.get("REMOTE_USER")
    if environ_user:
        return str(environ_user).strip()
    default_user = app.config.get("DEFAULT_USER", "")
    return default_user or None


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.update(load_config())
    app.config["ROLES_DATA"] = load_roles_file(app.config["ROLES_FILE"])

    @app.get("/")
    def index():
        source_key = request.args.get("source")
        current_user = get_current_user(app)
        context = load_context(app.config, source_key, current_user)
        return render_template("index.html", **context)

    @app.post("/api/preview")
    def api_preview():
        data = request.get_json(force=True, silent=True) or {}
        source_key = data.get("source_key") or request.args.get("source")
        current_user = get_current_user(app)
        context = load_context(app.config, source_key, current_user)
        normalized, errors = normalize_submission(data, context["existing_ids"], context["default_time_zone"])
        if errors:
            return jsonify({"errors": errors}), 400
        snippet = build_yaml_snippet(normalized)
        return jsonify({"snippet": snippet})

    @app.post("/api/save")
    def api_save():
        data = request.get_json(force=True, silent=True) or {}
        source_key = data.get("source_key") or request.args.get("source")
        current_user = get_current_user(app)
        context = load_context(app.config, source_key, current_user)
        normalized, errors = normalize_submission(data, context["existing_ids"], context["default_time_zone"])
        if errors:
            return jsonify({"errors": errors}), 400

        mode = (data.get("mode") or "add").strip().lower()
        original_id = (data.get("original_id") or "").strip()
        source_hash = (data.get("source_hash") or "").strip()
        snippet = build_yaml_snippet(normalized)
        try:
            pending_path = write_pending_file(
                snippet,
                app.config["NETS_FILE"],
                app.config["OUTPUT_DIR"],
                context["working_file"],
                mode=mode,
                original_id=original_id,
                expected_hash=source_hash,
            )
        except ValueError as exc:
            message = str(exc)
            return jsonify({"errors": {"conflict": message, "original_id": message}}), 409

        return jsonify(
            {
                "message": "Pending file created",
                "pending_path": str(pending_path),
                "snippet": snippet,
                "active_source": context["active_source_key"],
                "mode": mode,
                "net_id": normalized["id"],
                "original_id": original_id,
            }
        )

    @app.get("/api/pending")
    def api_pending():
        source_key = request.args.get("source")
        current_user = get_current_user(app)
        context = load_context(app.config, source_key, current_user)
        summaries = summarize_pending_files(context["pending_files"], context["canonical_file"])
        return jsonify(
            {
                "active_source": context["active_source_key"],
                "options": context["source_options"],
                "pending_files": summaries,
                "permissions": context["permissions"],
                "user": context["current_user"],
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

    @app.post("/api/pending/promote")
    def api_pending_promote():
        current_user = get_current_user(app)
        if not user_can_promote(app.config["ROLES_DATA"], current_user):
            return jsonify({"error": "You do not have permission to promote pending files."}), 403

        payload = request.get_json(force=True, silent=True) or {}
        key = payload.get("key")
        if not isinstance(key, str):
            return jsonify({"error": "Specify which pending file to promote."}), 400

        try:
            result = promote_pending_file(
                key,
                app.config["OUTPUT_DIR"],
                app.config["NETS_FILE"],
                current_user=current_user,
            )
        except FileNotFoundError:
            return jsonify({"error": "Pending file not found."}), 404
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        return jsonify(result)

    @app.get("/api/nets")
    def api_nets():
        source_key = request.args.get("source")
        current_user = get_current_user(app)
        context = load_context(app.config, source_key, current_user)
        nets_summary = build_nets_summary(context["nets_data"])
        return jsonify(
            {
                "nets": nets_summary,
                "active_source": context["active_source_key"],
                "permissions": context["permissions"],
                "user": context["current_user"],
            }
        )

    @app.get("/api/nets/<net_id>")
    def api_net_detail(net_id: str):
        source_key = request.args.get("source")
        current_user = get_current_user(app)
        context = load_context(app.config, source_key, current_user)
        target_net, actual_id = find_net_by_id(context["nets_data"], net_id)
        if not target_net:
            return jsonify({"error": "Net not found in the current snapshot."}), 404

        form_state = build_form_state(
            target_net,
            context["default_time_zone"],
            context["active_source_key"],
            context["working_file"],
        )
        label = build_edit_label(actual_id, target_net.get("name"))

        return jsonify(
            {
                "net": form_state,
                "original_id": actual_id,
                "active_source": context["active_source_key"],
                "label": label,
                "permissions": context["permissions"],
                "user": context["current_user"],
            }
        )

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

    roles_env = os.environ.get("BHN_NETS_ROLES")
    if roles_env:
        roles_file = Path(roles_env).expanduser()
    else:
        roles_file = BASE_DIR / "roles.yml"

    nets_file = nets_file.resolve(strict=False)
    output_dir = output_dir.resolve(strict=False)
    roles_file = roles_file.resolve(strict=False)

    return {
        "NETS_FILE": nets_file,
        "OUTPUT_DIR": output_dir,
        "ROLES_FILE": roles_file,
        "DEFAULT_USER": os.environ.get("BHN_NETS_DEFAULT_USER", "").strip(),
    }


def load_context(config: Dict, source_key: Optional[str] = None, current_user: Optional[str] = None) -> Dict:
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

    nets_data: List[Dict[str, Any]] = []

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
                nets_data.append(net)
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
    roles_data = config.get("ROLES_DATA", {})
    user_roles = determine_user_roles(roles_data, current_user)
    permissions = {
        "can_review": bool(user_roles),
        "can_promote": "publishers" in user_roles,
    }

    pending_summary = [
        {
            "key": entry["key"],
            "name": entry["name"],
            "label": entry.get("label", ""),
            "created_at": entry.get("created_at", ""),
        }
        for entry in pending_files
    ]

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
            "pending": pending_summary,
            "permissions": permissions,
            "user": current_user,
        },
        "help_texts": HELP_TEXTS,
        "help_labels": HELP_LABELS,
        "nets_data": nets_data,
        "current_user": current_user,
        "roles": list(user_roles),
        "permissions": permissions,
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

    mode = (data.get("mode") or "add").strip().lower()
    original_id = (data.get("original_id") or "").strip()
    existing_lower_map = {str(e).lower(): str(e) for e in existing_ids}
    editing_existing = mode == "edit" and bool(original_id)
    if editing_existing and original_id.lower() not in existing_lower_map:
        errors["original_id"] = "Original net not found in the current snapshot."

    net_id = (data.get("id") or "").strip()
    existing_lower = {str(e).lower() for e in existing_ids}
    if editing_existing:
        existing_lower.discard(original_id.lower())
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

    if editing_existing:
        record["original_id"] = original_id
        record["mode"] = "edit"
    else:
        record["original_id"] = ""
        record["mode"] = "add"

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


def find_net_block_match(original_text: str, net_id: str) -> Optional[re.Match[str]]:
    pattern = re.compile(ENTRY_BLOCK_TEMPLATE.format(id=re.escape(net_id)))
    return pattern.search(original_text)


def compute_block_hash(block_text: str) -> str:
    return hashlib.sha256(block_text.encode("utf-8")).hexdigest()


def extract_entry_block(path: Optional[Path], net_id: str) -> Optional[str]:
    if not path or not path.exists():
        return None
    try:
        original_text = path.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return None
    match = find_net_block_match(original_text, net_id)
    if not match:
        return None
    return match.group(0)


def write_pending_file(
    snippet: str,
    nets_file: Path,
    output_dir: Path,
    source_file: Optional[Path] = None,
    mode: str = "add",
    original_id: str = "",
    expected_hash: Optional[str] = "",
) -> Path:
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

    mode = (mode or "add").strip().lower()
    if mode == "edit":
        if not original_id:
            raise ValueError("original_id required for edit mode")
        updated_text, matched_block = replace_existing_entry(original_text, original_id, snippet)
        if expected_hash:
            current_hash = compute_block_hash(matched_block)
            if current_hash != expected_hash:
                raise ValueError("This net changed in the meantime. Reload the latest snapshot and try again.")
        new_content = updated_text
    else:
        new_content = append_new_entry(original_text, snippet)

    with tmp_path.open("w", encoding="utf-8") as fh:
        fh.write(new_content)
    os.replace(tmp_path, pending_path)

    return pending_path


def append_new_entry(original_text: str, snippet: str) -> str:
    snippet_text = snippet.strip("\n")
    combined = f"{original_text.rstrip()}\n\n{snippet_text}\n"
    return combined


def replace_existing_entry(original_text: str, original_id: str, snippet: str) -> Tuple[str, str]:
    pattern = re.compile(
        rf"(?ms)^  - id:\s*{re.escape(original_id)}\s*\n(?:^(?!  - id:).*\n?)*"
    )
    match = pattern.search(original_text)
    if not match:
        raise ValueError(f"Unable to locate net with id '{original_id}' in the current snapshot.")
    matched_block = match.group(0)
    trailing_newlines = "\n"
    if matched_block.endswith("\n\n"):
        trailing_newlines = "\n\n"
    replacement = f"{snippet.strip()}{trailing_newlines}"
    updated = original_text[: match.start()] + replacement + original_text[match.end() :]
    return updated, matched_block


def load_nets_map(path: Optional[Path]) -> Dict[str, Dict[str, Any]]:
    if not path or not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except (FileNotFoundError, yaml.YAMLError):
        return {}
    nets = data.get("nets", []) or []
    results: Dict[str, Dict[str, Any]] = {}
    for net in nets:
        if not isinstance(net, dict):
            continue
        net_id = str(net.get("id") or "").strip()
        if not net_id:
            continue
        results[net_id.lower()] = net
    return results


def net_signature(net: Dict[str, Any]) -> str:
    try:
        return json.dumps(net, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    except TypeError:
        sanitized: Dict[str, Any] = {}
        for key, value in net.items():
            try:
                json.dumps(value)
                sanitized[key] = value
            except TypeError:
                sanitized[key] = str(value)
        return json.dumps(sanitized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def summarize_pending_files(pending_entries: List[Dict[str, str]], canonical_file: Path) -> List[Dict[str, Any]]:
    canonical_map = load_nets_map(canonical_file)
    canonical_signatures = {key: net_signature(net) for key, net in canonical_map.items()}

    summaries: List[Dict[str, Any]] = []
    for entry in pending_entries:
        path = Path(entry["path"])
        pending_map = load_nets_map(path)
        pending_signatures = {key: net_signature(net) for key, net in pending_map.items()}

        stats = {"added": 0, "updated": 0, "removed": 0, "unchanged": 0}
        changes: List[Dict[str, str]] = []

        seen = set()
        for key, net in pending_map.items():
            seen.add(key)
            display_id = str(net.get("id") or "")
            display_name = str(net.get("name") or "")
            canonical_net = canonical_map.get(key)
            if not canonical_net:
                stats["added"] += 1
                changes.append({"id": display_id, "name": display_name, "type": "added"})
            else:
                if pending_signatures[key] != canonical_signatures.get(key):
                    stats["updated"] += 1
                    changes.append({"id": display_id, "name": display_name, "type": "updated"})
                else:
                    stats["unchanged"] += 1

        for key, canonical_net in canonical_map.items():
            if key in pending_map:
                continue
            stats["removed"] += 1
            changes.append(
                {
                    "id": str(canonical_net.get("id") or ""),
                    "name": str(canonical_net.get("name") or ""),
                    "type": "removed",
                }
            )

        stats["total"] = len(pending_map)
        stats["changed"] = len([c for c in changes if c["type"] != "unchanged"])

        summary_entry = {
            "key": entry["key"],
            "name": entry["name"],
            "label": entry.get("label", ""),
            "created_at": entry.get("created_at", ""),
            "changes": changes,
            "stats": stats,
        }
        summaries.append(summary_entry)

    return summaries


def promote_pending_file(key: str, output_dir: Path, nets_file: Path, current_user: Optional[str] = None) -> Dict[str, Any]:
    pending_lookup = {entry["key"]: entry for entry in list_pending_files(output_dir)}
    if key not in pending_lookup:
        raise FileNotFoundError(key)

    pending_entry = pending_lookup[key]
    pending_path = Path(pending_entry["path"])
    if not pending_path.exists():
        raise FileNotFoundError(pending_entry["path"])

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = nets_file.with_name(f"{nets_file.stem}.backup.{timestamp}{nets_file.suffix}")

    if nets_file.exists():
        shutil.copy2(nets_file, backup_path)

    pending_content = pending_path.read_text(encoding="utf-8")
    tmp_path = nets_file.with_suffix(nets_file.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as fh:
        fh.write(pending_content)
    os.replace(tmp_path, nets_file)

    pending_path.unlink()

    return {
        "message": "Pending file promoted",
        "promoted": pending_entry["name"],
        "backup": str(backup_path) if backup_path.exists() else "",
        "user": current_user,
    }


def build_nets_summary(nets: Iterable[Dict[str, Any]]) -> List[Dict[str, str]]:
    summary: List[Dict[str, str]] = []
    for net in nets:
        if not isinstance(net, dict):
            continue
        net_id = str(net.get("id") or "").strip()
        if not net_id:
            continue
        summary.append(
            {
                "id": net_id,
                "name": str(net.get("name") or "").strip(),
                "category": str(net.get("category") or "").strip(),
                "label": build_edit_label(net_id, net.get("name")),
            }
        )
    summary.sort(key=lambda item: item["id"].lower())
    return summary


def build_edit_label(net_id: str, name: Optional[str]) -> str:
    name_str = str(name or "").strip()
    if name_str:
        return f"{net_id} — {name_str}"
    return net_id


def find_net_by_id(nets: Iterable[Dict[str, Any]], net_id: str) -> Tuple[Optional[Dict[str, Any]], str]:
    target_lower = str(net_id or "").lower()
    for net in nets:
        if not isinstance(net, dict):
            continue
        current_id = str(net.get("id") or "")
        if current_id.lower() == target_lower:
            return net, current_id
    return None, ""


def build_form_state(
    net: Dict[str, Any],
    default_time_zone: str,
    active_source: str,
    source_file: Optional[Path] = None,
) -> Dict[str, Any]:
    values: Dict[str, str] = {}
    for key in BASE_FIELD_KEYS:
        if key == "duration_min":
            duration = net.get("duration_min")
            values[key] = "" if duration is None else str(duration)
        else:
            values[key] = str(net.get(key) or "")

    for key in OPTIONAL_FIELD_KEYS:
        values[key] = str(net.get(key) or "")

    custom_fields: List[Dict[str, str]] = []
    known_keys = set(BASE_FIELD_KEYS) | set(OPTIONAL_FIELD_KEYS)
    for key, value in net.items():
        if key in known_keys:
            continue
        if value in (None, "", []):
            continue
        if isinstance(value, (dict, list)):
            continue
        custom_fields.append({"key": str(key), "value": str(value)})

    connections = []
    for conn_key, field_names in CONNECTION_FIELD_MAP.items():
        enabled = any(str(net.get(field) or "").strip() for field in field_names)
        connections.append({"key": conn_key, "enabled": enabled})

    source_hash = ""
    if source_file:
        block_text = extract_entry_block(source_file, str(net.get("id") or ""))
        if block_text:
            source_hash = compute_block_hash(block_text)

    meta = {
        "manualTimeMode": False,
        "startPicker": values.get("start_local", ""),
        "startManual": "",
        "categoryChoice": values.get("category", ""),
        "sourceKey": active_source,
        "editing": {
            "isEditing": True,
            "originalId": str(net.get("id") or ""),
            "label": build_edit_label(str(net.get("id") or ""), net.get("name")),
            "sourceHash": source_hash,
        },
    }

    values["original_id"] = str(net.get("id") or "")
    values["mode"] = "edit"
    values["source_hash"] = source_hash

    return {
        "values": values,
        "customFields": custom_fields,
        "connections": connections,
        "meta": meta,
    }


if __name__ == "__main__":
    application = create_app()
    application.run(debug=True)
