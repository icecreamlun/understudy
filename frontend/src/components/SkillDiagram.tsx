import type { SkillGraph } from '../api/observatory'

const TYPE_LABEL: Record<string, string> = {
  read_input: 'Read',
  transform: 'Transform',
  analyze: 'Analyze',
  human_approval: 'Approve',
  draft_output: 'Draft',
  write_output: 'Write',
  validate: 'Validate',
}

export function SkillDiagram({ graph }: { graph: SkillGraph }) {
  return (
    <div className="diagram">
      <div className="diag-node diag-trigger">
        <span className="diag-kind">Trigger</span>
        <span className="diag-title">{graph.trigger}</span>
      </div>
      {graph.steps.map(step => (
        <div key={`${step.order}-${step.id}`} className={`diag-node diag-${step.type}`}>
          <span className="diag-kind">{TYPE_LABEL[step.type] ?? (step.type || 'Step')}</span>
          <span className="diag-title">{step.title}</span>
          {step.summary ? <span className="diag-summary">{step.summary}</span> : null}
        </div>
      ))}
      {graph.outcome ? (
        <div className="diag-node diag-outcome">
          <span className="diag-kind">Outcome</span>
          <span className="diag-title">{graph.outcome}</span>
        </div>
      ) : null}
    </div>
  )
}
