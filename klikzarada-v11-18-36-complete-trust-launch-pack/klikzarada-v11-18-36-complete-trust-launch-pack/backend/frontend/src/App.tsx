import { useCallback, useEffect, useState, type ReactNode } from 'react'
import Landing from './pages/Landing'
import Auth from './pages/Auth'
import TasksPublic from './pages/TasksPublic'
import UserDashboard from './pages/UserDashboard'
import AdvertiserPanel from './pages/AdvertiserPanel'
import AdminHub from './pages/AdminHub'
import Legal from './pages/Legal'
import HelpCenter from './pages/HelpCenter'
import AdvertisePublic from './pages/AdvertisePublic'
import { api, type SessionUser } from './lib/api'
import { userDashboardPageFromPath } from './lib/userDashboardRoutes'

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
  | 'advertising-public'

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
  'advertising-public': '/oglasavanje',
}

function routeFromPath(pathname: string): Route {
  if (/^\/zadaci\/\d+\/?$/.test(pathname)) return 'tasks-public'
  if (pathname === '/admin/prijava') return 'admin-login'
  if (pathname.startsWith('/admin')) return 'admin'
  if (pathname.startsWith('/korisnik')) return 'dashboard'
  if (pathname.startsWith('/oglasivac/panel') || pathname === '/oglasivac/testeri') return 'advertiser'
  if (pathname === '/pravila') return 'legal'
  if (pathname === '/pomoc') return 'help'
  if (pathname === '/login') return 'login'
  return (Object.entries(routePaths).find(([, path]) => path === pathname)?.[0] as Route | undefined) ?? 'home'
}

const roleNames = { korisnik: 'korisnik', oglasivac: 'oglašivač', admin: 'administrator' } as const

function ProtectedRoute({ roles, section, loginRoute, onNavigate, children }: { roles: SessionUser['role'][]; section: string; loginRoute: Route; onNavigate: (id: string) => void; children: ReactNode }) {
  const [account, setAccount] = useState<SessionUser | null>(null)
  const [checking, setChecking] = useState(true)
  useEffect(() => {
    let mounted = true
    void api.session()
      .then(({ user }) => {
        if (!mounted) return
        if (user) setAccount(user)
        else onNavigate(loginRoute)
      })
      .catch(() => { if (mounted) onNavigate(loginRoute) })
      .finally(() => { if (mounted) setChecking(false) })
    return () => { mounted = false }
  }, [onNavigate])

  if (checking || !account) return <div className="min-h-screen bg-mint-50 flex items-center justify-center px-4" aria-busy="true"><p className="rounded-xl border border-blue-100 bg-white px-6 py-4 text-sm font-medium text-ink shadow-sm">Proveravamo nalog i otvaramo tvoj panel...</p></div>
  if (roles.includes(account.role)) return children

  const ownRoute: Route = account.role === 'admin' ? 'admin' : account.role === 'oglasivac' ? 'advertiser' : 'dashboard'
  return <div className="min-h-screen bg-mint-50 flex items-center justify-center px-4">
    <div className="w-full max-w-lg rounded-2xl border border-blue-100 bg-white p-7 shadow-sm space-y-4">
      <div className="h-10 w-10 rounded-xl bg-blue-600 text-white font-bold flex items-center justify-center">K</div>
      <h1 className="text-xl font-bold text-ink">{section} je na drugom nalogu</h1>
      <p className="text-sm text-ink-2">Trenutno si prijavljen/a kao {roleNames[account.role]}: <strong className="text-ink">{account.email}</strong>. Ovaj nalog nema pristup sekciji {section.toLowerCase()}. Podaci i zadaci različitih naloga se ne mešaju.</p>
      <div className="flex flex-wrap gap-3">
        <button type="button" onClick={() => onNavigate(ownRoute)} className="rounded-lg border border-blue-200 px-4 py-2 text-sm font-semibold text-blue-700 hover:bg-blue-50">Otvori moj panel</button>
        <button type="button" onClick={() => { void api.logout().catch(() => undefined).finally(() => onNavigate(loginRoute)) }} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700">{loginRoute === 'admin-login' ? 'Odjavi se i prijavi kao admin' : 'Odjavi se i prijavi na drugi nalog'}</button>
      </div>
    </div>
  </div>
}

export default function App() {
  const [pathname, setPathname] = useState(() => window.location.pathname)
  const route = routeFromPath(pathname)

  const go = useCallback((id: string) => {
    const nextRoute = id as Route
    if (!routePaths[nextRoute]) return
    const nextPath = routePaths[nextRoute]
    const taskId = new URLSearchParams(window.location.search).get('task')
    const keepsTaskContext = Boolean(taskId) && ['tasks-public', 'login', 'register', 'dashboard'].includes(nextRoute)
    const nextUrl = keepsTaskContext ? `${nextPath}?task=${encodeURIComponent(taskId || '')}` : nextPath
    window.history.pushState({}, '', nextUrl)
    setPathname(nextPath)
    window.scrollTo(0, 0)
  }, [])

  useEffect(() => {
    const onPopState = () => setPathname(window.location.pathname)
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  if (route === 'home') return <Landing onNavigate={go} />

  if (route === 'tasks-public') return <TasksPublic />
  if (route === 'login') return <Auth key="login" initialMode="login" onNavigate={go} />
  if (route === 'register') return <Auth key="register" initialMode="register" onNavigate={go} />
  if (route === 'advertiser-login') return <Auth key="advertiser-login" initialMode="advertiser-login" onNavigate={go} />
  if (route === 'advertiser-register') return <Auth key="advertiser-register" initialMode="advertiser-register" onNavigate={go} />
  if (route === 'admin-login') return <Auth key="admin-login" initialMode="admin-login" onNavigate={go} />
  if (route === 'dashboard') {
    const directTaskId = Number(new URLSearchParams(window.location.search).get('task')) || 0
    return <ProtectedRoute key="user" roles={['korisnik']} section="Korisnički panel" loginRoute="login" onNavigate={go}><UserDashboard initialPage={directTaskId ? 'zadatak-detalj' : userDashboardPageFromPath(pathname)} onNavigate={go} /></ProtectedRoute>
  }
  if (route === 'advertiser') return <ProtectedRoute key="advertiser" roles={['oglasivac', 'admin']} section="Oglašivački panel" loginRoute="advertiser-login" onNavigate={go}><AdvertiserPanel onNavigate={go} /></ProtectedRoute>
  if (route === 'admin') return <ProtectedRoute key="admin" roles={['admin']} section="Admin panel" loginRoute="admin-login" onNavigate={go}><AdminHub onNavigate={go} /></ProtectedRoute>
  if (route === 'legal') return <Legal />
  if (route === 'help') return <HelpCenter onNavigate={go} />
  if (route === 'advertising-public') return <AdvertisePublic />

  return <Landing onNavigate={go} />
}
