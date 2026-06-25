from pathlib import Path

from skillforge_local.contracts import NormalizedEvent, parse_event
from skillforge_local.episode_builder import build_episodes
from skillforge_local.io_jsonl import read_jsonl, write_jsonl


def _email(
    *,
    event_id: str = "evt_email_acme",
    ts: str = "2026-06-14T09:12:00-07:00",
    actor: str = "fde_engineer",
    message_id: str = "msg_acme_001",
    thread_id: str = "thread_acme",
    intent: str = "customer_implementation_request",
    **payload,
) -> NormalizedEvent:
    return NormalizedEvent(
        event_id=event_id,
        type="email_received",
        ts=ts,
        actor=actor,
        payload={
            "message_id": message_id,
            "thread_id": thread_id,
            "intent": intent,
            "subject": "API onboarding request for Acme",
            "content_summary": "Acme needs API onboarding.",
            **payload,
        },
    )


def _spreadsheet(
    *,
    event_id: str = "evt_sheet_acme",
    ts: str = "2026-06-14T09:15:00-07:00",
    actor: str = "fde_engineer",
    workbook: str = "workbooks/onboarding_tracker.xlsx",
    sheet: str = "Onboarding Tracker",
    changes: dict | None = None,
    **payload,
) -> NormalizedEvent:
    return NormalizedEvent(
        event_id=event_id,
        type="spreadsheet_row_updated",
        ts=ts,
        actor=actor,
        payload={
            "workbook": workbook,
            "sheet": sheet,
            "row": 2,
            "changes": {
                "Customer": "Acme",
                "Contact": "maya@acme.example",
                "Request Type": "API onboarding",
                "Source Email": "msg_acme_001",
                "Thread ID": "thread_acme",
                **(changes or {}),
            },
            **payload,
        },
    )


def _outbound(
    *,
    event_id: str = "evt_msg_acme",
    ts: str = "2026-06-14T09:18:00-07:00",
    actor: str = "fde_engineer",
    message_id: str = "out_acme_001",
    thread_id: str = "thread_acme",
    summary: str = "Acknowledged request and asked for credentials.",
) -> NormalizedEvent:
    return NormalizedEvent(
        event_id=event_id,
        type="outbound_message_created",
        ts=ts,
        actor=actor,
        payload={
            "message_id": message_id,
            "thread_id": thread_id,
            "summary": summary,
            "channel": "local_outbox",
        },
    )


def test_parse_email_received_event():
    event = parse_event(
        {
            "contract_version": 1,
            "type": "email_received",
            "event_id": "evt_email_acme",
            "ts": "2026-06-14T09:12:00-07:00",
            "actor": "fde_engineer",
            "source": "email",
            "object_ref": "imap://INBOX/42",
            "payload": {
                "message_id": "msg_acme_001",
                "thread_id": "thread_acme",
                "intent": "customer_implementation_request",
                "customer": "Acme",
            },
        }
    )

    assert isinstance(event, NormalizedEvent)
    assert event.type == "email_received"
    assert event.payload["thread_id"] == "thread_acme"
    assert event.contract_version == "1"
    assert event.source == "email"
    assert event.object_ref == "imap://INBOX/42"


def test_parse_event_rejects_missing_required_keys():
    try:
        parse_event({"type": "email_received", "payload": {}})
    except ValueError as exc:
        assert "event_id" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_parse_event_rejects_unknown_event_type():
    try:
        parse_event(
            {
                "type": "email_sent",
                "event_id": "evt_email_acme",
                "ts": "2026-06-14T09:12:00-07:00",
                "actor": "fde_engineer",
                "payload": {},
            }
        )
    except ValueError as exc:
        assert "Unsupported event type" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_parse_event_rejects_non_object_payload():
    try:
        parse_event(
            {
                "type": "email_received",
                "event_id": "evt_email_acme",
                "ts": "2026-06-14T09:12:00-07:00",
                "actor": "fde_engineer",
                "payload": [],
            }
        )
    except ValueError as exc:
        assert "payload" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_jsonl_roundtrip(tmp_path: Path):
    path = tmp_path / "events.jsonl"
    records = [{"a": 1}, {"b": 2}]

    write_jsonl(path, records)

    assert read_jsonl(path) == records


