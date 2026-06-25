import type { StepCompletedEvent, StepStartedEvent } from '../../types/skill'

interface StepCardProps {
  event: StepStartedEvent | StepCompletedEvent
  isActive?: boolean
}

function formatElapsed(ms: number): string {
  if (ms < 1000) return `${ms} ms`
  return `${(ms / 1000).toFixed(1)} sec`
}

function rawString(raw: Record<string, unknown> | undefined, key: string): string {
  const value = raw?.[key]
  return typeof value === 'string' ? value : ''
}

function rawNumber(raw: Record<string, unknown> | undefined, key: string): number | null {
  const value = raw?.[key]
  return typeof value === 'number' ? value : null
}

function rawStringList(raw: Record<string, unknown> | undefined, key: string): string[] {
  const value = raw?.[key]
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []
}

function rawNumberList(raw: Record<string, unknown> | undefined, key: string): number[] {
  const value = raw?.[key]
  return Array.isArray(value) ? value.filter((item): item is number => typeof item === 'number') : []
}

function fileName(path: string): string {
  return path.split(/[\\/]/).pop() ?? path
}

function workflowText(text: string): string {
  return text
    .replace(/\bGenerate Skills\b/g, 'Generate Workflows')
    .replace(/\bGenerated skill\b/g, 'Generated workflow')
    .replace(/\bgenerated skill\b/g, 'generated workflow')
    .replace(/\bSkill Run Output\b/g, 'Workflow Run Output')
    .replace(/\bskill run\b/g, 'workflow run')
    .replace(/\bSkill\b/g, 'Workflow')
    .replace(/\bskill\b/g, 'workflow')
}

export function StepCard({ event, isActive = false }: StepCardProps) {
  const completed = event.type === 'step_completed' ? event : null
  const workbookCreated = rawString(completed?.raw, 'workbook_created')
  const workbookUrl = rawString(completed?.raw, 'workbook_url')
  const draftUrl = rawString(completed?.raw, 'draft_url')
  const changedSheets = rawStringList(completed?.raw, 'changed_sheets')
  const cellsWritten = rawNumber(completed?.raw, 'cells_written')
  const rowsAdded = rawNumber(completed?.raw, 'rows_added')
  const updatedRows = rawNumberList(completed?.raw, 'updated_rows')
  const reviewRows = rawNumberList(completed?.raw, 'review_rows')
  const summarySheet = rawString(completed?.raw, 'summary_sheet')
  const hasOutputProof = Boolean(workbookCreated)

  return (
    <article className={`workflow-card ${isActive ? 'active' : 'complete'}`}>
      <div className="card-status">
        <span className="status-marker" />
        <span>{isActive ? 'Rendering' : 'Complete'}</span>
      </div>
      <div className="card-body">
        <div className="card-title-row">
          <h3>{workflowText(event.label)}</h3>
          <span className="step-time">
            {completed ? formatElapsed(completed.elapsed_ms) : new Date(event.timestamp).toLocaleTimeString()}
          </span>
        </div>
        {completed?.summary ? (
          <p className="step-summary">{workflowText(completed.summary)}</p>
        ) : (
          <p className="step-summary muted">Generating this part of the workflow.</p>
        )}

        {hasOutputProof && (
          <div className="output-proof">
            <div>
              <span>Generated file</span>
              <strong>{fileName(workbookCreated)}</strong>
              <small>{workbookCreated}</small>
            </div>
            <div className="output-link-row">
              {workbookUrl && (
                <a href={workbookUrl} target="_blank" rel="noreferrer">
                  Open Excel output
                </a>
              )}
              {draftUrl && (
                <a href={draftUrl} target="_blank" rel="noreferrer">
                  Open email draft
                </a>
              )}
            </div>
            <div className="output-proof-grid">
              {rowsAdded !== null && (
                <div>
                  <strong>{rowsAdded}</strong>
                  <span>rows updated</span>
                </div>
              )}
              {cellsWritten !== null && cellsWritten > 0 && (
                <div>
                  <strong>{cellsWritten}</strong>
                  <span>cells changed</span>
                </div>
              )}
              {changedSheets.length > 0 && (
                <div>
                  <strong>{changedSheets.length}</strong>
                  <span>sheet updates</span>
                </div>
              )}
            </div>
            {changedSheets.length > 0 && (
              <div className="sheet-list">
                {changedSheets.map(sheet => (
                  <span key={sheet}>{workflowText(sheet)}</span>
                ))}
              </div>
            )}
            {updatedRows.length > 0 && (
              <p className="proof-note">
                Updated Daily Reconciliation rows {updatedRows[0]}-{updatedRows[updatedRows.length - 1]}
                {reviewRows.length > 0 ? `; review rows ${reviewRows.join(', ')}` : ''}.
              </p>
            )}
            {summarySheet && <p className="proof-note">The generated spreadsheet includes a visible "{workflowText(summarySheet)}" sheet with the run summary.</p>}
          </div>
        )}
      </div>
    </article>
  )
}
