from __future__ import annotations

import csv
import hashlib
import html
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEMO_DIR = Path("workspace") / "autoskill_demo"
SKILLS_DIR = Path("workspace") / "skills"
STATE_DIR = Path(".runtime") / "autoskill"

TRACKER_COLUMNS = [
    "email_id",
    "received_at",
    "from",
    "customer",
    "subject",
    "email_body",
    "request_type",
    "due_date",
    "blocker",
    "owner",
    "next_step",
    "status",
    "reply_draft",
]

OUTPUT_COLUMNS = [
    "request_type",
    "due_date",
    "blocker",
    "owner",
    "next_step",
    "status",
    "reply_draft",
]

MONTHS = {
    "jan": "01",
    "january": "01",
    "feb": "02",
    "february": "02",
    "mar": "03",
    "march": "03",
    "apr": "04",
    "april": "04",
    "may": "05",
    "jun": "06",
    "june": "06",
    "jul": "07",
    "july": "07",
    "aug": "08",
    "august": "08",
    "sep": "09",
    "sept": "09",
    "september": "09",
    "oct": "10",
    "october": "10",
    "nov": "11",
    "november": "11",
    "dec": "12",
    "december": "12",
}


@dataclass(frozen=True)
class WorkspacePaths:
    root: Path
    demo_dir: Path
    tracker_csv: Path
    completed_csv: Path
    candidate_json: Path
    candidate_md: Path
    registry_json: Path
    skills_dir: Path
    audit_log: Path
    dashboard_html: Path
    drafts_dir: Path


def workspace_paths(root: Path | str = ".") -> WorkspacePaths:
    root_path = Path(root).resolve()
    demo_dir = root_path / DEMO_DIR
    state_dir = root_path / STATE_DIR
    skills_dir = root_path / SKILLS_DIR
    return WorkspacePaths(
        root=root_path,
        demo_dir=demo_dir,
        tracker_csv=demo_dir / "onboarding_tracker.csv",
        completed_csv=demo_dir / "onboarding_tracker.completed.csv",
        candidate_json=state_dir / "candidate.fde-intake-skill.json",
        candidate_md=state_dir / "candidate.fde-intake-skill.md",
        registry_json=skills_dir / "registry.json",
        skills_dir=skills_dir,
        audit_log=demo_dir / "audit.jsonl",
        dashboard_html=demo_dir / "dashboard.html",
        drafts_dir=demo_dir / "drafts",
    )


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        return [dict(row) for row in csv.DictReader(f)]


def write_csv_rows(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    ensure_parent(path)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in columns})


