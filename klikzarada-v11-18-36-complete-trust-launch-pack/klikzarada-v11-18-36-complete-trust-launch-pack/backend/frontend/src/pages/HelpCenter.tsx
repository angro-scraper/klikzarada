import { useState } from 'react'
import { Btn, Card } from '../components/ui'

const guides = [
  { audience: 'Korisnici', icon: '📋', title: 'Kako preuzeti i završiti zadatak', body: 'Izaberi zadatak, pročitaj instrukcije i dokaz pre početka. Radi u aktivnom tabu, pošalji traženi rezultat, pa prati odluku oglašivača u svojim dokazima.' },
  { audience: 'Korisnici', icon: '💸', title: 'Kada je nagrada raspoloživa', body: 'Nagrada najpre ima status na čekanju. Kada oglašivač odobri dokaz, prelazi u raspoloživ saldo. Isplatu možeš zatražiti tek po dostizanju minimalnog iznosa i uz sačuvanu PayPal adresu.' },
  { audience: 'Oglašivači', icon: '🎯', title: 'Kako postaviti dobar zadatak', body: 'Navedi poslovni cilj, tačne korake, ko može da radi zadatak, šta je prihvatljiv dokaz i koliko vremena realno traje. Ne objavljuj zahteve za lažne recenzije, klikove ili pratioce.' },
  { audience: 'Oglašivači', icon: '🖼️', title: 'Banner i VIP pozicije', body: 'Izaberi poziciju, period od 1 do 31 dana i kreativni materijal. Rezervacija se vidi pre slanja, a banner ili isticanje postaje vidljivo tek nakon administrativne provere.' },
]

const questions = [
  ['Zašto se dokaz ne odobrava automatski?', 'Automatsko kreditiranje bi bilo lako zloupotrebiti. Dokaz proverava oglašivač koji plaća rezultat, dok admin ulazi samo kod sporova i bezbednosnih signala.'],
  ['Da li KlikZarada traži podatke moje kartice?', 'Ne. Kartične podatke, kada je ta opcija dostupna, obrađuje PayPal. Platforma ne čuva broj kartice.'],
  ['Šta ako oglašivač ne odgovori na dokaz?', 'Sačuvaj svu komunikaciju i otvori tiket podrške sa nazivom zadatka. Admin može pregledati spor i evidenciju procesa.'],
  ['Kako prijaviti sumnjiv zadatak ili oglas?', 'Ne nastavljaj zadatak. Otvori tiket i dodaj link, naziv kampanje i kratak opis problema.'],
]

export default function HelpCenter({ onNavigate }: { onNavigate: (id: string) => void }) {
  const [openQuestion, setOpenQuestion] = useState<number | null>(0)

  return (
    <main className="min-h-screen bg-mint-50 text-ink">
      <header className="sticky top-0 z-40 border-b border-frame bg-white/95 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center gap-4 px-4">
          <button onClick={() => onNavigate('home')} className="flex items-center gap-2 font-bold"><span className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-600 text-sm text-white">K</span>KlikZarada</button>
          <div className="flex-1" />
          <Btn size="sm" variant="secondary" onClick={() => onNavigate('home')}>Nazad na početnu</Btn>
        </div>
      </header>

      <section className="border-b border-blue-100 bg-[radial-gradient(circle_at_top_right,_#dbeafe,_transparent_38%),linear-gradient(135deg,#f7fdf9_0%,#eff9f3_52%,#eef5ff_100%)]">
        <div className="mx-auto max-w-6xl px-4 py-16 md:py-20">
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-blue-700">Centar za pomoć</p>
          <h1 className="mt-3 max-w-2xl text-4xl font-extrabold tracking-tight md:text-5xl">Jasna pravila pre prvog zadatka ili oglasa.</h1>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-ink-2">Kratki vodiči za rad, dokaze, nagrade, kampanje i bezbednost. Ako odgovor ne pronađeš ovde, tiket ostavlja trag i stiže do podrške.</p>
          <div className="mt-7 flex flex-wrap gap-3"><Btn onClick={() => onNavigate('register')}>Počni kao korisnik</Btn><Btn variant="secondary" onClick={() => onNavigate('advertiser-register')}>Objavi kao oglašivač</Btn></div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-14"><div className="grid gap-4 md:grid-cols-2">{guides.map(guide => <Card key={guide.title} className="p-6"><div className="flex items-start gap-4"><span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-xl">{guide.icon}</span><div><p className="text-xs font-bold uppercase tracking-wide text-blue-700">{guide.audience}</p><h2 className="mt-2 text-lg font-bold">{guide.title}</h2><p className="mt-3 text-sm leading-6 text-ink-2">{guide.body}</p></div></div></Card>)}</div></section>

      <section className="border-y border-frame bg-white"><div className="mx-auto grid max-w-6xl gap-8 px-4 py-14 lg:grid-cols-[1.1fr_.9fr]"><div><p className="text-xs font-bold uppercase tracking-[0.16em] text-emerald-700">Poverenje i bezbednost</p><h2 className="mt-2 text-3xl font-extrabold">Šta platforma proverava?</h2><div className="mt-6 space-y-3 text-sm leading-6 text-ink-2"><p className="rounded-xl border border-emerald-100 bg-emerald-50 p-4"><strong className="text-ink">Pre slanja dokaza:</strong> vreme rada, aktivnost i osnovni bezbednosni signali.</p><p className="rounded-xl border border-blue-100 bg-blue-50 p-4"><strong className="text-ink">Pre nagrade:</strong> oglašivač proverava da li dokaz ispunjava unapred objavljeni kriterijum.</p><p className="rounded-xl border border-violet-100 bg-violet-50 p-4"><strong className="text-ink">Kod spora:</strong> admin pregleda evidenciju procesa, a ne zamenjuje redovni pregled oglašivača.</p></div></div><Card className="self-start border-amber-200 bg-amber-50 p-6"><p className="text-xs font-bold uppercase tracking-[0.16em] text-amber-700">Prijavi problem</p><h2 className="mt-2 text-xl font-extrabold">Ne vidiš odgovor ili sumnjaš na zloupotrebu?</h2><p className="mt-3 text-sm leading-6 text-ink-2">U prijavi napiši naziv zadatka ili kampanje, kada se problem desio i dodaj dokaz ako ga imaš.</p><Btn className="mt-5" onClick={() => onNavigate('login')}>Prijavi se i otvori tiket</Btn></Card></div></section>

      <section className="mx-auto max-w-4xl px-4 py-14"><p className="text-xs font-bold uppercase tracking-[0.16em] text-violet-700">Česta pitanja</p><h2 className="mt-2 text-3xl font-extrabold">Odgovori bez sitnih slova.</h2><div className="mt-6 divide-y divide-frame rounded-2xl border border-frame bg-white">{questions.map(([question, answer], index) => <div key={question}><button onClick={() => setOpenQuestion(openQuestion === index ? null : index)} className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left font-bold"><span>{question}</span><span className="text-xl text-blue-600">{openQuestion === index ? '−' : '+'}</span></button>{openQuestion === index && <p className="px-5 pb-5 text-sm leading-6 text-ink-2">{answer}</p>}</div>)}</div></section>
    </main>
  )
}
