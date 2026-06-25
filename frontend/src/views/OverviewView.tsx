import { useQuery } from '@tanstack/react-query'
import { getWeeklyReport } from '../api/observatory'
import { Metric } from '../components/common'
import { TrendChart } from '../components/TrendChart'
import { cost, hours } from '../lib/format'

export function OverviewView() {
  const report = useQuery({ queryKey: ['weekly-report'], queryFn: getWeeklyReport })
  const totals = report.data?.totals

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
          <div className="totals-grid">
            <Metric label="Time freed / wk" value={hours(totals.time_saved_minutes_per_week)} sub={`≈ ${totals.fte_equivalent} FTE`} />
            <Metric label="Productivity" value={`${totals.productivity_multiplier}x`} sub="on automated tasks" />
            <Metric label="Added AI cost / wk" value={cost(totals.added_ai_cost_usd_per_week)} sub={`${cost(totals.added_ai_cost_usd_per_year)}/yr`} />
            <Metric label="Workflows found" value={String(totals.workflows_found)} sub={`${totals.workflows_accepted} accepted`} />
          </div>
        ) : null}
      </div>

      <div className="panel">
        <h3 className="fde-section-title">Skill invocation trend</h3>
        <p className="panel-sub">How often your installed skills have run, by day.</p>
        <TrendChart data={report.data?.usage_trend ?? []} />
      </div>

      <p className="view-note">
        We watch your connected tools, learn how your team works, and recommend what to automate — as reviewable
        skills you install locally. We never run anything ourselves.
      </p>
    </div>
  )
}
