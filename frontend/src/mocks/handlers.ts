import { http, HttpResponse } from 'msw'

// All timestamps are relative to load time so the "live activity" feed looks fresh.
const now = Date.now()
const minsAgo = (m: number) => new Date(now - m * 60000).toISOString()

// ---- in-memory mock state (resets on page reload) ----
const accepted = new Set<string>(['cand_daily_cash_recon_001'])

type Trend = { label: string; value: number }
const zeros = (n: number): Trend[] => Array.from({ length: n }, (_, i) => ({ label: `d-${n - i}`, value: 0 }))

const CASH_TREND: Trend[] = [
  { label: '06-08', value: 3 },
  { label: '06-09', value: 4 },
  { label: '06-10', value: 5 },
  { label: '06-11', value: 4 },
  { label: '06-12', value: 6 },
  { label: '06-13', value: 5 },
  { label: '06-14', value: 7 },
  { label: '06-15', value: 3 },
]

const RECOMMENDATIONS = [
  {
    id: 'cand_daily_cash_recon_001',
    title: 'Daily Cash Reconciliation',
    workflow_family: 'daily_cash_reconciliation',
    confidence: 0.95,
    source_apps: ['gmail', 'excel'],
    trigger: 'new daily bank transaction email',
    actions: [
      'read bank attachment rows',
      'match transactions against Payment Export',
      'compute Amount Diff',
      'fill Match Status / Exception Reason',
      'draft summary reply',
      'write audit log',
    ],
    forbidden_actions: ['send email automatically', 'access network', 'overwrite reviewed rows'],
    target_artifact: 'cash_recon.xlsx',
    target_sheet: 'Daily Reconciliation',
    common_fields: ['Recon Date', 'Txn ID', 'Amount Diff', 'Match Status'],
    roi: {
      occurrences_observed: 3,
      frequency: 'daily (business days)',
      minutes_per_run: 36,
      runs_per_week: 5,
      time_saved_minutes_per_week: 144,
      time_saved_hours_per_week: 2.4,
      throughput_multiplier: 5.1,
      est_tokens_per_run: 24600,
      added_ai_cost_usd_per_week: 0.53,
      added_ai_cost_usd_per_year: 27.56,
    },
  },
  {
    id: 'cand_vendor_onboarding_001',
    title: 'Vendor Onboarding Intake',
    workflow_family: 'fde_intake_candidate',
    confidence: 0.88,
    source_apps: ['gmail', 'excel'],
    trigger: 'new customer onboarding request email',
    actions: [
      'parse onboarding email',
      'extract customer + blockers',
      'append Onboarding Tracker row',
      'draft next-step reply',
    ],
    forbidden_actions: ['send email automatically', 'access network'],
    target_artifact: 'onboarding_tracker.xlsx',
    target_sheet: 'Onboarding Tracker',
    common_fields: ['Customer', 'Contact', 'Request Type', 'Blockers', 'Next Step'],
    roi: {
      occurrences_observed: 4,
      frequency: 'weekly',
      minutes_per_run: 18,
      runs_per_week: 6,
      time_saved_minutes_per_week: 86,
      time_saved_hours_per_week: 1.4,
      throughput_multiplier: 4.5,
      est_tokens_per_run: 9800,
      added_ai_cost_usd_per_week: 0.36,
      added_ai_cost_usd_per_year: 18.72,
    },
  },
]

