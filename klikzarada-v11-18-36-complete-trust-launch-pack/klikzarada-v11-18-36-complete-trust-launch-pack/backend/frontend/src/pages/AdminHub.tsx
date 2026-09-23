import { useEffect, useState } from 'react'
import { Sidebar, TopBar } from '../components/Sidebar'
import { Btn, Card, StatCard, SectionHeader, EmptyState, Table, StatusBadge, Tabs, Alert } from '../components/ui'
import { PageHeader } from '../components/PageHeader'
import { ConfirmModal } from '../components/Modal'
import { useToast } from '../components/Toast'
import { api, type AdminCampaign, type AdminMetrics, type AdminSubmission, type AdminUser, type AdminWithdrawal, type AdminSetting, type FraudOverview, type SupportTicket, type TaskSource } from '../lib/api'

const navGroups = [
  { group: 'Dashboard', items: [{ id: 'dashboard', label: 'Pregled', icon: '📊' }] },
  { group: 'Finansije', items: [
    { id: 'fin-racuni', label: 'Računi platforme', icon: '🏦' },
    { id: 'fin-isplate', label: 'Isplate korisnika', icon: '💸', badge: 3 },
    { id: 'fin-uplate', label: 'Uplate oglašivača', icon: '💳' },
    { id: 'fin-fakture', label: 'Fakture', icon: '🧾' },
  ]},
  { group: 'Kampanje i reklame', items: [
    { id: 'kam-kampanje', label: 'Kampanje', icon: '🎯', badge: 2 },
    { id: 'kam-dokazi', label: 'Moderacija dokaza', icon: '📎', badge: 7 },
    { id: 'kam-uvoz', label: 'Uvoz zadataka', icon: '🔄' },
    { id: 'kam-banneri', label: 'Banner slotovi', icon: '🖼️' },
  ]},
  { group: 'Ljudi', items: [
    { id: 'lj-korisnici', label: 'Korisnici', icon: '👥' },
    { id: 'lj-oglasivaci', label: 'Oglašivači', icon: '🏢' },
    { id: 'lj-referral', label: 'Referral', icon: '🔗' },
    { id: 'lj-podrska', label: 'Tiketi', icon: '🎫', badge: 1 },
  ]},
  { group: 'Operacije', items: [
    { id: 'ops-antifraud', label: 'Anti-fraud', icon: '🛡️' },
    { id: 'ops-logovi', label: 'Logovi i greške', icon: '📋' },
  ]},
  { group: 'Sistem', items: [
    { id: 'sys-api', label: 'API izvori', icon: '🔌' },
    { id: 'sys-settings', label: 'Podešavanja', icon: '⚙️' },
  ]},
]

type AdminPage = 'dashboard'|'fin-racuni'|'fin-isplate'|'fin-uplate'|'fin-fakture'|
  'kam-kampanje'|'kam-dokazi'|'kam-uvoz'|'kam-banneri'|
  'lj-korisnici'|'lj-oglasivaci'|'lj-referral'|'lj-podrska'|
  'ops-antifraud'|'ops-logovi'|'sys-api'|'sys-settings'

const BACK: Partial<Record<AdminPage, { label: string; to: AdminPage }>> = {
  'fin-racuni':    { label: 'Nazad u Finansije', to: 'fin-isplate' },
  'fin-isplate':   { label: 'Nazad na pregled', to: 'dashboard' },
  'fin-uplate':    { label: 'Nazad u Finansije', to: 'fin-isplate' },
  'fin-fakture':   { label: 'Nazad u Finansije', to: 'fin-isplate' },
  'kam-kampanje':  { label: 'Nazad na pregled', to: 'dashboard' },
  'kam-dokazi':    { label: 'Nazad u Kampanje', to: 'kam-kampanje' },
  'kam-uvoz':      { label: 'Nazad u Kampanje', to: 'kam-kampanje' },
  'kam-banneri':   { label: 'Nazad u Kampanje', to: 'kam-kampanje' },
  'lj-korisnici':  { label: 'Nazad na pregled', to: 'dashboard' },
  'lj-oglasivaci': { label: 'Nazad u Ljude', to: 'lj-korisnici' },
  'lj-referral':   { label: 'Nazad u Ljude', to: 'lj-korisnici' },
  'lj-podrska':    { label: 'Nazad u Ljude', to: 'lj-korisnici' },
  'ops-antifraud': { label: 'Nazad na pregled', to: 'dashboard' },
  'ops-logovi':    { label: 'Nazad na pregled', to: 'dashboard' },
  'sys-api':       { label: 'Nazad na pregled', to: 'dashboard' },
  'sys-settings':  { label: 'Nazad na pregled', to: 'dashboard' },
}

const CRUMBS: Partial<Record<AdminPage, { label: string }[]>> = {
  'fin-racuni':    [{ label: 'Admin' }, { label: 'Finansije' }, { label: 'Računi platforme' }],
  'fin-isplate':   [{ label: 'Admin' }, { label: 'Finansije' }, { label: 'Isplate korisnika' }],
  'fin-uplate':    [{ label: 'Admin' }, { label: 'Finansije' }, { label: 'Uplate oglašivača' }],
  'fin-fakture':   [{ label: 'Admin' }, { label: 'Finansije' }, { label: 'Fakture' }],
  'kam-kampanje':  [{ label: 'Admin' }, { label: 'Kampanje' }],
  'kam-dokazi':    [{ label: 'Admin' }, { label: 'Kampanje' }, { label: 'Moderacija dokaza' }],
  'kam-uvoz':      [{ label: 'Admin' }, { label: 'Kampanje' }, { label: 'Uvoz zadataka' }],
  'kam-banneri':   [{ label: 'Admin' }, { label: 'Kampanje' }, { label: 'Banner slotovi' }],
  'lj-korisnici':  [{ label: 'Admin' }, { label: 'Ljudi' }, { label: 'Korisnici' }],
  'lj-oglasivaci': [{ label: 'Admin' }, { label: 'Ljudi' }, { label: 'Oglašivači' }],
  'lj-referral':   [{ label: 'Admin' }, { label: 'Ljudi' }, { label: 'Referral' }],
  'lj-podrska':    [{ label: 'Admin' }, { label: 'Ljudi' }, { label: 'Tiketi' }],
  'ops-antifraud': [{ label: 'Admin' }, { label: 'Operacije' }, { label: 'Anti-fraud' }],
  'ops-logovi':    [{ label: 'Admin' }, { label: 'Operacije' }, { label: 'Logovi' }],
  'sys-api':       [{ label: 'Admin' }, { label: 'Sistem' }, { label: 'API izvori' }],
  'sys-settings':  [{ label: 'Admin' }, { label: 'Sistem' }, { label: 'Podešavanja' }],
}

