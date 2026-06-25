import client, { apiUrl } from './client'

export interface ConnectionStatus {
  id: string
  name: string
  kind: string
  description: string
  status: string
  event_count: number
  last_event_at: string
}

export interface Observation {
  id: string
  ts: string
  source: string
  type: string
  actor: string
  summary: string
}

export interface Roi {
  occurrences_observed: number
  frequency: string
  minutes_per_run: number
  runs_per_week: number
  time_saved_minutes_per_week: number
  time_saved_hours_per_week: number
  throughput_multiplier: number
  est_tokens_per_run: number
  added_ai_cost_usd_per_week: number
  added_ai_cost_usd_per_year: number
}

export interface Recommendation {
  id: string
  title: string
  workflow_family: string
  confidence: number
  source_apps: string[]
  trigger: string
  actions: string[]
  forbidden_actions: string[]
  target_artifact: string
  target_sheet: string
  common_fields: string[]
  status: 'proposed' | 'accepted'
  roi: Roi
}

export interface ReportTotals {
  workflows_found: number
  workflows_proposed: number
  workflows_accepted: number
  time_saved_minutes_per_week: number
  time_saved_hours_per_week: number
  fte_equivalent: number
  productivity_multiplier: number
  added_ai_cost_usd_per_week: number
  added_ai_cost_usd_per_year: number
  observation_cost_usd_per_week?: number
}

export interface TrendPoint {
  label: string
  value: number
}

export interface WeeklyReport {
  period: string
  generated_at: string
  summary: string
  totals: ReportTotals
  usage_trend: TrendPoint[]
  recommendations: Recommendation[]
}

export interface AcceptResult {
  status: string
  candidate_id: string
  skill_id: string
  bundle_dir: string
  local_path: string
  installed_files: string[]
  skill_md_preview: string
  planner: string
  codex_workflow?: string
  codex_invoke?: string
}

export async function getConnections(): Promise<ConnectionStatus[]> {
  const { data } = await client.get<ConnectionStatus[]>('/api/connections')
  return data
}

export async function getObservations(limit = 25): Promise<Observation[]> {
  const { data } = await client.get<Observation[]>(`/api/observations?limit=${limit}`)
  return data
}

export async function getRecommendations(): Promise<Recommendation[]> {
  const { data } = await client.get<Recommendation[]>('/api/recommendations')
  return data
}

export async function getWeeklyReport(): Promise<WeeklyReport> {
  const { data } = await client.get<WeeklyReport>('/api/report/weekly')
  return data
}

export interface AcceptProgress {
  stage: string
  label: string
  pct: number
  planner?: string | null
}

/**
 * Generate + install a skill, reporting live progress.
 *
 * Hits the SSE endpoint and parses progress events as they stream in. In mock
 * mode the endpoint returns plain JSON, so we detect the content-type and emit
 * a single synthetic "done" step instead.
 */
export async function acceptRecommendation(
  id: string,
  onProgress?: (p: AcceptProgress) => void,
): Promise<AcceptResult> {
  const res = await fetch(apiUrl(`/api/recommendations/${id}/accept/stream`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })

  const contentType = res.headers.get('content-type') ?? ''
  if (!res.body || !contentType.includes('text/event-stream')) {
    // Mock / non-streaming backend: parse the JSON result directly.
    const data = (await res.json()) as AcceptResult
    onProgress?.({ stage: 'done', label: 'Skill installed', pct: 100 })
    return data
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let result: AcceptResult | null = null

  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const frames = buffer.split('\n\n')
    buffer = frames.pop() ?? ''
    for (const frame of frames) {
      const dataLine = frame.split('\n').find(l => l.startsWith('data:'))
      if (!dataLine) continue
      const payload = JSON.parse(dataLine.slice(5).trim())
      if (payload.event === 'error') {
        throw new Error(payload.error ?? 'Skill generation failed.')
      }
      if (payload.event === 'done') {
        result = payload.result as AcceptResult
        onProgress?.({ stage: 'done', label: payload.label ?? 'Skill installed', pct: 100 })
      } else {
        onProgress?.({ stage: payload.stage, label: payload.label, pct: payload.pct, planner: payload.planner })
      }
    }
  }

  if (!result) throw new Error('The generation stream ended without a result.')
  return result
}

export interface SkillFeedbackResult {
  status: string
  rating: string
  note: string
  backend: string
  hydra_status?: string
}

export async function submitSkillFeedback(
  skillId: string,
  rating: 'up' | 'down',
  note: string,
): Promise<SkillFeedbackResult> {
  const { data } = await client.post<SkillFeedbackResult>(`/api/skills/${skillId}/feedback`, { rating, note })
  return data
}

export interface RunResult {
  status: string
  skill_id: string
  match_id?: string
  detail?: string
  memory?: {
    backend: string
    recalled: string[]
    auto_resolved: { transaction_id: string; applied: string }[]
    exceptions_before: number
    exceptions_after: number
  }
  artifacts?: {
    workbook?: string
    workbook_url?: string
    draft?: string
    draft_url?: string
    matched_count?: number
    exception_count?: number
  }
}

export async function runSkill(skillId: string): Promise<RunResult> {
  const { data } = await client.post<RunResult>(`/api/skills/${skillId}/run`, {})
  return data
}

export interface MemoryTraceEntry {
  ts: string
  op: 'write' | 'recall' | 'apply' | string
  backend?: string
  tenant_id?: string
  sub_tenant_id?: string
  query?: string
  hits?: number
  from_hydra?: number
  top?: { text: string; score?: number | null; source?: string }[]
  rating?: string
  stored?: string
  hydra_status?: string
  match_id?: string
  auto_resolved?: number
  exceptions_before?: number
  exceptions_after?: number
}

export async function getMemoryTrace(limit = 30): Promise<MemoryTraceEntry[]> {
  const { data } = await client.get<MemoryTraceEntry[]>(`/api/memory/trace?limit=${limit}`)
  return data
}

export interface MemoryStatus {
  backend: string
  tenant_id: string
  sub_tenant_id: string
  hydra_configured: boolean
  error?: string | null
}

export async function getMemoryStatus(): Promise<MemoryStatus> {
  const { data } = await client.get<MemoryStatus>('/api/memory/status')
  return data
}

export interface SkillStep {
  order: number
  id: string
  title: string
  type: string
  summary: string
}

export interface SkillGraph {
  trigger: string
  steps: SkillStep[]
  outcome: string
}

export interface SkillItem {
  skill_id: string
  name: string
  description: string
  status: string
  source_workflow: string
  step_count: number
  source_apps: string[]
  guardrails: string[]
  installed_locally: boolean
  installed_in_codex?: boolean
  codex_invoke?: string
  local_path: string
  invocations: number
  matches: number
  graph: SkillGraph
  trend: TrendPoint[]
}

export async function getSkills(): Promise<SkillItem[]> {
  const { data } = await client.get<SkillItem[]>('/api/skills')
  return data
}

export interface WorkflowImpact {
  people_involved: number
  runs_per_week: number
  team_hours_saved_per_week: number
  fte_equivalent: number
  productivity_multiplier: number
  added_ai_cost_usd_per_week: number
  added_ai_cost_usd_per_year: number
}

export interface WorkflowRec {
  id: string
  name: string
  description: string
  composed_of: string[]
  source_apps: string[]
  status: string
  priority: string
  fde_recommendation: string
  impact: WorkflowImpact
}

export async function getWorkflows(): Promise<WorkflowRec[]> {
  const { data } = await client.get<WorkflowRec[]>('/api/workflows')
  return data
}
