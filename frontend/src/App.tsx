import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getRecommendations, getSkills, getWorkflows } from './api/observatory'
import { OverviewView } from './views/OverviewView'
import { RecommendationsView } from './views/RecommendationsView'
import { SkillsView } from './views/SkillsView'
import { WorkflowsView } from './views/WorkflowsView'
import { ActivityView } from './views/ActivityView'
import { ConnectionsView } from './views/ConnectionsView'
import { MemoryView } from './views/MemoryView'
import { NavIcon } from './components/NavIcon'

type ViewId = 'connections' | 'activity' | 'recommendations' | 'skills' | 'memory' | 'workflows' | 'overview'

// Ordered top→bottom to match the journey: connect → observe → skills → memory → workflows → report.
const NAV: { id: ViewId; label: string }[] = [
  { id: 'connections', label: 'Connections' },
  { id: 'activity', label: 'Activity' },
  { id: 'recommendations', label: 'Recommendations' },
  { id: 'skills', label: 'Skills' },
  { id: 'memory', label: 'Memory' },
  { id: 'workflows', label: 'Workflows' },
  { id: 'overview', label: 'Overview' },
]

const TITLES: Record<ViewId, string> = {
  connections: 'Connected sources',
  activity: 'Live activity',
  recommendations: 'Tasks to turn into skills',
  skills: 'Your skills',
  memory: 'Agent memory (HydraDB)',
  workflows: 'Org workflows to deploy',
  overview: 'Weekly FDE report',
}

export default function App() {
  const [view, setView] = useState<ViewId>('connections')

  // Lightweight queries for the sidebar count badges (shared cache with views).
  const recommendations = useQuery({ queryKey: ['recommendations'], queryFn: getRecommendations })
  const skills = useQuery({ queryKey: ['skills'], queryFn: getSkills })
  const workflows = useQuery({ queryKey: ['workflows'], queryFn: getWorkflows })

  const badges: Partial<Record<ViewId, number>> = {
    recommendations: recommendations.data?.filter(r => r.status !== 'accepted').length,
    skills: skills.data?.length,
    workflows: workflows.data?.length,
  }

  return (
    <div className="fde-layout">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true" />
          <span className="brand-name">Understudy</span>
        </div>
        <nav className="nav">
          {NAV.map(item => {
            const badge = badges[item.id]
            return (
              <button
                key={item.id}
                type="button"
                className={`nav-item ${view === item.id ? 'active' : ''}`}
                onClick={() => setView(item.id)}
              >
                <NavIcon name={item.id} />
                <span className="nav-label">{item.label}</span>
                {badge ? <span className="nav-badge">{badge}</span> : null}
              </button>
            )
          })}
        </nav>
        <div className="sidebar-foot">
          <span className="live-dot" />
          <span>Listening</span>
        </div>
      </aside>

      <main className="content">
        <header className="content-header">
          <h2 className="content-title">{TITLES[view]}</h2>
        </header>
        {view === 'connections' ? <ConnectionsView /> : null}
        {view === 'activity' ? <ActivityView /> : null}
        {view === 'recommendations' ? <RecommendationsView /> : null}
        {view === 'skills' ? <SkillsView /> : null}
        {view === 'memory' ? <MemoryView /> : null}
        {view === 'workflows' ? <WorkflowsView /> : null}
        {view === 'overview' ? <OverviewView /> : null}
      </main>
    </div>
  )
}
