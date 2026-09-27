import { lazy, startTransition, Suspense, useEffect, useState } from 'react'
import Landing from './pages/Landing'
import Auth from './pages/Auth'
import TasksPublic from './pages/TasksPublic'
import { api } from './lib/api'
import { userDashboardPageFromPath } from './lib/userDashboardRoutes'

// Public visitors should not download the three authenticated workspaces.
// Their own registration and task pages stay instant on refresh and navigation.
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

  if (!checked) return <RouteLoader />
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

  if (!checked) return <RouteLoader />
  return <AdvertiserPanel onNavigate={onNavigate} />
}

function RouteLoader() {
  return (
    <main className="min-h-screen bg-mint-50" aria-busy="true" aria-label="Učitavanje panela">
      <header className="flex h-[68px] items-center justify-between border-b border-slate-200 bg-white px-5 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-600 font-bold text-white">K</div>
          <div>
            <p className="font-bold text-navy-900">KlikZarada</p>
            <p className="text-xs text-slate-500">platforma</p>
          </div>
        </div>
        <div className="h-9 w-28 animate-pulse rounded-xl bg-slate-100" />
      </header>
      <div className="flex">
        <aside className="hidden min-h-[calc(100vh-68px)] w-72 shrink-0 border-r border-navy-800 bg-navy-950 px-4 py-7 md:block">
          <div className="space-y-3">
            {["w-28", "w-40", "w-32", "w-36", "w-24", "w-40", "w-28"].map((width, index) => (
              <div key={index} className="flex items-center gap-3 rounded-xl px-3 py-2.5">
                <span className="h-5 w-5 animate-pulse rounded-md bg-navy-800" />
                <span className={`h-3 animate-pulse rounded bg-navy-800 ${width}`} />
              </div>
            ))}
          </div>
        </aside>
        <section className="w-full px-5 py-8 md:px-9">
          <div className="mb-7 h-4 w-36 animate-pulse rounded bg-slate-200" />
          <div className="h-8 w-64 animate-pulse rounded-lg bg-slate-200" />
          <div className="mt-3 h-4 w-96 max-w-full animate-pulse rounded bg-slate-100" />
          <div className="mt-8 grid gap-4 md:grid-cols-3">
            {[0, 1, 2].map(index => <div key={index} className="h-28 animate-pulse rounded-2xl border border-slate-200 bg-white" />)}
          </div>
          <div className="mt-5 h-64 animate-pulse rounded-2xl border border-slate-200 bg-white" />
        </section>
      </div>
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
    startTransition(() => setPathname(nextPath))
    window.scrollTo(0, 0)
  }

  useEffect(() => {
    const onPopState = () => startTransition(() => setPathname(window.location.pathname))
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
