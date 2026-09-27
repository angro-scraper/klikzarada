import { lazy, Suspense, useEffect, useState } from 'react'
import Landing from './pages/Landing'
import { api } from './lib/api'
import { userDashboardPageFromPath } from './lib/userDashboardRoutes'

// Public visitors should not download the three authenticated workspaces.
const Auth = lazy(() => import('./pages/Auth'))
const TasksPublic = lazy(() => import('./pages/TasksPublic'))
const UserDashboard = lazy(() => import('./pages/UserDashboard'))
const AdvertiserPanel = lazy(() => import('./pages/AdvertiserPanel'))
const AdminHub = lazy(() => import('./pages/AdminHub'))
const Legal = lazy(() => import('./pages/Legal'))
const HelpCenter = lazy(() => import('./pages/HelpCenter'))

type Route =
  | 'home'
  | 'login' | 'register'
  | 'advertiser-login' | 'advertiser-register'
  | 'admin-login'
  | 'tasks-public'
  | 'dashboard'
  | 'advertiser'
  | 'admin'
  | 'legal'
  | 'help'

const routePaths: Record<Route, string> = {
  home: '/',
  login: '/prijava',
  register: '/registracija',
  'advertiser-login': '/oglasivac/prijava',
  'advertiser-register': '/oglasivac/registracija',
  'admin-login': '/admin/prijava',
  'tasks-public': '/zadaci',
  dashboard: '/korisnik/panel',
  advertiser: '/oglasivac/panel',
  admin: '/admin',
  legal: '/pravila',
  help: '/pomoc',
}

function routeFromPath(pathname: string): Route {
  if (pathname === '/admin/prijava') return 'admin-login'
  if (pathname.startsWith('/admin')) return 'admin'
  if (pathname.startsWith('/korisnik')) return 'dashboard'
  if (pathname.startsWith('/oglasivac/panel')) return 'advertiser'
  if (pathname === '/pravila') return 'legal'
  if (pathname === '/pomoc') return 'help'
  if (pathname === '/login') return 'login'
  return (Object.entries(routePaths).find(([, path]) => path === pathname)?.[0] as Route | undefined) ?? 'home'
}

function AdminRoute({ onNavigate }: { onNavigate: (id: string) => void }) {
  const [checked, setChecked] = useState(false)

  useEffect(() => {
    void api.session()
      .then(({ user }) => {
        if (user?.role !== 'admin') onNavigate('admin-login')
        else setChecked(true)
      })
      .catch(() => onNavigate('admin-login'))
  }, [onNavigate])

  if (!checked) return <div className="min-h-screen bg-mint-50" />
  return <AdminHub onNavigate={onNavigate} />
}

function AdvertiserRoute({ onNavigate }: { onNavigate: (id: string) => void }) {
  const [checked, setChecked] = useState(false)

  useEffect(() => {
    void api.session()
      .then(({ user }) => {
        if (user?.role !== 'oglasivac' && user?.role !== 'admin') onNavigate('advertiser-login')
        else setChecked(true)
      })
      .catch(() => onNavigate('advertiser-login'))
  }, [onNavigate])

  if (!checked) return <div className="min-h-screen bg-mint-50" />
  return <AdvertiserPanel onNavigate={onNavigate} />
}

function RouteLoader() {
  return (
    <main className="min-h-screen bg-mint-50 px-5 py-24">
      <section className="mx-auto max-w-xl rounded-3xl border border-slate-200 bg-white p-8 text-center shadow-sm" aria-live="polite">
        <div className="mx-auto h-9 w-9 animate-pulse rounded-xl bg-blue-600" />
        <p className="mt-4 font-semibold text-navy-900">Učitavamo bezbedan prostor naloga...</p>
      </section>
    </main>
  )
}

export default function App() {
  const [pathname, setPathname] = useState(() => window.location.pathname)
  const route = routeFromPath(pathname)

  function go(id: string) {
    const nextRoute = id as Route
    if (!routePaths[nextRoute]) return
    const nextPath = routePaths[nextRoute]
    window.history.pushState({}, '', nextPath)
    setPathname(nextPath)
    window.scrollTo(0, 0)
  }

  useEffect(() => {
    const onPopState = () => setPathname(window.location.pathname)
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  if (route === 'home') return <Landing onNavigate={go} />

  return (
    <Suspense fallback={<RouteLoader />}>
      {route === 'tasks-public' && <TasksPublic onNavigate={go} />}
      {route === 'login' && <Auth initialMode="login" onNavigate={go} />}
      {route === 'register' && <Auth initialMode="register" onNavigate={go} />}
      {route === 'advertiser-login' && <Auth initialMode="advertiser-login" onNavigate={go} />}
      {route === 'advertiser-register' && <Auth initialMode="advertiser-register" onNavigate={go} />}
      {route === 'admin-login' && <Auth initialMode="admin-login" onNavigate={go} />}
      {route === 'dashboard' && <UserDashboard initialPage={userDashboardPageFromPath(pathname)} onNavigate={go} />}
      {route === 'advertiser' && <AdvertiserRoute onNavigate={go} />}
      {route === 'admin' && <AdminRoute onNavigate={go} />}
      {route === 'legal' && <Legal onNavigate={go} />}
      {route === 'help' && <HelpCenter onNavigate={go} />}
    </Suspense>
  )
}
