import { useEffect } from 'react'

type ToastType = 'success' | 'error' | 'info' | 'warning'

const styleMap: Record<ToastType, string> = {
  success: 'bg-emerald-600 text-white',
  error:   'bg-coral-600   text-white',
  info:    'bg-blue-600    text-white',
  warning: 'bg-amber-500   text-white',
}
const iconMap: Record<ToastType, string> = {
  success: '✓', error: '✕', info: 'ℹ', warning: '⚠',
}

export function Toast({
  message,
  type = 'success',
  onDismiss,
  duration = 3000,
}: {
  message: string
  type?: ToastType
  onDismiss: () => void
  duration?: number
}) {
  useEffect(() => {
    const t = setTimeout(onDismiss, duration)
    return () => clearTimeout(t)
  }, [onDismiss, duration])

  return (
    <div className={`fixed bottom-5 left-1/2 -translate-x-1/2 z-[60] flex items-center gap-2.5 px-4 py-3 rounded-xl shadow-xl text-sm font-semibold ${styleMap[type]}`}
         style={{ minWidth: 220, maxWidth: 400 }}>
      <span className="text-base leading-none">{iconMap[type]}</span>
      <span className="flex-1">{message}</span>
      <button onClick={onDismiss} className="ml-2 opacity-70 hover:opacity-100 cursor-pointer text-lg leading-none">×</button>
    </div>
  )
}

// Hook for easy toast management
import { useState, useCallback } from 'react'

export function useToast() {
  const [toast, setToast] = useState<{ message: string; type: ToastType } | null>(null)

  const show = useCallback((message: string, type: ToastType = 'success') => {
    setToast({ message, type })
  }, [])

  const dismiss = useCallback(() => setToast(null), [])

  const node = toast ? <Toast message={toast.message} type={toast.type} onDismiss={dismiss} /> : null

  return { show, node }
}
