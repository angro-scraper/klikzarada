import { useEffect, useRef, useState } from 'react'
import { Sidebar, TopBar } from '../components/Sidebar'
import { Btn, Card, StatCard, SectionHeader, EmptyState, Table, StatusBadge, Tabs, Alert, Input } from '../components/ui'
import { PageHeader } from '../components/PageHeader'
import { ConfirmModal, InfoModal } from '../components/Modal'
import { useToast } from '../components/Toast'
import { api, deviceFingerprint, type NotificationItem, type SessionUser, type SupportTicket, type Task, type TaskVerification, type UserDashboardData } from '../lib/api'
import { type UserDashboardPage, userDashboardPageFromPath, userDashboardPath } from '../lib/userDashboardRoutes'

const navGroups = [
  { items: [
    { id: 'pregled', label: 'Pregled', icon: '📊' },
    { id: 'zadaci', label: 'Dostupni zadaci', icon: '📋' },
    { id: 'preporuke', label: 'Preporuke', icon: '✨' },
    { id: 'dokazi', label: 'Moji dokazi', icon: '✅' },
    { id: 'obavestenja', label: 'Obaveštenja', icon: '🔔' },
  ]},
  { group: 'Zarada', items: [
    { id: 'novcanik', label: 'Novčanik', icon: '💰' },
    { id: 'isplate', label: 'Isplate', icon: '🏦' },
    { id: 'podaci-isplata', label: 'Podaci za isplatu', icon: '🏧' },
  ]},
  { group: 'Program', items: [
    { id: 'nagrade', label: 'Dnevne nagrade', icon: '🎁' },
    { id: 'misije', label: 'Misije i bedževi', icon: '🏆' },
    { id: 'referral', label: 'Referral program', icon: '🔗' },
  ]},
  { group: 'Nalog', items: [
    { id: 'profil', label: 'Profil', icon: '⚙️' },
    { id: 'podrska', label: 'Podrška', icon: '💬' },
  ]},
]

type Page = UserDashboardPage

const BACK: Partial<Record<Page, { label: string; to: Page }>> = {
  zadaci:          { label: 'Nazad na pregled', to: 'pregled' },
  preporuke:       { label: 'Nazad na pregled', to: 'pregled' },
  dokazi:          { label: 'Nazad na pregled', to: 'pregled' },
  obavestenja:     { label: 'Nazad na pregled', to: 'pregled' },
  novcanik:        { label: 'Nazad na pregled', to: 'pregled' },
  isplate:         { label: 'Nazad na pregled', to: 'pregled' },
  'podaci-isplata':{ label: 'Nazad na isplate', to: 'isplate' },
  nagrade:         { label: 'Nazad na pregled', to: 'pregled' },
  misije:          { label: 'Nazad na pregled', to: 'pregled' },
  referral:        { label: 'Nazad na pregled', to: 'pregled' },
  profil:          { label: 'Nazad na pregled', to: 'pregled' },
  podrska:         { label: 'Nazad na pregled', to: 'pregled' },
  'zadatak-detalj':{ label: 'Nazad na zadatke', to: 'zadaci' },
}

const BREADCRUMBS: Partial<Record<Page, { label: string }[]>> = {
  zadaci:          [{ label: 'Korisnik' }, { label: 'Dostupni zadaci' }],
  preporuke:       [{ label: 'Korisnik' }, { label: 'Preporuke' }],
  dokazi:          [{ label: 'Korisnik' }, { label: 'Moji dokazi' }],
  obavestenja:     [{ label: 'Korisnik' }, { label: 'Obaveštenja' }],
  novcanik:        [{ label: 'Korisnik' }, { label: 'Novčanik' }],
  isplate:         [{ label: 'Korisnik' }, { label: 'Isplate' }],
  'podaci-isplata':[{ label: 'Korisnik' }, { label: 'Isplate' }, { label: 'Podaci za isplatu' }],
  nagrade:         [{ label: 'Korisnik' }, { label: 'Dnevne nagrade' }],
  misije:          [{ label: 'Korisnik' }, { label: 'Misije i bedževi' }],
  referral:        [{ label: 'Korisnik' }, { label: 'Referral program' }],
  profil:          [{ label: 'Korisnik' }, { label: 'Profil' }],
  podrska:         [{ label: 'Korisnik' }, { label: 'Podrška' }],
  'zadatak-detalj':[{ label: 'Korisnik' }, { label: 'Zadaci' }, { label: 'Detalj zadatka' }],
}

const categoryColor = (category: string) => {
  const colors = ['bg-blue-100 text-blue-700', 'bg-violet-100 text-violet-700', 'bg-teal-100 text-teal-700', 'bg-emerald-100 text-emerald-700']
  const total = [...category].reduce((sum, character) => sum + character.charCodeAt(0), 0)
  return colors[total % colors.length]
}

const formatRsd = (amount: number) => `${new Intl.NumberFormat('sr-RS', { maximumFractionDigits: 2 }).format(amount)} RSD`
const formatDate = (value: string | null) => value ? new Intl.DateTimeFormat('sr-RS').format(new Date(value)) : '—'

const textValue = (value: unknown, fallback = '') => typeof value === 'string' ? value : fallback
const numberValue = (value: unknown, fallback = 0) => typeof value === 'number' && Number.isFinite(value) ? value : fallback

function normalizeDashboard(data: UserDashboardData): UserDashboardData {
  const raw = (data && typeof data === 'object' ? data : {}) as Partial<UserDashboardData>
  const rawUser = (raw.user && typeof raw.user === 'object' ? raw.user : {}) as Partial<SessionUser>
  const tasks = Array.isArray(raw.tasks) ? raw.tasks.filter(Boolean).map((item) => {
    const task = item as Task
    return {
      ...task,
      id: numberValue(task.id),
      title: textValue(task.title, 'Zadatak'),
      category: textValue(task.category, 'Ostalo'),
      task_type: textValue(task.task_type, 'zadatak'),
      description: textValue(task.description),
      instructions: textValue(task.instructions),
      proof_required: textValue(task.proof_required, 'Dokaz potreban'),
      reward_rsd: numberValue(task.reward_rsd),
      estimated_minutes: numberValue(task.estimated_minutes),
      repeat_interval_hours: numberValue(task.repeat_interval_hours),
      submission_deadline_hours: numberValue(task.submission_deadline_hours, 24),
      max_proof_revisions: numberValue(task.max_proof_revisions, 1),
      min_quality_score: numberValue(task.min_quality_score),
      tester_daily_reward_rsd: numberValue(task.tester_daily_reward_rsd),
      requires_tester_enrollment: Boolean(task.requires_tester_enrollment),
    }
  }) : []

  return {
    ...raw,
    user: {
      ...rawUser,
      full_name: textValue(rawUser.full_name, 'Korisnik'),
      email: textValue(rawUser.email),
      role: rawUser.role || 'korisnik',
      level: textValue(rawUser.level, 'Bronza'),
      balance_rsd: numberValue(rawUser.balance_rsd),
      pending_rsd: numberValue(rawUser.pending_rsd),
      lifetime_earned_rsd: numberValue(rawUser.lifetime_earned_rsd),
      interests: Array.isArray(rawUser.interests) ? rawUser.interests.filter((item): item is string => typeof item === 'string') : [],
    } as SessionUser,
    min_withdrawal_rsd: numberValue(raw.min_withdrawal_rsd, 1000),
    referral_count: numberValue(raw.referral_count),
    tasks,
    submissions: Array.isArray(raw.submissions) ? raw.submissions : [],
    withdrawals: Array.isArray(raw.withdrawals) ? raw.withdrawals : [],
    transactions: Array.isArray(raw.transactions) ? raw.transactions : [],
  }
}

