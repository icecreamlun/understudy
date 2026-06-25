from __future__ import annotations

from typing import Any

from skillforge_local.contracts import NormalizedEvent, WorkflowEpisode

SUPPORTED_INTENTS = {
    "customer_implementation_request",
    "onboarding_request",
    "integration_request",
    "daily_cash_reconciliation_request",
}

CASH_RECON_INTENT = "daily_cash_reconciliation_request"
WORKFLOW_EPISODE_VERSION = "workflow_episode.v1"


def build_episodes(events: list[NormalizedEvent]) -> list[WorkflowEpisode]:
    ordered_events = sorted(events, key=lambda event: event.ts)
    episodes: list[WorkflowEpisode] = []
    used_spreadsheet_event_ids: set[str] = set()
    used_outbound_event_ids: set[str] = set()

    for email in ordered_events:
        if email.type != "email_received":
            continue

        intent = email.payload.get("intent")
        if intent not in SUPPORTED_INTENTS:
            continue

        spreadsheet = _find_matching_spreadsheet(
            email,
            ordered_events,
            used_spreadsheet_event_ids,
        )
        if spreadsheet is None:
            continue

        outbound = _find_matching_outbound(
            email,
            spreadsheet,
            ordered_events,
            used_outbound_event_ids,
        )
        episodes.append(_build_episode(email, spreadsheet, outbound))
        used_spreadsheet_event_ids.add(spreadsheet.event_id)
        if outbound is not None:
            used_outbound_event_ids.add(outbound.event_id)

    return sorted(episodes, key=lambda episode: episode.started_at)


def _find_matching_spreadsheet(
    email: NormalizedEvent,
    events: list[NormalizedEvent],
    used_event_ids: set[str],
) -> NormalizedEvent | None:
    primary_matches: list[NormalizedEvent] = []
    fallback_matches: list[NormalizedEvent] = []
    message_id = email.payload.get("message_id")
    thread_id = email.payload.get("thread_id")

    for event in events:
        if event.type != "spreadsheet_row_updated":
            continue
        if event.event_id in used_event_ids:
            continue
        if event.actor != email.actor or event.ts < email.ts:
            continue

        changes = event.payload.get("changes")
        if not isinstance(changes, dict):
            continue

        source_email = changes.get("Source Email")
        thread_link = changes.get("Thread ID")
        if source_email and message_id and source_email == message_id:
            primary_matches.append(event)
        elif not source_email and thread_id and thread_link == thread_id:
            fallback_matches.append(event)

    if primary_matches:
        return primary_matches[0]
    if fallback_matches:
        return fallback_matches[0]
    return None


def _find_matching_outbound(
    email: NormalizedEvent,
    spreadsheet: NormalizedEvent,
    events: list[NormalizedEvent],
    used_event_ids: set[str],
) -> NormalizedEvent | None:
    thread_id = email.payload.get("thread_id")

    for event in events:
        if event.type != "outbound_message_created":
            continue
        if event.event_id in used_event_ids:
            continue
        if event.actor != email.actor or event.ts < spreadsheet.ts:
            continue
        if event.payload.get("thread_id") == thread_id:
            return event

    return None


def _build_episode(
    email: NormalizedEvent,
    spreadsheet: NormalizedEvent,
    outbound: NormalizedEvent | None,
) -> WorkflowEpisode:
    workflow_family = _workflow_family(email)
    episode_events = [email, spreadsheet]
    if outbound is not None:
        episode_events.append(outbound)

    workbook = _string_or_empty(spreadsheet.payload.get("workbook"))
    actions = [
        "read inbound request",
        _extract_action(workflow_family),
        _spreadsheet_action(workflow_family),
    ]
    if outbound is not None:
        actions.append("create follow-up message")

    return WorkflowEpisode(
        contract_version=WORKFLOW_EPISODE_VERSION,
        episode_id=f"episode_{email.payload.get('message_id')}",
        workflow_family=workflow_family,
        actor=email.actor,
        started_at=email.ts,
        ended_at=outbound.ts if outbound is not None else spreadsheet.ts,
        trigger_event_id=email.event_id,
        event_ids=[event.event_id for event in episode_events],
        timeline=[_timeline_entry(event, workflow_family) for event in episode_events],
        entities={
            "customer": _payload_field(email.payload, "customer"),
            "contact": _payload_field(email.payload, "contact"),
            "thread_id": _string_or_empty(email.payload.get("thread_id")),
            "source_email": _string_or_empty(email.payload.get("message_id")),
            "target_workbook": workbook,
            "target_sheet": _string_or_empty(spreadsheet.payload.get("sheet")),
            "spreadsheet_fields": _spreadsheet_fields(spreadsheet),
            "target_rows": _target_rows(spreadsheet),
            "trigger_subject": _string_or_empty(email.payload.get("subject")),
            "trigger_attachment": _trigger_attachment(email),
            "intent": _string_or_empty(email.payload.get("intent")),
            "outbound_summary": _outbound_summary(outbound),
            "audit_sequence": _audit_sequence(spreadsheet),
        },
        actions=actions,
        outcome={
            "status": "completed_by_human",
            "final_artifacts": [workbook] if workbook else [],
        },
    )


