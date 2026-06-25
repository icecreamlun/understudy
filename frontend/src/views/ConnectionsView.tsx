import { useQuery } from '@tanstack/react-query'
import { getConnections } from '../api/observatory'
import { SourceChip } from '../components/common'
import { timeAgo } from '../lib/format'

export function ConnectionsView() {
  const connections = useQuery({ queryKey: ['connections'], queryFn: getConnections, refetchInterval: 15_000 })

  return (
    <div className="view">
      <p className="view-note">
        The event sources you’ve connected for us to watch. Onboarding is just connecting the tools your team already
        uses — we observe, we don’t act.
      </p>
      <div className="conn-grid">
        {connections.isLoading ? <div className="empty-state">Connecting…</div> : null}
        {(connections.data ?? []).map(conn => (
          <div className="conn-card" key={conn.id}>
            <div className="conn-head">
              <SourceChip source={conn.id} />
              <span className="conn-status">
                <span className="conn-dot" /> {conn.status}
              </span>
            </div>
            <p className="conn-desc">{conn.description}</p>
            <div className="conn-meta">
              <span>{conn.event_count} events observed</span>
              {conn.last_event_at ? <span>· last {timeAgo(conn.last_event_at)}</span> : null}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
