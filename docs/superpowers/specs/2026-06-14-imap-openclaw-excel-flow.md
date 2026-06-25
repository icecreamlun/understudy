# IMAP OpenClaw Excel Flow Design

## Goal

Build a small live-input path inside `fde-agent`:

```text
IMAP unread email -> raw email parser -> OpenClaw local extraction -> activity_events.jsonl -> Excel write -> spreadsheet_row_updated activity event
```

This does not replace Section A/B. It feeds Section A with real `email_received` and `spreadsheet_row_updated` events instead of hand-written fixtures.

## Design

IMAP is only the transport. It fetches unread RFC822 messages from Gmail or any IMAP-compatible mailbox using local environment variables. It does not classify, summarize, or decide whether a workflow applies.

OpenClaw is the required interpretation layer. The pipeline sends subject, sender, timestamp, and body summary to an OpenClaw adapter and expects JSON fields:

```json
{
  "is_match": true,
  "intent": "customer_implementation_request",
  "extracted": {
    "customer": "Acme",
    "contact": "maya@acme.example",
    "request_type": "API onboarding",
    "due_date": "",
    "blockers": ["Credentials missing"],
    "next_step": "Ask customer for credentials"
  }
}
```

For tests and air-gapped demo fallback, the adapter can run in `mock` mode. Production/live IMAP mode defaults to `openclaw` mode and shells out to an OpenClaw command.

Excel writing is a separate step. It consumes an `email_received` activity event that already contains OpenClaw `intent` and `extracted` fields, previews or appends a row to `Onboarding Tracker`, and writes a matching `spreadsheet_row_updated` activity event after an approved write. That second event is mandatory for Section A to reconstruct the workflow.

## CLI

```bash
python -m autoskill_agent.cli imap-poll --once --openclaw-mode openclaw
python -m autoskill_agent.cli email-to-excel --workbook workspace/workbooks/onboarding_tracker.xlsx --yes
```

For deterministic local tests:

```bash
python -m autoskill_agent.cli imap-poll --once --openclaw-mode mock
```

## Environment

```bash
export SKILLFORGE_IMAP_HOST=imap.gmail.com
export SKILLFORGE_IMAP_PORT=993
export SKILLFORGE_IMAP_USERNAME=your@gmail.com
export SKILLFORGE_IMAP_PASSWORD='gmail-app-password'
export SKILLFORGE_IMAP_MAILBOX=INBOX
export SKILLFORGE_OPENCLAW_COMMAND=openclaw
```

## Current Scope

This MVP handles the FDE onboarding tracker path. Cash reconciliation skill execution remains in `autoskill_agent.skillgen`; its approved execution currently creates a generated workbook artifact and update log, not cell-level reconciliation writes.