def write_json(path: Path, payload: dict[str, Any]) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def append_audit(path: Path, event: str, payload: dict[str, Any]) -> None:
    ensure_parent(path)
    record = {"ts": utc_now(), "event": event, **payload}
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def init_demo(root: Path | str = ".", force: bool = False) -> WorkspacePaths:
    paths = workspace_paths(root)
    if paths.tracker_csv.exists() and not force:
        return paths

    rows = [
        {
            "email_id": "email-001",
            "received_at": "2026-06-14T09:03:00-07:00",
            "from": "nora@acme.example",
            "customer": "Acme",
            "subject": "SSO metadata blocker for kickoff",
            "email_body": (
                "Acme needs SSO metadata reviewed before kickoff. We are blocked on IdP "
                "metadata and need a security review by June 18."
            ),
            "request_type": "security_review",
            "due_date": "2026-06-18",
            "blocker": "IdP metadata",
            "owner": "Maya",
            "next_step": "Review SSO requirements with Acme",
            "status": "needs_review",
            "reply_draft": "Thanks Nora. Maya will review the SSO requirements and confirm the IdP metadata path.",
        },
        {
            "email_id": "email-002",
            "received_at": "2026-06-14T09:18:00-07:00",
            "from": "dev@globex.example",
            "customer": "Globex",
            "subject": "API field mapping for import",
            "email_body": (
                "Globex needs API field mapping for the first import. We can share sample "
                "payloads after legal approval. Target date is June 20."
            ),
            "request_type": "field_mapping",
            "due_date": "2026-06-20",
            "blocker": "sample payloads",
            "owner": "Ravi",
            "next_step": "Map customer fields and request missing sample payloads",
            "status": "waiting_on_customer",
            "reply_draft": "Thanks Dev. Ravi will start field mapping and we will wait for the sample payloads.",
        },
        {
            "email_id": "email-003",
            "received_at": "2026-06-14T09:37:00-07:00",
            "from": "ops@initech.example",
            "customer": "Initech",
            "subject": "Sandbox tenant request",
            "email_body": (
                "Initech requests a sandbox tenant and import template. Procurement approval "
                "is still pending. They want access by June 19."
            ),
            "request_type": "sandbox_access",
            "due_date": "2026-06-19",
            "blocker": "procurement approval",
            "owner": "Lena",
            "next_step": "Provision sandbox tenant after procurement approval",
            "status": "blocked",
            "reply_draft": "Thanks Ops. Lena will prepare the sandbox tenant once procurement approval lands.",
        },
        {
            "email_id": "email-004",
            "received_at": "2026-06-14T10:04:00-07:00",
            "from": "pm@umbrella.example",
            "customer": "Umbrella",
            "subject": "Need schema and API field mapping",
            "email_body": (
                "Umbrella needs schema and API field mapping for onboarding. We are waiting "
                "on a production-like sample payload. Can we target June 21?"
            ),
        },
        {
            "email_id": "email-005",
            "received_at": "2026-06-14T10:31:00-07:00",
            "from": "security@hooli.example",
            "customer": "Hooli",
            "subject": "Security review and SSO before launch",
            "email_body": (
                "Hooli needs SSO and a security review before launch. Their blocker is a "
                "SOC2 bridge letter. Desired due date is June 24."
            ),
        },
        {
            "email_id": "email-006",
            "received_at": "2026-06-14T11:02:00-07:00",
            "from": "it@soylent.example",
            "customer": "Soylent",
            "subject": "Sandbox access request",
            "email_body": (
                "Soylent is asking for sandbox access and a test tenant. They are blocked "
                "on VPN allowlisting and need access by June 23."
            ),
        },
    ]
    normalized_rows = [{col: row.get(col, "") for col in TRACKER_COLUMNS} for row in rows]

    paths.demo_dir.mkdir(parents=True, exist_ok=True)
    paths.drafts_dir.mkdir(parents=True, exist_ok=True)
    write_csv_rows(paths.tracker_csv, normalized_rows, TRACKER_COLUMNS)

    if paths.audit_log.exists():
        paths.audit_log.unlink()
    append_audit(
        paths.audit_log,
        "demo_initialized",
        {"tracker": str(paths.tracker_csv), "rows": len(normalized_rows)},
    )
    return paths


def is_completed(row: dict[str, str]) -> bool:
    return all(row.get(col, "").strip() for col in OUTPUT_COLUMNS)


def is_pending(row: dict[str, str]) -> bool:
    return bool(row.get("email_body", "").strip()) and not is_completed(row)


def learn_owner_map(rows: list[dict[str, str]]) -> dict[str, str]:
    owner_map: dict[str, str] = {}
    for row in rows:
        request_type = row.get("request_type", "").strip()
        owner = row.get("owner", "").strip()
        if request_type and owner:
            owner_map.setdefault(request_type, owner)
    return owner_map


