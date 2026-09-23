import { ReactNode } from 'react'

type NavItem = { id: string; label: string; icon: string; badge?: number }
type NavGroup = { group?: string; items: NavItem[] }

function Logo({ onClick }: { onClick: () => void }) {
  return (
    <button onClick={onClick} className="flex items-center gap-2.5 px-4 py-4 cursor-pointer w-full">
      <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center font-bold text-white text-sm shadow-sm">K</div>
      <div className="text-left">
        <span className="font-bold text-white text-sm tracking-tight">KlikZarada</span>
        <span className="block text-[10px] text-navy-600/60 leading-none mt-0.5" style={{color:'#9AB1C8'}}>platforma</span>
      </div>
    </button>
  )
}

function NavItemRow({ item, active, onClick }: { item: NavItem; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-3 px-3 py-2 text-[13px] transition-all duration-100 cursor-pointer rounded-lg mx-2 ${
        active
          ? 'bg-blue-600 text-white font-semibold shadow-sm'
          : 'text-[#9db5ca] hover:text-white hover:bg-[#183a5b] font-medium'
      }`}
      style={{ width: 'calc(100% - 16px)' }}
    >
      <span className="text-base w-5 text-center shrink-0">{item.icon}</span>
      <span className="flex-1 text-left">{item.label}</span>
      {item.badge ? (
        <span className="bg-coral-600 text-white text-[10px] font-bold rounded px-1.5 py-0.5 min-w-[18px] text-center">
          {item.badge}
        </span>
      ) : null}
    </button>
  )
}

export function Sidebar({
  groups, active, onNavigate, footer, isMobile, onClose
}: {
  groups: NavGroup[]
  active: string
  onNavigate: (id: string) => void
  footer?: ReactNode
  isMobile?: boolean
  onClose?: () => void
}) {
  return (
    <aside
      className={`flex flex-col h-full ${isMobile ? 'w-64' : 'w-56'}`}
      style={{ background: '#0a1628', borderRight: '1px solid #1a3050' }}
    >
      <Logo onClick={() => { onNavigate('home'); onClose?.() }} />
      <div className="flex-1 overflow-y-auto py-2">
        {groups.map((g, gi) => (
          <div key={gi} className="mb-3">
            {g.group && (
              <p className="px-4 mb-1 text-[10px] font-bold uppercase tracking-widest" style={{ color: '#8aa7c2' }}>
                {g.group}
              </p>
            )}
            <div className="flex flex-col gap-0.5">
              {g.items.map(item => (
                <NavItemRow
                  key={item.id}
                  item={item}
                  active={active === item.id}
                  onClick={() => { onNavigate(item.id); onClose?.() }}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
      {footer && (
        <div style={{ borderTop: '1px solid #1a3050' }} className="p-3">
          {footer}
        </div>
      )}
    </aside>
  )
}

export function TopBar({ onMenuClick, pageTitle, actions, onNavigate, badge }: {
  onMenuClick?: () => void
  pageTitle?: string
  actions?: ReactNode
  onNavigate: (id: string) => void
  badge?: string
}) {
  return (
    <header className="h-14 bg-white border-b border-frame flex items-center px-4 gap-3 shrink-0 shadow-sm">
      {onMenuClick && (
        <button
          onClick={onMenuClick}
          className="p-1.5 rounded-lg hover:bg-mint-100 text-ink-2 cursor-pointer lg:hidden"
        >
          ☰
        </button>
      )}
      {pageTitle && (
        <div className="flex items-center gap-2">
          {badge && (
            <span className="text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded" style={{ background: '#FEE2E2', color: '#b91c1c' }}>
              {badge}
            </span>
          )}
          <span className="text-sm font-semibold text-ink">{pageTitle}</span>
        </div>
      )}
      <div className="flex-1" />
      {actions}
    </header>
  )
}
