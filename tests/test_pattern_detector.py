import json
from pathlib import Path

from skillforge_local.contracts import WorkflowEpisode
from skillforge_local.pattern_detector import detect_skill_candidates
from skillforge_local.section_a_runner import run_section_a

FDE_FIELDS = [
    "Customer",
    "Contact",
    "Request Type",
    "Due Date",
    "Blocker",
    "Owner",
    "Next Step",
    "Status",
    "Source Email",
    "Thread ID",
]

CASH_RECON_FIELDS = [
    "Amount Diff",
    "Match Status",
    "Exception Reason",
    "Reviewer",
    "Reviewed At",
    "Source Email ID",
    "Notes",
]


def _episode(
    index: int,
    *,
    workflow_family: str = "fde_intake_candidate",
    workbook: str = "workbooks/onboarding_tracker.xlsx",
    sheet: str = "Onboarding Tracker",
    fields: list[str] | None = None,
    include_outbound: bool = True,
    actor: str = "fde_engineer",
    target_rows: str | None = None,
    subject: str = "API onboarding request",
    attachment: str | None = None,
    intent: str = "customer_implementation_request",
    outbound_summary: str = "Created follow-up message.",
    audit_sequence: list[str] | None = None,
    message_id: str | None = None,
    thread_id: str | None = None,
    email_event_id: str | None = None,
    sheet_event_id: str | None = None,
    outbound_event_id: str | None = None,
) -> WorkflowEpisode:
    day = 10 + index
    message_id = message_id or f"msg_{index:03d}"
    thread_id = thread_id or f"thread_{index:03d}"
    email_event_id = email_event_id or f"email_{index:03d}"
    sheet_event_id = sheet_event_id or f"sheet_{index:03d}"
    outbound_event_id = outbound_event_id or f"outbound_{index:03d}"
    timeline = [
        {
            "ts": f"2026-06-{day:02d}T09:00:00-07:00",
            "type": "email_received",
            "summary": f"Received request {message_id}.",
        },
        {
            "ts": f"2026-06-{day:02d}T09:05:00-07:00",
            "type": "spreadsheet_row_updated",
            "summary": "Updated tracker row.",
        },
    ]
    event_ids = [email_event_id, sheet_event_id]
    actions = ["read inbound request", "extract workflow fields", "update tracker row"]
    ended_at = f"2026-06-{day:02d}T09:05:00-07:00"
    if include_outbound:
        timeline.append(
            {
                "ts": f"2026-06-{day:02d}T09:08:00-07:00",
                "type": "outbound_message_created",
                "summary": outbound_summary,
            }
        )
        event_ids.append(outbound_event_id)
        actions.append("create follow-up message")
        ended_at = f"2026-06-{day:02d}T09:08:00-07:00"

    return WorkflowEpisode(
        contract_version="workflow_episode.v1",
        episode_id=f"episode_{message_id}",
        workflow_family=workflow_family,
        actor=actor,
        started_at=f"2026-06-{day:02d}T09:00:00-07:00",
        ended_at=ended_at,
        trigger_event_id=email_event_id,
        event_ids=event_ids,
        timeline=timeline,
        entities={
            "customer": f"Customer {index}",
            "contact": f"ops{index}@example.com",
            "thread_id": thread_id,
            "source_email": message_id,
            "target_workbook": workbook,
            "target_sheet": sheet,
            "spreadsheet_fields": fields or FDE_FIELDS,
            "target_rows": target_rows or str(index + 1),
            "trigger_subject": subject,
            "trigger_attachment": attachment or "",
            "intent": intent,
            "outbound_summary": outbound_summary if include_outbound else "",
            "audit_sequence": audit_sequence or [],
        },
        actions=actions,
        outcome={"status": "completed_by_human", "final_artifacts": [workbook]},
    )


