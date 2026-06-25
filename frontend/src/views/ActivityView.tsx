import { useQuery } from '@tanstack/react-query'
import { getObservations } from '../api/observatory'
import { SourceChip } from '../components/common'
import { timeAgo } from '../lib/format'

export function ActivityView() {
  const observations = useQuery({
    queryKey: ['observations'],
    queryFn: () => getObservations(50),
    refetchInterval: 15_000,
  })

  const rows = observations.data ?? []

  return (
    <div className="view">
      <p className="view-note">
        Everything we observe across your connected sources, logged in the background. This is the raw signal we mine
        into workflow recommendations.
      </p>
      <div className="feed-card">
        <ul className="feed-list">
          {observations.isLoading ? <li className="empty-state">Loading activity…</li> : null}
          {!observations.isLoading && rows.length === 0 ? <li className="empty-state">No activity observed yet.</li> : null}
          {rows.map(obs => (
            <li className="feed-row" key={`${obs.id}-${obs.ts}`}>
              <SourceChip source={obs.source} />
              <span className="feed-summary">{obs.summary}</span>
              <span className="feed-time">{timeAgo(obs.ts)}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
