from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Callable, Any

from .llm import complete_text


ModelRunner = Callable[[str], str]


def extract_email_activity_with_openclaw(
    event: dict,
    *,
    runner: ModelRunner | None = None,
    command: str | None = None,  # accepted for backward compatibility; ignored
    timeout_seconds: int = 60,
) -> dict[str, Any]:
    """Extract structured email-activity fields using the Anthropic API."""
    prompt = build_email_extraction_prompt(event)
    output = runner(prompt) if runner else run_model_prompt(prompt, timeout_seconds=timeout_seconds)
    payload = _parse_json_object(output)
    return normalize_openclaw_extraction(payload)


def run_model_prompt(prompt: str, *, timeout_seconds: int = 60) -> str:
    """Send the extraction prompt to Claude and return the raw text response."""
    return complete_text(
        [{"role": "user", "content": prompt}],
        max_tokens=1024,
        timeout_seconds=timeout_seconds,
    )


def build_email_extraction_prompt(event: dict) -> str:
    payload = event.get("payload", {})
    body_text = str(payload.get("body_text") or payload.get("content_summary") or "")
    return f"""You are SkillForge Local's offline email activity extractor.

Read the email below and return exactly one JSON object. Do not include markdown.

Required schema:
{{
  "is_match": true | false,
  "intent": "customer_implementation_request" | "unknown",
  "extracted": {{
    "customer": "string",
    "contact": "string",
    "request_type": "string",
    "due_date": "string",
    "blockers": ["string"],
    "next_step": "string"
  }}
}}

Email:
From: {payload.get("from", "")}
Subject: {payload.get("subject", "")}
Received at: {payload.get("received_at", event.get("ts", ""))}
Summary: {payload.get("content_summary", "")}
Body:
{body_text}
"""


def normalize_openclaw_extraction(payload: dict[str, Any]) -> dict[str, Any]:
    extracted = payload.get("extracted")
    if not isinstance(extracted, dict):
        extracted = {}
    blockers = extracted.get("blockers", [])
    if isinstance(blockers, str):
        blockers = [blockers]
    if not isinstance(blockers, list):
        blockers = []
    return {
        "is_match": bool(payload.get("is_match")),
        "intent": str(payload.get("intent") or "unknown"),
        "extracted": {
            "customer": str(extracted.get("customer") or "Unknown"),
            "contact": str(extracted.get("contact") or ""),
            "request_type": str(extracted.get("request_type") or ""),
            "due_date": str(extracted.get("due_date") or ""),
            "blockers": [str(item) for item in blockers if str(item)],
            "next_step": str(extracted.get("next_step") or ""),
        },
    }


def mock_openclaw_extract(event: dict) -> dict[str, Any]:
    payload = event.get("payload", {})
    subject = str(payload.get("subject", ""))
    summary = str(payload.get("content_summary", ""))
    lower = f"{subject}\n{summary}".lower()
    is_match = any(term in lower for term in ["onboard", "onboarding", "implementation", "integration", "api"])
    if not is_match:
        return {"is_match": False, "intent": "unknown", "extracted": {}}

    blockers: list[str] = []
    if "credential" in lower:
        blockers.append("Credentials missing")
    if "field mapping" in lower or "mapping" in lower:
        blockers.append("Field mapping needed")
    if not blockers:
        blockers.append("Needs review")
    return {
        "is_match": True,
        "intent": "customer_implementation_request",
        "extracted": {
            "customer": _extract_customer(subject, summary),
            "contact": payload.get("from", ""),
            "request_type": "API onboarding" if "api" in lower else "implementation request",
            "due_date": "",
            "blockers": blockers,
            "next_step": _next_step(blockers),
        },
    }


def enrich_email_event(event: dict, extraction: dict[str, Any]) -> dict:
    normalized = normalize_openclaw_extraction(extraction)
    enriched = deepcopy(event)
    payload = enriched.setdefault("payload", {})
    payload["openclaw"] = normalized
    if normalized["is_match"]:
        payload["intent"] = normalized["intent"]
        payload["extracted"] = normalized["extracted"]
        payload["customer"] = normalized["extracted"]["customer"]
        payload["contact"] = normalized["extracted"]["contact"]
    return enriched


def _parse_json_object(output: str) -> dict[str, Any]:
    text = output.strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise ValueError("OpenClaw output did not contain a JSON object")
        parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("OpenClaw output JSON must be an object")
    return parsed


def _extract_customer(subject: str, summary: str) -> str:
    combined = f"{subject} {summary}"
    match = re.search(r"\bfor\s+([A-Z][A-Za-z0-9_-]+)", combined)
    if match:
        return match.group(1)
    match = re.search(r"\bonboard\s+([A-Z][A-Za-z0-9_-]+)", combined)
    if match:
        return match.group(1)
    return "Unknown"


def _next_step(blockers: list[str]) -> str:
    if "Credentials missing" in blockers and "Field mapping needed" in blockers:
        return "Ask customer for credentials and field mapping details"
    if "Credentials missing" in blockers:
        return "Ask customer for credentials"
    if "Field mapping needed" in blockers:
        return "Ask customer for field mapping details"
    return "Review request and ask for missing setup details"