def test_detects_fde_candidate_after_three_similar_episodes():
    candidates = detect_skill_candidates([_episode(1), _episode(2), _episode(3)])

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.contract_version == "section_a.skill_candidate.v1"
    assert candidate.candidate_id == "cand_fde_intake_001"
    assert candidate.name_suggestion == "FDE Intake Skill"
    assert candidate.confidence >= 0.9
    assert candidate.status == "candidate"
    assert candidate.detected_at == "2026-06-13T09:08:00-07:00"
    assert candidate.pattern["workflow_family"] == "fde_intake_candidate"
    assert candidate.pattern["episode_count"] == 3
    assert candidate.pattern["common_sequence"] == [
        "email_received",
        "spreadsheet_row_updated",
        "outbound_message_created",
    ]
    assert candidate.pattern["trigger_signature"]["intent"] == (
        "customer_implementation_request"
    )
    assert candidate.evidence["episode_ids"] == [
        "episode_msg_001",
        "episode_msg_002",
        "episode_msg_003",
    ]
    assert candidate.evidence["source_event_ids"] == [
        "email_001",
        "sheet_001",
        "outbound_001",
        "email_002",
        "sheet_002",
        "outbound_002",
        "email_003",
        "sheet_003",
        "outbound_003",
    ]
    assert candidate.evidence["target_artifact"] == "workbooks/onboarding_tracker.xlsx"
    assert candidate.evidence["target_sheet"] == "Onboarding Tracker"
    assert candidate.evidence["common_fields"] == FDE_FIELDS
    assert candidate.suggested_skill["inputs"] == [
        "inbound customer implementation email",
        "Onboarding Tracker sheet",
    ]
    assert "send email automatically" in candidate.suggested_skill["forbidden_actions"]
    assert candidate.handoff["next_owner"] == "section_b_skill_creation"


def test_does_not_detect_candidate_with_two_episodes():
    assert detect_skill_candidates([_episode(1), _episode(2)]) == []


def test_does_not_detect_candidate_without_outbound_messages():
    episodes = [
        _episode(1, include_outbound=False),
        _episode(2, include_outbound=False),
        _episode(3, include_outbound=False),
    ]

    assert detect_skill_candidates(episodes) == []


def test_does_not_detect_candidate_for_different_workbooks():
    episodes = [
        _episode(1, workbook="workbooks/a.xlsx"),
        _episode(2, workbook="workbooks/b.xlsx"),
        _episode(3, workbook="workbooks/c.xlsx"),
    ]

    assert detect_skill_candidates(episodes) == []


def test_does_not_detect_candidate_when_required_fields_missing():
    episodes = [
        _episode(1, fields=FDE_FIELDS[:-1]),
        _episode(2, fields=FDE_FIELDS[:-1]),
        _episode(3, fields=FDE_FIELDS[:-1]),
    ]

    assert detect_skill_candidates(episodes) == []


def test_does_not_detect_fde_candidate_when_intents_are_mixed():
    episodes = [
        _episode(1, intent="customer_implementation_request"),
        _episode(2, intent="onboarding_request"),
        _episode(3, intent="integration_request"),
    ]

    assert detect_skill_candidates(episodes) == []


def test_candidate_ids_are_unique_across_multiple_valid_fde_groups():
    episodes = [
        _episode(1, workbook="workbooks/onboarding_a.xlsx"),
        _episode(2, workbook="workbooks/onboarding_a.xlsx"),
        _episode(3, workbook="workbooks/onboarding_a.xlsx"),
        _episode(4, workbook="workbooks/onboarding_b.xlsx"),
        _episode(5, workbook="workbooks/onboarding_b.xlsx"),
        _episode(6, workbook="workbooks/onboarding_b.xlsx"),
    ]

    candidates = detect_skill_candidates(episodes)

    candidate_ids = [candidate.candidate_id for candidate in candidates]
    assert len(candidate_ids) == 2
    assert len(set(candidate_ids)) == 2