def observe(root: Path | str = ".", min_examples: int = 3) -> dict[str, Any]:
    paths = workspace_paths(root)
    rows = read_csv_rows(paths.tracker_csv)
    completed = [row for row in rows if is_completed(row)]
    pending = [row for row in rows if is_pending(row)]
    if len(completed) < min_examples:
        raise RuntimeError(f"Need at least {min_examples} completed examples; found {len(completed)}.")
    if not pending:
        raise RuntimeError("No pending rows with email_body and empty generated fields were found.")

    owner_map = learn_owner_map(completed)
    candidate = {
        "id": "fde-intake-skill",
        "name": "FDE Intake Skill",
        "created_at": utc_now(),
        "source": {
            "tracker": str(paths.tracker_csv),
            "completed_examples": len(completed),
            "pending_rows": len(pending),
            "example_hashes": [content_hash(row.get("email_body", "")) for row in completed],
        },
        "trigger": {
            "kind": "tracker_row",
            "when": [
                "row has email_body",
                "one or more generated output columns are empty",
                "email_id has not already been completed by this skill",
            ],
        },
        "learned_behavior": {
            "input_columns": ["email_id", "received_at", "from", "customer", "subject", "email_body"],
            "output_columns": OUTPUT_COLUMNS,
            "owner_map": owner_map,
            "request_types": sorted(owner_map),
        },
        "guardrails": [
            "Never overwrite a non-empty output cell.",
            "Require explicit human approval before writing the completed tracker.",
            "Write an audit log entry for candidate creation, registration, and execution.",
            "Do not access network services during deterministic skill execution.",
            "Keep reply drafts as local files until a human sends them.",
        ],
        "confidence": {
            "score": 0.86,
            "reason": "Three completed examples share the same output columns and map request type to owner.",
        },
    }
    write_json(paths.candidate_json, candidate)
    paths.candidate_md.write_text(render_candidate_markdown(candidate), encoding="utf-8")
    append_audit(paths.audit_log, "skill_candidate_created", {"candidate": candidate["id"]})
    write_dashboard(paths, rows, candidate=candidate, preview=None)
    return candidate


def render_candidate_markdown(candidate: dict[str, Any]) -> str:
    lines = [
        f"# {candidate['name']}",
        "",
        "## Trigger",
        "",
    ]
    lines.extend(f"- {item}" for item in candidate["trigger"]["when"])
    lines.extend(["", "## Learned Behavior", ""])
    lines.append(f"- Completed examples: {candidate['source']['completed_examples']}")
    lines.append(f"- Pending rows: {candidate['source']['pending_rows']}")
    lines.append(f"- Request types: {', '.join(candidate['learned_behavior']['request_types'])}")
    lines.extend(["", "## Guardrails", ""])
    lines.extend(f"- {item}" for item in candidate["guardrails"])
    lines.extend(["", "## Output", ""])
    lines.append("This candidate compiles into a local executable skill plus registry metadata.")
    return "\n".join(lines) + "\n"


def approve_candidate(root: Path | str = ".", approved_by: str = "human") -> dict[str, Any]:
    paths = workspace_paths(root)
    candidate = read_json(paths.candidate_json)
    skill_dir = paths.skills_dir / candidate["id"]
    skill_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "id": candidate["id"],
        "name": candidate["name"],
        "version": "0.1.0",
        "created_at": utc_now(),
        "approved_by": approved_by,
        "entrypoint": "skill.py",
        "trigger": candidate["trigger"],
        "guardrails": candidate["guardrails"],
        "input_columns": candidate["learned_behavior"]["input_columns"],
        "output_columns": candidate["learned_behavior"]["output_columns"],
        "owner_map": candidate["learned_behavior"]["owner_map"],
    }
    write_json(skill_dir / "manifest.json", manifest)
    (skill_dir / "SKILL.md").write_text(render_skill_markdown(manifest), encoding="utf-8")
    (skill_dir / "skill.py").write_text(render_skill_py(), encoding="utf-8")

    registry = {"skills": []}
    if paths.registry_json.exists():
        registry = read_json(paths.registry_json)
    registry["skills"] = [skill for skill in registry.get("skills", []) if skill.get("id") != manifest["id"]]
    registry["skills"].append(
        {
            "id": manifest["id"],
            "name": manifest["name"],
            "version": manifest["version"],
            "path": str(skill_dir),
            "entrypoint": str(skill_dir / "skill.py"),
            "enabled": True,
            "registered_at": utc_now(),
        }
    )
    write_json(paths.registry_json, registry)
    append_audit(paths.audit_log, "skill_registered", {"skill": manifest["id"], "approved_by": approved_by})
    return manifest


def render_skill_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        f"# {manifest['name']}",
        "",
        "Use this skill when a local FDE onboarding tracker has inbound implementation request rows",
        "with blank generated output columns.",
        "",
        "## Trigger",
        "",
    ]
    lines.extend(f"- {item}" for item in manifest["trigger"]["when"])
    lines.extend(["", "## Guardrails", ""])
    lines.extend(f"- {item}" for item in manifest["guardrails"])
    lines.extend(["", "## Execution", ""])
    lines.append("Run from the repository root:")
    lines.append("")
    lines.append("```powershell")
    lines.append("python -m autoskill_agent.cli run --approve")
    lines.append("```")
    return "\n".join(lines) + "\n"


