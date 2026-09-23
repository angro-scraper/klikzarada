import { ReactNode } from 'react'

// ── Status badges ──────────────────────────────────────────────────────────────
const statusMap: Record<string, { label: string; cls: string }> = {
  aktivno:      { label: 'Aktivno',      cls: 'bg-emerald-100 text-emerald-700 border border-emerald-200' },
  na_cekanju:   { label: 'Na čekanju',   cls: 'bg-amber-100   text-amber-700   border border-amber-200' },
  odobreno:     { label: 'Odobreno',     cls: 'bg-emerald-100 text-emerald-700 border border-emerald-200' },
  odbijeno:     { label: 'Odbijeno',     cls: 'bg-coral-100   text-coral-700   border border-coral-200' },
  blokirano:    { label: 'Blokirano',    cls: 'bg-coral-100   text-coral-700   border border-coral-200' },
  placeno:      { label: 'Plaćeno',      cls: 'bg-blue-100    text-blue-700    border border-blue-200' },
  na_proveri:   { label: 'Na proveri',   cls: 'bg-violet-100  text-violet-700  border border-violet-200' },
  u_obradi:     { label: 'U obradi',     cls: 'bg-blue-100    text-blue-700    border border-blue-200' },
  greska:       { label: 'Greška',       cls: 'bg-coral-100   text-coral-700   border border-coral-200' },
  obustavljeno: { label: 'Obustavljeno', cls: 'bg-gray-100    text-gray-600    border border-gray-200' },
  premium:      { label: 'Premium',      cls: 'bg-violet-100  text-violet-700  border border-violet-200' },
  draft:        { label: 'Draft',        cls: 'bg-gray-100    text-gray-600    border border-gray-200' },
}

export function StatusBadge({ status }: { status: string }) {
  const s = statusMap[status] ?? { label: status, cls: 'bg-gray-100 text-gray-600 border border-gray-200' }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold tracking-wide ${s.cls}`}>
      {s.label}
    </span>
  )
}

// ── Buttons ────────────────────────────────────────────────────────────────────
type BtnVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'success' | 'premium'
export function Btn({
  variant = 'primary', children, onClick, disabled, size = 'md', className = '', type = 'button'
}: {
  variant?: BtnVariant; children: ReactNode; onClick?: () => void
  disabled?: boolean; size?: 'sm' | 'md' | 'lg'; className?: string; type?: 'button' | 'submit'
}) {
  const base = 'inline-flex items-center gap-1.5 font-semibold transition-all duration-150 rounded-md cursor-pointer select-none'
  const sizes = { sm: 'px-3 py-1.5 text-xs', md: 'px-4 py-2 text-sm', lg: 'px-5 py-2.5 text-sm' }
  const variants: Record<BtnVariant, string> = {
    primary:   'bg-blue-600 hover:bg-blue-700 text-white shadow-sm',
    secondary: 'bg-white hover:bg-gray-50 text-ink border border-frame shadow-sm',
    ghost:     'hover:bg-mint-100 text-ink-2 hover:text-ink',
    danger:    'bg-coral-600 hover:bg-coral-700 text-white shadow-sm',
    success:   'bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm',
    premium:   'bg-violet-600 hover:bg-violet-700 text-white shadow-sm',
  }
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`${base} ${sizes[size]} ${variants[variant]} ${disabled ? 'opacity-50 cursor-not-allowed' : ''} ${className}`}
    >
      {children}
    </button>
  )
}

// ── Cards ──────────────────────────────────────────────────────────────────────
export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`bg-white border border-frame rounded-xl shadow-sm ${className}`}>
      {children}
    </div>
  )
}

// Semantic card variants
type CardVariant = 'green' | 'blue' | 'purple' | 'orange' | 'red' | 'teal'
export function ColorCard({ variant, children, className = '' }: {
  variant: CardVariant; children: ReactNode; className?: string
}) {
  const map: Record<CardVariant, string> = {
    green:  'bg-emerald-50 border-emerald-200',
    blue:   'bg-blue-50    border-blue-200',
    purple: 'bg-violet-50  border-violet-200',
    orange: 'bg-amber-50   border-amber-200',
    red:    'bg-coral-50   border-coral-200',
    teal:   'bg-teal-50    border-teal-200',
  }
  return (
    <div className={`border rounded-xl ${map[variant]} ${className}`}>
      {children}
    </div>
  )
}

// ── Stat cards ─────────────────────────────────────────────────────────────────
type StatAccent = 'green' | 'blue' | 'purple' | 'orange' | 'red' | 'teal' | 'neutral'
export function StatCard({ label, value, sub, accent = 'green', icon }: {
  label: string; value: string; sub?: string; accent?: StatAccent; icon?: string
}) {
  const bgMap: Record<StatAccent, string> = {
    green:   'bg-emerald-50 border-emerald-200',
    blue:    'bg-blue-50    border-blue-200',
    purple:  'bg-violet-50  border-violet-200',
    orange:  'bg-amber-50   border-amber-200',
    red:     'bg-coral-50   border-coral-200',
    teal:    'bg-teal-50    border-teal-200',
    neutral: 'bg-white      border-frame',
  }
  const valMap: Record<StatAccent, string> = {
    green:   'text-emerald-700',
    blue:    'text-blue-700',
    purple:  'text-violet-700',
    orange:  'text-amber-700',
    red:     'text-coral-700',
    teal:    'text-teal-700',
    neutral: 'text-ink',
  }
  return (
    <div className={`border rounded-xl p-4 shadow-sm ${bgMap[accent]}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-[11px] text-ink-3 uppercase tracking-wide font-semibold mb-1">{label}</p>
          <p className={`font-mono text-2xl font-bold leading-tight ${valMap[accent]}`}>{value}</p>
          {sub && <p className="text-[11px] text-ink-3 mt-0.5">{sub}</p>}
        </div>
        {icon && <span className="text-2xl opacity-50">{icon}</span>}
      </div>
    </div>
  )
}

