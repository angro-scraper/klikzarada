import { useEffect, useRef, useState } from 'react'
import { Sidebar, TopBar } from '../components/Sidebar'
import { Btn, Card, StatCard, SectionHeader, EmptyState, Table, StatusBadge, Tabs, Alert, Input, Select } from '../components/ui'
import { PageHeader } from '../components/PageHeader'
import { ConfirmModal } from '../components/Modal'
import { TaskChat } from '../components/TaskChat'
import { useToast } from '../components/Toast'
import { api, type AdvertiserDashboardData, type BannerSlot, type ContentRevision, type NotificationItem, type PaidBanner, type PaidPromotion, type SupportTicket, type TaskChatInboxItem } from '../lib/api'

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

function firstBookableBannerDate(now = new Date()): string {
  const start = new Date(now)
  start.setHours(12, 0, 0, 0)
  if (start <= now) start.setDate(start.getDate() + 1)
  return calendarDate(start)
}

function displayDate(value: string | null | undefined): string {
  if (!value) return 'nije određen'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? 'nije određen' : new Intl.DateTimeFormat('sr-RS', { dateStyle: 'medium' }).format(date)
}

function bannerDate(value: string | null): Date | null {
  if (!value) return null
  const date = new Date(/[zZ]|[+-]\d\d:\d\d$/.test(value) ? value : `${value}Z`)
  return Number.isNaN(date.getTime()) ? null : date
}

function bannerVisibility(banner: PaidBanner): { label: string; className: string; detail: string } {
  if (!['aktivno', 'active'].includes(banner.status)) {
    return { label: banner.status === 'na_cekanju' ? 'Na proveri' : banner.status === 'odbijeno' ? 'Odbijeno' : 'Obustavljeno', className: 'bg-slate-100 text-slate-700', detail: 'Baner nije javno prikazan.' }
  }
  const start = bannerDate(banner.starts_at)
  const end = bannerDate(banner.ends_at)
  if (start && start > new Date()) return { label: 'Zakazano', className: 'bg-amber-100 text-amber-800', detail: 'Odobren je, ali još nije počeo javni prikaz.' }
  if (end && end <= new Date()) return { label: 'Završeno', className: 'bg-slate-100 text-slate-700', detail: 'Period prikazivanja je istekao.' }
  return { label: 'Prikazuje se', className: 'bg-emerald-100 text-emerald-800', detail: 'Baner je trenutno dostupan posetiocima početne stranice.' }
}

