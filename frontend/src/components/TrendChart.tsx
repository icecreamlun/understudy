import type { TrendPoint } from '../api/observatory'

/** Lightweight dependency-free SVG bar chart for invocation trends. */
export function TrendChart({ data, height = 96 }: { data: TrendPoint[]; height?: number }) {
  if (!data || data.length === 0) {
    return <div className="trend-empty">No invocations recorded yet.</div>
  }
  const max = Math.max(1, ...data.map(d => d.value))
  const total = data.reduce((sum, d) => sum + d.value, 0)

  return (
    <div className="trend-chart" style={{ ['--trend-h' as string]: `${height}px` }}>
      <div className="trend-bars" style={{ height }}>
        {data.map((d, i) => {
          const pct = Math.round((d.value / max) * 100)
          return (
            <div className="trend-col" key={`${d.label}-${i}`} title={`${d.label}: ${d.value}`}>
              <div className="trend-bar-track">
                <div className={`trend-bar ${d.value === 0 ? 'is-zero' : ''}`} style={{ height: `${pct}%` }}>
                  {d.value > 0 ? <span className="trend-val">{d.value}</span> : null}
                </div>
              </div>
              <span className="trend-label">{d.label}</span>
            </div>
          )
        })}
      </div>
      <div className="trend-total">{total} invocation{total === 1 ? '' : 's'} over {data.length} days</div>
    </div>
  )
}
