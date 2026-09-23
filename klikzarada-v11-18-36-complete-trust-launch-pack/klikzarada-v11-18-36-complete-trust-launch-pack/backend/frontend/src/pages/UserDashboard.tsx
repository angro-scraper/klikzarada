import { useEffect, useState } from 'react'
import { Sidebar, TopBar } from '../components/Sidebar'
import { Btn, Card, StatCard, SectionHeader, EmptyState, Table, StatusBadge, Tabs, Alert } from '../components/ui'
import { PageHeader } from '../components/PageHeader'
import { ConfirmModal, InfoModal } from '../components/Modal'
import { useToast } from '../components/Toast'
import { api, type SessionUser, type SupportTicket, type Task, type UserDashboardData } from '../lib/api'

const navGroups = [
  { items: [
    { id: 'pregled', label: 'Pregled', icon: '📊' },
    { id: 'zadaci', label: 'Dostupni zadaci', icon: '📋' },
    { id: 'preporuke', label: 'Preporuke', icon: '✨' },
    { id: 'dokazi', label: 'Moji dokazi', icon: '✅', badge: 2 },
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

type Page = 'pregled'|'zadaci'|'preporuke'|'dokazi'|'novcanik'|'isplate'|'podaci-isplata'|'nagrade'|'misije'|'referral'|'profil'|'podrska'|'zadatak-detalj'

const BACK: Partial<Record<Page, { label: string; to: Page }>> = {
  zadaci:          { label: 'Nazad na pregled', to: 'pregled' },
  preporuke:       { label: 'Nazad na pregled', to: 'pregled' },
  dokazi:          { label: 'Nazad na pregled', to: 'pregled' },
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

const badges = [
  { icon: '🚀', name: 'Starter', desc: 'Prvih 5 zadataka', unlocked: true },
  { icon: '🔥', name: 'Streak 7', desc: '7 dana zaredom', unlocked: true },
  { icon: '⭐', name: 'Trusted', desc: '20 odobrenih dokaza', unlocked: false },
  { icon: '💎', name: 'Pro Earner', desc: '500 RSD zarade', unlocked: false },
  { icon: '👑', name: 'Elite', desc: '50 dokaza', unlocked: false },
]

const missions = [
  { title: 'Izvrši 3 zadatka danas', progress: 1, total: 3, reward: '50 RSD', accent: 'bg-blue-500' },
  { title: 'Dostavi 5 dokaza ove nedelje', progress: 2, total: 5, reward: '150 RSD', accent: 'bg-emerald-500' },
  { title: 'Pozovi prvog prijatelja', progress: 0, total: 1, reward: '200 RSD', accent: 'bg-violet-500' },
]

export default function UserDashboard({ onNavigate }: { onNavigate: (id: string) => void }) {
  const [page, setPage] = useState<Page>('pregled')
  const [mobileOpen, setMobileOpen] = useState(false)
  const [proofTab, setProofTab] = useState('svi')
  const [confirmPayout, setConfirmPayout] = useState(false)
  const [submitProofModal, setSubmitProofModal] = useState<number | null>(null)
  const [selectedTaskId, setSelectedTaskId] = useState<number | null>(null)
  const [logoutConfirm, setLogoutConfirm] = useState(false)
  const [dashboard, setDashboard] = useState<UserDashboardData | null>(null)
  const [dashboardError, setDashboardError] = useState('')
  const [proofText, setProofText] = useState('')
  const [payoutAmount, setPayoutAmount] = useState('')
  const [paymentMethod, setPaymentMethod] = useState('bankovni račun')
  const [paymentDetails, setPaymentDetails] = useState('')
  const [profileName, setProfileName] = useState('')
  const [saving, setSaving] = useState(false)
  const [tickets, setTickets] = useState<SupportTicket[]>([])
  const [ticketSubject, setTicketSubject] = useState('')
  const [ticketBody, setTicketBody] = useState('')
  const { show: showToast, node: toastNode } = useToast()

  const refreshDashboard = async () => {
    try {
      const [data, ticketData] = await Promise.all([api.userDashboard(), api.tickets()])
      setDashboard(data)
      setTickets(ticketData.tickets)
      setPaymentMethod(data.user.payment_method || 'bankovni račun')
      setPaymentDetails(data.user.payment_details || '')
      setProfileName(data.user.full_name)
      setDashboardError('')
    } catch (error) {
      setDashboardError(error instanceof Error ? error.message : 'Podaci trenutno nisu dostupni.')
    }
  }

  useEffect(() => { void refreshDashboard() }, [])

  const user: SessionUser | undefined = dashboard?.user
  const activeTasks: Task[] = dashboard?.tasks ?? []
  const balance = user?.balance_rsd ?? 0
  const minWithdrawal = dashboard?.min_withdrawal_rsd ?? 1000
  const payoutGap = Math.max(0, minWithdrawal - balance)
  const selectedTask = activeTasks.find(task => task.id === selectedTaskId || task.id === submitProofModal)

  function goTo(p: Page) { setPage(p) }
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
        description={`Iznos od ${formatRsd(Number(payoutAmount) || balance)} biće prosleđen na navedene podatke. Zahtev prvo prolazi administrativnu proveru.`}
        confirmLabel="Zatraži isplatu"
        cancelLabel="Otkaži"
        variant="success"
        onConfirm={async () => {
          const amount = Number(payoutAmount) || balance
          if (!paymentDetails.trim()) {
            showToast('Unesi podatke za isplatu pre slanja zahteva.', 'error')
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
        title="Pošalji dokaz"
        onClose={() => setSubmitProofModal(null)}
      >
        {submitProofModal !== null && (
          <div className="space-y-3">
            <p className="text-sm text-ink-2">{selectedTask ? `Dokaz za: ${selectedTask.title}` : 'Pošalji dokaz izvršenja zadatka.'}</p>
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-bold text-ink-2 uppercase tracking-wide">Link ili opis dokaza</label>
              <textarea value={proofText} onChange={event => setProofText(event.target.value)} rows={4} placeholder="Nalepi javni link do screenshota ili napiši gde admin može da proveri izvršenje." className="bg-white border border-frame text-ink rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none resize-y" />
              <p className="text-xs text-ink-3">Upload fajlova dodajemo kao sledeći korak; trenutno se šalje link ili detaljan opis za proveru.</p>
            </div>
            <Btn
              variant="success"
              className="w-full justify-center"
              disabled={saving || !proofText.trim()}
              onClick={async () => {
                setSaving(true)
                try {
                  await api.submitProof(submitProofModal, proofText)
                  await refreshDashboard()
                  setProofText('')
                  setSubmitProofModal(null)
                  showToast('Dokaz je poslat i čeka pregled.', 'success')
                } catch (error) {
                  showToast(error instanceof Error ? error.message : 'Dokaz nije poslat.', 'error')
                } finally {
                  setSaving(false)
                }
              }}
            >
              {saving ? 'Slanje...' : 'Pošalji dokaz'}
            </Btn>
          </div>
        )}
      </InfoModal>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 bg-black/40 z-40 lg:hidden" onClick={() => setMobileOpen(false)} />
      )}

      <div className="hidden lg:flex shrink-0">
        <Sidebar groups={navGroups} active={page} onNavigate={p => goTo(p as Page)} footer={sidebarFooter} />
      </div>
      {mobileOpen && (
        <div className="fixed left-0 top-0 h-full z-50 lg:hidden">
          <Sidebar
            groups={navGroups}
            active={page}
            onNavigate={p => { goTo(p as Page); setMobileOpen(false) }}
            footer={sidebarFooter}
            isMobile
            onClose={() => setMobileOpen(false)}
          />
        </div>
      )}

      <div className="flex-1 flex flex-col overflow-hidden">
        <TopBar
          onMenuClick={() => setMobileOpen(true)}
          pageTitle="Zarada centar"
          onNavigate={onNavigate}
          actions={
            <div className="flex items-center gap-3">
              <div className="text-right hidden sm:block">
                <p className="font-mono text-sm font-bold text-emerald-600">{formatRsd(balance)}</p>
                <p className="text-[10px] text-ink-3">Balans</p>
              </div>
              <Btn variant="success" size="sm" onClick={() => goTo('isplate')}>💸 Isplati</Btn>
            </div>
          }
        />

        <main className="flex-1 overflow-y-auto bg-mint-50">
          <div className="max-w-4xl mx-auto px-4 py-6">
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
                    <p className="text-sm text-amber-700">Program dnevnih nagrada se uvodi uskoro. Ne prikazujemo izmišljene bonuse.</p>
                    </div>
                  </div>
                  <span className="text-sm text-amber-700 font-bold bg-amber-100 px-3 py-1.5 rounded-lg">Uskoro</span>
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
                    {[{ t: 'Explorer', icon: '🧭', active: true }, { t: 'Trusted', icon: '⭐', active: false }, { t: 'Pro', icon: '💎', active: false }, { t: 'Elite', icon: '👑', active: false }].map(tier => (
                      <div key={tier.t} className={`flex-1 text-center text-xs py-1.5 rounded-lg font-semibold ${tier.active ? 'bg-blue-600 text-white' : 'bg-gray-100 text-ink-3'}`}>
                        {tier.icon} <span className="hidden sm:inline">{tier.t}</span>
                      </div>
                    ))}
                  </div>
                  <div className="bg-gray-100 rounded-full h-1.5 mb-1">
                    <div className="bg-blue-600 h-1.5 rounded-full" style={{ width: '25%' }} />
                  </div>
                  <p className="text-xs text-ink-3">5 od 20 odobrenih dokaza</p>
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
                          <span className="font-mono font-bold text-emerald-600">{formatRsd(t.reward_rsd)}</span>
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
                            <StatusBadge status="aktivno" />
                          </div>
                          <h3 className="font-semibold text-ink">{t.title}</h3>
                          <p className="text-xs text-ink-3 mt-1">⏱ {t.estimated_minutes} min · 📎 {t.proof_required || 'Dokaz potreban'}</p>
                        </div>
                        <div className="text-right shrink-0">
                          <p className="font-mono font-bold text-emerald-600 text-lg">{formatRsd(t.reward_rsd)}</p>
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
                    <p><span className="text-ink-3 font-medium">Nagrada:</span> <span className="font-mono font-bold text-emerald-600">{formatRsd(selectedTask?.reward_rsd || 0)}</span></p>
                    <p><span className="text-ink-3 font-medium">Vreme:</span> oko {selectedTask?.estimated_minutes || 0} min</p>
                    <p><span className="text-ink-3 font-medium">Dokaz:</span> {selectedTask?.proof_required || '—'}</p>
                    <p><span className="text-ink-3 font-medium">Nivo:</span> {selectedTask?.min_user_level || 'Bronza'} i više</p>
                  </div>
                  <Alert type="info">Nakon što izvršiš zadatak, napravi screenshot i pošalji ga kao dokaz. Naknada se odobrava ručno.</Alert>
                  <div className="flex gap-2">
                    <Btn onClick={() => selectedTask && setSubmitProofModal(selectedTask.id)} variant="success">📎 Pošalji dokaz</Btn>
                    <Btn onClick={() => goTo('zadaci')} variant="secondary">Nazad na zadatke</Btn>
                  </div>
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
                          <p className="font-mono font-bold text-emerald-600 text-lg">{formatRsd(t.reward_rsd)}</p>
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
                  tabs={[{ id: 'svi', label: 'Svi' }, { id: 'na_cekanju', label: 'Na čekanju' }, { id: 'odobreno', label: 'Odobreno' }, { id: 'odbijeno', label: 'Odbijeno' }]}
                  active={proofTab}
                  onChange={setProofTab}
                />
                <Card>
                  <Table
                    headers={['Zadatak', 'Poslato', 'Nagrada', 'Status']}
                    rows={(dashboard?.submissions ?? []).filter(p => proofTab === 'svi' || p.status === proofTab).map(p => [
                      <span className="font-medium text-ink">{p.task_title}</span>,
                      <span className="font-mono text-xs text-ink-2">{formatDate(p.created_at)}</span>,
                      <span className="font-mono font-semibold text-emerald-600">{formatRsd(p.reward_rsd)}</span>,
                      <StatusBadge status={p.status} />,
                    ])}
                  />
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
                    {[["Metoda", user?.payment_method || 'Nije podešeno'], ['Podaci računa', user?.payment_details ? 'Sačuvano' : '—'], ['Primalac', user?.full_name || '—']].map(([k, v]) => (
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
                <SectionHeader title="Podaci za isplatu" description="Unesi podatke računa na koji primaš isplate." />
                <Card className="p-5 space-y-4">
                  <Alert type="info">Podaci su zaštićeni i koriste se isključivo za isplatu zarade.</Alert>
                  <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-bold text-ink-2 uppercase tracking-wide">Ime i prezime primaoca</label>
                    <input value={profileName} onChange={event => setProfileName(event.target.value)} placeholder="Ime i prezime" className="bg-white border border-frame text-ink rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-bold text-ink-2 uppercase tracking-wide">Metoda isplate</label>
                    <input value={paymentMethod} onChange={event => setPaymentMethod(event.target.value)} placeholder="npr. bankovni račun" className="bg-white border border-frame text-ink rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
                  </div>
                  <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-bold text-ink-2 uppercase tracking-wide">Broj računa / podaci za isplatu</label>
                    <input value={paymentDetails} onChange={event => setPaymentDetails(event.target.value)} placeholder="160-000000000000-00" className="bg-white border border-frame text-ink rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
                  </div>
                  <div className="flex gap-2">
                    <Btn variant="success" disabled={saving || !profileName.trim() || !paymentDetails.trim()} onClick={async () => { setSaving(true); try { await api.saveProfile({ full_name: profileName, payment_method: paymentMethod, payment_details: paymentDetails }); await refreshDashboard(); showToast('Podaci za isplatu su sačuvani.', 'success'); goTo('isplate') } catch (error) { showToast(error instanceof Error ? error.message : 'Podaci nisu sačuvani.', 'error') } finally { setSaving(false) } }}>{saving ? 'Čuvanje...' : 'Sačuvaj podatke'}</Btn>
                    <Btn variant="secondary" onClick={() => goTo('isplate')}>Otkaži</Btn>
                  </div>
                </Card>
              </div>
            )}

            {/* ── NAGRADE ── */}
            {page === 'nagrade' && (
              <div className="space-y-5">
                <SectionHeader title="Dnevne nagrade i streak" />
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-5">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <p className="font-bold text-ink text-lg">🔥 Streak: 7 dana</p>
                      <p className="text-sm text-amber-700 mt-0.5">Nastavi svaki dan za bonus nagrade!</p>
                    </div>
                    <span className="text-amber-700 font-bold bg-amber-100 px-3 py-1.5 rounded-lg text-sm">Uskoro</span>
                  </div>
                  <div className="grid grid-cols-7 gap-1.5">
                    {['Pon', 'Uto', 'Sre', 'Čet', 'Pet', 'Sub', 'Ned'].map((dan, i) => (
                      <div key={dan} className={`rounded-lg p-2 text-center ${i < 6 ? 'bg-amber-200' : 'bg-white border-2 border-amber-400'}`}>
                        <p className="text-[10px] text-amber-800 font-semibold">{dan}</p>
                        <p className="text-sm">{i < 6 ? '✓' : '⭐'}</p>
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
                    {missions.map(m => (
                      <Card key={m.title} className="p-4">
                        <div className="flex items-center justify-between mb-2">
                          <p className="font-semibold text-ink text-sm">{m.title}</p>
                          <span className="font-mono font-bold text-emerald-600 text-sm">{m.reward}</span>
                        </div>
                        <div className="flex items-center gap-3">
                          <div className="flex-1 bg-gray-100 rounded-full h-2">
                            <div className={`${m.accent} h-2 rounded-full transition-all`} style={{ width: `${(m.progress / m.total) * 100}%` }} />
                          </div>
                          <span className="text-xs text-ink-3 font-mono">{m.progress}/{m.total}</span>
                        </div>
                      </Card>
                    ))}
                  </div>
                </div>
                <div>
                  <h3 className="text-xs font-bold text-ink-3 uppercase tracking-widest mb-3">Bedževi</h3>
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
                    {badges.map(b => (
                      <div key={b.name} className={`rounded-xl p-4 text-center border ${b.unlocked ? 'bg-violet-50 border-violet-200' : 'bg-gray-50 border-gray-200 opacity-50'}`}>
                        <span className="text-3xl block mb-2">{b.icon}</span>
                        <p className="text-sm font-bold text-ink">{b.name}</p>
                        <p className="text-xs text-ink-3 mt-0.5">{b.desc}</p>
                        {b.unlocked && <span className="text-xs text-emerald-600 font-bold mt-1 block">✓ Otključano</span>}
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
                  <Btn variant="secondary" size="sm">Izmeni profil</Btn>
                </Card>
                <Card className="p-5">
                  <h3 className="font-bold text-ink mb-3">Bezbednost</h3>
                  <div className="flex flex-col gap-2">
                    <Btn variant="ghost" size="sm" className="justify-start">🔑 Promeni lozinku</Btn>
                    <Btn variant="ghost" size="sm" className="justify-start">🔐 Dvofaktorska autentifikacija</Btn>
                  </div>
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
                {tickets.length === 0 ? <EmptyState icon="🎫" title="Nema otvorenih tiketa" description="Sva tvoja pitanja su rešena." /> : <Card><Table headers={['Naslov', 'Kategorija', 'Status', 'Ažurirano']} rows={tickets.map(ticket => [<span className="font-medium text-ink">{ticket.subject}</span>, <span className="text-sm text-ink-2">{ticket.category}</span>, <StatusBadge status={ticket.status === 'open' ? 'na_cekanju' : ticket.status === 'closed' ? 'odobreno' : 'na_proveri'} />, <span className="font-mono text-xs text-ink-2">{formatDate(ticket.updated_at)}</span>])} /></Card>}
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}
