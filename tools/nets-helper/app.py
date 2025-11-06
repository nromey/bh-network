"""
Flask app that helps trusted editors draft additions to _data/nets.json.
"""
from __future__ import annotations

import os
import re
from collections import OrderedDict
from datetime import datetime, timezone
import json
import hashlib
import shutil
import subprocess
import threading
import unicodedata
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
PENDING_NAME_PATTERN = re.compile(r"^nets\.pending\.(\d{8})_(\d{6})\.json$")

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

METADATA_SUFFIX = ".meta.json"
PUBLIC_RATE_LIMIT_WINDOW_SECONDS = 3600
PUBLIC_RATE_LIMIT_MAX = 3
PUBLIC_RATE_LIMIT: Dict[str, List[float]] = {}
PUBLIC_RATE_LIMIT_LOCK = threading.Lock()


SLUG_PATTERN = re.compile(r"[^A-Za-z0-9\-]+")
TOP_LEVEL_ORDER = ["time_zone", "nets"]


def default_nets_payload() -> OrderedDict:
    payload = OrderedDict()
    payload["time_zone"] = "America/New_York"
    payload["nets"] = []
    return payload


def normalize_net_entry(entry: Dict[str, Any]) -> OrderedDict:
    ordered: OrderedDict[str, Any] = OrderedDict()
    for key in BASE_FIELD_KEYS:
        if key in entry:
            ordered[key] = entry[key]

    for key in OPTIONAL_FIELD_KEYS:
        if key in entry and key not in ordered and entry[key] not in (None, ""):
            ordered[key] = entry[key]

    remaining = sorted(k for k in entry.keys() if k not in ordered)
    for key in remaining:
        ordered[key] = entry[key]
    return ordered


def normalize_nets_payload(payload: Dict[str, Any]) -> OrderedDict:
    normalized = default_nets_payload()
    time_zone = payload.get("time_zone")
    if isinstance(time_zone, str) and time_zone.strip():
        normalized["time_zone"] = time_zone.strip()

    nets = payload.get("nets")
    if isinstance(nets, list):
        normalized["nets"] = [normalize_net_entry(entry) if isinstance(entry, dict) else entry for entry in nets]
    else:
        normalized["nets"] = []

    # Preserve any other top-level keys deterministically
    for key in sorted(payload.keys()):
        if key in normalized:
            continue
        normalized[key] = payload[key]
    return normalized


def load_nets_payload(path: Path) -> OrderedDict:
    try:
        with path.open("r", encoding="utf-8") as fh:
            raw = json.load(fh) or {}
    except FileNotFoundError:
        return default_nets_payload()
    except json.JSONDecodeError:
        return default_nets_payload()

    if not isinstance(raw, dict):
        return default_nets_payload()
    return normalize_nets_payload(raw)


