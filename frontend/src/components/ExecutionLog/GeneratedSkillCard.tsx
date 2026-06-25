import { useCallback, useEffect, useState } from 'react'
import type { ReviewedWorkflow, SkillGeneratedEvent, SkillTriggerCondition, SkillWorkflowStep } from '../../types/skill'

interface GeneratedSkillCardProps {
  event: SkillGeneratedEvent
  onChange?: (workflow: ReviewedWorkflow) => void
  onGenerateSkill?: (workflow: ReviewedWorkflow) => void
  onRunGeneratedSkill?: () => void
  skillCreated?: boolean
}

type EditableTrigger = SkillTriggerCondition & { localId: string }
type EditableStep = SkillWorkflowStep & { localId: string }

const triggerTypes = [
  { value: 'subject_pattern', label: 'Email subject' },
  { value: 'has_attachment_matching', label: 'Attachment name' },
  { value: 'sender_pattern', label: 'Sender' },
  { value: 'file_exists', label: 'Required file' },
  { value: 'custom', label: 'Custom input' },
]

const triggerOperators = ['contains', 'starts with', 'matches', 'exists', 'equals']

function uid(prefix: string): string {
  return `${prefix}_${Date.now()}_${Math.random().toString(16).slice(2)}`
}

function valueText(condition: SkillTriggerCondition): string {
  if (condition.value === undefined || condition.value === '') return ''
  if (typeof condition.value === 'object') return JSON.stringify(condition.value)
  return String(condition.value)
}

function normalizeTriggers(event: SkillGeneratedEvent): EditableTrigger[] {
  if (event.triggers.length === 0) {
    return [{ localId: uid('trigger'), label: 'When a matching email arrives', type: 'subject_pattern', operator: 'contains', value: '' }]
  }
  return event.triggers.map((condition, index) => ({
    ...condition,
    localId: uid(`trigger_${index}`),
    label: workflowText(condition.label ?? condition.field ?? `Trigger ${index + 1}`),
    operator: condition.operator ?? 'matches',
    value: workflowText(valueText(condition)),
  }))
}

function normalizeSteps(event: SkillGeneratedEvent): EditableStep[] {
  return event.steps
    .map((step, index) => ({
      ...step,
      localId: uid(`step_${index}`),
      order: index + 1,
      title: workflowText(step.title),
      summary: workflowText(step.summary),
    }))
    .sort((a, b) => a.order - b.order)
}

function stripTrigger(trigger: EditableTrigger): SkillTriggerCondition {
  return {
    label: trigger.label,
    field: trigger.field,
    operator: trigger.operator,
    value: trigger.value,
    type: trigger.type,
  }
}

function stripStep(step: EditableStep): SkillWorkflowStep {
  return {
    id: step.id,
    order: step.order,
    title: step.title,
    summary: step.summary,
    type: step.type,
  }
}

function renumber(steps: EditableStep[]): EditableStep[] {
  return steps.map((step, index) => ({ ...step, order: index + 1 }))
}

function fileName(path: string): string {
  return path.split(/[\\/]/).pop() ?? path
}

function workflowText(text: string): string {
  return text
    .replace(/\bSkill Run ID\b/g, 'Workflow Run ID')
    .replace(/\bskill_id\b/g, 'workflow_id')
    .replace(/\{skill_id\}/g, '{workflow_id}')
    .replace(/\bGenerated skill\b/g, 'Generated workflow')
    .replace(/\bgenerated skill\b/g, 'generated workflow')
    .replace(/\bSkill\b/g, 'Workflow')
    .replace(/\bskill\b/g, 'workflow')
}

