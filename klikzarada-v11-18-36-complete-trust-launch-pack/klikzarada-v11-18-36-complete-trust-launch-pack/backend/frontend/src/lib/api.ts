const API_ROOT = '/api/ui'

export type SessionUser = {
  id: number
  full_name: string
  email: string
  role: 'korisnik' | 'oglasivac' | 'admin'
  platform_publishing: boolean
  status: string
  level: string
  balance_rsd: number
  pending_rsd: number
  lifetime_earned_rsd: number
  phone: string | null
  email_verified: boolean
  phone_verified: boolean
  city: string | null
  city_needs_correction?: boolean
  age_group: string | null
  interests: string[]
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
  example_proof?: string | null
  advertiser_name?: string
  reward_rsd: number
  total_slots: number
  used_slots: number
  campaign_duration_days: number
  starts_at: string | null
  ends_at: string | null
  paused_at: string | null
  stopped_at: string | null
  estimated_minutes: number
  repeat_interval_hours: number
  submission_deadline_hours: number
  max_proof_revisions: number
  min_quality_score: number
  min_user_level: string
  featured: boolean
  requires_tester_enrollment: boolean
  tester_store?: 'ios' | 'android' | null
  tester_required_count: number
  tester_duration_days: number
  tester_daily_minutes: number
  tester_daily_reward_rsd: number
  tester_enrollment?: TesterEnrollment
  tester_checkins?: TesterDailyCheckin[]
  tester_progress?: TesterProgress
  verification_in_progress?: boolean
  tester_enrollment_total?: number
  tester_enrollment_requested?: number
  tester_enrollment_invited?: number
  tester_cohort_count?: number
  tester_checkin_total?: number
  tester_checkin_pending?: number
  tester_checkin_approved?: number
  platform_sponsored?: boolean
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
  submission_needs_revision?: number
  created_at: string | null
}

export type TesterEnrollment = {
  id: number
  task_id: number
  user_id?: number
  task_title?: string
  user_name?: string
  testing_email?: string
  account_email?: string | null
  email_conflict?: boolean
  status: string
  note: string | null
  cohort_number: number | null
  invited_at: string | null
  created_at: string | null
  updated_at: string | null
}

export type TesterDailyCheckin = {
  id: number
  user_id: number
  task_id: number
  task_title?: string
  user_name?: string
  day_number: number
  note: string
  reward_rsd: number
  status: string
  review_note: string | null
  revision_count: number
  revision_due_at: string | null
  reviewed_at: string | null
  checked_in_at: string | null
}

export type TesterProgress = {
  started: boolean
  started_at: string | null
  current_day: number
  days_elapsed: number
  duration_days: number
  checkin_total: number
  checked_days: number[]
  can_check_in: boolean
  complete: boolean
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
  user_id?: number
  task_id: number
  task_title: string
  proof: string
  status: string
  reward_rsd: number
  review_note: string | null
  revision_due_at?: string | null
  created_at: string | null
  user_name?: string
}

export type TaskChatMessage = {
  id: number
  sender_id: number
  body: string
  created_at: string | null
}

export type TaskChatThread = {
  task_id: number
  task_title: string
  participant_id: number
  participant_name: string
  current_user_id: number
  messages: TaskChatMessage[]
}

export type TaskChatInboxItem = {
  task_id: number
  task_title: string
  participant_id: number
  participant_name: string
  last_message: string
  last_message_at: string | null
}

export type WalletTransaction = {
  id: number
  amount_rsd: number
  tx_type: string
  description: string
  created_at: string | null
}

export type ProgramMission = {
  key: string
  title: string
  progress: number
  target: number
  reward_rsd: number
  accent: string
  eligible: boolean
  claimed: boolean
}

export type ProgramBadge = {
  key: string
  icon: string
  name: string
  description: string
  unlocked: boolean
}

