# Section A Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `fde-agent` self-contained so it can run `activity_events.jsonl -> workflow_episodes.jsonl -> skill_candidates.jsonl -> generated skill -> matched email preview/execution`.

**Architecture:** Keep Section A and Section B separated by the existing `workspace/events/skill_candidates.jsonl` contract. Add the Section A package inside `fde-agent`, then add a small orchestration module that stages demo inputs, runs Section A, and calls existing Section B `skillgen` functions.

**Tech Stack:** Python standard library, existing `autoskill_agent.skillgen`, existing Section A deterministic Python modules, JSONL files, SQLite registry.

---

### Task 1: Add Section A Package To Repo

**Files:**
- Create: `fde-agent/skillforge_local/__init__.py`
- Create: `fde-agent/skillforge_local/contracts.py`
- Create: `fde-agent/skillforge_local/episode_builder.py`
- Create: `fde-agent/skillforge_local/io_jsonl.py`
- Create: `fde-agent/skillforge_local/pattern_detector.py`
- Create: `fde-agent/skillforge_local/section_a_runner.py`

- [ ] Copy the existing deterministic Section A implementation into `fde-agent/skillforge_local/`.
- [ ] Keep the public function `run_section_a(events_path, episodes_path, candidates_path)` unchanged.
- [ ] Do not import `autoskill_agent` from Section A modules.

### Task 2: Add Integration Orchestrator

**Files:**
- Create: `fde-agent/autoskill_agent/section_a_integration.py`
- Modify: `fde-agent/autoskill_agent/cli.py`

- [ ] Add `run_section_a_skillgen_demo(root, events_path, workbook_path, force, execute)` that stages workbook metadata, writes demo trigger event/attachment, runs Section A, starts review, installs skill, matches event, creates preview, and optionally approves execution.
- [ ] Add CLI command `skillgen-section-a-demo`.
- [ ] Keep existing `skillgen-demo` unchanged.

### Task 3: Add Tests

**Files:**
- Create: `fde-agent/tests/test_section_a_integration.py`
- Create: `fde-agent/tests/fixtures/cash_recon_events.jsonl`

- [ ] Test the orchestrator in a temporary root using the fixture events and repo workbook.
- [ ] Assert the Section A output exists and contains `cand_daily_cash_recon_001`.
- [ ] Assert Section B installs `daily_cash_reconciliation`.
- [ ] Assert match, preview, execution, draft, generated workbook, and validation outputs exist.

### Task 4: Documentation And Verification

**Files:**
- Modify: `fde-agent/docs/skill-generation.md`
- Modify: `fde-agent/README.md`
- Modify: `fde-agent/.gitignore`

- [ ] Document the new one-command flow.
- [ ] Ensure `AGENTS.md` is ignored and not tracked.
- [ ] Run `PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 pytest -p no:cacheprovider tests -q` from `fde-agent`.
- [ ] Run the new CLI command from `fde-agent` with `--reset --execute`.