const CASH_SKILL = {
  skill_id: 'daily_cash_reconciliation',
  name: 'Daily Cash Reconciliation',
  description:
    'When the daily bank transaction email arrives, read the attachment, reconcile against the finance workbook, flag exceptions, and draft a summary reply — all under human approval.',
  status: 'active',
  source_workflow: 'cand_daily_cash_recon_001',
  step_count: 8,
  source_apps: ['excel', 'gmail'],
  guardrails: [
    'No email is sent automatically',
    'No network access',
    'No reviewed rows overwritten',
    'Human approval before any write',
  ],
  installed_locally: true,
  local_path: '~/.claude/skills/daily-cash-reconciliation',
  invocations: 37,
  matches: 42,
  graph: {
    trigger: 'Daily bank transactions email arrives',
    steps: [
      { order: 1, id: 'read', title: 'Read bank attachment', type: 'read_input', summary: 'Load the bank_transactions_*.xlsx rows.' },
      { order: 2, id: 'match', title: 'Match against Payment Export', type: 'transform', summary: 'Pair each bank row with the ledger.' },
      { order: 3, id: 'diff', title: 'Compute amount differences', type: 'analyze', summary: 'Flag rows where amounts disagree.' },
      { order: 4, id: 'fill', title: 'Fill Match Status / Exception', type: 'transform', summary: 'Annotate each reconciliation row.' },
      { order: 5, id: 'draft', title: 'Draft summary reply', type: 'draft_output', summary: 'Prepare the daily result email (not sent).' },
      { order: 6, id: 'approve', title: 'Reviewer approves', type: 'human_approval', summary: 'Human confirms before any file write.' },
      { order: 7, id: 'write', title: 'Write reconciled sheet', type: 'write_output', summary: 'Create the reconciled workbook copy.' },
      { order: 8, id: 'validate', title: 'Validate outputs', type: 'validate', summary: 'Re-open file, check guardrails, write run record.' },
    ],
    outcome: 'Reconciled spreadsheet + draft reply, fully auditable.',
  },
  trend: CASH_TREND,
}

function skillFromRec(rec: (typeof RECOMMENDATIONS)[number]) {
  const slug = (rec.workflow_family || rec.id).replace(/_/g, '-')
  return {
    skill_id: rec.workflow_family || rec.id,
    name: rec.title,
    description: `Generated from the “${rec.title}” workflow. Runs under human approval.`,
    status: 'active',
    source_workflow: rec.id,
    step_count: rec.actions.length,
    source_apps: rec.source_apps,
    guardrails: ['No email is sent automatically', 'No network access', 'Human approval before any write'],
    installed_locally: true,
    local_path: `~/.claude/skills/${slug}`,
    invocations: 0,
    matches: 0,
    graph: {
      trigger: rec.trigger,
      steps: rec.actions.map((a, i) => ({
        order: i + 1,
        id: `step_${i + 1}`,
        title: a,
        type: i === 0 ? 'read_input' : i === rec.actions.length - 1 ? 'write_output' : 'transform',
        summary: '',
      })),
      outcome: 'Local output produced after approval.',
    },
    trend: zeros(8),
  }
}

function currentSkills() {
  const skills = [CASH_SKILL] as ReturnType<typeof skillFromRec>[]
  const seen = new Set(skills.map(s => s.skill_id))
  for (const rec of RECOMMENDATIONS) {
    if (!accepted.has(rec.id)) continue
    const sid = rec.workflow_family || rec.id
    if (seen.has(sid)) continue
    seen.add(sid)
    skills.push(skillFromRec(rec))
  }
  return skills
}

function aggregateTrend() {
  const skills = currentSkills()
  return CASH_TREND.map((t, i) => ({
    label: t.label,
    value: skills.reduce((sum, s) => sum + (s.trend[i]?.value ?? 0), 0),
  }))
}

const OBSERVATIONS = [
  { id: 'e1', source: 'excel', type: 'spreadsheet_row_updated', actor: 'analyst_1', summary: 'cash_recon.xlsx · Daily Reconciliation row 137 updated', ts: minsAgo(3) },
  { id: 'e2', source: 'gmail', type: 'email_received', actor: 'analyst_1', summary: 'Email from ops@bank.com: Daily bank transactions - Jun 15', ts: minsAgo(8) },
  { id: 'e3', source: 'excel', type: 'spreadsheet_row_updated', actor: 'analyst_2', summary: 'onboarding_tracker.xlsx · Onboarding Tracker row 12 updated', ts: minsAgo(22) },
  { id: 'e4', source: 'gmail', type: 'outbound_message_created', actor: 'analyst_1', summary: 'Drafted reply: Re: Daily bank transactions', ts: minsAgo(31) },
  { id: 'e5', source: 'gmail', type: 'email_received', actor: 'analyst_2', summary: 'Email from acme@corp.com: API onboarding request for Acme', ts: minsAgo(46) },
  { id: 'e6', source: 'excel', type: 'spreadsheet_row_updated', actor: 'analyst_1', summary: 'cash_recon.xlsx · Daily Reconciliation row 92 updated', ts: minsAgo(58) },
  { id: 'e7', source: 'gmail', type: 'email_received', actor: 'analyst_2', summary: 'Email from globex@corp.com: Onboarding — need credentials', ts: minsAgo(74) },
  { id: 'e8', source: 'excel', type: 'spreadsheet_row_updated', actor: 'analyst_1', summary: 'cash_recon.xlsx · Payment Export row 5 updated', ts: minsAgo(95) },
]

