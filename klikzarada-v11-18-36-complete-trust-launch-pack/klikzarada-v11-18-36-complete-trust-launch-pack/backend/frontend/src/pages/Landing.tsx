import { useEffect, useRef, useState } from 'react'
import { Btn, Card } from '../components/ui'
import { api, type PaidBanner, type PublicOverview, type Task } from '../lib/api'

const categoryIcons: Record<string, string> = {
  'Ankete i testiranja': '📝',
  'Testiranje sajta ili aplikacije': '🧪',
  'Provera podataka': '🔎',
  'Kratak feedback': '💬',
  'Lokalna provera': '📍',
  'Označavanje podataka': '🏷️',
}

const userSteps = [
  ['01', 'Odaberi zadatak', 'Vidiš nagradu, dokaz i procenjeno vreme pre početka.'],
  ['02', 'Uradi ga pažljivo', 'Timer i provera aktivnosti štite i korisnike i oglašivače.'],
  ['03', 'Pošalji dokaz', 'Prilažeš traženi dokaz; nagrada ne ide automatski.'],
  ['04', 'Sačekaj odobrenje', 'Odobren rezultat ulazi u raspoloživ saldo za PayPal isplatu.'],
]

const faqs = [
  ['Kada dobijam nagradu?', 'Nagrada prvo odlazi na čekanje. Oglašivač proverava poslati dokaz, a posle odobrenja prelazi u raspoloživ saldo.'],
  ['Ko proverava dokaz?', 'Dokaz proverava oglašivač koji je postavio zadatak. Admin rešava prijavljene sporove, sumnjive aktivnosti i pitanja bezbednosti.'],
  ['Kada mogu da zatražim isplatu?', 'Kada dostigneš minimalni iznos prikazan u novčaniku i sačuvaš svoju PayPal email adresu za isplatu.'],
  ['Da li je registracija besplatna?', 'Da. Korisnik ne plaća registraciju ni pregled aktivnih zadataka.'],
  ['Kako oglašivač plaća?', 'Oglašivač dopunjuje budžet preko PayPal Checkout-a. Budžet se troši samo za odobrene rezultate, a banner i VIP zakup imaju jasno trajanje.'],
]

