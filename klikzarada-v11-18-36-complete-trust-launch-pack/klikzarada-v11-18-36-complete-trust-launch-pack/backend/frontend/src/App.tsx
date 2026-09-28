import { useCallback, useEffect, useState, type ReactNode } from 'react'
import Landing from './pages/Landing'
import Auth from './pages/Auth'
import TasksPublic from './pages/TasksPublic'
import UserDashboard from './pages/UserDashboard'
import AdvertiserPanel from './pages/AdvertiserPanel'
import AdminHub from './pages/AdminHub'
import Legal from './pages/Legal'
import HelpCenter from './pages/HelpCenter'
import { api } from './lib/api'
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

function ProtectedRoute({ roles, onNavigate, children }: { roles: Array<'korisnik' | 'oglasivac' | 'admin'>; onNavigate: (id: string) => void; children: ReactNode }) {
  const [allowed, setAllowed] = useState(false)
  useEffect(() => {
    let mounted = true
    void api.session()
      .then(({ user }) => {
        if (!mounted) return
        if (user && roles.includes(user.role)) setAllowed(true)
        else onNavigate(user?.role === 'admin' ? 'admin' : user?.role === 'oglasivac' ? 'advertiser' : user?.role === 'korisnik' ? 'dashboard' : roles.includes('admin') ? 'admin-login' : roles.includes('oglasivac') ? 'advertiser-login' : 'login')
      })
      .catch(() => { if (mounted) onNavigate(roles.includes('admin') ? 'admin-login' : roles.includes('oglasivac') ? 'advertiser-login' : 'login') })
    return () => { mounted = false }
  }, [onNavigate])

  return allowed ? children : <div className="min-h-screen bg-mint-50 flex items-center justify-center px-4" aria-busy="true"><p className="rounded-xl border border-blue-100 bg-white px-6 py-4 text-sm font-medium text-ink shadow-sm">Proveravamo nalog i otvaramo tvoj panel...</p></div>
}

export default function App() {
  const [pathname, setPathname] = useState(() => window.location.pathname)
  const route = routeFromPath(pathname)

  const go = useCallback((id: string) => {
    const nextRoute = id as Route
    if (!routePaths[nextRoute]) return
    const nextPath = routePaths[nextRoute]
    window.history.pushState({}, '', nextPath)
    setPathname(nextPath)
    window.scrollTo(0, 0)
  }, [])

  useEffect(() => {
    const onPopState = () => setPathname(window.location.pathname)
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  if (route === 'home') return <Landing onNavigate={go} />

  if (route === 'tasks-public') return <TasksPublic onNavigate={go} />
  if (route === 'login') return <Auth key="login" initialMode="login" onNavigate={go} />
  if (route === 'register') return <Auth key="register" initialMode="register" onNavigate={go} />
  if (route === 'advertiser-login') return <Auth key="advertiser-login" initialMode="advertiser-login" onNavigate={go} />
  if (route === 'advertiser-register') return <Auth key="advertiser-register" initialMode="advertiser-register" onNavigate={go} />
  if (route === 'admin-login') return <Auth key="admin-login" initialMode="admin-login" onNavigate={go} />
  if (route === 'dashboard') return <ProtectedRoute key="user" roles={['korisnik']} onNavigate={go}><UserDashboard initialPage={userDashboardPageFromPath(pathname)} onNavigate={go} /></ProtectedRoute>
  if (route === 'advertiser') return <ProtectedRoute key="advertiser" roles={['oglasivac', 'admin']} onNavigate={go}><AdvertiserPanel onNavigate={go} /></ProtectedRoute>
  if (route === 'admin') return <ProtectedRoute key="admin" roles={['admin']} onNavigate={go}><AdminHub onNavigate={go} /></ProtectedRoute>
  if (route === 'legal') return <Legal onNavigate={go} />
  if (route === 'help') return <HelpCenter onNavigate={go} />

  return <Landing onNavigate={go} />
}