export default function UserDashboard({ initialPage = 'pregled', onNavigate }: { initialPage?: UserDashboardPage; onNavigate: (id: string) => void }) {
  const [page, setPage] = useState<Page>(initialPage)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [proofTab, setProofTab] = useState('svi')
  const [confirmPayout, setConfirmPayout] = useState(false)
  const [submitProofModal, setSubmitProofModal] = useState<number | null>(null)
  const [selectedTaskId, setSelectedTaskId] = useState<number | null>(null)
  const [logoutConfirm, setLogoutConfirm] = useState(false)
  const [advertiserWorkspaceConfirm, setAdvertiserWorkspaceConfirm] = useState(false)
  const [dashboard, setDashboard] = useState<UserDashboardData | null>(null)
  const [dashboardError, setDashboardError] = useState('')
  const [proofText, setProofText] = useState('')
  const [testerEmail, setTesterEmail] = useState('')
  const [testerCheckinNote, setTesterCheckinNote] = useState('')
  const [verification, setVerification] = useState<TaskVerification | null>(null)
  const [payoutAmount, setPayoutAmount] = useState('')
  const [paymentMethod, setPaymentMethod] = useState('PayPal')
  const [paymentDetails, setPaymentDetails] = useState('')
  const [profileName, setProfileName] = useState('')
  const [profilePhone, setProfilePhone] = useState('')
  const [profileCity, setProfileCity] = useState('')
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [repeatPassword, setRepeatPassword] = useState('')
  const [saving, setSaving] = useState(false)
  const [tickets, setTickets] = useState<SupportTicket[]>([])
  const [notifications, setNotifications] = useState<NotificationItem[]>([])
  const [onboardingAge, setOnboardingAge] = useState('')
  const [onboardingInterests, setOnboardingInterests] = useState<string[]>([])
  const [ticketSubject, setTicketSubject] = useState('')
  const [ticketBody, setTicketBody] = useState('')
  const activityEvents = useRef(0)
  const focusLost = useRef(false)
  const { show: showToast, node: toastNode } = useToast()

  const refreshDashboard = async () => {
    try {
      const [data, ticketData, notificationData] = await Promise.all([api.userDashboard(), api.tickets(), api.notifications()])
      const safeDashboard = normalizeDashboard(data)
      setDashboard(safeDashboard)
      setTickets(Array.isArray(ticketData?.tickets) ? ticketData.tickets : [])
      setNotifications(Array.isArray(notificationData?.notifications) ? notificationData.notifications : [])
      setPaymentMethod('PayPal')
      setPaymentDetails(safeDashboard.user.payment_details || '')
      setProfileName(safeDashboard.user.full_name)
      setProfilePhone(safeDashboard.user.phone || '')
      setProfileCity(safeDashboard.user.city || '')
      setOnboardingAge(safeDashboard.user.age_group || '')
      setOnboardingInterests(safeDashboard.user.interests || [])
      setDashboardError('')
    } catch (error) {
      setDashboardError(error instanceof Error ? error.message : 'Podaci trenutno nisu dostupni.')
    }
  }

  useEffect(() => { void refreshDashboard() }, [])

  useEffect(() => { setPage(initialPage) }, [initialPage])

  useEffect(() => {
    if (!verification || submitProofModal === null || verification.active_seconds >= verification.required_seconds) return
    const countActivity = () => { activityEvents.current += 1 }
    const markFocusLoss = () => { focusLost.current = true }
    document.addEventListener('pointerdown', countActivity)
    document.addEventListener('pointermove', countActivity)
    document.addEventListener('keydown', countActivity)
    document.addEventListener('scroll', countActivity, { passive: true })
    window.addEventListener('blur', markFocusLoss)

    let disposed = false
    const heartbeat = async () => {
      const events = activityEvents.current
      const lostFocus = focusLost.current || document.visibilityState !== 'visible'
      activityEvents.current = 0
      focusLost.current = false
      try {
        const result = await api.taskVerificationHeartbeat({
          token: verification.token,
          activity_events: events,
          visible: document.visibilityState === 'visible',
          focus_lost: lostFocus,
        })
        if (!disposed) setVerification(result.session)
      } catch (error) {
        if (!disposed) showToast(error instanceof Error ? error.message : 'Provera zadatka je prekinuta.', 'error')
      }
    }
    const interval = window.setInterval(() => { void heartbeat() }, 10_000)
    return () => {
      disposed = true
      window.clearInterval(interval)
      document.removeEventListener('pointerdown', countActivity)
      document.removeEventListener('pointermove', countActivity)
      document.removeEventListener('keydown', countActivity)
      document.removeEventListener('scroll', countActivity)
      window.removeEventListener('blur', markFocusLoss)
    }
  }, [verification?.token, verification?.active_seconds, verification?.required_seconds, submitProofModal])

  const user: SessionUser | undefined = dashboard?.user
  const activeTasks: Task[] = dashboard?.tasks ?? []
  const proofCount = dashboard?.submissions?.length ?? 0
  const program = dashboard?.program
  const dailyReward = program?.daily
  const programMissions = program?.missions ?? []
  const programBadges = program?.badges ?? []
  const approvedProofCount = program?.stats.approved_total ?? 0
  const visibleProofs = (dashboard?.submissions ?? []).filter(proof => proofTab === 'svi' || proof.status === proofTab)
  const navigationGroups = navGroups.map(group => ({
    ...group,
    items: group.items.map(item => item.id === 'dokazi' ? { ...item, badge: proofCount || undefined } : item),
  }))
  const balance = user?.balance_rsd ?? 0
  const minWithdrawal = dashboard?.min_withdrawal_rsd ?? 1000
  const payoutGap = Math.max(0, minWithdrawal - balance)
  const selectedTask = activeTasks.find(task => task.id === selectedTaskId || task.id === submitProofModal)
  const selectedTesterProgress = selectedTask?.tester_progress
  const selectedTaskRevision = selectedTask ? (dashboard?.submissions ?? []).find(submission => submission.task_id === selectedTask.id && submission.status === 'needs_revision') : undefined

  async function claimProgramReward(rewardKey: string) {
    setSaving(true)
    try {
      const result = await api.claimProgramReward(rewardKey)
      await refreshDashboard()
      showToast(`Dodato je ${formatRsd(result.reward_rsd)} na raspoloživi saldo.`, 'success')
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Nagrada nije preuzeta.', 'error')
    } finally {
      setSaving(false)
    }
  }

  function goTo(p: Page) {
    setPage(p)
    const path = userDashboardPath(p)
    if (path && window.location.pathname !== path) window.history.pushState({}, '', path)
    window.scrollTo(0, 0)
  }

  async function beginTaskVerification(task: Task) {
    setSaving(true)
    try {
      const result = await api.startTaskVerification(task.id, {
        device_fingerprint: deviceFingerprint(),
        device_label: `${navigator.platform || 'Web'} · ${screen.width}x${screen.height}`,
      })
      activityEvents.current = 0
      focusLost.current = false
      setVerification(result.session)
      setProofText('')
      setSubmitProofModal(task.id)
      showToast(result.resumed ? 'Nastavljena je postojeća provera zadatka.' : 'Provera zadatka je pokrenuta. Ostani aktivan/na dok se timer ne završi.', 'info')
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Provera zadatka nije pokrenuta.', 'error')
    } finally {
      setSaving(false)
    }
  }

  async function requestTesterAccess(task: Task) {
    if (!testerEmail.trim()) {
      showToast('Unesi email naloga koji koristiš za pristup testiranju.', 'error')
      return
    }
    setSaving(true)
    try {
      await api.requestTesterEnrollment(task.id, testerEmail)
      await refreshDashboard()
      showToast('Prijava je poslata oglašivaču. Dobićeš obaveštenje kada te doda u test.', 'success')
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Prijava za testiranje nije poslata.', 'error')
    } finally {
      setSaving(false)
    }
  }

  async function submitTesterCheckin(task: Task) {
    if (testerCheckinNote.trim().length < 3) {
      showToast('Napiši kratko šta si danas testirao/la i da li si primetio/la problem.', 'error')
      return
    }
    setSaving(true)
    try {
      await api.createTesterCheckin(task.id, testerCheckinNote)
      setTesterCheckinNote('')
      await refreshDashboard()
      showToast('Dnevni izveštaj je poslat oglašivaču na odobrenje.', 'success')
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Dnevni izveštaj nije poslat.', 'error')
    } finally {
      setSaving(false)
    }
  }
  const back = BACK[page]
  const crumbs = BREADCRUMBS[page]

  const sidebarFooter = (
    <div className="flex items-center gap-2.5">
      <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm font-bold">{user?.full_name?.slice(0, 1).toUpperCase() || 'K'}</div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-white truncate">{user?.full_name || 'Učitavanje...'}</p>
        <p className="text-xs" style={{ color: '#9AB1C8' }}>🧭 {user?.level || 'Bronza'}</p>
      </div>
      <button
        onClick={() => setLogoutConfirm(true)}
        className="text-xs px-2 py-1 rounded hover:bg-white/10 cursor-pointer font-medium"
        style={{ color: '#B9CDE0' }}
        title="Odjavi se"
      >
        Odjava
      </button>
    </div>
  )

  return (
    <div className="flex h-screen bg-mint-50 text-ink overflow-hidden">
      {toastNode}

      {/* Logout confirm */}
      <ConfirmModal
        open={logoutConfirm}
        title="Odjaviti se?"
        description="Bićeš odjavljen/a sa KlikZarada platforme."
        confirmLabel="Da, odjavi me"
        cancelLabel="Otkaži"
        variant="danger"
        onConfirm={async () => {
          try {
            await api.logout()
          } finally {
            onNavigate('home')
          }
        }}
        onCancel={() => setLogoutConfirm(false)}
      />

      {/* Payout confirm */}
      <ConfirmModal
        open={confirmPayout}
        title="Zatražiti isplatu?"
        description={`Iznos od ${formatRsd(Number(payoutAmount) || balance)} biće prosleđen na tvoj PayPal e-mail. Zahtev prvo prolazi administrativnu proveru.`}
        confirmLabel="Zatraži isplatu"
        cancelLabel="Otkaži"
        variant="success"
        onConfirm={async () => {
          const amount = Number(payoutAmount) || balance
          if (!paymentDetails.trim()) {
            showToast('Unesi PayPal e-mail adresu pre slanja zahteva.', 'error')
            return
          }
          setSaving(true)
          try {
            await api.requestWithdrawal({ amount_rsd: amount, payment_method: paymentMethod, payment_details: paymentDetails })
            await refreshDashboard()
            setConfirmPayout(false)
            setPayoutAmount('')
            showToast('Zahtev za isplatu je poslat na administrativnu obradu.', 'success')
          } catch (error) {
            showToast(error instanceof Error ? error.message : 'Zahtev nije poslat.', 'error')
          } finally {
            setSaving(false)
          }
        }}
        onCancel={() => setConfirmPayout(false)}
      />

      {/* Submit proof modal */}
      <InfoModal
        open={submitProofModal !== null}
        title="Provera zadatka i dokaz"
        onClose={() => { setSubmitProofModal(null); setVerification(null) }}
      >
        {submitProofModal !== null && (
          <div className="space-y-3">
            <p className="text-sm text-ink-2">{selectedTask ? `Dokaz za: ${selectedTask.title}` : 'Pošalji dokaz izvršenja zadatka.'}</p>
            {selectedTaskRevision && <Alert type="warning"><strong>Potrebna je dorada:</strong> {selectedTaskRevision.review_note || 'Dopuni dokaz prema zahtevu oglašivača.'}{selectedTaskRevision.revision_due_at ? ` Rok: ${formatDate(selectedTaskRevision.revision_due_at)}.` : ''}</Alert>}
            {verification && (
              <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 space-y-2">
                <div className="flex items-center justify-between gap-3">
                  <p className="font-bold text-ink text-sm">🛡️ Provera aktivnosti</p>
                  <span className="font-mono text-sm font-bold text-blue-700">{verification.active_seconds}/{verification.required_seconds} s</span>
                </div>
                <div className="h-2 rounded-full bg-blue-100 overflow-hidden">
                  <div className="h-full rounded-full bg-blue-600 transition-all" style={{ width: `${Math.min(100, (verification.active_seconds / verification.required_seconds) * 100)}%` }} />
                </div>
                {verification.active_seconds < verification.required_seconds ? (
                  <p className="text-xs text-blue-800">Ostani na zadatku i povremeno pomeri miš, skroluj ili koristi tastaturu. Timer računa samo serverom potvrđeno vreme.</p>
                ) : (
                  <p className="text-xs text-emerald-700 font-semibold">Provera vremena je završena. Sada možeš poslati dokaz oglašivaču kampanje.</p>
                )}
                {verification.status === 'flagged' && <p className="text-xs text-amber-800">Ovaj zadatak će pre odobrenja proći dodatnu fraud proveru.</p>}
              </div>
            )}
            {!verification && <Alert type="warning">Pokreni proveru zadatka pre slanja dokaza.</Alert>}
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-bold text-ink-2 uppercase tracking-wide">Link ili opis dokaza</label>
              <textarea disabled={!verification || verification.active_seconds < verification.required_seconds} value={proofText} onChange={event => setProofText(event.target.value)} rows={4} placeholder="Nalepi javni link do screenshota ili napiši gde oglašivač može da proveri izvršenje." className="bg-white border border-frame text-ink rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none resize-y disabled:bg-gray-100 disabled:text-ink-3" />
              <p className="text-xs text-ink-3">Dokaz i nagrada prvo idu na čekanje. Oglašivač kampanje odobrava rezultat, a admin rešava samo sporove i fraud slučajeve.</p>
            </div>
            <Btn
              variant="success"
              className="w-full justify-center"
              disabled={saving || !proofText.trim() || !verification || verification.active_seconds < verification.required_seconds}
              onClick={async () => {
                if (!verification) return
                setSaving(true)
                try {
                  await api.submitProof(submitProofModal, proofText, verification.token)
                  await refreshDashboard()
                  setProofText('')
                  setSubmitProofModal(null)
                  setVerification(null)
                  showToast('Dokaz je poslat i čeka pregled.', 'success')
                } catch (error) {
                  showToast(error instanceof Error ? error.message : 'Dokaz nije poslat.', 'error')
                } finally {
                  setSaving(false)
                }
              }}
            >
              {saving ? 'Slanje...' : verification && verification.active_seconds < verification.required_seconds ? 'Sačekaj proveru vremena' : selectedTaskRevision ? 'Pošalji dopunjen dokaz' : 'Pošalji dokaz na proveru'}
            </Btn>
          </div>
        )}
      </InfoModal>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 bg-black/40 z-40 lg:hidden" onClick={() => setMobileOpen(false)} />
      )}

      <div className="hidden lg:flex shrink-0">
        <Sidebar groups={navigationGroups} active={page} onNavigate={p => goTo(p as Page)} footer={sidebarFooter} />
      </div>
      {mobileOpen && (
        <div className="fixed left-0 top-0 h-full z-50 lg:hidden">
          <Sidebar
            groups={navigationGroups}
            active={page}
            onNavigate={p => { goTo(p as Page); setMobileOpen(false) }}
            footer={sidebarFooter}
            isMobile
            onClose={() => setMobileOpen(false)}
          />
        </div>
      )}

      <div className="flex-1 min-w-0 flex flex-col overflow-hidden">
        <ConfirmModal
          open={advertiserWorkspaceConfirm}
          title="Uključiti oglašivački prostor?"
          description="Ne otvara se novi nalog: kampanje, aktivacije testera i tvoji zadaci ostaju povezani sa ovim istim nalogom."
          confirmLabel="Uključi oglašavanje"
          cancelLabel="Otkaži"
          variant="success"
          onConfirm={async () => {
            try {
              await api.enableAdvertiserWorkspace()
              setAdvertiserWorkspaceConfirm(false)
              onNavigate('advertiser')
            } catch (error) {
              showToast(error instanceof Error ? error.message : 'Oglašivački prostor nije uključen.', 'error')
            }
          }}
          onCancel={() => setAdvertiserWorkspaceConfirm(false)}
        />
        <TopBar
          onMenuClick={() => setMobileOpen(true)}
          pageTitle="Zarada centar"
          onNavigate={onNavigate}
          actions={
            <div className="flex items-center gap-3">
              {user?.role === 'korisnik' && <Btn variant="secondary" size="sm" onClick={() => setAdvertiserWorkspaceConfirm(true)} className="hidden sm:inline-flex">Oglašavanje</Btn>}
              <div className="text-right hidden sm:block">
                <p className="font-mono text-sm font-bold text-emerald-600">{formatRsd(balance)}</p>
                <p className="text-[10px] text-ink-3">Balans</p>
              </div>
              <Btn variant="success" size="sm" onClick={() => goTo('isplate')}>💸 Isplati</Btn>
            </div>
          }
        />

        <main className="flex-1 overflow-y-auto bg-mint-50">
          <div className="w-full max-w-none px-4 py-6 sm:px-6 xl:px-8 2xl:px-10">
            {dashboardError && <div className="mb-4"><Alert type="error">{dashboardError}</Alert></div>}
            {/* Back + breadcrumb */}
            {page !== 'pregled' && (back || crumbs) && (
              <PageHeader
                breadcrumbs={crumbs}
                onBack={back ? () => goTo(back.to) : undefined}
                backLabel={back?.label}
              />
            )}

            {/* ── PREGLED ── */}
            {page === 'pregled' && (
              <div className="space-y-5">
                <div>
                  <h1 className="text-xl font-extrabold text-ink">Dobrodošao/la, {user?.full_name || 'korisniče'}! 👋</h1>
                  <p className="text-sm text-ink-2 mt-0.5">Pregled stvarnog stanja tvog KlikZarada naloga.</p>
                </div>
                {user && (!user.age_group || user.interests.length === 0) && (
                  <Card className="p-5 border-blue-200 bg-blue-50">
                    <p className="font-bold text-ink">Završi kratak profil</p>
                    <p className="text-sm text-ink-2 mt-1">Ovi podaci služe samo za relevantnije zadatke i ne prikazuju se oglašivačima kao lični podaci.</p>
                    <div className="grid gap-3 mt-4 sm:grid-cols-2">
                      <select value={onboardingAge} onChange={event => setOnboardingAge(event.target.value)} className="bg-white border border-frame text-ink rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none">
                        <option value="">Starosna grupa</option>
                        {['18-24', '25-34', '35-44', '45-54', '55+'].map(age => <option key={age} value={age}>{age}</option>)}
                      </select>
                      <div className="flex flex-wrap gap-2">
                        {['Kupovina', 'Tehnologija', 'Hrana', 'Putovanja', 'Finansije', 'Zabava'].map(interest => <button key={interest} type="button" onClick={() => setOnboardingInterests(current => current.includes(interest) ? current.filter(item => item !== interest) : [...current, interest])} className={`rounded-full border px-3 py-1 text-xs font-semibold ${onboardingInterests.includes(interest) ? 'border-blue-600 bg-blue-600 text-white' : 'border-blue-200 bg-white text-blue-700'}`}>{interest}</button>)}
                      </div>
                    </div>
                    <Btn size="sm" className="mt-4" disabled={saving || !onboardingAge || onboardingInterests.length === 0} onClick={() => void (async () => { try { setSaving(true); await api.completeUserOnboarding({ city: profileCity || undefined, age_group: onboardingAge, interests: onboardingInterests }); await refreshDashboard(); showToast('Profil za preporuke je sačuvan.', 'success') } catch (error) { showToast(error instanceof Error ? error.message : 'Profil nije sačuvan.', 'error') } finally { setSaving(false) } })()}>Sačuvaj preporuke</Btn>
                  </Card>
                )}
                {notifications.some(item => item.status === 'unread') && <Alert type="info">Imaš {notifications.filter(item => item.status === 'unread').length} novo obaveštenje. <button onClick={() => goTo('obavestenja')} className="font-bold underline">Otvori obaveštenja</button></Alert>}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                  <StatCard label="Ukupan balans" value={formatRsd(balance)} icon="💰" accent="green" />
                  <StatCard label="Na čekanju" value={formatRsd(user?.pending_rsd ?? 0)} icon="⏳" accent="teal" />
                  <StatCard label="Dostupni zadaci" value={String(activeTasks.length)} icon="✅" accent="blue" />
                  <StatCard label="Do isplate" value={formatRsd(payoutGap)} sub={`Min. ${formatRsd(minWithdrawal)}`} icon="🏦" accent="orange" />
                </div>

                {/* Daily reward */}
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-5 flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <span className="text-3xl">🎁</span>
                    <div>
                      <p className="font-bold text-ink">Dnevna nagrada</p>
                      <p className="text-sm text-amber-700">{dailyReward?.claimed ? 'Današnja nagrada je preuzeta.' : dailyReward?.eligible ? `Dostupno ${formatRsd(dailyReward.reward_rsd)} nakon današnje aktivnosti.` : 'Pošalji prvi stvarni dokaz danas da otključaš nagradu.'}</p>
                    </div>
                  </div>
                  <Btn size="sm" variant={dailyReward?.eligible && !dailyReward.claimed ? 'success' : 'secondary'} disabled={saving || !dailyReward?.eligible || dailyReward.claimed} onClick={() => dailyReward?.eligible ? void claimProgramReward(dailyReward.key) : goTo('zadaci')}>
                    {dailyReward?.claimed ? 'Preuzeto' : dailyReward?.eligible ? `Preuzmi ${formatRsd(dailyReward.reward_rsd)}` : 'Pogledaj zadatke'}
                  </Btn>
                </div>

                {/* Tier */}
                <Card className="p-5">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <p className="text-sm font-bold text-ink">Nivo: <span className="text-blue-600">{user?.level || 'Bronza'} 🧭</span></p>
                      <p className="text-xs text-ink-3 mt-0.5">Nivoi i značke se računaju iz odobrenih dokaza.</p>
                    </div>
                  </div>
                  <div className="flex gap-2 mb-3">
                    {programBadges.slice(1).map(badge => (
                      <div key={badge.key} className={`flex-1 text-center text-xs py-1.5 rounded-lg font-semibold ${badge.unlocked ? 'bg-blue-600 text-white' : 'bg-gray-100 text-ink-3'}`}>
                        {badge.icon} <span className="hidden sm:inline">{badge.name}</span>
                      </div>
                    ))}
                  </div>
                  <div className="bg-gray-100 rounded-full h-1.5 mb-1">
                    <div className="bg-blue-600 h-1.5 rounded-full" style={{ width: `${Math.min(100, (approvedProofCount / 20) * 100)}%` }} />
                  </div>
                  <p className="text-xs text-ink-3">{approvedProofCount} od 20 odobrenih dokaza</p>
                </Card>

                {/* Priority tasks */}
                <div>
                  <SectionHeader title="Preporučeni zadaci" action={<Btn onClick={() => goTo('zadaci')} variant="ghost" size="sm">Svi zadaci →</Btn>} />
                  <div className="flex flex-col gap-2">
                    {activeTasks.slice(0, 3).map(t => (
                      <Card key={t.id} className="p-4 flex items-center gap-4 hover:shadow-md transition-shadow">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${categoryColor(t.category)}`}>{t.category}</span>
                            <span className="text-[11px] text-ink-3">⏱ {t.estimated_minutes} min</span>
                          </div>
                          <p className="font-semibold text-ink text-sm truncate">{t.title}</p>
                        </div>
                        <div className="flex items-center gap-3 shrink-0">
                          <span className="font-mono font-bold text-emerald-600">{t.requires_tester_enrollment ? `${formatRsd(t.tester_daily_reward_rsd)}/dan` : formatRsd(t.reward_rsd)}</span>
                          <Btn size="sm" onClick={() => { setSelectedTaskId(t.id); goTo('zadatak-detalj') }}>Detalji</Btn>
                        </div>
                      </Card>
                    ))}
                  </div>
                </div>

                {/* Referral */}
                <div className="bg-violet-50 border border-violet-200 rounded-xl p-5 flex items-start justify-between gap-4">
                  <div>
                    <p className="font-bold text-ink">🔗 Referral program</p>
                    <p className="text-sm text-violet-700 mt-0.5">Ti: <span className="font-mono font-bold">+100 RSD</span> · Prijatelj: <span className="font-mono font-bold">+50 RSD</span></p>
                    <p className="text-xs text-ink-3 mt-1">Pozvano: <strong className="text-ink">{dashboard?.referral_count ?? 0}</strong> korisnika</p>
                  </div>
                  <Btn onClick={() => goTo('referral')} variant="premium" size="sm">Podeli link</Btn>
                </div>
              </div>
            )}

            {/* ── OBAVEŠTENJA ── */}
            {page === 'obavestenja' && (
              <div className="space-y-4">
                <SectionHeader title="Obaveštenja" description="Promene statusa zadataka, tiketa i bezbednosne poruke." />
                {notifications.length === 0 ? <EmptyState icon="🔔" title="Nema obaveštenja" description="Kad se nešto promeni na nalogu, videćeš to ovde." /> : notifications.map(item => <Card key={item.id} className={`p-4 ${item.status === 'unread' ? 'border-blue-200 bg-blue-50' : ''}`}><div className="flex items-start justify-between gap-4"><div><p className="font-bold text-ink">{item.title}</p><p className="text-sm text-ink-2 mt-1">{item.body}</p><p className="text-xs text-ink-3 mt-2">{formatDate(item.created_at)}</p></div>{item.status === 'unread' && <Btn size="sm" variant="secondary" onClick={() => void (async () => { try { await api.markNotificationRead(item.id); await refreshDashboard() } catch (error) { showToast(error instanceof Error ? error.message : 'Obaveštenje nije ažurirano.', 'error') } })()}>Pročitano</Btn>}</div></Card>)}
              </div>
            )}

            {/* ── ZADACI ── */}
            {page === 'zadaci' && (
              <div>
                <SectionHeader title="Dostupni zadaci" description="Preuzmi zadatak, izvrši ga i pošalji dokaz." />
                <div className="flex flex-col gap-3">
                  {activeTasks.map(t => (
                    <Card key={t.id} className="p-5 hover:shadow-md transition-shadow">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex flex-wrap gap-2 mb-2">
                            <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${categoryColor(t.category)}`}>{t.category}</span>
                            {t.requires_tester_enrollment && <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800">Zatvoreni beta test</span>}
                            <StatusBadge status="aktivno" />
                          </div>
                          <h3 className="font-semibold text-ink">{t.title}</h3>
                          <p className="text-xs text-ink-3 mt-1">⏱ {t.estimated_minutes} min · 📎 {t.proof_required || 'Dokaz potreban'}</p>
                        </div>
                        <div className="text-right shrink-0">
                          <p className="font-mono font-bold text-emerald-600 text-lg">{t.requires_tester_enrollment ? `${formatRsd(t.tester_daily_reward_rsd)}/dan` : formatRsd(t.reward_rsd)}</p>
                          <Btn size="sm" className="mt-2" onClick={() => { setSelectedTaskId(t.id); goTo('zadatak-detalj') }}>Detalji →</Btn>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              </div>
            )}

            {/* ── ZADATAK DETALJ ── */}
            {page === 'zadatak-detalj' && (
              <div>
                <SectionHeader title={selectedTask?.title || 'Detalj zadatka'} />
                <Card className="p-5 space-y-4">
                  <div className="flex flex-wrap gap-2">
                    <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${categoryColor(selectedTask?.category || '')}`}>{selectedTask?.category || 'Zadatak'}</span>
                    <StatusBadge status="aktivno" />
                  </div>
                  <p className="text-sm text-ink-2">{selectedTask?.description || 'Izaberi dostupni zadatak sa liste.'}</p>
                  {selectedTask?.instructions && <Alert type="info">{selectedTask.instructions}</Alert>}
                  <div className="bg-mint-50 border border-frame rounded-lg p-3 text-sm space-y-1">
                    <p><span className="text-ink-3 font-medium">Nagrada:</span> <span className="font-mono font-bold text-emerald-600">{selectedTask?.requires_tester_enrollment ? `${formatRsd(selectedTask.tester_daily_reward_rsd)} dnevno` : formatRsd(selectedTask?.reward_rsd || 0)}</span></p>
                    <p><span className="text-ink-3 font-medium">Vreme:</span> oko {selectedTask?.estimated_minutes || 0} min</p>
                    <p><span className="text-ink-3 font-medium">Dokaz:</span> {selectedTask?.proof_required || '—'}</p>
                    <p><span className="text-ink-3 font-medium">Nivo:</span> {selectedTask?.min_user_level || 'Bronza'} i više</p>
                    {!selectedTask?.requires_tester_enrollment && <><p><span className="text-ink-3 font-medium">Ponavljanje:</span> {selectedTask?.repeat_interval_hours ? `na svakih ${selectedTask.repeat_interval_hours} h nakon odobrenja` : 'samo jednom'}</p><p><span className="text-ink-3 font-medium">Kvalitet:</span> {selectedTask?.min_quality_score ? `najmanje ${selectedTask.min_quality_score}%` : 'bez dodatnog uslova'}</p></>}
                  </div>
                  <Alert type="info">Za standardne zadatke server prati vreme, aktivnost i fokus taba. Za zatvoreni beta test šalješ dnevni izveštaj; svaki dan posebno odobrava oglašivač.</Alert>
                  {selectedTask?.requires_tester_enrollment && selectedTask.tester_enrollment?.status !== 'invited' ? (
                    <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 space-y-3">
                      <p className="font-bold text-amber-900">Prvo zatraži pristup zatvorenom testiranju</p>
                      {selectedTask.tester_enrollment?.status === 'requested' ? (
                        <p className="text-sm text-amber-800">Email je poslat oglašivaču. Test počinje čim te doda u tester listu i aktivira pristup; ne čeka se da se prijavi ceo broj testera.</p>
                      ) : (
                        <>
                          {selectedTask.tester_enrollment?.status === 'declined' && <p className="text-sm text-red-700">{selectedTask.tester_enrollment.note || 'Prijava nije odobrena. Proveri adresu i pošalji ponovo.'}</p>}
                          <Input label="Email za pristup testiranju" placeholder="ime@gmail.com" value={testerEmail} onChange={setTesterEmail} />
                          <Btn disabled={saving} onClick={() => selectedTask && void requestTesterAccess(selectedTask)}>Pošalji email za pristup</Btn>
                        </>
                      )}
                    </div>
                  ) : selectedTask?.requires_tester_enrollment ? (
                    <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 space-y-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <p className="font-bold text-blue-950">Tvoj lični plan zatvorenog testa</p>
                        <span className="rounded-full bg-white px-2.5 py-1 text-xs font-bold text-blue-800">{selectedTesterProgress?.checkin_total || 0}/{selectedTask.tester_duration_days} dana prijavljeno</span>
                      </div>
                      <p className="text-sm leading-6 text-blue-900">Od trenutka poziva imaš {selectedTask.tester_duration_days} uzastopnih dana. Svakog dana testiraj aplikaciju najmanje {selectedTask.tester_daily_minutes} minuta, zatim pošalji kratak izveštaj. Dnevna nagrada od {formatRsd(selectedTask.tester_daily_reward_rsd)} čeka odobrenje oglašivača.</p>
                      {selectedTesterProgress?.days_elapsed && selectedTesterProgress.days_elapsed > selectedTask.tester_duration_days && !selectedTesterProgress.complete && <Alert type="error">Rok od {selectedTask.tester_duration_days} dana je istekao pre nego što su poslati svi dnevni izveštaji. Obrati se oglašivaču kroz podršku.</Alert>}
                      {selectedTask.target_url && <Btn onClick={() => window.open(selectedTask.target_url || '', '_blank', 'noopener,noreferrer')} variant="secondary">↗ Otvori aplikaciju / test link</Btn>}
                      {selectedTesterProgress?.can_check_in ? <div className="space-y-2">
                        <label className="block text-xs font-bold uppercase tracking-wide text-blue-900">Dnevni izveštaj, dan {selectedTesterProgress.current_day}</label>
                        <textarea value={testerCheckinNote} onChange={event => setTesterCheckinNote(event.target.value)} rows={3} placeholder="Šta si danas testirao/la, koliko približno minuta i da li si primetio/la problem?" className="w-full resize-none rounded-lg border border-blue-200 bg-white px-3 py-2 text-sm text-ink outline-none focus:border-blue-500" />
                        <Btn disabled={saving} onClick={() => selectedTask && void submitTesterCheckin(selectedTask)} variant="success">Pošalji dnevni izveštaj</Btn>
                      </div> : <p className="text-sm font-medium text-blue-800">{selectedTesterProgress?.complete ? 'Poslao/la si sve potrebne dnevne izveštaje. Sačekaj odobrenja oglašivača.' : 'Današnji izveštaj je već poslat ili se otključava sledećeg dana.'}</p>}
                      {(selectedTask.tester_checkins || []).length > 0 && <div className="border-t border-blue-200 pt-3 text-xs text-blue-900"><p className="mb-1 font-bold">Evidencija dana</p>{selectedTask.tester_checkins?.sort((a, b) => a.day_number - b.day_number).map(checkin => <p key={checkin.id}>Dan {checkin.day_number}: {checkin.status === 'approved' ? 'odobreno' : checkin.status === 'rejected' ? 'potrebna dorada' : 'čeka odobrenje'}</p>)}</div>}
                    </div>
                  ) : (
                    <div className="flex gap-2">
                      {selectedTask?.target_url && <Btn onClick={() => window.open(selectedTask.target_url || '', '_blank', 'noopener,noreferrer')} variant="secondary">↗ Otvori zadatak</Btn>}
                      <Btn disabled={saving} onClick={() => selectedTask && void beginTaskVerification(selectedTask)} variant="success">🛡️ {selectedTaskRevision ? 'Pokreni doradu dokaza' : 'Pokreni proveru'}</Btn>
                    </div>
                  )}
                  <Btn onClick={() => goTo('zadaci')} variant="secondary">Nazad na zadatke</Btn>
                </Card>
              </div>
            )}

            {/* ── PREPORUKE ── */}
            {page === 'preporuke' && (
              <div>
                <SectionHeader title="Pametne preporuke" description="Zadaci odabrani prema tvom profilu i istoriji zarade." />
                <div className="bg-teal-50 border border-teal-200 rounded-xl p-4 mb-4">
                  <p className="text-sm text-teal-800 font-semibold">📊 Ovi zadaci imaju najveću verovatnoću odobrenja za tvoj profil.</p>
                </div>
                <div className="flex flex-col gap-3">
                  {activeTasks.slice(0, 2).map(t => (
                    <Card key={t.id} className="p-5 border-teal-200 bg-teal-50/30 hover:shadow-md transition-shadow">
                      <div className="flex items-start justify-between gap-4">
                        <div>
                            <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${categoryColor(t.category)} inline-block mb-2`}>{t.category}</span>
                          <h3 className="font-semibold text-ink">{t.title}</h3>
                          <p className="text-xs text-ink-3 mt-1">⏱ {t.estimated_minutes} min</p>
                        </div>
                        <div className="text-right shrink-0">
                          <p className="font-mono font-bold text-emerald-600 text-lg">{t.requires_tester_enrollment ? `${formatRsd(t.tester_daily_reward_rsd)}/dan` : formatRsd(t.reward_rsd)}</p>
                          <Btn size="sm" className="mt-2" onClick={() => { setSelectedTaskId(t.id); goTo('zadatak-detalj') }}>Detalji</Btn>
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              </div>
            )}

            {/* ── DOKAZI ── */}
            {page === 'dokazi' && (
              <div>
                <SectionHeader title="Moji dokazi" description="Status svakog poslatog dokaza." />
                <Tabs
                  tabs={[{ id: 'svi', label: 'Svi' }, { id: 'pending', label: 'Na čekanju' }, { id: 'needs_revision', label: 'Na doradi' }, { id: 'approved', label: 'Odobreno' }, { id: 'rejected', label: 'Odbijeno' }]}
                  active={proofTab}
                  onChange={setProofTab}
                />
                <Card>
                  {visibleProofs.length > 0 ? (
                    <Table
                      headers={['Zadatak', 'Poslato', 'Nagrada', 'Status', 'Napomena']}
                      rows={visibleProofs.map(p => [
                        <span className="font-medium text-ink">{p.task_title}</span>,
                        <span className="font-mono text-xs text-ink-2">{formatDate(p.created_at)}</span>,
                        <span className="font-mono font-semibold text-emerald-600">{formatRsd(p.reward_rsd)}</span>,
                        <StatusBadge status={p.status} />,
                        <span className="max-w-[280px] text-xs text-ink-2">{p.review_note || (p.status === 'needs_revision' ? 'Otvori zadatak i pošalji dopunjen dokaz.' : '—')}</span>,
                      ])}
                    />
                  ) : (
                    <EmptyState icon="📭" title="Još nema poslatih dokaza" description={proofTab === 'svi' ? 'Kada završiš zadatak i pošalješ dokaz, njegov stvarni status će biti prikazan ovde.' : 'Nema dokaza u izabranoj kategoriji.'} action={<Btn size="sm" onClick={() => goTo('zadaci')}>Pogledaj dostupne zadatke</Btn>} />
                  )}
                </Card>
              </div>
            )}

            {/* ── NOVČANIK ── */}
            {page === 'novcanik' && (
              <div>
                <SectionHeader title="Novčanik" description="Pregled zarade i transakcija." />
                <div className="grid grid-cols-2 gap-3 mb-5">
                  <StatCard label="Ukupan balans" value={formatRsd(balance)} accent="green" icon="💰" />
                  <StatCard label="Ukupno zarađeno" value={formatRsd(user?.lifetime_earned_rsd ?? 0)} accent="teal" icon="📈" />
                </div>
                <SectionHeader title="Istorija transakcija" />
                <Card>
                  <Table
                    headers={['Datum', 'Opis', 'Iznos']}
                    rows={(dashboard?.transactions ?? []).map(tx => [
                      <span className="font-mono text-xs text-ink-2">{formatDate(tx.created_at)}</span>,
                      <span className="text-ink">{tx.description}</span>,
                      <span className={`font-mono font-bold ${tx.amount_rsd >= 0 ? 'text-emerald-600' : 'text-coral-600'}`}>{tx.amount_rsd >= 0 ? '+' : ''}{formatRsd(tx.amount_rsd)}</span>,
                    ])}
                  />
                </Card>
              </div>
            )}

            {/* ── ISPLATE ── */}
            {page === 'isplate' && (
              <div className="space-y-4">
                <SectionHeader title="Isplate" description="Zatraži isplatu kada dostigneš minimalni iznos." />
                <Alert type="warning">
                  Minimalni iznos za isplatu je <strong>{formatRsd(minWithdrawal)}</strong>. Tvoj balans: <strong className="font-mono">{formatRsd(balance)}</strong>. {payoutGap > 0 ? <>Nedostaje još <strong className="font-mono text-amber-700">{formatRsd(payoutGap)}</strong>.</> : 'Možeš poslati zahtev za isplatu.'}
                </Alert>
                <Card className="p-5">
                  <h3 className="font-bold text-ink mb-4">Podaci za isplatu</h3>
                  <div className="divide-y divide-frame">
                    {[["Metoda", 'PayPal'], ['PayPal e-mail', user?.payment_details ? 'Sačuvan' : '—'], ['Primalac', user?.full_name || '—']].map(([k, v]) => (
                      <div key={k} className="flex justify-between py-3">
                        <span className="text-sm text-ink-2">{k}</span>
                        <span className="text-sm text-ink font-medium">{v}</span>
                      </div>
                    ))}
                  </div>
                  <Btn onClick={() => goTo('podaci-isplata')} variant="secondary" size="sm" className="mt-4">Podesi podatke za isplatu</Btn>
                </Card>
                <div className="flex flex-col sm:flex-row gap-2">
                  <input value={payoutAmount} onChange={event => setPayoutAmount(event.target.value)} type="number" min={minWithdrawal} max={balance} placeholder={`Iznos (${formatRsd(minWithdrawal)} min.)`} className="bg-white border border-frame text-ink rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none flex-1" />
                  <Btn disabled={balance < minWithdrawal || !user?.payment_details} onClick={() => setConfirmPayout(true)} className="justify-center">Zatraži isplatu</Btn>
                </div>
                <p className="text-xs text-ink-3 text-center">Zahtev se šalje adminu tek kada su saldo i podaci za isplatu validni.</p>
              </div>
            )}

            {/* ── PODACI ZA ISPLATU ── */}
            {page === 'podaci-isplata' && (
              <div className="space-y-4">
                <SectionHeader title="Podaci za PayPal isplatu" description="Unesi PayPal e-mail adresu na koju primaš isplate." />
                <Card className="p-5 space-y-4">
                  <Alert type="info">Podaci su zaštićeni i koriste se isključivo za isplatu zarade.</Alert>
                  <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-bold text-ink-2 uppercase tracking-wide">Ime i prezime primaoca</label>
                    <input value={profileName} onChange={event => setProfileName(event.target.value)} placeholder="Ime i prezime" className="bg-white border border-frame text-ink rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-bold text-ink-2 uppercase tracking-wide">Metoda isplate</label>
                    <div className="bg-blue-50 border border-blue-200 text-blue-900 rounded-lg px-3 py-2 text-sm font-semibold">PayPal</div>
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-bold text-ink-2 uppercase tracking-wide">PayPal e-mail adresa</label>
                    <input type="email" value={paymentDetails} onChange={event => setPaymentDetails(event.target.value)} placeholder="ime@primer.com" className="bg-white border border-frame text-ink rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
                  </div>
                  <div className="flex gap-2">
                    <Btn variant="success" disabled={saving || !profileName.trim() || !paymentDetails.trim()} onClick={async () => { setSaving(true); try { await api.saveProfile({ full_name: profileName, payment_method: 'PayPal', payment_details: paymentDetails }); await refreshDashboard(); showToast('PayPal podaci za isplatu su sačuvani.', 'success'); goTo('isplate') } catch (error) { showToast(error instanceof Error ? error.message : 'Podaci nisu sačuvani.', 'error') } finally { setSaving(false) } }}>{saving ? 'Čuvanje...' : 'Sačuvaj podatke'}</Btn>
                    <Btn variant="secondary" onClick={() => goTo('isplate')}>Otkaži</Btn>
                  </div>
                </Card>
              </div>
            )}

            {/* ── NAGRADE ── */}
            {page === 'nagrade' && (
              <div className="space-y-5">
                <SectionHeader title="Dnevne nagrade i streak" description="Nagrada se otključava tek nakon prvog stvarno poslatog dokaza tog dana." />
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-5">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <p className="font-bold text-ink text-lg">🔥 Streak: {dailyReward?.streak ?? 0} dana</p>
                      <p className="text-sm text-amber-700 mt-0.5">{dailyReward?.claimed ? 'Današnja nagrada je evidentirana.' : dailyReward?.eligible ? `Preuzmi današnjih ${formatRsd(dailyReward.reward_rsd)}.` : 'Pošalji dokaz danas da otključaš dnevnu nagradu.'}</p>
                    </div>
                    {dailyReward?.claimed ? <span className="text-emerald-700 font-bold bg-emerald-100 px-3 py-1.5 rounded-lg text-sm">Preuzeto</span> : <Btn size="sm" variant="success" disabled={saving || !dailyReward?.eligible} onClick={() => dailyReward?.eligible ? void claimProgramReward(dailyReward.key) : goTo('zadaci')}>{dailyReward?.eligible ? `Preuzmi ${formatRsd(dailyReward.reward_rsd)}` : 'Otvori zadatke'}</Btn>}
                  </div>
                  <div className="grid grid-cols-7 gap-1.5">
                    {(dailyReward?.week ?? []).map(day => (
                      <div key={day.date} className={`rounded-lg p-2 text-center ${day.claimed ? 'bg-amber-200' : day.is_today ? 'bg-white border-2 border-amber-400' : 'bg-white border border-amber-100'}`}>
                        <p className="text-[10px] text-amber-800 font-semibold">{day.label}</p>
                        <p className="text-sm">{day.claimed ? '✓' : day.is_today ? '⭐' : '—'}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* ── MISIJE ── */}
            {page === 'misije' && (
              <div className="space-y-5">
                <SectionHeader title="Misije i bedževi" />
                <div>
                  <h3 className="text-xs font-bold text-ink-3 uppercase tracking-widest mb-3">Aktivne misije</h3>
                  <div className="flex flex-col gap-3">
                    {programMissions.map(m => (
                      <Card key={m.key} className="p-4">
                        <div className="flex items-center justify-between mb-2">
                          <p className="font-semibold text-ink text-sm">{m.title}</p>
                          <span className="font-mono font-bold text-emerald-600 text-sm">{formatRsd(m.reward_rsd)}</span>
                        </div>
                        <div className="flex items-center gap-3">
                          <div className="flex-1 bg-gray-100 rounded-full h-2">
                            <div className={`${m.accent} h-2 rounded-full transition-all`} style={{ width: `${Math.min(100, (m.progress / m.target) * 100)}%` }} />
                          </div>
                          <span className="text-xs text-ink-3 font-mono">{m.progress}/{m.target}</span>
                          <Btn size="sm" variant={m.claimed ? 'secondary' : 'success'} disabled={saving || m.claimed || !m.eligible} onClick={() => void claimProgramReward(m.key)}>{m.claimed ? 'Preuzeto' : m.eligible ? 'Preuzmi' : 'U toku'}</Btn>
                        </div>
                      </Card>
                    ))}
                  </div>
                </div>
                <div>
                  <h3 className="text-xs font-bold text-ink-3 uppercase tracking-widest mb-3">Bedževi</h3>
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
                    {programBadges.map(badge => (
                      <div key={badge.key} className={`rounded-xl p-4 text-center border ${badge.unlocked ? 'bg-violet-50 border-violet-200' : 'bg-gray-50 border-gray-200 opacity-50'}`}>
                        <span className="text-3xl block mb-2">{badge.icon}</span>
                        <p className="text-sm font-bold text-ink">{badge.name}</p>
                        <p className="text-xs text-ink-3 mt-0.5">{badge.description}</p>
                        {badge.unlocked && <span className="text-xs text-emerald-600 font-bold mt-1 block">✓ Otključano</span>}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* ── REFERRAL ── */}
            {page === 'referral' && (
              <div className="space-y-4">
                <SectionHeader title="Referral program" description="Pozovi prijatelje i zaradite oboje." />
                <div className="grid grid-cols-2 gap-3">
                  <StatCard label="Pozvanih korisnika" value={String(dashboard?.referral_count ?? 0)} icon="👥" accent="blue" />
                  <StatCard label="Zarađeno referral" value="0 RSD" icon="💰" accent="green" />
                </div>
                <Card className="p-5">
                  <h3 className="font-bold text-ink mb-2">Tvoj referral link</h3>
                  <p className="text-sm text-ink-2 mb-4">Podeli ovaj link. Kad se prijatelj registruje i izvrši prvi zadatak, oboje dobijate bonus.</p>
                  <div className="flex items-center gap-2 bg-mint-100 border border-frame rounded-lg p-3">
                    <span className="font-mono text-sm text-ink-2 flex-1 truncate">{`${window.location.origin}/r/${user?.referral_code || '—'}`}</span>
                    <Btn size="sm" variant="secondary" onClick={() => { void navigator.clipboard?.writeText(`${window.location.origin}/r/${user?.referral_code || ''}`); showToast('Link je kopiran u clipboard!', 'success') }}>Kopiraj</Btn>
                  </div>
                  <div className="mt-4 grid grid-cols-2 gap-3">
                    <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3 text-center">
                      <p className="font-mono font-bold text-emerald-700 text-lg">+100 RSD</p>
                      <p className="text-xs text-emerald-600 mt-0.5 font-medium">Ti dobijaš</p>
                    </div>
                    <div className="bg-blue-50 border border-blue-200 rounded-xl p-3 text-center">
                      <p className="font-mono font-bold text-blue-700 text-lg">+50 RSD</p>
                      <p className="text-xs text-blue-600 mt-0.5 font-medium">Prijatelj dobija</p>
                    </div>
                  </div>
                </Card>
                <EmptyState icon="👥" title="Još nema pozvanih korisnika" description="Podeli referral link i pozovi prve prijatelje." />
              </div>
            )}

            {/* ── PROFIL ── */}
            {page === 'profil' && (
              <div className="space-y-4">
                <SectionHeader title="Profil i podešavanja" />
                <Card className="p-5">
                  <div className="flex items-center gap-4 mb-5">
                    <div className="w-14 h-14 rounded-full bg-blue-600 flex items-center justify-center text-white text-xl font-bold">{user?.full_name?.slice(0, 1).toUpperCase() || 'K'}</div>
                    <div>
                      <p className="font-bold text-ink text-lg">{user?.full_name || 'Učitavanje...'}</p>
                      <p className="text-sm text-ink-2">{user?.email || '—'}</p>
                      <span className="text-xs text-blue-600 font-semibold mt-0.5 block">🧭 {user?.level || 'Bronza'} nivo</span>
                    </div>
                  </div>
                  <div className="mt-5 grid gap-3 sm:grid-cols-2">
                    <div className="flex flex-col gap-1.5"><label className="text-xs font-bold text-ink-2 uppercase tracking-wide">Ime i prezime</label><input value={profileName} onChange={event => setProfileName(event.target.value)} className="bg-white border border-frame text-ink rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" /></div>
                    <div className="flex flex-col gap-1.5"><label className="text-xs font-bold text-ink-2 uppercase tracking-wide">Telefon</label><input value={profilePhone} onChange={event => setProfilePhone(event.target.value)} placeholder="+381..." className="bg-white border border-frame text-ink rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" /></div>
                    <div className="flex flex-col gap-1.5 sm:col-span-2"><label className="text-xs font-bold text-ink-2 uppercase tracking-wide">Grad</label><input value={profileCity} onChange={event => setProfileCity(event.target.value)} placeholder="npr. Beograd" className="bg-white border border-frame text-ink rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" /></div>
                  </div>
                  <Btn variant="success" size="sm" className="mt-4" disabled={saving || profileName.trim().length < 2} onClick={async () => { setSaving(true); try { await api.saveProfile({ full_name: profileName.trim(), phone: profilePhone.trim() || undefined, city: profileCity.trim() || undefined }); await refreshDashboard(); showToast('Profil je sačuvan.', 'success') } catch (error) { showToast(error instanceof Error ? error.message : 'Profil nije sačuvan.', 'error') } finally { setSaving(false) } }}>{saving ? 'Čuvanje...' : 'Sačuvaj profil'}</Btn>
                </Card>
                <Card className="p-5">
                  <h3 className="font-bold text-ink mb-3">Bezbednost</h3>
                  <div className={`rounded-lg border p-3 mb-4 flex flex-wrap items-center justify-between gap-3 ${user?.email_verified ? 'border-emerald-200 bg-emerald-50' : 'border-amber-200 bg-amber-50'}`}>
                    <div><p className="text-sm font-semibold text-ink">{user?.email_verified ? 'Email je potvrđen' : 'Email još nije potvrđen'}</p><p className="text-xs text-ink-2 mt-0.5">{user?.email_verified ? 'Potvrda pomaže pri zaštiti naloga i resetu lozinke.' : 'Pošalji novu poruku za potvrdu na svoju email adresu.'}</p></div>
                    {!user?.email_verified && <Btn size="sm" variant="secondary" disabled={saving} onClick={() => void (async () => { try { setSaving(true); const result = await api.resendEmailVerification(); showToast(result.delivered ? 'Poruka za potvrdu je poslata.' : 'Link je stavljen u email red. SMTP treba da bude podešen na Renderu.', 'info') } catch (error) { showToast(error instanceof Error ? error.message : 'Poruka nije poslata.', 'error') } finally { setSaving(false) } })()}>Pošalji ponovo</Btn>}
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <input type="password" value={currentPassword} onChange={event => setCurrentPassword(event.target.value)} placeholder="Trenutna lozinka" className="bg-white border border-frame text-ink rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
                    <input type="password" value={newPassword} onChange={event => setNewPassword(event.target.value)} placeholder="Nova lozinka, najmanje 8 znakova" className="bg-white border border-frame text-ink rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
                    <input type="password" value={repeatPassword} onChange={event => setRepeatPassword(event.target.value)} placeholder="Ponovi novu lozinku" className="bg-white border border-frame text-ink rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
                  </div>
                  <Btn variant="secondary" size="sm" className="mt-3" disabled={saving || newPassword.length < 8 || newPassword !== repeatPassword} onClick={async () => { setSaving(true); try { await api.changePassword({ current_password: currentPassword, new_password: newPassword }); setCurrentPassword(''); setNewPassword(''); setRepeatPassword(''); showToast('Lozinka je promenjena.', 'success') } catch (error) { showToast(error instanceof Error ? error.message : 'Lozinka nije promenjena.', 'error') } finally { setSaving(false) } }}>Promeni lozinku</Btn>
                  <p className="mt-3 text-xs text-ink-3">Dvofaktorska autentifikacija se uključuje tek kada postavimo SMS ili authenticator provajdera.</p>
                </Card>
                <Btn variant="danger" size="sm" onClick={() => setLogoutConfirm(true)}>Odjavi se</Btn>
              </div>
            )}

            {/* ── PODRŠKA ── */}
            {page === 'podrska' && (
              <div className="space-y-4">
                <SectionHeader title="Podrška" />
                <div className="grid sm:grid-cols-2 gap-4">
                  <div className="bg-blue-50 border border-blue-200 rounded-xl p-5">
                    <p className="font-bold text-ink mb-1">📚 Centar za pomoć</p>
                    <p className="text-sm text-ink-2 mb-3">Odgovori na česta pitanja korisnika.</p>
                    <Btn variant="secondary" size="sm" onClick={() => showToast('Centar za pomoć se priprema. Za konkretan slučaj otvori tiket.', 'info')}>Otvori pomoć</Btn>
                  </div>
                  <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-5">
                    <p className="font-bold text-ink mb-1">💬 Kontaktiraj podršku</p>
                    <p className="text-sm text-ink-2 mb-3">Odgovaramo u roku od 24h, svakog dana.</p>
                    <Btn variant="secondary" size="sm" onClick={() => document.getElementById('novi-tiket')?.scrollIntoView({ behavior: 'smooth' })}>Pošalji poruku</Btn>
                  </div>
                </div>
                <div id="novi-tiket"><Card className="p-5 space-y-3">
                  <h3 className="font-bold text-ink">Novi tiket</h3>
                  <input value={ticketSubject} onChange={event => setTicketSubject(event.target.value)} placeholder="Kratak naslov problema" className="w-full bg-white border border-frame text-ink rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
                  <textarea value={ticketBody} onChange={event => setTicketBody(event.target.value)} rows={4} placeholder="Opiši problem i dodaj bitne detalje." className="w-full bg-white border border-frame text-ink rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none resize-y" />
                  <Btn disabled={saving || !ticketSubject.trim() || !ticketBody.trim()} onClick={async () => { setSaving(true); try { await api.createTicket({ subject: ticketSubject, body: ticketBody }); await refreshDashboard(); setTicketSubject(''); setTicketBody(''); showToast('Tiket je poslat podršci.', 'success') } catch (error) { showToast(error instanceof Error ? error.message : 'Tiket nije poslat.', 'error') } finally { setSaving(false) } }}>{saving ? 'Slanje...' : 'Pošalji tiket'}</Btn>
                </Card></div>
                {tickets.length === 0 ? <EmptyState icon="🎫" title="Nema otvorenih tiketa" description="Sva tvoja pitanja su rešena." /> : tickets.map(ticket => <Card key={ticket.id} className="p-5"><div className="flex items-start justify-between gap-3"><div><p className="font-bold text-ink">#{ticket.id} · {ticket.subject}</p><p className="text-xs text-ink-3 mt-1">{ticket.category}</p></div><StatusBadge status={ticket.status === 'closed' ? 'odobreno' : ticket.status === 'waiting' ? 'na_proveri' : 'na_cekanju'} /></div><div className="mt-4 space-y-2">{ticket.messages.map(message => <div key={message.id} className={`rounded-lg p-3 text-sm ${message.from_support ? 'bg-blue-50 text-blue-900' : 'bg-mint-50 text-ink'}`}><p className="text-xs font-semibold">{message.from_support ? 'Podrška' : 'Ti'} · {message.created_at ? new Date(message.created_at).toLocaleString('sr-RS') : ''}</p><p className="mt-1 whitespace-pre-wrap">{message.body}</p></div>)}</div><Btn size="sm" variant="secondary" className="mt-4" onClick={() => { const body = window.prompt('Odgovor podršci:'); if (!body?.trim()) return; void (async () => { try { await api.replyToTicket(ticket.id, body.trim()); await refreshDashboard(); showToast('Odgovor je poslat.', 'success') } catch (error) { showToast(error instanceof Error ? error.message : 'Odgovor nije poslat.', 'error') } })() }}>Odgovori</Btn></Card>)}
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}
