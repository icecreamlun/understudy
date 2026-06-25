import { SOURCE_LABEL } from '../lib/format'

export function SourceChip({ source }: { source: string }) {
  return <span className={`source-chip source-${source}`}>{SOURCE_LABEL[source] ?? source}</span>
}

export function Metric({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="metric">
      <div className="metric-value">{value}</div>
      <div className="metric-label">{label}</div>
      {sub ? <div className="metric-sub">{sub}</div> : null}
    </div>
  )
}
