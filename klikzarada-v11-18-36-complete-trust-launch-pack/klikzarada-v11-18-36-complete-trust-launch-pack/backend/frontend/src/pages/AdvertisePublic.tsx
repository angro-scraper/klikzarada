import { useEffect, useState } from 'react'
import { api } from '../lib/api'

type AdvertisingInfo = Awaited<ReturnType<typeof api.publicAdvertisingInfo>>

const testerSteps = [
  ['01', 'Odredi zadatak', 'Navedi cilj, uređaj, jezik, trajanje i korake koje tester treba da prati.'],
  ['02', 'Postavi dokaz', 'Za dnevni test traži kratak izveštaj o korišćenju i eventualnom problemu.'],
  ['03', 'Pregledaj rad', 'Prati prijave, potvrdi pristup i odobri ili vrati svaki poslati dnevni rezultat.'],
]

const placementLabels: Record<string, string> = {
  home_top: 'Gornji deo početne',
  home_mid: 'Sredina početne',
  home_sponsor: 'Sponzorisane ponude',
  home_dashboard: 'Ispod informacija o isplati',
  home_bottom: 'Dno početne',
  admin_dashboard: 'Admin panel',
}

const formatLabels: Record<string, string> = {
  wide: 'puna širina',
  half: 'polovina reda',
  third: 'trećina reda',
  quarter: 'četvrtina reda',
}

