import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiUrl } from '../api/client'
import { acceptRecommendation, getMemoryStatus, getSkills, runSkill, submitSkillFeedback } from '../api/observatory'
import type { AcceptProgress, RunResult, SkillItem } from '../api/observatory'
import { SourceChip } from '../components/common'
import { GenProgress } from '../components/GenProgress'
import { SkillDiagram } from '../components/SkillDiagram'
import { TrendChart } from '../components/TrendChart'

function RunResultCard({ result }: { result: RunResult }) {
  if (result.status === 'no_match') {
    return <p className="run-note">{result.detail ?? 'No matching bank email to run on right now.'}</p>
  }
  const mem = result.memory
  const art = result.artifacts ?? {}
  return (
    <div className="run-result">
      {mem && mem.auto_resolved.length > 0 ? (
        <div className="run-memory-hit">
          <strong>🧠 Applied {mem.auto_resolved.length} remembered correction{mem.auto_resolved.length === 1 ? '' : 's'} from {mem.backend === 'hydradb' ? 'HydraDB' : 'memory'}:</strong>
          <ul>
            {mem.auto_resolved.map(a => (
              <li key={a.transaction_id}>
                <code>{a.transaction_id}</code> auto-resolved — {a.applied.replace(/^.*?feedback:\s*/i, '').slice(0, 120)}
              </li>
            ))}
          </ul>
          <p className="run-exc">
            Exceptions: <span className="was">{mem.exceptions_before}</span> → <span className="now">{mem.exceptions_after}</span>
            <span className="run-exc-note"> (the agent didn't make you flag it again)</span>
          </p>
        </div>
      ) : (
        <p className="run-note">Ran with no remembered corrections to apply — {art.exception_count ?? 0} exception(s) flagged.</p>
      )}
      <div className="run-stats">
        <span>{art.matched_count ?? 0} matched</span>
        <span>· {art.exception_count ?? 0} exceptions</span>
      </div>
      <div className="run-artifacts">
        {art.workbook_url ? (
          <a className="artifact-link" href={apiUrl(art.workbook_url)} target="_blank" rel="noreferrer">
            ⬇ Reconciled spreadsheet (.xlsx)
          </a>
        ) : null}
        {art.draft_url ? (
          <a className="artifact-link" href={apiUrl(art.draft_url)} target="_blank" rel="noreferrer">
            ⬇ Reply draft (.eml)
          </a>
        ) : null}
      </div>
    </div>
  )
}

function RunPanel({
  onRun,
  running,
  result,
}: {
  onRun: () => void
  running: boolean
  result?: RunResult
}) {
  return (
    <div className="run-panel">
      <h4 className="skill-sub">Run this skill</h4>
      <p className="feedback-hint">
        Executes for real on a new bank email — recalls your past corrections from memory and applies them before
        writing the reconciled file.
      </p>
      <button type="button" className="accept-btn" disabled={running} onClick={onRun}>
        {running ? 'Running…' : '▶ Run on a new bank email'}
      </button>
      {result ? <RunResultCard result={result} /> : null}
    </div>
  )
}

function FeedbackPanel({
  onSubmit,
  onRegenerate,
  submitting,
  regenerating,
  progress,
  savedMsg,
}: {
  onSubmit: (rating: 'up' | 'down', note: string) => void
  onRegenerate: () => void
  submitting: boolean
  regenerating: boolean
  progress?: AcceptProgress
  savedMsg?: string
}) {
  const [rating, setRating] = useState<'up' | 'down' | null>(null)
  const [note, setNote] = useState('')

  return (
    <div className="feedback-panel">
      <h4 className="skill-sub">Teach this skill</h4>
      <p className="feedback-hint">
        Rate the generated skill and add a note. We remember it and fold it into the next version — across sessions.
      </p>
      <div className="feedback-rate">
        <button
          type="button"
          className={`thumb ${rating === 'up' ? 'sel up' : ''}`}
          onClick={() => setRating('up')}
          disabled={regenerating}
        >
          👍 Good
        </button>
        <button
          type="button"
          className={`thumb ${rating === 'down' ? 'sel down' : ''}`}
          onClick={() => setRating('down')}
          disabled={regenerating}
        >
          👎 Needs work
        </button>
      </div>
      <textarea
        className="feedback-note"
        placeholder="e.g. The description is too generic — say it reconciles bank transactions against the Payment Export sheet, offline."
        value={note}
        onChange={e => setNote(e.target.value)}
        disabled={regenerating}
        rows={3}
      />
      <div className="feedback-actions">
        <button
          type="button"
          className="ghost-btn"
          disabled={rating === null || submitting || regenerating}
          onClick={() => onSubmit(rating ?? 'up', note)}
        >
          {submitting ? 'Saving…' : 'Save feedback to memory'}
        </button>
        <button type="button" className="accept-btn" disabled={regenerating} onClick={onRegenerate}>
          Regenerate with feedback
        </button>
      </div>
      {savedMsg ? <p className="feedback-saved">✓ {savedMsg}</p> : null}
      {regenerating && progress ? <GenProgress pct={progress.pct} label={progress.label} /> : null}
    </div>
  )
}

function SkillDetail({
  skill,
  onSubmitFeedback,
  onRegenerate,
  onRun,
  submitting,
  regenerating,
  running,
  progress,
  savedMsg,
  runResult,
}: {
  skill: SkillItem
  onSubmitFeedback: (rating: 'up' | 'down', note: string) => void
  onRegenerate: () => void
  onRun: () => void
  submitting: boolean
  regenerating: boolean
  running: boolean
  progress?: AcceptProgress
  savedMsg?: string
  runResult?: RunResult
}) {
  return (
    <div className="skill-detail">
      <div className="skill-detail-head">
        <div>
          <h3>{skill.name}</h3>
          <div className="rec-apps">
            {skill.source_apps.map(app => (
              <SourceChip key={app} source={app} />
            ))}
            <span className={`local-pill ${skill.installed_locally ? 'is-local' : ''}`}>
              {skill.installed_locally ? 'Installed in Codex' : 'Generated (not installed)'}
            </span>
          </div>
        </div>
        <div className="skill-usage">
          <div className="metric-value">{skill.invocations}</div>
          <div className="metric-label">invocations</div>
        </div>
      </div>

      {skill.description ? <p className="skill-desc">{skill.description}</p> : null}
      {skill.installed_locally && skill.codex_invoke ? (
        <p className="skill-path">
          Installed as a Codex workflow — run <code>{skill.codex_invoke}</code> inside Codex
          {skill.local_path ? <> · <code>{skill.local_path}</code></> : null}
        </p>
      ) : skill.installed_locally && skill.local_path ? (
        <p className="skill-path">
          <code>{skill.local_path}</code>
        </p>
      ) : null}

      <h4 className="skill-sub">Invocation trend</h4>
      <TrendChart data={skill.trend ?? []} />

      <h4 className="skill-sub">What this skill does</h4>
      <SkillDiagram graph={skill.graph} />

      {skill.guardrails.length ? (
        <>
          <h4 className="skill-sub">Guardrails</h4>
          <ul className="skill-guardrails">
            {skill.guardrails.map((g, i) => (
              <li key={i}>{g}</li>
            ))}
          </ul>
        </>
      ) : null}

      <FeedbackPanel
        onSubmit={onSubmitFeedback}
        onRegenerate={onRegenerate}
        submitting={submitting}
        regenerating={regenerating}
        progress={progress}
        savedMsg={savedMsg}
      />

      <RunPanel onRun={onRun} running={running} result={runResult} />
    </div>
  )
}

export function SkillsView() {
  const queryClient = useQueryClient()
  const skills = useQuery({ queryKey: ['skills'], queryFn: getSkills })
  const memory = useQuery({ queryKey: ['memory-status'], queryFn: getMemoryStatus })
  const [selected, setSelected] = useState<string | null>(null)
  const [progress, setProgress] = useState<AcceptProgress | undefined>()
  const [savedMsg, setSavedMsg] = useState<Record<string, string>>({})

  const items = skills.data ?? []
  const active = items.find(s => s.skill_id === selected) ?? items[0] ?? null

  const feedback = useMutation({
    mutationFn: ({ skillId, rating, note }: { skillId: string; rating: 'up' | 'down'; note: string }) =>
      submitSkillFeedback(skillId, rating, note),
    onSuccess: (res, vars) =>
      setSavedMsg(prev => ({
        ...prev,
        [vars.skillId]: `Saved to ${res.backend === 'hydradb' ? 'HydraDB' : 'local'} memory — the next regenerate will use it.`,
      })),
  })

  const regenerate = useMutation({
    mutationFn: (candidateId: string) => acceptRecommendation(candidateId, p => setProgress(p)),
    onMutate: () => setProgress({ stage: 'start', label: 'Preparing…', pct: 4 }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['skills'] })
      setProgress(undefined)
    },
    onError: () => setProgress(undefined),
  })

  const [runResult, setRunResult] = useState<Record<string, RunResult>>({})
  const run = useMutation({
    mutationFn: (skillId: string) => runSkill(skillId),
    onSuccess: async (res, skillId) => {
      setRunResult(prev => ({ ...prev, [skillId]: res }))
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['skills'] }),
        queryClient.invalidateQueries({ queryKey: ['memory-trace'] }),
      ])
    },
  })

  if (skills.isLoading) return <div className="view"><div className="empty-state">Loading skills…</div></div>
  if (items.length === 0) {
    return (
      <div className="view">
        <div className="empty-state">
          No skills generated yet. Accept a recommendation to generate one and install it locally.
        </div>
      </div>
    )
  }

  const mem = memory.data
  return (
    <div className="view">
      <p className="view-note">
        {items.length} skill{items.length === 1 ? '' : 's'} generated · {items.filter(s => s.installed_locally).length} installed into Codex.
        {mem ? (
          <span className={`mem-badge ${mem.backend === 'hydradb' ? 'on' : ''}`}>
            <span className="mem-dot" /> Memory: {mem.backend === 'hydradb' ? `HydraDB · ${mem.tenant_id}` : 'local'}
          </span>
        ) : null}
      </p>
      <div className="skills-layout">
        <div className="skill-list">
          {items.map(skill => {
            const isActive = active?.skill_id === skill.skill_id
            return (
              <button
                key={skill.skill_id}
                type="button"
                className={`skill-pick ${isActive ? 'active' : ''}`}
                onClick={() => setSelected(skill.skill_id)}
              >
                <h4>{skill.name}</h4>
                <div className="skill-pick-meta">
                  <span>{skill.step_count} steps</span>
                  <span>· {skill.invocations} runs</span>
                  <span className={`dot-status status-${skill.status}`}>{skill.status}</span>
                </div>
                <div className="rec-apps">
                  {skill.source_apps.map(app => (
                    <SourceChip key={app} source={app} />
                  ))}
                  {skill.installed_locally ? <span className="local-pill is-local">in Codex</span> : null}
                </div>
              </button>
            )
          })}
        </div>
        {active ? (
          <SkillDetail
            key={active.skill_id}
            skill={active}
            onSubmitFeedback={(rating, note) =>
              feedback.mutate({ skillId: active.skill_id, rating, note })
            }
            onRegenerate={() => regenerate.mutate(active.source_workflow)}
            onRun={() => run.mutate(active.skill_id)}
            submitting={feedback.isPending && feedback.variables?.skillId === active.skill_id}
            regenerating={regenerate.isPending && regenerate.variables === active.source_workflow}
            running={run.isPending && run.variables === active.skill_id}
            progress={progress}
            savedMsg={savedMsg[active.skill_id]}
            runResult={runResult[active.skill_id]}
          />
        ) : null}
      </div>
    </div>
  )
}
