import { useQuery } from '@tanstack/react-query'
import { getWeeklyReport } from '../api/observatory'
import { Metric, SourceChip } from '../components/common'
import { TrendChart } from '../components/TrendChart'
import { cost, hours } from '../lib/format'

export function OverviewView() {
  const report = useQuery({ queryKey: ['weekly-report'], queryFn: getWeeklyReport })
  const totals = report.data?.totals
  const recs = report.data?.recommendations ?? []

  return (
    <div className="view">
      <div className="report-card">
        <div className="report-head">
          <h2 className="fde-section-title">Weekly FDE report</h2>
          {report.data ? <span className="report-period">{report.data.period}</span> : null}
        </div>
        <p className="report-summary">
          {report.isLoading ? 'Generating this week’s advisory…' : report.data?.summary}
        </p>
        {totals ? (
          <>
            <div className="totals-grid">
              <Metric label="Time freed / wk" value={hours(totals.time_saved_minutes_per_week)} sub={`≈ ${totals.fte_equivalent} FTE`} />
              <Metric label="Productivity" value={`${totals.productivity_multiplier}x`} sub="on automated tasks" />
              <Metric label="Added AI cost / wk" value={cost(totals.added_ai_cost_usd_per_week)} sub={`${cost(totals.added_ai_cost_usd_per_year)}/yr`} />
              <Metric label="Workflows found" value={String(totals.workflows_found)} sub={`${totals.workflows_accepted} accepted · ${totals.workflows_proposed} proposed`} />
            </div>
            <div className="totals-grid secondary">
              <Metric label="Hours / yr" value={`${Math.round(totals.time_saved_hours_per_week * 52)}h`} sub="at this run rate" />
              <Metric label="Net new AI spend / yr" value={cost(totals.added_ai_cost_usd_per_year)} sub="it adds cost, not cuts it" />
              <Metric label="Observation cost / wk" value={cost(totals.observation_cost_usd_per_week ?? 0)} sub="always-on watching" />
              <Metric label="Skills run / day" value={`${Math.round((report.data?.usage_trend ?? []).slice(-1)[0]?.value ?? 0)}`} sub="most recent day" />
            </div>
          </>
        ) : null}
      </div>

      <div className="panel">
        <h3 className="fde-section-title">Skill invocation trend</h3>
        <p className="panel-sub">How often your installed Codex workflows have run, by day.</p>
        <TrendChart data={report.data?.usage_trend ?? []} />
      </div>

      {recs.length ? (
        <div className="panel">
          <h3 className="fde-section-title">Automatable workflows we found this week</h3>
          <p className="panel-sub">Detected from your activity, ranked by the time they’d free.</p>
          <table className="report-table">
            <thead>
              <tr>
                <th>Workflow</th>
                <th>Sources</th>
                <th>Confidence</th>
                <th>Time / wk</th>
                <th>Throughput</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {[...recs]
                .sort((a, b) => b.roi.time_saved_hours_per_week - a.roi.time_saved_hours_per_week)
                .map(r => (
                  <tr key={r.id}>
                    <td className="rt-name">{r.title}</td>
                    <td>
                      <span className="rt-apps">
                        {r.source_apps.map(app => <SourceChip key={app} source={app} />)}
                      </span>
                    </td>
                    <td>{Math.round(r.confidence * 100)}%</td>
                    <td>{r.roi.time_saved_hours_per_week}h</td>
                    <td>{r.roi.throughput_multiplier}x</td>
                    <td>
                      <span className={`rt-status ${r.status === 'accepted' ? 'done' : ''}`}>
                        {r.status === 'accepted' ? 'installed in Codex' : 'proposed'}
                      </span>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      ) : null}

      <p className="view-note">
        Understudy watches your connected tools, learns how your team works, and turns the repeated workflows into
        Codex skills. Every skill installs into Codex and runs only under human approval.
      </p>
    </div>
  )
}