// ── Section header ─────────────────────────────────────────────────────────────
export function SectionHeader({ title, description, action }: {
  title: string; description?: string; action?: ReactNode
}) {
  return (
    <div className="flex items-start justify-between mb-4">
      <div>
        <h2 className="text-base font-bold text-ink">{title}</h2>
        {description && <p className="text-sm text-ink-2 mt-0.5">{description}</p>}
      </div>
      {action}
    </div>
  )
}

// ── Empty state ────────────────────────────────────────────────────────────────
export function EmptyState({ icon, title, description, action }: {
  icon: string; title: string; description?: string; action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center py-14 text-center">
      <span className="text-4xl mb-3 opacity-60">{icon}</span>
      <p className="font-semibold text-ink">{title}</p>
      {description && <p className="text-sm text-ink-2 mt-1 max-w-xs">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

// ── Table ──────────────────────────────────────────────────────────────────────
export function Table({ headers, rows }: { headers: string[]; rows: ReactNode[][] }) {
  return (
    <div className="table-scroll">
      <table className="w-full min-w-full text-sm">
        <thead>
          <tr className="border-b border-frame bg-mint-50">
            {headers.map((h, i) => (
              <th key={i} className="text-left py-2.5 px-4 text-[11px] font-bold text-ink-3 uppercase tracking-wide whitespace-nowrap">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {rows.map((row, i) => (
            <tr key={i} className="hover:bg-mint-50 transition-colors">
              {row.map((cell, j) => (
                <td key={j} className="py-3 px-4 text-ink whitespace-nowrap">{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ── Inputs ─────────────────────────────────────────────────────────────────────
export function Input({ label, placeholder, type = 'text', value, onChange, min, max, step }: {
  label?: string; placeholder?: string; type?: string; value?: string; onChange?: (v: string) => void; min?: number; max?: number; step?: number
}) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && <label className="text-xs font-semibold text-ink-2 uppercase tracking-wide">{label}</label>}
      <input
        type={type}
        placeholder={placeholder}
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={e => onChange?.(e.target.value)}
        className="bg-white border border-frame text-ink placeholder-ink-4 rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-100 focus:outline-none transition-all"
      />
    </div>
  )
}

export function Select({ label, options, value, onChange }: {
  label?: string; options: { value: string; label: string }[]; value?: string; onChange?: (v: string) => void
}) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && <label className="text-xs font-semibold text-ink-2 uppercase tracking-wide">{label}</label>}
      <select
        value={value}
        onChange={e => onChange?.(e.target.value)}
        className="bg-white border border-frame text-ink rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-100 focus:outline-none transition-all"
      >
        {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  )
}

// ── Tabs ───────────────────────────────────────────────────────────────────────
export function Tabs({ tabs, active, onChange }: {
  tabs: { id: string; label: string }[]; active: string; onChange: (id: string) => void
}) {
  return (
    <div className="flex gap-1 border-b border-frame mb-5">
      {tabs.map(t => (
        <button
          key={t.id}
          onClick={() => onChange(t.id)}
          className={`px-4 py-2.5 text-sm font-semibold border-b-2 transition-colors cursor-pointer ${
            active === t.id
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-ink-2 hover:text-ink hover:border-frame'
          }`}
        >
          {t.label}
        </button>
      ))}
    </div>
  )
}

// ── Alerts ─────────────────────────────────────────────────────────────────────
export function Alert({ type, children }: { type: 'success' | 'error' | 'warning' | 'info'; children: ReactNode }) {
  const map = {
    success: 'bg-emerald-50 border-emerald-200 text-emerald-800',
    error:   'bg-coral-50   border-coral-200   text-coral-700',
    warning: 'bg-amber-50   border-amber-200   text-amber-800',
    info:    'bg-blue-50    border-blue-200    text-blue-800',
  }
  const icon = { success: '✓', error: '✕', warning: '⚠', info: 'ℹ' }
  return (
    <div className={`border rounded-lg p-3 text-sm flex gap-2 ${map[type]}`}>
      <span className="shrink-0 font-bold">{icon[type]}</span>
      <div>{children}</div>
    </div>
  )
}
