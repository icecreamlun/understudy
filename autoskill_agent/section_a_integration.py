from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from autoskill_agent import skillgen
from skillforge_local.section_a_runner import run_section_a


def run_section_a_skillgen_demo(
    root: Path | str = ".",
    *,
    events_path: Path | str | None = None,
    workbook_path: Path | str | None = None,
    force: bool = False,
    execute: bool = False,
) -> dict[str, Any]:
    p = skillgen.paths(root)
    _ensure_workspace(p)
    if force:
        _reset_runtime_outputs(p)

    resolved_events = _resolve_events_path(p.root, events_path)
    resolved_workbook = _resolve_workbook_path(p.root, workbook_path)
    staged_workbook = _stage_workbook(p, resolved_workbook, force=force)
    workbook_info = skillgen.inspect_xlsx_workbook(staged_workbook)
    skillgen.write_workbook_metadata(p, staged_workbook, workbook_info)
    attachment_path = p.attachments_dir / "bank_transactions_2026_06_15.xlsx"
    if force or not attachment_path.exists():
        skillgen.write_transaction_attachment(attachment_path)
    _seed_trigger_event(p, attachment_path)
    skillgen.init_registry(p.registry_db)

    episodes_path = p.events_dir / "workflow_episodes.jsonl"
    run_section_a(
        events_path=resolved_events,
        episodes_path=episodes_path,
        candidates_path=p.skill_candidates_log,
    )
    candidates = skillgen.read_section_a_candidates(p.root)
    if not candidates:
        return {
            "status": "no_candidate",
            "events_path": str(resolved_events),
            "episodes_path": str(episodes_path),
            "skill_candidates_log": str(p.skill_candidates_log),
        }

    candidate = _select_candidate(candidates)
    review = skillgen.create_review_session(p.root, candidate["candidate_id"])
    if review.get("status") == "needs_more_evidence":
        return {"status": "review_failed", "candidate": candidate, "review": review}

    feedback = skillgen.default_human_feedback(p.root, review["review_session_id"])
    feedback_result = skillgen.submit_feedback(p.root, review["review_session_id"], feedback)
    if feedback_result.get("status") != "ok":
        return {
            "status": "feedback_failed",
            "candidate": candidate,
            "review": review,
            "feedback": feedback_result,
        }

    install = skillgen.install_skill(p.root, review["review_session_id"])
    if install.get("status") != "installed":
        return {
            "status": "install_failed",
            "candidate": candidate,
            "review": review,
            "install": install,
        }

    matches = skillgen.match_events(p.root)
    preview = skillgen.preview_match(p.root, matches[0]["match_id"]) if matches else None
    execution = (
        skillgen.approve_match(p.root, matches[0]["match_id"])
        if execute and matches
        else None
    )
    return {
        "status": "executed" if execution else "preview_ready",
        "events_path": str(resolved_events),
        "episodes_path": str(episodes_path),
        "skill_candidates_log": str(p.skill_candidates_log),
        "candidate": candidate,
        "review": review,
        "install": install,
        "matches": matches,
        "preview": preview,
        "execution": execution,
        "skillops": skillgen.skillops_summary(p.root),
    }


def _ensure_workspace(p: skillgen.SkillGenPaths) -> None:
    for directory in [
        p.events_dir,
        p.attachments_dir,
        p.workbooks_dir,
        p.drafts_dir,
        p.matches_dir,
        p.reviews_dir,
        p.skills_dir,
        p.runtime_dir,
    ]:
        directory.mkdir(parents=True, exist_ok=True)


def _reset_runtime_outputs(p: skillgen.SkillGenPaths) -> None:
    for file_path in [
        p.registry_db,
        p.event_log,
        p.skill_candidates_log,
        p.events_dir / "workflow_episodes.jsonl",
    ]:
        if file_path.exists():
            file_path.unlink()
    if p.matches_dir.exists():
        shutil.rmtree(p.matches_dir)
    p.matches_dir.mkdir(parents=True, exist_ok=True)


def _resolve_events_path(root: Path, events_path: Path | str | None) -> Path:
    if events_path is not None:
        return _resolve_explicit_path(root, events_path, label="Section A demo events")

    default_path = root / "tests" / "fixtures" / "cash_recon_events.jsonl"
    if default_path.exists():
        return default_path
    raise FileNotFoundError(f"Section A demo events not found: {default_path}")


def _resolve_workbook_path(root: Path, workbook_path: Path | str | None) -> Path:
    if workbook_path is not None:
        return _resolve_explicit_path(root, workbook_path, label="Workbook")

    candidates = [
        root / "skillforge_finance_demo_cash_recon.xlsx",
        root / "workspace" / "workbooks" / "skillforge_finance_demo_cash_recon.xlsx",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Demo workbook not found in repo root or workspace/workbooks.")


def _resolve_explicit_path(root: Path, path_value: Path | str, *, label: str) -> Path:
    path = Path(path_value).expanduser()
    candidates = [path] if path.is_absolute() else [(root / path).resolve(), (Path.cwd() / path).resolve()]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    searched = ", ".join(str(candidate) for candidate in candidates)
    raise FileNotFoundError(f"{label} not found. Searched: {searched}")


def _stage_workbook(
    p: skillgen.SkillGenPaths,
    source_workbook: Path,
    *,
    force: bool,
) -> Path:
    staged_workbook = p.workbooks_dir / source_workbook.name
    if source_workbook.resolve() == staged_workbook.resolve():
        return staged_workbook
    if force or not staged_workbook.exists():
        staged_workbook.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_workbook, staged_workbook)
    return staged_workbook


def _seed_trigger_event(
    p: skillgen.SkillGenPaths,
    attachment_path: Path,
) -> None:
    skillgen.append_event(
        p.event_log,
        {
            "id": "event_email_bank_2026_06_15",
            "type": "email_received",
            "actor": "analyst_1",
            "workspace": "finance_demo",
            "payload": {
                "message_id": "msg_bank_2026_06_15",
                "thread_id": "thread_daily_cash_2026_06_15",
                "direction": "inbox",
                "from": "bank-ops@example.local",
                "to": ["finance-team@example.local"],
                "subject": "Daily bank transactions - June 15",
                "date": "2026-06-15T08:02:00-07:00",
                "body_text": "Attached are today's bank transactions.",
                "attachments": [
                    {
                        "filename": attachment_path.name,
                        "path": attachment_path.relative_to(p.root).as_posix(),
                    }
                ],
                "source_path": "workspace/mail/inbox_today/bank_2026_06_15.eml",
            },
        },
    )


def _select_candidate(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    for candidate in candidates:
        if candidate.get("candidate_id") == "cand_daily_cash_recon_001":
            return candidate
    return candidates[0]
