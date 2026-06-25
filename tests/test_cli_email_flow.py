from pathlib import Path


def test_cli_exposes_imap_poll_and_email_to_excel_commands():
    from autoskill_agent.cli import build_parser

    parser = build_parser()

    imap_args = parser.parse_args(["imap-poll", "--once", "--openclaw-mode", "mock", "--limit", "2", "--latest"])
    excel_args = parser.parse_args(
        [
            "email-to-excel",
            "--workbook",
            "workspace/workbooks/onboarding_tracker.xlsx",
            "--yes",
        ]
    )

    assert imap_args.func.__name__ == "cmd_imap_poll"
    assert imap_args.limit == 2
    assert imap_args.latest is True
    assert excel_args.func.__name__ == "cmd_email_to_excel"


def test_email_to_excel_cli_processes_activity_log(tmp_path: Path):
    from autoskill_agent.cli import build_parser, cmd_email_to_excel
    from skillforge_local.io_jsonl import write_jsonl

    events_log = tmp_path / "events" / "activity_events.jsonl"
    workbook_path = tmp_path / "workbooks" / "onboarding_tracker.xlsx"
    write_jsonl(
        events_log,
        [
            {
                "contract_version": "activity_event.v1",
                "event_id": "evt_email_acme_001",
                "ts": "2026-06-14T09:12:00-07:00",
                "actor": "fde_engineer",
                "source": "email",
                "type": "email_received",
                "object_ref": "imap://INBOX/42",
                "payload": {
                    "message_id": "msg_acme_001",
                    "thread_id": "thread_acme",
                    "from": "maya@acme.example",
                    "subject": "API onboarding request for Acme",
                    "content_summary": "Acme needs API onboarding and credentials are missing.",
                    "openclaw": {
                        "is_match": True,
                        "intent": "customer_implementation_request",
                        "extracted": {
                            "customer": "Acme",
                            "contact": "maya@acme.example",
                            "request_type": "API onboarding",
                            "due_date": "",
                            "blockers": ["Credentials missing"],
                            "next_step": "Ask customer for credentials",
                        },
                    },
                },
            }
        ],
    )
    parser = build_parser()
    args = parser.parse_args(
        [
            "--root",
            str(tmp_path),
            "email-to-excel",
            "--events-log",
            str(events_log),
            "--workbook",
            str(workbook_path),
            "--yes",
        ]
    )
    args.root = tmp_path

    exit_code = cmd_email_to_excel(args)

    assert exit_code == 0
    assert workbook_path.exists()
    assert "spreadsheet_row_updated" in events_log.read_text(encoding="utf-8")