def _workflow_family(email: NormalizedEvent) -> str:
    if email.payload.get("intent") == CASH_RECON_INTENT:
        return "daily_cash_reconciliation"
    return "fde_intake_candidate"


def _spreadsheet_action(workflow_family: str) -> str:
    if workflow_family == "daily_cash_reconciliation":
        return "update reconciliation rows"
    return "update tracker row"


def _extract_action(workflow_family: str) -> str:
    if workflow_family == "daily_cash_reconciliation":
        return "extract workflow fields"
    return "extract onboarding fields"


def _timeline_entry(
    event: NormalizedEvent,
    workflow_family: str,
) -> dict[str, Any]:
    return {
        "ts": event.ts,
        "type": event.type,
        "summary": _timeline_summary(event, workflow_family),
    }


def _timeline_summary(event: NormalizedEvent, workflow_family: str) -> str:
    if event.type == "email_received":
        if workflow_family == "daily_cash_reconciliation":
            source_email = _string_or_empty(event.payload.get("message_id"))
            return f"Received daily cash reconciliation request {source_email}."

        customer = _payload_field(event.payload, "customer") or "unknown customer"
        return f"Received inbound workflow request for {customer}."

    if event.type == "spreadsheet_row_updated":
        if workflow_family == "daily_cash_reconciliation":
            rows = event.payload.get("rows") or event.payload.get("row") or ""
            return f"Updated reconciliation rows {rows}."

        row = event.payload.get("row") or ""
        return f"Updated tracker row {row}."

    if event.type == "outbound_message_created":
        thread_id = _string_or_empty(event.payload.get("thread_id"))
        return f"Created follow-up message for {thread_id}."

    return f"Observed {event.type}."


def _payload_field(payload: dict[str, Any], field: str) -> str:
    if field in payload:
        return _string_or_empty(payload.get(field))

    extracted = payload.get("extracted")
    if isinstance(extracted, dict):
        return _string_or_empty(extracted.get(field))

    return ""


def _spreadsheet_fields(event: NormalizedEvent) -> list[str]:
    changes = event.payload.get("changes")
    if not isinstance(changes, dict):
        return []
    return [str(field) for field in changes.keys()]


def _target_rows(event: NormalizedEvent) -> str:
    rows = event.payload.get("rows")
    if rows:
        return _string_or_empty(rows)
    return _string_or_empty(event.payload.get("row"))


def _trigger_attachment(event: NormalizedEvent) -> str:
    attachment = event.payload.get("attachment")
    if attachment:
        return _string_or_empty(attachment)

    attachments = event.payload.get("attachments")
    if isinstance(attachments, list) and attachments:
        return _string_or_empty(attachments[0])

    return ""


def _outbound_summary(event: NormalizedEvent | None) -> str:
    if event is None:
        return ""
    return _string_or_empty(event.payload.get("summary"))


def _audit_sequence(event: NormalizedEvent) -> list[str]:
    sequence = event.payload.get("audit_sequence")
    if not isinstance(sequence, list):
        return []
    return [_string_or_empty(item) for item in sequence if _string_or_empty(item)]


def _string_or_empty(value: Any) -> str:
    if value is None:
        return ""
    return str(value)
