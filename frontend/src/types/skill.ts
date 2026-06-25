export interface SkillStep {
  id: string
  type: string
  label: string
  sublabel?: string
}

export interface SkillMatch {
  match_id: string
  skill_id: string
  skill_version: number
  trigger_event_id: string
  matched_at: string
  match_confidence: number
  match_reasons: string[]
  status:
    | 'awaiting_preview'
    | 'previewing'
    | 'awaiting_approval'
    | 'approved'
    | 'rejected'
    | 'executing'
    | 'executed'
    | 'done'
    | 'failed'
  skill_name: string
}

export type ExecutionEventType =
  | 'step_started'
  | 'step_completed'
  | 'pattern_detected'
  | 'skill_generated'
  | 'approval_required'
  | 'execution_complete'
  | 'validation_result'

export interface StepStartedEvent {
  type: 'step_started'
  step_id: string
  step_index: number
  label: string
  sublabel?: string
  timestamp: string
}

export interface StepCompletedEvent {
  type: 'step_completed'
  step_id: string
  step_index: number
  label: string
  summary: string
  elapsed_ms: number
  timestamp: string
  raw?: Record<string, unknown>
}

export interface PatternDetectedEvent {
  type: 'pattern_detected'
  timestamp: string
  title: string
  summary: string
  pattern_definition?: string
  explanation?: string
  confidence: number
  episode_count: number
  sequence: string[]
  signals: string[]
  issues: string[]
  evidence: {
    episodes: string[]
    common_fields: string[]
    target?: string
  }
  next_trigger?: {
    event_id?: string
    target_rows?: string
    unprocessed_action_columns?: string[]
  }
}

export interface SkillWorkflowStep {
  id?: string
  order: number
  title: string
  summary: string
  type?: string
}

export interface SkillTriggerCondition {
  label?: string
  field?: string
  operator?: string
  value?: string | number | boolean | Record<string, unknown>
  type?: string
}

export interface SkillGeneratedEvent {
  type: 'skill_generated'
  timestamp: string
  title: string
  summary: string
  issues: string[]
  triggers: SkillTriggerCondition[]
  steps: SkillWorkflowStep[]
  expected_outcome: {
    summary: string
    files_created: string[]
    files_modified: string[]
    safety_checks: string[]
  }
}

export interface ReviewedWorkflow {
  title?: string
  description?: string
  triggers: SkillTriggerCondition[]
  steps: SkillWorkflowStep[]
  expected_outcome: SkillGeneratedEvent['expected_outcome']
}

export interface ApprovalRequiredEvent {
  type: 'approval_required'
  step_index: number
  timestamp: string
  proposed_changes: {
    description: string
    files_to_create: string[]
    files_to_modify: string[]
    stats: Record<string, string | number>
    exceptions?: Array<Record<string, string | number>>
  }
  guardrails: string[]
  reply_draft?: string
}

export interface ExecutionCompleteEvent {
  type: 'execution_complete'
  decision: 'approved' | 'rejected'
  timestamp: string
  actor?: string
}

export interface ValidationResultEvent {
  type: 'validation_result'
  timestamp: string
  status: 'passed' | 'failed'
  checks: Array<{ name: string; status: 'passed' | 'failed'; detail?: string }>
}

export type ExecutionEvent =
  | StepStartedEvent
  | StepCompletedEvent
  | PatternDetectedEvent
  | SkillGeneratedEvent
  | ApprovalRequiredEvent
  | ExecutionCompleteEvent
  | ValidationResultEvent

export interface SkillOpsMetrics {
  skill_id: string
  skill_name: string
  users: number
  matches: number
  runs: number
  run_rate: number
  success_rate: number
  reject_rate: number
  last_used: string
  status: 'active' | 'beta' | 'team_standard' | 'needs_refinement' | 'disabled'
}

export interface SkillSummary {
  skill_id: string
  skill_name: string
  status: SkillOpsMetrics['status']
}
