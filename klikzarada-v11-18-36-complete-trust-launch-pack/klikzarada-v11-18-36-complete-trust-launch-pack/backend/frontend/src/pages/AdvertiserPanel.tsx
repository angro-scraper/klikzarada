import { useEffect, useRef, useState } from 'react'
import { Sidebar, TopBar } from '../components/Sidebar'
import { Btn, Card, StatCard, SectionHeader, EmptyState, Table, StatusBadge, Tabs, Alert, Input, Select } from '../components/ui'
import { PageHeader } from '../components/PageHeader'
import { ConfirmModal } from '../components/Modal'
import { useToast } from '../components/Toast'
import { api, type AdvertiserDashboardData, type BannerSlot, type PaidBanner, type PaidPromotion, type SupportTicket } from '../lib/api'

type PayPalSdk = {
  FUNDING: { CARD: unknown }
  Buttons: (options: {
    fundingSource: unknown
    createOrder: () => Promise<string>
    onApprove: (data: { orderID: string }) => Promise<void>
    onError: () => void
  }) => { isEligible: () => boolean; render: (target: HTMLElement) => Promise<void> }
}

declare global {
  interface Window { paypal?: PayPalSdk }
}

function calendarDate(value: string | Date | null | undefined): string {
  if (!value) return ''
  const date = value instanceof Date ? value : new Date(value)
  return Number.isNaN(date.getTime()) ? '' : date.toISOString().slice(0, 10)
}

function displayDate(value: string | null | undefined): string {
  if (!value) return 'nije određen'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'nije određen' : new Intl.DateTimeFormat('sr-RS', { dateStyle: 'medium' }).format(date)
}

function loadPayPalSdk(clientId: string): Promise<PayPalSdk> {
  if (window.paypal) return Promise.resolve(window.paypal)
  const scriptId = 'paypal-standard-checkout-sdk'
  const existing = document.getElementById(scriptId) as HTMLScriptElement | null
  if (existing) {
    if (existing.dataset.loaded === 'true') return window.paypal ? Promise.resolve(window.paypal) : Promise.reject(new Error('PayPal Checkout nije učitan.'))
    return new Promise((resolve, reject) => {
      existing.addEventListener('load', () => window.paypal ? resolve(window.paypal) : reject(new Error('PayPal Checkout nije učitan.')), { once: true })
      existing.addEventListener('error', () => reject(new Error('PayPal Checkout nije dostupan.')), { once: true })
    })
  }
  return new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.id = scriptId
    script.src = `https://www.paypal.com/sdk/js?client-id=${encodeURIComponent(clientId)}&currency=EUR&intent=capture&components=buttons,funding-eligibility&enable-funding=card&disable-funding=venmo,paylater`
    script.async = true
    script.onload = () => {
      script.dataset.loaded = 'true'
      window.paypal ? resolve(window.paypal) : reject(new Error('PayPal Checkout nije učitan.'))
    }
    script.onerror = () => reject(new Error('PayPal Checkout nije dostupan.'))
    document.head.appendChild(script)
  })
}

function PayPalCardCheckout({ amountRsd, onCaptured, onError }: { amountRsd: number; onCaptured: () => void; onError: (message: string) => void }) {
  const hostRef = useRef<HTMLDivElement>(null)
  const [status, setStatus] = useState<'loading' | 'available' | 'unavailable' | 'error'>('loading')

  useEffect(() => {
    let cancelled = false
    const host = hostRef.current
    if (!host || !Number.isFinite(amountRsd) || amountRsd < 200) return
    host.replaceChildren()
    setStatus('loading')
    void (async () => {
      try {
        const config = await api.paypalCheckoutConfig()
        if (!config.card_checkout_enabled) {
          if (!cancelled) setStatus('unavailable')
          return
        }
        const paypal = await loadPayPalSdk(config.client_id)
        if (cancelled) return
        const buttons = paypal.Buttons({
          fundingSource: paypal.FUNDING.CARD,
          createOrder: async () => (await api.createPayPalOrder(amountRsd, 'smart_button')).order_id,
          onApprove: async ({ orderID }) => {
            await api.capturePayPalOrder(orderID)
            onCaptured()
          },
          onError: () => onError('Plaćanje karticom nije završeno. Budžet nije promenjen.'),
        })
        if (!buttons.isEligible()) {
          if (!cancelled) setStatus('unavailable')
          return
        }
        await buttons.render(host)
        if (!cancelled) setStatus('available')
      } catch (error) {
        if (!cancelled) {
          setStatus('error')
          onError(error instanceof Error ? error.message : 'Kartično plaćanje trenutno nije dostupno.')
        }
      }
    })()
    return () => { cancelled = true }
  }, [amountRsd])

  return (
    <div className="mt-3">
      <div ref={hostRef} />
      {status === 'loading' && <p className="text-xs text-ink-3">Proveravamo da li je kartično plaćanje dostupno...</p>}
      {status === 'unavailable' && <p className="text-xs text-ink-3">PayPal trenutno ne nudi kartično plaćanje za ovaj nalog ili kupca. Možeš nastaviti standardnim PayPal plaćanjem.</p>}
    </div>
  )
}

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

type TaskDetailField = { key: string; label: string; placeholder: string }

// Each approved work type has its own mandatory brief, rather than one vague description.
const TASK_FORM_FIELDS: Record<string, { title: string; intro: string; fields: TaskDetailField[] }> = {
  'Ankete i testiranja': { title: 'Brief za anketu', intro: 'Definiši koga pitaš, pitanja i prihvatljiv odgovor.', fields: [
    { key: 'audience', label: 'Ko treba da odgovara', placeholder: 'npr. osobe koje kupuju online najmanje jednom mesečno' },
    { key: 'questions', label: 'Pitanja i odgovori', placeholder: 'Navedi pitanja redom i minimalnu dužinu otvorenog odgovora.' },
    { key: 'completion', label: 'Kriterijum završetka', placeholder: 'npr. odgovoriti na svih 8 pitanja bez ličnih podataka' },
  ] },
  'Testiranje sajta ili aplikacije': { title: 'Brief za UX test', intro: 'Traži konkretne scenarije, ne samo posetu stranici.', fields: [
    { key: 'device', label: 'Uređaj i pregledač', placeholder: 'npr. Android telefon, Chrome; ili desktop, Firefox' },
    { key: 'scenarios', label: 'Scenariji testiranja', placeholder: '1. Pronađi proizvod. 2. Dodaj u korpu. 3. Opiši gde je nastao problem.' },
    { key: 'report', label: 'Format izveštaja', placeholder: 'Očekivano/stvarno ponašanje, koraci i screenshot ako postoji greška.' },
  ] },
  'Provera podataka': { title: 'Brief za proveru podataka', intro: 'Odredi izvor, polja koja se proveravaju i format predaje.', fields: [
    { key: 'source', label: 'Izvor podataka', placeholder: 'Link, tabela ili opis izvora koji korisnik proverava.' },
    { key: 'fields', label: 'Polja za proveru', placeholder: 'npr. naziv, adresa, telefon, radno vreme i pravilo za svako polje' },
    { key: 'output', label: 'Format rezultata', placeholder: 'npr. Naziv | proverena vrednost | izvor | napomena' },
  ] },
  'Kratak feedback': { title: 'Brief za feedback', intro: 'Traži iskreno mišljenje o materijalu, nikada lažnu javnu recenziju ili ocenu.', fields: [
    { key: 'material', label: 'Materijal za pregled', placeholder: 'Link ka stranici, prototipu, tekstu ili slici.' },
    { key: 'angles', label: 'Pitanja za feedback', placeholder: 'npr. šta je jasno, šta zbunjuje i šta bi promenio/la' },
    { key: 'minimum', label: 'Minimalni sadržaj odgovora', placeholder: 'npr. najmanje 3 odgovora od po 2 rečenice' },
  ] },
  'Lokalna provera': { title: 'Brief za lokalnu proveru', intro: 'Dozvoljene su samo bezbedne provere javno dostupnih informacija i mesta.', fields: [
    { key: 'place', label: 'Javno mesto ili područje', placeholder: 'npr. centar Novog Sada ili javno dostupna poslovnica' },
    { key: 'observations', label: 'Šta se proverava', placeholder: 'npr. radno vreme, dostupnost usluge i vidljivost izloga' },
    { key: 'safety', label: 'Ograničenja i dokaz', placeholder: 'Bez snimanja ljudi i privatnih prostora; navedi prihvatljiv dokaz.' },
  ] },
  'Označavanje podataka': { title: 'Brief za označavanje podataka', intro: 'Objasni skup podataka, oznake i granične slučajeve kroz primer.', fields: [
    { key: 'dataset', label: 'Skup podataka', placeholder: 'Šta korisnik označava i koliko stavki obrađuje.' },
    { key: 'labels', label: 'Oznake i pravila', placeholder: 'npr. relevantno / nije relevantno, sa jasnim kriterijumima.' },
    { key: 'examples', label: 'Primeri i kontrola kvaliteta', placeholder: 'Navedi makar jedan dobar i jedan loš primer odgovora.' },
  ] },
}

