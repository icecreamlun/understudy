from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from skillforge_local.contracts import SkillCandidate, WorkflowEpisode

SECTION_A_CANDIDATE_VERSION = "section_a.skill_candidate.v1"
MIN_EPISODES = 3

FDE_WORKFLOW_FAMILY = "fde_intake_candidate"
CASH_RECON_WORKFLOW_FAMILY = "daily_cash_reconciliation"

FDE_REQUIRED_FIELDS = [
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

CASH_RECON_REQUIRED_FIELDS = [
    "Amount Diff",
    "Match Status",
    "Exception Reason",
    "Reviewer",
    "Reviewed At",
    "Source Email ID",
    "Notes",
]

CASH_RECON_AUDIT_SEQUENCE = [
    "workbook_saved",
    "formula_fill_or_status_update",
    "summary_ready",
]

HANDOFF_CONFIRMATION_FIELDS = [
    "skill_name",
    "owner_role",
    "trigger_conditions",
    "allowed_actions",
    "forbidden_actions",
    "approval_mode",
    "success_criteria",
]


def detect_skill_candidates(episodes: list[WorkflowEpisode]) -> list[SkillCandidate]:
    grouped: dict[tuple[str, str, str, tuple[str, ...], str], list[WorkflowEpisode]] = (
        defaultdict(list)
    )

    for episode in episodes:
        if episode.workflow_family not in {
            FDE_WORKFLOW_FAMILY,
            CASH_RECON_WORKFLOW_FAMILY,
        }:
            continue

        sequence = tuple(_episode_sequence(episode))
        if "outbound_message_created" not in sequence:
            continue

        workbook = _string_or_empty(episode.entities.get("target_workbook"))
        sheet = _string_or_empty(episode.entities.get("target_sheet"))
        if not workbook or not sheet:
            continue

        trigger_key = _trigger_group_key(episode)
        if not trigger_key:
            continue

        grouped[
            (episode.workflow_family, workbook, sheet, sequence, trigger_key)
        ].append(episode)

    candidates = []
    for (
        workflow_family,
        workbook,
        sheet,
        sequence,
        trigger_key,
    ), group in grouped.items():
        if len(group) < MIN_EPISODES:
            continue

        ordered_group = sorted(group, key=lambda episode: episode.started_at)
        required_fields = _required_fields_for(workflow_family)
        common_fields = _common_fields(ordered_group, required_fields)
        if common_fields != required_fields:
            continue

        if workflow_family == CASH_RECON_WORKFLOW_FAMILY:
            if not _cash_reconciliation_signals_match(ordered_group):
                continue
            candidates.append(
                _cash_reconciliation_candidate(
                    ordered_group,
                    workbook,
                    sheet,
                    sequence,
                    trigger_key,
                )
            )
        else:
            candidates.append(
                _fde_intake_candidate(
                    ordered_group,
                    workbook,
                    sheet,
                    sequence,
                    trigger_key,
                )
            )

    return sorted(candidates, key=lambda candidate: candidate.candidate_id)


def _fde_intake_candidate(
    episodes: list[WorkflowEpisode],
    workbook: str,
    sheet: str,
    sequence: tuple[str, ...],
    trigger_key: str,
) -> SkillCandidate:
    return SkillCandidate(
        contract_version=SECTION_A_CANDIDATE_VERSION,
        candidate_id=_candidate_id(
            prefix="cand_fde_intake",
            canonical_id="cand_fde_intake_001",
            canonical_workbook="workbooks/onboarding_tracker.xlsx",
            canonical_sheet="Onboarding Tracker",
            workbook=workbook,
            sheet=sheet,
            trigger_key=trigger_key,
        ),
        name_suggestion="FDE Intake Skill",
        confidence=_confidence(len(episodes), len(FDE_REQUIRED_FIELDS)),
        status="candidate",
        detected_at=max(episode.ended_at for episode in episodes),
        pattern={
            "workflow_family": FDE_WORKFLOW_FAMILY,
            "episode_count": len(episodes),
            "common_sequence": list(sequence),
            "trigger_signature": {
                "intent": trigger_key,
                "subject_contains": "onboarding",
            },
            "similarity_reason": [
                "same inbound email intent",
                "same target workbook",
                "same target sheet",
                "same tracker columns",
                "similar outbound follow-up message",
            ],
        },
        evidence={
            "episode_ids": [episode.episode_id for episode in episodes],
            "source_event_ids": _source_event_ids(episodes),
            "target_artifact": workbook,
            "target_sheet": sheet,
            "target_rows_examples": _target_rows_examples(episodes),
            "common_fields": FDE_REQUIRED_FIELDS,
        },
        suggested_skill={
            "trigger": "new customer implementation email",
            "inputs": [
                "inbound customer implementation email",
                f"{sheet} sheet",
            ],
            "actions": [
                "extract fields",
                "preview tracker row",
                "draft local reply",
                "ask approval",
                "write row",
                "write audit log",
            ],
            "forbidden_actions": [
                "send email automatically",
                "access network",
                "read outside approved workspace",
                "overwrite existing tracker rows",
            ],
        },
        handoff=_handoff(),
    )


def _cash_reconciliation_candidate(
    episodes: list[WorkflowEpisode],
    workbook: str,
    sheet: str,
    sequence: tuple[str, ...],
    trigger_key: str,
) -> SkillCandidate:
    return SkillCandidate(
        contract_version=SECTION_A_CANDIDATE_VERSION,
        candidate_id=_candidate_id(
            prefix="cand_daily_cash_recon",
            canonical_id="cand_daily_cash_recon_001",
            canonical_workbook="workspace/workbooks/skillforge_finance_demo_cash_recon.xlsx",
            canonical_sheet="Daily Reconciliation",
            workbook=workbook,
            sheet=sheet,
            trigger_key=trigger_key,
        ),
        name_suggestion="Daily Cash Reconciliation Skill",
        confidence=0.95,
        status="candidate",
        detected_at=max(episode.ended_at for episode in episodes),
        pattern={
            "workflow_family": CASH_RECON_WORKFLOW_FAMILY,
            "episode_count": len(episodes),
            "common_sequence": list(sequence),
            "trigger_signature": {
                "subject_prefix": "Daily bank transactions - Jun",
                "attachment_glob": "bank_transactions_*.xlsx",
                "intent": "daily_cash_reconciliation_request",
            },
            "similarity_reason": [
                "same inbound email intent",
                "same attachment naming pattern",
                "same target workbook",
                "same target sheet",
                "same 45-row daily batch size",
                "same spreadsheet audit sequence",
                "same status and exception classification columns",
                "same daily summary reply shape",
            ],
        },
        evidence={
            "episode_ids": [episode.episode_id for episode in episodes],
            "source_event_ids": _source_event_ids(episodes),
            "target_artifact": workbook,
            "target_sheet": sheet,
            "target_rows_examples": _target_rows_examples(episodes),
            "common_fields": CASH_RECON_REQUIRED_FIELDS,
            "daily_batch_size": 45,
            "audit_sequence": CASH_RECON_AUDIT_SEQUENCE,
        },
        suggested_skill={
            "trigger": "new daily bank transaction email",
            "inputs": [
                "inbound bank transaction attachment",
                "Daily Reconciliation sheet",
                "Payment Export sheet",
                "Lists & Rules sheet",
            ],
            "actions": [
                "read bank attachment rows",
                "match transactions against Payment Export",
                "compute Amount Diff",
                "preview Daily Reconciliation row updates",
                "fill Match Status",
                "fill Exception Reason",
                "fill Reviewer",
                "fill Reviewed At",
                "fill Source Email ID",
                "fill Skill Run ID",
                "draft summary reply",
                "write audit log",
            ],
            "forbidden_actions": [
                "send email automatically",
                "access network",
                "overwrite reviewed rows",
                "write closed-period rows",
            ],
        },
        handoff=_handoff(),
        next_trigger=_cash_next_trigger(episodes),
    )


def _episode_sequence(episode: WorkflowEpisode) -> list[str]:
    return [
        _string_or_empty(item.get("type"))
        for item in episode.timeline
        if item.get("type")
    ]


def _trigger_group_key(episode: WorkflowEpisode) -> str:
    return _string_or_empty(episode.entities.get("intent"))


def _candidate_id(
    *,
    prefix: str,
    canonical_id: str,
    canonical_workbook: str,
    canonical_sheet: str,
    workbook: str,
    sheet: str,
    trigger_key: str,
) -> str:
    if (
        workbook == canonical_workbook
        and sheet == canonical_sheet
        and trigger_key
        in {
            "customer_implementation_request",
            "daily_cash_reconciliation_request",
        }
    ):
        return canonical_id

    digest = hashlib.sha1(
        "|".join([workbook, sheet, trigger_key]).encode("utf-8")
    ).hexdigest()[:8]
    return f"{prefix}_{digest}"


def _cash_reconciliation_signals_match(episodes: list[WorkflowEpisode]) -> bool:
    return all(
        _cash_intent_matches(episode)
        and _cash_subject_matches(episode)
        and _cash_attachment_matches(episode)
        and _target_rows_count(episode) == 45
        and _cash_audit_sequence_matches(episode)
        and _cash_outbound_summary_matches(episode)
        for episode in episodes
    )


def _cash_intent_matches(episode: WorkflowEpisode) -> bool:
    return episode.entities.get("intent") == "daily_cash_reconciliation_request"


def _cash_subject_matches(episode: WorkflowEpisode) -> bool:
    subject = _string_or_empty(episode.entities.get("trigger_subject"))
    return subject.startswith("Daily bank transactions - Jun")


def _cash_attachment_matches(episode: WorkflowEpisode) -> bool:
    attachment = _string_or_empty(episode.entities.get("trigger_attachment"))
    return (
        re.fullmatch(r"bank_transactions_\d{4}_\d{2}_\d{2}\.xlsx", attachment)
        is not None
    )


def _target_rows_count(episode: WorkflowEpisode) -> int:
    target_rows = _string_or_empty(episode.entities.get("target_rows"))
    try:
        start_text, end_text = target_rows.split(":", maxsplit=1)
        start = int(start_text)
        end = int(end_text)
    except ValueError:
        return 0

    if end < start:
        return 0
    return end - start + 1


def _cash_outbound_summary_matches(episode: WorkflowEpisode) -> bool:
    summary = _string_or_empty(episode.entities.get("outbound_summary"))
    return (
        summary.startswith("Daily reconciliation complete.")
        and " matched," in summary
        and " exceptions need review." in summary
    )


def _cash_audit_sequence_matches(episode: WorkflowEpisode) -> bool:
    return (
        _string_list(episode.entities.get("audit_sequence"))
        == CASH_RECON_AUDIT_SEQUENCE
    )


def _cash_next_trigger(episodes: list[WorkflowEpisode]) -> dict[str, Any] | None:
    latest = max(episodes, key=lambda episode: episode.ended_at)
    latest_date = _latest_cash_date(latest)
    if latest_date is None:
        return None

    next_date = latest_date + timedelta(days=1)
    next_date_token = next_date.strftime("%Y_%m_%d")
    compact_date_token = next_date.strftime("%Y%m%d")
    next_rows = _next_target_rows(latest)
    if not next_rows:
        return None

    return {
        "event_id": f"email_in_{compact_date_token}",
        "message_id": f"msg_bank_{next_date_token}",
        "thread_id": f"thread_daily_cash_{next_date_token}",
        "target_rows": next_rows,
        "unprocessed_action_columns": [
            "Match Status",
            "Exception Reason",
            "Reviewer",
            "Reviewed At",
            "Source Email ID",
            "Skill Run ID",
        ],
    }


def _latest_cash_date(episode: WorkflowEpisode) -> datetime | None:
    values = [
        _string_or_empty(episode.entities.get("source_email")),
        _string_or_empty(episode.entities.get("thread_id")),
        episode.trigger_event_id,
    ]
    for value in values:
        match = re.search(r"(\d{4})_?(\d{2})_?(\d{2})", value)
        if not match:
            continue
        try:
            return datetime(
                year=int(match.group(1)),
                month=int(match.group(2)),
                day=int(match.group(3)),
            )
        except ValueError:
            continue
    return None


def _next_target_rows(episode: WorkflowEpisode) -> str:
    target_rows = _string_or_empty(episode.entities.get("target_rows"))
    try:
        start_text, end_text = target_rows.split(":", maxsplit=1)
        start = int(start_text)
        end = int(end_text)
    except ValueError:
        return ""

    batch_size = end - start + 1
    if batch_size <= 0:
        return ""

    next_start = end + 1
    next_end = next_start + batch_size - 1
    return f"{next_start}:{next_end}"


def _required_fields_for(workflow_family: str) -> list[str]:
    if workflow_family == CASH_RECON_WORKFLOW_FAMILY:
        return CASH_RECON_REQUIRED_FIELDS
    return FDE_REQUIRED_FIELDS


def _common_fields(
    episodes: list[WorkflowEpisode],
    required_fields: list[str],
) -> list[str]:
    episode_field_sets = [
        set(_string_list(episode.entities.get("spreadsheet_fields")))
        for episode in episodes
    ]
    if not episode_field_sets:
        return []

    common = set.intersection(*episode_field_sets)
    return [field for field in required_fields if field in common]


def _confidence(episode_count: int, common_field_count: int) -> float:
    score = 0.55
    score += min(episode_count, 5) * 0.06
    score += min(common_field_count, 10) * 0.015
    score += 0.06
    score += 0.06
    return round(min(score, 0.97), 2)


def _source_event_ids(episodes: list[WorkflowEpisode]) -> list[str]:
    event_ids = []
    for episode in episodes:
        event_ids.extend(episode.event_ids)
    return event_ids


def _target_rows_examples(episodes: list[WorkflowEpisode]) -> list[str]:
    rows = []
    for episode in episodes:
        target_rows = _string_or_empty(episode.entities.get("target_rows"))
        if target_rows:
            rows.append(target_rows)
    return rows


def _handoff() -> dict[str, Any]:
    return {
        "next_owner": "section_b_skill_creation",
        "required_confirmation_fields": HANDOFF_CONFIRMATION_FIELDS,
    }


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_string_or_empty(item) for item in value if _string_or_empty(item)]


def _first_non_empty(values: Any) -> str:
    for value in values:
        normalized = _string_or_empty(value)
        if normalized:
            return normalized
    return ""


def _string_or_empty(value: Any) -> str:
    if value is None:
        return ""
    return str(value)
