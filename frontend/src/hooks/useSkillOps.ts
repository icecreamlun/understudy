import { useQuery } from '@tanstack/react-query'
import { getSkillOps, listSkills } from '../api/skillops'
import type { SkillOpsMetrics, SkillSummary } from '../types/skill'

export function useSkillOps(skillId: string) {
  return useQuery<SkillOpsMetrics>({
    queryKey: ['skillops', skillId],
    queryFn: () => getSkillOps(skillId),
    refetchInterval: 10_000,
  })
}

export function useSkillList() {
  return useQuery<SkillSummary[]>({
    queryKey: ['skills'],
    queryFn: listSkills,
  })
}
