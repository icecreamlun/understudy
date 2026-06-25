# Skill Generation

This workspace implements the Team B side of the SkillForge Local design:

```text
PatternCandidate
-> candidate review
-> human trigger/input/output confirmation
-> human workflow-step and expected-outcome confirmation
-> workflow-shaped skill package
-> SQLite registry
-> dry-run match
-> execution preview
-> human approval
-> execution event
-> validation
-> SkillOps analytics
```

It does not mine raw patterns. It consumes Section A repeated-pattern candidates from `workspace/events/skill_candidates.jsonl`. The older `workspace/candidates/{candidate_id}.json` demo shape is still accepted as a fallback.

## Run The Demo

Run the live email intake path:

```powershell
python -m autoskill_agent.cli imap-poll --once --openclaw-mode openclaw
python -m autoskill_agent.cli email-to-excel --workbook workspace/workbooks/onboarding_tracker.xlsx --yes
```

The first command fetches unread IMAP messages, sends each parsed email to OpenClaw for local extraction/classification, and appends `email_received` records to `workspace/events/activity_events.jsonl`. The second command writes approved matching email events into Excel and appends `spreadsheet_row_updated` records to the same activity log, giving Section A the email-to-spreadsheet workflow evidence it needs.

Run the integrated Section A -> Section B path:

```powershell
cd D:\hackathon
python -m autoskill_agent.cli skillgen-section-a-demo --reset --execute
```

This is the preferred hackathon demo path. It starts with Section A activity events, writes `workspace/events/workflow_episodes.jsonl`, writes `workspace/events/skill_candidates.jsonl`, and then runs the Team B skill-generation flow from that candidate.

Run the Team B-only seeded demo:

```powershell
cd D:\hackathon
python -m autoskill_agent.cli skillgen-demo --reset
```

The demo creates the mocked finance candidate from the design doc, installs the generated skill, matches the June 15 bank email event, previews the run, approves it, validates it, and records SkillOps metrics.

## Step By Step

```powershell
python -m autoskill_agent.cli skillgen-bootstrap --force
python -m autoskill_agent.cli skillgen-seed-section-a --workbook "D:\apps\wechat\WeChat Files\wxid_jf2437118jx422\FileStorage\File\2026-06\skillforge_finance_demo_cash_recon.xlsx" --force
python -m autoskill_agent.cli skillgen-review --candidate-id cand_daily_cash_recon_001
python -m autoskill_agent.cli skillgen-install --review-session-id review_cand_daily_cash_recon_001
python -m autoskill_agent.cli skillgen-match
python -m autoskill_agent.cli skillgen-preview match_daily_cash_reconciliation_event_email_bank_2026_06_15
python -m autoskill_agent.cli skillgen-approve match_daily_cash_reconciliation_event_email_bank_2026_06_15
python -m autoskill_agent.cli skillgen-skillops
```

To use the local Qwen planner for the review-generation step, first check the configured local endpoint:

```powershell
python -m autoskill_agent.cli skillgen-model-check
```

Then run review generation with:

```powershell
python -m autoskill_agent.cli skillgen-review --candidate-id cand_daily_cash_recon_001 --planner local-model
```

Integrated Section A command:

```powershell
python -m autoskill_agent.cli skillgen-section-a-demo --reset --execute
```

Optional arguments:

```powershell
python -m autoskill_agent.cli skillgen-section-a-demo --events workspace/events/activity_events.jsonl --workbook workspace/workbooks/skillforge_finance_demo_cash_recon.xlsx --reset --execute
```

## Generated Bundle

```text
workspace/skills/daily-cash-reconciliation/
  skill.yaml
  skill.json
  SKILL.md
  policy.yaml
  human_feedback.json
  source_candidate.json
  examples/
  tests/
  audit_schema.json
```

`skill.yaml` is the important human-review artifact. `skill.json` is the internal dependency-free representation used by the local trigger/executor code because PyYAML is not installed on this host.

## Section A Input

Section A writes one JSON object per line to:

```text
workspace/events/skill_candidates.jsonl
```

Section B validates `contract_version` as either `section_a.skill_candidate.v1` or `section_a.v1`, then maps the candidate into the human review object:

```text
candidate_id                         -> source_candidate.candidate_id
name_suggestion                      -> suggested.skill_name
confidence                           -> source_candidate.confidence
pattern.workflow_family              -> suggested.skill_id
pattern.trigger_signature            -> suggested.trigger.conditions
suggested_skill.inputs               -> suggested.inputs
suggested_skill.actions              -> suggested.workflow_steps
suggested_skill.forbidden_actions    -> suggested.forbidden_actions
evidence.target_artifact             -> workbook resource and permissions
evidence.target_sheet                -> workbook step targets
next_trigger                         -> first-run preview evidence only
handoff.required_confirmation_fields -> review requirements
```

Section B never executes from the Section A candidate directly. It creates a review session first, then generates the skill only after the required fields are confirmed.

For local e2e testing, `skillgen-seed-section-a` stages a source workbook under `workspace/workbooks/`, inspects its `.xlsx` sheet package, writes `workspace/events/skill_candidates.jsonl`, creates a mock inbound email event, and creates a CSV-shaped transaction attachment with an `.xlsx` filename for the dependency-free demo executor.

## Local Model Planner

Skill generation has two planner modes:

```text
deterministic  -> pure Python fallback, no model call
local-model    -> OpenAI-compatible local model call using config/openclaw.json
```

`local-model` reads the OpenClaw config and calls:

```text
http://127.0.0.1:11434/v1/chat/completions
model: qwen3-30b-a3b-local
```

The model is only allowed to refine bounded review fields:

```text
description
workflow_steps
expected_outcome
validation_rules
```

It cannot change triggers, permissions, approval mode, source files, or install status. Model output is parsed as JSON, sanitized, and checked for invariants such as human approval before write, no email sending, no network use, and a reconciled spreadsheet output. If the model endpoint is unavailable or the output fails validation, Section B falls back to the deterministic planner.

## Skill Output Shape

Generated skills use a deterministic workflow schema:

```text
schema_version: skill.workflow.v1
skill_id: stable_machine_id
name: human readable name
triggers:
  - id, type, label
    conditions:
      - id, field, operator, value, label
resources:
  inputs: required inbound files, workbooks, messages, or records
  outputs: expected local artifacts or records
workflow:
  steps:
    - order, id, title, type, action_type, summary, inputs, outputs
  expected_outcome:
    summary
    files_created
    files_modified
    side_effects
guardrails: human-readable safety limits
permissions: local read/write capability bounds
validation: checks that must pass after execution
```

This keeps generation deterministic while leaving room for different trigger types, resource types, step types, and outcome artifacts. The human verifier should see the trigger labels, every ordered workflow step, and the expected final outcome before approving installation.

## Local Runtime Files

```text
workspace/candidates/cand_daily_cash_recon_001.json
workspace/events/skill_candidates.jsonl
workspace/reviews/review_cand_daily_cash_recon_001.json
workspace/events/events.jsonl
workspace/skill_matches/
workspace/mail/drafts/
workspace/workbooks/cash_recon.skill_updates.jsonl
.runtime/skillforge/skill_registry.sqlite3
```

The MVP uses a CSV-shaped transaction attachment with an `.xlsx` filename so the demo can run without Excel, macros, cloud APIs, or extra Python packages. The skill package and action names remain aligned to the design doc's `.xlsx` contract, so a real workbook adapter can replace the demo parser later.
