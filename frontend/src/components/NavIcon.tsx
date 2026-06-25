import type { ReactNode } from 'react'

// Minimal monochrome line icons (stroke = currentColor). Deliberately plain.
const ICONS: Record<string, ReactNode> = {
  connections: (
    <>
      <path d="M9 13a4.5 4.5 0 0 0 6.5 0l2.5-2.5a4.5 4.5 0 0 0-6.5-6.5L10 5.5" />
      <path d="M15 11a4.5 4.5 0 0 0-6.5 0L6 13.5a4.5 4.5 0 0 0 6.5 6.5L14 18.5" />
    </>
  ),
  activity: <path d="M3 12h3.5l2.5 7 4-14 2.5 7H21" />,
  recommendations: (
    <>
      <path d="M9.5 18h5" />
      <path d="M10.5 21h3" />
      <path d="M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.3 1 2.1h5c0-.8.4-1.6 1-2.1A6 6 0 0 0 12 3z" />
    </>
  ),
  skills: (
    <>
      <rect x="3.5" y="3.5" width="7" height="7" rx="1.2" />
      <rect x="13.5" y="3.5" width="7" height="7" rx="1.2" />
      <rect x="13.5" y="13.5" width="7" height="7" rx="1.2" />
      <rect x="3.5" y="13.5" width="7" height="7" rx="1.2" />
    </>
  ),
  workflows: (
    <>
      <circle cx="18" cy="5.5" r="2.5" />
      <circle cx="6" cy="12" r="2.5" />
      <circle cx="18" cy="18.5" r="2.5" />
      <path d="M8.3 13.3l7.4 4" />
      <path d="M15.7 6.7l-7.4 4" />
    </>
  ),
  overview: (
    <>
      <path d="M3.5 3.5v17h17" />
      <path d="M8 16v2.5" />
      <path d="M12.5 11v7.5" />
      <path d="M17 7v11.5" />
    </>
  ),
  memory: (
    <>
      <path d="M12 3a6 6 0 0 1 6 6v1.5a4 4 0 0 1-1.5 8H7.5A4 4 0 0 1 6 10.5V9a6 6 0 0 1 6-6z" />
      <path d="M12 8v4" />
      <path d="M9.5 10.5h5" />
    </>
  ),
}

export function NavIcon({ name }: { name: string }) {
  return (
    <svg
      className="nav-svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {ICONS[name]}
    </svg>
  )
}
