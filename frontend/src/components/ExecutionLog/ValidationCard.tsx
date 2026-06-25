import type { ValidationResultEvent } from '../../types/skill'

interface ValidationCardProps {
  event: ValidationResultEvent
}

function humanCheckName(name: string): string {
  const labels: Record<string, string> = {
    workbook_can_be_reopened: 'Created file opens correctly',
    only_allowed_sheets_modified: 'Only intended content changed',
    no_closed_period_sheets_modified: 'Protected content unchanged',
    no_reviewed_rows_overwritten: 'Reviewed rows preserved',
    reconciled_spreadsheet_created: 'Output file created',
    generated_spreadsheet_contains_run_output: 'Generated spreadsheet contains run output',
    exception_count_matches_summary: 'Exception count matches summary',
    draft_created_but_not_sent: 'Draft saved but not sent',
    audit_log_written: 'Run record saved',
  }
  return labels[name] ?? name.replace(/_/g, ' ')
}

export function ValidationCard({ event }: ValidationCardProps) {
  const passed = event.status === 'passed'

  return (
    <article className="validation-card">
      <div className="card-title-row">
        <div>
          <p className="eyebrow">Final checks</p>
          <h3>{passed ? 'Everything passed' : 'Needs attention'}</h3>
        </div>
        <span className={`validation-badge ${passed ? 'passed' : 'failed'}`}>
          {passed ? 'Passed' : 'Failed'}
        </span>
      </div>

      <div className="check-grid">
        {event.checks.map(check => (
          <div className="check-row" key={check.name}>
            <span className={`check-dot ${check.status}`} />
            <span>{humanCheckName(check.name)}</span>
            {check.detail && <small>{check.detail}</small>}
          </div>
        ))}
      </div>
    </article>
  )
}
