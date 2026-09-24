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
  phone: string | null
  city: string | null
  payment_method: string | null
  payment_details: string | null
  company_name: string | null
  company_pib: string | null
  company_website: string | null
  company_activity: string | null
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
  moderation_note: string | null
  target_city: string | null
  target_age_group: string | null
  target_interests: string | null
  sponsored?: boolean
  promotion_type?: 'featured' | 'priority' | null
  submission_total?: number
  submission_approved?: number
  submission_rejected?: number
  submission_pending?: number
  created_at: string | null
}

export type PublicOverview = {
  active_tasks: number
  categories: number
  active_advertisers: number
  approved_results: number
  average_minutes: number
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
  user_name?: string
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

export type AdvertiserDashboardData = {
  user: SessionUser
  tasks: Task[]
  submissions: Submission[]
  transactions: WalletTransaction[]
  pricing: AdvertisingPricing
}

export type AdvertisingPricing = {
  platform_fee_percent: number
  task_categories: string[]
  banner_price_basis_days: number
  banner_max_days: number
}

export type CampaignPayload = {
  title: string
  category: string
  task_type: string
  target_url?: string
  description: string
  instructions: string
  proof_required: string
  reward_rsd: number
  total_slots: number
  target_city?: string
  target_age_group?: string
  target_interests?: string
}

export type PayPalOrder = {
  order_id: string
  approval_url: string | null
  amount_rsd: number
  amount_eur: number
  exchange_rate: number
}

export type PayPalCheckoutConfig = {
  client_id: string
  currency: 'EUR'
  card_checkout_enabled: boolean
}

export type AdminMetrics = {
  users: number
  advertisers: number
  active_tasks: number
  pending_submissions: number
  pending_withdrawals: number
  pending_campaigns: number
  pending_banners: number
  pending_promotions?: number
  reserved_budget_rsd: number
}

export type AdminUser = SessionUser & { created_at: string | null }
export type AdminCampaign = Task & { advertiser_name: string }
export type AdminSubmission = Submission & { user_name: string }
export type AdminWithdrawal = Withdrawal & {
  user_name: string
  payment_details: string
  paypal_payout: null | {
    withdrawal_id: number
    paypal_batch_id: string | null
    sender_batch_id: string
    amount_rsd: number
    amount_paypal: number
    currency: string
    status: string
    created_at: string | null
    updated_at: string | null
  }
}
export type TaskSource = { id: number; name: string; endpoint_url: string; source_type: string; import_mode: string; status: string; has_api_key: boolean; last_sync_at: string | null; created_at: string | null }
export type SupportTicketMessage = { id: number; body: string; sender_name: string; from_support: boolean; created_at: string | null }
export type SupportTicket = { id: number; subject: string; category: string; priority: string; status: string; created_at: string | null; updated_at: string | null; user_name: string; messages: SupportTicketMessage[] }
export type AdminSetting = { key: string; value: string; has_value: boolean | null; description: string | null; sensitive: boolean }
export type PaidBanner = {
  id: number
  slot_id: number | null
  slot_title: string
  slot_code: string | null
  advertiser_id: number
  advertiser_name: string
  title: string
  body: string | null
  image_url: string | null
  target_url: string | null
  price_rsd: number
  days_count: number
  status: string
  admin_note: string | null
  starts_at: string | null
  ends_at: string | null
  views_count: number
  created_at: string | null
}
export type BannerSlot = {
  id: number
  code: string
  title: string
  placement: string
  width_label: string
  price_rsd: number
  is_active: boolean
  active_banner: PaidBanner | null
  pending_count: number
  schedule: PaidBanner[]
}
export type PaidPromotion = {
  id: number
  task_id: number | null
  task_title: string
  advertiser_id: number
  advertiser_name: string
  promotion_type: 'featured' | 'priority'
  price_rsd: number
  days_count: number
  status: string
  admin_note: string | null
  starts_at: string | null
  ends_at: string | null
  created_at: string | null
}
export type TaskVerification = {
  token: string
  status: 'started' | 'ready' | 'flagged' | 'submitted' | 'expired'
  required_seconds: number
  active_seconds: number
  activity_events: number
  risk_score: number
  remaining_seconds: number
}
export type FraudSignal = {
  id: number
  user_id: number | null
  user_name: string
  user_email: string | null
  signal_type: string
  risk_score: number
  status: string
  details: Record<string, unknown>
  created_at: string | null
}
export type FraudOverview = {
  policy: { daily_task_limit: number; daily_earnings_rsd: number; minimum_activity_events: number; ip_reputation_enabled: boolean }
  summary: { open_signals: number; high_risk_users: number; flagged_sessions: number; shared_devices: number }
  signals: FraudSignal[]
  sessions: Array<{ id: number; user_id: number; user_name: string; task_title: string; network: string | null; active_seconds: number; required_seconds: number; activity_events: number; focus_loss_count: number; risk_score: number; status: string; started_at: string | null }>
  devices: Array<{ id: number; user_id: number; user_name: string; network: string | null; device: string; last_seen_at: string | null }>
}

export function deviceFingerprint(): string {
  const key = 'klikzarada-device-id'
  let stableId = localStorage.getItem(key)
  if (!stableId) {
    stableId = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`
    localStorage.setItem(key, stableId)
  }
  const traits = [navigator.userAgent, navigator.language, screen.width, screen.height, Intl.DateTimeFormat().resolvedOptions().timeZone]
  return `${stableId}|${traits.join('|')}`.slice(0, 300)
}

type ApiErrorBody = { detail?: string }

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData
  const response = await fetch(`${API_ROOT}${path}`, {
    ...options,
    credentials: 'same-origin',
    headers: { ...(isFormData ? {} : { 'Content-Type': 'application/json' }), ...(options.headers ?? {}) },
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
  register: (payload: { full_name: string; email: string; password: string; role: 'korisnik' | 'oglasivac'; advertiser_type?: 'business' | 'private'; referral_code?: string; phone?: string; device_fingerprint?: string }) => request<{ user: SessionUser }>('/auth/register', {
    method: 'POST', body: JSON.stringify(payload),
  }),
  logout: () => request<void>('/auth/logout', { method: 'POST' }),
  publicTasks: () => request<{ tasks: Task[] }>('/public/tasks'),
  publicOverview: () => request<PublicOverview>('/public/overview'),
  publicBanners: () => request<{ banners: PaidBanner[] }>('/public/banners'),
  joinWaitlist: (email: string) => request<{ saved: boolean; already_registered: boolean }>('/public/waitlist', {
    method: 'POST', body: JSON.stringify({ email }),
  }),
  recordBannerImpression: (id: number) => request<void>(`/public/banners/${id}/impression`, { method: 'POST' }),
  userDashboard: () => request<UserDashboardData>('/user/dashboard'),
  startTaskVerification: (taskId: number, payload: { device_fingerprint: string; device_label?: string }) => request<{ session: TaskVerification; resumed: boolean }>(`/user/tasks/${taskId}/verification/start`, {
    method: 'POST', body: JSON.stringify(payload),
  }),
  taskVerificationHeartbeat: (payload: { token: string; activity_events: number; visible: boolean; focus_lost: boolean }) => request<{ session: TaskVerification }>('/user/tasks/verification/heartbeat', {
    method: 'POST', body: JSON.stringify(payload),
  }),
  submitProof: (taskId: number, proof: string, verificationToken: string) => request<{ submission: Submission }>(`/user/tasks/${taskId}/proof`, {
    method: 'POST', body: JSON.stringify({ proof, verification_token: verificationToken }),
  }),
  requestWithdrawal: (payload: { amount_rsd: number; payment_method: string; payment_details: string }) => request<{ withdrawal: Withdrawal }>('/user/withdrawals', {
    method: 'POST', body: JSON.stringify(payload),
  }),
  saveProfile: (payload: { full_name: string; phone?: string; city?: string; payment_method?: string; payment_details?: string; company_name?: string; company_pib?: string; company_website?: string; company_activity?: string }) => request<{ user: SessionUser }>('/user/profile', {
    method: 'PUT', body: JSON.stringify(payload),
  }),
  changePassword: (payload: { current_password: string; new_password: string }) => request<{ ok: true }>('/account/password', {
    method: 'PUT', body: JSON.stringify(payload),
  }),
  tickets: () => request<{ tickets: SupportTicket[] }>('/tickets'),
  createTicket: (payload: { subject: string; body: string; category?: string }) => request<{ ticket: SupportTicket }>('/tickets', {
    method: 'POST', body: JSON.stringify(payload),
  }),
  replyToTicket: (id: number, body: string) => request<{ ticket: SupportTicket }>(`/tickets/${id}/messages`, {
    method: 'POST', body: JSON.stringify({ body }),
  }),
  advertiserDashboard: () => request<AdvertiserDashboardData>('/advertiser/dashboard'),
  advertiserBanners: () => request<{ slots: BannerSlot[]; banners: PaidBanner[]; pricing: AdvertisingPricing }>('/advertiser/banners'),
  reserveAdvertiserBanner: (payload: { slot_id: number; title: string; body?: string; image_url?: string; target_url: string; days_count: number }) => request<{ banner: PaidBanner; reserved_rsd: number }>('/advertiser/banners', {
    method: 'POST', body: JSON.stringify(payload),
  }),
  uploadAdvertiserBanner: (file: File) => {
    const data = new FormData()
    data.append('file', file)
    return request<{ image_url: string; width: number; height: number; warning: string }>('/advertiser/banners/upload', { method: 'POST', body: data })
  },
  advertiserPromotions: () => request<{ promotions: PaidPromotion[]; prices: { featured_per_7_days_rsd: number; priority_per_7_days_rsd: number; max_days: number } }>('/advertiser/promotions'),
  reserveAdvertiserPromotion: (payload: { task_id: number; promotion_type: 'featured' | 'priority'; days_count: number }) => request<{ promotion: PaidPromotion; reserved_rsd: number }>('/advertiser/promotions', {
    method: 'POST', body: JSON.stringify(payload),
  }),
  createCampaign: (payload: CampaignPayload) => request<{ campaign: Task; reserved_rsd: number }>('/advertiser/campaigns', {
    method: 'POST', body: JSON.stringify(payload),
  }),
  reviseCampaign: (id: number, payload: CampaignPayload) => request<{ campaign: Task; reserved_rsd: number }>(`/advertiser/campaigns/${id}`, {
    method: 'PUT', body: JSON.stringify(payload),
  }),
  updateCampaignLifecycle: (id: number, action: 'pause' | 'resume') => request<{ campaign: Task }>(`/advertiser/campaigns/${id}/lifecycle`, {
    method: 'PATCH', body: JSON.stringify({ action }),
  }),
  reviewAdvertiserSubmission: (id: number, status: 'approved' | 'rejected', note?: string) => request<{ submission: Submission }>(`/advertiser/submissions/${id}`, {
    method: 'PATCH', body: JSON.stringify({ status, note }),
  }),
  createPayPalOrder: (amount_rsd: number, checkout_flow: 'redirect' | 'smart_button' = 'redirect') => request<PayPalOrder>('/advertiser/paypal/orders', {
    method: 'POST', body: JSON.stringify({ amount_rsd, checkout_flow }),
  }),
  paypalCheckoutConfig: () => request<PayPalCheckoutConfig>('/advertiser/paypal/checkout-config'),
  capturePayPalOrder: (orderId: string) => request<{ credited: boolean; advertiser_budget_rsd: number }>(`/advertiser/paypal/orders/${encodeURIComponent(orderId)}/capture`, {
    method: 'POST',
  }),
  adminDashboard: () => request<{ metrics: AdminMetrics }>('/admin/dashboard'),
  adminBanners: () => request<{ slots: BannerSlot[]; banners: PaidBanner[]; pricing: AdvertisingPricing }>('/admin/banners'),
  adminPromotions: () => request<{ promotions: PaidPromotion[] }>('/admin/promotions'),
  reviewAdminPromotion: (id: number, status: 'active' | 'rejected', note?: string) => request<{ promotion: PaidPromotion }>(`/admin/promotions/${id}`, {
    method: 'PATCH', body: JSON.stringify({ status, note }),
  }),
  reviewAdminBanner: (id: number, status: 'active' | 'rejected', note?: string) => request<{ banner: PaidBanner }>(`/admin/banners/${id}`, {
    method: 'PATCH', body: JSON.stringify({ status, note }),
  }),
  adminUsers: () => request<{ users: AdminUser[] }>('/admin/users'),
  updateAdminUser: (id: number, status: 'active' | 'blocked' | 'suspended', note?: string) => request<{ user: SessionUser }>(`/admin/users/${id}`, {
    method: 'PATCH', body: JSON.stringify({ status, note }),
  }),
  adminCampaigns: () => request<{ campaigns: AdminCampaign[] }>('/admin/campaigns'),
  updateAdminCampaign: (id: number, status: 'active' | 'rejected' | 'paused' | 'needs_revision', note?: string) => request<{ campaign: Task }>(`/admin/campaigns/${id}`, {
    method: 'PATCH', body: JSON.stringify({ status, note }),
  }),
  adminSubmissions: () => request<{ submissions: AdminSubmission[] }>('/admin/submissions'),
  reviewAdminSubmission: (id: number, status: 'approved' | 'rejected', note?: string) => request<{ submission: Submission }>(`/admin/submissions/${id}`, {
    method: 'PATCH', body: JSON.stringify({ status, note }),
  }),
  adminWithdrawals: () => request<{ withdrawals: AdminWithdrawal[] }>('/admin/withdrawals'),
  updateAdminWithdrawal: (id: number, status: 'paid' | 'rejected', note?: string) => request<{ withdrawal: Withdrawal }>(`/admin/withdrawals/${id}`, {
    method: 'PATCH', body: JSON.stringify({ status, note }),
  }),
  sendAdminPayPalPayout: (id: number) => request<{ withdrawal: Withdrawal; payout: AdminWithdrawal['paypal_payout'] }>(`/admin/withdrawals/${id}/paypal-payout`, {
    method: 'POST', body: JSON.stringify({ confirmation_code: `PAYPAL-ISPLATA-${id}` }),
  }),
  syncAdminPayPalPayout: (id: number) => request<{ withdrawal: Withdrawal; payout: AdminWithdrawal['paypal_payout'] }>(`/admin/withdrawals/${id}/paypal-payout/sync`, {
    method: 'POST',
  }),
  adminTickets: () => request<{ tickets: SupportTicket[] }>('/admin/tickets'),
  updateAdminTicket: (id: number, status: 'open' | 'waiting' | 'closed', note?: string) => request<{ ticket: SupportTicket }>(`/admin/tickets/${id}`, {
    method: 'PATCH', body: JSON.stringify({ status, note }),
  }),
  adminSettings: () => request<{ settings: AdminSetting[] }>('/admin/settings'),
  updateAdminSetting: (key: string, value: string) => request<{ setting: AdminSetting }>(`/admin/settings/${encodeURIComponent(key)}`, {
    method: 'PUT', body: JSON.stringify({ value }),
  }),
  adminTaskSources: () => request<{ sources: TaskSource[] }>('/admin/task-sources'),
  createTaskSource: (payload: { name: string; endpoint_url: string; api_key?: string; import_mode: 'review' | 'sync' | 'manual' }) => request<{ source: { id: number; name: string; status: string } }>('/admin/task-sources', {
    method: 'POST', body: JSON.stringify(payload),
  }),
  syncTaskSource: (id: number) => request<{ created: number; skipped: number; message: string }>(`/admin/task-sources/${id}/sync`, { method: 'POST' }),
  adminFraudOverview: () => request<FraudOverview>('/admin/fraud/overview'),
  reviewAdminFraudSignal: (id: number, status: 'reviewed' | 'dismissed', note?: string) => request<{ signal: { id: number; status: string } }>(`/admin/fraud/signals/${id}`, {
    method: 'PATCH', body: JSON.stringify({ status, note }),
  }),
}