const CONNECTIONS = [
  { id: 'gmail', name: 'Gmail', kind: 'email', description: 'Inbound and outbound email activity.', status: 'connected', event_count: 128, last_event_at: minsAgo(8) },
  { id: 'excel', name: 'Excel', kind: 'spreadsheet', description: 'Workbook and cell-level changes.', status: 'connected', event_count: 86, last_event_at: minsAgo(3) },
]

const OBSERVATION_COST_WEEK = 0.38

function totals() {
  const recs = RECOMMENDATIONS
  const minutes = recs.reduce((s, r) => s + r.roi.time_saved_minutes_per_week, 0)
  const addedSkills = recs.reduce((s, r) => s + r.roi.added_ai_cost_usd_per_week, 0)
  const added = Math.round((addedSkills + OBSERVATION_COST_WEEK) * 100) / 100
  const mult = recs.reduce((s, r) => s + r.roi.throughput_multiplier, 0) / recs.length
  return {
    workflows_found: recs.length,
    workflows_proposed: recs.filter(r => !accepted.has(r.id)).length,
    workflows_accepted: recs.filter(r => accepted.has(r.id)).length,
    time_saved_minutes_per_week: minutes,
    time_saved_hours_per_week: Math.round((minutes / 60) * 10) / 10,
    fte_equivalent: Math.round((minutes / 60 / 40) * 100) / 100,
    productivity_multiplier: Math.round(mult * 10) / 10,
    added_ai_cost_usd_per_week: added,
    added_ai_cost_usd_per_year: Math.round(added * 52 * 100) / 100,
    observation_cost_usd_per_week: OBSERVATION_COST_WEEK,
  }
}

const WORKFLOWS = [
  {
    id: 'daily_financial_close',
    name: 'Daily Financial Close',
    description:
      'An AI-assisted daily close: reconcile bank activity, triage exceptions, and draft the close summary — orchestrated end to end with human sign-off.',
    composed_of: ['Daily cash reconciliation', 'Exception triage', 'Close summary reporting'],
    source_apps: ['excel', 'gmail'],
    status: 'recommended',
    priority: 'high',
    fde_recommendation:
      "Deploy this as the team's standing daily-close workflow. It removes the most repetitive analyst time, scales with transaction volume, and keeps every write behind reviewer approval.",
    impact: {
      people_involved: 3,
      runs_per_week: 15,
      team_hours_saved_per_week: 7.2,
      fte_equivalent: 0.18,
      productivity_multiplier: 5.1,
      added_ai_cost_usd_per_week: 1.59,
      added_ai_cost_usd_per_year: 82.68,
    },
  },
  {
    id: 'customer_onboarding_pipeline',
    name: 'Customer Onboarding Pipeline',
    description:
      'Capture inbound onboarding requests, extract customer and blockers, update the tracker, and draft the next-step reply — one consistent intake path.',
    composed_of: ['Onboarding intake', 'Tracker update', 'Follow-up drafting'],
    source_apps: ['gmail', 'excel'],
    status: 'recommended',
    priority: 'medium',
    fde_recommendation:
      'Stand this up to give onboarding a single source of truth and cut intake latency. Highest value once volume exceeds a few requests per week.',
    impact: {
      people_involved: 2,
      runs_per_week: 12,
      team_hours_saved_per_week: 2.8,
      fte_equivalent: 0.07,
      productivity_multiplier: 4.5,
      added_ai_cost_usd_per_week: 0.72,
      added_ai_cost_usd_per_year: 37.44,
    },
  },
]

const withStatus = (r: (typeof RECOMMENDATIONS)[number]) => ({ ...r, status: accepted.has(r.id) ? 'accepted' : 'proposed' })