function BannerCard({ banner }: { banner: PaidBanner }) {
  const cardRef = useRef<HTMLAnchorElement>(null)

  useEffect(() => {
    const node = cardRef.current
    if (!node || !('IntersectionObserver' in window)) return
    let recorded = false
    const observer = new IntersectionObserver(entries => {
      if (!recorded && entries.some(entry => entry.isIntersecting && entry.intersectionRatio >= 0.5)) {
        recorded = true
        void api.recordBannerImpression(banner.id).catch(() => undefined)
        observer.disconnect()
      }
    }, { threshold: 0.5 })
    observer.observe(node)
    return () => observer.disconnect()
  }, [banner.id])

  return (
    <a
      ref={cardRef}
      href={banner.target_url || '#'}
      target="_blank"
      rel="noopener noreferrer sponsored"
      className="group block rounded-2xl border border-blue-200 bg-gradient-to-br from-blue-50 via-white to-violet-50 p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:border-blue-400 hover:shadow-md"
    >
      <div className="flex items-start gap-3">
        {banner.image_url
          ? <img src={banner.image_url} alt="" className="h-12 w-12 shrink-0 rounded-xl border border-blue-100 object-cover" />
          : <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-600 text-lg text-white">↗</span>}
        <div className="min-w-0">
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-blue-700">Sponzorisano</p>
          <h3 className="mt-1 font-bold text-ink group-hover:text-blue-700">{banner.title}</h3>
          {banner.body && <p className="mt-1 line-clamp-2 text-sm text-ink-2">{banner.body}</p>}
          <p className="mt-3 text-xs font-bold text-blue-700">Otvori ponudu →</p>
        </div>
      </div>
    </a>
  )
}

export default function Landing({ onNavigate }: { onNavigate: (id: string) => void }) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [banners, setBanners] = useState<PaidBanner[]>([])
  const [tasks, setTasks] = useState<Task[]>([])
  const [overview, setOverview] = useState<PublicOverview | null>(null)
  const [loading, setLoading] = useState(true)
  const [dailyMinutes, setDailyMinutes] = useState(15)
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [faqOpen, setFaqOpen] = useState<number | null>(0)
  const [waitlistEmail, setWaitlistEmail] = useState('')
  const [waitlistMessage, setWaitlistMessage] = useState('')
  const [waitlistSaving, setWaitlistSaving] = useState(false)

  useEffect(() => {
    let active = true
    void Promise.all([api.publicBanners(), api.publicTasks(), api.publicOverview()])
      .then(([bannerData, taskData, overviewData]) => {
        if (!active) return
        setBanners(bannerData.banners)
        setTasks(taskData.tasks)
        setOverview(overviewData)
      })
      .catch(() => {
        if (!active) return
        setBanners([])
        setTasks([])
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [])

  const bannersFor = (...codes: string[]) => banners.filter(banner => banner.slot_code !== null && codes.includes(banner.slot_code))
  const topBanners = bannersFor('home_top_left', 'home_top_right')
  const sponsorBanners = bannersFor('home_sponsor_1', 'home_sponsor_2', 'home_sponsor_3', 'home_sponsor_4')
  const dashboardBanners = bannersFor('home_dashboard_banner')
  const bottomBanners = bannersFor('home_bottom_1', 'home_bottom_2', 'home_bottom_3')
  const categorySummary = Object.entries(tasks.reduce<Record<string, number>>((summary, task) => {
    summary[task.category] = (summary[task.category] ?? 0) + 1
    return summary
  }, {})).sort(([left], [right]) => left.localeCompare(right, 'sr'))
  const featuredTasks = [...tasks].sort((left, right) => Number(right.featured) - Number(left.featured) || right.reward_rsd - left.reward_rsd).slice(0, 3)
  const newestTasks = [...tasks].sort((left, right) => Date.parse(right.created_at || '1970-01-01') - Date.parse(left.created_at || '1970-01-01')).slice(0, 3)
  const closingTasks = [...tasks].filter(task => {
    const remaining = task.total_slots - task.used_slots
    return remaining > 0 && remaining <= Math.max(3, Math.ceil(task.total_slots * 0.1))
  }).sort((left, right) => (left.total_slots - left.used_slots) - (right.total_slots - right.used_slots)).slice(0, 3)
  const selectedTasks = selectedCategory ? tasks.filter(task => task.category === selectedCategory).slice(0, 3) : featuredTasks
  const averageRsdPerMinute = tasks.length ? tasks.reduce((total, task) => total + task.reward_rsd / Math.max(task.estimated_minutes, 1), 0) / tasks.length : 0
  const estimatedMonthlyEarnings = Math.round(averageRsdPerMinute * dailyMinutes * 22)
  const formatRsd = (amount: number) => `${amount.toLocaleString('sr-RS')} RSD`

  const joinWaitlist = async () => {
    setWaitlistMessage('')
    setWaitlistSaving(true)
    try {
      const result = await api.joinWaitlist(waitlistEmail)
      setWaitlistMessage(result.already_registered ? 'Ova adresa je već prijavljena.' : 'Prijava je sačuvana. Poslaćemo obaveštenje kada aktiviramo email slanje.')
      if (!result.already_registered) setWaitlistEmail('')
    } catch (error) {
      setWaitlistMessage(error instanceof Error ? error.message : 'Prijava trenutno nije sačuvana.')
    } finally {
      setWaitlistSaving(false)
    }
  }

  return (
    <div className="min-h-screen bg-mint-50 text-ink">
      <nav className="sticky top-0 z-50 border-b border-frame bg-white/95 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center gap-4 px-4">
          <button onClick={() => onNavigate('home')} className="flex items-center gap-2 rounded-lg font-bold text-ink transition-colors hover:text-blue-700">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-600 text-sm text-white shadow-sm">K</span>
            <span>KlikZarada</span>
          </button>
          <div className="flex-1" />
          <div className="hidden items-center gap-1 md:flex">
            <button onClick={() => onNavigate('tasks-public')} className="rounded-lg px-3 py-2 text-sm font-semibold text-ink-2 transition-colors hover:bg-mint-100 hover:text-ink">Zadaci</button>
            <button onClick={() => onNavigate('advertiser-register')} className="rounded-lg px-3 py-2 text-sm font-semibold text-ink-2 transition-colors hover:bg-mint-100 hover:text-ink">Oglašavanje</button>
            <button onClick={() => onNavigate('login')} className="rounded-lg px-3 py-2 text-sm font-semibold text-ink-2 transition-colors hover:bg-mint-100 hover:text-ink">Prijava</button>
            <Btn onClick={() => onNavigate('register')} size="sm">Pokreni zaradu</Btn>
          </div>
          <button onClick={() => setMobileMenuOpen(open => !open)} className="rounded-lg p-2 text-xl text-ink-2 md:hidden" aria-label="Otvori meni">☰</button>
        </div>
        {mobileMenuOpen && (
          <div className="border-t border-frame bg-white px-4 py-3 md:hidden">
            <div className="mx-auto flex max-w-6xl flex-col gap-2">
              <button onClick={() => { onNavigate('tasks-public'); setMobileMenuOpen(false) }} className="rounded-lg px-3 py-2 text-left font-semibold text-ink">Zadaci</button>
              <button onClick={() => { onNavigate('advertiser-register'); setMobileMenuOpen(false) }} className="rounded-lg px-3 py-2 text-left font-semibold text-ink">Oglašavanje</button>
              <Btn onClick={() => onNavigate('register')} className="justify-center">Pokreni zaradu</Btn>
            </div>
          </div>
        )}
      </nav>

      <main>
        <section className="overflow-hidden border-b border-blue-100 bg-[radial-gradient(circle_at_top_right,_#dbeafe,_transparent_38%),linear-gradient(135deg,#f7fdf9_0%,#eff9f3_52%,#eef5ff_100%)]">
          <div className="mx-auto grid max-w-6xl gap-10 px-4 py-16 md:py-24 lg:grid-cols-[1.2fr_.8fr] lg:items-center">
            <div>
              <span className="inline-flex rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-700">Platforma za proverljive mikro-zadatke</span>
              <h1 className="mt-5 max-w-3xl text-4xl font-extrabold leading-[1.06] tracking-tight text-ink md:text-6xl">
                Zaradi na stvarnom radu.<br /><span className="text-blue-600">Bez prečica i bez praznih obećanja.</span>
              </h1>
              <p className="mt-6 max-w-2xl text-lg leading-8 text-ink-2">
                Biraj zadatke sa jasnim dokazom, pošalji rezultat i prati stanje nagrade pre PayPal isplate. Oglašivači plaćaju samo odobrene rezultate.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Btn onClick={() => onNavigate('register')} size="lg">Pogledaj kako se zarađuje →</Btn>
                <Btn onClick={() => onNavigate('advertiser-register')} variant="secondary" size="lg">Objavi zadatak ili banner</Btn>
              </div>
              <div className="mt-9 grid max-w-xl grid-cols-3 gap-3">
                <div className="rounded-xl border border-emerald-200 bg-white/80 p-3"><p className="font-mono text-2xl font-bold text-emerald-700">{loading ? '—' : overview?.active_tasks ?? tasks.length}</p><p className="mt-1 text-xs font-semibold text-ink-2">dostupnih zadataka</p></div>
                <div className="rounded-xl border border-blue-200 bg-white/80 p-3"><p className="font-mono text-2xl font-bold text-blue-700">{loading ? '—' : overview?.categories ?? categorySummary.length}</p><p className="mt-1 text-xs font-semibold text-ink-2">kategorija rada</p></div>
                <div className="rounded-xl border border-violet-200 bg-white/80 p-3"><p className="font-mono text-2xl font-bold text-violet-700">{loading ? '—' : overview?.approved_results ?? 0}</p><p className="mt-1 text-xs font-semibold text-ink-2">odobrenih rezultata</p></div>
              </div>
            </div>
            <Card className="relative overflow-hidden border-blue-200 p-6 shadow-lg">
              <div className="absolute right-0 top-0 h-28 w-28 rounded-bl-full bg-blue-100" />
              <p className="relative text-xs font-bold uppercase tracking-[0.16em] text-blue-700">Ovako izgleda zadatak</p>
              {featuredTasks[0] ? <>
                <div className="relative mt-4 flex items-start justify-between gap-3"><span className="rounded-full bg-blue-50 px-2.5 py-1 text-[11px] font-bold text-blue-700">{featuredTasks[0].category}</span><span className="font-mono text-lg font-bold text-emerald-700">{formatRsd(featuredTasks[0].reward_rsd)}</span></div>
                <h2 className="relative mt-4 text-xl font-extrabold text-ink">{featuredTasks[0].title}</h2>
                <div className="relative mt-5 grid grid-cols-2 gap-3 text-sm"><div className="rounded-xl bg-mint-50 p-3"><p className="text-[10px] font-bold uppercase tracking-wide text-ink-3">Vreme</p><p className="mt-1 font-bold text-ink">oko {featuredTasks[0].estimated_minutes} min</p></div><div className="rounded-xl bg-mint-50 p-3"><p className="text-[10px] font-bold uppercase tracking-wide text-ink-3">Dokaz</p><p className="mt-1 font-bold text-ink">obavezan</p></div></div>
                <button onClick={() => onNavigate('tasks-public')} className="relative mt-6 text-sm font-bold text-blue-700 hover:text-blue-800">Pogledaj detalje zadatka →</button>
              </> : <><h2 className="relative mt-3 text-2xl font-extrabold text-ink">Nagrada nikad ne ide na slepo.</h2><p className="relative mt-4 text-sm leading-6 text-ink-2">Čim se odobri prvi zadatak, ovde će se pojaviti stvaran primer sa nagradom, trajanjem i potrebnim dokazom.</p><button onClick={() => onNavigate('advertiser-register')} className="relative mt-6 text-sm font-bold text-blue-700 hover:text-blue-800">Objavi prvi zadatak →</button></>}
            </Card>
          </div>
        </section>

        {topBanners.length > 0 && <section className="border-b border-frame bg-white"><div className="mx-auto max-w-6xl px-4 py-7"><p className="mb-3 text-[10px] font-bold uppercase tracking-[0.16em] text-ink-3">Izdvojene ponude</p><div className="grid gap-4 md:grid-cols-2">{topBanners.map(banner => <BannerCard key={banner.id} banner={banner} />)}</div></div></section>}

        <section className="mx-auto max-w-6xl px-4 py-16">
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
            <div><p className="text-xs font-bold uppercase tracking-[0.16em] text-emerald-700">Aktuelno</p><h2 className="mt-2 text-3xl font-extrabold text-ink">Dostupni zadaci</h2><p className="mt-2 text-ink-2">Prikazujemo samo aktivne zadatke sa slobodnim mestima.</p></div>
            <Btn onClick={() => onNavigate('tasks-public')} variant="secondary">Svi zadaci →</Btn>
          </div>
          {loading ? <div className="py-12 text-sm text-ink-2">Učitavanje zadataka...</div> : featuredTasks.length === 0 ? (
            <Card className="mt-7 border-dashed p-8 text-center"><p className="text-lg font-bold text-ink">Trenutno nema odobrenih zadataka.</p><p className="mt-2 text-sm text-ink-2">Oglašivači mogu prvi objaviti proverljiv zadatak, a korisnici će ga videti čim prođe moderaciju.</p><Btn onClick={() => onNavigate('advertiser-register')} className="mt-5">Objavi prvi zadatak</Btn></Card>
          ) : <div className="mt-7 grid gap-4 md:grid-cols-3">{featuredTasks.map(task => <Card key={task.id} className="flex flex-col p-5"><div className="flex items-center justify-between gap-3"><span className="rounded-full bg-blue-50 px-2.5 py-1 text-[11px] font-bold text-blue-700">{task.category}</span><span className="font-mono text-lg font-bold text-emerald-700">{formatRsd(task.reward_rsd)}</span></div><h3 className="mt-4 text-lg font-bold text-ink">{task.title}</h3><p className="mt-2 line-clamp-2 text-sm leading-6 text-ink-2">{task.description}</p><div className="mt-5 flex items-center justify-between border-t border-frame pt-4 text-xs font-semibold text-ink-3"><span>oko {task.estimated_minutes} min</span><span>{task.total_slots - task.used_slots} slobodno</span></div><Btn onClick={() => onNavigate('tasks-public')} className="mt-4 justify-center">Detalji zadatka</Btn></Card>)}</div>}
        </section>

        {(newestTasks.length > 0 || closingTasks.length > 0) && <section className="border-y border-frame bg-white">
          <div className="mx-auto grid max-w-6xl gap-8 px-4 py-14 lg:grid-cols-2">
            <div><div className="flex items-end justify-between gap-4"><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-blue-700">Sveže objavljeno</p><h2 className="mt-2 text-2xl font-extrabold text-ink">Najnoviji zadaci</h2></div><button onClick={() => onNavigate('tasks-public')} className="text-sm font-bold text-blue-700">Svi zadaci →</button></div><div className="mt-5 space-y-3">{newestTasks.map(task => <button key={task.id} onClick={() => onNavigate('tasks-public')} className="flex w-full items-center justify-between gap-4 rounded-xl border border-frame bg-mint-50 p-4 text-left transition-all hover:border-blue-300 hover:bg-blue-50"><div className="min-w-0"><p className="truncate font-bold text-ink">{task.title}</p><p className="mt-1 text-xs text-ink-2">{task.category} · oko {task.estimated_minutes} min</p></div><span className="shrink-0 font-mono text-sm font-bold text-emerald-700">{formatRsd(task.reward_rsd)}</span></button>)}</div></div>
            <div><div className="flex items-end justify-between gap-4"><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-orange-700">Ograničen broj mesta</p><h2 className="mt-2 text-2xl font-extrabold text-ink">Uskoro popunjeni</h2></div><button onClick={() => onNavigate('tasks-public')} className="text-sm font-bold text-blue-700">Pogledaj →</button></div><div className="mt-5 space-y-3">{closingTasks.length ? closingTasks.map(task => <button key={task.id} onClick={() => onNavigate('tasks-public')} className="flex w-full items-center justify-between gap-4 rounded-xl border border-orange-200 bg-orange-50/60 p-4 text-left transition-all hover:border-orange-300"><div className="min-w-0"><p className="truncate font-bold text-ink">{task.title}</p><p className="mt-1 text-xs text-ink-2">Preostalo {task.total_slots - task.used_slots} mesta</p></div><span className="shrink-0 font-mono text-sm font-bold text-emerald-700">{formatRsd(task.reward_rsd)}</span></button>) : <Card className="border-dashed p-5"><p className="font-bold text-ink">Nijedan aktivan zadatak nije pred popunjavanjem.</p><p className="mt-1 text-sm text-ink-2">Kada broj slobodnih mesta bude mali, biće prikazani ovde.</p></Card>}</div></div>
          </div>
        </section>}

        <section className="bg-[linear-gradient(135deg,#f0fdf4_0%,#eff6ff_100%)]">
          <div className="mx-auto grid max-w-6xl gap-8 px-4 py-16 lg:grid-cols-[1fr_.9fr] lg:items-center">
            <div><p className="text-xs font-bold uppercase tracking-[0.16em] text-emerald-700">Realna procena</p><h2 className="mt-2 text-3xl font-extrabold text-ink">Koliko vremena želiš da odvojiš?</h2><p className="mt-3 max-w-xl leading-7 text-ink-2">Procena koristi prosečnu nagradu i vreme trenutno aktivnih zadataka. Nije obećanje zarade i menja se sa ponudom poslova.</p><div className="mt-6 flex flex-wrap gap-2">{[10, 15, 30, 60].map(minutes => <button key={minutes} onClick={() => setDailyMinutes(minutes)} className={`rounded-full border px-4 py-2 text-sm font-bold transition-colors ${dailyMinutes === minutes ? 'border-blue-600 bg-blue-600 text-white' : 'border-frame bg-white text-ink hover:border-blue-300'}`}>{minutes} min dnevno</button>)}</div></div>
            <Card className="border-emerald-200 p-6 shadow-sm"><p className="text-xs font-bold uppercase tracking-[0.16em] text-ink-3">Okvirno za 22 dana</p><p className="mt-3 font-mono text-4xl font-bold text-emerald-700">{tasks.length ? formatRsd(estimatedMonthlyEarnings) : '—'}</p><p className="mt-2 text-sm leading-6 text-ink-2">{tasks.length ? `Na osnovu ${tasks.length} trenutno aktivnih zadataka i ${dailyMinutes} minuta rada dnevno.` : 'Procena će se pojaviti kada budu dostupni aktivni zadaci.'}</p><div className="mt-5 border-t border-frame pt-4 text-xs text-ink-3">Prosečno trajanje zadatka: {overview?.average_minutes ? `oko ${overview.average_minutes} min` : 'biće dostupno uskoro'}.</div></Card>
          </div>
        </section>

        {categorySummary.length > 0 && <section className="border-y border-frame bg-white"><div className="mx-auto max-w-6xl px-4 py-14"><div className="flex items-center justify-between gap-4"><div><h2 className="text-2xl font-extrabold text-ink">Vrste posla</h2><p className="mt-1 text-sm text-ink-2">Sve kategorije su određene stvarno dostupnim zadacima.</p></div><button onClick={() => onNavigate('tasks-public')} className="text-sm font-bold text-blue-700">Filtriraj zadatke →</button></div><div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">{categorySummary.map(([category, count]) => <button key={category} onClick={() => onNavigate('tasks-public')} className="rounded-xl border border-frame bg-mint-50 p-4 text-left transition-all hover:-translate-y-0.5 hover:border-blue-300 hover:bg-blue-50"><span className="text-2xl">{categoryIcons[category] ?? '📌'}</span><p className="mt-3 text-sm font-bold leading-5 text-ink">{category}</p><p className="mt-2 font-mono text-xs text-emerald-700">{count} aktivno</p></button>)}</div></div></section>}

        {categorySummary.length > 0 && <section className="mx-auto max-w-6xl px-4 py-16"><div className="grid gap-8 lg:grid-cols-[.8fr_1.2fr]"><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-violet-700">Po interesovanju</p><h2 className="mt-2 text-3xl font-extrabold text-ink">Pronađi posao koji ti odgovara.</h2><p className="mt-3 leading-7 text-ink-2">Odaberi oblast i pogledaj trenutno dostupne zadatke. Kada napraviš nalog, interesovanja možeš dopuniti i u profilu.</p><div className="mt-6 flex flex-wrap gap-2"><button onClick={() => setSelectedCategory(null)} className={`rounded-full px-3 py-1.5 text-sm font-bold ${selectedCategory === null ? 'bg-violet-600 text-white' : 'bg-violet-50 text-violet-700 hover:bg-violet-100'}`}>Sve preporuke</button>{categorySummary.map(([category]) => <button key={category} onClick={() => setSelectedCategory(category)} className={`rounded-full px-3 py-1.5 text-sm font-bold ${selectedCategory === category ? 'bg-violet-600 text-white' : 'bg-violet-50 text-violet-700 hover:bg-violet-100'}`}>{category}</button>)}</div></div><div className="grid gap-3">{selectedTasks.map(task => <Card key={task.id} className="flex items-center justify-between gap-4 p-4"><div><p className="text-xs font-bold text-violet-700">{task.category}</p><p className="mt-1 font-bold text-ink">{task.title}</p><p className="mt-1 text-sm text-ink-2">oko {task.estimated_minutes} min · dokaz obavezan</p></div><div className="text-right"><p className="font-mono font-bold text-emerald-700">{formatRsd(task.reward_rsd)}</p><button onClick={() => onNavigate('tasks-public')} className="mt-2 text-xs font-bold text-blue-700">Detalji →</button></div></Card>)}</div></div></section>}

        {sponsorBanners.length > 0 && <section className="mx-auto max-w-6xl px-4 py-14"><div className="mb-5 flex items-center justify-between"><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-violet-700">Zakup reklame</p><h2 className="mt-2 text-2xl font-extrabold text-ink">Sponzorisane ponude</h2></div><button onClick={() => onNavigate('advertiser-register')} className="text-sm font-bold text-blue-700">Zakupljivanje pozicije →</button></div><div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{sponsorBanners.map(banner => <BannerCard key={banner.id} banner={banner} />)}</div></section>}

        <section className="border-y border-frame bg-blue-50/60"><div className="mx-auto max-w-6xl px-4 py-16"><div className="grid gap-10 lg:grid-cols-[.9fr_1.1fr]"><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-blue-700">Za korisnike</p><h2 className="mt-2 text-3xl font-extrabold text-ink">Od zadatka do odobrene nagrade.</h2><p className="mt-4 max-w-md leading-7 text-ink-2">Nema plaćenog klika, automatskog kredita ili obećanja bez provere. Svaki korak ostavlja trag koji admin može da proveri.</p><Btn onClick={() => onNavigate('register')} className="mt-7">Napravi besplatan nalog</Btn></div><div className="grid gap-3 sm:grid-cols-2">{userSteps.map(([step, title, description]) => <Card key={step} className="p-5"><p className="font-mono text-xs font-bold text-blue-600">{step}</p><h3 className="mt-3 font-bold text-ink">{title}</h3><p className="mt-2 text-sm leading-6 text-ink-2">{description}</p></Card>)}</div></div></div></section>

        <section className="mx-auto max-w-6xl px-4 py-16"><div className="overflow-hidden rounded-3xl border border-emerald-200 bg-gradient-to-br from-emerald-50 via-white to-blue-50 p-7 md:p-10"><div className="grid gap-8 lg:grid-cols-[1.1fr_.9fr] lg:items-center"><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-emerald-700">Za oglašivače</p><h2 className="mt-2 text-3xl font-extrabold text-ink">Objavi merljiv posao ili zakup banner pozicije.</h2><p className="mt-4 max-w-xl leading-7 text-ink-2">Definiši nagradu, dokaz i publiku. Kampanja ide na moderaciju, a budžet se troši samo za odobrene rezultate. Banner zakup ima tačno određenu poziciju i trajanje.</p><div className="mt-7 flex flex-wrap gap-3"><Btn onClick={() => onNavigate('advertiser-register')}>Kreiraj kampanju</Btn><Btn onClick={() => onNavigate('advertiser-login')} variant="secondary">Uđi u oglašivački panel</Btn></div></div><div className="grid gap-3"><Card className="p-4"><p className="font-bold text-ink">01. Zadatak sa dokazom</p><p className="mt-1 text-sm text-ink-2">Anketa, testiranje, provera podataka ili feedback.</p></Card><Card className="p-4"><p className="font-bold text-ink">02. Admin moderacija</p><p className="mt-1 text-sm text-ink-2">Pregled cilja, teksta, budžeta i bezbednosti kampanje.</p></Card><Card className="p-4"><p className="font-bold text-ink">03. Rezultat koji možeš da proveriš</p><p className="mt-1 text-sm text-ink-2">Statusi, dokazi i potrošnja budžeta ostaju u panelu.</p></Card></div></div></div></section>

        <section className="border-y border-frame bg-slate-950 text-white"><div className="mx-auto max-w-6xl px-4 py-16"><div className="max-w-2xl"><p className="text-xs font-bold uppercase tracking-[0.16em] text-emerald-300">Jasni modeli oglašavanja</p><h2 className="mt-2 text-3xl font-extrabold">Odaberi vidljivost koja odgovara cilju.</h2><p className="mt-3 leading-7 text-slate-300">Cene, slobodni termini i završni iznos uvek se vide pre rezervacije. Nema automatskog produžavanja ni skrivene potrošnje.</p></div><div className="mt-8 grid gap-4 md:grid-cols-3"><div className="rounded-2xl border border-white/15 bg-white/5 p-6"><p className="text-sm font-bold text-emerald-300">Mikro-zadatak</p><h3 className="mt-3 text-xl font-extrabold">Plati rezultat</h3><p className="mt-3 text-sm leading-6 text-slate-300">Postavi nagradu, potreban dokaz i broj izvršenja. Budžet se troši samo kada odobriš validan dokaz.</p></div><div className="rounded-2xl border border-blue-300/50 bg-blue-500/10 p-6"><p className="text-sm font-bold text-blue-200">Prioritetni prikaz</p><h3 className="mt-3 text-xl font-extrabold">Budi vidljiviji</h3><p className="mt-3 text-sm leading-6 text-slate-300">Istakni kampanju na listi tokom izabranog perioda. Sponzorisana oznaka ostaje vidljiva korisnicima.</p></div><div className="rounded-2xl border border-violet-300/50 bg-violet-500/10 p-6"><p className="text-sm font-bold text-violet-200">Banner zakup</p><h3 className="mt-3 text-xl font-extrabold">Zauzmi poziciju</h3><p className="mt-3 text-sm leading-6 text-slate-300">Odaberi mesto na početnoj, trajanje od 1 do 31 dana i pošalji kreativu na odobrenje.</p></div></div><Btn onClick={() => onNavigate('advertiser-register')} variant="success" className="mt-8">Pogledaj kampanje i pozicije →</Btn></div></section>

        <section className="mx-auto grid max-w-6xl gap-8 px-4 py-16 lg:grid-cols-[1fr_.9fr] lg:items-start"><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-blue-700">Česta pitanja</p><h2 className="mt-2 text-3xl font-extrabold text-ink">Sve jasno pre prve prijave.</h2><div className="mt-6 divide-y divide-frame rounded-2xl border border-frame bg-white">{faqs.map(([question, answer], index) => <div key={question}><button onClick={() => setFaqOpen(faqOpen === index ? null : index)} className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left font-bold text-ink"><span>{question}</span><span className="text-xl text-blue-600">{faqOpen === index ? '−' : '+'}</span></button>{faqOpen === index && <p className="px-5 pb-5 text-sm leading-6 text-ink-2">{answer}</p>}</div>)}</div></div><Card className="border-blue-200 bg-blue-50/70 p-7"><p className="text-xs font-bold uppercase tracking-[0.16em] text-blue-700">Prvi želiš da saznaš</p><h2 className="mt-2 text-2xl font-extrabold text-ink">Obavesti me kada stignu novi zadaci.</h2><p className="mt-3 text-sm leading-6 text-ink-2">Ostavi email samo ako želiš obaveštenje o novim aktivnim zadacima. Ne šaljemo promotivne poruke bez tvoje prijave.</p><form onSubmit={event => { event.preventDefault(); void joinWaitlist() }} className="mt-5 flex flex-col gap-3 sm:flex-row"><input type="email" required value={waitlistEmail} onChange={event => setWaitlistEmail(event.target.value)} placeholder="tvoj@email.com" className="min-w-0 flex-1 rounded-lg border border-blue-200 bg-white px-3 py-2.5 text-sm text-ink outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" /><Btn type="submit" disabled={waitlistSaving} className="justify-center">{waitlistSaving ? 'Čuvanje...' : 'Prijavi me'}</Btn></form>{waitlistMessage && <p className="mt-3 text-sm font-medium text-blue-800" role="status">{waitlistMessage}</p>}</Card></section>

        {dashboardBanners.length > 0 && <section className="border-y border-frame bg-white"><div className="mx-auto max-w-6xl px-4 py-10"><div className="grid gap-4">{dashboardBanners.map(banner => <BannerCard key={banner.id} banner={banner} />)}</div></div></section>}
        {bottomBanners.length > 0 && <section className="mx-auto max-w-6xl px-4 py-12"><div className="grid gap-4 md:grid-cols-3">{bottomBanners.map(banner => <BannerCard key={banner.id} banner={banner} />)}</div></section>}
      </main>

      <footer className="border-t border-frame bg-white"><div className="mx-auto grid max-w-6xl gap-8 px-4 py-10 md:grid-cols-[1.3fr_1fr_1fr]"><div><div className="flex items-center gap-2 font-bold text-ink"><span className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-xs text-white">K</span>KlikZarada</div><p className="mt-3 max-w-sm text-sm leading-6 text-ink-2">Platforma za proverljiv digitalni rad i kampanje sa jasnim pravilima, dokazima i moderacijom.</p></div><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-ink-3">Platforma</p><div className="mt-3 flex flex-col items-start gap-2"><button onClick={() => onNavigate('tasks-public')} className="text-sm text-ink-2 hover:text-blue-700">Aktivni zadaci</button><button onClick={() => onNavigate('register')} className="text-sm text-ink-2 hover:text-blue-700">Registracija korisnika</button><button onClick={() => onNavigate('advertiser-register')} className="text-sm text-ink-2 hover:text-blue-700">Oglašavanje i banneri</button></div></div><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-ink-3">Važno</p><p className="mt-3 text-sm leading-6 text-ink-2">Nagrade se odobravaju nakon provere dokaza. Isplate se vrše preko PayPal adrese koju korisnik sačuva u svom profilu.</p><button onClick={() => onNavigate('legal')} className="mt-3 text-sm font-semibold text-blue-700 hover:text-blue-800">Uslovi, privatnost i zabranjeni sadržaji</button></div></div><div className="border-t border-frame"><div className="mx-auto flex max-w-6xl flex-col justify-between gap-2 px-4 py-5 text-xs text-ink-3 sm:flex-row"><span>© 2026 KlikZarada. Sva prava zadržana.</span><span>Proverljiv rad. Jasna pravila. Odgovorno oglašavanje.</span></div></div></footer>
    </div>
  )
}
