import { useEffect, useState } from 'react'

/**
 * Skill-generation progress bar. Snaps to each real stage milestone as SSE
 * events arrive, and eases smoothly toward the next one in between so the long
 * "calling Codex" step still looks alive instead of frozen.
 */
export function GenProgress({ pct, label }: { pct: number; label: string }) {
  const [display, setDisplay] = useState(0)
  useEffect(() => {
    const ceiling = pct >= 100 ? 100 : Math.min(pct + 18, 96)
    const timer = setInterval(() => {
      setDisplay(d => (d >= ceiling - 0.5 ? ceiling : d + (ceiling - d) * 0.08))
    }, 120)
    return () => clearInterval(timer)
  }, [pct])
  const done = pct >= 100
  return (
    <div
      className="gen-progress"
      role="progressbar"
      aria-valuenow={Math.round(display)}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div className="gen-progress-head">
        <span className="gen-progress-label">{label}</span>
        <span className="gen-progress-pct">{Math.round(display)}%</span>
      </div>
      <div className="gen-bar">
        <div className={`gen-bar-fill ${done ? 'done' : 'working'}`} style={{ width: `${display}%` }} />
      </div>
    </div>
  )
}