def save_nets_payload(path: Path, payload: Dict[str, Any]) -> None:
    normalized = normalize_nets_payload(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as fh:
        json.dump(normalized, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.replace(tmp_path, path)


def compute_record_hash(record: Dict[str, Any]) -> str:
    canonical = json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def extract_entry_record(path: Optional[Path], net_id: str) -> Optional[Dict[str, Any]]:
    if not path or not path.exists():
        return None
    payload = load_nets_payload(path)
    nets = payload.get("nets") or []
    target = net_id.strip().lower()
    for entry in nets:
        if not isinstance(entry, dict):
            continue
        current_id = str(entry.get("id") or "").strip().lower()
        if current_id == target:
            return entry
    return None


def record_to_entry(record: Dict[str, Any]) -> OrderedDict:
    entry: Dict[str, Any] = {
        "id": record["id"],
        "category": record["category"],
        "name": record["name"],
        "description": record["description"],
        "start_local": record["start_local"],
        "duration_min": record["duration_min"],
        "rrule": record["rrule"],
    }
    tz = record.get("time_zone")
    if tz:
        entry["time_zone"] = tz

    optional_fields = record.get("optional") or {}
    for key, value in optional_fields.items():
        if value not in (None, ""):
            entry[key] = value

    for key, value in record.get("custom", []):
        if value not in (None, ""):
            entry[key] = value

    return normalize_net_entry(entry)


def slugify(value: str) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = normalized.strip().lower()
    normalized = re.sub(r"\s+", "-", normalized)
    normalized = SLUG_PATTERN.sub("", normalized)
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-")
    return normalized


def generate_candidate_id(name: str, existing_ids: Iterable[str]) -> str:
    base = slugify(name) or "net"
    existing_lower = {str(e).lower() for e in existing_ids}
    if base.lower() not in existing_lower:
        return base
    counter = 2
    while True:
        candidate = f"{base}-{counter}"
        if candidate.lower() not in existing_lower:
            return candidate
        counter += 1


class RateLimitExceeded(Exception):
    pass


def enforce_public_rate_limit(identifier: str) -> None:
    if not identifier:
        identifier = "unknown"
    now = datetime.now(timezone.utc).timestamp()
    with PUBLIC_RATE_LIMIT_LOCK:
        entries = PUBLIC_RATE_LIMIT.setdefault(identifier, [])
        entries[:] = [ts for ts in entries if now - ts < PUBLIC_RATE_LIMIT_WINDOW_SECONDS]
        if len(entries) >= PUBLIC_RATE_LIMIT_MAX:
            raise RateLimitExceeded()
        entries.append(now)


def pending_metadata_path(pending_path: Path) -> Path:
    return pending_path.with_suffix(pending_path.suffix + METADATA_SUFFIX)


def load_pending_metadata(meta_path: Path) -> Dict[str, Any]:
    try:
        with meta_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh) or {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return data


def write_pending_metadata(meta_path: Path, metadata: Dict[str, Any]) -> None:
    try:
        with meta_path.open("w", encoding="utf-8") as fh:
            json.dump(metadata, fh, ensure_ascii=False, indent=2)
    except OSError:
        # Metadata is helpful but non-critical; ignore write failures.
        pass


def remove_pending_metadata(pending_path: Path) -> None:
    meta_path = pending_metadata_path(pending_path)
    try:
        meta_path.unlink()
    except FileNotFoundError:
        pass


def run_git_command(repo_root: Path, args: List[str], env: Optional[Dict[str, str]] = None) -> subprocess.CompletedProcess:
    command = ["git"] + args
    result = subprocess.run(
        command,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        message = stderr or stdout or "Unknown git error"
        raise RuntimeError(f"git {' '.join(args)} failed: {message}")
    return result


def git_stage_paths(repo_root: Path, paths: Iterable[Path]) -> None:
    for path in paths:
        run_git_command(repo_root, ["add", str(path)])


def git_has_staged_changes(repo_root: Path) -> bool:
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=str(repo_root),
    )
    return result.returncode == 1


def git_commit(repo_root: Path, message: str, author: Optional[str] = None) -> str:
    env = os.environ.copy()
    if author:
        sanitized = re.sub(r"[^A-Za-z0-9]+", ".", author).strip(".") or "nets-helper"
        env.setdefault("GIT_AUTHOR_NAME", author)
        env.setdefault("GIT_COMMITTER_NAME", author)
        env.setdefault("GIT_AUTHOR_EMAIL", f"{sanitized}@blindhams.network")
        env.setdefault("GIT_COMMITTER_EMAIL", f"{sanitized}@blindhams.network")
    run_git_command(repo_root, ["commit", "-m", message], env=env)
    result = run_git_command(repo_root, ["rev-parse", "HEAD"])
    return result.stdout.strip()


def git_push(repo_root: Path, remote: str, branch: str) -> None:
    run_git_command(repo_root, ["push", remote, branch])


def git_current_branch(repo_root: Path) -> str:
    try:
        result = run_git_command(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"])
        branch = result.stdout.strip()
        if branch and branch != "HEAD":
            return branch
    except RuntimeError:
        pass
    return "main"


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
    roles_data = load_roles_file(app.config["ROLES_FILE"])
    app.config["ROLES_DATA"] = roles_data
    app.config["ROLE_NAMES"] = {
        "publishers": [str(user) for user in sorted(roles_data.get("publishers", []))],
        "reviewers": [str(user) for user in sorted(roles_data.get("reviewers", []))],
    }

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
        entry = record_to_entry(normalized)
        snippet = build_json_preview(entry)
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
        entry = record_to_entry(normalized)
        snippet = build_json_preview(entry)
        submission_note = sanitize_optional(data.get("submission_note"))
        metadata: Dict[str, Any] = {}
        if submission_note:
            metadata["note"] = submission_note
        try:
            pending_path = write_pending_file(
                entry,
                app.config["NETS_FILE"],
                app.config["OUTPUT_DIR"],
                context["working_file"],
                mode=mode,
                original_id=original_id,
                expected_hash=source_hash,
                current_user=current_user,
                metadata=metadata,
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
                "submitted_by": current_user or "",
                "submission_note": submission_note,
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

    @app.post("/api/pending/promote_commit")
    def api_pending_promote_commit():
        current_user = get_current_user(app)
        if not user_can_promote(app.config["ROLES_DATA"], current_user):
            return jsonify({"error": "You do not have permission to promote pending files."}), 403

        payload = request.get_json(force=True, silent=True) or {}
        key = payload.get("key")
        if not isinstance(key, str):
            return jsonify({"error": "Specify which pending file to promote."}), 400

        output_dir: Path = app.config["OUTPUT_DIR"]
        nets_file: Path = app.config["NETS_FILE"]
        repo_root: Path = app.config["REPO_ROOT"]
        remote_name: str = app.config.get("GIT_REMOTE", "origin")
        branch_name: str = app.config.get("GIT_BRANCH") or git_current_branch(repo_root)
        auto_push: bool = app.config.get("AUTO_PUSH", True)

        pending_entries = list_pending_files(output_dir)
        pending_lookup = {entry["key"]: entry for entry in pending_entries}
        if key not in pending_lookup:
            return jsonify({"error": "Pending file not found."}), 404

        summary_list = summarize_pending_files([pending_lookup[key]], nets_file)
        if not summary_list:
            return jsonify({"error": "Unable to summarize pending file."}), 400
        summary_entry = summary_list[0]

        try:
            promote_result = promote_pending_file(
                key,
                output_dir,
                nets_file,
                current_user=current_user,
            )
        except FileNotFoundError:
            return jsonify({"error": "Pending file not found."}), 404
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        nets_rel = nets_file.relative_to(repo_root)
        paths_to_stage = [nets_rel]
        backup_path = promote_result.get("backup")
        if backup_path:
            backup = Path(backup_path)
            try:
                paths_to_stage.append(backup.relative_to(repo_root))
            except ValueError:
                pass

        try:
            git_stage_paths(repo_root, paths_to_stage)
            if not git_has_staged_changes(repo_root):
                run_git_command(repo_root, ["reset"])
                return jsonify({
                    "message": "Pending file promoted but no changes detected for commit.",
                    "promoted": promote_result.get("promoted", ""),
                    "backup": promote_result.get("backup", ""),
                    "changes": summary_entry.get("changes", []),
                    "stats": summary_entry.get("stats", {}),
                })

            commit_msg = payload.get("commit_message")
            if not isinstance(commit_msg, str) or not commit_msg.strip():
                change_labels = [f"{change.get('type', 'updated')}: {change.get('id')}" for change in summary_entry.get("changes", [])]
                if change_labels:
                    changes_text = ", ".join(change_labels)
                else:
                    changes_text = "nets update"
                commit_msg = f"Publish nets helper: {changes_text}"

            commit_hash = git_commit(repo_root, commit_msg.strip(), author=current_user or "nets-helper")

            push_status = {"pushed": False, "message": "Push skipped"}
            if auto_push:
                try:
                    git_push(repo_root, remote_name, branch_name)
                    push_status = {"pushed": True, "message": f"Pushed to {remote_name}/{branch_name}"}
                except RuntimeError as exc:
                    push_status = {"pushed": False, "message": str(exc)}

        except RuntimeError as exc:
            try:
                run_git_command(repo_root, ["reset", "--mixed"])
            except RuntimeError:
                pass
            return jsonify({"error": str(exc)}), 500

        return jsonify(
            {
                "message": "Pending file promoted and committed.",
                "promoted": promote_result.get("promoted", ""),
                "backup": promote_result.get("backup", ""),
                "changes": summary_entry.get("changes", []),
                "stats": summary_entry.get("stats", {}),
                "commit": {
                    "hash": commit_hash,
                    "short_hash": commit_hash[:7],
                    "message": commit_msg.strip(),
                    "branch": branch_name,
                    "pushed": push_status.get("pushed", False),
                    "push_message": push_status.get("message", ""),
                },
            }
        )

    @app.post("/api/public/suggest")
    def api_public_suggest():
        payload = request.get_json(force=True, silent=True)
        if not payload:
            payload = request.form.to_dict()
        if not payload:
            return jsonify({"error": "No data submitted."}), 400

        honeypot = (payload.get("website") or payload.get("url") or "").strip()
        if honeypot:
            # silently accept to confuse bots
            return jsonify({"message": "Submission received."}), 204

        client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
        client_ip = client_ip.split(",")[0].strip()
        try:
            enforce_public_rate_limit(client_ip)
        except RateLimitExceeded:
            return jsonify({"error": "Too many submissions from this address. Please try again later."}), 429

        name = (payload.get("name") or "").strip()
        description = (payload.get("description") or "").strip()
        category = (payload.get("category") or "").strip() or "bhn"
        start_local = (payload.get("start_local") or payload.get("start_time") or "").strip()
        duration = payload.get("duration_min") or payload.get("duration_minutes") or payload.get("duration") or ""
        time_zone = (payload.get("time_zone") or payload.get("timezone") or "").strip() or "America/New_York"
        rrule = (payload.get("rrule") or payload.get("recurrence") or "").strip()
        contact_name = (payload.get("contact_name") or "").strip()
        contact_email = (payload.get("contact_email") or "").strip()
        additional_info = (payload.get("additional_info") or payload.get("notes") or "").strip()

        allstar = (payload.get("allstar") or "").strip()
        echolink = (payload.get("echolink") or "").strip()
        frequency = (payload.get("frequency") or payload.get("hf_frequency") or "").strip()
        mode = (payload.get("mode") or payload.get("hf_mode") or "").strip()

        if not name or not description or not start_local or not duration or not rrule or not contact_email:
            return jsonify({"error": "Missing required fields."}), 400

        context = load_context(app.config, "nets", None)
        existing_ids = set(context.get("existing_ids", []))
        for net in context.get("nets_data", []):
            net_id = str(net.get("id") or "").strip()
            if net_id:
                existing_ids.add(net_id)
        pending_entries = context.get("pending_context", {}).get("pending", [])
        for entry in pending_entries:
            for change in entry.get("changes", []):
                change_id = str(change.get("id") or "").strip()
                if change_id:
                    existing_ids.add(change_id)

        candidate_id = generate_candidate_id(name, existing_ids)

        submission_data = {
            "id": candidate_id,
            "name": name,
            "description": description,
            "category": category,
            "start_local": start_local,
        }

        try:
            duration_int = int(str(duration).strip())
        except ValueError:
            return jsonify({"error": "Duration must be a number (minutes)."}), 400
        submission_data["duration_min"] = str(duration_int)
        submission_data["rrule"] = rrule
        submission_data["time_zone"] = time_zone

        optional_fields = {}
        if allstar:
            optional_fields["allstar"] = allstar
        if echolink:
            optional_fields["echolink"] = echolink
        if frequency:
            optional_fields["frequency"] = frequency
        if mode:
            optional_fields["mode"] = mode
        if additional_info:
            optional_fields["notes"] = additional_info
        for key, value in optional_fields.items():
            submission_data[key] = value

        normalized, errors = normalize_submission(submission_data, existing_ids, context["default_time_zone"])
        if errors:
            return jsonify({"errors": errors}), 400

        metadata = {
            "submitted_via": "public_form",
            "submitted_by": contact_name or contact_email,
            "contact_email": contact_email,
            "contact_name": contact_name,
            "note": additional_info,
        }

        submission_note = f"Public submission by {contact_name or 'anonymous'} ({contact_email})"

        try:
            pending_path = write_pending_file(
                record_to_entry(normalized),
                app.config["NETS_FILE"],
                app.config["OUTPUT_DIR"],
                context["working_file"],
                mode="add",
                original_id="",
                expected_hash="",
                current_user=None,
                metadata=metadata,
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        return jsonify(
            {
                "message": "Submission received. A moderator will review it soon.",
                "generated_id": normalized["id"],
                "pending_path": str(pending_path),
                "submission_note": submission_note,
            }
        ), 202

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

        metadata_entry = {}
        if context["active_source_key"].startswith("pending:"):
            metadata_entry = context.get("pending_metadata", {}).get(context["active_source_key"], {})

        form_state = build_form_state(
            target_net,
            context["default_time_zone"],
            context["active_source_key"],
            context["working_file"],
            metadata=metadata_entry,
        )
        label = build_edit_label(actual_id, target_net.get("name"))

        return jsonify(
            {
                "net": form_state,
                "original_id": actual_id,
                "active_source": context["active_source_key"],
                "label": label,
                "metadata": form_state.get("metadata", {}),
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
        nets_file = repo_root / "_data" / "nets.json"

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
    resolved_nets = nets_file.resolve()
    repo_root = resolved_nets.parent
    current = repo_root
    while current.parent != current:
        if (current / ".git").is_dir():
            repo_root = current
            break
        current = current.parent

    auto_push_env = os.environ.get("BHN_NETS_AUTO_PUSH", "1").strip().lower()
    auto_push = auto_push_env not in {"0", "false", "off", "no"}

    return {
        "NETS_FILE": nets_file,
        "OUTPUT_DIR": output_dir,
        "ROLES_FILE": roles_file,
        "DEFAULT_USER": os.environ.get("BHN_NETS_DEFAULT_USER", "").strip(),
        "REPO_ROOT": repo_root,
        "GIT_REMOTE": os.environ.get("BHN_NETS_REMOTE", "origin"),
        "GIT_BRANCH": os.environ.get("BHN_NETS_BRANCH", ""),
        "AUTO_PUSH": auto_push,
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
        data = load_nets_payload(working_file)
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
            "submitted_by": entry.get("submitted_by", ""),
            "submitted_at": entry.get("submitted_at", ""),
            "note": entry.get("note", ""),
        }
        for entry in pending_files
    ]

    pending_metadata_map = {entry["key"]: entry.get("metadata", {}) for entry in pending_files}

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
            "role_names": config.get("ROLE_NAMES", {}),
        },
        "pending_metadata": pending_metadata_map,
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

    candidates = sorted(iter_pending_snapshot_paths(pending_dir), key=lambda p: p.name, reverse=True)
    if not candidates:
        return None
    return candidates[0]


def list_pending_files(output_dir: Path) -> List[Dict[str, str]]:
    pending_dir = output_dir / "pending"
    if not pending_dir.is_dir():
        return []

    entries: List[Dict[str, str]] = []
    for path in sorted(iter_pending_snapshot_paths(pending_dir), key=lambda p: p.name, reverse=True):
        label, iso_timestamp = pending_label_from_name(path.name)
        meta_path = pending_metadata_path(path)
        metadata = load_pending_metadata(meta_path)
        entries.append(
            {
                "key": f"pending:{path.name}",
                "name": path.name,
                "path": str(path),
                "label": label,
                "created_at": iso_timestamp or "",
                "submitted_by": str(metadata.get("submitted_by", "") or ""),
                "submitted_at": str(metadata.get("submitted_at", "") or ""),
                "note": str(metadata.get("note", "") or ""),
                "metadata": metadata,
            }
        )
    return entries


def iter_pending_snapshot_paths(pending_dir: Path):
    for path in pending_dir.glob("nets.pending.*.json"):
        if not path.is_file():
            continue
        if path.name.endswith(".meta.json"):
            continue
        yield path


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
                "submitted_by": entry.get("submitted_by", ""),
                "submitted_at": entry.get("submitted_at", ""),
                "note": entry.get("note", ""),
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
            remove_pending_metadata(path)
        except FileNotFoundError:
            continue
    return deleted


def delete_single_pending(output_dir: Path, key: str) -> List[str]:
    pending_files = {entry["key"]: entry for entry in list_pending_files(output_dir)}
    if key not in pending_files:
        raise FileNotFoundError(key)
    path = Path(pending_files[key]["path"])
    path.unlink()
    remove_pending_metadata(path)
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


def build_json_preview(entry: Dict[str, Any]) -> str:
    return json.dumps(entry, ensure_ascii=False, indent=2)


def write_pending_file(
    net_entry: Dict[str, Any],
    nets_file: Path,
    output_dir: Path,
    source_file: Optional[Path] = None,
    mode: str = "add",
    original_id: str = "",
    expected_hash: Optional[str] = "",
    current_user: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    pending_dir = output_dir / "pending"
    pending_dir.mkdir(parents=True, exist_ok=True)
    pending_name = f"nets.pending.{timestamp}.json"
    pending_path = pending_dir / pending_name

    base_file = source_file or nets_file
    payload = load_nets_payload(base_file)
    nets = []
    for entry in payload.get("nets", []) or []:
        if isinstance(entry, dict):
            nets.append(entry.copy())
        else:
            nets.append(entry)

    normalized_entry = normalize_net_entry(net_entry)
    mode = (mode or "add").strip().lower()
    if mode == "edit":
        if not original_id:
            raise ValueError("original_id required for edit mode")
        target = original_id.strip().lower()
        index = -1
        for idx, existing in enumerate(nets):
            if not isinstance(existing, dict):
                continue
            current_id = str(existing.get("id") or "").strip().lower()
            if current_id == target:
                index = idx
                break
        if index == -1:
            raise ValueError(f"Unable to locate net with id '{original_id}' in the current snapshot.")
        if expected_hash:
            current_hash = compute_record_hash(nets[index])
            if current_hash != expected_hash:
                raise ValueError("This net changed in the meantime. Reload the latest snapshot and try again.")
        nets[index] = normalized_entry
    else:
        nets.append(normalized_entry)

    payload["nets"] = nets
    save_nets_payload(pending_path, payload)

    metadata_payload: Dict[str, Any] = {
        "submitted_by": (current_user or ""),
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
    }
    if original_id:
        metadata_payload["original_id"] = original_id
    if metadata:
        for key, value in metadata.items():
            if value in (None, "", []):
                continue
            metadata_payload[key] = value

    meta_path = pending_metadata_path(pending_path)
    write_pending_metadata(meta_path, metadata_payload)

    return pending_path


def load_nets_map(path: Optional[Path]) -> Dict[str, Dict[str, Any]]:
    if not path or not path.exists():
        return {}
    payload = load_nets_payload(path)
    nets = payload.get("nets", []) or []
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
            "submitted_by": entry.get("submitted_by", ""),
            "submitted_at": entry.get("submitted_at", ""),
            "note": entry.get("note", ""),
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
    remove_pending_metadata(pending_path)

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
    metadata: Optional[Dict[str, Any]] = None,
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
        existing_record = extract_entry_record(source_file, str(net.get("id") or ""))
        if existing_record:
            source_hash = compute_record_hash(existing_record)

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
    metadata = metadata or {}
    values["submission_note"] = str(metadata.get("note", "") or "")

    return {
        "values": values,
        "customFields": custom_fields,
        "connections": connections,
        "meta": meta,
        "metadata": {
            "submitted_by": str(metadata.get("submitted_by", "") or ""),
            "submitted_at": str(metadata.get("submitted_at", "") or ""),
            "note": str(metadata.get("note", "") or ""),
        },
    }


if __name__ == "__main__":
    application = create_app()
    application.run(debug=True)