export const handlers = [
  http.get('/api/connections', () => HttpResponse.json(CONNECTIONS)),
  http.get('/api/observations', () => HttpResponse.json(OBSERVATIONS)),
  http.get('/api/recommendations', () => HttpResponse.json(RECOMMENDATIONS.map(withStatus))),
  http.get('/api/report/weekly', () =>
    HttpResponse.json({
      period: 'this week',
      generated_at: minsAgo(0),
      summary:
        'This week we found 2 repeatable workflows worth automating (Daily Cash Reconciliation, Vendor Onboarding Intake). Adopting them frees ~3.8 analyst hours/week (~0.1 FTE of capacity, ~4.8x throughput on those tasks). This does not cut spend — it adds ~$1.27/week (~$66/year) of AI cost — but it converts manual hours into capacity. Every skill runs under human approval; nothing runs automatically.',
      totals: totals(),
      usage_trend: aggregateTrend(),
      recommendations: RECOMMENDATIONS.map(withStatus),
    }),
  ),
  http.get('/api/skills', () => HttpResponse.json(currentSkills())),
  http.get('/api/workflows', () => HttpResponse.json(WORKFLOWS)),
  http.post('/api/recommendations/:id/accept/stream', ({ params }) => {
    const id = String(params.id)
    accepted.add(id)
    const rec = RECOMMENDATIONS.find(r => r.id === id)
    const slug = (rec?.workflow_family || id).replace(/_/g, '-')
    return HttpResponse.json({
      status: 'installed',
      candidate_id: id,
      skill_id: rec?.workflow_family || id,
      bundle_dir: `workspace/skills/${slug}`,
      local_path: `~/.claude/skills/${slug}`,
      installed_files: ['SKILL.md', 'skill.json', 'skill.yaml', 'policy.yaml'],
      skill_md_preview: `# ${rec?.title ?? 'Generated skill'}\n\nTrigger: ${rec?.trigger ?? ''}\n\nThis skill runs under human approval. It reads the matched input, prepares the change, waits for a reviewer, then writes the local output and records a run.`,
      planner: 'anthropic',
    })
  }),
  http.get('/api/memory/status', () =>
    HttpResponse.json({
      backend: 'hydradb',
      tenant_id: 'default-tenant',
      sub_tenant_id: 'controller',
      hydra_configured: true,
      error: null,
    }),
  ),
  http.post('/api/skills/:id/feedback', async ({ request, params }) => {
    const body = (await request.json().catch(() => ({}))) as { rating?: string; note?: string }
    return HttpResponse.json({
      status: 'ok',
      skill_id: String(params.id),
      rating: body.rating ?? 'up',
      note: body.note ?? '',
      backend: 'hydradb',
      hydra_status: 'queued',
    })
  }),
  http.post('/api/skills/:id/run', ({ params }) =>
    HttpResponse.json({
      status: 'executed',
      skill_id: String(params.id),
      match_id: 'match_demo',
      memory: {
        backend: 'hydradb',
        recalled: ['tx-1004 (Amount variance) is a known recurring timing difference — treat as Matched.'],
        auto_resolved: [{ transaction_id: 'tx-1004', applied: 'tx-1004 is a known recurring timing difference — treat as Matched.' }],
        exceptions_before: 1,
        exceptions_after: 0,
      },
      artifacts: {
        workbook: 'workspace/workbooks/generated/cash_recon_2026_06_15_reconciled.xlsx',
        workbook_url: '/api/files/workspace/workbooks/generated/cash_recon_2026_06_15_reconciled.xlsx',
        draft: 'workspace/mail/drafts/cash_recon_2026_06_15_reply.eml',
        draft_url: '/api/files/workspace/mail/drafts/cash_recon_2026_06_15_reply.eml',
        matched_count: 4,
        exception_count: 0,
      },
    }),
  ),
  http.get('/api/memory/trace', () =>
    HttpResponse.json([
      { ts: '2026-06-21T19:11:26', op: 'apply', backend: 'hydradb', auto_resolved: 1, exceptions_before: 1, exceptions_after: 0 },
      {
        ts: '2026-06-21T19:11:26',
        op: 'recall',
        backend: 'hydradb',
        query: 'reconciliation corrections and standing rules to apply when running the skill',
        hits: 1,
        from_hydra: 1,
        top: [{ text: 'tx-1004 is a known recurring timing difference — treat as Matched.', score: 1.46, source: 'hydradb' }],
      },
      { ts: '2026-06-21T19:11:25', op: 'write', backend: 'hydradb', rating: 'up', stored: 'Reviewer feedback: tx-1004 is a known recurring timing difference — treat as Matched.', hydra_status: 'queued' },
    ]),
  ),
]