const usersData = [
  { id: 1, ime: 'Marko Marković', email: 'marko@primer.rs', tier: 'Explorer', zarada: '1.285 RSD', dokazi: 5, status: 'aktivno' },
  { id: 2, ime: 'Jelena Jovanović', email: 'jelena@primer.rs', tier: 'Trusted', zarada: '3.420 RSD', dokazi: 21, status: 'aktivno' },
  { id: 3, ime: 'Nikola Petrović', email: 'nikola@primer.rs', tier: 'Pro', zarada: '8.700 RSD', dokazi: 58, status: 'aktivno' },
  { id: 4, ime: 'Ana Stanković', email: 'ana@primer.rs', tier: 'Explorer', zarada: '0 RSD', dokazi: 1, status: 'blokirano' },
]

const campaignModData = [
  { id: 1, naziv: 'Google Play recenzije', oglasivac: 'Acme d.o.o.', budžet: '8.000 RSD', status: 'na_cekanju' },
  { id: 2, naziv: 'TikTok follow kampanja', oglasivac: 'StartupXYZ', budžet: '2.500 RSD', status: 'na_cekanju' },
  { id: 3, naziv: 'Instagram lajk — Jan', oglasivac: 'Acme d.o.o.', budžet: '5.000 RSD', status: 'aktivno' },
]

const proofsModData = [
  { id: 1, korisnik: 'marko_m', zadatak: 'Instagram lajk', kampanja: 'Instagram lajk — Jan', flag: 'OK', flagColor: 'text-emerald-600' },
  { id: 2, korisnik: 'jelena_j', zadatak: 'Instagram lajk', kampanja: 'Instagram lajk — Jan', flag: 'OK', flagColor: 'text-emerald-600' },
  { id: 3, korisnik: 'petar_k', zadatak: 'Google Play rec.', kampanja: 'Google Play recenzije', flag: '⚠ Sumnjivo', flagColor: 'text-amber-700' },
  { id: 4, korisnik: 'ana_s', zadatak: 'Instagram lajk', kampanja: 'Instagram lajk — Jan', flag: '⚠ Duplikat', flagColor: 'text-coral-700' },
]

const importSources = [
  { naziv: 'Partner API 1', url: 'https://partner1.example.com/feed', status: 'aktivno', sync: '23.12. 14:30', novi: 12, preskoceni: 3 },
  { naziv: 'Partner API 2', url: 'https://partner2.example.com/api', status: 'greska', sync: '22.12. 09:00', novi: 0, preskoceni: 0, greska: 'Endpoint ne vraća validan JSON' },
  { naziv: 'Partner API 3', url: 'https://partner3.example.com/tasks', status: 'obustavljeno', sync: '18.12. 11:00', novi: 0, preskoceni: 0 },
]

const payoutsData = [
  { id: 1, korisnik: 'Jelena J.', iznos: '2.500 RSD', metoda: 'Banka', trazeno: '23.12.2024', status: 'na_cekanju' },
  { id: 2, korisnik: 'Nikola P.', iznos: '5.000 RSD', metoda: 'Banka', trazeno: '22.12.2024', status: 'na_cekanju' },
  { id: 3, korisnik: 'Stefan K.', iznos: '1.800 RSD', metoda: 'Banka', trazeno: '20.12.2024', status: 'placeno' },
]