export type UserProgram = {
  daily: {
    key: string
    reward_rsd: number
    eligible: boolean
    claimed: boolean
    streak: number
    week: Array<{ date: string; label: string; claimed: boolean; is_today: boolean }>
  }
  missions: ProgramMission[]
  badges: ProgramBadge[]
  stats: { submitted_total: number; approved_total: number }
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
  referral_earned_rsd: number
  referral_inviter_bonus_rsd: number
  referral_joiner_bonus_rsd: number
  tasks: Task[]
  my_tasks: Task[]
  submissions: Submission[]
  withdrawals: Withdrawal[]
  transactions: WalletTransaction[]
  program?: UserProgram
}

export type NotificationItem = {
  id: number
  title: string
  body: string
  status: string
  created_at: string | null
}

export type ProductionReadiness = {
  checks: Array<{ key: string; label: string; ready: boolean; action: string }>
  ready_count: number
  total: number
}

export type AdvertiserDashboardData = {
  user: SessionUser
  tasks: Task[]
  submissions: Submission[]
  tester_enrollments: TesterEnrollment[]
  tester_checkins: TesterDailyCheckin[]
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
  campaign_duration_days?: number
  target_city?: string
  target_age_group?: string
  target_interests?: string
  requires_tester_enrollment?: boolean
  tester_required_count?: number
  tester_duration_days?: number
  tester_daily_minutes?: number
  tester_daily_reward_rsd?: number
  repeat_interval_hours?: number
  submission_deadline_hours?: number
  max_proof_revisions?: number
  min_quality_score?: number
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

export type RegistrationFailureReason =
  | 'email_taken'
  | 'phone_taken'
  | 'terms_missing'
  | 'invalid_phone'
  | 'invalid_referral'
  | 'validation'
  | 'network_error'
  | 'server_error'
  | 'request_error'

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
  site_views_today: number
  site_unique_today: number
  site_views_7d: number
  site_unique_7d: number
  site_views_total: number
  site_unique_total: number
  site_active_now: number
  site_tracking_started_at: string | null
  site_daily: Array<{
    date: string
    views: number
    unique_visitors: number
  }>
  acquisition_funnel: {
    landings: number
    opened: number
    submitted: number
    failed: number
    completed: number
    conversion_rate: number
    failure_reasons: Array<{
      reason: RegistrationFailureReason
      label: string
      count: number
    }>
    sources: Array<{
      source: string
      medium: string
      campaign: string
      landings: number
      opened: number
      submitted: number
      failed: number
      completed: number
    }>
  }
}

