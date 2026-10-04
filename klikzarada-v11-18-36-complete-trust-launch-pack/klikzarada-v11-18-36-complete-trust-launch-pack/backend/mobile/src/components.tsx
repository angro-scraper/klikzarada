import type { ReactNode } from 'react';
import coinLogo from './assets/klikzarada-coins.svg';

export function Icon({ name, size = 20 }: { name: string; size?: number }) {
  const paths: Record<string, ReactNode> = {
    home: <><path d="m3 10 9-7 9 7"/><path d="M5 9v11h14V9M9 20v-6h6v6"/></>,
    list: <><path d="M9 6h12M9 12h12M9 18h12"/><circle cx="4" cy="6" r="1"/><circle cx="4" cy="12" r="1"/><circle cx="4" cy="18" r="1"/></>,
    user: <><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></>,
    chat: <><path d="M7 4.5h10a3.5 3.5 0 0 1 3.5 3.5v6a3.5 3.5 0 0 1-3.5 3.5h-6.2L5 21v-3.7A3.5 3.5 0 0 1 3.5 14V8A3.5 3.5 0 0 1 7 4.5Z"/><circle cx="9" cy="11" r=".8" fill="currentColor" stroke="none"/><circle cx="15" cy="11" r=".8" fill="currentColor" stroke="none"/></>,
    wallet: <><path d="M3 6a3 3 0 0 1 3-3h12v5H6a3 3 0 0 1 0-6"/><path d="M3 6v13a2 2 0 0 0 2 2h16V8H6"/><path d="M16 14h2"/></>,
    bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/></>,
    chevron: <path d="m9 18 6-6-6-6"/>,
    clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
    file: <><path d="M6 3h8l4 4v14H6z"/><path d="M14 3v5h5M9 13h6M9 17h6"/></>,
    send: <><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></>,
    users: <><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M19 8v6M22 11h-6"/></>,
    campaign: <><path d="m3 11 15-6v14L3 13z"/><path d="M7 14v5a2 2 0 0 0 2 2h2v-6M19 9a4 4 0 0 1 0 6"/></>,
    proof: <><path d="M7 3h10v4h3v14H4V7h3z"/><path d="M8 3v5h8V3M8 13h8M8 17h5"/></>,
    lock: <><rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></>,
    chart: <><path d="M4 20V10M10 20V4M16 20v-7M22 20V7"/></>,
    arrow: <><path d="M4 12h16M14 6l6 6-6 6"/></>,
    search: <><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></>,
    check: <path d="m4 12 5 5L20 6"/>,
    plus: <path d="M12 4v16M4 12h16"/>,
    mail: <><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 7 9-7"/></>,
    warning: <><path d="m12 3 10 18H2Z"/><path d="M12 9v5M12 18h.01"/></>,
  };
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}
export function Logo() { return <div className="logo"><span className="logo-mark"><img src={coinLogo} alt=""/></span><span>Klik<span>Zarada</span></span></div>; }
export function Badge({ tone = 'blue', children }: { tone?: 'blue' | 'green' | 'orange' | 'red' | 'gray'; children: ReactNode }) { return <span className={`badge badge-${tone}`}>{children}</span>; }
export function PrimaryButton({ children, onClick, secondary = false, disabled = false }: { children: ReactNode; onClick?: () => void; secondary?: boolean; disabled?: boolean }) { return <button className={`btn ${secondary ? 'btn-secondary' : ''}`} onClick={onClick} disabled={disabled}>{children}</button>; }
export function PageTitle({ children, subtitle }: { children: ReactNode; subtitle?: string }) { return <div className="page-title"><div><h1>{children}</h1>{subtitle && <p>{subtitle}</p>}</div></div>; }
export function TaskCard({ title, description, reward, daily, time, status, onClick }: { title: string; description: string; reward: string; daily?: string; time: string; status?: string; onClick: () => void }) {
  return <button className="task-card" onClick={onClick}><div className="task-main"><div className={`task-logo ${title.includes('QR') ? 'qr' : 'chart'}`}><Icon name={title.includes('QR') ? 'proof' : 'chart'} size={26}/></div><div className="grow"><strong>{title}</strong><p>{description}</p></div><Icon name="chevron" size={18}/></div><div className="task-reward"><strong>{reward}</strong>{daily && <small>{daily}</small>}</div><div className="task-meta"><span><Icon name="clock" size={15}/>{time}</span><span className="task-proof"><Icon name="file" size={15}/><span>{status || 'Kratak izveštaj'}</span></span></div></button>;
}
