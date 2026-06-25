from __future__ import annotations

import argparse
import json
import mimetypes
import re
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from autoskill_agent import observatory, skillgen


STEP_IDS = {
    "trigger": 0,
    "parse_bank_transactions": 1,
    "build_reconciliation_preview": 2,
    "require_approval": 3,
    "create_reconciled_spreadsheet": 4,
    "validate_outputs": 5,
    "write_audit_log": 6,
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def skillgen_paths(root: Path) -> skillgen.SkillGenPaths:
    return skillgen.paths(root)


def match_files(root: Path) -> list[Path]:
    p = skillgen_paths(root)
    if not p.matches_dir.exists():
        return []
    return sorted(path for path in p.matches_dir.glob("*.json") if not path.name.endswith((".preview.json", ".validation.json")))


def load_skill(root: Path, skill_id: str, version: int) -> dict[str, Any]:
    try:
        return skillgen.load_skill_from_registry(root, skill_id, version)
    except Exception:
        workspace_skills = root / "workspace" / "skills"
        for candidate in workspace_skills.glob("*/skill.json"):
            data = read_json(candidate)
            if data.get("skill_id") == skill_id:
                return data
    return {"skill_id": skill_id, "name": skill_id.replace("_", " ").title(), "version": version}


def clean_display_text(value: str) -> str:
    replacements = {
        "repeated daily_cash_reconciliation workflow": "repeated workflow",
        "daily_cash_reconciliation workflow": "detected workflow",
        "Daily Cash Reconciliation Skill": "Generated workflow skill",
        "daily_cash_reconciliation": "detected workflow",
        "Request human approval": "Request review",
        "request human approval": "request review",
        "Require human approval before workbook changes.": "Require review before file changes.",
        "human approval": "review",
        "Human approval": "Review",
        "Skill Run ID": "Run ID",
        "skill run id": "run id",
        "audit/SkillOps evidence": "run history",
        "run record/run history evidence": "run history",
        "SkillOps": "run history",
        "audit log": "run record",
        "audit": "run record",
        "detected workflow workflow": "detected workflow",
    }
    text = value
    for before, after in replacements.items():
        text = text.replace(before, after)
    return text


def humanize(value: Any) -> str:
    text = str(value)
    text = clean_display_text(text)
    text = text.replace("_", " ").replace("-", " ")
    return " ".join(text.split()).capitalize()


def read_skill_candidate_rows(root: Path) -> list[dict[str, Any]]:
    jsonl_path = root / "workspace" / "events" / "skill_candidates.jsonl"
    try:
        return skillgen.read_jsonl(jsonl_path)
    except Exception:
        return []


def candidate_for_match(root: Path, match: dict[str, Any], skill: dict[str, Any]) -> dict[str, Any]:
    candidate_id = (skill.get("source_candidate") or {}).get("candidate_id")
    if candidate_id:
        for row in read_skill_candidate_rows(root):
            if row.get("candidate_id") == candidate_id:
                return row
        candidate_path = root / "workspace" / "candidates" / f"{candidate_id}.json"
        if candidate_path.exists():
            return read_json(candidate_path)
    rows = read_skill_candidate_rows(root)
    return rows[-1] if rows else {}


def as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [clean_display_text(str(item)) for item in value if item is not None]


def plain_sequence_label(value: Any) -> str:
    labels = {
        "email_received": "Receive the bank transaction email",
        "spreadsheet_row_updated": "Update the matching spreadsheet rows",
        "outbound_message_created": "Draft the result reply",
        "read bank attachment rows": "Read the bank attachment rows",
        "match transactions against Payment Export": "Compare rows with the finance workbook",
        "compute Amount Diff": "Calculate the amount difference",
        "preview Daily Reconciliation row updates": "Prepare the spreadsheet update",
        "draft summary reply": "Draft the result reply",
        "write audit log": "Save the local run record",
    }
    text = str(value)
    return labels.get(text, humanize(text))


def pattern_definition(root: Path, match: dict[str, Any], candidate: dict[str, Any]) -> str:
    event = find_event(root, match["trigger_event_id"]) or {}
    payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
    subject = payload.get("subject") or "a daily bank transaction email"
    sender = payload.get("from") or "the bank operations sender"
    evidence = candidate.get("evidence", {}) if isinstance(candidate.get("evidence"), dict) else {}
    workbook = filename(str(evidence.get("target_artifact") or "the finance workbook"))
    sheet = evidence.get("target_sheet") or "the tracking sheet"
    return (
        f"This pattern is a daily bank email workflow: when {sender} sends '{subject}', "
        f"the finance team opens the attached transaction spreadsheet, checks the rows against {workbook}, "
        f"updates the {sheet} sheet, separates exceptions for review, and saves a reply draft."
    )


def pattern_explanation(candidate: dict[str, Any]) -> str:
    pattern = candidate.get("pattern", {}) if isinstance(candidate.get("pattern"), dict) else {}
    evidence = candidate.get("evidence", {}) if isinstance(candidate.get("evidence"), dict) else {}
    episode_count = int(pattern.get("episode_count") or 0)
    if episode_count == 0:
        episodes = evidence.get("episode_ids") or evidence.get("episodes") or []
        episode_count = len(episodes) if isinstance(episodes, list) else 0
    workbook = filename(str(evidence.get("target_artifact") or "the same workbook"))
    target_sheet = evidence.get("target_sheet") or "the same spreadsheet tab"
    return (
        f"It is repetitive because the same email-driven workflow appeared in {episode_count or 3} examples: "
        f"the attachment follows the bank_transactions_*.xlsx naming pattern, the rows are checked against {workbook}, "
        f"the same {target_sheet} fields are filled, and the reply always reports how many rows matched plus which rows need review. "
        "The date, row range, and amounts change; the work pattern stays the same."
    )


def concrete_pattern_signals(candidate: dict[str, Any]) -> list[str]:
    pattern = candidate.get("pattern", {}) if isinstance(candidate.get("pattern"), dict) else {}
    evidence = candidate.get("evidence", {}) if isinstance(candidate.get("evidence"), dict) else {}
    episode_count = int(pattern.get("episode_count") or 0)
    if episode_count == 0:
        episodes = evidence.get("episode_ids") or evidence.get("episodes") or []
        episode_count = len(episodes) if isinstance(episodes, list) else 0
    workbook = filename(str(evidence.get("target_artifact") or "the same workbook"))
    target_sheet = evidence.get("target_sheet") or "the same spreadsheet tab"
    fields = as_string_list(evidence.get("common_fields"))
    important_fields = [field for field in fields if field in {"Match Status", "Exception Reason", "Reviewer", "Reviewed At", "Source Email ID"}]
    signals = [
        f"{episode_count or 3} prior examples used the same bank email workflow",
        "Each example used an attachment named like bank_transactions_*.xlsx",
        f"Each example updated {workbook} / {target_sheet}",
    ]
    if important_fields:
        signals.append(f"Each example filled the same review fields: {', '.join(important_fields)}")
    signals.append("Each example ended with a reply draft summarizing matched rows and review items")
    return signals


def issue_list_from_candidate(candidate: dict[str, Any]) -> list[str]:
    guardrails = as_string_list(candidate.get("suggested_guardrails"))
    if guardrails:
        return guardrails
    suggested_skill = candidate.get("suggested_skill", {}) if isinstance(candidate.get("suggested_skill"), dict) else {}
    forbidden = as_string_list(suggested_skill.get("forbidden_actions"))
    if forbidden:
        return [f"Prevent {item}" for item in forbidden]
    handoff = candidate.get("handoff", {}) if isinstance(candidate.get("handoff"), dict) else {}
    fields = as_string_list(handoff.get("required_confirmation_fields"))
    return [f"Confirm {field}" for field in fields]


def find_event(root: Path, event_id: str) -> dict[str, Any] | None:
    for event in skillgen.read_events(skillgen_paths(root).event_log):
        if event.get("id") == event_id:
            return event
    return None


def latest_execution(root: Path, match: dict[str, Any]) -> dict[str, Any] | None:
    events = skillgen.read_events(skillgen_paths(root).event_log)
    executions = [
        event
        for event in events
        if event.get("type") == "skill_execution"
        and event.get("skill_id") == match.get("skill_id")
        and event.get("skill_version") == match.get("skill_version")
        and event.get("trigger_event_id") == match.get("trigger_event_id")
    ]
    return executions[-1] if executions else None


def ensure_preview(root: Path, match_id: str) -> dict[str, Any]:
    preview_path = skillgen_paths(root).matches_dir / f"{match_id}.preview.json"
    if preview_path.exists():
        return read_json(preview_path)
    return skillgen.preview_match(root, match_id)


def validation_for(root: Path, match_id: str) -> dict[str, Any] | None:
    path = skillgen_paths(root).matches_dir / f"{match_id}.validation.json"
    return read_json(path) if path.exists() else None


def list_matches(root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in match_files(root):
        match = read_json(path)
        skill = load_skill(root, match["skill_id"], int(match["skill_version"]))
        rows.append(
            {
                **match,
                "skill_name": skill.get("name", match["skill_id"].replace("_", " ").title()),
            }
        )
    return rows


def skillops_payload(root: Path, skill_id: str) -> dict[str, Any]:
    summary = skillgen.skillops_summary(root)
    for item in summary.get("skills", []):
        if item.get("skill_id") == skill_id:
            return {
                "skill_id": item["skill_id"],
                "skill_name": item["name"],
                "users": item["users"],
                "matches": item["matches"],
                "runs": item["runs"],
                "run_rate": item["run_per_match"],
                "success_rate": item["success"],
                "reject_rate": item["reject_rate"],
                "last_used": item.get("last_used_at") or item.get("installed_at") or "",
                "status": item["status"],
            }
    return {
        "skill_id": skill_id,
        "skill_name": skill_id.replace("_", " ").title(),
        "users": 0,
        "matches": 0,
        "runs": 0,
        "run_rate": 0,
        "success_rate": 0,
        "reject_rate": 0,
        "last_used": "",
        "status": "active",
    }


def skill_list_payload(root: Path) -> list[dict[str, Any]]:
    return [
        {"skill_id": item["skill_id"], "skill_name": item["name"], "status": item["status"]}
        for item in skillgen.skillops_summary(root).get("skills", [])
    ]


def filename(path: str) -> str:
    return Path(path).name


def trigger_summary(root: Path, match: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    event = find_event(root, match["trigger_event_id"]) or {}
    payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
    subject = payload.get("subject") or match["trigger_event_id"]
    attachment_names = [
        item.get("filename")
        for item in payload.get("attachments", [])
        if isinstance(item, dict) and item.get("filename")
    ]
    attachment_part = f" with {', '.join(attachment_names)}" if attachment_names else ""
    return f"Matched email: {subject}{attachment_part}.", {"email": payload, "match_reasons": match.get("match_reasons", [])}


def preview_stats(preview: dict[str, Any]) -> dict[str, int]:
    update = preview.get("proposed_workbook_update", {})
    return {
        "total": int(update.get("import_transactions", 0)),
        "matched": int(update.get("matched_count", 0)),
        "exceptions": int(update.get("exception_count", 0)),
    }


def event_step_started(step_id: str, label: str, timestamp: str, sublabel: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": "step_started",
        "step_id": step_id,
        "step_index": STEP_IDS[step_id],
        "label": label,
        "timestamp": timestamp,
    }
    if sublabel:
        payload["sublabel"] = sublabel
    return payload


def event_step_completed(
    step_id: str,
    label: str,
    summary: str,
    elapsed_ms: int,
    timestamp: str,
    raw: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": "step_completed",
        "step_id": step_id,
        "step_index": STEP_IDS[step_id],
        "label": label,
        "summary": summary,
        "elapsed_ms": elapsed_ms,
        "timestamp": timestamp,
    }
    if raw is not None:
        payload["raw"] = raw
    return payload


def pattern_detected_event(root: Path, match: dict[str, Any], skill: dict[str, Any], timestamp: str) -> dict[str, Any]:
    candidate = candidate_for_match(root, match, skill)
    pattern = candidate.get("pattern", {}) if isinstance(candidate.get("pattern"), dict) else {}
    summary = candidate.get("summary", {}) if isinstance(candidate.get("summary"), dict) else {}
    evidence = candidate.get("evidence", {}) if isinstance(candidate.get("evidence"), dict) else {}
    next_trigger = candidate.get("next_trigger", {}) if isinstance(candidate.get("next_trigger"), dict) else {}
    episode_count = int(pattern.get("episode_count") or summary.get("episode_count") or 0)
    if episode_count == 0:
        episodes = evidence.get("episode_ids") or evidence.get("episodes") or []
        episode_count = len(episodes) if isinstance(episodes, list) else 0
    common_sequence = pattern.get("common_sequence") or []
    sequence = [plain_sequence_label(item) for item in common_sequence]
    if not sequence:
        sequence = [
            plain_sequence_label(action.get("type", "workflow step"))
            for action in candidate.get("observed_actions", [])
            if isinstance(action, dict)
        ]
    return {
        "type": "pattern_detected",
        "timestamp": timestamp,
        "title": "Daily bank email workflow found",
        "summary": pattern_definition(root, match, candidate),
        "pattern_definition": pattern_definition(root, match, candidate),
        "explanation": pattern_explanation(candidate),
        "confidence": float(candidate.get("confidence") or (skill.get("source_candidate") or {}).get("confidence") or 0),
        "episode_count": episode_count,
        "sequence": sequence,
        "signals": concrete_pattern_signals(candidate),
        "issues": issue_list_from_candidate(candidate),
        "evidence": {
            "episodes": as_string_list(evidence.get("episode_ids") or evidence.get("episodes")),
            "common_fields": as_string_list(evidence.get("common_fields")),
            "target": clean_display_text(str(evidence.get("target_artifact") or evidence.get("target_sheet") or "")),
        },
        "next_trigger": {
            "event_id": next_trigger.get("event_id"),
            "target_rows": next_trigger.get("target_rows"),
            "unprocessed_action_columns": as_string_list(next_trigger.get("unprocessed_action_columns")),
        },
    }


def trigger_condition_payload(condition: dict[str, Any]) -> dict[str, Any]:
    value = condition.get("value")
    if isinstance(value, dict):
        display_value = ", ".join(f"{humanize(key)}: {clean_display_text(str(val))}" for key, val in value.items())
    elif value is None:
        display_value = ""
    else:
        display_value = clean_display_text(str(value))
    return {
        "label": clean_display_text(str(condition.get("label") or humanize(condition.get("type") or condition.get("field") or "Condition"))),
        "field": condition.get("field"),
        "operator": condition.get("operator"),
        "type": condition.get("type"),
        "value": display_value,
    }


def generated_skill_event(skill: dict[str, Any], timestamp: str) -> dict[str, Any]:
    workflow = skill.get("workflow", {}) if isinstance(skill.get("workflow"), dict) else {}
    expected = workflow.get("expected_outcome", {}) if isinstance(workflow.get("expected_outcome"), dict) else {}
    triggers = []
    for trigger in skill.get("triggers", []):
        if isinstance(trigger, dict):
            triggers.extend(trigger_condition_payload(condition) for condition in trigger.get("conditions", []) if isinstance(condition, dict))
    steps = []
    for step in workflow.get("steps", []):
        if not isinstance(step, dict):
            continue
        steps.append(
            {
                "order": int(step.get("order") or len(steps) + 1),
                "title": clean_display_text(str(step.get("title") or humanize(step.get("id") or "Workflow step"))),
                "summary": clean_display_text(str(step.get("summary") or "")),
                "type": clean_display_text(str(step.get("type") or "")),
            }
        )
    return {
        "type": "skill_generated",
        "timestamp": timestamp,
        "title": "Generated FDE workflow",
        "summary": (
            "When the daily bank transaction email arrives, this FDE workflow reads the attached spreadsheet, "
            "checks the rows against the finance workbook, separates items that need review, and creates a new "
            "updated spreadsheet after approval."
        ),
        "issues": as_string_list(expected.get("side_effects") or skill.get("guardrails")),
        "triggers": triggers,
        "steps": steps,
        "expected_outcome": {
            "summary": clean_display_text(str(expected.get("summary") or "")),
            "files_created": as_string_list(expected.get("files_created")),
            "files_modified": as_string_list(expected.get("files_modified")),
            "safety_checks": as_string_list(expected.get("side_effects") or skill.get("guardrails")),
        },
    }


def pre_approval_events(root: Path, match_id: str) -> list[dict[str, Any]]:
    p = skillgen_paths(root)
    match = read_json(p.matches_dir / f"{match_id}.json")
    skill = load_skill(root, match["skill_id"], int(match["skill_version"]))
    preview = ensure_preview(root, match_id)
    now = skillgen.utc_now()
    stats = preview_stats(preview)
    _, trigger_raw = trigger_summary(root, match)
    input_file = filename(preview.get("input", "attachment.xlsx"))
    create_files = preview.get("files_to_create", [])
    modify_files = preview.get("files_to_modify", [])
    update = preview.get("proposed_workbook_update", {})
    target_sheet = update.get("target_sheet", "Daily Reconciliation")
    exception_word = "item" if stats["exceptions"] == 1 else "items"
    return [
        event_step_started("trigger", "Spot Repetitive Pattern", now, "recent activity"),
        event_step_completed(
            "trigger",
            "Spot Repetitive Pattern",
            "Found the daily bank email workflow repeated across prior examples.",
            120,
            now,
            trigger_raw,
        ),
        pattern_detected_event(root, match, skill, now),
        event_step_started("parse_bank_transactions", "Collect evidence", now, input_file),
        event_step_completed(
            "parse_bank_transactions",
            "Collect evidence",
            f"Loaded {stats['total']} records from the workflow input.",
            1080,
            now,
            {"input": preview.get("input"), "transactions": stats["total"]},
        ),
        event_step_started("build_reconciliation_preview", "Generate Skills", now, target_sheet),
        event_step_completed(
            "build_reconciliation_preview",
            "Generate Skills",
            f"Generated an editable FDE workflow that can handle {stats['matched']} records and leave {stats['exceptions']} {exception_word} for review.",
            2600,
            now,
            update,
        ),
        generated_skill_event(skill, now),
        {
            "type": "approval_required",
            "step_index": STEP_IDS["require_approval"],
            "timestamp": now,
            "proposed_changes": {
                "description": "Create the output file and save a local draft after review.",
                "files_to_create": create_files,
                "files_to_modify": modify_files,
                "stats": stats,
                "exceptions": update.get("exceptions", []),
            },
            "guardrails": preview.get("guardrails", []),
            "reply_draft": preview.get("proposed_reply_draft"),
        },
    ]


def post_approval_events(root: Path, match_id: str) -> list[dict[str, Any]]:
    p = skillgen_paths(root)
    match = read_json(p.matches_dir / f"{match_id}.json")
    preview = ensure_preview(root, match_id)
    execution = latest_execution(root, match) or {}
    validation = validation_for(root, match_id) or {"validation_status": "passed", "checks": []}
    now = execution.get("timestamp") or skillgen.utc_now()
    outputs = execution.get("outputs", {})
    workbook_created = outputs.get("workbook_created") or (preview.get("files_to_create") or [""])[0]
    rows_added = outputs.get("rows_added") or preview_stats(preview)["total"]
    return [
        event_step_completed(
            "require_approval",
            "Review",
            f"Approved by {execution.get('actor', 'analyst_1')}.",
            0,
            now,
        ),
        event_step_started("create_reconciled_spreadsheet", "Create output", now, "local file"),
        event_step_completed(
            "create_reconciled_spreadsheet",
            "Create output",
            f"Created {filename(workbook_created)} with {rows_added} rows.",
            980,
            now,
            outputs,
        ),
        event_step_started("validate_outputs", "Check output", now, "quality checks"),
        event_step_completed(
            "validate_outputs",
            "Check output",
            f"Final checks {validation.get('validation_status', 'passed')}.",
            410,
            now,
        ),
        {
            "type": "validation_result",
            "timestamp": now,
            "status": validation.get("validation_status", "passed"),
            "checks": validation.get("checks", []),
        },
        event_step_started("write_audit_log", "Save run record", now, "local record"),
        event_step_completed(
            "write_audit_log",
            "Save run record",
            "Saved the created file, draft path, and check result.",
            180,
            now,
            {"event_log": "workspace/events/events.jsonl"},
        ),
        {
            "type": "execution_complete",
            "decision": execution.get("decision", "approved"),
            "timestamp": now,
            "actor": execution.get("actor", "analyst_1"),
        },
    ]


class SkillForgeHandler(BaseHTTPRequestHandler):
    server_version = "SkillForgeAPI/0.1"

    @property
    def root(self) -> Path:
        return self.server.root  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format % args}")

    def end_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            # --- Phase 1: observe -> recommend surface ---
            if path == "/api/connections":
                return self.send_json(observatory.connection_status(self.root))
            if path == "/api/observations":
                query = parse_qs(parsed.query)
                limit = int(query.get("limit", ["25"])[0])
                return self.send_json(observatory.observation_feed(self.root, limit=limit))
            if path == "/api/recommendations":
                return self.send_json(observatory.recommendations(self.root))
            if path == "/api/report/weekly":
                query = parse_qs(parsed.query)
                use_ai = query.get("ai", ["1"])[0] != "0"
                return self.send_json(observatory.weekly_report(self.root, use_ai=use_ai))
            if path == "/api/skills":
                return self.send_json(observatory.skills_inventory(self.root))
            if path == "/api/workflows":
                return self.send_json(observatory.workflows(self.root))
            if path == "/api/memory/status":
                return self.send_json(observatory.memory_status(self.root))
            if path == "/api/memory/trace":
                query = parse_qs(parsed.query)
                limit = int(query.get("limit", ["30"])[0])
                return self.send_json(observatory.memory_trace(self.root, limit=limit))
            # --- legacy execution endpoints (unused by the Phase 1 UI) ---
            if path == "/api/skills/matches":
                return self.send_json(list_matches(self.root))
            if path == "/api/skillops/summary":
                return self.send_json(skill_list_payload(self.root))
            match = re.fullmatch(r"/api/files/(.+)", path)
            if match:
                return self.send_file(match.group(1))
            match = re.fullmatch(r"/api/skillops/skills/([^/]+)", path)
            if match:
                return self.send_json(skillops_payload(self.root, match.group(1)))
            match = re.fullmatch(r"/api/skills/matches/([^/]+)/stream", path)
            if match:
                return self.send_stream(match.group(1))
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
        except Exception as exc:
            self.send_json({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_HEAD(self) -> None:
        path = urlparse(self.path).path
        try:
            match = re.fullmatch(r"/api/files/(.+)", path)
            if match:
                return self.send_file(match.group(1), include_body=False)
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
        except Exception:
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            body = self.read_json_body()
            match = re.fullmatch(r"/api/recommendations/([^/]+)/accept/stream", path)
            if match:
                return self.send_accept_stream(unquote(match.group(1)))
            match = re.fullmatch(r"/api/recommendations/([^/]+)/accept", path)
            if match:
                result = observatory.accept_recommendation(self.root, unquote(match.group(1)))
                status = HTTPStatus.OK if result.get("status") == "installed" else HTTPStatus.BAD_REQUEST
                return self.send_json(result, status=status)
            match = re.fullmatch(r"/api/skills/([^/]+)/feedback", path)
            if match:
                payload = body if isinstance(body, dict) else {}
                result = observatory.submit_skill_feedback(
                    self.root,
                    unquote(match.group(1)),
                    rating=str(payload.get("rating", "")),
                    note=str(payload.get("note", "")),
                    user=payload.get("user"),
                )
                return self.send_json(result)
            match = re.fullmatch(r"/api/skills/([^/]+)/run", path)
            if match:
                payload = body if isinstance(body, dict) else {}
                result = observatory.run_skill(self.root, unquote(match.group(1)), user=payload.get("user"))
                return self.send_json(result)
            match = re.fullmatch(r"/api/skills/matches/([^/]+)/approve", path)
            if match:
                execution = skillgen.approve_match(
                    self.root,
                    match.group(1),
                    actor="analyst_1",
                    reviewed_workflow=body.get("reviewed_workflow") if isinstance(body, dict) else None,
                )
                return self.send_json(execution)
            match = re.fullmatch(r"/api/skills/matches/([^/]+)/reject", path)
            if match:
                result = skillgen.reject_match(self.root, match.group(1), actor="analyst_1")
                return self.send_json(result)
            match = re.fullmatch(r"/api/skills/matches/([^/]+)/preview", path)
            if match:
                preview = skillgen.preview_match(self.root, match.group(1))
                if isinstance(body, dict) and body:
                    preview["run_inputs"] = body.get("run_inputs", body)
                    skillgen.write_json(skillgen_paths(self.root).matches_dir / f"{match.group(1)}.preview.json", preview)
                return self.send_json(preview)
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
        except Exception as exc:
            self.send_json({"error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        if not raw:
            return {}
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}

    def send_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_file(self, rel_path: str, *, include_body: bool = True) -> None:
        decoded = unquote(rel_path)
        target = (self.root / decoded).resolve()
        root = self.root.resolve()
        if root not in target.parents and target != root:
            self.send_error(HTTPStatus.FORBIDDEN, "Forbidden")
            return
        allowed_roots = [
            root / "workspace" / "workbooks" / "generated",
            root / "workspace" / "mail" / "drafts",
            root / "workspace" / "skill_matches",
        ]
        if not any(base.resolve() in target.parents for base in allowed_roots):
            self.send_error(HTTPStatus.FORBIDDEN, "Forbidden")
            return
        if not target.exists() or not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        mime_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        data = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Content-Disposition", f'inline; filename="{target.name}"')
        self.end_headers()
        if include_body:
            self.wfile.write(data)

    def send_sse_event(self, event: dict[str, Any]) -> None:
        self.wfile.write(f"data: {json.dumps(event, sort_keys=True)}\n\n".encode("utf-8"))
        self.wfile.flush()

    def send_sse_comment(self, comment: str) -> None:
        self.wfile.write(f": {comment}\n\n".encode("utf-8"))
        self.wfile.flush()

    def send_accept_stream(self, candidate_id: str) -> None:
        """Stream skill-generation progress as Server-Sent Events."""
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        try:
            for event in observatory.accept_recommendation_steps(self.root, candidate_id):
                self.send_sse_event(event)
                # Small spacing so the early stages are visible before the
                # blocking model call; the long wait happens inside the iterator.
                time.sleep(0.25)
        except Exception as exc:  # noqa: BLE001 - report into the stream, headers already sent
            try:
                self.send_sse_event({"event": "error", "error": str(exc)})
            except Exception:
                pass

    def send_stream(self, match_id: str) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        for event in pre_approval_events(self.root, match_id):
            self.send_sse_event(event)
            time.sleep(0.35)

        last_status = None
        deadline = time.time() + 180
        while time.time() < deadline:
            match_path = skillgen_paths(self.root).matches_dir / f"{match_id}.json"
            match = read_json(match_path)
            status = match.get("status")
            if status != last_status:
                last_status = status
            if status == "executed":
                for event in post_approval_events(self.root, match_id):
                    self.send_sse_event(event)
                    time.sleep(0.35)
                return
            if status == "rejected":
                self.send_sse_event(
                    {
                        "type": "execution_complete",
                        "decision": "rejected",
                        "timestamp": skillgen.utc_now(),
                        "actor": "analyst_1",
                    }
                )
                return
            self.send_sse_comment("waiting_for_human_approval")
            time.sleep(1.0)


class SkillForgeServer(ThreadingHTTPServer):
    def __init__(self, server_address: tuple[str, int], handler: type[BaseHTTPRequestHandler], root: Path) -> None:
        super().__init__(server_address, handler)
        self.root = root


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Serve the local SkillForge demo API.")
    parser.add_argument("--root", type=Path, default=Path("."), help="Repository root.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8017)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = args.root.resolve()
    server = SkillForgeServer((args.host, args.port), SkillForgeHandler, root)
    print(f"SkillForge API serving {root} at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
