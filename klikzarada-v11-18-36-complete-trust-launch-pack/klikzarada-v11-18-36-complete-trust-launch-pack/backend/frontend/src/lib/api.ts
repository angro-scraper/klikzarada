export type SessionUser = {
  id: number
  full_name: string
  email: string
  role: 'korisnik' | 'oglasivac' | 'admin'
  status: string
  level: string
  balance_rsd: number
  pending_rsd: number
  lifetime_earned_rsd: number
  payment_method?: string | null
  payment_details?: string | null
  company_name?: string | null
  advertiser_budget_rsd: number
  advertiser_reserved_rsd: number
  referral_code?: string | null
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api/ui${path}`, {
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', ...(init.headers || {}) },
    ...init,
  })
  if (response.status === 204) return undefined as T
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.detail || 'Akcija trenutno nije uspela. Pokušaj ponovo.')
  return data as T
}

export function formatRsd(value: number) {
  return `${new Intl.NumberFormat('sr-RS', { maximumFractionDigits: 0 }).format(value || 0)} RSD`
}
