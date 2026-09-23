import { useState } from 'react'
import { Sidebar, TopBar } from '../components/Sidebar'
import { Btn, Card, StatCard, SectionHeader, EmptyState, Table, StatusBadge, Tabs, Alert, Input, Select } from '../components/ui'
import { PageHeader } from '../components/PageHeader'
import { ConfirmModal } from '../components/Modal'
import { useToast } from '../components/Toast'

const navGroups = [
  { items: [
    { id: 'pregled', label: 'Pregled', icon: '📊' },
    { id: 'nova', label: 'Nova kampanja', icon: '➕' },
    { id: 'kampanje', label: 'Moje kampanje', icon: '🎯' },
    { id: 'dokazi', label: 'Dokazi korisnika', icon: '📎', badge: 5 },
  ]},
  { group: 'Analitika', items: [
    { id: 'analitika', label: 'Rezultati', icon: '📈' },
  ]},
  { group: 'Finansije', items: [
    { id: 'budzet', label: 'Budžet i uplate', icon: '💳' },
    { id: 'fakture', label: 'Fakture', icon: '🧾' },
    { id: 'izvestaji', label: 'Izveštaji', icon: '📋' },
  ]},
  { group: 'Reklame', items: [
    { id: 'banneri', label: 'Banner reklame', icon: '🖼️' },
    { id: 'premium', label: 'Premium pozicije', icon: '⭐' },
  ]},
  { group: 'Nalog', items: [
    { id: 'profil', label: 'Profil firme', icon: '🏢' },
    { id: 'podrska', label: 'Podrška', icon: '💬' },
  ]},
]

const campaignsData = [
  { naziv: 'Instagram kampanja — Dec 2024', budžet: '5.000 RSD', potrošeno: '2.340 RSD', dokazi: 12, status: 'aktivno' },
  { naziv: 'Anketa — kupovne navike Q4', budžet: '3.000 RSD', potrošeno: '3.000 RSD', dokazi: 37, status: 'obustavljeno' },
  { naziv: 'Google Play recenzije', budžet: '8.000 RSD', potrošeno: '1.200 RSD', dokazi: 6, status: 'na_cekanju' },
]

const proofsData = [
  { id: 1, korisnik: 'marko_m', zadatak: 'Instagram lajk', poslato: '23.12.2024', status: 'na_proveri' },
  { id: 2, korisnik: 'jelena_j', zadatak: 'Instagram lajk', poslato: '23.12.2024', status: 'na_proveri' },
  { id: 3, korisnik: 'nikola_p', zadatak: 'Anketa kupovine', poslato: '22.12.2024', status: 'odobreno' },
  { id: 4, korisnik: 'ana_s', zadatak: 'Instagram lajk', poslato: '22.12.2024', status: 'odbijeno' },
  { id: 5, korisnik: 'stefan_k', zadatak: 'Play recenzija', poslato: '21.12.2024', status: 'na_proveri' },
]

type Page = 'pregled'|'nova'|'kampanje'|'dokazi'|'analitika'|'budzet'|'fakture'|'izvestaji'|'banneri'|'premium'|'profil'|'podrska'

const BACK: Partial<Record<Page, { label: string; to: Page }>> = {
  nova:      { label: 'Nazad na pregled', to: 'pregled' },
  kampanje:  { label: 'Nazad na pregled', to: 'pregled' },
  dokazi:    { label: 'Nazad na pregled', to: 'pregled' },
  analitika: { label: 'Nazad na pregled', to: 'pregled' },
  budzet:    { label: 'Nazad na pregled', to: 'pregled' },
  fakture:   { label: 'Nazad na finansije', to: 'budzet' },
  izvestaji: { label: 'Nazad na finansije', to: 'budzet' },
  banneri:   { label: 'Nazad na pregled', to: 'pregled' },
  premium:   { label: 'Nazad na pregled', to: 'pregled' },
  profil:    { label: 'Nazad na pregled', to: 'pregled' },
  podrska:   { label: 'Nazad na pregled', to: 'pregled' },
}