function bannerDateTime(value: string | null): string {
  const date = bannerDate(value)
  return date ? new Intl.DateTimeFormat('sr-RS', { dateStyle: 'medium', timeStyle: 'short' }).format(date) : 'Nije određen'
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
    { id: 'poruke', label: 'Poruke', icon: '💬' },
    { id: 'obavestenja', label: 'Obaveštenja', icon: '🔔' },
    { id: 'dokazi', label: 'Dokazi korisnika', icon: '📎' },
    { id: 'testeri', label: 'Prijavljeni testeri', icon: '🧪' },
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

type Page = 'pregled'|'nova'|'kampanje'|'poruke'|'obavestenja'|'dokazi'|'testeri'|'analitika'|'budzet'|'fakture'|'izvestaji'|'banneri'|'premium'|'profil'|'podrska'

const BACK: Partial<Record<Page, { label: string; to: Page }>> = {
  nova:      { label: 'Nazad na pregled', to: 'pregled' },
  kampanje:  { label: 'Nazad na pregled', to: 'pregled' },
  poruke:    { label: 'Nazad na pregled', to: 'pregled' },
  obavestenja: { label: 'Nazad na pregled', to: 'pregled' },
  dokazi:    { label: 'Nazad na pregled', to: 'pregled' },
  testeri:   { label: 'Nazad na pregled', to: 'pregled' },
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
  poruke:    [{ label: 'Oglašivač' }, { label: 'Poruke' }],
  obavestenja: [{ label: 'Oglašivač' }, { label: 'Obaveštenja' }],
  dokazi:    [{ label: 'Oglašivač' }, { label: 'Dokazi korisnika' }],
  testeri:   [{ label: 'Oglašivač' }, { label: 'Prijavljeni testeri' }],
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
type CampaignTemplate = {
  id: string
  label: string
  category: string
  taskType: string
  subjectLabel: string
  subjectPlaceholder: string
  title: (subject: string) => string
  description: string
  instructionLead: string
  proof: string
  requiresTesterEnrollment?: boolean
  fields: TaskDetailField[]
}

// Templates define the actual work and evidence for a campaign. They prevent
// unrelated campaigns from being published with the same vague instructions.
const CAMPAIGN_TEMPLATES: CampaignTemplate[] = [
  { id: 'survey', label: 'Anketa korisnika', category: 'Ankete i testiranja', taskType: 'Anketa korisnika', subjectLabel: 'Naziv proizvoda, usluge ili teme', subjectPlaceholder: 'npr. aplikacija za dostavu hrane', title: subject => `Anketa korisnika: ${subject || 'nova tema'}`, description: 'Prikupi strukturirano mišljenje od jasno definisane publike pre poslovne odluke.', instructionLead: 'Popuni sva navedena pitanja iskreno i bez deljenja ličnih podataka. Odgovaraj samo ako pripadaš traženoj publici.', proof: 'Odgovori na sva pitanja u predviđenom formatu', fields: [
    { key: 'audience', label: 'Ko treba da odgovara', placeholder: 'npr. osobe koje kupuju online najmanje jednom mesečno' },
    { key: 'questions', label: 'Pitanja i odgovori', placeholder: 'Navedi pitanja redom i minimalnu dužinu otvorenog odgovora.' },
    { key: 'completion', label: 'Kriterijum završetka', placeholder: 'npr. odgovoriti na svih 8 pitanja bez ličnih podataka' },
  ] },
  { id: 'website-ux', label: 'UX test sajta', category: 'Testiranje sajta ili aplikacije', taskType: 'UX test sajta', subjectLabel: 'Naziv sajta ili proizvoda', subjectPlaceholder: 'npr. web prodavnica Moj Brend', title: subject => `UX test sajta: ${subject || 'novi sajt'}`, description: 'Proveri da li korisnik može bez pomoći da završi ključan tok na sajtu.', instructionLead: 'Otvori zadati link na navedenom uređaju, prođi kroz sve scenarije redom i prijavi samo stvarno uočene prepreke.', proof: 'Kratak izveštaj sa koracima + screenshot greške ako postoji', fields: [
    { key: 'device', label: 'Uređaj i pregledač', placeholder: 'npr. Android telefon, Chrome; ili desktop, Firefox' },
    { key: 'scenarios', label: 'Scenariji testiranja', placeholder: '1. Pronađi proizvod. 2. Dodaj u korpu. 3. Opiši gde je nastao problem.' },
    { key: 'report', label: 'Format izveštaja', placeholder: 'Očekivano/stvarno ponašanje, koraci i screenshot ako postoji greška.' },
  ] },
  { id: 'closed-beta', label: 'Zatvoreni beta test aplikacije', category: 'Testiranje sajta ili aplikacije', taskType: 'Zatvoreni beta test aplikacije', subjectLabel: 'Naziv aplikacije', subjectPlaceholder: 'npr. Stock Radar', title: subject => `${subject || 'Nova aplikacija'}: zatvoreno beta testiranje`, description: 'Okupi testere za zatvoreni beta kanal i prikupi iskrene dnevne izveštaje tokom testiranja.', instructionLead: 'Najpre pošalji email na koji želiš da primiš poziv za testiranje. Nakon ručnog dodavanja u tester listu, koristi aplikaciju svakog dana po zadatom planu i pošalji istinit dnevni izveštaj.', proof: 'Dnevni izveštaj o korišćenju; screenshot samo kada prijavljuješ grešku', requiresTesterEnrollment: true, fields: [
    { key: 'store', label: 'Aplikacija ili pristupni link', placeholder: 'Nalepi App Store, Play Store ili interni link za testere.' },
    { key: 'device', label: 'Uređaj za testiranje', placeholder: 'npr. iPhone ili Android telefon; navedi posebne uslove ako postoje.' },
    { key: 'daily_scenarios', label: 'Šta tester radi svakog dana', placeholder: 'npr. otvori listu akcija, pretraži akciju, sačuvaj je i proveri obaveštenje.' },
    { key: 'report', label: 'Šta mora da sadrži dnevni izveštaj', placeholder: 'npr. datum, korišćene funkcije, trajanje i svaka uočena greška.' },
  ] },
  { id: 'data-check', label: 'Provera podataka', category: 'Provera podataka', taskType: 'Provera informacija', subjectLabel: 'Naziv baze, brenda ili liste', subjectPlaceholder: 'npr. spisak restorana u Beogradu', title: subject => `Provera podataka: ${subject || 'nova lista'}`, description: 'Proveri unapred određena javno dostupna polja i predaj rezultat u traženom formatu.', instructionLead: 'Koristi samo navedene javne izvore. Ne unosi, ne prikupljaj i ne deli privatne podatke.', proof: 'Popunjena provera u propisanom formatu sa javnim izvorom', fields: [
    { key: 'source', label: 'Izvor podataka', placeholder: 'Link, tabela ili opis izvora koji korisnik proverava.' },
    { key: 'fields', label: 'Polja za proveru', placeholder: 'npr. naziv, adresa, telefon, radno vreme i pravilo za svako polje' },
    { key: 'output', label: 'Format rezultata', placeholder: 'npr. Naziv | proverena vrednost | izvor | napomena' },
  ] },
  { id: 'feedback', label: 'Kratak feedback', category: 'Kratak feedback', taskType: 'Korisnički feedback', subjectLabel: 'Naziv materijala ili proizvoda', subjectPlaceholder: 'npr. nova početna stranica', title: subject => `Feedback korisnika: ${subject || 'novi materijal'}`, description: 'Prikupi privatno, iskreno mišljenje o materijalu, proizvodu ili komunikaciji.', instructionLead: 'Daj konkretan privatni feedback. Ne tražimo javne ocene, lažne recenzije, praćenja niti plaćene klikove.', proof: 'Tekstualni odgovor koji pokriva sva pitanja', fields: [
    { key: 'material', label: 'Materijal za pregled', placeholder: 'Link ka stranici, prototipu, tekstu ili slici.' },
    { key: 'angles', label: 'Pitanja za feedback', placeholder: 'npr. šta je jasno, šta zbunjuje i šta bi promenio/la' },
    { key: 'minimum', label: 'Minimalni sadržaj odgovora', placeholder: 'npr. najmanje 3 odgovora od po 2 rečenice' },
  ] },
  { id: 'local-check', label: 'Lokalna provera', category: 'Lokalna provera', taskType: 'Lokalna provera', subjectLabel: 'Naziv lokacije ili usluge', subjectPlaceholder: 'npr. poslovnica u centru Novog Sada', title: subject => `Lokalna provera: ${subject || 'nova lokacija'}`, description: 'Proveri bezbedno i diskretno javno dostupne informacije o mestu ili usluzi.', instructionLead: 'Proveravaj samo javno dostupne informacije i prostore. Ne snimaj ljude, privatne prostore ili podatke bez dozvole.', proof: 'Kratak opis provere i samo dozvoljen javni dokaz', fields: [
    { key: 'place', label: 'Javno mesto ili područje', placeholder: 'npr. centar Novog Sada ili javno dostupna poslovnica' },
    { key: 'observations', label: 'Šta se proverava', placeholder: 'npr. radno vreme, dostupnost usluge i vidljivost izloga' },
    { key: 'safety', label: 'Ograničenja i dokaz', placeholder: 'Bez snimanja ljudi i privatnih prostora; navedi prihvatljiv dokaz.' },
  ] },
  { id: 'data-labeling', label: 'Označavanje podataka', category: 'Označavanje podataka', taskType: 'Označavanje podataka', subjectLabel: 'Naziv skupa podataka', subjectPlaceholder: 'npr. fotografije proizvoda', title: subject => `Označavanje podataka: ${subject || 'novi skup'}`, description: 'Označi unapred pripremljen skup podataka prema jasnim pravilima kvaliteta.', instructionLead: 'Primeni zadate oznake dosledno i označi granični slučaj kada pravilo nije dovoljno jasno.', proof: 'Popunjene oznake u traženom formatu', fields: [
    { key: 'dataset', label: 'Skup podataka', placeholder: 'Šta korisnik označava i koliko stavki obrađuje.' },
    { key: 'labels', label: 'Oznake i pravila', placeholder: 'npr. relevantno / nije relevantno, sa jasnim kriterijumima.' },
    { key: 'examples', label: 'Primeri i kontrola kvaliteta', placeholder: 'Navedi makar jedan dobar i jedan loš primer odgovora.' },
  ] },
]

function NovaCampanja({ onCancel, onSuccess, onCreate, onRevise, feePercent, platformPublishing, categories, campaign }: { onCancel: () => void; onSuccess: () => void; onCreate: (payload: Parameters<typeof api.createCampaign>[0]) => Promise<void>; onRevise: (id: number, payload: Parameters<typeof api.createCampaign>[0]) => Promise<void>; feePercent: number; platformPublishing: boolean; categories: string[]; campaign?: import('../lib/api').Task }) {
  const initialTemplate = campaign ? CAMPAIGN_TEMPLATES.find(template => template.category === campaign.category && template.taskType === campaign.task_type)?.id ?? 'legacy' : ''
  const [step, setStep] = useState(1)
  const [naziv, setNaziv] = useState(campaign?.title ?? '')
  const [templateId, setTemplateId] = useState(initialTemplate)
  const [subject, setSubject] = useState(campaign?.title ?? '')
  const [reward, setReward] = useState(campaign ? String(campaign.reward_rsd) : '')
  const [budget, setBudget] = useState(campaign ? String(Math.ceil(campaign.reward_rsd * campaign.total_slots * (1 + feePercent / 100))) : '')
  const [slots, setSlots] = useState(campaign ? String(campaign.total_slots) : '')
  const [campaignDurationDays, setCampaignDurationDays] = useState(String(campaign?.campaign_duration_days ?? 30))
  const [description, setDescription] = useState(campaign?.description ?? '')
  const [taskUrl, setTaskUrl] = useState(campaign?.target_url ?? '')
  const [category, setCategory] = useState(campaign?.category ?? '')
  const [proofRequired, setProofRequired] = useState(campaign?.proof_required ?? 'screenshot')
  const [repeatIntervalHours, setRepeatIntervalHours] = useState(String(campaign?.repeat_interval_hours ?? 0))
  const [revisionDeadlineHours, setRevisionDeadlineHours] = useState(String(campaign?.submission_deadline_hours ?? 24))
  const [maxProofRevisions, setMaxProofRevisions] = useState(String(campaign?.max_proof_revisions ?? 1))
  const [minQualityScore, setMinQualityScore] = useState(String(campaign?.min_quality_score ?? 0))
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
  const taskForm = CAMPAIGN_TEMPLATES.find(template => template.id === templateId)
  const keepsExistingBrief = Boolean(campaign) && templateId === 'legacy'
  const hasCompleteBrief = Boolean(campaign) || (Boolean(taskForm && subject.trim()) && Boolean(taskForm?.fields.every(field => taskDetails[field.key]?.trim())))
  const detailLines = taskForm?.fields.filter(field => taskDetails[field.key]?.trim()).map(field => `${field.label}: ${taskDetails[field.key].trim()}`) ?? []

  const selectTemplate = (id: string) => {
    const template = CAMPAIGN_TEMPLATES.find(item => item.id === id)
    setTemplateId(id)
    setTaskDetails({})
    if (!template) return
    setCategory(template.category)
    setProofRequired(template.proof)
    setDescription(template.description)
    setRequiresTesterEnrollment(Boolean(template.requiresTesterEnrollment))
    setNaziv(template.title(subject.trim()))
  }

  const updateSubject = (value: string) => {
    setSubject(value)
    if (!campaign && taskForm) setNaziv(taskForm.title(value.trim()))
  }

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
            <h3 className="font-bold text-ink">Izaberi šablon kampanje</h3>
            <p className="text-sm leading-6 text-ink-2">Šablon određuje stvarni tip posla, obavezne korake i dokaz. Tako anketu, UX test i beta test ne mogu imati iste uslove.</p>
            <Select label="Šta tačno želiš da uradi korisnik?" options={[
              { value: '', label: 'Odaberi šablon kampanje' },
              ...(campaign ? [{ value: 'legacy', label: 'Zadrži postojeći brief kampanje' }] : []),
              ...CAMPAIGN_TEMPLATES.filter(template => categories.includes(template.category)).map(template => ({ value: template.id, label: template.label })),
            ]} value={templateId} onChange={selectTemplate} />
            {taskForm && <>
              <div className="rounded-xl border border-violet-200 bg-violet-50 p-4"><p className="text-xs font-bold uppercase tracking-wide text-violet-700">Tip zadatka</p><p className="mt-1 font-bold text-ink">{taskForm.taskType}</p><p className="mt-1 text-xs leading-5 text-ink-2">Traženi dokaz: {taskForm.proof}</p></div>
              <Input label={taskForm.subjectLabel} placeholder={taskForm.subjectPlaceholder} value={subject} onChange={updateSubject} />
              <Input label="Naziv kampanje" placeholder="Naziv se predlaže iz šablona" value={naziv} onChange={setNaziv} />
            </>}
            {keepsExistingBrief && <>
              <Input label="Naziv kampanje" value={naziv} onChange={setNaziv} />
              <Alert type="info">Ova ranije kreirana kampanja nema novi šablon. Njene postojeće instrukcije i tip dokaza ostaju sačuvani dok ne izabereš novi šablon.</Alert>
            </>}
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-bold text-ink-2 uppercase tracking-wide">Cilj zadatka</label>
              <textarea value={description} onChange={event => setDescription(event.target.value)} rows={3} placeholder="Koju poslovnu odluku ili problem ovaj zadatak pomaže da se proveri?" className="bg-white border border-frame text-ink placeholder-ink-4 rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none resize-none" />
            </div>
            <Input label="Link za zadatak (opciono)" placeholder="https://vas-sajt.rs/test" value={taskUrl} onChange={setTaskUrl} />
            {taskForm?.id === 'website-ux' && <label className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950 cursor-pointer">
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
              <div><h4 className="font-bold text-ink">Obavezni detalji za: {taskForm.label}</h4><p className="mt-1 text-xs leading-5 text-ink-2">Ovi detalji postaju jasne instrukcije za korisnika i deo su moderacije kampanje.</p></div>
              {taskForm.fields.map(field => <div key={field.key} className="flex flex-col gap-1.5">
                <label className="text-xs font-bold text-ink-2 uppercase tracking-wide">{field.label}</label>
                <textarea value={taskDetails[field.key] ?? ''} onChange={event => setTaskDetails(current => ({ ...current, [field.key]: event.target.value }))} rows={2} placeholder={field.placeholder} className="bg-white border border-frame text-ink placeholder-ink-4 rounded-lg px-3 py-2 text-sm focus:border-blue-500 focus:outline-none resize-none" />
              </div>)}
            </div>}
            <div className="flex gap-2">
              <Btn variant="ghost" onClick={onCancel} size="sm">Otkaži</Btn>
              <Btn onClick={() => setStep(2)} disabled={!naziv || !description || !category || (!taskForm && !keepsExistingBrief) || !hasCompleteBrief} className="flex-1 justify-center">Dalje →</Btn>
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
            {!requiresTesterEnrollment && <div className="rounded-xl border border-sky-200 bg-sky-50/70 p-4 space-y-3">
              <div><p className="font-bold text-ink">Pravila izvršavanja</p><p className="mt-1 text-xs leading-5 text-ink-2">Postavi jasna pravila koja korisnik vidi pre početka. Ponavljanje se računa tek posle odobrenog dokaza.</p></div>
              <div className="grid gap-3 sm:grid-cols-2">
                <Select label="Ponavljanje zadatka" options={[{ value: '0', label: 'Samo jednom' }, { value: '12', label: 'Na 12 sati' }, { value: '24', label: 'Jednom dnevno' }, { value: '168', label: 'Jednom nedeljno' }]} value={repeatIntervalHours} onChange={setRepeatIntervalHours} />
                <Select label="Minimalni kvalitet izvršioca" options={[{ value: '0', label: 'Bez ograničenja' }, { value: '80', label: 'Najmanje 80%' }, { value: '90', label: 'Najmanje 90%' }]} value={minQualityScore} onChange={setMinQualityScore} />
                <Input label="Rok za doradu dokaza (sati)" type="number" min={1} max={336} value={revisionDeadlineHours} onChange={setRevisionDeadlineHours} />
                <Select label="Dopuštene dorade dokaza" options={[{ value: '0', label: 'Bez dorade' }, { value: '1', label: 'Jedna dorada' }, { value: '2', label: 'Dve dorade' }, { value: '3', label: 'Tri dorade' }]} value={maxProofRevisions} onChange={setMaxProofRevisions} />
              </div>
            </div>}
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
                {!requiresTesterEnrollment && <><div className="flex justify-between gap-4"><span className="text-ink-2">Ponavljanje</span><span className="font-semibold text-ink text-right">{Number(repeatIntervalHours) ? `na ${repeatIntervalHours} h` : 'samo jednom'}</span></div><div className="flex justify-between gap-4"><span className="text-ink-2">Dorada dokaza</span><span className="font-semibold text-ink text-right">do {maxProofRevisions} puta, rok {revisionDeadlineHours} h</span></div><div className="flex justify-between gap-4"><span className="text-ink-2">Kvalitet izvršioca</span><span className="font-semibold text-ink text-right">{Number(minQualityScore) ? `najmanje ${minQualityScore}%` : 'bez ograničenja'}</span></div></>}
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
                const deliveryConfigValid = requiresTesterEnrollment || (Number(repeatIntervalHours) >= 0 && Number(repeatIntervalHours) <= 720 && Number(revisionDeadlineHours) >= 1 && Number(revisionDeadlineHours) <= 336 && Number(maxProofRevisions) >= 0 && Number(maxProofRevisions) <= 3 && Number(minQualityScore) >= 0 && Number(minQualityScore) <= 100)
                if (!Number.isFinite(rewardRsd) || rewardRsd <= 0 || totalSlots < 1 || !testerConfigValid || !durationValid || !deliveryConfigValid) {
                  setError(platformPublishing ? 'Unesi validnu nagradu i broj izvršenja od najmanje jedan.' : 'Unesi validnu nagradu i budžet dovoljan za najmanje jedan zadatak.')
                  return
                }
                setSubmitting(true)
                setError('')
                try {
                  const betaPlan = requiresTesterEnrollment ? `\n\nPlan zatvorenog beta testiranja:\n- Tester prvo šalje email za poziv u store tester listu.\n- Svaki tester ima ${testerDurationDays} dana od ručne potvrde pristupa.\n- Svakog dana testira najmanje ${testerDailyMinutes} minuta i šalje kratak izveštaj.\n- Dnevna nagrada: ${testerDailyReward} RSD, uz odobrenje oglašivača.` : ''
                  const instructionLead = taskForm?.instructionLead ?? 'Korisnik treba da prati specifikaciju zadatka i dostavi samo traženi dokaz.'
                  const preservesCurrentContent = Boolean(campaign) && detailLines.length === 0
                  const payload = { title: naziv, category, task_type: taskForm?.taskType ?? campaign?.task_type ?? category, target_url: taskUrl || undefined, description: description.trim(), instructions: preservesCurrentContent ? campaign?.instructions ?? instructionLead : `${instructionLead}\n\nKoraci i pravila:\n${detailLines.map(line => `- ${line}`).join('\n')}${betaPlan}`, proof_required: proofRequired, reward_rsd: rewardRsd, total_slots: totalSlots, campaign_duration_days: Number(campaignDurationDays), target_city: targetCity || undefined, target_age_group: targetAgeGroup, target_interests: targetInterests || undefined, requires_tester_enrollment: requiresTesterEnrollment, tester_required_count: Number(testerRequiredCount), tester_duration_days: Number(testerDurationDays), tester_daily_minutes: Number(testerDailyMinutes), tester_daily_reward_rsd: requiresTesterEnrollment ? Number(testerDailyReward) : 0, repeat_interval_hours: requiresTesterEnrollment ? 0 : Number(repeatIntervalHours), submission_deadline_hours: Number(revisionDeadlineHours), max_proof_revisions: Number(maxProofRevisions), min_quality_score: Number(minQualityScore) }
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
  const [page, setPage] = useState<Page>(() => window.location.pathname === '/oglasivac/testeri' ? 'testeri' : 'pregled')
  const [mobileOpen, setMobileOpen] = useState(false)
  const [proofsTab, setProofsTab] = useState('svi')
  const [visibleEvidenceCount, setVisibleEvidenceCount] = useState(20)
  const [chatTarget, setChatTarget] = useState<{ taskId: number; participantId: number } | null>(null)
  const [logoutConfirm, setLogoutConfirm] = useState(false)
  const [roleCorrectionConfirm, setRoleCorrectionConfirm] = useState(false)
  const [campaignLifecycleAction, setCampaignLifecycleAction] = useState<{ id: number; title: string; action: 'pause' | 'resume' | 'stop' } | null>(null)
  const [dashboard, setDashboard] = useState<AdvertiserDashboardData | null>(null)
  const [campaignToRevise, setCampaignToRevise] = useState<import('../lib/api').Task | null>(null)
  const [campaignContentEdit, setCampaignContentEdit] = useState<{ id: number; title: string; description: string; instructions: string; target_url: string } | null>(null)
  const [contentRevisions, setContentRevisions] = useState<ContentRevision[]>([])
  const [contentSaving, setContentSaving] = useState(false)
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
  const [bannerStartDate, setBannerStartDate] = useState(() => firstBookableBannerDate())
  const [bannerError, setBannerError] = useState('')
  const [bannerLoading, setBannerLoading] = useState(false)
  const [startingBannerId, setStartingBannerId] = useState<number | null>(null)
  const [bannerUploading, setBannerUploading] = useState(false)
  const [bannerEdit, setBannerEdit] = useState<{ id: number; title: string; body: string; image_url: string; target_url: string } | null>(null)
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
  const [notifications, setNotifications] = useState<NotificationItem[]>([])
  const [chatThreads, setChatThreads] = useState<TaskChatInboxItem[]>([])
  const [ticketSubject, setTicketSubject] = useState('')
  const [ticketBody, setTicketBody] = useState('')
  const [ticketLoading, setTicketLoading] = useState(false)
  const { show: showToast, node: toastNode } = useToast()

  const refreshDashboard = async () => {
    try {
      const [dashboardData, bannerData, promotionData, ticketData, notificationData, chatData, revisionData] = await Promise.all([api.advertiserDashboard(), api.advertiserBanners(), api.advertiserPromotions(), api.tickets(), api.notifications().catch(() => ({ notifications: [] })), api.advertiserTaskChats().catch(() => ({ threads: [] })), api.advertiserContentRevisions()])
      setDashboard(dashboardData)
      setBannerSlots(bannerData.slots)
      setOwnBanners(bannerData.banners)
      setContentRevisions(revisionData.revisions)
      setPromotions(promotionData.promotions)
      setTickets(ticketData.tickets)
      setNotifications(notificationData.notifications)
      setChatThreads(chatData.threads)
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
    const refreshChats = () => {
      if (document.visibilityState !== 'visible') return
      void api.advertiserTaskChats().then(data => setChatThreads(data.threads)).catch(() => {})
      void api.notifications().then(data => setNotifications(data.notifications)).catch(() => {})
    }
    refreshChats()
    const timer = window.setInterval(refreshChats, 15000)
    window.addEventListener('focus', refreshChats)
    return () => { window.clearInterval(timer); window.removeEventListener('focus', refreshChats) }
  }, [])

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
      if (!order.approval_url) throw new Error('PayPal nije vratio link za potvrdu uplate. Uplata nije pokrenuta.')
      window.location.assign(order.approval_url)
    } catch (error) {
      setTopupError(error instanceof Error ? error.message : 'PayPal uplata nije mogla da se pokrene.')
      setTopupLoading(false)
    }
  }

  const reserveBanner = async () => {
    const daysCount = Number(bannerDays)
    if (!bannerSlotId || !bannerStartDate || !bannerTitle.trim() || !Number.isInteger(daysCount) || daysCount < 1 || daysCount > 31) {
      setBannerError('Izaberi slot i datum početka, unesi naslov, pa trajanje od 1 do 31 dana.')
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
        target_url: bannerUrl.trim() || undefined,
        days_count: daysCount,
        requested_start_at: new Date(`${bannerStartDate}T12:00:00`).toISOString(),
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

  const pendingRevision = (entityType: 'campaign' | 'banner', entityId: number) => contentRevisions.find(revision => revision.entity_type === entityType && revision.entity_id === entityId && revision.status === 'pending')

  const startPlatformBannerNow = async (id: number) => {
    setStartingBannerId(id)
    try {
      await api.startPlatformBannerNow(id)
      await refreshDashboard()
      showToast('Baner se sada prikazuje. Period zakupa počinje od ovog trenutka.', 'success')
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Baner nije mogao da krene sada.', 'error')
    } finally {
      setStartingBannerId(null)
    }
  }

  const saveBannerEdit = async () => {
    if (!bannerEdit) return
    setContentSaving(true)
    try {
      const result = await api.editAdvertiserBanner(bannerEdit.id, {
        title: bannerEdit.title.trim(), body: bannerEdit.body.trim() || null,
        image_url: bannerEdit.image_url.trim() || null, target_url: bannerEdit.target_url.trim() || null,
      })
      await refreshDashboard()
      setBannerEdit(null)
      showToast(result.revision ? 'Izmena bannera je poslata adminu. Odobrena verzija ostaje aktivna do odluke.' : 'Banner je izmenjen i i dalje čeka admin proveru.', 'success')
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Izmena bannera nije poslata.', 'error')
    } finally {
      setContentSaving(false)
    }
  }

  const saveCampaignContentEdit = async () => {
    if (!campaignContentEdit) return
    setContentSaving(true)
    try {
      await api.editActiveCampaignContent(campaignContentEdit.id, {
        title: campaignContentEdit.title.trim(), description: campaignContentEdit.description.trim(),
        instructions: campaignContentEdit.instructions.trim(),
        target_url: campaignContentEdit.target_url.trim() || null,
      })
      await refreshDashboard()
      setCampaignContentEdit(null)
      showToast('Izmena kampanje je poslata adminu. Dosadašnja verzija ostaje aktivna do odluke.', 'success')
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Izmena kampanje nije poslata.', 'error')
    } finally {
      setContentSaving(false)
    }
  }

  const uploadBannerEdit = async (file: File | undefined) => {
    if (!file || !bannerEdit) return
    setBannerUploading(true)
    try {
      const uploaded = await api.uploadAdvertiserBanner(file)
      setBannerEdit(current => current ? { ...current, image_url: uploaded.image_url } : null)
      showToast('Nova slika je otpremljena. Prikazaće se tek kada admin odobri izmenu.', 'success')
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Slika nije otpremljena.', 'error')
    } finally {
      setBannerUploading(false)
    }
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
  const submittedEvidence = [
    ...testerCheckins.map(item => ({
      kind: 'checkin' as const, key: `day-${item.id}`, id: item.id,
      taskId: item.task_id, userId: item.user_id, userName: item.user_name || 'Korisnik',
      taskTitle: item.task_title || 'Zadatak', body: item.note, rewardRsd: item.reward_rsd,
      status: item.status === 'pending' ? 'na_proveri' : item.status === 'approved' ? 'odobreno' : 'odbijeno',
      submittedAt: item.checked_in_at, dayNumber: item.day_number, reviewNote: item.review_note,
    })),
    ...proofs.map(item => ({
      kind: 'proof' as const, key: `proof-${item.id}`, id: item.id,
      taskId: item.submission.task_id, userId: item.submission.user_id, userName: item.korisnik,
      taskTitle: item.zadatak, body: item.submission.proof, rewardRsd: item.submission.reward_rsd,
      status: item.status, submittedAt: item.submission.created_at, reviewNote: item.submission.review_note,
    })),
  ].sort((a, b) => Number(b.status === 'na_proveri') - Number(a.status === 'na_proveri') || new Date(b.submittedAt || 0).getTime() - new Date(a.submittedAt || 0).getTime())
  const filteredEvidence = submittedEvidence.filter(item => proofsTab === 'svi' || item.status === proofsTab)
  const unreadChatNotifications = notifications.filter(item => item.status === 'unread' && item.title === 'Nova poruka uz zadatak')
  const unreadNotificationCount = notifications.filter(item => item.status === 'unread').length
  const pendingProofCount = proofs.filter(proof => proof.status === 'na_proveri').length + testerCheckins.filter(item => item.status === 'pending').length
  const pendingTesterEnrollmentCount = testerEnrollments.filter(enrollment => enrollment.status === 'requested').length
  const navigationGroups = navGroups.map(group => ({
    ...group,
    items: group.items.map(item => item.id === 'dokazi' ? { ...item, badge: pendingProofCount || undefined } : item.id === 'testeri' ? { ...item, badge: pendingTesterEnrollmentCount || undefined } : item.id === 'poruke' ? { ...item, badge: unreadChatNotifications.length || undefined } : item.id === 'obavestenja' ? { ...item, badge: unreadNotificationCount || undefined } : item),
  }))

  useEffect(() => {
    const onPopState = () => setPage(window.location.pathname === '/oglasivac/testeri' ? 'testeri' : 'pregled')
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  function goTo(p: Page) {
    const path = p === 'testeri' ? '/oglasivac/testeri' : '/oglasivac/panel'
    if (window.location.pathname !== path) window.history.pushState({}, '', path)
    setPage(p)
  }
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
      {chatTarget && <TaskChat taskId={chatTarget.taskId} participantId={chatTarget.participantId} onClose={() => setChatTarget(null)} />}

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
        open={roleCorrectionConfirm}
        title="Prebaciti nalog u korisnički režim?"
        description="Ovaj nalog će moći da radi zadatke umesto da objavljuje kampanje. Promena je dozvoljena samo ako nemaš kampanje, budžet ili uplate."
        confirmLabel="Da, želim da radim zadatke"
        cancelLabel="Otkaži"
        variant="success"
        onConfirm={async () => {
          try {
            await api.correctAccountRoleToUser()
            showToast('Nalog je prebačen u korisnički režim.', 'success')
            setRoleCorrectionConfirm(false)
            onNavigate('dashboard')
          } catch (error) {
            showToast(error instanceof Error ? error.message : 'Uloga naloga nije promenjena.', 'error')
          }
        }}
        onCancel={() => setRoleCorrectionConfirm(false)}
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
        <Sidebar groups={navigationGroups} active={page} onNavigate={p => goTo(p as Page)} footer={sidebarFooter} />
      </div>
      {mobileOpen && (
        <div className="fixed left-0 top-0 h-full z-50 lg:hidden">
          <Sidebar groups={navigationGroups} active={page} onNavigate={p => { goTo(p as Page); setMobileOpen(false) }} footer={sidebarFooter} isMobile onClose={() => setMobileOpen(false)} />
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
                {advertiser && <p className="text-xs font-medium text-ink-3">{advertiser.role === 'admin' ? 'Admin nalog · objave platforme' : 'Oglašivački nalog'}: {advertiser.email}</p>}
                {advertiser?.role === 'oglasivac' && (dashboard?.tasks ?? []).length === 0 && (dashboard?.transactions ?? []).length === 0 && !advertiser.advertiser_budget_rsd && !advertiser.advertiser_reserved_rsd && !advertiser.advertiser_spent_rsd && <Card className="p-5 border-violet-200 bg-violet-50"><div className="flex flex-wrap items-center justify-between gap-4"><div><p className="font-bold text-ink">Otvorio/la si oglašivački nalog greškom?</p><p className="text-sm text-ink-2 mt-1">Samo prazan nalog bez kampanja i uplata možeš jednokratno ispraviti u korisnički. Nalog sa poslovnim podacima ne menja se automatski.</p></div><Btn size="sm" variant="secondary" onClick={() => setRoleCorrectionConfirm(true)}>Ispravi u korisnički nalog</Btn></div></Card>}
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
                       ['needs_revision', 'pending'].includes(c.task.status)
                         ? <Btn size="sm" variant="secondary" onClick={() => { setCampaignToRevise(c.task); goTo('nova') }}>Uredi i pošalji na proveru</Btn>
                         : c.task.status === 'active'
                           ? <div className="flex flex-wrap gap-1.5">{pendingRevision('campaign', c.task.id) ? <span className="text-xs font-semibold text-amber-700">Izmena čeka proveru</span> : <Btn size="sm" variant="secondary" onClick={() => setCampaignContentEdit({ id: c.task.id, title: c.task.title, description: c.task.description, instructions: c.task.instructions, target_url: c.task.target_url || '' })}>Uredi sadržaj</Btn>}<Btn size="sm" variant="secondary" onClick={() => setCampaignLifecycleAction({ id: c.task.id, title: c.task.title, action: 'pause' })}>Pauziraj</Btn><Btn size="sm" variant="danger" onClick={() => setCampaignLifecycleAction({ id: c.task.id, title: c.task.title, action: 'stop' })}>Završi</Btn></div>
                           : c.task.status === 'paused'
                             ? <div className="flex flex-wrap gap-1.5"><Btn size="sm" variant="success" onClick={() => setCampaignLifecycleAction({ id: c.task.id, title: c.task.title, action: 'resume' })}>Nastavi</Btn><Btn size="sm" variant="danger" onClick={() => setCampaignLifecycleAction({ id: c.task.id, title: c.task.title, action: 'stop' })}>Završi</Btn></div>
                             : <span className="text-xs text-ink-3">{c.task.moderation_note || 'Čeka proveru'}</span>,
                    ])}
                  />
                </Card>
                {campaignContentEdit && <Card className="mt-5 space-y-4 border-blue-200 p-5">
                  <div><h2 className="font-bold text-ink">Izmena aktivne kampanje</h2><p className="mt-1 text-sm text-ink-2">Stari odobreni sadržaj ostaje javno dostupan do admin odluke. Nagradu, broj mesta i uslove postojećih učesnika ovde ne menjamo.</p></div>
                  <Input label="Naslov" value={campaignContentEdit.title} onChange={value => setCampaignContentEdit(current => current ? { ...current, title: value } : null)} />
                  <label className="block text-xs font-semibold uppercase tracking-wide text-ink-2" htmlFor="active-campaign-description">Opis kampanje</label>
                  <textarea id="active-campaign-description" rows={5} value={campaignContentEdit.description} onChange={event => setCampaignContentEdit(current => current ? { ...current, description: event.target.value } : null)} className="w-full rounded-lg border border-frame bg-white p-3 text-sm text-ink focus:border-blue-500 focus:outline-none" />
                  <label className="block text-xs font-semibold uppercase tracking-wide text-ink-2" htmlFor="active-campaign-instructions">Uputstvo za korisnika</label>
                  <textarea id="active-campaign-instructions" rows={8} value={campaignContentEdit.instructions} onChange={event => setCampaignContentEdit(current => current ? { ...current, instructions: event.target.value } : null)} className="w-full rounded-lg border border-frame bg-white p-3 text-sm text-ink focus:border-blue-500 focus:outline-none" />
                  <Input label="Link zadatka (opciono)" value={campaignContentEdit.target_url} onChange={value => setCampaignContentEdit(current => current ? { ...current, target_url: value } : null)} />
                  <div className="flex flex-wrap gap-2"><Btn disabled={contentSaving || campaignContentEdit.title.trim().length < 3 || campaignContentEdit.description.trim().length < 5 || campaignContentEdit.instructions.trim().length < 5} onClick={() => void saveCampaignContentEdit()}>{contentSaving ? 'Slanje...' : 'Pošalji izmenu adminu'}</Btn><Btn variant="secondary" onClick={() => setCampaignContentEdit(null)}>Otkaži</Btn></div>
                </Card>}
              </div>
            )}

            {page === 'obavestenja' && (
              <div className="space-y-4">
                <SectionHeader title="Obaveštenja" description="Novosti o kampanjama, testerima, dokazima i nalogu." />
                {notifications.length === 0 ? <EmptyState icon="🔔" title="Nema obaveštenja" description="Nove informacije o kampanjama i nalogu pojaviće se ovde." /> : notifications.map(item => <Card key={item.id} className={`p-4 ${item.status === 'unread' ? 'border-blue-200 bg-blue-50' : ''}`}>
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="min-w-0 flex-1"><p className="font-bold text-ink">{item.title}</p><p className="mt-1 break-words text-sm text-ink-2">{item.body}</p><p className="mt-2 text-xs text-ink-3">{displayDate(item.created_at)}</p></div>
                    <div className="flex shrink-0 flex-wrap gap-2">
                      {item.title === 'Nova poruka uz zadatak' && <Btn size="sm" variant="secondary" onClick={() => goTo('poruke')}>Otvori poruke</Btn>}
                      {item.status === 'unread' && <Btn size="sm" variant="secondary" onClick={() => void (async () => { try { await api.markNotificationRead(item.id); setNotifications(current => current.map(note => note.id === item.id ? { ...note, status: 'read' } : note)) } catch { showToast('Obaveštenje nije označeno kao pročitano.', 'error') } })()}>Pročitano</Btn>}
                    </div>
                  </div>
                </Card>)}
              </div>
            )}

            {page === 'poruke' && (
              <div className="space-y-5">
                <SectionHeader title="Poruke uz zadatke" description="Razgovori sa korisnicima o pristupu i toku njihovih zadataka." />
                {unreadChatNotifications.length > 0 && <Card className="border-blue-200 bg-blue-50 p-5">
                  <h3 className="font-bold text-blue-950">Nove poruke ({unreadChatNotifications.length})</h3>
                  <div className="mt-3 space-y-2">{unreadChatNotifications.map(item => <div key={item.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-blue-100 bg-white p-3">
                    <p className="text-sm text-ink">{item.body}</p>
                    <Btn size="sm" variant="secondary" onClick={() => void (async () => { try { await api.markNotificationRead(item.id); setNotifications(current => current.map(note => note.id === item.id ? { ...note, status: 'read' } : note)) } catch { showToast('Poruka nije označena kao pročitana.', 'error') } })()}>Pročitano</Btn>
                  </div>)}</div>
                </Card>}
                {chatThreads.length === 0 ? <EmptyState icon="💬" title="Još nema razgovora" description="Kada korisnik pošalje poruku uz zadatak, razgovor će se pojaviti ovde." /> : <Card className="p-5">
                  <div className="space-y-3">{chatThreads.map(thread => <div key={`${thread.task_id}-${thread.participant_id}`} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-frame bg-mint-50 p-4">
                    <div className="min-w-0"><p className="font-semibold text-ink">{thread.participant_name}</p><p className="text-sm text-ink-2">{thread.task_title}</p><p className="mt-1 line-clamp-2 break-words text-sm text-ink-3">{thread.last_message}</p></div>
                    <Btn size="sm" variant="secondary" onClick={() => setChatTarget({ taskId: thread.task_id, participantId: thread.participant_id })}>Otvori razgovor</Btn>
                  </div>)}</div>
                </Card>}
              </div>
            )}

            {page === 'testeri' && (
              <div>
                <SectionHeader title="Prijavljeni testeri" description="Prijave za zatvoreno testiranje, adrese za poziv i aktivacija pristupa na jednom mestu." action={<Btn size="sm" variant="secondary" onClick={() => goTo('dokazi')}>Otvori dokaze →</Btn>} />
                {testerEnrollments.length === 0 && <Card className="p-5 text-sm text-ink-2">Još nema prijava za zatvoreno testiranje.</Card>}
                {testerEnrollments.length > 0 && <div className="mb-5">
                  <div className="mb-4 rounded-2xl border border-violet-200 bg-gradient-to-r from-violet-50 via-white to-emerald-50 p-5 shadow-sm">
                    <p className="text-xs font-bold uppercase tracking-[0.18em] text-violet-700">Kontrola zatvorenog testiranja</p>
                    <h2 className="mt-1 text-xl font-extrabold text-ink">Prijave za zatvoreno testiranje</h2>
                    <p className="mt-2 max-w-3xl text-sm leading-6 text-ink-2">Ne čeka se ciljnih 20 prijava. Čim email testera dodaš u odgovarajuću tester listu, aktiviraj ga ovde i njegov lični period od 14 dana počinje odmah.</p>
                  </div>
                  <div className="mb-5 grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
                    {(dashboard?.tasks ?? []).filter(task => task.requires_tester_enrollment).map(task => {
                      const requested = testerEnrollments.filter(item => item.task_id === task.id && item.status === 'requested').length
                      const ready = testerEnrollments.filter(item => item.task_id === task.id && item.status === 'requested' && !item.email_conflict).length
                      const target = task.tester_required_count
                      const canStart = ready > 0
                      return <Card key={task.id} className="group relative overflow-hidden border-violet-200 bg-white p-5 shadow-md transition-shadow hover:shadow-lg">
                        <div className="pointer-events-none absolute -right-10 -top-10 h-28 w-28 rounded-full bg-violet-100/70 transition-transform group-hover:scale-125" />
                        <div className="relative">
                          <div className="flex items-start justify-between gap-3">
                            <div className="flex min-w-0 items-center gap-3">
                              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-violet-600 text-xl shadow-sm">📱</div>
                              <div className="min-w-0">
                                <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-violet-700">Kontinuirano testiranje</p>
                                <h3 className="truncate text-base font-extrabold text-ink" title={task.title}>{task.title}</h3>
                              </div>
                            </div>
                            <StatusBadge status={canStart ? 'aktivno' : 'na_cekanju'} />
                          </div>
                          <div className="mt-5 grid grid-cols-3 divide-x divide-violet-100 rounded-xl border border-violet-100 bg-violet-50/70 py-3 text-center">
                            <div><p className="font-mono text-lg font-extrabold text-violet-700">{requested}</p><p className="text-[10px] font-semibold uppercase tracking-wide text-ink-3">prijava</p></div>
                            <div><p className="font-mono text-lg font-extrabold text-emerald-700">{target}</p><p className="text-[10px] font-semibold uppercase tracking-wide text-ink-3">cilj</p></div>
                            <div><p className="font-mono text-lg font-extrabold text-blue-700">{task.tester_enrollment_invited ?? 0}</p><p className="text-[10px] font-semibold uppercase tracking-wide text-ink-3">aktivno</p></div>
                          </div>
                          <p className="mt-4 min-h-10 text-xs leading-5 text-ink-2">{requested > ready ? `${ready} prijava je spremno za aktivaciju; ${requested - ready} ima konflikt test adrese i zahteva proveru.` : canStart ? `${ready} prijava čeka. Aktiviraj svakog testera čim ga dodaš u store listu; nema čekanja da se dostigne cilj od ${target}.` : `Nema prijava na čekanju. Cilj kampanje je ${target} aktivnih testera, ali svaki novi može krenuti odmah.`}</p>
                          <Btn size="sm" className="mt-4 w-full justify-center" disabled={!canStart} variant="success" onClick={() => void (async () => { try { const result = await api.startTesterCohort(task.id, 1); await refreshDashboard(); showToast(`${result.activated_count} tester je aktiviran. Njegov lični period testiranja počinje danas.`, 'success') } catch (error) { showToast(error instanceof Error ? error.message : 'Tester nije aktiviran.', 'error') } })()}>
                            Aktiviraj sledećeg testera
                          </Btn>
                        </div>
                      </Card>
                    })}
                  </div>
                  <Card className="border-violet-100 p-4 shadow-md sm:p-5">
                    <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
                      <div>
                        <h3 className="font-bold text-ink">Prijavljeni testeri</h3>
                        <p className="mt-1 text-xs text-ink-3">KlikZarada nalog i email za testiranje su odvojeni podaci.</p>
                      </div>
                      <span className="rounded-full bg-violet-50 px-3 py-1 text-xs font-semibold text-violet-700">{testerEnrollments.length} prijava</span>
                    </div>
                    <div className="space-y-3">
                      {testerEnrollments.map(item => <div key={item.id} className={`grid min-w-0 gap-4 rounded-xl border p-4 lg:grid-cols-2 2xl:grid-cols-4 ${item.email_conflict ? 'border-red-200 bg-red-50/40' : 'border-frame bg-white'}`}>
                        <div className="min-w-0">
                          <p className="mb-1 text-[11px] font-bold uppercase tracking-wide text-ink-3">KlikZarada nalog</p>
                          <p className="font-semibold text-ink break-words">{item.user_name || 'Korisnik'}</p>
                          <p className="mt-1 text-xs text-ink-2 break-all select-all">{item.account_email || '—'}</p>
                          <p className="mt-1 text-xs text-ink-3">ID naloga: {item.user_id || '—'}</p>
                        </div>
                        <div className="min-w-0">
                          <p className="mb-1 text-[11px] font-bold uppercase tracking-wide text-ink-3">Kampanja</p>
                          <p className="text-sm leading-5 text-ink-2 break-words">{item.task_title || 'Zadatak'}</p>
                        </div>
                        <div className="min-w-0">
                          <p className="mb-1 text-[11px] font-bold uppercase tracking-wide text-ink-3">Email za testiranje</p>
                          <p className="font-mono text-xs leading-5 text-ink break-all select-all">{item.testing_email || '—'}</p>
                          {item.email_conflict && <p className="mt-2 rounded-lg bg-red-100 px-2.5 py-2 text-xs font-semibold leading-5 text-red-800">Adresa je povezana i sa drugim nalogom. Proveri vlasništvo pre odobravanja.</p>}
                          {!item.email_conflict && item.account_email && item.testing_email?.toLowerCase() !== item.account_email.toLowerCase() && <p className="mt-2 text-xs leading-5 text-amber-700">Druga adresa koju je tester uneo.</p>}
                        </div>
                        <div className="min-w-0">
                          <p className="mb-2 text-[11px] font-bold uppercase tracking-wide text-ink-3">Status i akcije</p>
                          <StatusBadge status={item.status === 'requested' ? 'na_cekanju' : item.status === 'invited' ? 'aktivno' : 'odbijeno'} />
                          <p className="my-2 text-xs leading-5 text-ink-3">{item.status === 'requested' ? item.email_conflict ? 'Prvo razjasni test adresu.' : 'Dodaj email u store listu, pa aktiviraj.' : item.note || (item.status === 'invited' ? `Aktiviran od ${item.invited_at ? new Intl.DateTimeFormat('sr-RS').format(new Date(item.invited_at)) : 'danas'}` : 'Obrađeno')}</p>
                          <div className="flex flex-wrap gap-2">
                            {item.status === 'requested' && <><Btn size="sm" variant="success" disabled={item.email_conflict} onClick={() => void (async () => { try { await api.updateTesterEnrollment(item.id, 'invited'); await refreshDashboard(); showToast('Tester je aktiviran, a njegov lični period testiranja počinje danas.', 'success') } catch (error) { showToast(error instanceof Error ? error.message : 'Tester nije aktiviran.', 'error') } })()}>Aktiviraj sada</Btn><Btn size="sm" variant="danger" onClick={() => void (async () => { try { await api.updateTesterEnrollment(item.id, 'declined', 'Trenutno nema slobodnih mesta u zatvorenom testiranju.'); await refreshDashboard(); showToast('Prijava je odbijena uz obaveštenje korisniku.', 'success') } catch (error) { showToast(error instanceof Error ? error.message : 'Status prijave nije ažuriran.', 'error') } })()}>Odbij</Btn></>}
                            {item.user_id && item.status !== 'declined' && <Btn size="sm" variant="secondary" onClick={() => setChatTarget({ taskId: item.task_id, participantId: item.user_id! })}>Poruke</Btn>}
                          </div>
                        </div>
                      </div>)}
                    </div>
                  </Card>
                </div>}
              </div>
            )}

            {page === 'dokazi' && (
              <div>
                <SectionHeader title="Dokazi korisnika" description="Svi poslati dnevni izveštaji i ostali dokazi su u jednom spisku. Otvori stavku da vidiš ceo dokaz i odlučiš o njemu." action={<Btn size="sm" variant="secondary" onClick={() => goTo('testeri')}>Prijavljeni testeri →</Btn>} />
                <div className="mb-6 grid gap-3 sm:grid-cols-3">
                  <StatCard label="Na proveri" value={String(pendingProofCount)} accent="orange" />
                  <StatCard label="Dnevni izveštaji" value={String(testerCheckins.length)} accent="blue" />
                  <StatCard label="Ostali dokazi" value={String(proofs.length)} accent="green" />
                </div>
                <SectionHeader title="Poslati dokazi" description="Dnevni izveštaji i ostali dokazi na jednom mestu. Stavke na proveri su prve; otvori red za ceo sadržaj i akcije." />
                <Tabs
                  tabs={[{ id: 'svi', label: 'Svi' }, { id: 'na_proveri', label: 'Na proveri' }, { id: 'needs_revision', label: 'Na doradi' }, { id: 'odobreno', label: 'Odobreno' }, { id: 'odbijeno', label: 'Odbijeno' }]}
                  active={proofsTab}
                  onChange={tab => { setProofsTab(tab); setVisibleEvidenceCount(20) }}
                />
                {filteredEvidence.length === 0 ? <Card className="p-5 text-sm text-ink-2">Nema poslatih dokaza za izabrani status.</Card> : <>
                  <Card className="overflow-hidden">
                    <div className="divide-y divide-frame">
                      {filteredEvidence.slice(0, visibleEvidenceCount).map(item => {
                        const emailConflict = item.kind === 'checkin' && testerEnrollments.some(enrollment => enrollment.task_id === item.taskId && enrollment.user_id === item.userId && enrollment.email_conflict)
                        return <details key={item.key} className="group">
                          <summary className="grid cursor-pointer list-none gap-2 px-4 py-3 hover:bg-mint-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-600 sm:grid-cols-[minmax(0,1.2fr)_minmax(0,1.8fr)_auto_auto] sm:items-center sm:gap-4">
                            <span className="min-w-0 font-semibold text-ink break-words">{item.userName}</span>
                            <span className="min-w-0 text-sm text-ink-2 break-words">{item.taskTitle} <span className="text-ink-3">· {item.kind === 'checkin' ? `Dan ${item.dayNumber}` : 'Dokaz zadatka'}</span></span>
                            <StatusBadge status={item.status} />
                            <span className="text-sm font-semibold text-emerald-700 sm:text-right">{item.rewardRsd} RSD <span className="ml-2 text-blue-600 group-open:hidden">Pregledaj ↓</span><span className="ml-2 hidden text-blue-600 group-open:inline">Zatvori ↑</span></span>
                          </summary>
                          <div className="border-t border-frame bg-mint-50/60 px-4 py-4">
                            <p className="text-xs font-bold uppercase tracking-wide text-ink-3">{item.kind === 'checkin' ? 'Dnevni izveštaj' : 'Poslati dokaz'}</p>
                            <p className="mt-2 whitespace-pre-wrap break-words text-sm leading-6 text-ink">{item.body || 'Nema tekstualnog dokaza.'}</p>
                            {item.submittedAt && <p className="mt-3 text-xs text-ink-3">Poslato: {new Intl.DateTimeFormat('sr-RS', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(item.submittedAt))}</p>}
                            {emailConflict && <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm font-semibold text-red-800">Test adresa je povezana sa drugim nalogom. Proveri vlasništvo pre odobravanja.</p>}
                            {item.status === 'na_proveri' ? <div className="mt-4 flex flex-wrap gap-2 border-t border-frame pt-4">
                              {item.kind === 'checkin' ? <>
                                <Btn size="sm" variant="success" disabled={emailConflict} onClick={() => void (async () => { try { await api.reviewTesterCheckin(item.id, 'approved'); await refreshDashboard(); showToast('Dnevni izveštaj je odobren, a nagrada prebačena korisniku.', 'success') } catch (error) { showToast(error instanceof Error ? error.message : 'Dnevni izveštaj nije obrađen.', 'error') } })()}>Odobri izveštaj i nagradu</Btn>
                                <Btn size="sm" variant="danger" onClick={() => void (async () => { try { await api.reviewTesterCheckin(item.id, 'rejected', 'Izveštaj nema dovoljno detalja za ovaj dan.'); await refreshDashboard(); showToast('Dnevni izveštaj je odbijen.', 'success') } catch (error) { showToast(error instanceof Error ? error.message : 'Dnevni izveštaj nije obrađen.', 'error') } })()}>Odbij izveštaj</Btn>
                              </> : <>
                                <Btn size="sm" variant="success" onClick={() => void (async () => { try { await api.reviewAdvertiserSubmission(item.id, 'approved'); await refreshDashboard(); showToast('Dokaz je odobren, a nagrada prebačena korisniku.', 'success') } catch (error) { showToast(error instanceof Error ? error.message : 'Dokaz nije obrađen.', 'error') } })()}>Odobri</Btn>
                                <Btn size="sm" variant="secondary" onClick={() => void (async () => { try { await api.reviewAdvertiserSubmission(item.id, 'needs_revision', 'Dopuni dokaz jasnim linkom ili snimkom ekrana i odgovori na zahteve iz specifikacije zadatka.'); await refreshDashboard(); showToast('Korisnik je obavešten da dopuni dokaz.', 'success') } catch (error) { showToast(error instanceof Error ? error.message : 'Dorada dokaza nije poslata.', 'error') } })()}>Traži doradu</Btn>
                                <Btn size="sm" variant="danger" onClick={() => void (async () => { try { await api.reviewAdvertiserSubmission(item.id, 'rejected', 'Dokaz ne ispunjava zahteve kampanje.'); await refreshDashboard(); showToast('Dokaz je vraćen korisniku kao odbijen.', 'success') } catch (error) { showToast(error instanceof Error ? error.message : 'Dokaz nije obrađen.', 'error') } })()}>Odbij</Btn>
                              </>}
                            </div> : <p className="mt-4 text-xs text-ink-3">{item.reviewNote || 'Obrađeno'}</p>}
                            {item.userId && <div className="mt-3"><Btn size="sm" variant="secondary" onClick={() => setChatTarget({ taskId: item.taskId, participantId: item.userId! })}>Poruke</Btn></div>}
                          </div>
                        </details>
                      })}
                    </div>
                  </Card>
                  <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-sm text-ink-3">
                    <span>Prikazano {Math.min(visibleEvidenceCount, filteredEvidence.length)} od {filteredEvidence.length} dokaza</span>
                    {visibleEvidenceCount < filteredEvidence.length && <Btn size="sm" variant="secondary" onClick={() => setVisibleEvidenceCount(count => count + 20)}>Prikaži još 20</Btn>}
                  </div>
                </>}
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
                    <div><Input label="Željeni početak prikaza" type="date" min={firstBookableBannerDate()} value={bannerStartDate} onChange={setBannerStartDate} /><p className="mt-1 text-xs text-ink-3">Prikaz počinje izabranog dana u 12:00 po tvom lokalnom vremenu.</p></div>
                    <Input label="Naslov reklame" placeholder="npr. Jesenja ponuda" value={bannerTitle} onChange={setBannerTitle} />
                    <Input label="Link na koji vodi banner (opciono)" placeholder="Dodaj kasnije kada aplikacija bude javna" value={bannerUrl} onChange={setBannerUrl} />
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
                    : <div className="grid gap-3">
                      {ownBanners.map(banner => {
                        const visibility = bannerVisibility(banner)
                        const revisionPending = pendingRevision('banner', banner.id)
                        return <Card key={banner.id} className="p-4 sm:p-5">
                          <div className="flex flex-col gap-4 lg:flex-row lg:items-start">
                            {banner.image_url && <img src={banner.image_url} alt="" className="h-24 w-full rounded-xl border border-frame bg-mint-50 object-contain lg:w-40" />}
                            <div className="min-w-0 flex-1">
                              <div className="flex flex-wrap items-center gap-2">
                                <h3 className="text-base font-bold text-ink">{banner.title}</h3>
                                <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${visibility.className}`}>{visibility.label}</span>
                              </div>
                              <p className="mt-1 text-sm text-ink-2">{banner.slot_title}</p>
                              <p className="mt-2 text-xs text-ink-3">{visibility.detail}</p>
                              <div className="mt-3 grid gap-2 rounded-xl bg-mint-50 p-3 text-sm sm:grid-cols-2 xl:grid-cols-4">
                                <p><span className="block text-xs text-ink-3">Početak</span><strong>{bannerDateTime(banner.starts_at)}</strong></p>
                                <p><span className="block text-xs text-ink-3">Kraj</span><strong>{bannerDateTime(banner.ends_at)}</strong></p>
                                <p><span className="block text-xs text-ink-3">Prikazi</span><strong>{banner.views_count}</strong></p>
                                <p><span className="block text-xs text-ink-3">Zakup</span><strong>{banner.days_count} dana · {platformPublishing ? '0 RSD' : `${new Intl.NumberFormat('sr-RS').format(banner.price_rsd)} RSD`}</strong></p>
                              </div>
                              <div className="mt-3 flex flex-wrap items-center gap-3">
                                {banner.target_url ? <a href={banner.target_url} target="_blank" rel="noopener noreferrer" className="text-sm font-bold text-blue-700 hover:underline">Otvori odredište ↗</a> : <span className="text-xs text-amber-700">Odredište nije postavljeno.</span>}
                                {platformPublishing && visibility.label === 'Zakazano' && <Btn size="sm" disabled={startingBannerId !== null} onClick={() => void startPlatformBannerNow(banner.id)}>{startingBannerId === banner.id ? 'Pokretanje...' : 'Pokreni sada'}</Btn>}
                                {revisionPending ? <span className="text-xs font-semibold text-amber-700">Izmena čeka proveru</span> : ['aktivno', 'active', 'na_cekanju', 'pending'].includes(banner.status) ? <Btn size="sm" variant="secondary" onClick={() => setBannerEdit({ id: banner.id, title: banner.title, body: banner.body || '', image_url: banner.image_url || '', target_url: banner.target_url || '' })}>Uredi baner</Btn> : null}
                              </div>
                              {banner.target_url && <p className="mt-2 break-all text-xs text-ink-3">{banner.target_url}</p>}
                              {banner.admin_note && <details className="mt-3 text-xs text-ink-2"><summary className="cursor-pointer font-semibold">Napomena administratora</summary><p className="mt-1">{banner.admin_note}</p></details>}
                            </div>
                          </div>
                        </Card>
                      })}
                    </div>}
                  {bannerEdit && <Card className="mt-5 space-y-4 border-blue-200 p-5">
                    <div><h3 className="font-bold text-ink">Uredi postojeći banner</h3><p className="mt-1 text-sm text-ink-2">Pozicija, cena i trajanje ostaju isti. Ako je banner već aktivan, stara verzija ostaje javna dok admin ne odobri novu.</p></div>
                    <div className="grid gap-3 sm:grid-cols-2"><Input label="Naslov" value={bannerEdit.title} onChange={value => setBannerEdit(current => current ? { ...current, title: value } : null)} /><Input label="Link (opciono)" value={bannerEdit.target_url} onChange={value => setBannerEdit(current => current ? { ...current, target_url: value } : null)} /><Input label="Kratak opis" value={bannerEdit.body} onChange={value => setBannerEdit(current => current ? { ...current, body: value } : null)} /><Input label="URL slike (opciono)" value={bannerEdit.image_url} onChange={value => setBannerEdit(current => current ? { ...current, image_url: value } : null)} /></div>
                    {bannerEdit.image_url && <img src={bannerEdit.image_url} alt="Pregled izmene bannera" className="max-h-44 w-full rounded-lg border border-frame object-contain" />}
                    <label className="block text-sm font-semibold text-ink-2">Otpremi novu sliku<input type="file" accept="image/jpeg,image/png,image/webp" disabled={bannerUploading} onChange={event => void uploadBannerEdit(event.target.files?.[0])} className="mt-2 block w-full text-sm font-normal" /></label>
                    <div className="flex flex-wrap gap-2"><Btn disabled={contentSaving || bannerUploading || bannerEdit.title.trim().length < 3} onClick={() => void saveBannerEdit()}>{contentSaving ? 'Slanje...' : 'Pošalji izmenu adminu'}</Btn><Btn variant="secondary" onClick={() => setBannerEdit(null)}>Otkaži</Btn></div>
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
