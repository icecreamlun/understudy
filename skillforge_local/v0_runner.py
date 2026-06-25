from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from skillforge_local.excel_writer import (
    append_onboarding_row,
    build_row_preview,
    ensure_onboarding_tracker,
)
from skillforge_local.io_jsonl import append_jsonl, read_jsonl


def process_email_event_to_excel(
    event: dict,
    workbook_path: Path,
    *,
    approved: bool,
    preview_log_path: Path | None = None,
    audit_log_path: Path | None = None,
    activity_log_path: Path | None = None,
) -> dict:
    extraction = _extraction_from_event(event)
    if not extraction["is_match"]:
        return {"status": "ignored", "reason": "email_not_matching_target_activity"}

    preview = build_row_preview(event, extraction)
    if not approved:
        result = {"status": "preview", "row": preview}
        if preview_log_path:
            append_jsonl(
                preview_log_path,
                {
                    "contract_version": "execution_preview.v1",
                    "source_event_id": event.get("event_id", ""),
                    "status": "preview",
                    "row": preview,
                },
            )
        return result

    ensure_onboarding_tracker(workbook_path)
    row_number = append_onboarding_row(workbook_path, preview)
    result = {
        "status": "written",
        "row_number": row_number,
        "row": preview,
    }
    spreadsheet_event = build_spreadsheet_activity_event(event, workbook_path, row_number, preview)
    if activity_log_path:
        append_jsonl(activity_log_path, spreadsheet_event)
    if audit_log_path:
        append_jsonl(
            audit_log_path,
            {
                "contract_version": "audit_event.v1",
                "source_event_id": event.get("event_id", ""),
                "action": "append_onboarding_tracker_row",
                "status": "written",
                "workbook": str(workbook_path),
                "row_number": row_number,
                "source_email": preview["Source Email"],
                "thread_id": preview["Thread ID"],
                "spreadsheet_event_id": spreadsheet_event["event_id"],
            },
        )
    return result


def process_activity_log_to_excel(
    events_log: Path,
    workbook_path: Path,
    *,
    approved: bool,
    preview_log_path: Path | None = None,
    audit_log_path: Path | None = None,
) -> list[dict]:
    events = [event for event in read_jsonl(events_log) if event.get("type") == "email_received"]
    results = []
    for event in events:
        try:
            result = process_email_event_to_excel(
                event,
                workbook_path,
                approved=approved,
                preview_log_path=preview_log_path,
                audit_log_path=audit_log_path,
                activity_log_path=events_log,
            )
        except ValueError as exc:
            result = {"status": "error", "reason": str(exc), "source_event_id": event.get("event_id", "")}
        results.append(result)
    return results


def build_spreadsheet_activity_event(
    email_event: dict,
    workbook_path: Path,
    row_number: int,
    row: dict,
) -> dict:
    source_event_id = email_event.get("event_id", "email_unknown")
    return {
        "contract_version": "activity_event.v1",
        "event_id": f"sheet_{source_event_id}",
        "ts": _utc_now(),
        "actor": email_event.get("actor", "fde_engineer"),
        "source": "excel",
        "type": "spreadsheet_row_updated",
        "object_ref": f"xlsx://{workbook_path}#Onboarding Tracker!{row_number}",
        "payload": {
            "workbook": str(workbook_path),
            "sheet": "Onboarding Tracker",
            "row": row_number,
            "changes": row,
        },
    }


def _extraction_from_event(event: dict) -> dict:
    payload = event.get("payload", {})
    openclaw = payload.get("openclaw")
    if isinstance(openclaw, dict):
        return openclaw
    if payload.get("intent") == "customer_implementation_request" and isinstance(payload.get("extracted"), dict):
        return {
            "is_match": True,
            "intent": payload["intent"],
            "extracted": payload["extracted"],
        }
    return {"is_match": False, "intent": "unknown", "extracted": {}}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def main() -> None:
    parser = argparse.ArgumentParser(description="Process OpenClaw-enriched email activity events into Excel.")
    parser.add_argument("--workbook", type=Path, required=True)
    parser.add_argument(
        "--events-log",
        type=Path,
        default=Path("workspace/events/activity_events.jsonl"),
    )
    parser.add_argument(
        "--preview-log",
        type=Path,
        default=Path("workspace/events/execution_previews.jsonl"),
    )
    parser.add_argument(
        "--audit-log",
        type=Path,
        default=Path("workspace/events/audit_log.jsonl"),
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Approve workbook writes without prompting for demo use.",
    )
    args = parser.parse_args()
    ensure_onboarding_tracker(args.workbook)
    for result in process_activity_log_to_excel(
        args.events_log,
        args.workbook,
        approved=args.yes,
        preview_log_path=args.preview_log,
        audit_log_path=args.audit_log,
    ):
        print(result["status"])


if __name__ == "__main__":
    main()
