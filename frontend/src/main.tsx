import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import './index.css'

const queryClient = new QueryClient()

// Mocks run when explicitly requested (VITE_USE_MOCKS=1) OR in any production build
// that has no real backend configured (VITE_API_BASE_URL unset) — e.g. a static host
// like Lovable. Local `vite dev` without flags still hits the real Python backend, so
// the live HydraDB demo is unaffected.
const USE_MOCKS =
  import.meta.env.VITE_USE_MOCKS === '1' ||
  (import.meta.env.PROD && !import.meta.env.VITE_API_BASE_URL)

async function prepare() {
  if (USE_MOCKS) {
    const { worker } = await import('./mocks/browser')
    return worker.start({ onUnhandledRequest: 'bypass' })
  }
}

prepare().then(() => {
  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </React.StrictMode>
  )
})
