import { ReactNode, useEffect } from 'react'
import { Btn } from './ui'

export function ConfirmModal({
  open,
  title,
  description,
  confirmLabel = 'Potvrdi',
  cancelLabel = 'Otkaži',
  variant = 'danger',
  onConfirm,
  onCancel,
}: {
  open: boolean
  title: string
  description?: string
  confirmLabel?: string
  cancelLabel?: string
  variant?: 'danger' | 'success' | 'primary'
  onConfirm: () => void
  onCancel: () => void
}) {
  // Close on Escape
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onCancel() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, onCancel])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onCancel} />
      {/* Panel */}
      <div className="relative bg-white rounded-2xl shadow-2xl max-w-sm w-full p-6 border border-frame">
        <button
          onClick={onCancel}
          aria-label="Zatvori"
          className="absolute top-4 right-4 text-ink-3 hover:text-ink cursor-pointer text-xl leading-none p-1"
        >
          ×
        </button>
        <h2 className="text-lg font-bold text-ink mb-2 pr-6">{title}</h2>
        {description && <p className="text-sm text-ink-2 mb-5">{description}</p>}
        <div className="flex gap-2 justify-end">
          <Btn variant="secondary" onClick={onCancel}>{cancelLabel}</Btn>
          <Btn variant={variant} onClick={onConfirm}>{confirmLabel}</Btn>
        </div>
      </div>
    </div>
  )
}

export function InfoModal({
  open,
  title,
  children,
  onClose,
}: {
  open: boolean
  title: string
  children: ReactNode
  onClose: () => void
}) {
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, onClose])

  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-2xl max-w-md w-full p-6 border border-frame">
        <button onClick={onClose} aria-label="Zatvori" className="absolute top-4 right-4 text-ink-3 hover:text-ink cursor-pointer text-xl leading-none p-1">×</button>
        <h2 className="text-lg font-bold text-ink mb-4 pr-6">{title}</h2>
        {children}
        <div className="mt-5">
          <Btn variant="secondary" onClick={onClose} className="w-full justify-center">Zatvori</Btn>
        </div>
      </div>
    </div>
  )
}
