import { useEffect, useState } from 'react'
import Landing from './pages/Landing'
import Auth from './pages/Auth'
import TasksPublic from './pages/TasksPublic'
import UserDashboard from './pages/UserDashboard'
import AdvertiserPanel from './pages/AdvertiserPanel'
import AdminHub from './pages/AdminHub'

type Route =
  | 'home'
  | 'login' | 'register'
  | 'advertiser-login' | 'advertiser-register'
  | 'tasks-public'
  | 'dashboard'
  | 'advertiser'
  | 'admin'

export default function App() {
  const [route, setRoute] = useState<Route>(() => routeFromPath(window.location.pathname))

  useEffect(() => {
    const onPopState = () => setRoute(routeFromPath(window.location.pathname))
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  function go(id: string) {
    const next = id as Route
    const path = pathForRoute(next)
    if (window.location.pathname !== path) window.history.pushState({}, '', path)
    setRoute(next)
    window.scrollTo(0, 0)
  }

  if (route === 'home')               return <Landing onNavigate={go} />
  if (route === 'tasks-public')       return <TasksPublic onNavigate={go} />
  if (route === 'login')              return <Auth initialMode="login" onNavigate={go} />
  if (route === 'register')           return <Auth initialMode="register" onNavigate={go} />
  if (route === 'advertiser-login')   return <Auth initialMode="advertiser-login" onNavigate={go} />
  if (route === 'advertiser-register')return <Auth initialMode="advertiser-register" onNavigate={go} />
  if (route === 'dashboard')          return <UserDashboard onNavigate={go} />
  if (route === 'advertiser')         return <AdvertiserPanel onNavigate={go} />
  if (route === 'admin')              return <AdminHub onNavigate={go} />

  return <Landing onNavigate={go} />
}

function routeFromPath(path: string): Route {
  if (path === '/login') return 'login'
  if (path === '/registracija') return 'register'
  if (path === '/oglasivac/login') return 'advertiser-login'
  if (path === '/oglasivac/registracija') return 'advertiser-register'
  if (path === '/zadaci') return 'tasks-public'
  if (path.startsWith('/korisnik')) return 'dashboard'
  if (path.startsWith('/oglasivac')) return 'advertiser'
  if (path.startsWith('/admin')) return 'admin'
  return 'home'
}

function pathForRoute(route: Route) {
  return {
    home: '/', login: '/login', register: '/registracija',
    'advertiser-login': '/oglasivac/login', 'advertiser-register': '/oglasivac/registracija',
    'tasks-public': '/zadaci', dashboard: '/korisnik/panel', advertiser: '/oglasivac/panel', admin: '/admin/v11',
  }[route]
}
