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

function NovaCampanja({ onCancel, onSuccess, onCreate, onRevise, feePercent, categories, campaign }: { onCancel: () => void; onSuccess: () => void; onCreate: (payload: Parameters<typeof api.createCampaign>[0]) => Promise<void>; onRevise: (id: number, payload: Parameters<typeof api.createCampaign>[0]) => Promise<void>; feePercent: number; categories: string[]; campaign?: import('../lib/api').Task }) {
  const [step, setStep] = useState(1)
  const [naziv, setNaziv] = useState(campaign?.title ?? '')
  const [reward, setReward] = useState(campaign ? String(campaign.reward_rsd) : '')
  const [budget, setBudget] = useState(campaign ? String(Math.ceil(campaign.reward_rsd * campaign.total_slots * (1 + feePercent / 100))) : '')
  const [description, setDescription] = useState(campaign?.description ?? '')
  const [taskUrl, setTaskUrl] = useState(campaign?.target_url ?? '')
  const [category, setCategory] = useState(campaign?.category ?? '')
  const [proofRequired, setProofRequired] = useState(campaign?.proof_required ?? 'screenshot')
  const [targetCity, setTargetCity] = useState(campaign?.target_city ?? 'Srbija')
  const [targetAgeGroup, setTargetAgeGroup] = useState(campaign?.target_age_group ?? '18+')
  const [targetInterests, setTargetInterests] = useState(campaign?.target_interests ?? '')
  const [taskDetails, setTaskDetails] = useState<Record<string, string>>({})
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const steps = ['Definicija', 'Nagrada i budžet', 'Publika i dokaz', 'Pregled']
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
            <h3 className="font-bold text-ink">Nagrada i budžet</h3>
            <Input label="Nagrada po zadatku (RSD)" placeholder="npr. 80" value={reward} onChange={setReward} />
            <Input label="Ukupni budžet (RSD)" placeholder="npr. 5000" value={budget} onChange={setBudget} />
            <Select label="Trajanje" options={[{ value: '7', label: '7 dana' }, { value: '14', label: '14 dana' }, { value: '30', label: '30 dana' }]} />
            {reward && budget && (
              <Alert type="info">Procenjeno: <strong className="font-mono">{Math.floor(Number(budget) / (Number(reward) * (1 + feePercent / 100)))}</strong> izvršenih zadataka, uključujući platformsku naknadu od {feePercent}%.</Alert>
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
                <div><span className="text-ink-2">Precizni detalji</span><ul className="mt-1 list-disc space-y-1 pl-4 text-xs text-ink">{detailLines.map(line => <li key={line}>{line}</li>)}</ul></div>
                <div className="flex justify-between"><span className="text-ink-2">Nagrada</span><span className="font-mono font-bold text-emerald-600">{reward} RSD</span></div>
                <div className="flex justify-between"><span className="text-ink-2">Budžet</span><span className="font-mono font-bold text-blue-600">{budget} RSD</span></div>
            </div>
            {error && <Alert type="error">{error}</Alert>}
            <Alert type="warning">Kampanja ide na moderaciju pre aktivacije. Budžet se rezerviše tek kada zahtev prođe proveru dostupnih sredstava.</Alert>
            <div className="flex gap-2">
              <Btn onClick={() => setStep(3)} variant="secondary">← Izmeni prethodni korak</Btn>
              <Btn disabled={submitting} onClick={async () => {
                const rewardRsd = Number(reward)
                const totalSlots = Math.floor(Number(budget) / (rewardRsd * (1 + feePercent / 100)))
                if (!Number.isFinite(rewardRsd) || rewardRsd <= 0 || totalSlots < 1) {
                  setError('Unesi validnu nagradu i budžet dovoljan za najmanje jedan zadatak.')
                  return
                }
                setSubmitting(true)
                setError('')
                try {
                  const fullDescription = `${description.trim()}\n\nSpecifikacija zadatka:\n${detailLines.map(line => `- ${line}`).join('\n')}`
                  const payload = { title: naziv, category, task_type: category, target_url: taskUrl || undefined, description: fullDescription, instructions: `Korisnik treba da prati specifikaciju zadatka i dostavi samo traženi dokaz.\n${detailLines.map(line => `- ${line}`).join('\n')}`, proof_required: proofRequired, reward_rsd: rewardRsd, total_slots: totalSlots, target_city: targetCity || undefined, target_age_group: targetAgeGroup, target_interests: targetInterests || undefined }
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
  const [bannerError, setBannerError] = useState('')
  const [bannerLoading, setBannerLoading] = useState(false)
  const [bannerUploading, setBannerUploading] = useState(false)
  const [profileName, setProfileName] = useState('')
  const [profilePhone, setProfilePhone] = useState('')
  const [profileCity, setProfileCity] = useState('')
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
    if (!bannerSlotId || !bannerTitle.trim() || !bannerUrl.trim() || !Number.isInteger(daysCount) || daysCount < 1 || daysCount > 31) {
      setBannerError('Izaberi slot, unesi naslov i link, pa trajanje od 1 do 31 dana.')
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
      })
      setBannerTitle('')
      setBannerBody('')
      setBannerImageUrl('')
      setBannerUrl('')
      await refreshDashboard()
      showToast(`Zakup je rezervisan: ${new Intl.NumberFormat('sr-RS').format(result.reserved_rsd)} RSD. Čeka odobrenje admina.`, 'success')
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
      showToast(`Promocija je rezervisana: ${new Intl.NumberFormat('sr-RS').format(result.reserved_rsd)} RSD. Čeka odobrenje admina.`, 'success')
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
  const feePercent = pricing?.platform_fee_percent ?? 20
  const feeMultiplier = 1 + feePercent / 100
  const selectedBannerSlot = bannerSlots.find(slot => slot.id === Number(bannerSlotId))
  const bannerMaxDays = pricing?.banner_max_days ?? 31
  const normalizedBannerDays = Math.min(bannerMaxDays, Math.max(1, Math.floor(Number(bannerDays) || 1)))
  const selectedBannerPrice = selectedBannerSlot
    ? selectedBannerSlot.price_rsd * normalizedBannerDays / (pricing?.banner_price_basis_days ?? 7)
    : 0
  const campaigns = (dashboard?.tasks ?? []).map(task => ({
    task,
    naziv: task.title,
    budžet: `${new Intl.NumberFormat('sr-RS').format(task.reward_rsd * task.total_slots * feeMultiplier)} RSD`,
    potrošeno: `${new Intl.NumberFormat('sr-RS').format(task.reward_rsd * task.used_slots * feeMultiplier)} RSD`,
    dokazi: task.used_slots,
    status: task.status === 'active' ? 'aktivno' : task.status === 'pending' ? 'na_cekanju' : task.status === 'paused' ? 'obustavljeno' : task.status === 'rejected' ? 'odbijeno' : task.status === 'needs_revision' ? 'dorada' : task.status,
  }))
  const proofs = (dashboard?.submissions ?? []).map(submission => ({
    submission,
    id: submission.id,
    korisnik: submission.user_name || 'Korisnik',
    zadatak: submission.task_title,
    poslato: submission.created_at ? new Intl.DateTimeFormat('sr-RS').format(new Date(submission.created_at)) : '—',
    status: submission.status === 'pending' ? 'na_proveri' : submission.status === 'approved' ? 'odobreno' : submission.status === 'rejected' ? 'odbijeno' : submission.status,
  }))

  function goTo(p: Page) { setPage(p) }
  const back = BACK[page]
  const crumbs = CRUMBS[page]

  const sidebarFooter = (
    <div className="flex items-center gap-2.5">
      <div className="w-8 h-8 rounded-full bg-violet-600 flex items-center justify-center text-white text-sm font-bold">{advertiser?.full_name?.slice(0, 1).toUpperCase() || 'O'}</div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-white truncate">{advertiser?.company_name || advertiser?.full_name || 'Učitavanje...'}</p>
        <p className="text-xs" style={{ color: '#9AB1C8' }}>Oglašivač</p>
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
                      <span className="text-xs text-ink-3">Admin pregled</span>,
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
                categories={pricing?.task_categories ?? []}
                campaign={campaignToRevise ?? undefined}
              />
            )}

            {page === 'kampanje' && (
              <div>
                <SectionHeader title="Moje kampanje" action={<Btn onClick={() => { setCampaignToRevise(null); goTo('nova') }} size="sm">+ Nova kampanja</Btn>} />
                <Card>
                  <Table
                    headers={['Naziv', 'Budžet', 'Potrošeno', 'Dokazi', 'Status', 'Akcija']}
                    rows={campaigns.map(c => [
                      <span className="font-semibold text-ink">{c.naziv}</span>,
                      <span className="font-mono">{c.budžet}</span>,
                      <span className="font-mono text-amber-700">{c.potrošeno}</span>,
                      <span className="font-mono">{c.dokazi}</span>,
                      <StatusBadge status={c.status} />,
                      c.task.status === 'needs_revision'
                        ? <Btn size="sm" variant="secondary" onClick={() => { setCampaignToRevise(c.task); goTo('nova') }}>Doradi</Btn>
                        : <span className="text-xs text-ink-3">{c.task.moderation_note || '—'}</span>,
                    ])}
                  />
                </Card>
              </div>
            )}

            {page === 'dokazi' && (
              <div>
                <SectionHeader title="Dokazi korisnika" description="Ti odlučuješ o rezultatu svoje kampanje. Admin interveniše samo kod spora ili anti-fraud provere." />
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
                <SectionHeader title="Budžet i uplate" />
                <div className="grid grid-cols-2 gap-3">
                  <StatCard label="Raspoloživi budžet" value={`${new Intl.NumberFormat('sr-RS').format(advertiser?.advertiser_budget_rsd ?? 0)} RSD`} accent="green" />
                  <StatCard label="Rezervisan" value={`${new Intl.NumberFormat('sr-RS').format(advertiser?.advertiser_reserved_rsd ?? 0)} RSD`} accent="orange" />
                </div>
                <Card className="p-5">
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
              <div className="space-y-5">
                <SectionHeader title="Izveštaji" description="Pregled koristi stvarne kampanje, dokaze, zakup banera i potrošnju sa ovog naloga." />
                <div className="grid gap-3 sm:grid-cols-3">
                  <StatCard label="Ukupno kampanja" value={String(campaigns.length)} accent="blue" />
                  <StatCard label="Poslato dokaza" value={String(proofs.length)} accent="green" />
                  <StatCard label="Prikazi banera" value={String(ownBanners.reduce((total, banner) => total + banner.views_count, 0))} accent="teal" />
                </div>
                <Card>
                  <Table
                    headers={['Kampanja', 'Dokazi', 'Rezervisano', 'Status']}
                    rows={campaigns.length > 0 ? campaigns.map(campaign => [
                      <span className="font-semibold text-ink">{campaign.naziv}</span>,
                      <span className="font-mono">{campaign.dokazi}</span>,
                      <span className="font-mono text-xs">{campaign.budžet}</span>,
                      <StatusBadge status={campaign.status} />,
                    ]) : [[<span className="text-sm text-ink-3">Još nema kampanja.</span>, '—', '—', '—']]}
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
                <SectionHeader title="Banner reklame" description="Rezerviši poziciju na početnoj stranici. Svaki zakup prolazi proveru administratora pre objave." />
                <Card className="p-5">
                  <h2 className="font-bold text-ink">Novi zakup</h2>
                  <p className="text-sm text-ink-3 mt-1">Iznos se samo rezerviše iz budžeta dok admin ne odobri sadržaj.</p>
                  <div className="grid sm:grid-cols-2 gap-3 mt-4">
                    <Select
                      label="Pozicija na početnoj"
                      value={bannerSlotId}
                      onChange={setBannerSlotId}
                      options={bannerSlots.map(slot => ({
                        value: String(slot.id),
                        label: `${slot.title} — ${new Intl.NumberFormat('sr-RS').format(slot.price_rsd)} RSD / 7 dana`,
                      }))}
                    />
                    <Input label="Trajanje u danima" type="number" min={1} max={bannerMaxDays} step={1} value={String(normalizedBannerDays)} onChange={value => setBannerDays(String(Math.min(bannerMaxDays, Math.max(1, Math.floor(Number(value) || 1))))) } />
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
                    <p><strong className="text-ink">Cena rezervacije:</strong> {new Intl.NumberFormat('sr-RS').format(Math.round(selectedBannerPrice))} RSD za {normalizedBannerDays} dana.</p>
                    <p className="mt-1 text-xs">Format: {selectedBannerSlot.width_label}. Zauzeti termini se prikazuju pre rezervacije i admin proverava kreativni sadržaj.</p>
                    {selectedBannerSlot.schedule.length > 0 && <p className="mt-1 text-xs text-amber-700">Postojeće rezervacije: {selectedBannerSlot.schedule.map(item => item.title).join(', ')}.</p>}
                  </div>}
                  {bannerError && <div className="mt-3"><Alert type="error">{bannerError}</Alert></div>}
                  <div className="flex flex-wrap items-center gap-3 mt-4">
                    <Btn disabled={bannerLoading || bannerSlots.length === 0} onClick={() => void reserveBanner()}>{bannerLoading ? 'Rezervacija...' : 'Rezerviši banner'}</Btn>
                    <span className="text-xs text-ink-3">Objava je moguća samo posle admin odobrenja.</span>
                  </div>
                </Card>
                <div>
                  <SectionHeader title="Moji zakupi" />
                  {ownBanners.length === 0
                    ? <EmptyState icon="🖼️" title="Još nemaš zakupljen banner" description="Izaberi slobodnu poziciju i pošalji rezervaciju na proveru." />
                    : <Card>
                      <Table
                        headers={['Reklama', 'Pozicija', 'Trajanje', 'Prikazi', 'Iznos', 'Status', 'Napomena']}
                        rows={ownBanners.map(banner => [
                          <span className="font-semibold text-ink">{banner.title}</span>,
                          <span className="text-xs text-ink-2">{banner.slot_title}</span>,
                          <span>{banner.days_count} dana</span>,
                          <span className="font-mono text-xs">{banner.views_count}</span>,
                          <span className="font-mono text-xs">{new Intl.NumberFormat('sr-RS').format(banner.price_rsd)} RSD</span>,
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
                    <p className="mt-3 font-mono text-sm font-bold text-blue-700">Naknada: {feePercent}% na nagrade</p>
                    <Btn size="sm" className="mt-4" onClick={() => goTo('nova')}>Kreiraj kampanju</Btn>
                  </Card>
                  <Card className="border-violet-200 p-5">
                    <p className="text-xs font-bold uppercase tracking-wide text-violet-700">Proizvod 02</p>
                    <h3 className="mt-2 font-bold text-ink">Zakup banner pozicije</h3>
                    <p className="mt-2 text-sm leading-6 text-ink-2">Pozicija na početnoj, izabran broj dana, URL odredišta i opciona slika. Admin odobrava sadržaj pre objave.</p>
                    <p className="mt-3 font-mono text-sm font-bold text-violet-700">Od {new Intl.NumberFormat('sr-RS').format(bannerSlots.length > 0 ? Math.min(...bannerSlots.map(slot => slot.price_rsd)) : 0)} RSD / 7 dana</p>
                    <Btn size="sm" variant="premium" className="mt-4" onClick={() => goTo('banneri')}>Pogledaj slotove</Btn>
                  </Card>
                </div>
                <Card className="border-violet-200 p-5">
                  <p className="text-xs font-bold uppercase tracking-wide text-violet-700">VIP promocija</p>
                  <h3 className="mt-2 font-bold text-ink">Istaknuta kampanja ili prioritetni prikaz</h3>
                  <p className="mt-2 text-sm leading-6 text-ink-2">Promocija važi 1–31 dan, najpre rezerviše budžet i objavljuje se tek posle admin odobrenja. Na listi zadataka uvek je vidljivo označena kao „Sponzorisano”.</p>
                  <div className="mt-4 grid gap-3 sm:grid-cols-3">
                    <Select label="Aktivna kampanja" value={promotionTaskId} onChange={setPromotionTaskId} options={dashboard?.tasks.filter(task => task.status === 'aktivno' || task.status === 'active').map(task => ({ value: String(task.id), label: task.title })) ?? []} />
                    <Select label="Tip promocije" value={promotionType} onChange={value => setPromotionType(value as 'featured' | 'priority')} options={[{ value: 'featured', label: 'Istaknuta kampanja — 1.200 RSD / 7 dana' }, { value: 'priority', label: 'Prioritetni prikaz — 700 RSD / 7 dana' }]} />
                    <Input label="Trajanje u danima" type="number" min={1} max={31} step={1} value={promotionDays} onChange={value => setPromotionDays(String(Math.min(31, Math.max(1, Math.floor(Number(value) || 1)))))} />
                  </div>
                  {promotionError && <div className="mt-3"><Alert type="error">{promotionError}</Alert></div>}
                  <div className="mt-4 flex flex-wrap items-center gap-3">
                    <Btn variant="premium" disabled={promotionLoading || !promotionTaskId} onClick={() => void reservePromotion()}>{promotionLoading ? 'Rezervacija...' : 'Pošalji VIP rezervaciju'}</Btn>
                    <span className="text-xs text-ink-3">Istaknuta: 1.200 RSD / 7 dana. Prioritet: 700 RSD / 7 dana.</span>
                  </div>
                </Card>
                {promotions.length > 0 && <Card>
                  <Table headers={['Kampanja', 'Tip', 'Trajanje', 'Iznos', 'Status', 'Napomena']} rows={promotions.map(item => [
                    <span className="font-semibold text-ink">{item.task_title}</span>,
                    <span className="text-violet-700 text-xs font-semibold">{item.promotion_type === 'featured' ? 'Istaknuta' : 'Prioritetna'}</span>,
                    <span>{item.days_count} dana</span>,
                    <span className="font-mono text-xs">{new Intl.NumberFormat('sr-RS').format(item.price_rsd)} RSD</span>,
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
                  <div className="flex gap-2">
                    <Btn variant="success" disabled={profileSaving || profileName.trim().length < 2} onClick={() => void (async () => { try { setProfileSaving(true); await api.saveProfile({ full_name: profileName.trim(), phone: profilePhone.trim() || undefined, city: profileCity.trim() || undefined }); await refreshDashboard(); showToast('Profil oglašivača je sačuvan.', 'success') } catch (error) { showToast(error instanceof Error ? error.message : 'Profil nije sačuvan.', 'error') } finally { setProfileSaving(false) } })()}>{profileSaving ? 'Čuvanje...' : 'Sačuvaj izmene'}</Btn>
                    <Btn variant="secondary" onClick={() => { setProfileName(advertiser?.full_name || ''); setProfilePhone(advertiser?.phone || ''); setProfileCity('') }}>Otkaži</Btn>
                  </div>
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
                {tickets.length === 0 ? <EmptyState icon="🎫" title="Nema tiketa" description="Kada pošalješ zahtev, ovde ćeš videti celu prepisku." /> : tickets.map(ticket => <Card key={ticket.id} className="p-5"><div className="flex items-start justify-between gap-3"><div><p className="font-bold text-ink">#{ticket.id} · {ticket.subject}</p><p className="text-xs text-ink-3 mt-1">{ticket.category}</p></div><StatusBadge status={ticket.status === 'closed' ? 'obustavljeno' : ticket.status === 'waiting' ? 'na_cekanju' : 'aktivno'} /></div><div className="mt-4 space-y-2">{ticket.messages.map(message => <div key={message.id} className={`rounded-lg p-3 text-sm ${message.from_support ? 'bg-blue-50 text-blue-900' : 'bg-mint-50 text-ink'}`}><p className="text-xs font-semibold">{message.from_support ? 'Podrška' : 'Ti'} · {message.created_at ? new Date(message.created_at).toLocaleString('sr-RS') : ''}</p><p className="mt-1 whitespace-pre-wrap">{message.body}</p></div>)}</div></Card>)}
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}