export function GeneratedSkillCard({ event, onChange, onGenerateSkill, onRunGeneratedSkill, skillCreated }: GeneratedSkillCardProps) {
  const [title, setTitle] = useState(workflowText(event.title || 'Bank transaction email workflow'))
  const [description, setDescription] = useState(workflowText(event.summary))
  const [triggers, setTriggers] = useState<EditableTrigger[]>(() => normalizeTriggers(event))
  const [steps, setSteps] = useState<EditableStep[]>(() => normalizeSteps(event))
  const [outcome, setOutcome] = useState<SkillGeneratedEvent['expected_outcome']>(() => ({
    ...event.expected_outcome,
    summary: workflowText(event.expected_outcome.summary || ''),
    files_created: event.expected_outcome.files_created.map(workflowText),
    files_modified: event.expected_outcome.files_modified.map(workflowText),
    safety_checks: event.expected_outcome.safety_checks.map(workflowText),
  }))
  const [selectedStepIndex, setSelectedStepIndex] = useState(0)
  const [accepted, setAccepted] = useState(false)
  const [feedbackOpen, setFeedbackOpen] = useState(false)
  const [feedbackText, setFeedbackText] = useState('')
  const [feedbackSent, setFeedbackSent] = useState(false)
  const selectedStep = steps[Math.min(selectedStepIndex, Math.max(0, steps.length - 1))]

  const reviewedWorkflow = useCallback((): ReviewedWorkflow => {
    return {
      title,
      description,
      triggers: triggers.map(stripTrigger),
      steps: steps.map(stripStep),
      expected_outcome: outcome,
    }
  }, [title, description, triggers, steps, outcome])

  useEffect(() => {
    onChange?.(reviewedWorkflow())
  }, [onChange, reviewedWorkflow])

  function updateTrigger(index: number, patch: Partial<EditableTrigger>) {
    setTriggers(current => current.map((trigger, itemIndex) => (itemIndex === index ? { ...trigger, ...patch } : trigger)))
  }

  function addTrigger() {
    setTriggers(current => [
      ...current,
      {
        localId: uid('trigger'),
        label: 'New trigger',
        type: 'custom',
        operator: 'contains',
        value: '',
      },
    ])
  }

  function removeTrigger(index: number) {
    setTriggers(current => current.filter((_, itemIndex) => itemIndex !== index))
  }

  function updateStep(index: number, patch: Partial<EditableStep>) {
    setSteps(current => current.map((step, itemIndex) => (itemIndex === index ? { ...step, ...patch } : step)))
  }

  function moveStep(index: number, direction: -1 | 1) {
    setSteps(current => {
      const nextIndex = index + direction
      if (nextIndex < 0 || nextIndex >= current.length) return current
      const next = [...current]
      const [item] = next.splice(index, 1)
      next.splice(nextIndex, 0, item)
      return renumber(next)
    })
  }

  function addStep() {
    const newIndex = steps.length
    setSteps(current =>
      renumber([
        ...current,
        {
          localId: uid('step'),
          order: current.length + 1,
          title: 'New workflow step',
          summary: '',
          type: 'custom',
        },
      ]),
    )
    setSelectedStepIndex(newIndex)
  }

  function removeStep(index: number) {
    setSteps(current => {
      const next = renumber(current.filter((_, itemIndex) => itemIndex !== index))
      setSelectedStepIndex(Math.max(0, Math.min(index, next.length - 1)))
      return next
    })
  }

  function clearStep(index: number) {
    updateStep(index, { title: '', summary: '' })
  }

  function updateCreatedFile(index: number, value: string) {
    setOutcome(current => ({
      ...current,
      files_created: current.files_created.map((path, itemIndex) => (itemIndex === index ? value : path)),
    }))
  }

  function addCreatedFile() {
    setOutcome(current => ({ ...current, files_created: [...current.files_created, 'workspace/workbooks/generated/output.xlsx'] }))
  }

  function removeCreatedFile(index: number) {
    setOutcome(current => ({ ...current, files_created: current.files_created.filter((_, itemIndex) => itemIndex !== index) }))
  }

  return (
    <article className="generated-skill-card">
      <div className="insight-header">
        <div>
          <p className="eyebrow">FDE workflow drafted</p>
          <h3>Generated FDE workflow</h3>
        </div>
        <span className="generated-badge">{skillCreated ? 'Workflow created' : 'Review before creating'}</span>
      </div>

      <section className="skill-content-section primary-skill-section">
        <div className="section-title-row">
          <h4>Workflow review</h4>
          <div className="review-action-row">
            <button className="primary-button compact-primary" type="button" onClick={() => onGenerateSkill?.(reviewedWorkflow())}>
              {skillCreated ? 'Workflow generated' : 'Generate workflow'}
            </button>
            {skillCreated && (
              <button className="secondary-button compact-primary" type="button" onClick={onRunGeneratedSkill}>
                Run workflow once for current target
              </button>
            )}
          </div>
        </div>
        <div className="skill-review-grid">
          <label>
            <span>Title</span>
            <input value={title} onChange={event => setTitle(event.target.value)} />
          </label>
          <label>
            <span>Description</span>
            <textarea value={description} onChange={event => setDescription(event.target.value)} rows={3} />
          </label>
        </div>

        {skillCreated && (
          <div className="skill-decision-panel">
            <div>
              <h4>Keep this workflow?</h4>
              <p>
                Accept it to keep this workflow available for future matching emails, or leave feedback so the generator can revise it.
              </p>
            </div>
            <div className="review-action-row">
              <button className="primary-button compact-primary" type="button" onClick={() => {
                setAccepted(true)
                setFeedbackOpen(false)
                setFeedbackSent(false)
              }}>
                Accept and keep workflow
              </button>
              <button className="secondary-button compact-primary" type="button" onClick={() => {
                setAccepted(false)
                setFeedbackOpen(true)
              }}>
                Leave feedback
              </button>
            </div>

            {accepted && <div className="decision-note accepted">Accepted. This workflow is now available in the workflow dashboard.</div>}

            {feedbackOpen && (
              <div className="feedback-box">
                <label>
                  <span>Feedback for revision</span>
                  <textarea
                    value={feedbackText}
                    onChange={event => setFeedbackText(event.target.value)}
                    placeholder="Tell the generator what should change before this workflow is kept."
                    rows={4}
                  />
                </label>
                <button className="secondary-button compact-primary" type="button" onClick={() => setFeedbackSent(true)}>
                  Send feedback
                </button>
                {feedbackSent && <div className="decision-note">Feedback saved for the next revision.</div>}
              </div>
            )}
          </div>
        )}
      </section>

      <section className="skill-content-section primary-skill-section">
        <div className="section-title-row">
          <h4>Triggers</h4>
          <button className="text-button" type="button" onClick={addTrigger}>
            Add trigger
          </button>
        </div>
        <div className="editable-trigger-list">
          {triggers.map((condition, index) => (
            <div className="editable-trigger-row" key={condition.localId}>
              <label>
                <span>Trigger name</span>
                <textarea
                  value={condition.label ?? ''}
                  onChange={event => updateTrigger(index, { label: event.target.value })}
                  placeholder={`Trigger ${index + 1}`}
                  rows={2}
                />
              </label>
              <label>
                <span>Type</span>
                <select value={condition.type ?? 'custom'} onChange={event => updateTrigger(index, { type: event.target.value })}>
                  {triggerTypes.map(option => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>Rule</span>
                <select value={condition.operator ?? 'matches'} onChange={event => updateTrigger(index, { operator: event.target.value })}>
                  {triggerOperators.map(option => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              </label>
              <label className="wide-field">
                <span>Value</span>
                <textarea value={valueText(condition)} onChange={event => updateTrigger(index, { value: event.target.value })} rows={2} />
              </label>
              <button className="secondary-button compact danger" type="button" onClick={() => removeTrigger(index)}>
                Remove
              </button>
              <div className="trigger-full-rule">
                <span>Full trigger rule</span>
                <strong>
                  {workflowText((condition.label ?? `Trigger ${index + 1}`).trim())} {condition.operator ?? 'matches'} {workflowText(valueText(condition) || 'any matching value')}
                </strong>
              </div>
            </div>
          ))}
        </div>
      </section>

      {event.issues.length > 0 && (
        <section className="skill-content-section safety-section">
          <h4>Issues addressed</h4>
          <div className="issue-list">
            {event.issues.map(issue => (
              <span key={issue}>{workflowText(issue)}</span>
            ))}
          </div>
        </section>
      )}

      <section className="skill-steps-section">
        <div className="sticky-workflow-graph">
          <div className="section-title-row">
            <h4>Workflow graph</h4>
            <button className="text-button" type="button" onClick={addStep}>
              Add step
            </button>
          </div>
          <div className="workflow-graph-scroll" aria-label="Generated workflow steps">
            <div className="workflow-graph">
            {steps.map((step, index) => (
              <button
                className={`workflow-graph-node ${index === selectedStepIndex ? 'selected' : ''}`}
                key={step.localId}
                type="button"
                onClick={() => setSelectedStepIndex(index)}
              >
                <span>{index + 1}</span>
                <strong>{step.title || `Step ${index + 1}`}</strong>
              </button>
            ))}
            </div>
          </div>
        </div>

        {selectedStep && (
          <div className="selected-step-editor">
            <div className="selected-step-heading">
              <span className="step-number">{selectedStepIndex + 1}</span>
              <strong>Edit selected step</strong>
            </div>
            <div className="editable-step-fields">
              <input
                value={selectedStep.title}
                onChange={event => updateStep(selectedStepIndex, { title: event.target.value })}
                placeholder={`Step ${selectedStepIndex + 1}`}
              />
              <textarea
                value={selectedStep.summary}
                onChange={event => updateStep(selectedStepIndex, { summary: event.target.value })}
                placeholder="Describe what this step should do"
                rows={3}
              />
            </div>
            <div className="step-edit-actions horizontal-actions">
              <button className="secondary-button compact" type="button" onClick={() => moveStep(selectedStepIndex, -1)} disabled={selectedStepIndex === 0}>
                Move left
              </button>
              <button className="secondary-button compact" type="button" onClick={() => moveStep(selectedStepIndex, 1)} disabled={selectedStepIndex === steps.length - 1}>
                Move right
              </button>
              <button className="secondary-button compact" type="button" onClick={() => clearStep(selectedStepIndex)}>
                Clear content
              </button>
              <button className="secondary-button compact danger" type="button" onClick={() => removeStep(selectedStepIndex)}>
                Remove step
              </button>
            </div>
          </div>
        )}
      </section>

      <section className="skill-content-section outcome-section">
        <div className="section-title-row">
          <h4>Final expected outcome</h4>
          <button className="text-button" type="button" onClick={addCreatedFile}>
            Add output file
          </button>
        </div>
        <textarea
          className="outcome-editor"
          value={outcome.summary || ''}
          onChange={event => setOutcome(current => ({ ...current, summary: event.target.value }))}
          rows={3}
        />
        <div className="created-file-editor-list">
          {outcome.files_created.map((path, index) => (
            <div className="created-file-editor" key={`${path}-${index}`}>
                  <span>{workflowText(fileName(path) || `Output ${index + 1}`)}</span>
              <input value={path} onChange={event => updateCreatedFile(index, event.target.value)} />
              <button className="secondary-button compact danger" type="button" onClick={() => removeCreatedFile(index)}>
                Remove
              </button>
            </div>
          ))}
        </div>
      </section>
    </article>
  )
}