export default function AdminHub({ onNavigate }: { onNavigate: (id: string) => void }) {
  const [page, setPage] = useState<AdminPage>('dashboard')
  const [mobileOpen, setMobileOpen] = useState(false)
  const [dokaziTab, setDokaziTab] = useState('svi')
  const [logoutConfirm, setLogoutConfirm] = useState(false)
  const [blockUser, setBlockUser] = useState<{ id: number; ime: string; action: 'block' | 'unblock' } | null>(null)
  const [payoutAction, setPayoutAction] = useState<{ id: number; korisnik: string; iznos: string; type: 'approve' | 'reject' } | null>(null)
  const [paypalPayoutAction, setPaypalPayoutAction] = useState<{ id: number; korisnik: string; iznos: string } | null>(null)
  const [campAction, setCampAction] = useState<{ id: number; naziv: string; type: 'approve' | 'reject' } | null>(null)
  const [submissionAction, setSubmissionAction] = useState<{ id: number; naslov: string; type: 'approve' | 'reject' } | null>(null)
  const [userStatuses, setUserStatuses] = useState<Record<number, string>>({})
  const [payoutStatuses, setPayoutStatuses] = useState<Record<number, string>>({})
  const [campStatuses, setCampStatuses] = useState<Record<number, string>>({})
  const [metrics, setMetrics] = useState<AdminMetrics | null>(null)
  const [users, setUsers] = useState<AdminUser[]>([])
  const [campaigns, setCampaigns] = useState<AdminCampaign[]>([])
  const [submissions, setSubmissions] = useState<AdminSubmission[]>([])
  const [withdrawals, setWithdrawals] = useState<AdminWithdrawal[]>([])
  const [sources, setSources] = useState<TaskSource[]>([])
  const [tickets, setTickets] = useState<SupportTicket[]>([])
  const [settings, setSettings] = useState<AdminSetting[]>([])
  const [fraudOverview, setFraudOverview] = useState<FraudOverview | null>(null)
  const [settingDrafts, setSettingDrafts] = useState<Record<string, string>>({})
  const [dataError, setDataError] = useState('')
  const [savingAction, setSavingAction] = useState(false)
  const [sourceFormOpen, setSourceFormOpen] = useState(false)
  const [sourceName, setSourceName] = useState('')
  const [sourceUrl, setSourceUrl] = useState('')
  const [sourceKey, setSourceKey] = useState('')
  const { show: showToast, node: toastNode } = useToast()

  const refreshAdmin = async () => {
    try {
      const [dashboard, userData, campaignData, submissionData, withdrawalData, sourceData, ticketData, settingData, fraudData] = await Promise.all([
        api.adminDashboard(), api.adminUsers(), api.adminCampaigns(), api.adminSubmissions(), api.adminWithdrawals(), api.adminTaskSources(), api.adminTickets(), api.adminSettings(), api.adminFraudOverview(),
      ])
      setMetrics(dashboard.metrics)
      setUsers(userData.users)
      setCampaigns(campaignData.campaigns)
      setSubmissions(submissionData.submissions)
      setWithdrawals(withdrawalData.withdrawals)
      setSources(sourceData.sources)
      setTickets(ticketData.tickets)
      setSettings(settingData.settings)
      setFraudOverview(fraudData)
      setSettingDrafts(Object.fromEntries(settingData.settings.map(setting => [setting.key, setting.value])))
      setDataError('')
    } catch (error) {
      setDataError(error instanceof Error ? error.message : 'Admin podaci nisu dostupni.')
    }
  }

  useEffect(() => { void refreshAdmin() }, [])

  function goTo(p: AdminPage) { setPage(p) }
  const back = BACK[page]
  const crumbs = CRUMBS[page]

  function userStatus(id: number, orig: string) {
    const status = userStatuses[id] ?? orig
    return status === 'active' ? 'aktivno' : status === 'blocked' ? 'blokirano' : status === 'suspended' ? 'obustavljeno' : status
  }
  function payoutStatus(id: number, orig: string) {
    const status = payoutStatuses[id] ?? orig
    return status === 'pending' ? 'na_cekanju' : status === 'paid' ? 'placeno' : status === 'rejected' ? 'odbijeno' : status === 'processing' ? 'u_obradi' : status === 'payout_failed' ? 'greska' : status
  }
  function campStatus(id: number, orig: string) {
    const status = campStatuses[id] ?? orig
    return status === 'pending' ? 'na_cekanju' : status === 'active' ? 'aktivno' : status === 'rejected' ? 'odbijeno' : status === 'paused' ? 'obustavljeno' : status
  }
  function sourceStatus(status: string) { return status === 'active' ? 'aktivno' : status === 'paused' ? 'obustavljeno' : status === 'error' ? 'greska' : status }
  function ticketStatus(status: string) { return status === 'open' ? 'otvoren' : status === 'waiting' ? 'na_cekanju' : status === 'closed' ? 'zatvoreno' : status }

  async function saveSetting(setting: AdminSetting) {
    setSavingAction(true)
    try {
      await api.updateAdminSetting(setting.key, settingDrafts[setting.key] ?? '')
      await refreshAdmin()
      showToast('Podešavanje je sačuvano.', 'success')
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Podešavanje nije sačuvano.', 'error')
    } finally { setSavingAction(false) }
  }

  const sidebarFooter = (
    <div className="flex items-center gap-2.5">
      <div className="w-8 h-8 rounded-full bg-coral-600 flex items-center justify-center text-white text-sm font-bold">A</div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-white truncate">Administrator</p>
        <p className="text-xs" style={{ color: '#9AB1C8' }}>Ops pristup</p>
      </div>
      <button
        onClick={() => setLogoutConfirm(true)}
        className="text-xs px-2 py-1 rounded hover:bg-white/10 cursor-pointer font-medium"
        style={{ color: '#B9CDE0' }}
      >
        Odjava
      </button>
    </div>
  )

  return (
    <div className="flex h-screen bg-mint-50 text-ink overflow-hidden">
      {toastNode}

      <ConfirmModal
        open={logoutConfirm}
        title="Odjaviti se?"
        description="Bićeš odjavljen/a sa admin panela."
        confirmLabel="Da, odjavi me"
        cancelLabel="Otkaži"
        variant="danger"
        onConfirm={async () => { try { await api.logout() } finally { onNavigate('home') } }}
        onCancel={() => setLogoutConfirm(false)}
      />

      <ConfirmModal
        open={blockUser !== null}
        title={blockUser?.action === 'block' ? `Blokiraj korisnika?` : `Odblokiraj korisnika?`}
        description={blockUser?.action === 'block'
          ? `Korisnik ${blockUser?.ime} neće moći da pristupa platformi. Akcija se loguje u audit log.`
          : `Korisnik ${blockUser?.ime} ponovo dobija pristup platformi.`}
        confirmLabel={blockUser?.action === 'block' ? 'Blokiraj korisnika' : 'Odblokiraj korisnika'}
        cancelLabel="Otkaži"
        variant={blockUser?.action === 'block' ? 'danger' : 'success'}
        onConfirm={async () => {
          if (!blockUser) return
          setSavingAction(true)
          try {
            const newStatus = blockUser.action === 'block' ? 'blocked' : 'active'
            await api.updateAdminUser(blockUser.id, newStatus)
            await refreshAdmin()
            showToast(blockUser.action === 'block' ? `${blockUser.ime} je blokiran/a.` : `${blockUser.ime} je odblokirano.`, blockUser.action === 'block' ? 'error' : 'success')
            setBlockUser(null)
          } catch (error) {
            showToast(error instanceof Error ? error.message : 'Status korisnika nije promenjen.', 'error')
          } finally { setSavingAction(false) }
        }}
        onCancel={() => setBlockUser(null)}
      />

      <ConfirmModal
        open={payoutAction !== null}
        title={payoutAction?.type === 'approve' ? 'Odobri isplatu?' : 'Odbij isplatu?'}
        description={payoutAction?.type === 'approve'
          ? `Isplata od ${payoutAction?.iznos} za ${payoutAction?.korisnik} biće pokrenuta.`
          : `Korisnik ${payoutAction?.korisnik} neće primiti isplatu od ${payoutAction?.iznos}.`}
        confirmLabel={payoutAction?.type === 'approve' ? 'Odobri isplatu' : 'Odbij isplatu'}
        cancelLabel="Otkaži"
        variant={payoutAction?.type === 'approve' ? 'success' : 'danger'}
        onConfirm={async () => {
          if (!payoutAction) return
          setSavingAction(true)
          try {
            await api.updateAdminWithdrawal(payoutAction.id, payoutAction.type === 'approve' ? 'paid' : 'rejected')
            await refreshAdmin()
            showToast(payoutAction.type === 'approve' ? 'Isplata je označena kao plaćena.' : 'Isplata je odbijena i saldo je vraćen.', payoutAction.type === 'approve' ? 'success' : 'error')
            setPayoutAction(null)
          } catch (error) {
            showToast(error instanceof Error ? error.message : 'Isplata nije promenjena.', 'error')
          } finally { setSavingAction(false) }
        }}
        onCancel={() => setPayoutAction(null)}
      />

      <ConfirmModal
        open={paypalPayoutAction !== null}
        title="Poslati stvarnu PayPal isplatu?"
        description={`Poslaćeš ${paypalPayoutAction?.iznos} korisniku ${paypalPayoutAction?.korisnik} na PayPal email koji je korisnik uneo. Isplata je prethodno prošla fraud proveru. Nakon slanja, prvo ćeš morati da osvežiš PayPal status pre konačnog označavanja kao plaćene.`}
        confirmLabel="Da, pošalji na PayPal"
        cancelLabel="Otkaži"
        variant="danger"
        onConfirm={async () => {
          if (!paypalPayoutAction) return
          setSavingAction(true)
          try {
            await api.sendAdminPayPalPayout(paypalPayoutAction.id)
            await refreshAdmin()
            showToast('PayPal batch je poslat. Osveži status dok PayPal ne potvrdi obradu.', 'success')
            setPaypalPayoutAction(null)
          } catch (error) {
            showToast(error instanceof Error ? error.message : 'PayPal isplata nije poslata.', 'error')
          } finally { setSavingAction(false) }
        }}
        onCancel={() => setPaypalPayoutAction(null)}
      />

      <ConfirmModal
        open={campAction !== null}
        title={campAction?.type === 'approve' ? 'Odobri kampanju?' : 'Odbij kampanju?'}
        description={campAction?.type === 'approve'
          ? `Kampanja "${campAction?.naziv}" postaje aktivna i vidljiva korisnicima.`
          : `Kampanja "${campAction?.naziv}" je odbijena. Oglašivač će biti obavešten.`}
        confirmLabel={campAction?.type === 'approve' ? 'Aktiviraj kampanju' : 'Odbij kampanju'}
        cancelLabel="Otkaži"
        variant={campAction?.type === 'approve' ? 'success' : 'danger'}
        onConfirm={async () => {
          if (!campAction) return
          setSavingAction(true)
          try {
            await api.updateAdminCampaign(campAction.id, campAction.type === 'approve' ? 'active' : 'rejected')
            await refreshAdmin()
            showToast(campAction.type === 'approve' ? 'Kampanja je aktivirana.' : 'Kampanja je odbijena.', campAction.type === 'approve' ? 'success' : 'error')
            setCampAction(null)
          } catch (error) {
            showToast(error instanceof Error ? error.message : 'Kampanja nije promenjena.', 'error')
          } finally { setSavingAction(false) }
        }}
        onCancel={() => setCampAction(null)}
      />

      <ConfirmModal
        open={submissionAction !== null}
        title={submissionAction?.type === 'approve' ? 'Odobri dokaz?' : 'Odbij dokaz?'}
        description={submissionAction?.type === 'approve'
          ? `Dokaz za „${submissionAction?.naslov}” biće odobren, a nagrada prebačena na korisnički saldo.`
          : `Dokaz za „${submissionAction?.naslov}” biće odbijen. Korisnik neće dobiti nagradu.`}
        confirmLabel={submissionAction?.type === 'approve' ? 'Odobri dokaz' : 'Odbij dokaz'}
        cancelLabel="Otkaži"
        variant={submissionAction?.type === 'approve' ? 'success' : 'danger'}
        onConfirm={async () => {
          if (!submissionAction) return
          setSavingAction(true)
          try {
            await api.reviewAdminSubmission(submissionAction.id, submissionAction.type === 'approve' ? 'approved' : 'rejected')
            await refreshAdmin()
            showToast(submissionAction.type === 'approve' ? 'Dokaz je odobren i saldo je ažuriran.' : 'Dokaz je odbijen.', submissionAction.type === 'approve' ? 'success' : 'error')
            setSubmissionAction(null)
          } catch (error) {
            showToast(error instanceof Error ? error.message : 'Dokaz nije obrađen.', 'error')
          } finally { setSavingAction(false) }
        }}
        onCancel={() => setSubmissionAction(null)}
      />

      {mobileOpen && <div className="fixed inset-0 bg-black/40 z-40 lg:hidden" onClick={() => setMobileOpen(false)} />}
      <div className="hidden lg:flex shrink-0">
        <Sidebar groups={navGroups} active={page} onNavigate={p => goTo(p as AdminPage)} footer={sidebarFooter} />
      </div>
      {mobileOpen && (
        <div className="fixed left-0 top-0 h-full z-50 lg:hidden">
          <Sidebar groups={navGroups} active={page} onNavigate={p => { goTo(p as AdminPage); setMobileOpen(false) }} footer={sidebarFooter} isMobile onClose={() => setMobileOpen(false)} />
        </div>
      )}

      <div className="flex-1 flex flex-col overflow-hidden">
        <TopBar
          onMenuClick={() => setMobileOpen(true)}
          pageTitle="Operations Hub"
          badge="Admin"
          onNavigate={onNavigate}
          actions={<span className="text-xs text-ink-3 font-mono hidden md:block">klikzarada.rs</span>}
        />

        <main className="flex-1 overflow-y-auto bg-mint-50">
          <div className="max-w-5xl mx-auto px-4 py-6">
            {dataError && <div className="mb-4"><Alert type="error">{dataError}</Alert></div>}
            {page !== 'dashboard' && (back || crumbs) && (
              <PageHeader
                breadcrumbs={crumbs}
                onBack={back ? () => goTo(back.to) : undefined}
                backLabel={back?.label}
              />
            )}

            {page === 'dashboard' && (
              <div className="space-y-5">
                <div>
                  <h1 className="text-xl font-extrabold text-ink">Operativni pregled</h1>
                  <p className="text-sm text-ink-2 mt-0.5">Pregled stvarnog operativnog stanja platforme.</p>
                </div>
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                  <StatCard label="Ukupno korisnika" value={String(metrics?.users ?? 0)} icon="👥" accent="blue" />
                  <StatCard label="Aktivnih kampanja" value={String(metrics?.active_tasks ?? 0)} icon="🎯" accent="green" />
                  <StatCard label="Dokazi na čekanju" value={String(metrics?.pending_submissions ?? 0)} icon="📎" accent="orange" />
                  <StatCard label="Isplate na čekanju" value={String(metrics?.pending_withdrawals ?? 0)} icon="💸" accent="purple" />
                </div>
                <div className="space-y-2">
                  {(metrics?.pending_campaigns ?? 0) > 0 && <Alert type="warning"><strong>{metrics?.pending_campaigns} kampanja</strong> čeka moderaciju pre aktivacije.</Alert>}
                  {sources.some(source => source.status === 'error') && <Alert type="error">Najmanje jedan partner izvor je u grešci. Proveri API izvore pre sledećeg uvoza.</Alert>}
                </div>
                <div className="grid sm:grid-cols-3 gap-4">
                  {[
                    { label: 'Finansije', items: [`Isplate na čekanju: ${metrics?.pending_withdrawals ?? 0}`, `Rezervisan budžet: ${new Intl.NumberFormat('sr-RS').format(metrics?.reserved_budget_rsd ?? 0)} RSD`, 'Fakture: uskoro'], page: 'fin-isplate' as AdminPage, color: 'bg-emerald-50 border-emerald-200' },
                    { label: 'Kampanje', items: [`Na čekanju: ${metrics?.pending_campaigns ?? 0}`, `Aktivnih: ${metrics?.active_tasks ?? 0}`, `Moderacija dokaza: ${metrics?.pending_submissions ?? 0}`], page: 'kam-kampanje' as AdminPage, color: 'bg-blue-50 border-blue-200' },
                    { label: 'Korisnici', items: [`Korisnici: ${metrics?.users ?? 0}`, `Oglašivači: ${metrics?.advertisers ?? 0}`, 'Tiketi: uskoro'], page: 'lj-korisnici' as AdminPage, color: 'bg-violet-50 border-violet-200' },
                  ].map(g => (
                    <div key={g.label} className={`border rounded-xl p-4 ${g.color}`}>
                      <h3 className="text-sm font-bold text-ink mb-2">{g.label}</h3>
                      <ul className="space-y-1 mb-3">
                        {g.items.map(i => <li key={i} className="text-xs text-ink-2">{i}</li>)}
                      </ul>
                      <Btn onClick={() => goTo(g.page)} size="sm" variant="secondary">Prikaži →</Btn>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {page === 'fin-isplate' && (
              <div>
                <SectionHeader title="Isplate korisnika" description="Odobri ili odbij zahteve za isplatu." />
                <Card>
                  <Table
                    headers={['Korisnik', 'Iznos', 'Metoda', 'Traženo', 'Status', 'Akcija']}
                    rows={withdrawals.map(p => {
                      const st = payoutStatus(p.id, p.status)
                      return [
                        <span className="font-semibold text-ink">{p.user_name}</span>,
                        <span className="font-mono font-semibold text-emerald-600">{new Intl.NumberFormat('sr-RS').format(p.amount_rsd)} RSD</span>,
                        <span>{p.payment_method}</span>,
                        <span className="font-mono text-xs">{p.created_at ? new Intl.DateTimeFormat('sr-RS').format(new Date(p.created_at)) : '—'}</span>,
                        <StatusBadge status={st} />,
                        st === 'na_cekanju'
                          ? <div className="flex gap-1.5">
                              {p.payment_method.toLowerCase().includes('paypal')
                                ? <Btn size="sm" variant="success" disabled={savingAction} onClick={() => setPaypalPayoutAction({ id: p.id, korisnik: p.user_name, iznos: `${new Intl.NumberFormat('sr-RS').format(p.amount_rsd)} RSD` })}>Pošalji PayPal</Btn>
                                : <Btn size="sm" variant="success" disabled={savingAction} onClick={() => setPayoutAction({ id: p.id, korisnik: p.user_name, iznos: `${new Intl.NumberFormat('sr-RS').format(p.amount_rsd)} RSD`, type: 'approve' })}>Označi plaćeno</Btn>}
                              <Btn size="sm" variant="danger" disabled={savingAction} onClick={() => setPayoutAction({ id: p.id, korisnik: p.user_name, iznos: `${new Intl.NumberFormat('sr-RS').format(p.amount_rsd)} RSD`, type: 'reject' })}>Odbij</Btn>
                            </div>
                          : st === 'u_obradi' && p.paypal_payout
                            ? <Btn size="sm" variant="secondary" disabled={savingAction} onClick={async () => {
                                setSavingAction(true)
                                try { await api.syncAdminPayPalPayout(p.id); await refreshAdmin(); showToast('PayPal status je osvežen.', 'success') }
                                catch (error) { showToast(error instanceof Error ? error.message : 'PayPal status nije osvežen.', 'error') }
                                finally { setSavingAction(false) }
                              }}>Proveri PayPal</Btn>
                          : st === 'greska'
                            ? <Btn size="sm" variant="danger" disabled={savingAction} onClick={() => setPayoutAction({ id: p.id, korisnik: p.user_name, iznos: `${new Intl.NumberFormat('sr-RS').format(p.amount_rsd)} RSD`, type: 'reject' })}>Vrati saldo</Btn>
                          : <span className="text-xs text-ink-3">—</span>,
                      ]
                    })}
                  />
                </Card>
              </div>
            )}

            {page === 'fin-uplate' && (
              <div>
                <SectionHeader title="Uplate oglašivača" />
                <EmptyState icon="💳" title="Nema novih uplata" description="Sve uplate su obrađene." />
              </div>
            )}

            {page === 'fin-fakture' && (
              <div>
                <SectionHeader title="Fakture" />
                <EmptyState icon="🧾" title="Nema faktura" description="Fakture će biti prikazane kada budu generisane." />
              </div>
            )}

            {page === 'fin-racuni' && (
              <div className="space-y-4">
                <SectionHeader title="Računi platforme" />
                <Alert type="warning">Podaci o bankovnom računu su zaštićeni. Prikazani samo ovlašćenim adminima.</Alert>
                <Card className="p-5">
                  <p className="text-sm text-ink-2 mb-3">Podaci o poslovnom računu platforme dostupni su u sistemskim podešavanjima. Pristup je ograničen i logovan u audit log-u.</p>
                  <Btn onClick={() => goTo('sys-settings')} variant="secondary" size="sm">Sistemska podešavanja</Btn>
                </Card>
              </div>
            )}

            {page === 'kam-kampanje' && (
              <div>
                <SectionHeader title="Kampanje" description="Moderacija novih kampanja pre aktivacije." />
                <Card>
                  <Table
                    headers={['Naziv', 'Oglašivač', 'Budžet', 'Status', 'Akcija']}
                    rows={campaigns.map(c => {
                      const st = campStatus(c.id, c.status)
                      return [
                        <span className="font-semibold text-ink">{c.title}</span>,
                        <span className="text-sm text-ink-2">{c.advertiser_name}</span>,
                        <span className="font-mono">{new Intl.NumberFormat('sr-RS').format(c.reward_rsd * c.total_slots * 1.2)} RSD</span>,
                        <StatusBadge status={st} />,
                        st === 'na_cekanju'
                          ? <div className="flex gap-1.5">
                              <Btn size="sm" variant="success" disabled={savingAction} onClick={() => setCampAction({ id: c.id, naziv: c.title, type: 'approve' })}>Odobri</Btn>
                              <Btn size="sm" variant="danger" disabled={savingAction} onClick={() => setCampAction({ id: c.id, naziv: c.title, type: 'reject' })}>Odbij</Btn>
                            </div>
                          : <Btn size="sm" variant="ghost">Detalji</Btn>,
                      ]
                    })}
                  />
                </Card>
              </div>
            )}

            {page === 'kam-dokazi' && (
              <div>
                <SectionHeader title="Moderacija dokaza" description="Anti-fraud signali su automatski označeni." />
                <Tabs
                  tabs={[{ id: 'svi', label: 'Svi' }, { id: 'ok', label: 'OK' }, { id: 'flag', label: 'Flagovano' }]}
                  active={dokaziTab}
                  onChange={setDokaziTab}
                />
                <Card>
                  <Table
                    headers={['Korisnik', 'Zadatak', 'Kampanja', 'Anti-fraud', 'Akcija']}
                    rows={submissions
                      .filter(submission => dokaziTab === 'svi' || (dokaziTab === 'ok' ? submission.status !== 'pending' : submission.status === 'pending'))
                      .map(submission => [
                        <span className="font-mono text-xs">{submission.user_name}</span>,
                        <span>{submission.task_title}</span>,
                        <span className="text-xs text-ink-3">{submission.proof || 'Bez dodatne napomene'}</span>,
                        <span className={`text-xs font-bold ${submission.status === 'pending' ? 'text-amber-700' : submission.status === 'approved' ? 'text-emerald-600' : 'text-coral-700'}`}>{submission.status === 'pending' ? 'Čeka pregled' : submission.status === 'approved' ? 'Odobreno' : 'Odbijeno'}</span>,
                        submission.status === 'pending'
                          ? <div className="flex gap-1.5">
                              <Btn size="sm" variant="success" disabled={savingAction} onClick={() => setSubmissionAction({ id: submission.id, naslov: submission.task_title, type: 'approve' })}>✓</Btn>
                              <Btn size="sm" variant="danger" disabled={savingAction} onClick={() => setSubmissionAction({ id: submission.id, naslov: submission.task_title, type: 'reject' })}>✗</Btn>
                            </div>
                          : <span className="text-xs text-ink-3">—</span>,
                      ])}
                  />
                </Card>
              </div>
            )}

            {page === 'kam-uvoz' && (
              <div>
                <SectionHeader title="Uvoz zadataka" description="Upravljanje eksternim API izvorima. Svi uvozi čekaju moderaciju." />
                <Alert type="info">Zadaci uvezeni od partnera ne postaju vidljivi korisnicima dok admin ne odobri svaki zadatak posebno.</Alert>
                <div className="mt-4 space-y-3">
                  {sources.map(src => (
                    <Card key={src.id} className="p-4">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <p className="font-bold text-ink">{src.name}</p>
                            <StatusBadge status={sourceStatus(src.status)} />
                          </div>
                          <p className="text-xs text-ink-3 font-mono truncate">{src.endpoint_url}</p>
                          <div className="flex gap-4 mt-2">
                            <span className="text-xs text-ink-2">Poslednja sync: {src.last_sync_at ? new Intl.DateTimeFormat('sr-RS').format(new Date(src.last_sync_at)) : 'nije pokrenuta'}</span>
                          </div>
                        </div>
                        <div className="flex gap-2 shrink-0">
                          {src.status === 'active' && <Btn size="sm" variant="secondary" disabled={savingAction} onClick={async () => { setSavingAction(true); try { const result = await api.syncTaskSource(src.id); await refreshAdmin(); showToast(`${result.created} zadataka je uvezeno, ${result.skipped} preskočeno.`, 'success') } catch (error) { showToast(error instanceof Error ? error.message : 'Uvoz nije uspeo.', 'error') } finally { setSavingAction(false) } }}>Sync</Btn>}
                          {src.status === 'error' && <Btn size="sm" variant="danger" onClick={() => showToast('Proveri HTTPS endpoint i JSON format izvora pre novog pokušaja.', 'warning')}>Dijagnostika</Btn>}
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
                <div className="mt-4">
                  <Btn variant="secondary" size="sm" onClick={() => goTo('sys-api')}>+ Dodaj novi izvor</Btn>
                </div>
              </div>
            )}

            {page === 'kam-banneri' && (
              <div>
                <SectionHeader title="Banner slotovi" description="Reklamni prostor na platformi. Sponzorisani sadržaj mora biti označen." />
                <div className="grid sm:grid-cols-2 gap-3">
                  {[
                    { naziv: 'Header baner — početna', status: 'aktivno', oglasivac: 'Acme d.o.o.', ističe: '31.12.2024', cena: '2.000 RSD / mesec' },
                    { naziv: 'Sidebar — korisnički panel', status: 'obustavljeno', oglasivac: '—', ističe: '—', cena: '1.500 RSD / mesec' },
                  ].map(b => (
                    <Card key={b.naziv} className="p-4">
                      <div className="flex items-start justify-between mb-3">
                        <p className="font-bold text-ink text-sm">{b.naziv}</p>
                        <StatusBadge status={b.status} />
                      </div>
                      <div className="space-y-1 text-xs text-ink-2">
                        <p>Oglašivač: <span className="text-ink font-medium">{b.oglasivac}</span></p>
                        <p>Ističe: <span className="text-ink font-medium">{b.ističe}</span></p>
                        <p>Cena: <span className="font-mono font-semibold text-emerald-600">{b.cena}</span></p>
                      </div>
                      <div className="flex gap-2 mt-3">
                        <Btn size="sm" variant="ghost">Uredi</Btn>
                        {b.status === 'aktivno' && <Btn size="sm" variant="danger">Pauziraj</Btn>}
                      </div>
                    </Card>
                  ))}
                </div>
              </div>
            )}

            {page === 'lj-korisnici' && (
              <div>
                <SectionHeader title="Korisnici" />
                <Card>
                  <Table
                    headers={['Ime', 'Email', 'Tier', 'Zarada', 'Dokazi', 'Status', 'Akcija']}
                    rows={users.filter(u => u.role === 'korisnik').map(u => {
                      const st = userStatus(u.id, u.status)
                      return [
                        <span className="font-semibold text-ink">{u.full_name}</span>,
                        <span className="text-xs font-mono text-ink-2">{u.email}</span>,
                        <span className="text-xs font-medium">{u.level}</span>,
                        <span className="font-mono text-xs font-semibold text-emerald-600">{new Intl.NumberFormat('sr-RS').format(u.lifetime_earned_rsd)} RSD</span>,
                        <span className="font-mono text-xs">—</span>,
                        <StatusBadge status={st} />,
                        <div className="flex gap-1.5">
                          <Btn size="sm" variant="ghost">Profil</Btn>
                          {st !== 'blokirano'
                            ? <Btn size="sm" variant="danger" disabled={savingAction} onClick={() => setBlockUser({ id: u.id, ime: u.full_name, action: 'block' })}>Blokiraj</Btn>
                            : <Btn size="sm" variant="success" disabled={savingAction} onClick={() => setBlockUser({ id: u.id, ime: u.full_name, action: 'unblock' })}>Odblokiraj</Btn>
                          }
                        </div>,
                      ]
                    })}
                  />
                </Card>
              </div>
            )}

            {page === 'lj-oglasivaci' && (
              <div>
                <SectionHeader title="Oglašivači" />
                <Card>
                  <Table
                    headers={['Oglašivač', 'Email', 'Kampanje', 'Potrošeno', 'Status']}
                    rows={users.filter(user => user.role === 'oglasivac').map(advertiser => [
                      <span className="font-semibold text-ink">{advertiser.company_name || advertiser.full_name}</span>,
                      <span className="font-mono text-xs text-ink-2">{advertiser.email}</span>,
                      <span className="font-mono">{campaigns.filter(campaign => campaign.advertiser_name === advertiser.full_name).length}</span>,
                      <span className="font-mono text-xs font-semibold text-amber-700">{new Intl.NumberFormat('sr-RS').format(advertiser.advertiser_spent_rsd)} RSD</span>,
                      <StatusBadge status={userStatus(advertiser.id, advertiser.status)} />,
                    ])}
                  />
                </Card>
              </div>
            )}

            {page === 'lj-referral' && (
              <div>
                <SectionHeader title="Referral program" />
                <div className="grid grid-cols-2 gap-3 mb-4">
                  <StatCard label="Ukupno referral veza" value="—" accent="blue" />
                  <StatCard label="Isplaćeno bonusa" value="—" accent="green" />
                </div>
                <EmptyState icon="🔗" title="Nema referral podataka" description="Statistika će se pojaviti kada korisnici počnu da pozivaju prijatelje." />
              </div>
            )}

            {page === 'lj-podrska' && (
              <div className="space-y-4">
                <SectionHeader title="Tiketi i podrška" description="Stvarni zahtevi korisnika, bez demo poruka." />
                {tickets.length === 0 ? <EmptyState icon="✅" title="Nema otvorenih tiketa" description="Novi zahtevi korisnika pojaviće se ovde." /> : (
                  <Card>
                    <Table
                      headers={['Tiket', 'Korisnik', 'Kategorija', 'Ažuriran', 'Status', 'Akcija']}
                      rows={tickets.map(ticket => [
                        <div><p className="font-semibold text-ink">#{ticket.id} · {ticket.subject}</p><p className="text-xs text-ink-3">Prioritet: {ticket.priority}</p></div>,
                        <span className="text-sm text-ink-2">{ticket.user_name}</span>,
                        <span className="text-sm text-ink-2">{ticket.category}</span>,
                        <span className="text-xs text-ink-3">{ticket.updated_at ? new Date(ticket.updated_at).toLocaleString('sr-RS') : '—'}</span>,
                        <StatusBadge status={ticketStatus(ticket.status)} />,
                        ticket.status === 'closed'
                          ? <Btn size="sm" variant="secondary" disabled={savingAction} onClick={async () => { try { await api.updateAdminTicket(ticket.id, 'open'); await refreshAdmin(); showToast('Tiket je ponovo otvoren.', 'success') } catch (error) { showToast(error instanceof Error ? error.message : 'Tiket nije promenjen.', 'error') } }}>Otvori</Btn>
                          : <Btn size="sm" variant="success" disabled={savingAction} onClick={async () => { try { await api.updateAdminTicket(ticket.id, 'closed'); await refreshAdmin(); showToast('Tiket je zatvoren.', 'success') } catch (error) { showToast(error instanceof Error ? error.message : 'Tiket nije promenjen.', 'error') } }}>Zatvori</Btn>,
                      ])}
                    />
                  </Card>
                )}
              </div>
            )}

            {page === 'ops-antifraud' && (
              <div className="space-y-4">
                <SectionHeader
                  title="Anti-fraud kontrola"
                  description="Server proverava uređaj, mrežu, vreme na zadatku i aktivnost pre nego što nagrada ode na čekanje."
                  action={<Btn size="sm" variant="secondary" onClick={() => void refreshAdmin()}>Osveži podatke</Btn>}
                />
                {fraudOverview ? <>
                  {fraudOverview.summary.open_signals > 0 ? (
                    <Alert type="warning"><strong>{fraudOverview.summary.open_signals} otvorenih signala</strong> čeka pregled. Isplate korisnika sa visokim rizikom ostaju blokirane dok signal ne pregledaš.</Alert>
                  ) : (
                    <Alert type="success">Nema otvorenih fraud signala. Sistem i dalje beleži proveru vremena, fokusa i uređaja.</Alert>
                  )}

                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                    <StatCard label="Otvoreni signali" value={String(fraudOverview.summary.open_signals)} icon="⚠️" accent={fraudOverview.summary.open_signals ? 'orange' : 'green'} />
                    <StatCard label="Visok rizik" value={String(fraudOverview.summary.high_risk_users)} icon="🛑" accent={fraudOverview.summary.high_risk_users ? 'red' : 'green'} />
                    <StatCard label="Flagovane sesije" value={String(fraudOverview.summary.flagged_sessions)} icon="🕒" accent="purple" />
                    <StatCard label="Deljeni uređaji" value={String(fraudOverview.summary.shared_devices)} icon="📱" accent="blue" />
                  </div>

                  <Card>
                    <div className="p-4 border-b border-frame">
                      <h3 className="font-bold text-ink">Signali za ručni pregled</h3>
                      <p className="text-xs text-ink-3 mt-0.5">Mreže su prikazane u maskiranom obliku; ne čuvamo sirove identifikatore uređaja u admin prikazu.</p>
                    </div>
                    {fraudOverview.signals.filter(signal => signal.status === 'open').length === 0 ? (
                      <EmptyState icon="✅" title="Red za pregled je prazan" description="Novi rizični nalozi i sesije pojaviće se ovde." />
                    ) : (
                      <Table
                        headers={['Korisnik', 'Signal', 'Rizik', 'Mreža / detalj', 'Vreme', 'Akcije']}
                        rows={fraudOverview.signals.filter(signal => signal.status === 'open').map(signal => {
                          const reason = typeof signal.details.reason === 'string' ? signal.details.reason : signal.signal_type
                          const network = typeof signal.details.network === 'string' ? signal.details.network : 'Nije dostupno'
                          const highRisk = signal.risk_score >= 70
                          return [
                            <div><p className="font-semibold text-ink">{signal.user_name}</p><p className="text-xs text-ink-3">{signal.user_email ?? 'Bez emaila'}</p></div>,
                            <span className="text-sm text-ink-2">{reason}</span>,
                            <span className={`font-mono text-xs font-bold ${highRisk ? 'text-coral-700' : 'text-amber-700'}`}>{signal.risk_score}/100</span>,
                            <div><p className="text-xs text-ink-2">{network}</p><p className="text-xs text-ink-3 truncate max-w-48">{signal.signal_type}</p></div>,
                            <span className="text-xs text-ink-3">{signal.created_at ? new Date(signal.created_at).toLocaleString('sr-RS') : '—'}</span>,
                            <div className="flex gap-2">
                              <Btn size="sm" variant="secondary" disabled={savingAction} onClick={async () => {
                                setSavingAction(true)
                                try { await api.reviewAdminFraudSignal(signal.id, 'reviewed'); await refreshAdmin(); showToast('Signal je označen kao pregledan.', 'success') }
                                catch (error) { showToast(error instanceof Error ? error.message : 'Signal nije promenjen.', 'error') }
                                finally { setSavingAction(false) }
                              }}>Pregledano</Btn>
                              {signal.user_id && <Btn size="sm" variant="danger" disabled={savingAction} onClick={() => setBlockUser({ id: signal.user_id as number, ime: signal.user_name, action: 'block' })}>Blokiraj</Btn>}
                            </div>,
                          ]
                        })}
                      />
                    )}
                  </Card>

                  <div className="grid lg:grid-cols-2 gap-4">
                    <Card>
                      <div className="p-4 border-b border-frame"><h3 className="font-bold text-ink">Sesije provere zadataka</h3></div>
                      {fraudOverview.sessions.length === 0 ? <EmptyState icon="🕒" title="Nema sesija" description="Provera se pojavljuje kada korisnik započne zadatak." /> : <Table
                        headers={['Korisnik', 'Zadatak', 'Aktivnost', 'Rizik', 'Status']}
                        rows={fraudOverview.sessions.slice(0, 20).map(session => [
                          <span className="text-sm font-medium">{session.user_name}</span>,
                          <span className="text-xs text-ink-2 max-w-48 truncate block">{session.task_title}</span>,
                          <span className="font-mono text-xs">{session.active_seconds}/{session.required_seconds}s · {session.activity_events} događaja</span>,
                          <span className={`font-mono text-xs font-bold ${session.risk_score >= 70 ? 'text-coral-700' : 'text-ink-2'}`}>{session.risk_score}/100</span>,
                          <StatusBadge status={session.status === 'flagged' ? 'na_proveri' : session.status === 'ready' ? 'aktivno' : session.status} />,
                        ])}
                      />}
                    </Card>
                    <Card className="p-5">
                      <h3 className="font-bold text-ink">Aktivna pravila</h3>
                      <dl className="mt-3 space-y-3 text-sm">
                        <div className="flex justify-between gap-4"><dt className="text-ink-2">Dnevni broj zadataka</dt><dd className="font-mono font-bold">{fraudOverview.policy.daily_task_limit}</dd></div>
                        <div className="flex justify-between gap-4"><dt className="text-ink-2">Dnevna zarada</dt><dd className="font-mono font-bold">{new Intl.NumberFormat('sr-RS').format(fraudOverview.policy.daily_earnings_rsd)} RSD</dd></div>
                        <div className="flex justify-between gap-4"><dt className="text-ink-2">Minimum aktivnosti</dt><dd className="font-mono font-bold">{fraudOverview.policy.minimum_activity_events} događaja</dd></div>
                        <div className="flex justify-between gap-4"><dt className="text-ink-2">IP/VPN reputacija</dt><dd className={fraudOverview.policy.ip_reputation_enabled ? 'font-semibold text-emerald-700' : 'font-semibold text-amber-700'}>{fraudOverview.policy.ip_reputation_enabled ? 'Uključena' : 'Nije podešena'}</dd></div>
                      </dl>
                      {!fraudOverview.policy.ip_reputation_enabled && <p className="mt-4 text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-lg p-3">Dodaj `IPQUALITYSCORE_API_KEY` u Render samo ako želiš dodatnu proveru VPN/proxy reputacije. Osnovne provere uređaja, mreže, fokusa i tajmera rade i bez spoljnog servisa.</p>}
                    </Card>
                  </div>
                </> : <EmptyState icon="🛡️" title="Učitavam anti-fraud podatke" description="Ako se poruka ne promeni, proveri administratorsku prijavu i API konekciju." />}
              </div>
            )}

            {page === 'ops-logovi' && (
              <div>
                <SectionHeader title="Logovi i greške" />
                <Card className="p-4">
                  <div className="font-mono text-xs space-y-0">
                    {[
                      { time: '14:32:01', level: 'ERROR', msg: 'Partner API 2: Connection timeout', color: 'text-coral-600' },
                      { time: '14:30:00', level: 'INFO',  msg: 'Import sync started: Partner API 1', color: 'text-ink-3' },
                      { time: '14:30:12', level: 'INFO',  msg: 'Import sync done: 12 new, 3 skipped', color: 'text-ink-3' },
                      { time: '13:45:22', level: 'WARN',  msg: 'Anti-fraud: 2 proofs flagged', color: 'text-amber-700' },
                      { time: '12:00:00', level: 'INFO',  msg: 'Daily payout batch: 3 pending', color: 'text-ink-3' },
                    ].map((l, i) => (
                      <div key={i} className="flex gap-3 py-2 border-b border-frame last:border-0">
                        <span className="text-ink-3 w-20 shrink-0">{l.time}</span>
                        <span className={`w-12 shrink-0 font-bold ${l.color}`}>{l.level}</span>
                        <span className="text-ink-2">{l.msg}</span>
                      </div>
                    ))}
                  </div>
                </Card>
              </div>
            )}

            {page === 'sys-api' && (
              <div>
                <SectionHeader title="API izvori zadataka" description="Konfiguracija partner integacija." />
                <Card className="p-5 mb-4">
                  <div className="flex items-center justify-between gap-3 mb-3">
                    <div>
                      <h3 className="font-bold text-ink">Dodaj partner izvor</h3>
                      <p className="text-xs text-ink-3 mt-0.5">Prihvatamo samo javno dostupan HTTPS JSON feed. Ključ se ne prikazuje nakon čuvanja.</p>
                    </div>
                    <Btn size="sm" variant="secondary" onClick={() => setSourceFormOpen(open => !open)}>{sourceFormOpen ? 'Zatvori' : '+ Dodaj izvor'}</Btn>
                  </div>
                  {sourceFormOpen && <div className="grid gap-3">
                    <input value={sourceName} onChange={event => setSourceName(event.target.value)} placeholder="Naziv partnera" className="bg-white border border-frame text-ink rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
                    <input value={sourceUrl} onChange={event => setSourceUrl(event.target.value)} placeholder="https://partner.example/api/tasks" type="url" className="bg-white border border-frame text-ink rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
                    <input value={sourceKey} onChange={event => setSourceKey(event.target.value)} placeholder="API ključ (opciono)" type="password" autoComplete="new-password" className="bg-white border border-frame text-ink rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
                    <div className="flex gap-2">
                      <Btn disabled={savingAction || !sourceName.trim() || !sourceUrl.trim()} onClick={async () => { setSavingAction(true); try { await api.createTaskSource({ name: sourceName, endpoint_url: sourceUrl, api_key: sourceKey || undefined, import_mode: 'review' }); await refreshAdmin(); setSourceName(''); setSourceUrl(''); setSourceKey(''); setSourceFormOpen(false); showToast('Partner izvor je sačuvan. Prvi uvoz moraš ručno pokrenuti.', 'success') } catch (error) { showToast(error instanceof Error ? error.message : 'Izvor nije sačuvan.', 'error') } finally { setSavingAction(false) } }}>Sačuvaj izvor</Btn>
                      <Btn variant="ghost" onClick={() => setSourceFormOpen(false)}>Otkaži</Btn>
                    </div>
                  </div>}
                </Card>
                <div className="space-y-3">
                  {sources.map(src => (
                    <Card key={src.id} className="p-4 flex items-center justify-between gap-4">
                      <div>
                        <p className="font-bold text-ink">{src.name}</p>
                        <p className="font-mono text-xs text-ink-3">{src.endpoint_url}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <StatusBadge status={sourceStatus(src.status)} />
                        <Btn size="sm" variant="ghost">Uredi</Btn>
                      </div>
                    </Card>
                  ))}
                </div>
              </div>
            )}

            {page === 'sys-settings' && (
              <div className="space-y-4">
                <SectionHeader title="Sistemska podešavanja" description="Računi, isplate i provajder plaćanja se čuvaju direktno u konfiguraciji platforme." />
                <Alert type="warning">Osetljive vrednosti se nikada ne vraćaju u preglednik. Prazno polje za tajnu zadržava postojeću vrednost.</Alert>
                <Card className="p-5">
                  <div className="space-y-4">
                    {settings.map(setting => (
                      <div key={setting.key} className="grid gap-2 border-b border-frame pb-4 last:border-0 last:pb-0 md:grid-cols-[minmax(0,1fr)_minmax(240px,1.2fr)_auto] md:items-end">
                        <div>
                          <p className="font-semibold text-sm text-ink">{setting.description || setting.key}</p>
                          <p className="font-mono text-[11px] text-ink-3 mt-1">{setting.key}</p>
                        </div>
                        <input
                          type={setting.sensitive ? 'password' : 'text'}
                          value={settingDrafts[setting.key] ?? ''}
                          placeholder={setting.sensitive && setting.has_value ? 'Sačuvano · unesi novu vrednost za izmenu' : 'Unesi vrednost'}
                          onChange={event => setSettingDrafts(current => ({ ...current, [setting.key]: event.target.value }))}
                          className="w-full rounded-lg border border-frame bg-white px-3 py-2 text-sm font-medium text-ink outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                        />
                        <Btn size="sm" variant="secondary" disabled={savingAction} onClick={() => void saveSetting(setting)}>Sačuvaj</Btn>
                      </div>
                    ))}
                    {settings.length === 0 && <EmptyState icon="⚙️" title="Nema sistemskih podešavanja" description="Podešavanja će biti dostupna kada se baza inicijalizuje." />}
                  </div>
                </Card>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}
