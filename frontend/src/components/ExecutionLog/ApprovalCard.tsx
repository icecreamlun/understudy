import type { ApprovalRequiredEvent } from '../../types/skill'

interface ApprovalCardProps {
  event: ApprovalRequiredEvent
  onApprove: () => void
  onReject: () => void
  decided?: { decision: 'approved' | 'rejected'; actor?: string; timestamp: string } | null
}

function labelForStat(key: string): string {
  switch (key) {
    case 'total':
      return 'Records'
    case 'matched':
      return 'Automated'
    case 'exceptions':
      return 'Review'
    default:
      return key.replace(/_/g, ' ')
  }
}

function fileName(path: string): string {
  return path.split(/[\\/]/).pop() ?? path
}

function workflowText(text: string): string {
  return text
    .replace(/\bskill_id\b/g, 'workflow_id')
    .replace(/\{skill_id\}/g, '{workflow_id}')
    .replace(/\bGenerated skill\b/g, 'Generated workflow')
    .replace(/\bgenerated skill\b/g, 'generated workflow')
    .replace(/\bSkill\b/g, 'Workflow')
    .replace(/\bskill\b/g, 'workflow')
}

function cleanGuardrail(text: string): string {
  const labels: Record<string, string> = {
    'No email will be sent': 'No email is sent automatically',
    'No network access': 'No external network access',
    'No closed-period sheets modified': 'Protected files are left unchanged',
    'Human approval required before write': 'Review required before writing files',
  }
  return labels[text] ?? text
}

export function ApprovalCard({ event, onApprove, onReject, decided }: ApprovalCardProps) {
  const { proposed_changes, guardrails } = event
  const orderedStats = ['total', 'matched', 'exceptions']
    .filter(key => key in proposed_changes.stats)
    .map(key => [key, proposed_changes.stats[key]] as const)
  const total = Number(proposed_changes.stats.total ?? 0)
  const matched = Number(proposed_changes.stats.matched ?? 0)
  const exceptions = Number(proposed_changes.stats.exceptions ?? 0)
  const exceptionWord = exceptions === 1 ? 'item' : 'items'

  if (decided) {
    const approved = decided.decision === 'approved'
    return (
      <article className={`approval-result ${approved ? 'approved' : 'rejected'}`}>
        <div>
          <p className="eyebrow">Review result</p>
          <h3>{approved ? 'Run approved' : 'Run declined'}</h3>
        </div>
        <span>{decided.actor ? `${decided.actor} at ` : ''}{new Date(decided.timestamp).toLocaleTimeString()}</span>
      </article>
    )
  }

  return (
    <article className="approval-card">
      <div className="approval-header">
        <div>
          <p className="eyebrow">Approval required</p>
          <h3>Approve this FDE workflow run</h3>
        </div>
        <span className="review-indicator" aria-label="Waiting for review" />
      </div>

      <p className="approval-description">
        The agent found {total} records in this repeated workflow. It can handle {matched} automatically and leaves {exceptions} {exceptionWord} for review.
      </p>

      <div className="stat-grid">
        {orderedStats.map(([key, value]) => (
          <div className="stat-tile" key={key}>
            <span>{labelForStat(key)}</span>
            <strong>{value}</strong>
          </div>
        ))}
      </div>

      {proposed_changes.exceptions && proposed_changes.exceptions.length > 0 && (
        <div className="exception-box">
          <h4>Items to review</h4>
          {proposed_changes.exceptions.map((item, index) => (
            <div className="exception-row" key={`${item.transaction_id ?? index}`}>
              <strong>{item.transaction_id ?? `Exception ${index + 1}`}</strong>
              <span>{item.description}</span>
              <span>{item.bank_amount} vs {item.erp_amount}</span>
            </div>
          ))}
        </div>
      )}

      <div className="file-section">
        <h4>Files to create</h4>
        {proposed_changes.files_to_create.map(path => (
          <div className="file-row" key={path}>
            <span>{workflowText(fileName(path))}</span>
            <small>{workflowText(path)}</small>
          </div>
        ))}
      </div>

      <div className="guardrail-box">
        <h4>Safety checks</h4>
        <ul>
          {guardrails.map(item => (
            <li key={item}>{cleanGuardrail(item)}</li>
          ))}
        </ul>
      </div>

      <div className="action-row">
        <button className="primary-button" onClick={onApprove}>
          Approve and run
        </button>
        <button className="secondary-button danger" onClick={onReject}>
          Reject
        </button>
      </div>
    </article>
  )
}
