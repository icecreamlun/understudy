from __future__ import annotations

import argparse
import json
from pathlib import Path

from autoskill_agent import core, observatory, section_a_integration, skillgen
from skillforge_local.excel_writer import ensure_onboarding_tracker
from skillforge_local.imap_collector import fetch_unseen_once
from skillforge_local.imap_config import load_imap_config
from skillforge_local import excel_watcher
from skillforge_local.io_jsonl import append_jsonl
from skillforge_local.openclaw_email import (
    enrich_email_event,
    extract_email_activity_with_openclaw,
    mock_openclaw_extract,
)
from skillforge_local.v0_runner import process_activity_log_to_excel


def cmd_init_demo(args: argparse.Namespace) -> int:
    paths = core.init_demo(args.root, force=args.force)
    print(f"Demo tracker: {paths.tracker_csv}")
    print(f"Dashboard:    {paths.dashboard_html}")
    return 0


def cmd_observe(args: argparse.Namespace) -> int:
    candidate = core.observe(args.root, min_examples=args.min_examples)
    paths = core.workspace_paths(args.root)
    print(f"Candidate: {candidate['name']} ({candidate['id']})")
    print(f"Examples:  {candidate['source']['completed_examples']}")
    print(f"Pending:   {candidate['source']['pending_rows']}")
    print(f"Wrote:     {paths.candidate_json}")
    print(f"Review:    {paths.candidate_md}")
    return 0


