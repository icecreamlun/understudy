import client from './client'
import type { ReviewedWorkflow, SkillMatch, SkillOpsMetrics, SkillSummary } from '../types/skill'

export async function listMatches(): Promise<SkillMatch[]> {
  const { data } = await client.get<SkillMatch[]>('/api/skills/matches')
  return data
}

export interface RunInputs {
  incomingItem?: string
  sourceFile?: string
  targetFile?: string
}

export async function approveMatch(matchId: string, reviewedWorkflow?: ReviewedWorkflow | null): Promise<void> {
  await client.post(`/api/skills/matches/${matchId}/approve`, reviewedWorkflow ? { reviewed_workflow: reviewedWorkflow } : {})
}

export async function rejectMatch(matchId: string): Promise<void> {
  await client.post(`/api/skills/matches/${matchId}/reject`)
}

export async function previewMatch(matchId: string, runInputs?: RunInputs): Promise<void> {
  await client.post(`/api/skills/matches/${matchId}/preview`, runInputs ? { run_inputs: runInputs } : {})
}

export async function getSkillOps(skillId: string): Promise<SkillOpsMetrics> {
  const { data } = await client.get<SkillOpsMetrics>(`/api/skillops/skills/${skillId}`)
  return data
}

export async function listSkills(): Promise<SkillSummary[]> {
  const { data } = await client.get<SkillSummary[]>('/api/skillops/summary')
  return data
}
