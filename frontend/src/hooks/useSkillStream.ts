import { useEffect, useReducer, useRef } from 'react'
import type { ExecutionEvent } from '../types/skill'
import { apiUrl } from '../api/client'

interface UseSkillStreamResult {
  events: ExecutionEvent[]
  activeStepIndex: number
  status: 'idle' | 'connecting' | 'streaming' | 'paused' | 'done' | 'error'
  error?: string
}

type SkillStreamState = UseSkillStreamResult

type SkillStreamAction =
  | { type: 'connect' }
  | { type: 'open' }
  | { type: 'event'; event: ExecutionEvent }
  | { type: 'error'; error: string }

const initialState: SkillStreamState = {
  events: [],
  activeStepIndex: -1,
  status: 'idle',
}

function skillStreamReducer(state: SkillStreamState, action: SkillStreamAction): SkillStreamState {
  switch (action.type) {
    case 'connect':
      return { events: [], activeStepIndex: -1, status: 'connecting' }
    case 'open':
      return { ...state, status: 'streaming', error: undefined }
    case 'event': {
      const events = [...state.events, action.event]
      if (action.event.type === 'step_started') {
        return { ...state, events, activeStepIndex: action.event.step_index, status: 'streaming' }
      }
      if (action.event.type === 'approval_required') {
        return { ...state, events, activeStepIndex: action.event.step_index, status: 'paused' }
      }
      if (action.event.type === 'execution_complete') {
        return { ...state, events, status: 'done' }
      }
      return { ...state, events }
    }
    case 'error':
      if (state.status === 'done') return state
      return { ...state, status: 'error', error: action.error }
  }
}

export function useSkillStream(matchId: string | null, resetKey = 0): UseSkillStreamResult {
  const [state, dispatch] = useReducer(skillStreamReducer, initialState)
  const esRef = useRef<EventSource | null>(null)

  useEffect(() => {
    if (!matchId) return

    dispatch({ type: 'connect' })

    const es = new EventSource(apiUrl(`/api/skills/matches/${matchId}/stream`))
    esRef.current = es

    es.onopen = () => dispatch({ type: 'open' })

    es.onmessage = (e) => {
      try {
        const event: ExecutionEvent = JSON.parse(e.data)
        dispatch({ type: 'event', event })
        if (event.type === 'execution_complete') {
          es.close()
        }
      } catch {
        // ignore malformed events
      }
    }

    es.onerror = () => {
      dispatch({ type: 'error', error: 'Connection lost' })
      es.close()
    }

    return () => {
      es.close()
      esRef.current = null
    }
  }, [matchId, resetKey])

  return state
}
