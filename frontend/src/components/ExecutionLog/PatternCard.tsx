import type { PatternDetectedEvent } from '../../types/skill'

interface PatternCardProps {
  event: PatternDetectedEvent
}

function percent(value: number): string {
  return `${Math.round(Math.max(0, Math.min(1, value)) * 100)}%`
}

function workflowText(text: string): string {
  return text
    .replace(/\bSkill Run ID\b/g, 'Workflow Run ID')
    .replace(/\bGenerated skill\b/g, 'Generated workflow')
    .replace(/\bgenerated skill\b/g, 'generated workflow')
    .replace(/\bSkill\b/g, 'Workflow')
    .replace(/\bskill\b/g, 'workflow')
}

export function PatternCard({ event }: PatternCardProps) {
  const fieldPreview = event.evidence.common_fields.slice(0, 8)
  const hiddenFieldCount = Math.max(0, event.evidence.common_fields.length - fieldPreview.length)

  return (
    <article className="pattern-card">
      <div className="insight-header">
        <div>
          <p className="eyebrow">Pattern spotted</p>
          <h3>{workflowText(event.title)}</h3>
        </div>
        <div className="insight-score">
          <strong>{percent(event.confidence)}</strong>
          <span>confidence</span>
        </div>
      </div>

      <section className="pattern-explanation-block">
        <h4>Pattern definition</h4>
        <p>{workflowText(event.pattern_definition ?? event.summary)}</p>
      </section>

      <section className="pattern-explanation-block">
        <h4>Why this is repetitive</h4>
        <p>{workflowText(event.explanation ?? event.summary)}</p>
      </section>

      <div className="pattern-metrics">
        <div>
          <strong>{event.episode_count}</strong>
          <span>examples</span>
        </div>
        <div>
          <strong>{event.sequence.length}</strong>
          <span>repeated actions</span>
        </div>
        <div>
          <strong>{event.evidence.common_fields.length}</strong>
          <span>shared fields</span>
        </div>
      </div>

      <div className="sequence-strip">
        {event.sequence.map((item, index) => (
          <div className="sequence-item" key={`${item}-${index}`}>
            <span>{index + 1}</span>
            <strong>{workflowText(item)}</strong>
          </div>
        ))}
      </div>

      {event.signals.length > 0 && (
        <div className="evidence-section">
          <h4>Why it matched</h4>
          <div className="evidence-list">
            {event.signals.map(signal => (
              <span key={signal}>{workflowText(signal)}</span>
            ))}
          </div>
        </div>
      )}

      {event.issues.length > 0 && (
        <div className="evidence-section">
          <h4>Issues to address</h4>
          <div className="issue-list">
            {event.issues.map(issue => (
              <span key={issue}>{workflowText(issue)}</span>
            ))}
          </div>
        </div>
      )}

      {fieldPreview.length > 0 && (
        <div className="evidence-section">
          <h4>Repeated fields</h4>
          <div className="field-list">
            {fieldPreview.map(field => (
              <span key={field}>{workflowText(field)}</span>
            ))}
            {hiddenFieldCount > 0 && <span>{hiddenFieldCount} more</span>}
          </div>
        </div>
      )}

      {event.next_trigger && (
        <div className="next-trigger">
          <span>Next matching activity</span>
          <strong>New activity with the same pattern</strong>
          {event.next_trigger.target_rows && <small>Target rows {event.next_trigger.target_rows}</small>}
        </div>
      )}
    </article>
  )
}
