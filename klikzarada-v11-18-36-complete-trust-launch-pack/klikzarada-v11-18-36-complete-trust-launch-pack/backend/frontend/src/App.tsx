import { useEffect, useState } from 'react'
import Landing from './pages/Landing'
import Auth from './pages/Auth'
import TasksPublic from './pages/TasksPublic'
import UserDashboard from './pages/UserDashboard'
import AdvertiserPanel from './pages/AdvertiserPanel'
import AdminHub from './pages/AdminHub'
import { api } from './lib/api'

type Route =
  | 'home'
  | 'login' | 'register'
  | 'advertiser-login' | 'advertiser-register'
  | 'admin-login'
  | 'tasks-public'
  | 'dashboard'
  | 'advertiser'
  | 'admin'

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
}

function routeFromPath(pathname: string): Route {
  if (pathname === '/admin/prijava') return 'admin-login'
  if (pathname.startsWith('/admin')) return 'admin'
  if (pathname.startsWith('/korisnik')) return 'dashboard'
  if (pathname.startsWith('/oglasivac/panel')) return 'advertiser'
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

export default function App() {
  const [route, setRoute] = useState<Route>(() => routeFromPath(window.location.pathname))

  function go(id: string) {
    const nextRoute = id as Route
    if (!routePaths[nextRoute]) return
    window.history.pushState({}, '', routePaths[nextRoute])
    setRoute(nextRoute)
    window.scrollTo(0, 0)
  }

  useEffect(() => {
    const onPopState = () => setRoute(routeFromPath(window.location.pathname))
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  if (route === 'home')               return <Landing onNavigate={go} />
  if (route === 'tasks-public')       return <TasksPublic onNavigate={go} />
  if (route === 'login')              return <Auth initialMode="login" onNavigate={go} />
  if (route === 'register')           return <Auth initialMode="register" onNavigate={go} />
  if (route === 'advertiser-login')   return <Auth initialMode="advertiser-login" onNavigate={go} />
  if (route === 'advertiser-register')return <Auth initialMode="advertiser-register" onNavigate={go} />
  if (route === 'admin-login')         return <Auth initialMode="admin-login" onNavigate={go} />
  if (route === 'dashboard')          return <UserDashboard onNavigate={go} />
  if (route === 'advertiser')         return <AdvertiserRoute onNavigate={go} />
  if (route === 'admin')              return <AdminRoute onNavigate={go} />

  return <Landing onNavigate={go} />
}