def test_build_cash_recon_episode_from_email_sheet_summary_ready_and_message():
    email = _email(
        event_id="email_in_20260612",
        ts="2026-06-12T08:02:00-07:00",
        actor="analyst_1",
        message_id="msg_bank_2026_06_12",
        thread_id="thread_daily_cash_2026_06_12",
        intent="daily_cash_reconciliation_request",
        subject="Daily bank transactions - Jun 12",
        attachment="bank_transactions_2026_06_12.xlsx",
    )
    sheet = _spreadsheet(
        event_id="audit_003",
        ts="2026-06-12T08:42:00-07:00",
        actor="analyst_1",
        workbook="workspace/workbooks/skillforge_finance_demo_cash_recon.xlsx",
        sheet="Daily Reconciliation",
        row=None,
        rows="2:46",
        audit_sequence=[
            "workbook_saved",
            "formula_fill_or_status_update",
            "summary_ready",
        ],
        changes={
            "Workflow": "Daily Cash Reconciliation",
            "Rows Changed": "2:46",
            "Columns Changed": "Notes",
            "Source Email": "msg_bank_2026_06_12",
            "Thread ID": "thread_daily_cash_2026_06_12",
        },
    )
    outbound = _outbound(
        event_id="email_sent_20260612",
        ts="2026-06-12T08:44:00-07:00",
        actor="analyst_1",
        message_id="sent_cash_summary_2026_06_12",
        thread_id="thread_daily_cash_2026_06_12",
        summary="Daily reconciliation complete. 38 matched, 7 exceptions need review.",
    )

    episodes = build_episodes([outbound, sheet, email])

    assert len(episodes) == 1
    episode = episodes[0]
    assert episode.contract_version == "workflow_episode.v1"
    assert episode.episode_id == "episode_msg_bank_2026_06_12"
    assert episode.workflow_family == "daily_cash_reconciliation"
    assert episode.started_at == "2026-06-12T08:02:00-07:00"
    assert episode.ended_at == "2026-06-12T08:44:00-07:00"
    assert episode.trigger_event_id == "email_in_20260612"
    assert episode.event_ids == [
        "email_in_20260612",
        "audit_003",
        "email_sent_20260612",
    ]
    assert [item["type"] for item in episode.timeline] == [
        "email_received",
        "spreadsheet_row_updated",
        "outbound_message_created",
    ]
    assert episode.entities == {
        "customer": "",
        "contact": "",
        "thread_id": "thread_daily_cash_2026_06_12",
        "source_email": "msg_bank_2026_06_12",
        "target_workbook": "workspace/workbooks/skillforge_finance_demo_cash_recon.xlsx",
        "target_sheet": "Daily Reconciliation",
        "spreadsheet_fields": [
            "Customer",
            "Contact",
            "Request Type",
            "Source Email",
            "Thread ID",
            "Workflow",
            "Rows Changed",
            "Columns Changed",
        ],
        "target_rows": "2:46",
        "trigger_subject": "Daily bank transactions - Jun 12",
        "trigger_attachment": "bank_transactions_2026_06_12.xlsx",
        "intent": "daily_cash_reconciliation_request",
        "outbound_summary": "Daily reconciliation complete. 38 matched, 7 exceptions need review.",
        "audit_sequence": [
            "workbook_saved",
            "formula_fill_or_status_update",
            "summary_ready",
        ],
    }
    assert episode.actions == [
        "read inbound request",
        "extract workflow fields",
        "update reconciliation rows",
        "create follow-up message",
    ]
    assert episode.outcome == {
        "status": "completed_by_human",
        "final_artifacts": [
            "workspace/workbooks/skillforge_finance_demo_cash_recon.xlsx"
        ],
    }


def test_build_episode_accepts_nested_extracted_email_fields():
    email = _email(
        extracted={
            "customer": "NestedCo",
            "contact": "ops@nested.example",
            "request_type": "Integration",
        }
    )
    sheet = _spreadsheet()

    episode = build_episodes([sheet, email])[0]

    assert episode.workflow_family == "fde_intake_candidate"
    assert episode.entities["customer"] == "NestedCo"
    assert episode.entities["contact"] == "ops@nested.example"
    assert episode.actions == [
        "read inbound request",
        "extract onboarding fields",
        "update tracker row",
    ]


def test_build_episode_without_outbound_still_creates_episode():
    email = _email(customer="Acme", contact="maya@acme.example")
    sheet = _spreadsheet()

    episode = build_episodes([sheet, email])[0]

    assert episode.ended_at == "2026-06-14T09:15:00-07:00"
    assert episode.event_ids == ["evt_email_acme", "evt_sheet_acme"]
    assert [item["type"] for item in episode.timeline] == [
        "email_received",
        "spreadsheet_row_updated",
    ]
    assert "create follow-up message" not in episode.actions


def test_build_episode_ignores_unsupported_intent():
    episodes = build_episodes(
        [
            _email(intent="billing_question"),
            _spreadsheet(),
        ]
    )

    assert episodes == []


def test_build_episode_ignores_spreadsheet_before_email():
    episodes = build_episodes(
        [
            _spreadsheet(ts="2026-06-14T09:11:00-07:00"),
            _email(ts="2026-06-14T09:12:00-07:00"),
        ]
    )

    assert episodes == []


def test_build_episode_requires_same_actor():
    episodes = build_episodes(
        [
            _email(actor="fde_engineer"),
            _spreadsheet(actor="other_engineer"),
        ]
    )

    assert episodes == []


def test_build_episode_matches_by_thread_id_when_source_email_missing():
    email = _email()
    sheet = _spreadsheet(changes={"Source Email": None, "Thread ID": "thread_acme"})

    episode = build_episodes([sheet, email])[0]

    assert episode.event_ids == ["evt_email_acme", "evt_sheet_acme"]


def test_build_episode_requires_non_empty_link_key():
    email = _email(message_id=None, thread_id=None)
    sheet = _spreadsheet(changes={"Source Email": None, "Thread ID": None})

    assert build_episodes([sheet, email]) == []


def test_build_episode_does_not_fallback_to_thread_id_when_source_email_differs():
    email = _email()
    sheet = _spreadsheet(
        changes={"Source Email": "different_message", "Thread ID": "thread_acme"}
    )

    assert build_episodes([sheet, email]) == []


def test_build_episode_does_not_reuse_fallback_spreadsheet_event():
    first_email = _email(
        event_id="evt_email_first",
        message_id="msg_first",
        thread_id="thread_shared",
    )
    second_email = _email(
        event_id="evt_email_second",
        ts="2026-06-14T09:13:00-07:00",
        message_id="msg_second",
        thread_id="thread_shared",
    )
    sheet = _spreadsheet(
        event_id="evt_sheet_shared",
        changes={"Source Email": None, "Thread ID": "thread_shared"},
    )

    episodes = build_episodes([first_email, second_email, sheet])

    assert len(episodes) == 1
    assert episodes[0].event_ids == ["evt_email_first", "evt_sheet_shared"]
