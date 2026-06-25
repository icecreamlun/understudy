import { useQuery } from '@tanstack/react-query'
import { getMemoryStatus, getMemoryTrace } from '../api/observatory'
import type { MemoryTraceEntry } from '../api/observatory'

function TraceRow({ e }: { e: MemoryTraceEntry }) {
  const time = (e.ts ?? '').slice(11, 19)
  if (e.op === 'write') {
    return (
      <li className="trace-item write">
        <span className="trace-time">{time}</span>
        <span className="trace-op op-write">WRITE → HydraDB</span>
        <span className="trace-body">{e.stored}</span>
      </li>
    )
  }
  if (e.op === 'recall') {
    const top = e.top?.[0]
    return (
      <li className="trace-item recall">
        <span className="trace-time">{time}</span>
        <span className="trace-op op-recall">RECALL ← HydraDB</span>
        <span className="trace-body">
          <em>“{e.query}”</em> → {e.hits ?? 0} hit{e.hits === 1 ? '' : 's'}
          {typeof e.from_hydra === 'number' ? ` (${e.from_hydra} from HydraDB)` : ''}
          {top ? <span className="trace-top"> · top: {top.text}{top.score != null ? ` (score ${Number(top.score).toFixed(2)})` : ''}</span> : null}
        </span>
      </li>
    )
  }
  if (e.op === 'apply') {
    return (
      <li className="trace-item apply">
        <span className="trace-time">{time}</span>
        <span className="trace-op op-apply">APPLY</span>
        <span className="trace-body">
          Auto-resolved {e.auto_resolved ?? 0} exception{e.auto_resolved === 1 ? '' : 's'} from memory · exceptions {e.exceptions_before} → {e.exceptions_after}
        </span>
      </li>
    )
  }
  return (
    <li className="trace-item">
      <span className="trace-time">{time}</span>
      <span className="trace-op">{e.op}</span>
    </li>
  )
}

export function MemoryView() {
  const status = useQuery({ queryKey: ['memory-status'], queryFn: getMemoryStatus })
  const trace = useQuery({ queryKey: ['memory-trace'], queryFn: () => getMemoryTrace(40), refetchInterval: 4000 })

  const mem = status.data
  const rows = trace.data ?? []

  return (
    <div className="view">
      <p className="view-note">
        Every time the agent writes a preference or recalls one, it shows up here — autonomous reads and writes against
        HydraDB. This is the agent's long-term memory, live.
      </p>

      {mem ? (
        <div className="mem-status-card">
          <div className="mem-status-row">
            <span className={`mem-dot ${mem.backend === 'hydradb' ? 'on' : ''}`} />
            <strong>{mem.backend === 'hydradb' ? 'Connected to HydraDB' : 'Local fallback memory'}</strong>
          </div>
          <div className="mem-status-meta">
            <span>tenant: <code>{mem.tenant_id}</code></span>
            <span>namespace: <code>{mem.sub_tenant_id}</code></span>
          </div>
        </div>
      ) : null}

      <h4 className="skill-sub">Memory activity</h4>
      {rows.length === 0 ? (
        <div className="empty-state">No memory activity yet. Give a skill feedback or run one to see reads/writes.</div>
      ) : (
        <ul className="trace-list">
          {rows.map((e, i) => (
            <TraceRow key={`${e.ts}-${i}`} e={e} />
          ))}
        </ul>
      )}
    </div>
  )
}
