import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { acceptRecommendation, getRecommendations } from '../api/observatory'
import type { AcceptProgress, AcceptResult, Recommendation } from '../api/observatory'
import { Metric, SourceChip } from '../components/common'
import { GenProgress } from '../components/GenProgress'
import { cost, hours } from '../lib/format'

function RecommendationCard({
  rec,
  onAccept,
  accepting,
  progress,
  result,
  error,
}: {
  rec: Recommendation
  onAccept: (id: string) => void
  accepting: boolean
  progress?: AcceptProgress
  result?: AcceptResult
  error?: string
}) {
  const installed = rec.status === 'accepted' || result?.status === 'installed'
  return (
    <article className={`rec-card ${installed ? 'rec-installed' : ''}`}>
      <header className="rec-head">
        <div>
          <h3>{rec.title}</h3>
          <div className="rec-apps">
            {rec.source_apps.map(app => (
              <SourceChip key={app} source={app} />
            ))}
            <span className="rec-confidence">{Math.round(rec.confidence * 100)}% confidence</span>
          </div>
        </div>
        {installed ? <span className="rec-badge">Installed</span> : null}
      </header>

      <div className="rec-metrics">
        <Metric label="Time saved / wk" value={hours(rec.roi.time_saved_minutes_per_week)} />
        <Metric label="Productivity" value={`${rec.roi.throughput_multiplier}x`} sub="throughput on this task" />
        <Metric label="Added AI cost / wk" value={cost(rec.roi.added_ai_cost_usd_per_week)} sub={`${cost(rec.roi.added_ai_cost_usd_per_year)}/yr`} />
        <Metric label="Frequency" value={rec.roi.frequency.split(' ')[0]} sub={`${rec.roi.occurrences_observed} seen`} />
      </div>

      <p className="rec-trigger">
        <strong>Trigger:</strong> {rec.trigger || '—'}
        {rec.target_artifact ? (
          <>
            {' '}· updates <code>{rec.target_artifact}</code>
            {rec.target_sheet ? ` / ${rec.target_sheet}` : ''}
          </>
        ) : null}
      </p>

      {rec.actions.length ? (
        <details className="rec-actions">
          <summary>{rec.actions.length} steps in the proposed skill</summary>
          <ol>
            {rec.actions.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ol>
        </details>
      ) : null}

      <footer className="rec-foot">
        {installed ? (
          <div className="installed-banner">
            <strong>Skill installed locally.</strong>
            <code>{result?.local_path ?? '~/.claude/skills'}</code>
            {result?.skill_md_preview ? (
              <details className="skill-preview">
                <summary>Preview SKILL.md</summary>
                <pre>{result.skill_md_preview}…</pre>
              </details>
            ) : null}
          </div>
        ) : accepting ? (
          <GenProgress pct={progress?.pct ?? 4} label={progress?.label ?? 'Preparing…'} />
        ) : (
          <button className="accept-btn" type="button" onClick={() => onAccept(rec.id)}>
            Accept &amp; install skill
          </button>
        )}
        {error ? <p className="rec-error">{error}</p> : null}
      </footer>
    </article>
  )
}

export function RecommendationsView() {
  const queryClient = useQueryClient()
  const [results, setResults] = useState<Record<string, AcceptResult>>({})
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [progress, setProgress] = useState<Record<string, AcceptProgress>>({})

  const recommendations = useQuery({ queryKey: ['recommendations'], queryFn: getRecommendations })

  const accept = useMutation({
    mutationFn: (id: string) =>
      acceptRecommendation(id, p => setProgress(prev => ({ ...prev, [id]: p }))),
    onMutate: (id: string) => {
      setErrors(prev => ({ ...prev, [id]: '' }))
      setProgress(prev => ({ ...prev, [id]: { stage: 'start', label: 'Preparing…', pct: 4 } }))
    },
    onSuccess: async (result, id) => {
      if (result.status === 'installed') {
        setResults(prev => ({ ...prev, [id]: result }))
        setErrors(prev => ({ ...prev, [id]: '' }))
        await Promise.all([
          queryClient.invalidateQueries({ queryKey: ['recommendations'] }),
          queryClient.invalidateQueries({ queryKey: ['weekly-report'] }),
          queryClient.invalidateQueries({ queryKey: ['skills'] }),
        ])
      } else {
        setErrors(prev => ({ ...prev, [id]: 'The skill could not be generated. Check the API logs.' }))
      }
    },
    onError: (err, id) => {
      setErrors(prev => ({ ...prev, [id]: err instanceof Error ? err.message : 'Accept failed.' }))
    },
  })

  const recs = recommendations.data ?? []

  return (
    <div className="view">
      <p className="view-note">
        Workflows we detected by watching your activity. Accepting one generates a detailed skill and installs it
        locally — it still runs under human approval, never automatically.
      </p>
      <div className="rec-list">
        {recommendations.isLoading ? <div className="empty-state">Mining your activity for repeated workflows…</div> : null}
        {!recommendations.isLoading && recs.length === 0 ? (
          <div className="empty-state">No repeated workflows detected yet. Keep working — we’re watching.</div>
        ) : null}
        {recs.map(rec => (
          <RecommendationCard
            key={rec.id}
            rec={rec}
            onAccept={accept.mutate}
            accepting={accept.isPending && accept.variables === rec.id}
            progress={progress[rec.id]}
            result={results[rec.id]}
            error={errors[rec.id]}
          />
        ))}
      </div>
    </div>
  )
}