def test_detects_cash_reconciliation_candidate_for_section_b_handoff():
    episodes = [
        _cash_episode(2, actor="analyst_1"),
        _cash_episode(3, actor="analyst_2"),
        _cash_episode(4, actor="analyst_1"),
    ]

    candidates = detect_skill_candidates(episodes)

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.candidate_id == "cand_daily_cash_recon_001"
    assert candidate.name_suggestion == "Daily Cash Reconciliation Skill"
    assert candidate.confidence == 0.95
    assert candidate.pattern["workflow_family"] == "daily_cash_reconciliation"
    assert candidate.pattern["trigger_signature"] == {
        "subject_prefix": "Daily bank transactions - Jun",
        "attachment_glob": "bank_transactions_*.xlsx",
        "intent": "daily_cash_reconciliation_request",
    }
    assert candidate.evidence["target_rows_examples"] == ["2:46", "47:91", "92:136"]
    assert candidate.evidence["daily_batch_size"] == 45
    assert candidate.next_trigger == {
        "event_id": "email_in_20260615",
        "message_id": "msg_bank_2026_06_15",
        "thread_id": "thread_daily_cash_2026_06_15",
        "target_rows": "137:181",
        "unprocessed_action_columns": [
            "Match Status",
            "Exception Reason",
            "Reviewer",
            "Reviewed At",
            "Source Email ID",
            "Skill Run ID",
        ],
    }
    assert candidate.suggested_skill["trigger"] == "new daily bank transaction email"
    assert "Payment Export sheet" in candidate.suggested_skill["inputs"]
    assert "send email automatically" in candidate.suggested_skill["forbidden_actions"]
    assert candidate.handoff["required_confirmation_fields"] == [
        "skill_name",
        "owner_role",
        "trigger_conditions",
        "allowed_actions",
        "forbidden_actions",
        "approval_mode",
        "success_criteria",
    ]


def _cash_episode(index: int, **overrides) -> WorkflowEpisode:
    day = 10 + index
    date_token = f"2026_06_{day:02d}"
    audit_sequence = overrides.get(
        "audit_sequence",
        [
            "workbook_saved",
            "formula_fill_or_status_update",
            "summary_ready",
        ],
    )
    return _episode(
        index,
        workflow_family=str(
            overrides.get("workflow_family", "daily_cash_reconciliation")
        ),
        workbook=str(
            overrides.get(
                "workbook",
                "workspace/workbooks/skillforge_finance_demo_cash_recon.xlsx",
            )
        ),
        sheet=str(overrides.get("sheet", "Daily Reconciliation")),
        fields=overrides.get("fields", CASH_RECON_FIELDS),
        actor=str(overrides.get("actor", "analyst_1")),
        target_rows=str(overrides.get("target_rows", _cash_target_rows(index))),
        subject=str(overrides.get("subject", f"Daily bank transactions - Jun {day}")),
        attachment=str(
            overrides.get("attachment", f"bank_transactions_2026_06_{day:02d}.xlsx")
        ),
        intent=str(overrides.get("intent", "daily_cash_reconciliation_request")),
        message_id=str(overrides.get("message_id", f"msg_bank_{date_token}")),
        thread_id=str(overrides.get("thread_id", f"thread_daily_cash_{date_token}")),
        email_event_id=str(
            overrides.get("email_event_id", f"email_in_{date_token.replace('_', '')}")
        ),
        sheet_event_id=str(overrides.get("sheet_event_id", f"audit_{index:03d}")),
        outbound_event_id=str(
            overrides.get(
                "outbound_event_id",
                f"email_sent_{date_token.replace('_', '')}",
            )
        ),
        outbound_summary=str(
            overrides.get(
                "outbound_summary",
                (
                    f"Daily reconciliation complete. {40 - index} matched, "
                    f"{5 + index} exceptions need review."
                ),
            )
        ),
        audit_sequence=audit_sequence,
    )


def _cash_target_rows(index: int) -> str:
    start = 2 + (index - 2) * 45
    end = start + 44
    return f"{start}:{end}"


def test_does_not_detect_cash_candidate_when_subject_prefix_differs():
    episodes = [
        _cash_episode(2),
        _cash_episode(3, subject="Cash export ready - Jun 13"),
        _cash_episode(4),
    ]

    assert detect_skill_candidates(episodes) == []


def test_does_not_detect_cash_candidate_when_attachment_glob_differs():
    episodes = [
        _cash_episode(2),
        _cash_episode(3, attachment="transactions_2026_06_13.csv"),
        _cash_episode(4),
    ]

    assert detect_skill_candidates(episodes) == []


def test_does_not_detect_cash_candidate_when_batch_is_not_45_rows():
    episodes = [
        _cash_episode(2),
        _cash_episode(3, target_rows="47:90"),
        _cash_episode(4),
    ]

    assert detect_skill_candidates(episodes) == []


def test_does_not_detect_cash_candidate_when_outbound_summary_shape_differs():
    episodes = [
        _cash_episode(2),
        _cash_episode(3, outbound_summary="Reconciliation done."),
        _cash_episode(4),
    ]

    assert detect_skill_candidates(episodes) == []


