import MetricCard from './MetricCard'

interface RunStats {
  total: number
  matched: number
  exceptions: number
  outputFile: string
}

interface StatsPanelProps {
  runStats: RunStats | null
  status: 'idle' | 'connecting' | 'streaming' | 'paused' | 'done' | 'error'
}

function fileName(path: string): string {
  return path.split(/[\\/]/).pop() ?? path
}

function statusLabel(status: StatsPanelProps['status']): string {
  switch (status) {
    case 'paused':
      return 'Ready to review'
    case 'done':
      return 'Complete'
    case 'streaming':
      return 'Generating'
    case 'connecting':
      return 'Connecting'
    case 'error':
      return 'Needs attention'
    default:
      return 'Ready'
  }
}

export default function StatsPanel({ runStats, status }: StatsPanelProps) {
  return (
    <aside className="stats-panel">
      <div>
        <p className="eyebrow">Current run</p>
        <h2>{statusLabel(status)}</h2>
      </div>

      <div className="metric-stack">
        <MetricCard label="Records found" value={runStats?.total ?? '--'} detail="Items in the repeated workflow" />
        <MetricCard label="Can automate" value={runStats?.matched ?? '--'} detail="Steps the agent can handle" tone="good" />
        <MetricCard label="Needs review" value={runStats?.exceptions ?? '--'} detail="Items left for a person" tone={runStats?.exceptions ? 'warn' : 'good'} />
      </div>

      {runStats?.outputFile && (
        <div className="output-card">
          <span>Created file</span>
          <strong>{fileName(runStats.outputFile)}</strong>
        </div>
      )}
    </aside>
  )
}
