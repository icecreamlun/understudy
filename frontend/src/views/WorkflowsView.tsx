import { useQuery } from '@tanstack/react-query'
import { getWorkflows } from '../api/observatory'
import type { WorkflowRec } from '../api/observatory'
import { Metric, SourceChip } from '../components/common'
import { cost } from '../lib/format'

function WorkflowCard({ wf }: { wf: WorkflowRec }) {
  return (
    <article className="wf-card">
      <header className="wf-head">
        <div>
          <h3>{wf.name}</h3>
          <div className="rec-apps">
            {wf.source_apps.map(app => (
              <SourceChip key={app} source={app} />
            ))}
            <span className="wf-people">{wf.impact.people_involved} people involved</span>
          </div>
        </div>
        <span className={`wf-priority prio-${wf.priority}`}>{wf.priority} priority</span>
      </header>

      <p className="wf-desc">{wf.description}</p>

      <div className="wf-compose">
        {wf.composed_of.map(part => (
          <span className="wf-chip" key={part}>{part}</span>
        ))}
      </div>

      <div className="rec-metrics">
        <Metric label="Team time / wk" value={`${wf.impact.team_hours_saved_per_week}h`} sub={`≈ ${wf.impact.fte_equivalent} FTE`} />
        <Metric label="Productivity" value={`${wf.impact.productivity_multiplier}x`} sub="on these tasks" />
        <Metric label="Added AI cost / wk" value={cost(wf.impact.added_ai_cost_usd_per_week)} sub={`${cost(wf.impact.added_ai_cost_usd_per_year)}/yr`} />
        <Metric label="Runs / wk" value={String(wf.impact.runs_per_week)} />
      </div>

      <div className="wf-rec">
        <span className="wf-rec-label">FDE recommendation</span>
        <p>{wf.fde_recommendation}</p>
      </div>
    </article>
  )
}

export function WorkflowsView() {
  const workflows = useQuery({ queryKey: ['workflows'], queryFn: getWorkflows })
  const items = workflows.data ?? []

  return (
    <div className="view">
      <p className="view-note">
        Above individual skills: the end-to-end processes a forward-deployed engineer would deploy to lift the whole
        team’s efficiency. Each composes several skills into one workflow, with the org-level impact and a
        deployment recommendation.
      </p>
      <div className="rec-list">
        {workflows.isLoading ? <div className="empty-state">Composing org-level workflows…</div> : null}
        {!workflows.isLoading && items.length === 0 ? (
          <div className="empty-state">No org workflows yet — accept more skills so we can compose them.</div>
        ) : null}
        {items.map(wf => (
          <WorkflowCard key={wf.id} wf={wf} />
        ))}
      </div>
    </div>
  )
}