function NovaCampanja({ onCancel, onSuccess, onCreate, onRevise, feePercent, platformPublishing, categories, campaign }: { onCancel: () => void; onSuccess: () => void; onCreate: (payload: Parameters<typeof api.createCampaign>[0]) => Promise<void>; onRevise: (id: number, payload: Parameters<typeof api.createCampaign>[0]) => Promise<void>; feePercent: number; platformPublishing: boolean; categories: string[]; campaign?: import('../lib/api').Task }) {
  const [step, setStep] = useState(1)
  const [naziv, setNaziv] = useState(campaign?.title ?? '')
  const [reward, setReward] = useState(campaign ? String(campaign.reward_rsd) : '')
  const [budget, setBudget] = useState(campaign ? String(Math.ceil(campaign.reward_rsd * campaign.total_slots * (1 + feePercent / 100))) : '')
  const [slots, setSlots] = useState(campaign ? String(campaign.total_slots) : '')
  const [campaignDurationDays, setCampaignDurationDays] = useState(String(campaign?.campaign_duration_days ?? 30))
  const [description, setDescription] = useState(campaign?.description ?? '')
  const [taskUrl, setTaskUrl] = useState(campaign?.target_url ?? '')
  const [category, setCategory] = useState(campaign?.category ?? '')
  const [proofRequired, setProofRequired] = useState(campaign?.proof_required ?? 'screenshot')
  const [targetCity, setTargetCity] = useState(campaign?.target_city ?? 'Srbija')
  const [targetAgeGroup, setTargetAgeGroup] = useState(campaign?.target_age_group ?? '18+')
  const [targetInterests, setTargetInterests] = useState(campaign?.target_interests ?? '')
  const [requiresTesterEnrollment, setRequiresTesterEnrollment] = useState(campaign?.requires_tester_enrollment ?? false)
  const [testerRequiredCount, setTesterRequiredCount] = useState(String(campaign?.tester_required_count ?? 12))
  const [testerDurationDays, setTesterDurationDays] = useState(String(campaign?.tester_duration_days ?? 14))
  const [testerDailyMinutes, setTesterDailyMinutes] = useState(String(campaign?.tester_daily_minutes ?? 5))
  const [testerDailyReward, setTesterDailyReward] = useState(campaign?.tester_daily_reward_rsd ? String(campaign.tester_daily_reward_rsd) : '')
  const [taskDetails, setTaskDetails] = useState<Record<string, string>>({})
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const steps = ['Definicija', platformPublishing ? 'Nagrada i obim' : 'Nagrada i budžet', 'Publika i dokaz', 'Pregled']
  const taskForm = TASK_FORM_FIELDS[category]
  const hasCompleteBrief = Boolean(taskForm) && taskForm.fields.every(field => taskDetails[field.key]?.trim())
  const detailLines = taskForm?.fields.filter(field => taskDetails[field.key]?.trim()).map(field => `${field.label}: ${taskDetails[field.key].trim()}`) ?? []

  if (submitted) {
    return (
      <div className="flex flex-col items-center text-center py-12">
        <span className="text-5xl mb-4">🎉</span>
        <h2 className="text-xl font-extrabold text-ink mb-2">{campaign ? 'Izmena je poslata na moderaciju!' : 'Kampanja je poslata na moderaciju!'}</h2>
        <p className="text-sm text-ink-2 max-w-xs mb-6">Dobićeš obaveštenje kada kampanja bude odobrena. Status možeš pratiti u sekciji Kampanje.</p>
        <Btn onClick={onSuccess}>Idi na kampanje</Btn>
      </div>
    )
  }

  return (
    <div>
      <SectionHeader title={campaign ? 'Doradi kampanju' : 'Nova kampanja'} description={campaign?.moderation_note || 'Kreiraj merljiv, bezbedan zadatak koji može da se proveri dokazom.'} />
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
            <Input label="Naziv kampanje" placeholder="npr. Test poručivanja na sajtu — oktobar" value={naziv} onChange={setNaziv} />
            <Select label="Vrsta zadatka" options={[
              { value: '', label: 'Odaberi vrstu zadatka' },
              ...categories.map(value => ({ value, label: value })),
            ]} value={category} onChange={value => { setCategory(value); setTaskDetails({}) }} />
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-bold text-ink-2 uppercase tracking-wide">Cilj zadatka</label>
              <textarea value={description} onChange={event => setDescription(event.target.value)} rows={3} placeholder="Koju poslovnu odluku ili problem ovaj zadatak pomaže da se proveri?" className="bg-white border border-frame text-ink placeholder-ink-4 rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none resize-none" />
            </div>
            <Input label="Link za zadatak (opciono)" placeholder="https://vas-sajt.rs/test" value={taskUrl} onChange={setTaskUrl} />
            {category === 'Testiranje sajta ili aplikacije' && <label className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950 cursor-pointer">
              <input type="checkbox" checked={requiresTesterEnrollment} onChange={event => setRequiresTesterEnrollment(event.target.checked)} className="mt-0.5 h-4 w-4" />
              <span><strong>Zatvoreni beta test</strong><br /><span className="text-xs text-amber-800">Korisnik prvo šalje email za pristup testiranju. Tek kada ga ručno dodaš u odgovarajuću tester listu i označiš kao pozvanog, može da pokrene zadatak.</span></span>
            </label>}
            {requiresTesterEnrollment && <div className="grid gap-3 rounded-xl border border-amber-200 bg-amber-50/50 p-4 sm:grid-cols-2">
              <Input label="Obavezno aktivnih testera" type="number" min={12} value={testerRequiredCount} onChange={setTesterRequiredCount} />
              <Input label="Trajanje po testeru (dani)" type="number" min={14} max={31} value={testerDurationDays} onChange={setTesterDurationDays} />
              <Input label="Dnevni minimum (minuti)" type="number" min={1} max={60} value={testerDailyMinutes} onChange={setTesterDailyMinutes} />
              <p className="self-end text-xs leading-5 text-amber-900">Svaki tester ima sopstvenih 14 dana od trenutka kada ga ručno označiš kao aktivnog. Google Play proverava ostanak u zatvorenom testu; KlikZarada vodi dnevne izveštaje.</p>
            </div>}
            {taskForm && <div className="rounded-xl border border-blue-100 bg-blue-50/50 p-4 space-y-3">
              <div><h4 className="font-bold text-ink">{taskForm.title}</h4><p className="mt-1 text-xs leading-5 text-ink-2">{taskForm.intro}</p></div>
              {taskForm.fields.map(field => <div key={field.key} className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-ink-2 uppercase tracking-wide">{field.label}</label>
                <textarea value={taskDetails[field.key] ?? ''} onChange={event => setTaskDetails(current => ({ ...current, [field.key]: event.target.value }))} rows={2} placeholder={field.placeholder} className="bg-white border border-frame text-ink placeholder-ink-4 rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none resize-none" />
              </div>)}
            </div>}
            <div className="flex gap-2">
              <Btn variant="ghost" onClick={onCancel} size="sm">Otkaži</Btn>
              <Btn onClick={() => setStep(2)} disabled={!naziv || !description || !category || !hasCompleteBrief} className="flex-1 justify-center">Dalje →</Btn>
            </div>
          </div>
        )}
        {step === 2 && (
          <div className="space-y-4">
            <h3 className="font-bold text-ink">{platformPublishing ? 'Nagrada i obim' : 'Nagrada i budžet'}</h3>
            {requiresTesterEnrollment
              ? <Input label="Nagrada po danu testiranja (RSD)" placeholder="npr. 20" type="number" min={1} value={testerDailyReward} onChange={setTesterDailyReward} />
              : <Input label="Nagrada po zadatku (RSD)" placeholder="npr. 80" value={reward} onChange={setReward} />}
            {platformPublishing
              ? <Input label="Broj korisnika / izvršenja" placeholder="npr. 50" type="number" min={1} step={1} value={slots} onChange={setSlots} />
              : <Input label="Ukupni budžet (RSD)" placeholder="npr. 5000" value={budget} onChange={setBudget} />}
            <Input label="Trajanje kampanje (dani)" type="number" min={1} max={365} step={1} value={campaignDurationDays} onChange={value => setCampaignDurationDays(String(Math.min(365, Math.max(1, Math.floor(Number(value) || 1)))))} />
            {requiresTesterEnrollment && testerDailyReward && <Alert type="warning">Ukupna nagrada po testeru je <strong>{Number(testerDailyReward) * Number(testerDurationDays || 14)} RSD</strong>: {testerDailyReward} RSD dnevno tokom {testerDurationDays || 14} dana. Svaki dnevni izveštaj odobravaš posebno.</Alert>}
            {platformPublishing && (requiresTesterEnrollment ? testerDailyReward : reward) && slots ? (
              <Alert type="info">Platformska objava je <strong>bez naknade</strong>. Odobrene dnevne nagrade ostaju stvarni trošak platforme.</Alert>
            ) : !requiresTesterEnrollment && reward && budget && (
              <Alert type="info">Procenjeno: <strong className="font-mono">{Math.floor(Number(budget) / (Number(reward) * (1 + feePercent / 100)))}</strong> izvršenih zadataka u okviru unetog ukupnog budžeta.</Alert>
            )}
            <div className="flex gap-2">
              <Btn onClick={() => setStep(1)} variant="secondary">← Prethodni korak</Btn>
              <Btn onClick={() => setStep(3)} disabled={!(requiresTesterEnrollment ? testerDailyReward : reward) || !(platformPublishing ? slots : budget)} className="flex-1 justify-center">Dalje →</Btn>
            </div>
          </div>
        )}
        {step === 3 && (
          <div className="space-y-4">
            <h3 className="font-bold text-ink">Ciljna publika i dokaz</h3>
            <Input label="Država ili grad (opciono)" placeholder="npr. Srbija ili Novi Sad" value={targetCity} onChange={setTargetCity} />
            <Select label="Starosna grupa" options={[
              { value: '18+', label: '18+ godina' },
              { value: '18-24', label: '18–24 godine' },
              { value: '25-44', label: '25–44 godine' },
              { value: '45+', label: '45+ godina' },
            ]} value={targetAgeGroup} onChange={setTargetAgeGroup} />
            <Input label="Interesovanja publike (opciono)" placeholder="npr. online kupovina, tehnologija" value={targetInterests} onChange={setTargetInterests} />
            <Select label="Potreban dokaz" options={[
              { value: '', label: 'Odaberi tip dokaza' },
              { value: 'screenshot', label: 'Screenshot' },
              { value: 'link', label: 'Screenshot + link' },
              { value: 'video', label: 'Video snimak' },
              { value: 'kod', label: 'Kod potvrde' },
            ]} value={proofRequired} onChange={setProofRequired} />
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
                <div className="flex justify-between gap-4"><span className="text-ink-2">Kategorija</span><span className="font-semibold text-ink text-right">{category}</span></div>
                <div className="flex justify-between gap-4"><span className="text-ink-2">Trajanje kampanje</span><span className="font-semibold text-ink text-right">{campaignDurationDays} dana od odobrenja</span></div>
                {requiresTesterEnrollment && <><div className="flex justify-between gap-4"><span className="text-ink-2">Pristup aplikaciji</span><span className="font-semibold text-amber-800 text-right">Ručno dodavanje testera</span></div><div className="flex justify-between gap-4"><span className="text-ink-2">Plan testiranja</span><span className="font-semibold text-amber-800 text-right">{testerRequiredCount} testera, {testerDurationDays} dana, min. {testerDailyMinutes} min/dan</span></div><div className="flex justify-between gap-4"><span className="text-ink-2">Dnevna nagrada</span><span className="font-mono font-bold text-emerald-600">{testerDailyReward || 0} RSD</span></div></>}
                <div><span className="text-ink-2">Precizni detalji</span><ul className="mt-1 list-disc space-y-1 pl-4 text-xs text-ink">{detailLines.map(line => <li key={line}>{line}</li>)}</ul></div>
                <div className="flex justify-between"><span className="text-ink-2">Ukupno po testeru</span><span className="font-mono font-bold text-emerald-600">{requiresTesterEnrollment ? Number(testerDailyReward || 0) * Number(testerDurationDays || 14) : reward} RSD</span></div>
                {platformPublishing
                  ? <><div className="flex justify-between"><span className="text-ink-2">Broj izvršenja</span><span className="font-mono font-bold text-blue-600">{slots}</span></div><div className="flex justify-between"><span className="text-ink-2">Naknada objave</span><span className="font-mono font-bold text-emerald-600">0 RSD</span></div></>
                  : <div className="flex justify-between"><span className="text-ink-2">Budžet</span><span className="font-mono font-bold text-blue-600">{budget} RSD</span></div>}
            </div>
            {error && <Alert type="error">{error}</Alert>}
            <Alert type="warning">{platformPublishing ? 'Platformska kampanja ide na moderaciju pre aktivacije. Nema PayPal naplate ni rezervacije budžeta.' : 'Kampanja ide na moderaciju pre aktivacije. Budžet se rezerviše tek kada zahtev prođe proveru dostupnih sredstava.'}</Alert>
            <div className="flex gap-2">
              <Btn onClick={() => setStep(3)} variant="secondary">← Izmeni prethodni korak</Btn>
              <Btn disabled={submitting} onClick={async () => {
                const rewardRsd = requiresTesterEnrollment ? Number(testerDailyReward) * Number(testerDurationDays) : Number(reward)
                const totalSlots = platformPublishing ? Math.floor(Number(slots)) : Math.floor(Number(budget) / (rewardRsd * (1 + feePercent / 100)))
                const durationValid = Number.isInteger(Number(campaignDurationDays)) && Number(campaignDurationDays) >= 1 && Number(campaignDurationDays) <= 365
                const testerConfigValid = !requiresTesterEnrollment || (Number(testerRequiredCount) >= 12 && Number(testerDurationDays) >= 14 && Number(testerDurationDays) <= 31 && Number(testerDailyMinutes) >= 1 && Number(testerDailyReward) > 0 && totalSlots >= Number(testerRequiredCount))
                if (!Number.isFinite(rewardRsd) || rewardRsd <= 0 || totalSlots < 1 || !testerConfigValid || !durationValid) {
                  setError(platformPublishing ? 'Unesi validnu nagradu i broj izvršenja od najmanje jedan.' : 'Unesi validnu nagradu i budžet dovoljan za najmanje jedan zadatak.')
                  return
                }
                setSubmitting(true)
                setError('')
                try {
                  const fullDescription = `${description.trim()}\n\nSpecifikacija zadatka:\n${detailLines.map(line => `- ${line}`).join('\n')}`
                  const betaPlan = requiresTesterEnrollment ? `\n\nPlan zatvorenog beta testiranja:\n- Tester prvo šalje email za poziv u store tester listu.\n- Svaki tester ima ${testerDurationDays} dana od ručne potvrde pristupa.\n- Svakog dana testira najmanje ${testerDailyMinutes} minuta i šalje kratak izveštaj.\n- Dnevna nagrada: ${testerDailyReward} RSD, uz odobrenje oglašivača.` : ''
                  const payload = { title: naziv, category, task_type: category, target_url: taskUrl || undefined, description: fullDescription + betaPlan, instructions: `Korisnik treba da prati specifikaciju zadatka i dostavi samo traženi dokaz.\n${detailLines.map(line => `- ${line}`).join('\n')}${betaPlan}`, proof_required: proofRequired, reward_rsd: rewardRsd, total_slots: totalSlots, campaign_duration_days: Number(campaignDurationDays), target_city: targetCity || undefined, target_age_group: targetAgeGroup, target_interests: targetInterests || undefined, requires_tester_enrollment: requiresTesterEnrollment, tester_required_count: Number(testerRequiredCount), tester_duration_days: Number(testerDurationDays), tester_daily_minutes: Number(testerDailyMinutes), tester_daily_reward_rsd: requiresTesterEnrollment ? Number(testerDailyReward) : 0 }
                  if (campaign) await onRevise(campaign.id, payload)
                  else await onCreate(payload)
                  setSubmitted(true)
                } catch (requestError) {
                  setError(requestError instanceof Error ? requestError.message : 'Kampanja nije poslata.')
                } finally {
                  setSubmitting(false)
                }
              }} variant="success" className="flex-1 justify-center">{submitting ? 'Slanje...' : campaign ? '✓ Pošalji izmenu na moderaciju' : '✓ Pošalji na moderaciju'}</Btn>
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
  const [logoutConfirm, setLogoutConfirm] = useState(false)
  const [campaignLifecycleAction, setCampaignLifecycleAction] = useState<{ id: number; title: string; action: 'pause' | 'resume' | 'stop' } | null>(null)
  const [dashboard, setDashboard] = useState<AdvertiserDashboardData | null>(null)
  const [campaignToRevise, setCampaignToRevise] = useState<import('../lib/api').Task | null>(null)
  const [dashboardError, setDashboardError] = useState('')
  const [topupAmount, setTopupAmount] = useState('')
  const [topupError, setTopupError] = useState('')
  const [topupLoading, setTopupLoading] = useState(false)
  const [bannerSlots, setBannerSlots] = useState<BannerSlot[]>([])
  const [ownBanners, setOwnBanners] = useState<PaidBanner[]>([])
  const [promotions, setPromotions] = useState<PaidPromotion[]>([])
  const [promotionTaskId, setPromotionTaskId] = useState('')
  const [promotionType, setPromotionType] = useState<'featured' | 'priority'>('featured')
  const [promotionDays, setPromotionDays] = useState('7')
  const [promotionError, setPromotionError] = useState('')
  const [promotionLoading, setPromotionLoading] = useState(false)
  const [bannerSlotId, setBannerSlotId] = useState('')
  const [bannerTitle, setBannerTitle] = useState('')
  const [bannerBody, setBannerBody] = useState('')
  const [bannerImageUrl, setBannerImageUrl] = useState('')
  const [bannerUrl, setBannerUrl] = useState('')
  const [bannerDays, setBannerDays] = useState('7')
  const [bannerStartDate, setBannerStartDate] = useState(() => calendarDate(new Date()))
  const [bannerError, setBannerError] = useState('')
  const [bannerLoading, setBannerLoading] = useState(false)
  const [bannerUploading, setBannerUploading] = useState(false)
  const [profileName, setProfileName] = useState('')
  const [profilePhone, setProfilePhone] = useState('')
  const [profileCity, setProfileCity] = useState('')
  const [companyName, setCompanyName] = useState('')
  const [companyPib, setCompanyPib] = useState('')
  const [companyWebsite, setCompanyWebsite] = useState('')
  const [companyActivity, setCompanyActivity] = useState('')
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [repeatPassword, setRepeatPassword] = useState('')
  const [profileSaving, setProfileSaving] = useState(false)
  const [tickets, setTickets] = useState<SupportTicket[]>([])
  const [ticketSubject, setTicketSubject] = useState('')
  const [ticketBody, setTicketBody] = useState('')
  const [ticketLoading, setTicketLoading] = useState(false)
  const { show: showToast, node: toastNode } = useToast()

  const refreshDashboard = async () => {
    try {
      const [dashboardData, bannerData, promotionData, ticketData] = await Promise.all([api.advertiserDashboard(), api.advertiserBanners(), api.advertiserPromotions(), api.tickets()])
      setDashboard(dashboardData)
      setBannerSlots(bannerData.slots)
      setOwnBanners(bannerData.banners)
      setPromotions(promotionData.promotions)
      setTickets(ticketData.tickets)
      setBannerSlotId(current => current || String(bannerData.slots[0]?.id ?? ''))
      setPromotionTaskId(current => current || String(dashboardData.tasks.find(task => task.status === 'aktivno' || task.status === 'active')?.id ?? ''))
      setProfileName(current => current || dashboardData.user.full_name)
      setProfilePhone(current => current || dashboardData.user.phone || '')
      setProfileCity(current => current || dashboardData.user.city || '')
      setCompanyName(current => current || dashboardData.user.company_name || '')
      setCompanyPib(current => current || dashboardData.user.company_pib || '')
      setCompanyWebsite(current => current || dashboardData.user.company_website || '')
      setCompanyActivity(current => current || dashboardData.user.company_activity || '')
      setDashboardError('')
    } catch (error) {
      setDashboardError(error instanceof Error ? error.message : 'Podaci trenutno nisu dostupni.')
    }
  }

  useEffect(() => { void refreshDashboard() }, [])

  useEffect(() => {
    const payment = new URLSearchParams(window.location.search).get('payment')
    if (!payment) return
    const messages: Record<string, string> = {
      success: 'PayPal uplata je potvrđena i budžet je dopunjen.',
      cancelled: 'PayPal uplata je otkazana. Budžet nije promenjen.',
      error: 'Uplata nije potvrđena. Budžet nije promenjen.',
    }
    if (messages[payment]) showToast(messages[payment], payment === 'success' ? 'success' : 'error')
    window.history.replaceState({}, document.title, window.location.pathname)
    if (payment === 'success') void refreshDashboard()
  }, [])

  const startPayPalTopup = async () => {
    const amount = Number(topupAmount.replace(',', '.'))
    if (!Number.isFinite(amount) || amount < 200) {
      setTopupError('Unesi iznos od najmanje 200 RSD.')
      return
    }
    setTopupLoading(true)
    setTopupError('')
    try {
      const order = await api.createPayPalOrder(amount)
      window.location.assign(order.approval_url)
    } catch (error) {
      setTopupError(error instanceof Error ? error.message : 'PayPal uplata nije mogla da se pokrene.')
      setTopupLoading(false)
    }
  }

  const reserveBanner = async () => {
    const daysCount = Number(bannerDays)
    if (!bannerSlotId || !bannerStartDate || !bannerTitle.trim() || !bannerUrl.trim() || !Number.isInteger(daysCount) || daysCount < 1 || daysCount > 31) {
      setBannerError('Izaberi slot i datum početka, unesi naslov i link, pa trajanje od 1 do 31 dana.')
      return
    }
    setBannerLoading(true)
    setBannerError('')
    try {
      const result = await api.reserveAdvertiserBanner({
        slot_id: Number(bannerSlotId),
        title: bannerTitle.trim(),
        body: bannerBody.trim() || undefined,
        image_url: bannerImageUrl.trim() || undefined,
        target_url: bannerUrl.trim(),
        days_count: daysCount,
        requested_start_at: `${bannerStartDate}T12:00:00`,
      })
      setBannerTitle('')
      setBannerBody('')
      setBannerImageUrl('')
      setBannerUrl('')
      await refreshDashboard()
      showToast(platformPublishing ? 'Platformski banner je poslat na moderaciju bez naknade.' : `Zakup je rezervisan: ${new Intl.NumberFormat('sr-RS').format(result.reserved_rsd)} RSD. Čeka odobrenje admina.`, 'success')
    } catch (error) {
      setBannerError(error instanceof Error ? error.message : 'Zakup banera nije uspeo.')
    } finally {
      setBannerLoading(false)
    }
  }

  const uploadBanner = async (file: File | undefined) => {
    if (!file) return
    setBannerUploading(true)
    setBannerError('')
    try {
      const result = await api.uploadAdvertiserBanner(file)
      setBannerImageUrl(result.image_url)
      showToast(`Slika je otpremljena (${result.width}×${result.height}). ${result.warning}`, 'success')
    } catch (error) {
      setBannerError(error instanceof Error ? error.message : 'Upload bannera nije uspeo.')
    } finally { setBannerUploading(false) }
  }

  const reservePromotion = async () => {
    const daysCount = Number(promotionDays)
    if (!promotionTaskId || !Number.isInteger(daysCount) || daysCount < 1 || daysCount > 31) {
      setPromotionError('Izaberi aktivnu kampanju i trajanje od 1 do 31 dana.')
      return
    }
    setPromotionLoading(true)
    setPromotionError('')
    try {
      const result = await api.reserveAdvertiserPromotion({ task_id: Number(promotionTaskId), promotion_type: promotionType, days_count: daysCount })
      await refreshDashboard()
      showToast(platformPublishing ? 'Platformska VIP promocija je poslata na moderaciju bez naknade.' : `Promocija je rezervisana: ${new Intl.NumberFormat('sr-RS').format(result.reserved_rsd)} RSD. Čeka odobrenje admina.`, 'success')
    } catch (error) {
      setPromotionError(error instanceof Error ? error.message : 'Promocija nije rezervisana.')
    } finally { setPromotionLoading(false) }
  }

  const createTicket = async () => {
    if (ticketSubject.trim().length < 3 || ticketBody.trim().length < 5) {
      showToast('Unesi naslov i poruku od najmanje 5 karaktera.', 'warning')
      return
    }
    setTicketLoading(true)
    try {
      await api.createTicket({ subject: ticketSubject.trim(), body: ticketBody.trim(), category: 'Oglašivač' })
      setTicketSubject('')
      setTicketBody('')
      await refreshDashboard()
      showToast('Tiket je poslat podršci.', 'success')
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Tiket nije poslat.', 'error')
    } finally { setTicketLoading(false) }
  }

  const advertiser = dashboard?.user
  const pricing = dashboard?.pricing
  const platformPublishing = advertiser?.platform_publishing === true
  const feePercent = pricing?.platform_fee_percent ?? 20
  const feeMultiplier = 1 + feePercent / 100
  const selectedBannerSlot = bannerSlots.find(slot => slot.id === Number(bannerSlotId))
  const bannerMaxDays = pricing?.banner_max_days ?? 31
  const normalizedBannerDays = Math.min(bannerMaxDays, Math.max(1, Math.floor(Number(bannerDays) || 1)))
  const selectedBannerPrice = selectedBannerSlot
    ? selectedBannerSlot.price_rsd * normalizedBannerDays / (pricing?.banner_price_basis_days ?? 7)
    : 0
  const selectBannerSlot = (value: string) => {
    setBannerSlotId(value)
    const slot = bannerSlots.find(item => item.id === Number(value))
    const earliest = calendarDate(slot?.next_available_at)
    if (earliest && earliest > bannerStartDate) setBannerStartDate(earliest)
  }
  const campaigns = (dashboard?.tasks ?? []).map(task => ({
    task,
    naziv: task.title,
    budžet: platformPublishing ? `${new Intl.NumberFormat('sr-RS').format(task.reward_rsd * task.total_slots)} RSD nagrada` : `${new Intl.NumberFormat('sr-RS').format(task.reward_rsd * task.total_slots * feeMultiplier)} RSD`,
    potrošeno: task.requires_tester_enrollment
      ? `${new Intl.NumberFormat('sr-RS').format((task.tester_checkin_approved ?? 0) * task.tester_daily_reward_rsd * (platformPublishing ? 1 : feeMultiplier))} RSD`
      : platformPublishing ? `${new Intl.NumberFormat('sr-RS').format(task.reward_rsd * task.used_slots)} RSD nagrada` : `${new Intl.NumberFormat('sr-RS').format(task.reward_rsd * task.used_slots * feeMultiplier)} RSD`,
    dokazi: task.requires_tester_enrollment ? (task.tester_checkin_total ?? 0) : (task.submission_total ?? 0),
    odobreno: task.submission_approved ?? 0,
    naProveri: task.submission_pending ?? 0,
    status: task.status === 'active' ? 'aktivno' : task.status === 'pending' ? 'na_cekanju' : task.status === 'paused' ? 'obustavljeno' : task.status === 'stopped' ? 'zavrseno' : task.status === 'expired' ? 'isteklo' : task.status === 'rejected' ? 'odbijeno' : task.status === 'needs_revision' ? 'dorada' : task.status,
  }))
  const proofs = (dashboard?.submissions ?? []).map(submission => ({
    submission,
    id: submission.id,
    korisnik: submission.user_name || 'Korisnik',
    zadatak: submission.task_title,
    poslato: submission.created_at ? new Intl.DateTimeFormat('sr-RS').format(new Date(submission.created_at)) : '—',
    status: submission.status === 'pending' ? 'na_proveri' : submission.status === 'approved' ? 'odobreno' : submission.status === 'rejected' ? 'odbijeno' : submission.status,
  }))
  const testerEnrollments = dashboard?.tester_enrollments ?? []
  const testerCheckins = dashboard?.tester_checkins ?? []

  function goTo(p: Page) { setPage(p) }
  const back = BACK[page]
  const crumbs = CRUMBS[page]

  const sidebarFooter = (
    <div className="flex items-center gap-2.5">
      <div className="w-8 h-8 rounded-full bg-violet-600 flex items-center justify-center text-white text-sm font-bold">{advertiser?.full_name?.slice(0, 1).toUpperCase() || 'O'}</div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-white truncate">{advertiser?.company_name || advertiser?.full_name || 'Učitavanje...'}</p>
        <p className="text-xs" style={{ color: '#9AB1C8' }}>{advertiser?.role === 'admin' ? 'Admin · objava platforme' : 'Oglašivač'}</p>
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

  function proofStatus(_id: number, original: string) { return original }

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
        onConfirm={async () => { try { await api.logout() } finally { onNavigate('home') } }}
        onCancel={() => setLogoutConfirm(false)}
      />

      <ConfirmModal
        open={campaignLifecycleAction !== null}
        title={campaignLifecycleAction?.action === 'pause' ? 'Pauzirati kampanju?' : campaignLifecycleAction?.action === 'resume' ? 'Ponovo aktivirati kampanju?' : 'Završiti kampanju pre isteka?'}
        description={campaignLifecycleAction?.action === 'pause'
          ? `Kampanja „${campaignLifecycleAction?.title}” neće biti dostupna korisnicima dok je ponovo ne aktiviraš. Kraj kampanje se produžava za vreme pauze.`
          : campaignLifecycleAction?.action === 'resume'
            ? `Kampanja „${campaignLifecycleAction?.title}” ponovo postaje dostupna korisnicima.`
            : `Kampanja „${campaignLifecycleAction?.title}” se trajno zaustavlja. Neiskorišćeni rezervisani budžet vraća se na raspoloživi budžet, dok već poslati dokazi ostaju pokriveni.`}
        confirmLabel={campaignLifecycleAction?.action === 'pause' ? 'Pauziraj' : campaignLifecycleAction?.action === 'resume' ? 'Aktiviraj' : 'Završi kampanju'}
        cancelLabel="Otkaži"
        variant={campaignLifecycleAction?.action === 'stop' ? 'danger' : campaignLifecycleAction?.action === 'resume' ? 'success' : 'danger'}
        onConfirm={async () => {
          if (!campaignLifecycleAction) return
          try {
            await api.updateCampaignLifecycle(campaignLifecycleAction.id, campaignLifecycleAction.action)
            await refreshDashboard()
            showToast(campaignLifecycleAction.action === 'pause' ? 'Kampanja je pauzirana.' : campaignLifecycleAction.action === 'resume' ? 'Kampanja je ponovo aktivna.' : 'Kampanja je završena, a neiskorišćeni budžet je vraćen.', campaignLifecycleAction.action === 'stop' ? 'warning' : 'success')
            setCampaignLifecycleAction(null)
          } catch (error) {
            showToast(error instanceof Error ? error.message : 'Status kampanje nije promenjen.', 'error')
          }
        }}
        onCancel={() => setCampaignLifecycleAction(null)}
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

      <div className="flex-1 min-w-0 flex flex-col overflow-hidden">
        <TopBar
          onMenuClick={() => setMobileOpen(true)}
          pageTitle={advertiser?.role === 'admin' ? 'Objave platforme' : 'Oglašivački panel'}
          badge={advertiser?.role === 'admin' ? 'Admin' : undefined}
          onNavigate={onNavigate}
          actions={<div className="flex gap-2">{advertiser?.role === 'admin' && <Btn onClick={() => onNavigate('admin')} variant="secondary" size="sm" className="hidden sm:inline-flex">Admin</Btn>}<Btn onClick={() => goTo('nova')} size="sm">+ Nova kampanja</Btn></div>}
        />
        <main className="flex-1 overflow-y-auto bg-mint-50">
          <div className="w-full max-w-none px-4 py-6 sm:px-6 xl:px-8 2xl:px-10">
            {dashboardError && <div className="mb-4"><Alert type="error">{dashboardError}</Alert></div>}
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
                {advertiser && (!advertiser.company_name || !advertiser.phone || !advertiser.company_website) && <Card className="p-5 border-blue-200 bg-blue-50"><div className="flex flex-wrap items-center justify-between gap-4"><div><p className="font-bold text-ink">Završi profil oglašivača</p><p className="text-sm text-ink-2 mt-1">Za sigurniju moderaciju kampanja dodaj naziv, kontakt telefon i sajt firme ili ponude.</p></div><Btn size="sm" onClick={() => goTo('profil')}>Dopuni profil</Btn></div><div className="flex flex-wrap gap-2 mt-3 text-xs font-semibold"><span className={`rounded-full px-2 py-1 ${advertiser.company_name ? 'bg-emerald-100 text-emerald-700' : 'bg-white text-ink-3'}`}>Naziv {advertiser.company_name ? 'spreman' : 'nedostaje'}</span><span className={`rounded-full px-2 py-1 ${advertiser.phone ? 'bg-emerald-100 text-emerald-700' : 'bg-white text-ink-3'}`}>Telefon {advertiser.phone ? 'spreman' : 'nedostaje'}</span><span className={`rounded-full px-2 py-1 ${advertiser.company_website ? 'bg-emerald-100 text-emerald-700' : 'bg-white text-ink-3'}`}>Sajt {advertiser.company_website ? 'spreman' : 'nedostaje'}</span></div></Card>}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                  <StatCard label="Raspoloživi budžet" value={`${new Intl.NumberFormat('sr-RS').format(advertiser?.advertiser_budget_rsd ?? 0)} RSD`} accent="green" icon="💰" />
                  <StatCard label="Rezervisan budžet" value={`${new Intl.NumberFormat('sr-RS').format(advertiser?.advertiser_reserved_rsd ?? 0)} RSD`} accent="orange" icon="🔒" />
                  <StatCard label="Aktivnih kampanja" value={String((dashboard?.tasks ?? []).filter(task => task.status === 'active').length)} accent="blue" icon="🎯" />
                  <StatCard label="Odobrenih dokaza" value={String((dashboard?.submissions ?? []).filter(submission => submission.status === 'approved').length)} accent="teal" icon="✅" />
                </div>
                <SectionHeader title="Kampanje" action={<Btn onClick={() => goTo('kampanje')} variant="ghost" size="sm">Sve →</Btn>} />
                <Card>
                  <Table
                    headers={['Naziv', 'Budžet', 'Potrošeno', 'Dokazi', 'Status']}
                    rows={campaigns.map(c => [
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
                    rows={proofs.filter(p => proofStatus(p.id, p.status) === 'na_proveri').map(p => [
                      <span className="font-mono text-xs">{p.korisnik}</span>,
                      <span>{p.zadatak}</span>,
                      <span className="font-mono text-xs">{p.poslato}</span>,
                      <StatusBadge status={proofStatus(p.id, p.status)} />,
                      <span className="text-xs text-ink-3">Pregledaj kao oglašivač</span>,
                    ])}
                  />
                </Card>
              </div>
            )}

            {page === 'nova' && (
              <NovaCampanja
                key={campaignToRevise?.id ?? 'new'}
                onCancel={() => { setCampaignToRevise(null); goTo('pregled') }}
                onSuccess={() => { setCampaignToRevise(null); goTo('kampanje') }}
                onCreate={async payload => { await api.createCampaign(payload); await refreshDashboard(); showToast('Kampanja je poslata na moderaciju.', 'success') }}
                onRevise={async (id, payload) => { await api.reviseCampaign(id, payload); await refreshDashboard(); showToast('Izmena kampanje je poslata na novu moderaciju.', 'success') }}
                feePercent={feePercent}
                platformPublishing={platformPublishing}
                categories={pricing?.task_categories ?? []}
                campaign={campaignToRevise ?? undefined}
              />
            )}

            {page === 'kampanje' && (
              <div>
                <SectionHeader title="Moje kampanje" action={<Btn onClick={() => { setCampaignToRevise(null); goTo('nova') }} size="sm">+ Nova kampanja</Btn>} />
                <Card>
                  <Table
                    headers={['Naziv', 'Trajanje', 'Budžet', 'Potrošeno', 'Dokazi', 'Status', 'Akcija']}
                    rows={campaigns.map(c => [
                      <span className="font-semibold text-ink">{c.naziv}</span>,
                      <span className="text-xs text-ink-2">{c.task.starts_at && c.task.ends_at ? <>{new Intl.DateTimeFormat('sr-RS').format(new Date(c.task.starts_at))}<br />do {new Intl.DateTimeFormat('sr-RS').format(new Date(c.task.ends_at))}</> : `Po odobrenju · ${c.task.campaign_duration_days} dana`}</span>,
                      <span className="font-mono">{c.budžet}</span>,
                      <span className="font-mono text-amber-700">{c.potrošeno}</span>,
                      <span className="font-mono">{c.dokazi}</span>,
                      <StatusBadge status={c.status} />,
                       c.task.status === 'needs_revision'
                         ? <Btn size="sm" variant="secondary" onClick={() => { setCampaignToRevise(c.task); goTo('nova') }}>Doradi</Btn>
                         : c.task.status === 'active'
                           ? <div className="flex flex-wrap gap-1.5"><Btn size="sm" variant="secondary" onClick={() => setCampaignLifecycleAction({ id: c.task.id, title: c.task.title, action: 'pause' })}>Pauziraj</Btn><Btn size="sm" variant="danger" onClick={() => setCampaignLifecycleAction({ id: c.task.id, title: c.task.title, action: 'stop' })}>Završi</Btn></div>
                           : c.task.status === 'paused'
                             ? <div className="flex flex-wrap gap-1.5"><Btn size="sm" variant="success" onClick={() => setCampaignLifecycleAction({ id: c.task.id, title: c.task.title, action: 'resume' })}>Nastavi</Btn><Btn size="sm" variant="danger" onClick={() => setCampaignLifecycleAction({ id: c.task.id, title: c.task.title, action: 'stop' })}>Završi</Btn></div>
                             : <span className="text-xs text-ink-3">{c.task.moderation_note || 'Čeka proveru'}</span>,
                    ])}
                  />
                </Card>
              </div>
            )}

            {page === 'dokazi' && (
              <div>
                <SectionHeader title="Dokazi korisnika" description="Ti odlučuješ o rezultatu svoje kampanje. Admin interveniše samo kod spora ili anti-fraud provere." />
                {testerEnrollments.length > 0 && <div className="mb-5">
                  <SectionHeader title="Prijave za zatvoreno testiranje" description="Početnu kohortu aktiviraj tek kada su svi testeri stvarno dodati u store listu. Prvih 12 tada dobija isti datum početka i zajedničkih 14 dana." />
                  <div className="mb-4 grid gap-3">
                    {(dashboard?.tasks ?? []).filter(task => task.requires_tester_enrollment).map(task => {
                      const requested = testerEnrollments.filter(item => item.task_id === task.id && item.status === 'requested').length
                      const initialCohort = !(task.tester_cohort_count ?? 0)
                      const needed = task.tester_required_count
                      const canStart = initialCohort ? requested >= needed : requested > 0
                      return <Card key={task.id} className="flex flex-wrap items-center justify-between gap-3 border-amber-200 bg-amber-50/60">
                        <div>
                          <p className="font-bold text-ink">{task.title}</p>
                          <p className="mt-1 text-xs text-amber-950">{initialCohort ? `Početna Google kohorta: ${requested}/${needed} spremnih prijava.` : `Sledeća kohorta: ${requested} prijava čeka aktivaciju.`} Aktivni testeri: {task.tester_enrollment_invited ?? 0}.</p>
                        </div>
                        <Btn size="sm" disabled={!canStart} variant="success" onClick={() => void (async () => { try { const result = await api.startTesterCohort(task.id, initialCohort ? needed : undefined); await refreshDashboard(); showToast(`Kohorta ${result.cohort_number} je aktivirana za ${result.activated_count} testera istog dana.`, 'success') } catch (error) { showToast(error instanceof Error ? error.message : 'Kohorta nije aktivirana.', 'error') } })()}>
                          {initialCohort ? `Pokreni prvih ${needed} zajedno` : 'Pokreni sledeću grupu'}
                        </Btn>
                      </Card>
                    })}
                  </div>
                  <Card>
                    <Table
                      headers={['Korisnik', 'Kampanja', 'Email za pristup', 'Status', 'Akcija']}
                      rows={testerEnrollments.map(item => [
                        <span className="font-semibold text-ink">{item.user_name || 'Korisnik'}</span>,
                        <span className="text-xs text-ink-2">{item.task_title || 'Zadatak'}</span>,
                        <span className="font-mono text-xs select-all">{item.testing_email || '—'}</span>,
                        <StatusBadge status={item.status === 'requested' ? 'na_cekanju' : item.status === 'invited' ? 'aktivno' : 'odbijeno'} />,
                        item.status === 'requested'
                          ? <div className="flex items-center gap-2"><span className="text-xs text-ink-3">Čeka početak kohorte</span><Btn size="sm" variant="danger" onClick={() => void (async () => { try { await api.updateTesterEnrollment(item.id, 'declined', 'Trenutno nema slobodnih mesta u zatvorenom testiranju.'); await refreshDashboard(); showToast('Prijava je odbijena uz obaveštenje korisniku.', 'success') } catch (error) { showToast(error instanceof Error ? error.message : 'Status prijave nije ažuriran.', 'error') } })()}>Odbij</Btn></div>
                          : <span className="text-xs text-ink-3">{item.note || (item.status === 'invited' ? `Kohorta ${item.cohort_number || 'ranija'}, aktivna od ${item.invited_at ? new Intl.DateTimeFormat('sr-RS').format(new Date(item.invited_at)) : 'danas'}` : 'Obrađeno')}</span>,
                      ])}
                    />
                  </Card>
                </div>}
                {testerCheckins.length > 0 && <div className="mb-5">
                  <SectionHeader title="Dnevni izveštaji testera" description="Odobri samo stvarno pregledane dnevne izveštaje. Svako odobrenje prebacuje dnevnu nagradu korisniku u raspoloživi saldo." />
                  <Card>
                    <Table
                      headers={['Korisnik', 'Kampanja', 'Dan', 'Izveštaj', 'Nagrada', 'Status', 'Akcija']}
                      rows={testerCheckins.map(item => [
                        <span className="font-semibold text-ink">{item.user_name || 'Korisnik'}</span>,
                        <span className="text-xs text-ink-2">{item.task_title || 'Zadatak'}</span>,
                        <span className="font-mono font-bold">{item.day_number}</span>,
                        <span className="max-w-[260px] text-xs text-ink-2">{item.note}</span>,
                        <span className="font-mono text-emerald-600">{item.reward_rsd} RSD</span>,
                        <StatusBadge status={item.status === 'pending' ? 'na_proveri' : item.status === 'approved' ? 'odobreno' : 'odbijeno'} />,
                        item.status === 'pending'
                          ? <div className="flex gap-2"><Btn size="sm" variant="success" onClick={() => void (async () => { try { await api.reviewTesterCheckin(item.id, 'approved'); await refreshDashboard(); showToast('Dnevni izveštaj je odobren, a nagrada prebačena korisniku.', 'success') } catch (error) { showToast(error instanceof Error ? error.message : 'Dnevni izveštaj nije obrađen.', 'error') } })()}>Odobri dan</Btn><Btn size="sm" variant="danger" onClick={() => void (async () => { try { await api.reviewTesterCheckin(item.id, 'rejected', 'Izveštaj nema dovoljno detalja za ovaj dan.'); await refreshDashboard(); showToast('Dnevni izveštaj je odbijen.', 'success') } catch (error) { showToast(error instanceof Error ? error.message : 'Dnevni izveštaj nije obrađen.', 'error') } })()}>Odbij</Btn></div>
                          : <span className="text-xs text-ink-3">{item.review_note || 'Obrađeno'}</span>,
                      ])}
                    />
                  </Card>
                </div>}
                <Tabs
                  tabs={[{ id: 'svi', label: 'Svi' }, { id: 'na_proveri', label: 'Na proveri' }, { id: 'odobreno', label: 'Odobreno' }, { id: 'odbijeno', label: 'Odbijeno' }]}
                  active={proofsTab}
                  onChange={setProofsTab}
                />
                <Card>
                  <Table
                    headers={['Korisnik', 'Zadatak', 'Poslato', 'Status', 'Akcija']}
                    rows={proofs.filter(p => proofsTab === 'svi' || proofStatus(p.id, p.status) === proofsTab).map(p => {
                      const st = proofStatus(p.id, p.status)
                      return [
                        <span className="font-mono text-xs">{p.korisnik}</span>,
                        <span>{p.zadatak}</span>,
                        <span className="font-mono text-xs">{p.poslato}</span>,
                        <StatusBadge status={st} />,
                        st === 'na_proveri'
                          ? <div className="flex gap-2"><Btn size="sm" variant="success" onClick={() => void (async () => { try { await api.reviewAdvertiserSubmission(p.id, 'approved'); await refreshDashboard(); showToast('Dokaz je odobren, a nagrada prebačena korisniku.', 'success') } catch (error) { showToast(error instanceof Error ? error.message : 'Dokaz nije obrađen.', 'error') } })()}>Odobri</Btn><Btn size="sm" variant="danger" onClick={() => void (async () => { try { await api.reviewAdvertiserSubmission(p.id, 'rejected', 'Dokaz ne ispunjava zahteve kampanje.'); await refreshDashboard(); showToast('Dokaz je vraćen korisniku kao odbijen.', 'success') } catch (error) { showToast(error instanceof Error ? error.message : 'Dokaz nije obrađen.', 'error') } })()}>Odbij</Btn></div>
                          : <span className="text-xs text-ink-3">{p.submission.review_note || 'Obrađeno'}</span>,
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
                <SectionHeader title={platformPublishing ? 'Platformske objave' : 'Budžet i uplate'} description={platformPublishing ? 'Kao administrator objavljuješ kampanje, bannere i VIP pozicije bez PayPal naplate i bez rezervacije budžeta.' : undefined} />
                <div className="grid grid-cols-2 gap-3">
                  <StatCard label={platformPublishing ? 'Naknada za objave' : 'Raspoloživi budžet'} value={platformPublishing ? '0 RSD' : `${new Intl.NumberFormat('sr-RS').format(advertiser?.advertiser_budget_rsd ?? 0)} RSD`} accent="green" />
                  <StatCard label={platformPublishing ? 'Status objava' : 'Rezervisan'} value={platformPublishing ? 'Bez naplate' : `${new Intl.NumberFormat('sr-RS').format(advertiser?.advertiser_reserved_rsd ?? 0)} RSD`} accent="orange" />
                </div>
                {platformPublishing ? <Card className="p-5">
                  <h3 className="font-bold text-ink">Objavljivanje platforme je besplatno</h3>
                  <p className="mt-2 text-sm leading-6 text-ink-2">Kampanje, banneri, prioritetni prikaz i istaknute kampanje koje kreiraš kao administrator ne koriste PayPal niti saldo oglašivača.</p>
                  <div className="mt-4"><Alert type="warning">Kada odobriš dokaz korisnika na platformskoj kampanji, njegova nagrada postaje stvarna obaveza platforme za isplatu. Zato objavljuj samo zadatke za koje je nagrada stvarno planirana.</Alert></div>
                </Card> : <Card className="p-5">
                  <div className="flex items-start justify-between gap-4 mb-4">
                    <div>
                      <h3 className="font-bold text-ink">Uplati sredstva</h3>
                      <p className="text-xs text-ink-3 mt-1">Plati PayPal nalogom ili kreditnom/debitnom karticom preko PayPal Checkout-a.</p>
                    </div>
                    <span className="text-xs font-bold text-blue-700 bg-blue-50 border border-blue-100 rounded-full px-2.5 py-1">PayPal + kartice</span>
                  </div>
                  <Input label="Iznos uplate (RSD)" placeholder="npr. 5000" type="number" value={topupAmount} onChange={setTopupAmount} />
                  {topupError && <div className="mt-3"><Alert type="error">{topupError}</Alert></div>}
                  <p className="text-xs text-ink-3 mt-3">Na PayPal-u će iznos biti prikazan u EUR prema kursu koji je postavio administrator. Budžet se knjiži samo nakon PayPal potvrde.</p>
                  <div className="mt-4 grid gap-3 sm:grid-cols-2 sm:items-end">
                    <div>
                      <p className="text-xs font-bold text-ink mb-2">PayPal nalog</p>
                      <Btn disabled={topupLoading} onClick={() => void startPayPalTopup()}>{topupLoading ? 'Otvaranje PayPal-a...' : 'Nastavi na PayPal →'}</Btn>
                    </div>
                    <div className="rounded-xl border border-blue-100 bg-blue-50/60 px-3 py-2">
                      <p className="text-xs font-bold text-ink mb-1">Kreditna ili debitna kartica</p>
                      {Number(topupAmount.replace(',', '.')) >= 200
                        ? <PayPalCardCheckout
                            amountRsd={Number(topupAmount.replace(',', '.'))}
                            onCaptured={() => { showToast('Uplata karticom je potvrđena i budžet je dopunjen.', 'success'); void refreshDashboard() }}
                            onError={setTopupError}
                          />
                        : <p className="text-xs text-ink-3">Prvo unesi iznos od najmanje 200 RSD.</p>}
                    </div>
                  </div>
                  <p className="text-xs text-ink-3 mt-3">Karticu obrađuje PayPal. Prikaz kartične opcije zavisi od PayPal odobrenja, zemlje i provere kupca; KlikZarada ne prima niti čuva podatke kartice.</p>
                </Card>}
              </div>
            )}

            {page === 'fakture' && (
              <div>
                <SectionHeader title="Fakture" />
                <EmptyState icon="🧾" title="Nema faktura" description="Fakture se generišu automatski na kraju obračunskog perioda." />
              </div>
            )}

            {page === 'izvestaji' && (
              <div className="space-y-5">
                <SectionHeader title="Izveštaji" description="Pregled koristi stvarne kampanje, dokaze, zakup banera i potrošnju sa ovog naloga." />
                <div className="grid gap-3 sm:grid-cols-3">
                  <StatCard label="Ukupno kampanja" value={String(campaigns.length)} accent="blue" />
                  <StatCard label="Poslato dokaza" value={String(proofs.length)} accent="green" />
                  <StatCard label="Prikazi banera" value={String(ownBanners.reduce((total, banner) => total + banner.views_count, 0))} accent="teal" />
                </div>
                <Card>
                  <Table
                    headers={['Kampanja', 'Dokazi', 'Odobreno', 'Na proveri', 'Rezervisano', 'Status']}
                    rows={campaigns.length > 0 ? campaigns.map(campaign => [
                      <span className="font-semibold text-ink">{campaign.naziv}</span>,
                      <span className="font-mono">{campaign.dokazi}</span>,
                      <span className="font-mono text-emerald-700">{campaign.odobreno}</span>,
                      <span className="font-mono text-amber-700">{campaign.naProveri}</span>,
                      <span className="font-mono text-xs">{campaign.budžet}</span>,
                      <StatusBadge status={campaign.status} />,
                    ]) : [[<span className="text-sm text-ink-3">Još nema kampanja.</span>, '—', '—', '—', '—', '—']]}
                  />
                </Card>
                <Card>
                  <Table
                    headers={['Banner', 'Pozicija', 'Prikazi', 'Status']}
                    rows={ownBanners.length > 0 ? ownBanners.map(banner => [
                      <span className="font-semibold text-ink">{banner.title}</span>,
                      <span className="text-xs text-ink-2">{banner.slot_title}</span>,
                      <span className="font-mono">{banner.views_count}</span>,
                      <StatusBadge status={banner.status} />,
                    ]) : [[<span className="text-sm text-ink-3">Još nema zakupa banera.</span>, '—', '—', '—']]}
                  />
                </Card>
              </div>
            )}

            {page === 'banneri' && (
              <div className="space-y-5">
                <SectionHeader title="Banner reklame" description={platformPublishing ? 'Objavi banner platforme bez naplate. Sadržaj i dalje prolazi proveru pre prikaza na početnoj.' : 'Rezerviši poziciju na početnoj stranici. Svaki zakup prolazi proveru administratora pre objave.'} />
                <Card className="p-5">
                  <h2 className="font-bold text-ink">{platformPublishing ? 'Novi platformski banner' : 'Novi zakup'}</h2>
                  <p className="text-sm text-ink-3 mt-1">{platformPublishing ? 'Platformski banner ne koristi budžet niti PayPal. Objavljuje se posle moderacije.' : 'Iznos se samo rezerviše iz budžeta dok admin ne odobri sadržaj.'}</p>
                  <div className="grid sm:grid-cols-2 gap-3 mt-4">
                    <Select
                      label="Pozicija na početnoj"
                      value={bannerSlotId}
                      onChange={selectBannerSlot}
                      options={bannerSlots.map(slot => ({
                        value: String(slot.id),
                        label: `${slot.title} — ${platformPublishing ? '0 RSD za platformu' : `${new Intl.NumberFormat('sr-RS').format(slot.price_rsd)} RSD / 7 dana`}`,
                      }))}
                    />
                    <Input label="Trajanje u danima" type="number" min={1} max={bannerMaxDays} step={1} value={String(normalizedBannerDays)} onChange={value => setBannerDays(String(Math.min(bannerMaxDays, Math.max(1, Math.floor(Number(value) || 1))))) } />
                    <Input label="Željeni početak prikaza" type="date" min={calendarDate(new Date())} value={bannerStartDate} onChange={setBannerStartDate} />
                    <Input label="Naslov reklame" placeholder="npr. Jesenja ponuda" value={bannerTitle} onChange={setBannerTitle} />
                    <Input label="Link na koji vodi banner" placeholder="https://vas-sajt.rs/ponuda" value={bannerUrl} onChange={setBannerUrl} />
                    <Input label="URL slike banera (opciono)" placeholder="https://vas-sajt.rs/banner.jpg" value={bannerImageUrl} onChange={setBannerImageUrl} />
                  </div>
                  <div className="mt-3 rounded-lg border border-frame bg-mint-50 p-3">
                    <label className="text-xs font-semibold uppercase tracking-wide text-ink-2">Otpremi sliku bannera</label>
                    <input className="mt-2 block w-full text-sm text-ink-2" type="file" accept="image/jpeg,image/png,image/webp" disabled={bannerUploading} onChange={event => void uploadBanner(event.target.files?.[0])} />
                    <p className="mt-1 text-xs text-ink-3">JPG, PNG ili WEBP, najviše 5 MB, najmanje 200×80 px. {bannerUploading ? 'Slika se šalje...' : 'Možeš koristiti i spoljašnji URL.'}</p>
                  </div>
                  <div className="mt-3">
                    <Input label="Kratak opis (opciono)" placeholder="Jedna jasna poruka za posetioce" value={bannerBody} onChange={setBannerBody} />
                  </div>
                  {selectedBannerSlot && <div className="mt-4 rounded-xl border border-blue-100 bg-blue-50/60 p-3 text-sm text-ink-2">
                    <p><strong className="text-ink">{platformPublishing ? 'Naknada platforme:' : 'Cena rezervacije:'}</strong> {platformPublishing ? '0 RSD' : `${new Intl.NumberFormat('sr-RS').format(Math.round(selectedBannerPrice))} RSD za ${normalizedBannerDays} dana`}.</p>
                    <p className="mt-1 text-xs">Format: {selectedBannerSlot.width_label}. Termin rezervišeš odmah, a admin proverava kreativni sadržaj.</p>
                    <p className={`mt-2 text-xs font-semibold ${selectedBannerSlot.is_available_now ? 'text-emerald-700' : 'text-amber-700'}`}>
                      {selectedBannerSlot.is_available_now ? 'Pozicija je slobodna danas.' : `Pozicija je zauzeta. Prvi slobodan termin je ${displayDate(selectedBannerSlot.next_available_at)}.`}
                    </p>
                    {!selectedBannerSlot.is_available_now && <button type="button" onClick={() => setBannerStartDate(calendarDate(selectedBannerSlot.next_available_at))} className="mt-2 text-xs font-bold text-blue-700 hover:text-blue-800">Postavi prvi slobodan termin →</button>}
                    {selectedBannerSlot.schedule.length > 0 && <div className="mt-3 border-t border-blue-100 pt-3 text-xs text-ink-2"><p className="font-bold text-ink">Raspored pozicije</p><ul className="mt-1 space-y-1">{selectedBannerSlot.schedule.map(item => <li key={item.id}>{item.title}: {displayDate(item.starts_at)} – {displayDate(item.ends_at)} ({item.status.replace('_', ' ')})</li>)}</ul></div>}
                  </div>}
                  {bannerError && <div className="mt-3"><Alert type="error">{bannerError}</Alert></div>}
                  <div className="flex flex-wrap items-center gap-3 mt-4">
                    <Btn disabled={bannerLoading || bannerSlots.length === 0} onClick={() => void reserveBanner()}>{bannerLoading ? 'Slanje...' : platformPublishing ? 'Pošalji banner na moderaciju' : 'Rezerviši banner'}</Btn>
                    <span className="text-xs text-ink-3">Objava je moguća samo posle admin odobrenja.</span>
                  </div>
                </Card>
                <div>
                  <SectionHeader title="Moji zakupi" />
                  {ownBanners.length === 0
                    ? <EmptyState icon="🖼️" title={platformPublishing ? 'Još nemaš platformski banner' : 'Još nemaš zakupljen banner'} description={platformPublishing ? 'Izaberi slobodnu poziciju i pošalji platformsku objavu na proveru.' : 'Izaberi slobodnu poziciju i pošalji rezervaciju na proveru.'} />
                    : <Card>
                      <Table
                        headers={['Reklama', 'Pozicija', 'Trajanje', 'Prikazi', 'Iznos', 'Status', 'Napomena']}
                        rows={ownBanners.map(banner => [
                          <span className="font-semibold text-ink">{banner.title}</span>,
                          <span className="text-xs text-ink-2">{banner.slot_title}</span>,
                          <span>{banner.days_count} dana</span>,
                          <span className="font-mono text-xs">{banner.views_count}</span>,
                          <span className="font-mono text-xs">{platformPublishing ? '0 RSD' : `${new Intl.NumberFormat('sr-RS').format(banner.price_rsd)} RSD`}</span>,
                          <StatusBadge status={banner.status} />,
                          <span className="text-xs text-ink-3">{banner.admin_note || '—'}</span>,
                        ])}
                      />
                    </Card>}
                </div>
              </div>
            )}

            {page === 'premium' && (
              <div className="space-y-5">
                <SectionHeader title="Katalog oglašavanja" description="Objavljuj samo merljive zadatke i banere sa jasnom cenom. Nedozvoljeni su plaćeni klikovi, lažni pratioci i manipulacija ocenama." />
                <div className="grid gap-3 sm:grid-cols-2">
                  <Card className="border-blue-200 p-5">
                    <p className="text-xs font-bold uppercase tracking-wide text-blue-700">Proizvod 01</p>
                    <h3 className="mt-2 font-bold text-ink">Kampanja sa dokazom</h3>
                    <p className="mt-2 text-sm leading-6 text-ink-2">Anketa, testiranje sajta, provera podataka ili feedback. Nagrada se isplaćuje tek nakon odobrenog dokaza.</p>
                    <p className="mt-3 font-mono text-sm font-bold text-blue-700">{platformPublishing ? 'Platformska objava: 0 RSD naknada' : 'Konačan potreban budžet vidi se pre potvrde.'}</p>
                    <Btn size="sm" className="mt-4" onClick={() => goTo('nova')}>Kreiraj kampanju</Btn>
                  </Card>
                  <Card className="border-violet-200 p-5">
                    <p className="text-xs font-bold uppercase tracking-wide text-violet-700">Proizvod 02</p>
                    <h3 className="mt-2 font-bold text-ink">Zakup banner pozicije</h3>
                    <p className="mt-2 text-sm leading-6 text-ink-2">Pozicija na početnoj, izabran broj dana, URL odredišta i opciona slika. Admin odobrava sadržaj pre objave.</p>
                    <p className="mt-3 font-mono text-sm font-bold text-violet-700">{platformPublishing ? 'Platformska objava: 0 RSD' : `Od ${new Intl.NumberFormat('sr-RS').format(bannerSlots.length > 0 ? Math.min(...bannerSlots.map(slot => slot.price_rsd)) : 0)} RSD / 7 dana`}</p>
                    <Btn size="sm" variant="premium" className="mt-4" onClick={() => goTo('banneri')}>Pogledaj slotove</Btn>
                  </Card>
                </div>
                <Card className="border-violet-200 p-5">
                  <p className="text-xs font-bold uppercase tracking-wide text-violet-700">VIP promocija</p>
                  <h3 className="mt-2 font-bold text-ink">Istaknuta kampanja ili prioritetni prikaz</h3>
                  <p className="mt-2 text-sm leading-6 text-ink-2">{platformPublishing ? 'Promocija platforme važi 1–31 dan, bez rezervacije budžeta, i objavljuje se tek posle moderacije. Na listi zadataka uvek je vidljivo označena kao „Sponzorisano”.' : 'Promocija važi 1–31 dan, najpre rezerviše budžet i objavljuje se tek posle admin odobrenja. Na listi zadataka uvek je vidljivo označena kao „Sponzorisano”.'}</p>
                  <div className="mt-4 grid gap-3 sm:grid-cols-3">
                    <Select label="Aktivna kampanja" value={promotionTaskId} onChange={setPromotionTaskId} options={dashboard?.tasks.filter(task => task.status === 'aktivno' || task.status === 'active').map(task => ({ value: String(task.id), label: task.title })) ?? []} />
                    <Select label="Tip promocije" value={promotionType} onChange={value => setPromotionType(value as 'featured' | 'priority')} options={[{ value: 'featured', label: platformPublishing ? 'Istaknuta kampanja — 0 RSD za platformu' : 'Istaknuta kampanja — 1.200 RSD / 7 dana' }, { value: 'priority', label: platformPublishing ? 'Prioritetni prikaz — 0 RSD za platformu' : 'Prioritetni prikaz — 700 RSD / 7 dana' }]} />
                    <Input label="Trajanje u danima" type="number" min={1} max={31} step={1} value={promotionDays} onChange={value => setPromotionDays(String(Math.min(31, Math.max(1, Math.floor(Number(value) || 1)))))} />
                  </div>
                  {promotionError && <div className="mt-3"><Alert type="error">{promotionError}</Alert></div>}
                  <div className="mt-4 flex flex-wrap items-center gap-3">
                    <Btn variant="premium" disabled={promotionLoading || !promotionTaskId} onClick={() => void reservePromotion()}>{promotionLoading ? 'Slanje...' : platformPublishing ? 'Pošalji VIP na moderaciju' : 'Pošalji VIP rezervaciju'}</Btn>
                    <span className="text-xs text-ink-3">{platformPublishing ? 'Za administratora: 0 RSD. Trajanje je i dalje ograničeno na 1–31 dan.' : 'Istaknuta: 1.200 RSD / 7 dana. Prioritet: 700 RSD / 7 dana.'}</span>
                  </div>
                </Card>
                {promotions.length > 0 && <Card>
                  <Table headers={['Kampanja', 'Tip', 'Trajanje', 'Iznos', 'Status', 'Napomena']} rows={promotions.map(item => [
                    <span className="font-semibold text-ink">{item.task_title}</span>,
                    <span className="text-violet-700 text-xs font-semibold">{item.promotion_type === 'featured' ? 'Istaknuta' : 'Prioritetna'}</span>,
                    <span>{item.days_count} dana</span>,
                    <span className="font-mono text-xs">{platformPublishing ? '0 RSD' : `${new Intl.NumberFormat('sr-RS').format(item.price_rsd)} RSD`}</span>,
                    <StatusBadge status={item.status} />,
                    <span className="text-xs text-ink-3">{item.admin_note || '—'}</span>,
                  ])} />
                </Card>}
              </div>
            )}

            {page === 'profil' && (
              <div className="space-y-4">
                <SectionHeader title="Profil oglašivača" description="Kontakt podaci se čuvaju na nalogu i koriste za komunikaciju o kampanjama." />
                <Card className="p-5 space-y-4">
                  <Input label={advertiser?.company_name ? 'Kontakt osoba' : 'Ime i prezime'} placeholder="Ime i prezime" value={profileName} onChange={setProfileName} />
                  <Input label="Telefon" placeholder="+381 11 ..." value={profilePhone} onChange={setProfilePhone} />
                  <Input label="Grad" placeholder="npr. Beograd" value={profileCity} onChange={setProfileCity} />
                  <div className="border-t border-frame pt-4"><p className="text-sm font-bold text-ink">Podaci o oglašivaču</p><p className="mt-1 text-xs text-ink-3">Popuni samo podatke koje stvarno želiš da koristiš za račune i kontakt. Firma se ne smatra verifikovanom samo unosom ovih podataka.</p></div>
                  <Input label="Naziv firme ili preduzetnika" placeholder="npr. KlikZarada d.o.o." value={companyName} onChange={setCompanyName} />
                  <Input label="PIB / poreski identifikator" placeholder="Opciono" value={companyPib} onChange={setCompanyPib} />
                  <Input label="Sajt firme" placeholder="https://primer.rs" value={companyWebsite} onChange={setCompanyWebsite} />
                  <Input label="Delatnost" placeholder="npr. internet oglašavanje" value={companyActivity} onChange={setCompanyActivity} />
                  <div className="flex gap-2">
                    <Btn variant="success" disabled={profileSaving || profileName.trim().length < 2} onClick={() => void (async () => { try { setProfileSaving(true); await api.saveProfile({ full_name: profileName.trim(), phone: profilePhone.trim() || undefined, city: profileCity.trim() || undefined, company_name: companyName.trim() || undefined, company_pib: companyPib.trim() || undefined, company_website: companyWebsite.trim() || undefined, company_activity: companyActivity.trim() || undefined }); await refreshDashboard(); showToast('Profil oglašivača je sačuvan.', 'success') } catch (error) { showToast(error instanceof Error ? error.message : 'Profil nije sačuvan.', 'error') } finally { setProfileSaving(false) } })()}>{profileSaving ? 'Čuvanje...' : 'Sačuvaj izmene'}</Btn>
                    <Btn variant="secondary" onClick={() => { setProfileName(advertiser?.full_name || ''); setProfilePhone(advertiser?.phone || ''); setProfileCity(advertiser?.city || ''); setCompanyName(advertiser?.company_name || ''); setCompanyPib(advertiser?.company_pib || ''); setCompanyWebsite(advertiser?.company_website || ''); setCompanyActivity(advertiser?.company_activity || '') }}>Otkaži</Btn>
                  </div>
                </Card>
                <Card className="p-5 space-y-3">
                  <h3 className="font-bold text-ink">Bezbednost naloga</h3>
                  <input type="password" value={currentPassword} onChange={event => setCurrentPassword(event.target.value)} placeholder="Trenutna lozinka" className="w-full bg-white border border-frame text-ink rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
                  <input type="password" value={newPassword} onChange={event => setNewPassword(event.target.value)} placeholder="Nova lozinka, najmanje 8 znakova" className="w-full bg-white border border-frame text-ink rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
                  <input type="password" value={repeatPassword} onChange={event => setRepeatPassword(event.target.value)} placeholder="Ponovi novu lozinku" className="w-full bg-white border border-frame text-ink rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none" />
                  <Btn variant="secondary" size="sm" disabled={profileSaving || newPassword.length < 8 || newPassword !== repeatPassword} onClick={() => void (async () => { try { setProfileSaving(true); await api.changePassword({ current_password: currentPassword, new_password: newPassword }); setCurrentPassword(''); setNewPassword(''); setRepeatPassword(''); showToast('Lozinka je promenjena.', 'success') } catch (error) { showToast(error instanceof Error ? error.message : 'Lozinka nije promenjena.', 'error') } finally { setProfileSaving(false) } })()}>Promeni lozinku</Btn>
                </Card>
              </div>
            )}

            {page === 'podrska' && (
              <div className="space-y-4">
                <SectionHeader title="Podrška za oglašivače" description="Pošalji zahtev, a odgovor administratora ostaje sačuvan u istoj prepisci." />
                <Card className="p-5 space-y-3">
                  <Input label="Naslov zahteva" placeholder="npr. Pitanje o kampanji" value={ticketSubject} onChange={setTicketSubject} />
                  <div className="flex flex-col gap-1.5"><label className="text-xs font-semibold uppercase tracking-wide text-ink-2">Poruka</label><textarea className="min-h-28 rounded-lg border border-frame bg-white px-3 py-2 text-sm text-ink focus:border-blue-500 focus:ring-2 focus:ring-blue-100 focus:outline-none" value={ticketBody} onChange={event => setTicketBody(event.target.value)} placeholder="Opiši pitanje ili problem što preciznije." /></div>
                  <Btn disabled={ticketLoading} onClick={() => void createTicket()}>{ticketLoading ? 'Slanje...' : 'Pošalji tiket'}</Btn>
                </Card>
                {tickets.length === 0 ? <EmptyState icon="🎫" title="Nema tiketa" description="Kada pošalješ zahtev, ovde ćeš videti celu prepisku." /> : tickets.map(ticket => <Card key={ticket.id} className="p-5"><div className="flex items-start justify-between gap-3"><div><p className="font-bold text-ink">#{ticket.id} · {ticket.subject}</p><p className="text-xs text-ink-3 mt-1">{ticket.category}</p></div><StatusBadge status={ticket.status === 'closed' ? 'obustavljeno' : ticket.status === 'waiting' ? 'na_cekanju' : 'aktivno'} /></div><div className="mt-4 space-y-2">{ticket.messages.map(message => <div key={message.id} className={`rounded-lg p-3 text-sm ${message.from_support ? 'bg-blue-50 text-blue-900' : 'bg-mint-50 text-ink'}`}><p className="text-xs font-semibold">{message.from_support ? 'Podrška' : 'Ti'} · {message.created_at ? new Date(message.created_at).toLocaleString('sr-RS') : ''}</p><p className="mt-1 whitespace-pre-wrap">{message.body}</p></div>)}</div><Btn size="sm" variant="secondary" className="mt-4" onClick={() => { const body = window.prompt('Odgovor podršci:'); if (!body?.trim()) return; void (async () => { try { await api.replyToTicket(ticket.id, body.trim()); await refreshDashboard(); showToast('Odgovor je poslat.', 'success') } catch (error) { showToast(error instanceof Error ? error.message : 'Odgovor nije poslat.', 'error') } })() }}>Odgovori</Btn></Card>)}
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}