def test_does_not_detect_cash_candidate_when_audit_sequence_differs():
    episodes = [
        _cash_episode(2),
        _cash_episode(3, audit_sequence=["workbook_saved", "summary_ready"]),
        _cash_episode(4),
    ]

    assert detect_skill_candidates(episodes) == []


def test_cash_next_trigger_is_derived_from_latest_episode():
    episodes = [
        _cash_episode(10, target_rows="1000:1044"),
        _cash_episode(11, target_rows="1045:1089"),
        _cash_episode(12, target_rows="1090:1134"),
    ]

    candidates = detect_skill_candidates(episodes)

    assert len(candidates) == 1
    assert candidates[0].next_trigger == {
        "event_id": "email_in_20260623",
        "message_id": "msg_bank_2026_06_23",
        "thread_id": "thread_daily_cash_2026_06_23",
        "target_rows": "1135:1179",
        "unprocessed_action_columns": [
            "Match Status",
            "Exception Reason",
            "Reviewer",
            "Reviewed At",
            "Source Email ID",
            "Skill Run ID",
        ],
    }


def test_cash_next_trigger_is_omitted_for_malformed_latest_date():
    episodes = [
        _cash_episode(2),
        _cash_episode(3),
        _cash_episode(
            4,
            message_id="msg_bank_2026_06_31",
            thread_id="thread_daily_cash_2026_06_31",
            email_event_id="email_in_20260631",
        ),
    ]

    candidates = detect_skill_candidates(episodes)

    assert len(candidates) == 1
    assert candidates[0].next_trigger is None


def test_runner_writes_episode_and_candidate_outputs(tmp_path: Path):
    events_path = Path("tests/fixtures/fde_intake_events.jsonl")
    episodes_path = tmp_path / "workflow_episodes.jsonl"
    candidates_path = tmp_path / "skill_candidates.jsonl"

    run_section_a(events_path, episodes_path, candidates_path)

    episode_lines = episodes_path.read_text(encoding="utf-8").splitlines()
    candidate_lines = candidates_path.read_text(encoding="utf-8").splitlines()

    assert len(episode_lines) == 3
    assert len(candidate_lines) == 1
    assert '"candidate_id": "cand_fde_intake_001"' in candidate_lines[0]
    assert '"next_trigger"' not in candidate_lines[0]


def test_runner_writes_cash_recon_candidate_output(tmp_path: Path):
    events_path = Path("tests/fixtures/cash_recon_events.jsonl")
    episodes_path = tmp_path / "workflow_episodes.jsonl"
    candidates_path = tmp_path / "skill_candidates.jsonl"

    run_section_a(events_path, episodes_path, candidates_path)

    episodes = [
        json.loads(line)
        for line in episodes_path.read_text(encoding="utf-8").splitlines()
    ]
    candidates = [
        json.loads(line)
        for line in candidates_path.read_text(encoding="utf-8").splitlines()
    ]

    assert len(episodes) == 3
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate["candidate_id"] == "cand_daily_cash_recon_001"
    assert candidate["evidence"]["source_event_ids"] == [
        "email_in_20260612",
        "audit_003",
        "email_sent_20260612",
        "email_in_20260613",
        "audit_006",
        "email_sent_20260613",
        "email_in_20260614",
        "audit_009",
        "email_sent_20260614",
    ]
    assert candidate["next_trigger"] == {
        "event_id": "email_in_20260615",
        "message_id": "msg_bank_2026_06_15",
        "thread_id": "thread_daily_cash_2026_06_15",
        "target_rows": "137:181",
        "unprocessed_action_columns": [
            "Match Status",
            "Exception Reason",
            "Reviewer",
            "Reviewed At",
            "Source Email ID",
            "Skill Run ID",
        ],
    }


def test_runner_rejects_invalid_event_file(tmp_path: Path):
    events_path = tmp_path / "bad_events.jsonl"
    events_path.write_text(
        '{"type": "email_received", "payload": {}}\n', encoding="utf-8"
    )

    try:
        run_section_a(
            events_path,
            tmp_path / "workflow_episodes.jsonl",
            tmp_path / "skill_candidates.jsonl",
        )
    except ValueError as exc:
        assert "event_id" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
