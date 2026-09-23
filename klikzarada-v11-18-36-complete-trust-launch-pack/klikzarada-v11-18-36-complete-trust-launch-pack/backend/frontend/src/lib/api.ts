const API_ROOT = '/api/ui'

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
  payment_method: string | null
  payment_details: string | null
  company_name: string | null
  advertiser_budget_rsd: number
  advertiser_reserved_rsd: number
  advertiser_spent_rsd: number
  referral_code: string | null
}

export type Task = {
  id: number
  title: string
  category: string
  task_type: string
  target_url: string | null
  description: string
  instructions: string
  proof_required: string
  reward_rsd: number
  total_slots: number
  used_slots: number
  estimated_minutes: number
  min_user_level: string
  featured: boolean
  status: string
  created_at: string | null
}

export type Submission = {
  id: number
  task_id: number
  task_title: string
  proof: string
  status: string
  reward_rsd: number
  review_note: string | null
  created_at: string | null
}

export type WalletTransaction = {
  id: number
  amount_rsd: number
  tx_type: string
  description: string
  created_at: string | null
}

export type Withdrawal = {
  id: number
  amount_rsd: number
  status: string
  payment_method: string
  created_at: string | null
}

export type UserDashboardData = {
  user: SessionUser
  min_withdrawal_rsd: number
  referral_count: number
  tasks: Task[]
  submissions: Submission[]
  withdrawals: Withdrawal[]
  transactions: WalletTransaction[]
}

type ApiErrorBody = { detail?: string }

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_ROOT}${path}`, {
    ...options,
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', ...(options.headers ?? {}) },
  })

  if (response.status === 204) return undefined as T
  const body = await response.json().catch(() => ({} as ApiErrorBody))
  if (!response.ok) throw new Error((body as ApiErrorBody).detail || 'Zahtev nije uspeo. Pokušaj ponovo.')
  return body as T
}

export const api = {
  session: () => request<{ authenticated: boolean; user: SessionUser | null }>('/session'),
  login: (email: string, password: string) => request<{ user: SessionUser }>('/auth/login', {
    method: 'POST', body: JSON.stringify({ email, password }),
  }),
  register: (payload: { full_name: string; email: string; password: string; role: 'korisnik' | 'oglasivac'; referral_code?: string }) => request<{ user: SessionUser }>('/auth/register', {
    method: 'POST', body: JSON.stringify(payload),
  }),
  logout: () => request<void>('/auth/logout', { method: 'POST' }),
  publicTasks: () => request<{ tasks: Task[] }>('/public/tasks'),
  userDashboard: () => request<UserDashboardData>('/user/dashboard'),
  submitProof: (taskId: number, proof: string) => request<{ submission: Submission }>(`/user/tasks/${taskId}/proof`, {
    method: 'POST', body: JSON.stringify({ proof }),
  }),
  requestWithdrawal: (payload: { amount_rsd: number; payment_method: string; payment_details: string }) => request<{ withdrawal: Withdrawal }>('/user/withdrawals', {
    method: 'POST', body: JSON.stringify(payload),
  }),
  saveProfile: (payload: { full_name: string; phone?: string; city?: string; payment_method?: string; payment_details?: string }) => request<{ user: SessionUser }>('/user/profile', {
    method: 'PUT', body: JSON.stringify(payload),
  }),
}