def cmd_approve(args: argparse.Namespace) -> int:
    if not args.yes:
        print("Approval required. Re-run with --yes after reviewing the candidate markdown.")
        return 2
    manifest = core.approve_candidate(args.root, approved_by=args.approved_by)
    paths = core.workspace_paths(args.root)
    print(f"Registered skill: {manifest['id']} v{manifest['version']}")
    print(f"Skill dir:         {paths.skills_dir / manifest['id']}")
    print(f"Registry:          {paths.registry_json}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    result = core.run_registered_skill(args.root, approve=args.approve)
    if result["wrote"]:
        print(f"Executed skill. Output: {result['output']}")
    else:
        print(f"Preview only. Review: {result['preview_path']}")
        print("Re-run with --approve to write the completed tracker.")
    print(f"Proposed row changes: {len(result['preview'])}")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    print(json.dumps(core.status(args.root), indent=2))
    return 0


def cmd_demo(args: argparse.Namespace) -> int:
    paths = core.init_demo(args.root, force=args.reset)
    candidate = core.observe(args.root)
    manifest = core.approve_candidate(args.root, approved_by=args.approved_by)
    result = core.run_registered_skill(args.root, approve=True)
    print("SheetSkill Local demo complete")
    print(f"Candidate: {candidate['id']}")
    print(f"Skill:     {manifest['id']} v{manifest['version']}")
    print(f"Output:    {result['output']}")
    print(f"Dashboard: {paths.dashboard_html}")
    print(f"Audit:     {paths.audit_log}")
    return 0


def cmd_reset_demo(args: argparse.Namespace) -> int:
    result = observatory.reset_demo(
        args.root,
        keep_local_skills=args.keep_local_skills,
        clear_memory=args.clear_memory,
    )
    print(json.dumps(result, indent=2))
    return 0


def cmd_skillgen_bootstrap(args: argparse.Namespace) -> int:
    result = skillgen.bootstrap_demo(args.root, force=args.force)
    print(json.dumps(result, indent=2))
    return 0


def cmd_skillgen_seed_section_a(args: argparse.Namespace) -> int:
    result = skillgen.seed_section_a_mock_from_workbook(args.root, args.workbook, force=args.force)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "ok" else 2


def cmd_skillgen_review(args: argparse.Namespace) -> int:
    review = skillgen.create_review_session(
        args.root,
        args.candidate_id,
        planner=args.planner,
        model_timeout_seconds=args.model_timeout,
    )
    print(json.dumps(review, indent=2))
    return 0


def cmd_skillgen_install(args: argparse.Namespace) -> int:
    feedback = skillgen.default_human_feedback(args.root, args.review_session_id, reviewer=args.reviewer)
    submit = skillgen.submit_feedback(args.root, args.review_session_id, feedback)
    if submit["status"] != "ok":
        print(json.dumps(submit, indent=2))
        return 2
    result = skillgen.install_skill(args.root, args.review_session_id)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "installed" else 2


def cmd_skillgen_match(args: argparse.Namespace) -> int:
    matches = skillgen.match_events(args.root)
    print(json.dumps({"matches": matches}, indent=2))
    return 0


def cmd_skillgen_preview(args: argparse.Namespace) -> int:
    preview = skillgen.preview_match(args.root, args.match_id)
    print(json.dumps(preview, indent=2))
    return 0


def cmd_skillgen_approve(args: argparse.Namespace) -> int:
    execution = skillgen.approve_match(args.root, args.match_id, actor=args.actor)
    print(json.dumps(execution, indent=2))
    return 0


def cmd_skillgen_skillops(args: argparse.Namespace) -> int:
    print(json.dumps(skillgen.skillops_summary(args.root), indent=2))
    return 0


def cmd_skillgen_model_check(args: argparse.Namespace) -> int:
    result = skillgen.check_local_model(args.root, timeout_seconds=args.model_timeout)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "ok" else 2


def cmd_skillgen_demo(args: argparse.Namespace) -> int:
    result = skillgen.run_full_skillgen_demo(
        args.root,
        force=args.reset,
        planner=args.planner,
        model_timeout_seconds=args.model_timeout,
    )
    print(json.dumps(result, indent=2))
    return 0


def cmd_skillgen_section_a_demo(args: argparse.Namespace) -> int:
    result = section_a_integration.run_section_a_skillgen_demo(
        args.root,
        events_path=args.events,
        workbook_path=args.workbook,
        force=args.reset,
        execute=args.execute,
    )
    print(json.dumps(result, indent=2))
    return 0 if result["status"] in {"preview_ready", "executed"} else 2


def cmd_imap_poll(args: argparse.Namespace) -> int:
    config = load_imap_config()
    events_log = _workspace_path(args.root, args.events_log)
    count = 0
    for event in fetch_unseen_once(config, actor=args.actor, limit=args.limit, latest=args.latest):
        if args.openclaw_mode == "mock":
            extraction = mock_openclaw_extract(event)
        else:
            extraction = extract_email_activity_with_openclaw(
                event,
                command=args.openclaw_command,
                timeout_seconds=args.openclaw_timeout,
            )
        append_jsonl(events_log, enrich_email_event(event, extraction))
        count += 1
    print(json.dumps({"status": "ok", "events_written": count, "events_log": str(events_log)}, indent=2))
    return 0


def cmd_email_to_excel(args: argparse.Namespace) -> int:
    events_log = _workspace_path(args.root, args.events_log)
    workbook = _workspace_path(args.root, args.workbook)
    preview_log = _workspace_path(args.root, args.preview_log)
    audit_log = _workspace_path(args.root, args.audit_log)
    ensure_onboarding_tracker(workbook)
    results = process_activity_log_to_excel(
        events_log,
        workbook,
        approved=args.yes,
        preview_log_path=preview_log,
        audit_log_path=audit_log,
    )
    summary = {
        "status": "ok",
        "events_log": str(events_log),
        "workbook": str(workbook),
        "results": results,
        "counts": {
            "written": sum(1 for item in results if item.get("status") == "written"),
            "preview": sum(1 for item in results if item.get("status") == "preview"),
            "ignored": sum(1 for item in results if item.get("status") == "ignored"),
            "error": sum(1 for item in results if item.get("status") == "error"),
        },
    }
    print(json.dumps(summary, indent=2))
    return 0 if summary["counts"]["error"] == 0 else 2


def cmd_excel_watch(args: argparse.Namespace) -> int:
    root = Path(args.root)
    events_log = _workspace_path(root, args.events_log)
    target = _workspace_path(root, args.path)
    count = excel_watcher.watch(
        root,
        target,
        events_log,
        interval=args.interval,
        actor=args.actor,
        once=args.once,
    )
    if args.once:
        print(json.dumps({"status": "ok", "events_emitted": count, "events_log": str(events_log)}, indent=2))
    return 0


def _workspace_path(root: Path, path: Path | str) -> Path:
    value = Path(path).expanduser()
    return value if value.is_absolute() else root / value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="autoskill",
        description="Offline auto-skillizing agent prototype for repeated spreadsheet workflows.",
    )
    parser.add_argument("--root", default=".", help="Repository/workspace root.")
    subparsers = parser.add_subparsers(required=True)

    init_parser = subparsers.add_parser("init-demo", help="Create the local demo tracker.")
    init_parser.add_argument("--force", action="store_true", help="Overwrite existing demo data.")
    init_parser.set_defaults(func=cmd_init_demo)

    observe_parser = subparsers.add_parser("observe", help="Detect a reusable skill candidate.")
    observe_parser.add_argument("--min-examples", type=int, default=3)
    observe_parser.set_defaults(func=cmd_observe)

    approve_parser = subparsers.add_parser("approve", help="Register the generated skill.")
    approve_parser.add_argument("--yes", action="store_true", help="Approve candidate registration.")
    approve_parser.add_argument("--approved-by", default="human")
    approve_parser.set_defaults(func=cmd_approve)

    run_parser = subparsers.add_parser("run", help="Preview or execute the registered skill.")
    run_parser.add_argument("--approve", action="store_true", help="Write output files.")
    run_parser.set_defaults(func=cmd_run)

    demo_parser = subparsers.add_parser("demo", help="Run the full end-to-end demo.")
    demo_parser.add_argument("--reset", action="store_true", help="Reset demo data first.")
    demo_parser.add_argument("--approved-by", default="human")
    demo_parser.set_defaults(func=cmd_demo)

    status_parser = subparsers.add_parser("status", help="Show current local state.")
    status_parser.set_defaults(func=cmd_status)

    reset_demo_parser = subparsers.add_parser(
        "reset-demo",
        help="Reset to the pre-accept observe state: Skills empty, recommendation 'proposed'.",
    )
    reset_demo_parser.add_argument(
        "--keep-local-skills",
        action="store_true",
        help="Leave copies under ~/.claude/skills in place (only clears the project workspace).",
    )
    reset_demo_parser.add_argument(
        "--clear-memory",
        action="store_true",
        help="Also wipe the local skill-feedback mirror for a clean before/after demo.",
    )
    reset_demo_parser.set_defaults(func=cmd_reset_demo)

    skillgen_bootstrap = subparsers.add_parser("skillgen-bootstrap", help="Create Section A demo candidate/events.")
    skillgen_bootstrap.add_argument("--force", action="store_true")
    skillgen_bootstrap.set_defaults(func=cmd_skillgen_bootstrap)

    skillgen_seed_section_a = subparsers.add_parser(
        "skillgen-seed-section-a",
        help="Create Section A mock candidate/events from a workbook.",
    )
    skillgen_seed_section_a.add_argument("--workbook", required=True, type=Path)
    skillgen_seed_section_a.add_argument("--force", action="store_true")
    skillgen_seed_section_a.set_defaults(func=cmd_skillgen_seed_section_a)

    skillgen_review = subparsers.add_parser("skillgen-review", help="Start review from a Section A skill candidate.")
    skillgen_review.add_argument("--candidate-id", default="cand_daily_cash_recon_001")
    skillgen_review.add_argument("--planner", choices=["deterministic", "codex", "anthropic", "local-model"], default="codex")
    skillgen_review.add_argument("--model-timeout", type=int, default=180)
    skillgen_review.set_defaults(func=cmd_skillgen_review)

    skillgen_install = subparsers.add_parser("skillgen-install", help="Submit default feedback and install skill.")
    skillgen_install.add_argument("--review-session-id", default="review_cand_daily_cash_recon_001")
    skillgen_install.add_argument("--reviewer", default="controller")
    skillgen_install.set_defaults(func=cmd_skillgen_install)

    skillgen_match = subparsers.add_parser("skillgen-match", help="Match active skills against local events.")
    skillgen_match.set_defaults(func=cmd_skillgen_match)

    skillgen_preview = subparsers.add_parser("skillgen-preview", help="Create an execution preview for a match.")
    skillgen_preview.add_argument("match_id")
    skillgen_preview.set_defaults(func=cmd_skillgen_preview)

    skillgen_approve = subparsers.add_parser("skillgen-approve", help="Approve and execute a skill match.")
    skillgen_approve.add_argument("match_id")
    skillgen_approve.add_argument("--actor", default="analyst_1")
    skillgen_approve.set_defaults(func=cmd_skillgen_approve)

    skillgen_skillops = subparsers.add_parser("skillgen-skillops", help="Show SkillOps metrics and recommendations.")
    skillgen_skillops.set_defaults(func=cmd_skillgen_skillops)

    skillgen_model_check = subparsers.add_parser("skillgen-model-check", help="Check local model connectivity.")
    skillgen_model_check.add_argument("--model-timeout", type=int, default=60)
    skillgen_model_check.set_defaults(func=cmd_skillgen_model_check)

    skillgen_demo = subparsers.add_parser("skillgen-demo", help="Run Team B skill-generation demo end-to-end.")
    skillgen_demo.add_argument("--reset", action="store_true")
    skillgen_demo.add_argument("--planner", choices=["deterministic", "codex", "anthropic", "local-model"], default="codex")
    skillgen_demo.add_argument("--model-timeout", type=int, default=180)
    skillgen_demo.set_defaults(func=cmd_skillgen_demo)

    skillgen_section_a_demo = subparsers.add_parser(
        "skillgen-section-a-demo",
        help="Run Section A activity detection into Team B skill generation.",
    )
    skillgen_section_a_demo.add_argument("--events", type=Path, help="Section A activity_events.jsonl input.")
    skillgen_section_a_demo.add_argument("--workbook", type=Path, help="Cash reconciliation workbook to stage.")
    skillgen_section_a_demo.add_argument("--reset", action="store_true", help="Reset runtime demo outputs first.")
    skillgen_section_a_demo.add_argument("--execute", action="store_true", help="Approve and execute the first matched skill.")
    skillgen_section_a_demo.set_defaults(func=cmd_skillgen_section_a_demo)

    imap_poll = subparsers.add_parser("imap-poll", help="Fetch unread IMAP email and write OpenClaw-enriched activity events.")
    imap_poll.add_argument("--once", action="store_true", help="Fetch one UNSEEN batch. Continuous IMAP IDLE is out of MVP scope.")
    imap_poll.add_argument("--actor", default="fde_engineer")
    imap_poll.add_argument("--events-log", type=Path, default=Path("workspace/events/activity_events.jsonl"))
    imap_poll.add_argument("--limit", type=int, default=None, help="Maximum number of UNSEEN messages to fetch.")
    imap_poll.add_argument("--latest", action="store_true", help="Fetch newest UNSEEN messages first when used with --limit.")
    imap_poll.add_argument("--openclaw-mode", choices=["anthropic", "openclaw", "mock"], default="anthropic")
    imap_poll.add_argument("--openclaw-command", default=None)
    imap_poll.add_argument("--openclaw-timeout", type=int, default=60)
    imap_poll.set_defaults(func=cmd_imap_poll)

    excel_watch = subparsers.add_parser("excel-watch", help="Watch local .xlsx files and record changes as activity events.")
    excel_watch.add_argument("--path", default="workspace/workbooks", help="Workbook file or directory to watch.")
    excel_watch.add_argument("--events-log", type=Path, default=Path("workspace/events/activity_events.jsonl"))
    excel_watch.add_argument("--interval", type=float, default=2.0)
    excel_watch.add_argument("--actor", default="excel_watch")
    excel_watch.add_argument("--once", action="store_true", help="Single pass instead of a watch loop.")
    excel_watch.set_defaults(func=cmd_excel_watch)

    email_to_excel = subparsers.add_parser("email-to-excel", help="Write OpenClaw-enriched email activity events into Excel.")
    email_to_excel.add_argument("--workbook", required=True, type=Path)
    email_to_excel.add_argument("--events-log", type=Path, default=Path("workspace/events/activity_events.jsonl"))
    email_to_excel.add_argument("--preview-log", type=Path, default=Path("workspace/events/execution_previews.jsonl"))
    email_to_excel.add_argument("--audit-log", type=Path, default=Path("workspace/events/audit_log.jsonl"))
    email_to_excel.add_argument("--yes", action="store_true", help="Approve workbook writes without prompting for demo use.")
    email_to_excel.set_defaults(func=cmd_email_to_excel)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    args.root = Path(args.root).resolve()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
