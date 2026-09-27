import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

type ErrorBoundaryState = { hasError: boolean }

class AppErrorBoundary extends React.Component<React.PropsWithChildren, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false }

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true }
  }

  render() {
    if (this.state.hasError) {
      return <main className="min-h-screen bg-mint-50 px-5 py-16 text-center text-ink"><div className="mx-auto max-w-md rounded-2xl border border-amber-200 bg-white p-6 shadow-sm"><h1 className="text-xl font-extrabold">Stranica nije učitana</h1><p className="mt-2 text-sm text-ink-2">Aplikacija je ažurirana dok je ova kartica bila otvorena. Učitaj najnoviju verziju i pokušaj ponovo.</p><button className="mt-5 rounded-lg bg-blue-600 px-4 py-2 text-sm font-bold text-white" onClick={() => { const url = new URL(window.location.href); url.searchParams.set('_reload', String(Date.now())); window.location.replace(url.toString()) }}>Učitaj ponovo</button></div></main>
    }
    return this.props.children
  }
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <AppErrorBoundary>
      <App />
    </AppErrorBoundary>
  </React.StrictMode>,
)