export default function AdvertisePublic() {
  const [info, setInfo] = useState<AdvertisingInfo | null>(null)
  const [error, setError] = useState(false)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let active = true
    setError(false)
    void api.publicAdvertisingInfo().then(value => {
      if (!active) return
      if (typeof value?.platform_fee_percent !== 'number' || !Array.isArray(value?.slots)) throw new Error('Nevažeći podaci o ponudi')
      setInfo(value)
    }).catch(() => { if (active) setError(true) })
    return () => { active = false }
  }, [attempt])

  return <div className="min-h-screen bg-mint-50 text-ink">
    <header className="sticky top-0 z-40 border-b border-frame bg-white/95 backdrop-blur"><div className="mx-auto flex h-16 max-w-6xl items-center gap-3 px-4"><a href="/" className="flex items-center gap-2 font-bold"><span className="grid h-8 w-8 place-items-center rounded-lg bg-blue-600 text-sm text-white">K</span>KlikZarada</a><div className="flex-1" /><a href="/oglasivac/prijava" className="text-sm font-semibold text-blue-700">Prijava oglašivača</a></div></header>
    <main>
      <section className="border-b border-blue-100 bg-[radial-gradient(circle_at_top_right,_#dbeafe,_transparent_42%),linear-gradient(135deg,#f7fdf9,#eef5ff)]"><div className="mx-auto max-w-6xl px-4 py-12 md:py-16"><p className="text-xs font-bold uppercase tracking-widest text-blue-700">Za oglašivače i razvojne timove</p><h1 className="mt-3 max-w-3xl text-4xl font-extrabold leading-tight md:text-5xl">Testeri za stvaran rad. Reklama na jasnoj poziciji.</h1><p className="mt-4 max-w-2xl text-lg leading-8 text-ink-2">Izaberi zadatak sa proverljivim rezultatom ili zakup banner mesta. Uslove, cenu i sledeći korak vidi pre registracije.</p><div className="mt-7 flex flex-wrap gap-3"><a href="#testeri" className="grid min-h-11 place-items-center rounded-lg bg-blue-600 px-5 text-sm font-bold text-white">Potrebni su mi testeri</a><a href="#baneri" className="grid min-h-11 place-items-center rounded-lg border border-blue-200 bg-white px-5 text-sm font-bold text-blue-700">Želim reklamnu poziciju</a></div></div></section>
      <section id="testeri" className="mx-auto max-w-6xl scroll-mt-20 px-4 py-14"><div className="max-w-2xl"><p className="text-xs font-bold uppercase tracking-widest text-emerald-700">Kampanja sa zadatkom</p><h2 className="mt-2 text-3xl font-extrabold">Potrebni su mi testeri</h2><p className="mt-3 leading-7 text-ink-2">Definiši ko može da učestvuje i šta se tačno proverava. Kod zatvorenog testa tester šalje prijavu, ti potvrđuješ pristup i zatim pregledaš dnevne izveštaje.</p></div><div className="mt-7 grid gap-4 md:grid-cols-3">{testerSteps.map(([number, title, body]) => <div key={number} className="rounded-2xl border border-frame bg-white p-5 shadow-sm"><span className="font-mono text-sm font-bold text-blue-700">{number}</span><h3 className="mt-3 text-lg font-bold">{title}</h3><p className="mt-2 text-sm leading-6 text-ink-2">{body}</p></div>)}</div><div className="mt-6 rounded-2xl border border-emerald-200 bg-emerald-50 p-5 text-sm leading-7"><h3 className="font-bold text-ink">Budžet kampanje</h3><p className="mt-1">Nagrada po korisniku × broj mesta, uz naknadu platforme{info ? ` od ${info.platform_fee_percent.toLocaleString('sr-RS')}%` : ''}. Konačna rezervacija prikazuje se u obrascu kampanje pre objave. Nagrada se obračunava po odobrenom rezultatu; spor ili odustajanje rešava se kroz pregled dokaza i podršku.</p></div><a href="/oglasivac/registracija" className="mt-6 inline-grid min-h-11 place-items-center rounded-lg bg-blue-600 px-5 text-sm font-bold text-white">Registruj se i napravi kampanju</a></section>
      <section id="baneri" className="scroll-mt-20 border-y border-frame bg-white">
        <div className="mx-auto max-w-6xl px-4 py-14">
          <div className="max-w-2xl"><p className="text-xs font-bold uppercase tracking-widest text-blue-700">Zakup pozicije</p><h2 className="mt-2 text-3xl font-extrabold">Želim reklamnu poziciju</h2><p className="mt-3 leading-7 text-ink-2">Izaberi mesto na početnoj strani, trajanje i kreativu. Banner je označen kao sponzorisan; moderacija proverava sadržaj pre prikaza. Dostupnost termina i konačna cena potvrđuju se u oglašivačkom panelu.</p></div>
          <div className="mt-7 rounded-2xl border border-blue-100 bg-blue-50/60 p-5">
            <p className="text-xs font-bold uppercase tracking-widest text-blue-700">Kako izgleda raspored</p>
            <p className="mt-1 text-sm text-ink-2">Ilustracija rasporeda na računaru i telefonu; ne označava slobodan termin.</p>
            <div className="mt-4 grid items-end gap-5 sm:grid-cols-[1fr_11rem]" aria-hidden="true">
              <div className="rounded-xl border border-blue-200 bg-white p-3 shadow-sm"><div className="h-3 w-1/3 rounded bg-slate-200" /><div className="mt-3 h-10 rounded bg-blue-200" /><div className="mt-2 grid grid-cols-2 gap-2"><div className="h-8 rounded bg-emerald-100" /><div className="h-8 rounded bg-emerald-100" /></div><div className="mt-3 h-8 rounded bg-blue-100" /></div>
              <div className="mx-auto w-28 rounded-[1.5rem] border-4 border-slate-700 bg-white p-2 shadow-sm"><div className="mx-auto h-1 w-8 rounded-full bg-slate-700" /><div className="mt-3 h-7 rounded bg-blue-200" /><div className="mt-2 h-12 rounded bg-emerald-100" /><div className="mt-2 h-7 rounded bg-blue-100" /></div>
            </div>
          </div>
          {error ? <div className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm" role="alert">Cenovnik trenutno nije dostupan. <button onClick={() => setAttempt(value => value + 1)} className="font-bold text-blue-700 underline">Pokušaj ponovo</button></div> : !info ? <p className="mt-6 text-sm text-ink-2" role="status">Učitavanje pozicija i cena...</p> : info.slots.length ? <div className="mt-7 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{info.slots.map(slot => <div key={slot.id} className="rounded-2xl border border-blue-100 bg-mint-50 p-5"><span className="text-xs font-bold uppercase tracking-widest text-blue-700">{placementLabels[slot.placement] || slot.placement}</span><h3 className="mt-2 text-lg font-bold">{slot.title}</h3><p className="mt-2 text-sm text-ink-2">Širina: {formatLabels[slot.width_label] || slot.width_label}</p><p className="mt-4 font-mono text-lg font-bold text-emerald-700">{slot.price_rsd.toLocaleString('sr-RS')} RSD / {info.banner_price_basis_days} dana</p></div>)}</div> : <p className="mt-6 text-sm text-ink-2">Trenutno nema objavljenih banner pozicija.</p>}
          <p className="mt-6 text-sm leading-6 text-ink-2">{info ? `Kreativa: ${info.banner_image_formats.join(', ')} do ${info.banner_upload_max_mb} MB, od ${info.banner_image_min_size} do ${info.banner_image_max_size}. Trajanje se bira do ${info.banner_max_days} dana.` : 'Pravila za kreativu prikazaćemo kada se cenovnik učita.'} Stvarni pregled, raspoloživost termina i izveštavanje vidi u panelu pre potvrde zakupa.</p>
          <a href="/oglasivac/registracija" className="mt-6 inline-grid min-h-11 place-items-center rounded-lg bg-blue-600 px-5 text-sm font-bold text-white">Registruj se i pogledaj termine</a>
        </div>
      </section>
    </main>
    <footer className="mx-auto flex max-w-6xl flex-wrap gap-5 px-4 py-8 text-sm"><a className="font-semibold text-blue-700" href="/pomoc">Pomoć i kontakt</a><a className="font-semibold text-blue-700" href="/pravila">Pravila i privatnost</a><a className="font-semibold text-blue-700" href="/">Početna</a></footer>
  </div>
}
