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

const routePaths: Record<Route, string> = {
  home: '/',
  login: '/prijava',
  register: '/registracija',
  'advertiser-login': '/oglasivac/prijava',
  'advertiser-register': '/oglasivac/registracija',
  'tasks-public': '/zadaci',
  dashboard: '/korisnik/panel',
  advertiser: '/oglasivac/panel',
  admin: '/admin',
}

function routeFromPath(pathname: string): Route {
  if (pathname.startsWith('/admin')) return 'admin'
  if (pathname.startsWith('/korisnik')) return 'dashboard'
  if (pathname.startsWith('/oglasivac/panel')) return 'advertiser'
  if (pathname === '/login') return 'login'
  return (Object.entries(routePaths).find(([, path]) => path === pathname)?.[0] as Route | undefined) ?? 'home'
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
  if (route === 'dashboard')          return <UserDashboard onNavigate={go} />
  if (route === 'advertiser')         return <AdvertiserPanel onNavigate={go} />
  if (route === 'admin')              return <AdminHub onNavigate={go} />

  return <Landing onNavigate={go} />
}
