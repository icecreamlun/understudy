# IMAP OpenClaw Excel Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a live-input path that turns unread IMAP email into OpenClaw-enriched activity events, then writes approved matching events into Excel and emits spreadsheet activity events.

**Architecture:** Keep IMAP, OpenClaw extraction, and Excel writing as separate modules under `skillforge_local`. `autoskill_agent.cli` only wires them together. Tests use injected fake OpenClaw output and local `.eml` fixtures, not real network or OpenClaw.

**Tech Stack:** Python standard library `imaplib`, `email`, `subprocess`, JSONL files, `openpyxl`, existing `autoskill_agent.cli`.

---

### Task 1: Add Email And IMAP Modules

**Files:**
- Create: `skillforge_local/imap_config.py`
- Create: `skillforge_local/imap_collector.py`
- Create: `skillforge_local/email_parser.py`
- Create: `tests/fixtures/acme_request.eml`
- Create: `tests/test_email_parser.py`

- [ ] Write tests for IMAP env config, RFC822 parsing, and IMAP message event creation.
- [ ] Implement `load_imap_config`, `parse_email_bytes`, and `build_event_from_imap_message`.

### Task 2: Add OpenClaw Extraction Adapter

**Files:**
- Create: `skillforge_local/openclaw_email.py`
- Test: `tests/test_openclaw_email.py`

- [ ] Write tests for parsing JSON returned by an injected OpenClaw runner.
- [ ] Write tests for deterministic mock extraction used in offline test/demo mode.
- [ ] Implement `extract_email_activity_with_openclaw`.

### Task 3: Add Excel Write Pipeline

**Files:**
- Create: `skillforge_local/excel_writer.py`
- Create: `skillforge_local/v0_runner.py`
- Test: `tests/test_excel_writer.py`

- [ ] Write tests for preview row generation, approved append, duplicate rejection, preview log, audit log, and emitted `spreadsheet_row_updated` event.
- [ ] Implement true `openpyxl` append for `Onboarding Tracker`.
- [ ] Ensure approved writes append a spreadsheet event to the same activity log.

### Task 4: Add CLI Commands

**Files:**
- Modify: `autoskill_agent/cli.py`
- Modify: `README.md`
- Modify: `docs/skill-generation.md`

- [ ] Add `imap-poll --once --openclaw-mode openclaw|mock`.
- [ ] Add `email-to-excel --workbook ... --yes`.
- [ ] Document Gmail IMAP env variables and the local demo commands.

### Task 5: Verify

**Commands:**
- `PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 pytest -p no:cacheprovider tests -q`
- `PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 python -m autoskill_agent.cli email-to-excel --events-log <fixture-log> --workbook <tmp.xlsx> --yes`

- [ ] Confirm tests pass.
- [ ] Confirm no `AGENTS.md`, cache files, or credentials are tracked.
