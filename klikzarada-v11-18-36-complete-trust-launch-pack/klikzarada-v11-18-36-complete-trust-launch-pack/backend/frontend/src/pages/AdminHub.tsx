import { useState } from 'react'
import { Sidebar, TopBar } from '../components/Sidebar'
import { Btn, Card, StatCard, SectionHeader, EmptyState, Table, StatusBadge, Tabs, Alert } from '../components/ui'
import { PageHeader } from '../components/PageHeader'
import { ConfirmModal } from '../components/Modal'
import { useToast } from '../components/Toast'

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
  const [campAction, setCampAction] = useState<{ id: number; naziv: string; type: 'approve' | 'reject' } | null>(null)
  const [userStatuses, setUserStatuses] = useState<Record<number, string>>({})
  const [payoutStatuses, setPayoutStatuses] = useState<Record<number, string>>({})
  const [campStatuses, setCampStatuses] = useState<Record<number, string>>({})
  const { show: showToast, node: toastNode } = useToast()

  function goTo(p: AdminPage) { setPage(p) }
  const back = BACK[page]
  const crumbs = CRUMBS[page]

  function userStatus(id: number, orig: string) { return userStatuses[id] ?? orig }
  function payoutStatus(id: number, orig: string) { return payoutStatuses[id] ?? orig }
  function campStatus(id: number, orig: string) { return campStatuses[id] ?? orig }

  const sidebarFooter = (
    <div className="flex items-center gap-2.5">
      <div className="w-8 h-8 rounded-full bg-coral-600 flex items-center justify-center text-white text-sm font-bold">A</div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-white truncate">Administrator</p>
        <p className="text-xs" style={{ color: '#4a6a8a' }}>Ops pristup</p>
      </div>
      <button
        onClick={() => setLogoutConfirm(true)}
        className="text-xs px-2 py-1 rounded hover:bg-white/10 cursor-pointer font-medium"
        style={{ color: '#4a6a8a' }}
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
        onConfirm={() => onNavigate('home')}
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
        onConfirm={() => {
          if (!blockUser) return
          const newStatus = blockUser.action === 'block' ? 'blokirano' : 'aktivno'
          setUserStatuses(s => ({ ...s, [blockUser.id]: newStatus }))
          showToast(blockUser.action === 'block' ? `${blockUser.ime} je blokiran/a.` : `${blockUser.ime} je odblokirano.`, blockUser.action === 'block' ? 'error' : 'success')
          setBlockUser(null)
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
        onConfirm={() => {
          if (!payoutAction) return
          setPayoutStatuses(s => ({ ...s, [payoutAction.id]: payoutAction.type === 'approve' ? 'placeno' : 'odbijeno' }))
          showToast(payoutAction.type === 'approve' ? 'Isplata je odobrena.' : 'Isplata je odbijena.', payoutAction.type === 'approve' ? 'success' : 'error')
          setPayoutAction(null)
        }}
        onCancel={() => setPayoutAction(null)}
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
        onConfirm={() => {
          if (!campAction) return
          setCampStatuses(s => ({ ...s, [campAction.id]: campAction.type === 'approve' ? 'aktivno' : 'odbijeno' }))
          showToast(campAction.type === 'approve' ? 'Kampanja je aktivirana.' : 'Kampanja je odbijena.', campAction.type === 'approve' ? 'success' : 'error')
          setCampAction(null)
        }}
        onCancel={() => setCampAction(null)}
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
                  <p className="text-sm text-ink-2 mt-0.5">23. decembar 2024.</p>
                </div>
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                  <StatCard label="Ukupno korisnika" value="—" icon="👥" accent="blue" />
                  <StatCard label="Aktivnih kampanja" value="1" icon="🎯" accent="green" />
                  <StatCard label="Dokazi na čekanju" value="7" icon="📎" accent="orange" />
                  <StatCard label="Isplate na čekanju" value="2" icon="💸" accent="purple" />
                </div>
                <div className="space-y-2">
                  <Alert type="warning"><strong>2 kampanje</strong> čekaju moderaciju pre aktivacije.</Alert>
                  <Alert type="error"><strong>Partner API 2</strong> vraća grešku — uvoz zadataka nije moguć.</Alert>
                </div>
                <div className="grid sm:grid-cols-3 gap-4">
                  {[
                    { label: 'Finansije', items: ['Isplate na čekanju: 2', 'Uplate ovaj mesec: —', 'Fakture: 0 novih'], page: 'fin-isplate' as AdminPage, color: 'bg-emerald-50 border-emerald-200' },
                    { label: 'Kampanje', items: ['Na čekanju: 2', 'Aktivnih: 1', 'Moderacija dokaza: 7'], page: 'kam-kampanje' as AdminPage, color: 'bg-blue-50 border-blue-200' },
                    { label: 'Korisnici', items: ['Ukupno: —', 'Blokiranih: 1', 'Tiketa: 1 novih'], page: 'lj-korisnici' as AdminPage, color: 'bg-violet-50 border-violet-200' },
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
                    rows={payoutsData.map(p => {
                      const st = payoutStatus(p.id, p.status)
                      return [
                        <span className="font-semibold text-ink">{p.korisnik}</span>,
                        <span className="font-mono font-semibold text-emerald-600">{p.iznos}</span>,
                        <span>{p.metoda}</span>,
                        <span className="font-mono text-xs">{p.trazeno}</span>,
                        <StatusBadge status={st} />,
                        st === 'na_cekanju'
                          ? <div className="flex gap-1.5">
                              <Btn size="sm" variant="success" onClick={() => setPayoutAction({ id: p.id, korisnik: p.korisnik, iznos: p.iznos, type: 'approve' })}>Odobri</Btn>
                              <Btn size="sm" variant="danger" onClick={() => setPayoutAction({ id: p.id, korisnik: p.korisnik, iznos: p.iznos, type: 'reject' })}>Odbij</Btn>
                            </div>
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
                    rows={campaignModData.map(c => {
                      const st = campStatus(c.id, c.status)
                      return [
                        <span className="font-semibold text-ink">{c.naziv}</span>,
                        <span className="text-sm text-ink-2">{c.oglasivac}</span>,
                        <span className="font-mono">{c.budžet}</span>,
                        <StatusBadge status={st} />,
                        st === 'na_cekanju'
                          ? <div className="flex gap-1.5">
                              <Btn size="sm" variant="success" onClick={() => setCampAction({ id: c.id, naziv: c.naziv, type: 'approve' })}>Odobri</Btn>
                              <Btn size="sm" variant="danger" onClick={() => setCampAction({ id: c.id, naziv: c.naziv, type: 'reject' })}>Odbij</Btn>
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
                    rows={proofsModData
                      .filter(p => dokaziTab === 'svi' || (dokaziTab === 'ok' ? p.flag === 'OK' : p.flag !== 'OK'))
                      .map(p => [
                        <span className="font-mono text-xs">{p.korisnik}</span>,
                        <span>{p.zadatak}</span>,
                        <span className="text-xs text-ink-3">{p.kampanja}</span>,
                        <span className={`text-xs font-bold ${p.flagColor}`}>{p.flag}</span>,
                        <div className="flex gap-1.5">
                          <Btn size="sm" variant="success">✓</Btn>
                          <Btn size="sm" variant="danger">✗</Btn>
                        </div>,
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
                  {importSources.map(src => (
                    <Card key={src.naziv} className="p-4">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <p className="font-bold text-ink">{src.naziv}</p>
                            <StatusBadge status={src.status} />
                          </div>
                          <p className="text-xs text-ink-3 font-mono truncate">{src.url}</p>
                          <div className="flex gap-4 mt-2">
                            <span className="text-xs text-ink-2">Poslednja sync: {src.sync}</span>
                            {src.status === 'aktivno' && (
                              <>
                                <span className="text-xs font-semibold text-emerald-600">+{src.novi} novih</span>
                                <span className="text-xs text-ink-3">{src.preskoceni} preskočenih</span>
                              </>
                            )}
                          </div>
                          {src.greska && <p className="text-xs text-coral-700 font-semibold mt-1.5">⚠ {src.greska}</p>}
                        </div>
                        <div className="flex gap-2 shrink-0">
                          {src.status === 'aktivno' && <Btn size="sm" variant="secondary">Sync</Btn>}
                          {src.status === 'greska' && <Btn size="sm" variant="danger">Dijagnostika</Btn>}
                          {src.status === 'obustavljeno' && <Btn size="sm" variant="ghost">Aktiviraj</Btn>}
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
                <div className="mt-4">
                  <Btn variant="secondary" size="sm">+ Dodaj novi izvor</Btn>
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
                    rows={usersData.map(u => {
                      const st = userStatus(u.id, u.status)
                      return [
                        <span className="font-semibold text-ink">{u.ime}</span>,
                        <span className="text-xs font-mono text-ink-2">{u.email}</span>,
                        <span className="text-xs font-medium">{u.tier}</span>,
                        <span className="font-mono text-xs font-semibold text-emerald-600">{u.zarada}</span>,
                        <span className="font-mono text-xs">{u.dokazi}</span>,
                        <StatusBadge status={st} />,
                        <div className="flex gap-1.5">
                          <Btn size="sm" variant="ghost">Profil</Btn>
                          {st !== 'blokirano'
                            ? <Btn size="sm" variant="danger" onClick={() => setBlockUser({ id: u.id, ime: u.ime, action: 'block' })}>Blokiraj</Btn>
                            : <Btn size="sm" variant="success" onClick={() => setBlockUser({ id: u.id, ime: u.ime, action: 'unblock' })}>Odblokiraj</Btn>
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
                    headers={['Firma', 'Email', 'Kampanje', 'Potrošeno', 'Status']}
                    rows={[
                      { firma: 'Acme d.o.o.', email: 'kontakt@acme.rs', kampanje: '2', potroseno: '6.540 RSD', status: 'aktivno' },
                      { firma: 'StartupXYZ', email: 'info@startupxyz.rs', kampanje: '1', potroseno: '0 RSD', status: 'na_cekanju' },
                    ].map(r => [
                      <span className="font-semibold text-ink">{r.firma}</span>,
                      <span className="font-mono text-xs text-ink-2">{r.email}</span>,
                      <span className="font-mono">{r.kampanje}</span>,
                      <span className="font-mono text-xs font-semibold text-amber-700">{r.potroseno}</span>,
                      <StatusBadge status={r.status} />,
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
              <div>
                <SectionHeader title="Tiketi i podrška" />
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-3">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <p className="font-bold text-ink">#001 — Problem sa isplatom</p>
                      <p className="text-xs text-ink-2 mt-0.5">Korisnik: jelena_j · Otvoreno: 23.12.2024</p>
                    </div>
                    <StatusBadge status="na_cekanju" />
                  </div>
                  <p className="text-sm text-ink-2">„Nisam primila isplatu za prošli mesec, sve je odobreno ali iznos nije na računu."</p>
                  <Btn size="sm" className="mt-3">Odgovori</Btn>
                </div>
                <EmptyState icon="✅" title="Nema više otvorenih tiketa" />
              </div>
            )}

            {page === 'ops-antifraud' && (
              <div>
                <SectionHeader title="Anti-fraud sistem" description="Automatski signali za sumnjive aktivnosti." />
                <Alert type="warning"><strong>2 dokaza</strong> su automatski flagovana i čekaju manuelni pregled.</Alert>
                <div className="mt-4">
                  <Card>
                    <Table
                      headers={['Korisnik', 'Signal', 'Ozbiljnost', 'Datum', 'Akcija']}
                      rows={[
                        { k: 'petar_k', s: 'Sumnjiv obrazac aktivnosti', o: 'Srednje ⚠', d: '23.12.2024', oc: 'text-amber-700' },
                        { k: 'ana_s', s: 'Duplikat dokaza', o: 'Visoko 🔴', d: '22.12.2024', oc: 'text-coral-700' },
                      ].map(r => [
                        <span className="font-mono text-xs">{r.k}</span>,
                        <span className="text-sm">{r.s}</span>,
                        <span className={`text-xs font-bold ${r.oc}`}>{r.o}</span>,
                        <span className="font-mono text-xs">{r.d}</span>,
                        <Btn size="sm" variant="danger"
                          onClick={() => setBlockUser({ id: r.k === 'ana_s' ? 4 : 99, ime: r.k, action: 'block' })}>
                          Blokiraj
                        </Btn>,
                      ])}
                    />
                  </Card>
                </div>
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
                <div className="space-y-3">
                  {importSources.map(src => (
                    <Card key={src.naziv} className="p-4 flex items-center justify-between gap-4">
                      <div>
                        <p className="font-bold text-ink">{src.naziv}</p>
                        <p className="font-mono text-xs text-ink-3">{src.url}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <StatusBadge status={src.status} />
                        <Btn size="sm" variant="ghost">Uredi</Btn>
                      </div>
                    </Card>
                  ))}
                  <Btn variant="secondary" size="sm">+ Dodaj izvor</Btn>
                </div>
              </div>
            )}

            {page === 'sys-settings' && (
              <div className="space-y-4">
                <SectionHeader title="Sistemska podešavanja" />
                <Alert type="error">Osetljivi podaci (bankovni račun, API ključevi) su zaštićeni i loguju se pri svakom pristupu.</Alert>
                <Card className="p-5">
                  <div className="divide-y divide-frame">
                    {[
                      { label: 'Minimum za isplatu (RSD)', val: '1.500' },
                      { label: 'Max zadataka po korisniku / dan', val: '10' },
                      { label: 'Platforma komisija (%)', val: '—' },
                      { label: 'Anti-fraud auto-blokada', val: 'Uključeno' },
                    ].map(s => (
                      <div key={s.label} className="flex items-center justify-between py-3">
                        <span className="text-sm text-ink-2">{s.label}</span>
                        <span className="font-mono text-sm font-semibold text-ink">{s.val}</span>
                      </div>
                    ))}
                  </div>
                  <Btn variant="secondary" size="sm" className="mt-4">Uredi podešavanja</Btn>
                </Card>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}
