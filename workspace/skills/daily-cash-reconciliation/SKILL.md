# Daily Cash Reconciliation Skill

## Purpose

Use this skill when the finance team receives a daily bank transaction email and needs to update the local cash reconciliation workbook.

## Trigger

- `trigger_email_received_daily_cash_reconciliation` (email_received): new daily bank transaction email
  - Subject starts with Daily bank transactions - Jun
  - Attachment matches bank_transactions_*.xlsx
  - Required file exists: workspace/workbooks/cash_recon.xlsx
  - Workbook workspace/workbooks/cash_recon.xlsx has sheet Daily Reconciliation
  - No existing reconciliation row for the email date

## Inputs

- `inbound_attachment` (xlsx_attachment)
- `target_workbook` (xlsx_workbook)
- `daily_reconciliation_sheet` (workbook_sheet)
- `payment_export_sheet` (workbook_sheet)
- `lists_rules_sheet` (workbook_sheet)

## Workflow Steps

1. Read bank attachment rows: Read transaction rows from the local bank spreadsheet attachment matching bank_transactions_*.xlsx.
2. Match transactions against Payment Export: Compare imported bank rows with the Payment Export sheet in the local finance workbook and build proposed matches.
3. Compute Amount Diff: Perform the repeated action: compute Amount Diff.
4. Preview Daily Reconciliation updates: Validate the proposed update set before approval, including target row range, allowed sheet scope, required fields, closed-period protection, and reviewed-row protection.
5. Fill Match Status: Compare the bank rows with the finance workbook.
6. Fill Exception Reason: Fill the Exception Reason field in the proposed spreadsheet update.
7. Fill Reviewer: Fill the Reviewer field in the proposed spreadsheet update.
8. Fill Reviewed At: Fill the Reviewed At field in the proposed spreadsheet update.
9. Fill Source Email ID: Fill the Source Email ID field in the proposed spreadsheet update.
10. Fill Skill Run ID: Fill the Skill Run ID field in the proposed spreadsheet update.
11. Draft summary reply: Prepare an unsent local reply draft describing matched rows, exception count, review items, and the pending reconciled spreadsheet path.
12. Request human approval: Ask a reviewer to approve the reconciliation preview and reply draft before any output file is written.
13. Create reconciled spreadsheet: After approval, create a new reconciled workbook in the generated folder, updating only allowed Daily Reconciliation rows and preserving reviewed or closed-period rows.
14. Write audit and SkillOps evidence: Record the approved run, output paths, validation results, exception count, and local-only side-effect evidence in the workspace logs.

## Expected Outcome

After human approval, the workflow creates a new reconciled spreadsheet, saves an unsent local reply draft, records exception details for review, and writes local audit and SkillOps evidence. It does not access the network, send email, modify closed-period sheets, overwrite reviewed rows, or read outside the workspace.

Files created:

- `workspace/workbooks/generated/{source_workbook}_{event_date}_reconciled.xlsx`
- `workspace/mail/drafts/{skill_id}_{event_date}_reply.eml`

Files modified:

- `workspace/workbooks/cash_recon.skill_updates.jsonl`
- `workspace/events/events.jsonl`

Side effects:

- Do not access the network.
- Do not modify closed-period sheets.
- Do not overwrite reviewed rows.
- Do not read outside the workspace.
- Do not send email automatically.
- Require human approval before workbook changes.

## Guardrails

- Do not access the network.
- Do not modify closed-period sheets.
- Do not overwrite reviewed rows.
- Do not read outside the workspace.
- Do not send email automatically.
- Require human approval before workbook changes.

## Success Criteria

- `workbook_can_be_reopened`
- `only_allowed_sheets_modified`
- `no_closed_period_sheets_modified`
- `no_reviewed_rows_overwritten`
- `reconciled_spreadsheet_created`
- `exception_count_matches_summary`
- `draft_created_but_not_sent`
- `audit_log_written`
- `target_rows_match_next_trigger`
- `field_populated_amount_diff`
- `field_populated_match_status`
- `field_populated_exception_reason`
- `field_populated_reviewer`
- `field_populated_reviewed_at`
- `field_populated_source_email_id`
- `field_populated_notes`