const CRUMBS: Partial<Record<Page, { label: string }[]>> = {
  nova:      [{ label: 'Oglašivač' }, { label: 'Nova kampanja' }],
  kampanje:  [{ label: 'Oglašivač' }, { label: 'Kampanje' }],
  dokazi:    [{ label: 'Oglašivač' }, { label: 'Dokazi korisnika' }],
  analitika: [{ label: 'Oglašivač' }, { label: 'Analitika' }],
  budzet:    [{ label: 'Oglašivač' }, { label: 'Budžet i uplate' }],
  fakture:   [{ label: 'Oglašivač' }, { label: 'Finansije' }, { label: 'Fakture' }],
  izvestaji: [{ label: 'Oglašivač' }, { label: 'Finansije' }, { label: 'Izveštaji' }],
  banneri:   [{ label: 'Oglašivač' }, { label: 'Banner reklame' }],
  premium:   [{ label: 'Oglašivač' }, { label: 'Premium pozicije' }],
  profil:    [{ label: 'Oglašivač' }, { label: 'Profil firme' }],
  podrska:   [{ label: 'Oglašivač' }, { label: 'Podrška' }],
}

function NovaCampanja({ onCancel, onSuccess }: { onCancel: () => void; onSuccess: () => void }) {
  const [step, setStep] = useState(1)
  const [naziv, setNaziv] = useState('')
  const [reward, setReward] = useState('')
  const [budget, setBudget] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const steps = ['Definicija', 'Nagrada i budžet', 'Publika i dokaz', 'Pregled']

  if (submitted) {
    return (
      <div className="flex flex-col items-center text-center py-12">
        <span className="text-5xl mb-4">🎉</span>
        <h2 className="text-xl font-extrabold text-ink mb-2">Kampanja je poslata na moderaciju!</h2>
        <p className="text-sm text-ink-2 max-w-xs mb-6">Dobićeš obaveštenje kada kampanja bude odobrena. Status možeš pratiti u sekciji Kampanje.</p>
        <Btn onClick={onSuccess}>Idi na kampanje</Btn>
      </div>
    )
  }

  return (
    <div>
      <SectionHeader title="Nova kampanja" description="Definiši zadatak koji korisnici treba da izvrše." />
      <div className="flex items-center gap-2 mb-6 flex-wrap">
        {steps.map((s, i) => (
          <div key={s} className="flex items-center gap-2">
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-semibold ${
              step === i + 1 ? 'bg-blue-600 text-white' :
              step > i + 1 ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-ink-3'
            }`}>
              <span className="w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold bg-white/20">
                {step > i + 1 ? '✓' : i + 1}
              </span>
              {s}
            </div>
            {i < steps.length - 1 && <span className="text-ink-3 text-sm">→</span>}
          </div>
        ))}
      </div>

      <Card className="p-6 max-w-lg">
        {step === 1 && (
          <div className="space-y-4">
            <h3 className="font-bold text-ink">Definicija zadatka</h3>
            <Input label="Naziv kampanje" placeholder="npr. Instagram kampanja — jan 2025" value={naziv} onChange={setNaziv} />
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-bold text-ink-2 uppercase tracking-wide">Opis zadatka</label>
              <textarea rows={3} placeholder="Šta korisnik treba da uradi? Budi precizan." className="bg-white border border-frame text-ink placeholder-ink-4 rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none resize-none" />
            </div>
            <Select label="Kategorija" options={[
              { value: '', label: 'Odaberi kategoriju' },
              { value: 'social', label: 'Društvene mreže' },
              { value: 'anketa', label: 'Ankete' },
              { value: 'recenzija', label: 'Recenzije' },
              { value: 'video', label: 'Video' },
              { value: 'web', label: 'Web zadaci' },
            ]} />
            <div className="flex gap-2">
              <Btn variant="ghost" onClick={onCancel} size="sm">Otkaži</Btn>
              <Btn onClick={() => setStep(2)} disabled={!naziv} className="flex-1 justify-center">Dalje →</Btn>
            </div>
          </div>
        )}
        {step === 2 && (
          <div className="space-y-4">
            <h3 className="font-bold text-ink">Nagrada i budžet</h3>
            <Input label="Nagrada po zadatku (RSD)" placeholder="npr. 80" value={reward} onChange={setReward} />
            <Input label="Ukupni budžet (RSD)" placeholder="npr. 5000" value={budget} onChange={setBudget} />
            <Select label="Trajanje" options={[{ value: '7', label: '7 dana' }, { value: '14', label: '14 dana' }, { value: '30', label: '30 dana' }]} />
            {reward && budget && (
              <Alert type="info">Procenjeno: <strong className="font-mono">{Math.floor(Number(budget) / Number(reward))}</strong> izvršenih zadataka</Alert>
            )}
            <div className="flex gap-2">
              <Btn onClick={() => setStep(1)} variant="secondary">← Prethodni korak</Btn>
              <Btn onClick={() => setStep(3)} disabled={!reward || !budget} className="flex-1 justify-center">Dalje →</Btn>
            </div>
          </div>
        )}
        {step === 3 && (
          <div className="space-y-4">
            <h3 className="font-bold text-ink">Ciljna publika i dokaz</h3>
            <Select label="Ciljni nivo korisnika" options={[
              { value: 'sve', label: 'Svi korisnici' },
              { value: 'trusted', label: 'Trusted i više' },
              { value: 'pro', label: 'Pro i više' },
            ]} />
            <Select label="Potreban dokaz" options={[
              { value: '', label: 'Odaberi tip dokaza' },
              { value: 'screenshot', label: 'Screenshot' },
              { value: 'link', label: 'Screenshot + link' },
              { value: 'video', label: 'Video snimak' },
              { value: 'kod', label: 'Kod potvrde' },
            ]} />
            <div className="flex gap-2">
              <Btn onClick={() => setStep(2)} variant="secondary">← Prethodni korak</Btn>
              <Btn onClick={() => setStep(4)} className="flex-1 justify-center">Pregled →</Btn>
            </div>
          </div>
        )}
        {step === 4 && (
          <div className="space-y-4">
            <h3 className="font-bold text-ink">Pregled kampanje</h3>
            <div className="bg-mint-50 border border-frame rounded-xl p-4 space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-ink-2">Naziv</span><span className="font-semibold text-ink">{naziv}</span></div>
              <div className="flex justify-between"><span className="text-ink-2">Nagrada</span><span className="font-mono font-bold text-emerald-600">{reward} RSD</span></div>
              <div className="flex justify-between"><span className="text-ink-2">Budžet</span><span className="font-mono font-bold text-blue-600">{budget} RSD</span></div>
            </div>
            <Alert type="warning">Kampanja ide na moderaciju pre aktivacije. Status možeš pratiti u sekciji Kampanje.</Alert>
            <div className="flex gap-2">
              <Btn onClick={() => setStep(3)} variant="secondary">← Izmeni prethodni korak</Btn>
              <Btn onClick={() => setSubmitted(true)} variant="success" className="flex-1 justify-center">✓ Pošalji na moderaciju</Btn>
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}

export default function AdvertiserPanel({ onNavigate }: { onNavigate: (id: string) => void }) {
  const [page, setPage] = useState<Page>('pregled')
  const [mobileOpen, setMobileOpen] = useState(false)
  const [proofsTab, setProofsTab] = useState('svi')
  const [proofAction, setProofAction] = useState<{ id: number; type: 'approve' | 'reject' } | null>(null)
  const [proofStatuses, setProofStatuses] = useState<Record<number, string>>({})
  const [logoutConfirm, setLogoutConfirm] = useState(false)
  const { show: showToast, node: toastNode } = useToast()

  function goTo(p: Page) { setPage(p) }
  const back = BACK[page]
  const crumbs = CRUMBS[page]

  const sidebarFooter = (
    <div className="flex items-center gap-2.5">
      <div className="w-8 h-8 rounded-full bg-violet-600 flex items-center justify-center text-white text-sm font-bold">A</div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-white truncate">Acme d.o.o.</p>
        <p className="text-xs" style={{ color: '#4a6a8a' }}>Oglašivač</p>
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

  function proofStatus(id: number, original: string) {
    return proofStatuses[id] ?? original
  }

  return (
    <div className="flex h-screen bg-mint-50 text-ink overflow-hidden">
      {toastNode}

      <ConfirmModal
        open={logoutConfirm}
        title="Odjaviti se?"
        description="Bićeš odjavljen/a sa KlikZarada oglašivačkog panela."
        confirmLabel="Da, odjavi me"
        cancelLabel="Otkaži"
        variant="danger"
        onConfirm={() => onNavigate('home')}
        onCancel={() => setLogoutConfirm(false)}
      />

      <ConfirmModal
        open={proofAction !== null}
        title={proofAction?.type === 'approve' ? 'Odobri dokaz?' : 'Odbij dokaz?'}
        description={proofAction?.type === 'approve'
          ? 'Korisniku će biti odobrena nagrada i sredstva će biti povučena iz budžeta kampanje.'
          : 'Korisnik neće dobiti nagradu. Možeš uneti razlog odbijanja.'}
        confirmLabel={proofAction?.type === 'approve' ? '✓ Odobri' : '✗ Odbij'}
        cancelLabel="Otkaži"
        variant={proofAction?.type === 'approve' ? 'success' : 'danger'}
        onConfirm={() => {
          if (!proofAction) return
          setProofStatuses(s => ({ ...s, [proofAction.id]: proofAction.type === 'approve' ? 'odobreno' : 'odbijeno' }))
          showToast(proofAction.type === 'approve' ? 'Dokaz je odobren.' : 'Dokaz je odbijen.', proofAction.type === 'approve' ? 'success' : 'error')
          setProofAction(null)
        }}
        onCancel={() => setProofAction(null)}
      />

      {mobileOpen && <div className="fixed inset-0 bg-black/40 z-40 lg:hidden" onClick={() => setMobileOpen(false)} />}
      <div className="hidden lg:flex shrink-0">
        <Sidebar groups={navGroups} active={page} onNavigate={p => goTo(p as Page)} footer={sidebarFooter} />
      </div>
      {mobileOpen && (
        <div className="fixed left-0 top-0 h-full z-50 lg:hidden">
          <Sidebar groups={navGroups} active={page} onNavigate={p => { goTo(p as Page); setMobileOpen(false) }} footer={sidebarFooter} isMobile onClose={() => setMobileOpen(false)} />
        </div>
      )}

      <div className="flex-1 flex flex-col overflow-hidden">
        <TopBar
          onMenuClick={() => setMobileOpen(true)}
          pageTitle="Oglašivački panel"
          onNavigate={onNavigate}
          actions={<Btn onClick={() => goTo('nova')} size="sm">+ Nova kampanja</Btn>}
        />
        <main className="flex-1 overflow-y-auto bg-mint-50">
          <div className="max-w-4xl mx-auto px-4 py-6">
            {page !== 'pregled' && (back || crumbs) && (
              <PageHeader
                breadcrumbs={crumbs}
                onBack={back ? () => goTo(back.to) : undefined}
                backLabel={back?.label}
              />
            )}

            {page === 'pregled' && (
              <div className="space-y-5">
                <h1 className="text-xl font-extrabold text-ink">Pregled</h1>
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                  <StatCard label="Raspoloživi budžet" value="9.460 RSD" accent="green" icon="💰" />
                  <StatCard label="Rezervisan budžet" value="6.540 RSD" accent="orange" icon="🔒" />
                  <StatCard label="Aktivnih kampanja" value="1" accent="blue" icon="🎯" />
                  <StatCard label="Odobrenih dokaza" value="55" accent="teal" icon="✅" />
                </div>
                <SectionHeader title="Kampanje" action={<Btn onClick={() => goTo('kampanje')} variant="ghost" size="sm">Sve →</Btn>} />
                <Card>
                  <Table
                    headers={['Naziv', 'Budžet', 'Potrošeno', 'Dokazi', 'Status']}
                    rows={campaignsData.map(c => [
                      <span className="font-semibold text-ink">{c.naziv}</span>,
                      <span className="font-mono">{c.budžet}</span>,
                      <span className="font-mono text-amber-700">{c.potrošeno}</span>,
                      <span className="font-mono">{c.dokazi}</span>,
                      <StatusBadge status={c.status} />,
                    ])}
                  />
                </Card>
                <SectionHeader title="Dokazi na proveri" action={<Btn onClick={() => goTo('dokazi')} variant="ghost" size="sm">Svi →</Btn>} />
                <Card>
                  <Table
                    headers={['Korisnik', 'Zadatak', 'Poslato', 'Status', 'Akcija']}
                    rows={proofsData.filter(p => proofStatus(p.id, p.status) === 'na_proveri').map(p => [
                      <span className="font-mono text-xs">{p.korisnik}</span>,
                      <span>{p.zadatak}</span>,
                      <span className="font-mono text-xs">{p.poslato}</span>,
                      <StatusBadge status={proofStatus(p.id, p.status)} />,
                      <div className="flex gap-1.5">
                        <Btn size="sm" variant="success" onClick={() => setProofAction({ id: p.id, type: 'approve' })}>✓ Odobri</Btn>
                        <Btn size="sm" variant="danger" onClick={() => setProofAction({ id: p.id, type: 'reject' })}>✗ Odbij</Btn>
                      </div>,
                    ])}
                  />
                </Card>
              </div>
            )}

            {page === 'nova' && (
              <NovaCampanja
                onCancel={() => goTo('pregled')}
                onSuccess={() => goTo('kampanje')}
              />
            )}

            {page === 'kampanje' && (
              <div>
                <SectionHeader title="Moje kampanje" action={<Btn onClick={() => goTo('nova')} size="sm">+ Nova kampanja</Btn>} />
                <Card>
                  <Table
                    headers={['Naziv', 'Budžet', 'Potrošeno', 'Dokazi', 'Status', 'Akcija']}
                    rows={campaignsData.map(c => [
                      <span className="font-semibold text-ink">{c.naziv}</span>,
                      <span className="font-mono">{c.budžet}</span>,
                      <span className="font-mono text-amber-700">{c.potrošeno}</span>,
                      <span className="font-mono">{c.dokazi}</span>,
                      <StatusBadge status={c.status} />,
                      <Btn size="sm" variant="ghost">Detalji</Btn>,
                    ])}
                  />
                </Card>
              </div>
            )}

            {page === 'dokazi' && (
              <div>
                <SectionHeader title="Dokazi korisnika" description="Pregledaj i odobri ili odbij dostavljene dokaze." />
                <Tabs
                  tabs={[{ id: 'svi', label: 'Svi' }, { id: 'na_proveri', label: 'Na proveri' }, { id: 'odobreno', label: 'Odobreno' }, { id: 'odbijeno', label: 'Odbijeno' }]}
                  active={proofsTab}
                  onChange={setProofsTab}
                />
                <Card>
                  <Table
                    headers={['Korisnik', 'Zadatak', 'Poslato', 'Status', 'Akcija']}
                    rows={proofsData.filter(p => proofsTab === 'svi' || proofStatus(p.id, p.status) === proofsTab).map(p => {
                      const st = proofStatus(p.id, p.status)
                      return [
                        <span className="font-mono text-xs">{p.korisnik}</span>,
                        <span>{p.zadatak}</span>,
                        <span className="font-mono text-xs">{p.poslato}</span>,
                        <StatusBadge status={st} />,
                        st === 'na_proveri'
                          ? <div className="flex gap-1.5">
                              <Btn size="sm" variant="success" onClick={() => setProofAction({ id: p.id, type: 'approve' })}>✓ Odobri</Btn>
                              <Btn size="sm" variant="danger" onClick={() => setProofAction({ id: p.id, type: 'reject' })}>✗ Odbij</Btn>
                            </div>
                          : <span className="text-xs text-ink-3">—</span>,
                      ]
                    })}
                  />
                </Card>
              </div>
            )}

            {page === 'analitika' && (
              <div>
                <SectionHeader title="Rezultati i analitika" />
                <div className="grid sm:grid-cols-3 gap-3 mb-5">
                  <StatCard label="Avg. cena po dokazu" value="—" accent="teal" />
                  <StatCard label="Stopa odobrenja" value="—" accent="green" />
                  <StatCard label="Konverzije" value="—" accent="blue" />
                </div>
                <EmptyState icon="📊" title="Nema dovoljno podataka" description="Pokreni prvu kampanju da bi video analitiku." action={<Btn onClick={() => goTo('nova')} size="sm">Kreiraj kampanju</Btn>} />
              </div>
            )}

            {page === 'budzet' && (
              <div className="space-y-4">
                <SectionHeader title="Budžet i uplate" />
                <div className="grid grid-cols-2 gap-3">
                  <StatCard label="Raspoloživi budžet" value="9.460 RSD" accent="green" />
                  <StatCard label="Rezervisan" value="6.540 RSD" accent="orange" />
                </div>
                <Card className="p-5">
                  <h3 className="font-bold text-ink mb-4">Uplati sredstva</h3>
                  <Input label="Iznos uplate (RSD)" placeholder="npr. 5000" />
                  <p className="text-xs text-ink-3 mt-2 mb-4">Sredstva su dostupna odmah po potvrdi transakcije.</p>
                  <Btn>Nastavi na plaćanje →</Btn>
                </Card>
              </div>
            )}

            {page === 'fakture' && (
              <div>
                <SectionHeader title="Fakture" />
                <EmptyState icon="🧾" title="Nema faktura" description="Fakture se generišu automatski na kraju obračunskog perioda." />
              </div>
            )}

            {page === 'izvestaji' && (
              <div>
                <SectionHeader title="Izveštaji" />
                <EmptyState icon="📋" title="Nema izveštaja" description="Izveštaji će biti dostupni nakon aktivacije prve kampanje." />
              </div>
            )}

            {page === 'banneri' && (
              <div>
                <SectionHeader title="Banner reklame" description="Sponzorisani prostor. Oznaka 'Sponzorisano' je obavezna." />
                <EmptyState icon="🖼️" title="Nema aktivnih banera" description="Kontaktiraj podršku za rezervaciju banner prostora." action={<Btn variant="secondary" size="sm" onClick={() => goTo('podrska')}>Kontaktiraj podršku</Btn>} />
              </div>
            )}

            {page === 'premium' && (
              <div>
                <SectionHeader title="Premium pozicije" />
                <Alert type="info">Premium pozicije uključuju istaknuto mesto u listi zadataka i push obaveštenje korisnicima.</Alert>
                <div className="mt-4 grid sm:grid-cols-2 gap-3">
                  {[{ naziv: 'Istaknuto u listi zadataka', cena: '500 RSD / dan' }, { naziv: 'Push obaveštenje', cena: '800 RSD / slanje' }].map(p => (
                    <div key={p.naziv} className="bg-violet-50 border border-violet-200 rounded-xl p-4">
                      <p className="font-bold text-ink">{p.naziv}</p>
                      <p className="font-mono font-bold text-violet-700 text-lg mt-1">{p.cena}</p>
                      <Btn variant="premium" size="sm" className="mt-3">Rezerviši</Btn>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {page === 'profil' && (
              <div className="space-y-4">
                <SectionHeader title="Profil firme" />
                <Card className="p-5 space-y-4">
                  <Input label="Naziv firme" placeholder="Acme d.o.o." />
                  <Input label="PIB" placeholder="123456789" />
                  <Input label="Kontakt email" placeholder="kontakt@firma.rs" />
                  <Input label="Telefon" placeholder="+381 11 ..." />
                  <div className="flex gap-2">
                    <Btn variant="success" onClick={() => showToast('Profil firme je sačuvan.', 'success')}>Sačuvaj izmene</Btn>
                    <Btn variant="secondary">Otkaži</Btn>
                  </div>
                </Card>
              </div>
            )}

            {page === 'podrska' && (
              <div className="space-y-4">
                <SectionHeader title="Podrška za oglašivače" />
                <div className="bg-blue-50 border border-blue-200 rounded-xl p-5">
                  <p className="font-bold text-ink mb-1">💬 Kontakt za oglašivače</p>
                  <p className="text-sm text-ink-2 mb-3">Podrška za kreiranje kampanja, cenovnik i tehničke integracije.</p>
                  <Btn variant="secondary" size="sm">Pošalji poruku</Btn>
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}
