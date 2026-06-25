from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ALLOWED_EVENT_TYPES = {
    "email_received",
    "spreadsheet_row_updated",
    "outbound_message_created",
}


@dataclass(frozen=True)
class NormalizedEvent:
    event_id: str
    type: str
    ts: str
    actor: str
    payload: dict[str, Any]
    contract_version: str | None = None
    source: str | None = None
    object_ref: str | None = None


@dataclass(frozen=True)
class WorkflowEpisode:
    contract_version: str
    episode_id: str
    workflow_family: str
    actor: str
    started_at: str
    ended_at: str
    trigger_event_id: str
    event_ids: list[str]
    timeline: list[dict[str, Any]]
    entities: dict[str, Any]
    actions: list[str]
    outcome: dict[str, Any]


WorkEpisode = WorkflowEpisode


@dataclass(frozen=True)
class SkillCandidate:
    contract_version: str
    candidate_id: str
    name_suggestion: str
    confidence: float
    status: str
    detected_at: str
    pattern: dict[str, Any]
    evidence: dict[str, Any]
    suggested_skill: dict[str, Any]
    handoff: dict[str, Any]
    next_trigger: dict[str, Any] | None = None


def parse_event(raw: dict[str, Any]) -> NormalizedEvent:
    required_keys = ("event_id", "type", "ts", "actor", "payload")
    missing_keys = [key for key in required_keys if key not in raw]
    if missing_keys:
        raise ValueError(f"Missing required event keys: {', '.join(missing_keys)}")

    event_type = raw["type"]
    if event_type not in ALLOWED_EVENT_TYPES:
        raise ValueError(f"Unsupported event type: {event_type}")

    payload = raw["payload"]
    if not isinstance(payload, dict):
        raise ValueError("Event payload must be an object")

    return NormalizedEvent(
        event_id=raw["event_id"],
        type=event_type,
        ts=raw["ts"],
        actor=raw["actor"],
        payload=payload,
        contract_version=_optional_string(raw.get("contract_version")),
        source=_optional_string(raw.get("source")),
        object_ref=_optional_string(raw.get("object_ref")),
    )


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
