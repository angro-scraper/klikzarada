import { useEffect, useState } from 'react'
import { Btn, Card } from '../components/ui'
import { api, type PaidBanner, type Task } from '../lib/api'

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

function BannerCard({ banner }: { banner: PaidBanner }) {
  return (
    <a
      href={banner.target_url || '#'}
      target="_blank"
      rel="noopener noreferrer sponsored"
      className="group block rounded-2xl border border-blue-200 bg-gradient-to-br from-blue-50 via-white to-violet-50 p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:border-blue-400 hover:shadow-md"
    >
      <div className="flex items-start gap-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-600 text-lg text-white">↗</span>
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
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    void Promise.all([api.publicBanners(), api.publicTasks()])
      .then(([bannerData, taskData]) => {
        if (!active) return
        setBanners(bannerData.banners)
        setTasks(taskData.tasks)
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
  const formatRsd = (amount: number) => `${amount.toLocaleString('sr-RS')} RSD`

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
                <div className="rounded-xl border border-emerald-200 bg-white/80 p-3"><p className="font-mono text-2xl font-bold text-emerald-700">{loading ? '—' : tasks.length}</p><p className="mt-1 text-xs font-semibold text-ink-2">dostupnih zadataka</p></div>
                <div className="rounded-xl border border-blue-200 bg-white/80 p-3"><p className="font-mono text-2xl font-bold text-blue-700">{loading ? '—' : categorySummary.length}</p><p className="mt-1 text-xs font-semibold text-ink-2">kategorija rada</p></div>
                <div className="rounded-xl border border-violet-200 bg-white/80 p-3"><p className="font-mono text-2xl font-bold text-violet-700">100%</p><p className="mt-1 text-xs font-semibold text-ink-2">provera dokaza</p></div>
              </div>
            </div>
            <Card className="relative overflow-hidden border-blue-200 p-6 shadow-lg">
              <div className="absolute right-0 top-0 h-28 w-28 rounded-bl-full bg-blue-100" />
              <p className="relative text-xs font-bold uppercase tracking-[0.16em] text-blue-700">Kako ostajemo bezbedni</p>
              <h2 className="relative mt-3 text-2xl font-extrabold text-ink">Nagrada nikad ne ide na slepo.</h2>
              <div className="relative mt-6 space-y-4">
                {[
                  ['01', 'Zadatak ima jasna pravila i potreban dokaz.'],
                  ['02', 'Timer i aktivnost sprečavaju automatsko izvršavanje.'],
                  ['03', 'Nagrada prvo čeka proveru, zatim ulazi u saldo.'],
                ].map(([number, text]) => <div key={number} className="flex gap-3"><span className="font-mono text-sm font-bold text-blue-600">{number}</span><p className="text-sm leading-6 text-ink-2">{text}</p></div>)}
              </div>
              <button onClick={() => onNavigate('tasks-public')} className="relative mt-6 text-sm font-bold text-blue-700 hover:text-blue-800">Pregledaj pravila kroz zadatke →</button>
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

        {categorySummary.length > 0 && <section className="border-y border-frame bg-white"><div className="mx-auto max-w-6xl px-4 py-14"><div className="flex items-center justify-between gap-4"><div><h2 className="text-2xl font-extrabold text-ink">Vrste posla</h2><p className="mt-1 text-sm text-ink-2">Sve kategorije su određene stvarno dostupnim zadacima.</p></div><button onClick={() => onNavigate('tasks-public')} className="text-sm font-bold text-blue-700">Filtriraj zadatke →</button></div><div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">{categorySummary.map(([category, count]) => <button key={category} onClick={() => onNavigate('tasks-public')} className="rounded-xl border border-frame bg-mint-50 p-4 text-left transition-all hover:-translate-y-0.5 hover:border-blue-300 hover:bg-blue-50"><span className="text-2xl">{categoryIcons[category] ?? '📌'}</span><p className="mt-3 text-sm font-bold leading-5 text-ink">{category}</p><p className="mt-2 font-mono text-xs text-emerald-700">{count} aktivno</p></button>)}</div></div></section>}

        {sponsorBanners.length > 0 && <section className="mx-auto max-w-6xl px-4 py-14"><div className="mb-5 flex items-center justify-between"><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-violet-700">Zakup reklame</p><h2 className="mt-2 text-2xl font-extrabold text-ink">Sponzorisane ponude</h2></div><button onClick={() => onNavigate('advertiser-register')} className="text-sm font-bold text-blue-700">Zakupljivanje pozicije →</button></div><div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{sponsorBanners.map(banner => <BannerCard key={banner.id} banner={banner} />)}</div></section>}

        <section className="border-y border-frame bg-blue-50/60"><div className="mx-auto max-w-6xl px-4 py-16"><div className="grid gap-10 lg:grid-cols-[.9fr_1.1fr]"><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-blue-700">Za korisnike</p><h2 className="mt-2 text-3xl font-extrabold text-ink">Od zadatka do odobrene nagrade.</h2><p className="mt-4 max-w-md leading-7 text-ink-2">Nema plaćenog klika, automatskog kredita ili obećanja bez provere. Svaki korak ostavlja trag koji admin može da proveri.</p><Btn onClick={() => onNavigate('register')} className="mt-7">Napravi besplatan nalog</Btn></div><div className="grid gap-3 sm:grid-cols-2">{userSteps.map(([step, title, description]) => <Card key={step} className="p-5"><p className="font-mono text-xs font-bold text-blue-600">{step}</p><h3 className="mt-3 font-bold text-ink">{title}</h3><p className="mt-2 text-sm leading-6 text-ink-2">{description}</p></Card>)}</div></div></div></section>

        <section className="mx-auto max-w-6xl px-4 py-16"><div className="overflow-hidden rounded-3xl border border-emerald-200 bg-gradient-to-br from-emerald-50 via-white to-blue-50 p-7 md:p-10"><div className="grid gap-8 lg:grid-cols-[1.1fr_.9fr] lg:items-center"><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-emerald-700">Za oglašivače</p><h2 className="mt-2 text-3xl font-extrabold text-ink">Objavi merljiv posao ili zakup banner pozicije.</h2><p className="mt-4 max-w-xl leading-7 text-ink-2">Definiši nagradu, dokaz i publiku. Kampanja ide na moderaciju, a budžet se troši samo za odobrene rezultate. Banner zakup ima tačno određenu poziciju i trajanje.</p><div className="mt-7 flex flex-wrap gap-3"><Btn onClick={() => onNavigate('advertiser-register')}>Kreiraj kampanju</Btn><Btn onClick={() => onNavigate('advertiser-login')} variant="secondary">Uđi u oglašivački panel</Btn></div></div><div className="grid gap-3"><Card className="p-4"><p className="font-bold text-ink">01. Zadatak sa dokazom</p><p className="mt-1 text-sm text-ink-2">Anketa, testiranje, provera podataka ili feedback.</p></Card><Card className="p-4"><p className="font-bold text-ink">02. Admin moderacija</p><p className="mt-1 text-sm text-ink-2">Pregled cilja, teksta, budžeta i bezbednosti kampanje.</p></Card><Card className="p-4"><p className="font-bold text-ink">03. Rezultat koji možeš da proveriš</p><p className="mt-1 text-sm text-ink-2">Statusi, dokazi i potrošnja budžeta ostaju u panelu.</p></Card></div></div></div></section>

        {dashboardBanners.length > 0 && <section className="border-y border-frame bg-white"><div className="mx-auto max-w-6xl px-4 py-10"><div className="grid gap-4">{dashboardBanners.map(banner => <BannerCard key={banner.id} banner={banner} />)}</div></div></section>}
        {bottomBanners.length > 0 && <section className="mx-auto max-w-6xl px-4 py-12"><div className="grid gap-4 md:grid-cols-3">{bottomBanners.map(banner => <BannerCard key={banner.id} banner={banner} />)}</div></section>}
      </main>

      <footer className="border-t border-frame bg-white"><div className="mx-auto grid max-w-6xl gap-8 px-4 py-10 md:grid-cols-[1.3fr_1fr_1fr]"><div><div className="flex items-center gap-2 font-bold text-ink"><span className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-xs text-white">K</span>KlikZarada</div><p className="mt-3 max-w-sm text-sm leading-6 text-ink-2">Platforma za proverljiv digitalni rad i kampanje sa jasnim pravilima, dokazima i moderacijom.</p></div><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-ink-3">Platforma</p><div className="mt-3 flex flex-col items-start gap-2"><button onClick={() => onNavigate('tasks-public')} className="text-sm text-ink-2 hover:text-blue-700">Aktivni zadaci</button><button onClick={() => onNavigate('register')} className="text-sm text-ink-2 hover:text-blue-700">Registracija korisnika</button><button onClick={() => onNavigate('advertiser-register')} className="text-sm text-ink-2 hover:text-blue-700">Oglašavanje i banneri</button></div></div><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-ink-3">Važno</p><p className="mt-3 text-sm leading-6 text-ink-2">Nagrade se odobravaju nakon provere dokaza. Isplate se vrše preko PayPal adrese koju korisnik sačuva u svom profilu.</p></div></div><div className="border-t border-frame"><div className="mx-auto flex max-w-6xl flex-col justify-between gap-2 px-4 py-5 text-xs text-ink-3 sm:flex-row"><span>© 2026 KlikZarada. Sva prava zadržana.</span><span>Proverljiv rad. Jasna pravila. Odgovorno oglašavanje.</span></div></div></footer>
    </div>
  )
}
