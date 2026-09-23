import { ReactNode } from 'react'

type Crumb = { label: string; onClick?: () => void }

export function PageHeader({
  breadcrumbs,
  onBack,
  backLabel,
  title,
  description,
  action,
}: {
  breadcrumbs?: Crumb[]
  onBack?: () => void
  backLabel?: string
  title?: string
  description?: string
  action?: ReactNode
}) {
  return (
    <div className="mb-5">
      {/* Breadcrumb + back */}
      {(breadcrumbs || onBack) && (
        <div className="flex items-center gap-2 mb-3">
          {onBack && (
            <button
              onClick={onBack}
              className="inline-flex items-center gap-1.5 text-sm font-semibold text-blue-600 hover:text-blue-700 cursor-pointer px-2.5 py-1.5 rounded-lg hover:bg-blue-50 transition-colors -ml-2.5"
            >
              <span className="text-base leading-none">←</span>
              {backLabel ?? 'Nazad'}
            </button>
          )}
          {onBack && breadcrumbs && <span className="text-ink-3 text-sm">·</span>}
          {breadcrumbs && (
            <nav className="flex items-center gap-1.5 text-sm">
              {breadcrumbs.map((c, i) => (
                <span key={i} className="flex items-center gap-1.5">
                  {i > 0 && <span className="text-ink-3">/</span>}
                  {c.onClick ? (
                    <button onClick={c.onClick} className="text-blue-600 hover:underline cursor-pointer font-medium">
                      {c.label}
                    </button>
                  ) : (
                    <span className={i === breadcrumbs.length - 1 ? 'text-ink font-semibold' : 'text-ink-2'}>{c.label}</span>
                  )}
                </span>
              ))}
            </nav>
          )}
        </div>
      )}

      {/* Title row */}
      {(title || action) && (
        <div className="flex items-start justify-between gap-3">
          <div>
            {title && <h1 className="text-xl font-extrabold text-ink leading-tight">{title}</h1>}
            {description && <p className="text-sm text-ink-2 mt-0.5">{description}</p>}
          </div>
          {action && <div className="shrink-0">{action}</div>}
        </div>
      )}
    </div>
  )
}
