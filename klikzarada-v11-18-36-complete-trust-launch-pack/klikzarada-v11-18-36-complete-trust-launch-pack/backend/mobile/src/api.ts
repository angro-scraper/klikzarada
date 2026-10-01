export type Account = {
  id: number; full_name: string; email: string; role: 'korisnik' | 'oglasivac' | 'admin';
  balance_rsd: number; pending_rsd: number; advertiser_budget_rsd: number;
  advertiser_reserved_rsd: number; email_verified: boolean; phone: string | null;
  city: string | null; payment_method: string | null; payment_details: string | null;
  referral_code: string | null;
};
export type TesterEnrollment = {
  id: number; task_id: number; user_id?: number; user_name?: string; account_email?: string | null;
  testing_email?: string; status: string; email_conflict?: boolean;
  created_at?: string | null; invited_at?: string | null;
};
export type TesterCheckin = {
  id: number; task_id: number; user_id?: number; task_title?: string; user_name?: string;
  day_number: number; note: string; reward_rsd: number; status: string;
  review_note: string | null; checked_in_at: string | null;
};
export type Task = {
  id: number; title: string; description: string; instructions: string; category: string;
  task_type: string; reward_rsd: number; estimated_minutes: number; status: string;
  proof_required: string; requires_tester_enrollment: boolean;
  tester_enrollment?: TesterEnrollment | null; tester_checkins?: TesterCheckin[];
  tester_progress?: { current_day: number; duration_days: number; can_check_in: boolean; complete: boolean };
  tester_daily_reward_rsd?: number; tester_daily_minutes?: number;
  target_url: string | null; submission_pending?: number; submission_approved?: number;
};
export type Submission = {
  id: number; task_id: number; user_id?: number; task_title: string; proof: string; status: string;
  reward_rsd: number; review_note: string | null; created_at: string | null; user_name?: string;
};
export type Notification = { id: number; title: string; body: string; status: string; created_at: string | null };
export type ChatInboxItem = { task_id: number; task_title: string; participant_id: number; participant_name: string; last_message: string; last_message_at: string | null };
export type ChatThread = { task_id: number; task_title: string; participant_id: number; participant_name: string; current_user_id: number; messages: Array<{ id: number; sender_id: number; body: string; created_at: string | null }> };
export type UserDashboard = { user: Account; tasks: Task[]; my_tasks: Task[]; submissions: Submission[]; min_withdrawal_rsd: number; withdrawals: Array<{ id: number; amount_rsd: number; status: string; created_at: string | null }> };
export type AdvertiserDashboard = { user: Account; tasks: Task[]; submissions: Submission[]; tester_enrollments: TesterEnrollment[]; tester_checkins: TesterCheckin[] };

export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}
async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api/ui${path}`, {
      ...init, credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', ...init.headers },
    });
  } catch {
    throw new ApiError('Nema veze sa serverom. Proveri internet i pokušaj ponovo.', 0);
  }
  if (response.status === 204) return undefined as T;
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof body.detail === 'string' ? body.detail : response.status >= 500 ? 'Server trenutno nije dostupan.' : 'Zahtev nije uspeo.';
    throw new ApiError(detail, response.status);
  }
  return body as T;
}
const json = (method: string, value: unknown): RequestInit => ({ method, body: JSON.stringify(value) });
export const api = {
  session: () => request<{ authenticated: boolean; user: Account | null }>('/session'),
  login: (email: string, password: string) => request<{ user: Account }>('/auth/login', json('POST', { email, password })),
  register: (value: { full_name: string; email: string; password: string; role: 'korisnik' | 'oglasivac'; accept_terms: boolean; referral_code?: string }) => request<{ user: Account }>('/auth/register', json('POST', value)),
  logout: () => request<void>('/auth/logout', { method: 'POST' }),
  resendVerification: () => request<{ queued: boolean; already_verified: boolean }>('/auth/email-verification/resend', { method: 'POST' }),
  publicTasks: () => request<{ tasks: Task[] }>('/public/tasks'),
  userDashboard: () => request<UserDashboard>('/user/dashboard'),
  advertiserDashboard: () => request<AdvertiserDashboard>('/advertiser/dashboard'),
  notifications: () => request<{ notifications: Notification[] }>('/notifications'),
  markNotificationRead: (id: number) => request(`/notifications/${id}/read`, { method: 'PATCH' }),
  chats: (role: 'korisnik' | 'oglasivac') => request<{ threads: ChatInboxItem[] }>(role === 'korisnik' ? '/user/task-chats' : '/advertiser/task-chats'),
  chat: (taskId: number, participantId: number) => request<ChatThread>(`/task-chat/${taskId}/${participantId}`),
  sendChat: (taskId: number, participantId: number, body: string) => request(`/task-chat/${taskId}/${participantId}`, json('POST', { body })),
  enrollTester: (taskId: number, testingEmail: string) => request<{ enrollment: TesterEnrollment }>(`/user/tasks/${taskId}/tester-enrollments`, json('POST', { testing_email: testingEmail })),
  checkIn: (taskId: number, note: string) => request<{ checkin: TesterCheckin }>(`/user/tasks/${taskId}/tester-checkins`, json('POST', { note })),
  decideEnrollment: (id: number, status: 'invited' | 'declined', note?: string) => request(`/advertiser/tester-enrollments/${id}`, json('PATCH', { status, note })),
  decideCheckin: (id: number, status: 'approved' | 'rejected', note?: string) => request(`/advertiser/tester-checkins/${id}`, json('PATCH', { status, note })),
  decideSubmission: (id: number, status: 'approved' | 'rejected' | 'needs_revision', note?: string) => request(`/advertiser/submissions/${id}`, json('PATCH', { status, note })),
  campaignLifecycle: (id: number, action: 'pause' | 'resume' | 'stop') => request(`/advertiser/campaigns/${id}/lifecycle`, json('PATCH', { action })),
  saveProfile: (value: { full_name: string; phone?: string; city?: string; payment_method?: string; payment_details?: string }) => request<{ user: Account }>('/user/profile', json('PUT', value)),
  withdraw: (value: { amount_rsd: number; payment_method: string; payment_details: string }) => request('/user/withdrawals', json('POST', value)),
};