export type AdminUser = SessionUser & { created_at: string | null }
export type AdminUserProfile = {
  user: AdminUser
  activity: {
    submissions_total: number
    submissions_pending: number
    submissions_approved: number
    submissions_rejected: number
    withdrawals_total: number
    withdrawals_pending: number
  }
}
export type AdminCampaign = Task & { advertiser_name: string; platform_fee_percent: number }
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
export type ContentRevision = {
  id: number
  entity_type: 'campaign' | 'banner'
  entity_id: number
  owner_id: number
  owner_name?: string
  changes: Record<string, string | null>
  current?: Record<string, string | null> | null
  status: 'pending' | 'approved' | 'rejected'
  admin_note: string | null
  created_at: string | null
  reviewed_at: string | null
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
  is_available_now: boolean
  next_available_at: string | null
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

type ApiErrorBody = { detail?: string | Array<{ msg?: string }> }

export class ApiRequestError extends Error {
  constructor(message: string, readonly status: number) {
    super(message)
    this.name = 'ApiRequestError'
  }
}

function apiErrorMessage(body: ApiErrorBody, status: number): string {
  if (status === 422) return 'Podaci u formi nisu ispravni. Proveri ime, email i lozinku.'
  if (typeof body.detail === 'string' && body.detail.trim()) return body.detail
  if (status >= 500) return 'Server trenutno nije dostupan. Pokušaj ponovo za trenutak.'
  return 'Zahtev nije uspeo. Pokušaj ponovo.'
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData
  let response: Response
  try {
    response = await fetch(`${API_ROOT}${path}`, {
      ...options,
      credentials: 'same-origin',
      headers: { ...(isFormData ? {} : { 'Content-Type': 'application/json' }), ...(options.headers ?? {}) },
    })
  } catch {
    throw new ApiRequestError('Veza sa serverom je prekinuta. Proveri internet i pokušaj ponovo.', 0)
  }

  if (response.status === 204) return undefined as T
  const body = await response.json().catch(() => ({} as ApiErrorBody))
  if (!response.ok) throw new ApiRequestError(apiErrorMessage(body as ApiErrorBody, response.status), response.status)
  return body as T
}

export const api = {
  session: () => request<{ authenticated: boolean; user: SessionUser | null }>('/session'),
  login: (email: string, password: string) => request<{ user: SessionUser }>('/auth/login', {
    method: 'POST', body: JSON.stringify({ email, password }),
  }),
  register: (payload: { full_name: string; email: string; password: string; role: 'korisnik' | 'oglasivac'; advertiser_type?: 'business' | 'private'; referral_code?: string; phone?: string; device_fingerprint?: string; accept_terms: boolean; website?: string }) => request<{ user: SessionUser }>('/auth/register', {
    method: 'POST', body: JSON.stringify(payload),
  }),
  logout: () => request<void>('/auth/logout', { method: 'POST' }),
  verifyEmail: (token: string) => request<{ verified: boolean }>('/auth/email-verification/confirm', {
    method: 'POST', body: JSON.stringify({ token }),
  }),
  resendEmailVerification: () => request<{ queued: boolean; delivered?: boolean; already_verified: boolean }>('/auth/email-verification/resend', { method: 'POST' }),
  requestPasswordReset: (email: string) => request<{ accepted: boolean }>('/auth/password-reset/request', {
    method: 'POST', body: JSON.stringify({ email }),
  }),
  confirmPasswordReset: (token: string, newPassword: string) => request<{ reset: boolean }>('/auth/password-reset/confirm', {
    method: 'POST', body: JSON.stringify({ token, new_password: newPassword }),
  }),
  publicTasks: () => request<{ tasks: Task[] }>('/public/tasks'),
  publicTask: (taskId: number) => request<{ task: Task }>(`/public/tasks/${taskId}`),
  publicOverview: () => request<PublicOverview>('/public/overview'),
  publicServiceTerms: () => request<{ min_withdrawal_rsd: number; wallet_currency: string; payout_destination: string; support_email: string; proof_review_deadline: string | null; withdrawal_processing_deadline: string | null }>('/public/service-terms'),
  publicAdvertisingInfo: () => request<{ platform_fee_percent: number; banner_price_basis_days: number; banner_max_days: number; slots: { id: number; title: string; placement: string; width_label: string; price_rsd: number }[] }>('/public/advertising-info'),
  publicBanners: () => request<{ banners: PaidBanner[] }>('/public/banners'),
  joinWaitlist: (email: string) => request<{ saved: boolean; already_registered: boolean }>('/public/waitlist', {
    method: 'POST', body: JSON.stringify({ email }),
  }),
  recordBannerImpression: (id: number) => request<void>(`/public/banners/${id}/impression`, { method: 'POST' }),
  userDashboard: () => request<UserDashboardData>('/user/dashboard'),
  claimProgramReward: (rewardKey: string) => request<{ claimed: boolean; reward_rsd: number; program: UserProgram }>(`/user/program/rewards/${encodeURIComponent(rewardKey)}`, {
    method: 'POST',
  }),
  completeUserOnboarding: (payload: { city?: string; age_group: string; interests: string[] }) => request<{ user: SessionUser; onboarding_complete: boolean }>('/user/onboarding', {
    method: 'POST', body: JSON.stringify(payload),
  }),
  notifications: () => request<{ notifications: NotificationItem[] }>('/notifications'),
  taskChat: (taskId: number, participantId: number) => request<TaskChatThread>(`/task-chat/${taskId}/${participantId}`),
  advertiserTaskChats: () => request<{ threads: TaskChatInboxItem[] }>('/advertiser/task-chats'),
  userTaskChats: () => request<{ threads: TaskChatInboxItem[] }>('/user/task-chats'),
  sendTaskChatMessage: (taskId: number, participantId: number, body: string) => request<{ message: TaskChatMessage }>(`/task-chat/${taskId}/${participantId}`, {
    method: 'POST', body: JSON.stringify({ body }),
  }),
  markNotificationRead: (id: number) => request<{ notification: NotificationItem }>(`/notifications/${id}/read`, { method: 'PATCH' }),
  startTaskVerification: (taskId: number, payload: { device_fingerprint: string; device_label?: string }) => request<{ session: TaskVerification; resumed: boolean }>(`/user/tasks/${taskId}/verification/start`, {
    method: 'POST', body: JSON.stringify(payload),
  }),
  taskVerificationHeartbeat: (payload: { token: string; activity_events: number; visible: boolean; focus_lost: boolean }) => request<{ session: TaskVerification }>('/user/tasks/verification/heartbeat', {
    method: 'POST', body: JSON.stringify(payload),
  }),
  submitProof: (taskId: number, proof: string, verificationToken: string) => request<{ submission: Submission }>(`/user/tasks/${taskId}/proof`, {
    method: 'POST', body: JSON.stringify({ proof, verification_token: verificationToken }),
  }),
  requestTesterEnrollment: (taskId: number, testingEmail: string) => request<{ enrollment: TesterEnrollment }>(`/user/tasks/${taskId}/tester-enrollments`, {
    method: 'POST', body: JSON.stringify({ testing_email: testingEmail }),
  }),
  createTesterCheckin: (taskId: number, note: string) => request<{ checkin: TesterDailyCheckin }>(`/user/tasks/${taskId}/tester-checkins`, {
    method: 'POST', body: JSON.stringify({ note }),
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
  reserveAdvertiserBanner: (payload: { slot_id: number; title: string; body?: string; image_url?: string; target_url?: string; days_count: number; requested_start_at?: string }) => request<{ banner: PaidBanner; reserved_rsd: number }>('/advertiser/banners', {
    method: 'POST', body: JSON.stringify(payload),
  }),
  updateAdvertiserBannerTarget: (id: number, targetUrl?: string) => request<{ banner: PaidBanner }>(`/advertiser/banners/${id}/target`, {
    method: 'PATCH', body: JSON.stringify({ target_url: targetUrl || null }),
  }),
  editAdvertiserBanner: (id: number, payload: { title: string; body?: string | null; image_url?: string | null; target_url?: string | null }) => request<{ banner: PaidBanner; revision: ContentRevision | null }>(`/advertiser/banners/${id}`, {
    method: 'PUT', body: JSON.stringify(payload),
  }),
  advertiserContentRevisions: () => request<{ revisions: ContentRevision[] }>('/advertiser/content-revisions'),
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
  editActiveCampaignContent: (id: number, payload: { title: string; description: string; instructions?: string; target_url?: string | null }) => request<{ campaign: Task; revision: ContentRevision }>(`/advertiser/campaigns/${id}/content`, {
    method: 'PUT', body: JSON.stringify(payload),
  }),
  updateCampaignLifecycle: (id: number, action: 'pause' | 'resume' | 'stop') => request<{ campaign: Task }>(`/advertiser/campaigns/${id}/lifecycle`, {
    method: 'PATCH', body: JSON.stringify({ action }),
  }),
  reviewAdvertiserSubmission: (id: number, status: 'approved' | 'rejected' | 'needs_revision', note?: string) => request<{ submission: Submission }>(`/advertiser/submissions/${id}`, {
    method: 'PATCH', body: JSON.stringify({ status, note }),
  }),
  updateTesterEnrollment: (id: number, status: 'invited' | 'declined', note?: string) => request<{ enrollment: TesterEnrollment }>(`/advertiser/tester-enrollments/${id}`, {
    method: 'PATCH', body: JSON.stringify({ status, note }),
  }),
  startTesterCohort: (taskId: number, count?: number) => request<{ cohort_number: number, activated_count: number, started_at: string, enrollments: TesterEnrollment[] }>(`/advertiser/tasks/${taskId}/tester-cohorts/start`, {
    method: 'POST', body: JSON.stringify(count ? { count } : {}),
  }),
  reviewTesterCheckin: (id: number, status: 'approved' | 'rejected', note?: string) => request<{ checkin: TesterDailyCheckin }>(`/advertiser/tester-checkins/${id}`, {
    method: 'PATCH', body: JSON.stringify({ status, note }),
  }),
  createPayPalOrder: (amount_rsd: number, checkout_flow: 'redirect' | 'smart_button' = 'redirect') => request<PayPalOrder>('/advertiser/paypal/orders', {
    method: 'POST', body: JSON.stringify({ amount_rsd, checkout_flow }),
  }),
  paypalCheckoutConfig: () => request<PayPalCheckoutConfig>('/advertiser/paypal/checkout-config'),
  capturePayPalOrder: (orderId: string) => request<{ credited: boolean; advertiser_budget_rsd: number }>(`/advertiser/paypal/orders/${encodeURIComponent(orderId)}/capture`, {
    method: 'POST',
  }),
  trackPublicFunnel: (eventType: 'registration_opened' | 'registration_submitted' | 'registration_failed', failureReason?: RegistrationFailureReason) => request<{ recorded: boolean }>('/analytics/funnel', {
    method: 'POST', body: JSON.stringify({ event_type: eventType, failure_reason: failureReason }),
  }),
  adminDashboard: () => request<{ metrics: AdminMetrics }>('/admin/dashboard'),
  resetAdminAnalytics: () => request<{ deleted: number; started_at: string; legacy_measurements_hidden: boolean }>('/admin/analytics/reset', { method: 'POST' }),
  adminProductionReadiness: () => request<ProductionReadiness>('/admin/production-readiness'),
  adminBanners: () => request<{ slots: BannerSlot[]; banners: PaidBanner[]; pricing: AdvertisingPricing }>('/admin/banners'),
  adminContentRevisions: () => request<{ revisions: ContentRevision[] }>('/admin/content-revisions'),
  reviewContentRevision: (id: number, status: 'approved' | 'rejected', note?: string) => request<{ revision: ContentRevision }>(`/admin/content-revisions/${id}`, {
    method: 'PATCH', body: JSON.stringify({ status, note }),
  }),
  adminPromotions: () => request<{ promotions: PaidPromotion[] }>('/admin/promotions'),
  reviewAdminPromotion: (id: number, status: 'active' | 'rejected', note?: string) => request<{ promotion: PaidPromotion }>(`/admin/promotions/${id}`, {
    method: 'PATCH', body: JSON.stringify({ status, note }),
  }),
  reviewAdminBanner: (id: number, status: 'active' | 'rejected', note?: string) => request<{ banner: PaidBanner }>(`/admin/banners/${id}`, {
    method: 'PATCH', body: JSON.stringify({ status, note }),
  }),
  adminUsers: () => request<{ users: AdminUser[] }>('/admin/users'),
  correctAccountRoleToUser: () => request<{ user: SessionUser }>('/account/role/correct-to-user', { method: 'POST' }),
  adminUserProfile: (id: number) => request<AdminUserProfile>(`/admin/users/${id}/profile`),
  updateAdminUser: (id: number, status: 'active' | 'blocked' | 'suspended', note?: string) => request<{ user: SessionUser }>(`/admin/users/${id}`, {
    method: 'PATCH', body: JSON.stringify({ status, note }),
  }),
  adminCampaigns: () => request<{ campaigns: AdminCampaign[] }>('/admin/campaigns'),
  updateAdminCampaign: (id: number, status: 'active' | 'rejected' | 'paused' | 'needs_revision' | 'stopped', note?: string) => request<{ campaign: Task }>(`/admin/campaigns/${id}`, {
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