def render_skill_py() -> str:
    return '''from __future__ import annotations

import argparse
from pathlib import Path

from autoskill_agent.core import run_registered_skill


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local FDE intake skill.")
    parser.add_argument("--root", default=".", help="Repository/workspace root.")
    parser.add_argument("--approve", action="store_true", help="Write the completed tracker.")
    args = parser.parse_args()
    run_registered_skill(Path(args.root), approve=args.approve)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def classify_request(text: str) -> str:
    lowered = text.lower()
    if any(term in lowered for term in ["sso", "security", "soc2", "idp"]):
        return "security_review"
    if any(term in lowered for term in ["api", "schema", "field", "mapping", "payload"]):
        return "field_mapping"
    if any(term in lowered for term in ["sandbox", "tenant", "test environment"]):
        return "sandbox_access"
    return "implementation_request"


def extract_due_date(text: str, default_year: str = "2026") -> str:
    iso = re.search(r"\b(20\d{2})-(\d{2})-(\d{2})\b", text)
    if iso:
        return iso.group(0)
    month_day = re.search(
        r"\b("
        + "|".join(MONTHS)
        + r")\s+([0-3]?\d)\b",
        text,
        flags=re.IGNORECASE,
    )
    if month_day:
        month = MONTHS[month_day.group(1).lower()]
        day = int(month_day.group(2))
        return f"{default_year}-{month}-{day:02d}"
    slash = re.search(r"\b([0-1]?\d)/([0-3]?\d)(?:/(20\d{2}))?\b", text)
    if slash:
        month = int(slash.group(1))
        day = int(slash.group(2))
        year = slash.group(3) or default_year
        return f"{year}-{month:02d}-{day:02d}"
    return ""


def extract_blocker(text: str) -> str:
    lowered = text.lower()
    patterns = [
        r"blocked on ([^.]+)",
        r"blocker is ([^.]+)",
        r"waiting on ([^.]+)",
        r"pending ([^.]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, lowered)
        if match:
            value = match.group(1).strip(" .")
            return value
    return "none identified"


def next_step_for(request_type: str, customer: str) -> str:
    templates = {
        "security_review": f"Review SSO/security requirements with {customer}",
        "field_mapping": "Map customer fields and request missing sample payloads",
        "sandbox_access": "Provision sandbox tenant after blocker clears",
        "implementation_request": f"Triage implementation request with {customer}",
    }
    return templates.get(request_type, templates["implementation_request"])


def status_for(blocker: str) -> str:
    if blocker and blocker != "none identified":
        if any(term in blocker for term in ["approval", "allowlisting", "metadata", "letter"]):
            return "blocked"
        return "waiting_on_customer"
    return "needs_review"


def draft_reply(row: dict[str, str], owner: str, request_type: str, blocker: str) -> str:
    customer = row.get("customer", "there")
    first_name = row.get("from", "").split("@")[0].split(".")[0].title() or "there"
    if blocker and blocker != "none identified":
        return (
            f"Thanks {first_name}. {owner} will take the {request_type.replace('_', ' ')} work for "
            f"{customer}. We have noted the current blocker: {blocker}."
        )
    return (
        f"Thanks {first_name}. {owner} will take the {request_type.replace('_', ' ')} work for "
        f"{customer} and confirm the next step."
    )


def propose_row_changes(row: dict[str, str], owner_map: dict[str, str]) -> dict[str, str]:
    text = f"{row.get('subject', '')}\n{row.get('email_body', '')}"
    request_type = classify_request(text)
    blocker = extract_blocker(text)
    owner = owner_map.get(request_type, "FDE triage")
    return {
        "request_type": request_type,
        "due_date": extract_due_date(text),
        "blocker": blocker,
        "owner": owner,
        "next_step": next_step_for(request_type, row.get("customer", "customer")),
        "status": status_for(blocker),
        "reply_draft": draft_reply(row, owner, request_type, blocker),
    }


def build_preview(rows: list[dict[str, str]], owner_map: dict[str, str]) -> list[dict[str, Any]]:
    preview: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=2):
        if not is_pending(row):
            continue
        proposed = propose_row_changes(row, owner_map)
        changes: dict[str, dict[str, str]] = {}
        skipped_existing: list[str] = []
        for col in OUTPUT_COLUMNS:
            existing = row.get(col, "").strip()
            if existing:
                skipped_existing.append(col)
                continue
            value = proposed.get(col, "")
            if value:
                changes[col] = {"from": "", "to": value}
        if changes:
            preview.append(
                {
                    "csv_row": index,
                    "email_id": row.get("email_id", ""),
                    "customer": row.get("customer", ""),
                    "changes": changes,
                    "skipped_existing": skipped_existing,
                }
            )
    return preview


def apply_preview(rows: list[dict[str, str]], preview: list[dict[str, Any]]) -> list[dict[str, str]]:
    by_email = {item["email_id"]: item for item in preview}
    output_rows: list[dict[str, str]] = []
    for row in rows:
        updated = dict(row)
        item = by_email.get(row.get("email_id", ""))
        if item:
            for col, change in item["changes"].items():
                if not updated.get(col, "").strip():
                    updated[col] = change["to"]
        output_rows.append(updated)
    return output_rows


def run_registered_skill(root: Path | str = ".", approve: bool = False) -> dict[str, Any]:
    paths = workspace_paths(root)
    candidate = read_json(paths.candidate_json)
    manifest_path = paths.skills_dir / candidate["id"] / "manifest.json"
    if not manifest_path.exists():
        raise RuntimeError("Skill has not been approved/registered yet. Run approve first.")
    manifest = read_json(manifest_path)
    rows = read_csv_rows(paths.tracker_csv)
    preview = build_preview(rows, manifest.get("owner_map", {}))
    preview_path = paths.demo_dir / "execution_preview.json"
    write_json(preview_path, {"skill": manifest["id"], "changes": preview})
    write_dashboard(paths, rows, candidate=candidate, preview=preview)

    if not approve:
        append_audit(paths.audit_log, "skill_preview_created", {"skill": manifest["id"], "changes": len(preview)})
        return {"preview": preview, "wrote": False, "preview_path": str(preview_path)}

    output_rows = apply_preview(rows, preview)
    write_csv_rows(paths.completed_csv, output_rows, TRACKER_COLUMNS)
    paths.drafts_dir.mkdir(parents=True, exist_ok=True)
    for item in preview:
        draft = item["changes"].get("reply_draft", {}).get("to")
        if draft:
            draft_path = paths.drafts_dir / f"{item['email_id']}.txt"
            draft_path.write_text(draft + "\n", encoding="utf-8")

    append_audit(
        paths.audit_log,
        "skill_executed",
        {
            "skill": manifest["id"],
            "changes": len(preview),
            "output": str(paths.completed_csv),
            "drafts": str(paths.drafts_dir),
        },
    )
    write_dashboard(paths, output_rows, candidate=candidate, preview=preview)
    return {"preview": preview, "wrote": True, "output": str(paths.completed_csv)}


def write_dashboard(
    paths: WorkspacePaths,
    rows: list[dict[str, str]],
    candidate: dict[str, Any] | None,
    preview: list[dict[str, Any]] | None,
) -> None:
    completed = sum(1 for row in rows if is_completed(row))
    pending = sum(1 for row in rows if is_pending(row))
    candidate_status = "not created"
    if candidate:
        candidate_status = f"{candidate['name']} ({candidate['confidence']['score']:.2f})"
    changes = len(preview or [])
    rows_html = []
    for row in rows:
        rows_html.append(
            "<tr>"
            + "".join(
                f"<td>{html.escape(row.get(col, ''))}</td>"
                for col in ["email_id", "customer", "request_type", "due_date", "blocker", "owner", "status"]
            )
            + "</tr>"
        )
    preview_html = []
    for item in preview or []:
        changed_cols = ", ".join(sorted(item["changes"]))
        preview_html.append(
            f"<tr><td>{html.escape(item['email_id'])}</td><td>{html.escape(item['customer'])}</td>"
            f"<td>{html.escape(changed_cols)}</td></tr>"
        )
    if not preview_html:
        preview_html.append("<tr><td colspan=\"3\">No execution preview yet.</td></tr>")

    page = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>SheetSkill Local Dashboard</title>
  <style>
    :root {{ color-scheme: light; font-family: Arial, sans-serif; }}
    body {{ margin: 0; background: #f7f8fa; color: #18202a; }}
    header {{ padding: 24px 32px; background: #ffffff; border-bottom: 1px solid #d8dee8; }}
    main {{ padding: 24px 32px 40px; max-width: 1180px; }}
    h1 {{ font-size: 28px; margin: 0 0 8px; letter-spacing: 0; }}
    h2 {{ font-size: 18px; margin: 28px 0 12px; letter-spacing: 0; }}
    p {{ margin: 0; color: #4d5b6d; }}
    .metrics {{ display: grid; grid-template-columns: repeat(4, minmax(160px, 1fr)); gap: 12px; margin-top: 20px; }}
    .metric {{ background: #ffffff; border: 1px solid #d8dee8; border-radius: 8px; padding: 14px; }}
    .label {{ color: #66758a; font-size: 12px; text-transform: uppercase; }}
    .value {{ font-size: 22px; margin-top: 6px; }}
    table {{ width: 100%; border-collapse: collapse; background: #ffffff; border: 1px solid #d8dee8; }}
    th, td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid #e5e9f0; vertical-align: top; }}
    th {{ background: #eef2f7; font-size: 12px; text-transform: uppercase; color: #465568; }}
    code {{ background: #eef2f7; padding: 2px 5px; border-radius: 4px; }}
  </style>
</head>
<body>
  <header>
    <h1>SheetSkill Local</h1>
    <p>Offline auto-skillizing agent for repeated enterprise spreadsheet workflows.</p>
  </header>
  <main>
    <section class=\"metrics\">
      <div class=\"metric\"><div class=\"label\">Rows</div><div class=\"value\">{len(rows)}</div></div>
      <div class=\"metric\"><div class=\"label\">Completed examples</div><div class=\"value\">{completed}</div></div>
      <div class=\"metric\"><div class=\"label\">Pending rows</div><div class=\"value\">{pending}</div></div>
      <div class=\"metric\"><div class=\"label\">Preview changes</div><div class=\"value\">{changes}</div></div>
    </section>
    <h2>Candidate</h2>
    <p>{html.escape(candidate_status)}</p>
    <h2>Execution Preview</h2>
    <table>
      <thead><tr><th>Email</th><th>Customer</th><th>Generated columns</th></tr></thead>
      <tbody>{''.join(preview_html)}</tbody>
    </table>
    <h2>Tracker</h2>
    <table>
      <thead><tr><th>Email</th><th>Customer</th><th>Type</th><th>Due</th><th>Blocker</th><th>Owner</th><th>Status</th></tr></thead>
      <tbody>{''.join(rows_html)}</tbody>
    </table>
    <h2>Local Artifacts</h2>
    <p><code>{html.escape(str(paths.tracker_csv))}</code></p>
    <p><code>{html.escape(str(paths.completed_csv))}</code></p>
    <p><code>{html.escape(str(paths.audit_log))}</code></p>
  </main>
</body>
</html>
"""
    ensure_parent(paths.dashboard_html)
    paths.dashboard_html.write_text(page, encoding="utf-8")


def status(root: Path | str = ".") -> dict[str, Any]:
    paths = workspace_paths(root)
    rows = read_csv_rows(paths.tracker_csv) if paths.tracker_csv.exists() else []
    registry = read_json(paths.registry_json) if paths.registry_json.exists() else {"skills": []}
    return {
        "root": str(paths.root),
        "tracker_exists": paths.tracker_csv.exists(),
        "candidate_exists": paths.candidate_json.exists(),
        "completed_exists": paths.completed_csv.exists(),
        "rows": len(rows),
        "completed_examples": sum(1 for row in rows if is_completed(row)),
        "pending_rows": sum(1 for row in rows if is_pending(row)),
        "skills": registry.get("skills", []),
    }
