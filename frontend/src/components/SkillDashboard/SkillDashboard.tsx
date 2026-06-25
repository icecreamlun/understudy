import { useMemo, useState } from 'react'
import type { RunInputs } from '../../api/skillops'
import { useSkillList } from '../../hooks/useSkillOps'

interface SkillDashboardProps {
  activeSkillId?: string
  onRunSkill: (skillId: string, inputs: RunInputs) => Promise<void>
  runError?: string | null
}

interface WorkflowInventoryItem {
  skillId: string
  department: string
  workflowName: string
  description: string
  repeatsToday: number
  repeatsYesterday: number
  historicalRepeats: number
}

const workflowInventory: WorkflowInventoryItem[] = [
  {
    skillId: 'daily_cash_reconciliation',
    department: 'Finance',
    workflowName: 'Bank transaction email workflow',
    description: 'Bank transaction emails are checked against the finance workbook and turned into an updated spreadsheet.',
    repeatsToday: 4,
    repeatsYesterday: 5,
    historicalRepeats: 42,
  },
  {
    skillId: 'meeting_report_followup',
    department: 'Business Operations',
    workflowName: 'Meeting report follow-up workflow',
    description: 'Meeting notes are converted into owner follow-ups, target dates, and a weekly report for managers.',
    repeatsToday: 3,
    repeatsYesterday: 4,
    historicalRepeats: 31,
  },
  {
    skillId: 'invoice_aging_followup',
    department: 'Accounts Receivable',
    workflowName: 'Invoice aging follow-up workflow',
    description: 'Aging invoice spreadsheets are reviewed and follow-up drafts are prepared for overdue accounts.',
    repeatsToday: 5,
    repeatsYesterday: 6,
    historicalRepeats: 58,
  },
  {
    skillId: 'variance_explanation_draft',
    department: 'FP&A',
    workflowName: 'Variance explanation draft workflow',
    description: 'Monthly variance rows are grouped and converted into manager-ready explanation drafts.',
    repeatsToday: 2,
    repeatsYesterday: 3,
    historicalRepeats: 24,
  },
]

function displayName(skillId: string, skillName: string): string {
  if (skillId === 'daily_cash_reconciliation') return 'Bank transaction email workflow'
  return skillName.replace(/\s+Skill$/i, '').replace(/_/g, ' ')
}

export function SkillDashboard({ activeSkillId, onRunSkill, runError }: SkillDashboardProps) {
  const { data: skills = [], isLoading } = useSkillList()
  const [selectedSkillId, setSelectedSkillId] = useState<string | null>(null)
  const [isStarting, setIsStarting] = useState(false)
  const [inputs, setInputs] = useState<RunInputs>({
    incomingItem: 'Daily bank transactions - June 15',
    sourceFile: 'workspace/attachments/bank_transactions_2026_06_15.xlsx',
    targetFile: 'workspace/workbooks/skillforge_finance_demo_cash_recon.xlsx',
  })

  const generatedSkillIds = useMemo(() => new Set(skills.map(skill => skill.skill_id)), [skills])
  const departmentReport = useMemo(() => {
    const rows = new Map<string, { department: string; workflowCount: number; repeatsToday: number; historicalRepeats: number; workflows: string[] }>()
    for (const item of workflowInventory) {
      const current = rows.get(item.department) ?? {
        department: item.department,
        workflowCount: 0,
        repeatsToday: 0,
        historicalRepeats: 0,
        workflows: [],
      }
      current.workflowCount += 1
      current.repeatsToday += item.repeatsToday
      current.historicalRepeats += item.historicalRepeats
      current.workflows.push(item.workflowName)
      rows.set(item.department, current)
    }
    return Array.from(rows.values())
  }, [])

  const selected = useMemo(() => {
    const id = selectedSkillId ?? activeSkillId ?? workflowInventory[0]?.skillId
    return workflowInventory.find(item => item.skillId === id) ?? workflowInventory[0] ?? null
  }, [activeSkillId, selectedSkillId])

  async function runSelected() {
    if (!selected) return
    setIsStarting(true)
    try {
      await onRunSkill(selected.skillId, inputs)
    } finally {
      setIsStarting(false)
    }
  }

  return (
    <section className="skill-dashboard" id="workflow-dashboard">
      <div className="dashboard-heading">
        <div>
          <p className="eyebrow">Generated FDE workflows</p>
          <h2>Workflow dashboard</h2>
        </div>
        <span>{workflowInventory.length} repeated workflows tracked</span>
      </div>

      <div className="dashboard-grid">
        <div className="dashboard-list">
          {isLoading && <div className="empty-state compact">Loading generated workflows.</div>}
          {workflowInventory.map(workflow => {
            const active = selected?.skillId === workflow.skillId
            const generated = generatedSkillIds.has(workflow.skillId)
            return (
              <button
                className={`dashboard-skill-row ${active ? 'active' : ''}`}
                key={workflow.skillId}
                type="button"
                onClick={() => setSelectedSkillId(workflow.skillId)}
              >
                <span>{workflow.workflowName}</span>
                <small>{workflow.department}</small>
                <strong>{generated ? 'Generated workflow' : 'Candidate'}</strong>
                <em>{workflow.repeatsToday} today / {workflow.historicalRepeats} history</em>
              </button>
            )
          })}
        </div>

        <div className="dashboard-run-panel">
          <div>
            <p className="eyebrow">Run selected workflow</p>
            <h3>{selected ? displayName(selected.skillId, selected.workflowName) : 'No workflow selected'}</h3>
            {selected && <p className="dashboard-description">{selected.description}</p>}
          </div>

          <div className="run-input-grid">
            <label>
              <span>Incoming item</span>
              <input
                value={inputs.incomingItem ?? ''}
                onChange={event => setInputs(current => ({ ...current, incomingItem: event.target.value }))}
              />
            </label>
            <label>
              <span>Source file</span>
              <input
                value={inputs.sourceFile ?? ''}
                onChange={event => setInputs(current => ({ ...current, sourceFile: event.target.value }))}
              />
            </label>
            <label>
              <span>Target file</span>
              <input
                value={inputs.targetFile ?? ''}
                onChange={event => setInputs(current => ({ ...current, targetFile: event.target.value }))}
              />
            </label>
          </div>

          {runError && <div className="error-box compact">{runError}</div>}

          <button className="primary-button dashboard-run-button" type="button" onClick={runSelected} disabled={!selected || isStarting}>
            {isStarting ? 'Starting workflow' : 'Run workflow once for selected target'}
          </button>
        </div>
      </div>

      <section className="bi-report-panel">
        <div>
          <p className="eyebrow">BI report</p>
          <h3>Department workflow distribution</h3>
        </div>
        <div className="bi-report-grid">
          {departmentReport.map(row => (
            <div className="bi-report-row" key={row.department}>
              <div>
                <strong>{row.department}</strong>
                <span>{row.workflows.join(', ')}</span>
              </div>
              <em>{row.workflowCount} workflows</em>
              <em>{row.repeatsToday} repeats today</em>
              <em>{row.historicalRepeats} historical repeats</em>
            </div>
          ))}
        </div>
      </section>
    </section>
  )
}
