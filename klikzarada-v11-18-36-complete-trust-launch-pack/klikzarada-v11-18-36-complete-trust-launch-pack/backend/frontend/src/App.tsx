import { useState } from 'react'
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
  const [route, setRoute] = useState<Route>('home')

  function go(id: string) {
    setRoute(id as Route)
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
