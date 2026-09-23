import { useState } from 'react'
import { Btn, Card } from '../components/ui'

const taskCategories = [
  { icon: '📱', label: 'Društvene mreže', count: 42 },
  { icon: '📝', label: 'Ankete i testiranja', count: 28 },
  { icon: '🔍', label: 'Pretraga i recenzije', count: 35 },
  { icon: '🎬', label: 'Video i audio', count: 19 },
  { icon: '💻', label: 'Web zadaci', count: 31 },
  { icon: '🛒', label: 'Kupovina i aplikacije', count: 14 },
]

const steps = [
  { step: '01', title: 'Registruj se', desc: 'Besplatna registracija. Bez skrivenih troškova.', icon: '👤' },
  { step: '02', title: 'Preuzmi zadatak', desc: 'Odaberi zadatke koji odgovaraju tvom vremenu i uređaju.', icon: '📋' },
  { step: '03', title: 'Dostavi dokaz', desc: 'Priloži screenshot ili video kao potvrdu izvršenja.', icon: '✅' },
  { step: '04', title: 'Primi isplatu', desc: 'Zarađeni iznos se automatski dodaje tvom novčaniku.', icon: '💰' },
]

const advertiserSteps = [
  { icon: '🎯', title: 'Definiši kampanju', desc: 'Opiši zadatak, cilj i potrebni dokaz izvršenja.' },
  { icon: '💳', title: 'Uplati budžet', desc: 'Siguran platni sistem. Plaćaš samo proverene rezultate.' },
  { icon: '📊', title: 'Prati rezultate', desc: 'Realni dokazi korisnika. Anti-fraud sistem u pozadini.' },
]

const trustPoints = [
  { icon: '🔒', title: 'Proverljivi zadaci', desc: 'Svaki zadatak zahteva dokaz — screenshot, link ili video.' },
  { icon: '🛡️', title: 'Anti-fraud zaštita', desc: 'Automatski sistem otkriva lažne dokaze pre odobravanja.' },
  { icon: '💵', title: 'Transparentne isplate', desc: 'Znaš tačno koliko zarađuješ i kada dobijate isplatu.' },
  { icon: '🤝', title: 'Podrška 7/7', desc: 'Ekipa podrške odgovara na sve upite korisnika i oglašivača.' },
]

export default function Landing({ onNavigate }: { onNavigate: (id: string) => void }) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  return (
    <div className="min-h-screen bg-navy-900 text-slate-200">
      {/* Nav */}
      <nav className="border-b border-border bg-navy-950/90 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center gap-4">
          <button onClick={() => onNavigate('home')} className="flex items-center gap-2 cursor-pointer">
            <div className="w-7 h-7 bg-blue-500 rounded-md flex items-center justify-center font-bold text-white text-xs">K</div>
            <span className="font-semibold text-slate-100">KlikZarada</span>
          </button>
          <div className="flex-1" />
          <div className="hidden md:flex items-center gap-1">
            <button onClick={() => onNavigate('tasks-public')} className="px-3 py-1.5 text-sm text-slate-400 hover:text-slate-200 cursor-pointer rounded hover:bg-navy-700/50 transition-colors">
              Zadaci
            </button>
            <button onClick={() => onNavigate('login')} className="px-3 py-1.5 text-sm text-slate-400 hover:text-slate-200 cursor-pointer rounded hover:bg-navy-700/50 transition-colors">
              Prijava
            </button>
            <Btn onClick={() => onNavigate('register')} size="sm">Pokreni zaradu</Btn>
            <Btn onClick={() => onNavigate('advertiser-login')} variant="secondary" size="sm">Za oglašivače</Btn>
          </div>
          <button className="md:hidden text-slate-400 p-1.5 cursor-pointer" onClick={() => setMobileMenuOpen(v => !v)}>☰</button>
        </div>
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-border bg-navy-950 px-4 py-3 flex flex-col gap-2">
            <button onClick={() => { onNavigate('tasks-public'); setMobileMenuOpen(false) }} className="text-sm text-slate-300 py-2 text-left cursor-pointer">Zadaci</button>
            <button onClick={() => { onNavigate('login'); setMobileMenuOpen(false) }} className="text-sm text-slate-300 py-2 text-left cursor-pointer">Prijava</button>
            <Btn onClick={() => onNavigate('register')} size="sm" className="w-full justify-center">Pokreni zaradu</Btn>
            <Btn onClick={() => onNavigate('advertiser-login')} variant="secondary" size="sm" className="w-full justify-center">Za oglašivače</Btn>
          </div>
        )}
      </nav>

      {/* Hero */}
      <section className="max-w-6xl mx-auto px-4 py-20 md:py-28">
        <div className="max-w-2xl">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded text-xs font-medium bg-blue-900/50 text-blue-300 border border-blue-500/20 mb-5">
            🇷🇸 Srpska platforma za mikro-zadatke
          </span>
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-slate-50 leading-tight mb-5">
            Zarađuj.<br />
            <span className="text-blue-400">Proverljivo.</span><br />
            Transparentno.
          </h1>
          <p className="text-lg text-slate-400 mb-8 max-w-xl">
            Izvršavaj kratke zadatke za stvarne oglašivače i primaj isplate direktno na račun.
            Bez prevara. Bez skrivenih troškova.
          </p>
          <div className="flex flex-wrap gap-3">
            <Btn onClick={() => onNavigate('register')} size="lg">Pokreni zaradu →</Btn>
            <Btn onClick={() => onNavigate('advertiser-login')} variant="secondary" size="lg">Kreiraj kampanju</Btn>
          </div>
          <div className="flex gap-6 mt-8">
            {[
              { label: 'Korisnika', val: '—' },
              { label: 'Isplaćeno', val: '—' },
              { label: 'Aktivnih kampanja', val: '—' },
            ].map(s => (
              <div key={s.label}>
                <p className="font-mono text-xl font-semibold text-slate-100">{s.val}</p>
                <p className="text-xs text-slate-500">{s.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Categories */}
      <section className="border-t border-border bg-navy-950/50">
        <div className="max-w-6xl mx-auto px-4 py-14">
          <h2 className="text-xl font-semibold text-slate-100 mb-6">Kategorije zadataka</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
            {taskCategories.map(c => (
              <button
                key={c.label}
                onClick={() => onNavigate('tasks-public')}
                className="bg-surface-2 border border-border rounded-lg p-4 flex flex-col items-center gap-2 hover:border-blue-500/40 hover:bg-navy-700/40 transition-all cursor-pointer text-center"
              >
                <span className="text-2xl">{c.icon}</span>
                <span className="text-xs font-medium text-slate-300 leading-tight">{c.label}</span>
                <span className="text-[10px] text-slate-500">{c.count} zadataka</span>
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* How it works - users */}
      <section className="max-w-6xl mx-auto px-4 py-14">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-xl font-semibold text-slate-100">Kako radi za korisnike</h2>
            <p className="text-sm text-slate-500 mt-1">4 koraka do prve zarade</p>
          </div>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {steps.map(s => (
            <Card key={s.step} className="p-5">
              <div className="flex items-start gap-3 mb-3">
                <span className="font-mono text-xs text-slate-600 font-semibold">{s.step}</span>
                <span className="text-xl">{s.icon}</span>
              </div>
              <h3 className="font-semibold text-slate-100 mb-1">{s.title}</h3>
              <p className="text-sm text-slate-400">{s.desc}</p>
            </Card>
          ))}
        </div>
        <div className="mt-6">
          <Btn onClick={() => onNavigate('register')} size="md">Registruj se besplatno</Btn>
        </div>
      </section>

      {/* Advertiser section */}
      <section className="border-t border-border bg-navy-950/50">
        <div className="max-w-6xl mx-auto px-4 py-14">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <span className="text-xs font-semibold text-blue-400 uppercase tracking-wide">Za oglašivače</span>
              <h2 className="text-2xl font-bold text-slate-50 mt-2 mb-4">
                Plaćaj samo<br />dokazane rezultate
              </h2>
              <p className="text-slate-400 mb-6">
                Kreiraj kampanju, definiši zadatak i dobij stvarne dokaze od proverenih korisnika.
                Budžet se troši isključivo po odobrenim dokazima.
              </p>
              <Btn onClick={() => onNavigate('advertiser-login')} variant="secondary">Kreiraj kampanju →</Btn>
            </div>
            <div className="flex flex-col gap-4">
              {advertiserSteps.map(a => (
                <div key={a.title} className="flex gap-4 items-start">
                  <div className="w-10 h-10 rounded-lg bg-surface-2 border border-border flex items-center justify-center text-xl shrink-0">{a.icon}</div>
                  <div>
                    <h3 className="font-medium text-slate-100">{a.title}</h3>
                    <p className="text-sm text-slate-400 mt-0.5">{a.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Trust */}
      <section className="max-w-6xl mx-auto px-4 py-14">
        <h2 className="text-xl font-semibold text-slate-100 mb-6">Zašto nam verovati</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {trustPoints.map(t => (
            <Card key={t.title} className="p-5">
              <span className="text-2xl mb-3 block">{t.icon}</span>
              <h3 className="font-medium text-slate-100 mb-1">{t.title}</h3>
              <p className="text-sm text-slate-400">{t.desc}</p>
            </Card>
          ))}
        </div>
      </section>

      {/* CTA Banner */}
      <section className="border-t border-border bg-blue-900/20">
        <div className="max-w-6xl mx-auto px-4 py-12 flex flex-col sm:flex-row items-center justify-between gap-6">
          <div>
            <h2 className="text-xl font-bold text-slate-50">Spreman/a da počneš?</h2>
            <p className="text-slate-400 text-sm mt-1">Registracija je besplatna i traje manje od 2 minuta.</p>
          </div>
          <div className="flex gap-3">
            <Btn onClick={() => onNavigate('register')} size="lg">Pokreni zaradu</Btn>
            <Btn onClick={() => onNavigate('tasks-public')} variant="secondary" size="lg">Pregledaj zadatke</Btn>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border bg-navy-950">
        <div className="max-w-6xl mx-auto px-4 py-10">
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-8 mb-8">
            <div>
              <div className="flex items-center gap-2 mb-3">
                <div className="w-6 h-6 bg-blue-500 rounded flex items-center justify-center text-white text-xs font-bold">K</div>
                <span className="font-semibold text-slate-100 text-sm">KlikZarada</span>
              </div>
              <p className="text-xs text-slate-500">Srpska platforma za mikro-zadatke. Transparentna. Pouzdana. Proverljiva.</p>
            </div>
            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">Platforma</p>
              <div className="flex flex-col gap-2">
                {['Kako radi', 'Kategorije zadataka', 'Oglašivači', 'Cene'].map(l => (
                  <span key={l} className="text-xs text-slate-500 hover:text-slate-300 cursor-pointer transition-colors">{l}</span>
                ))}
              </div>
            </div>
            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">Podrška</p>
              <div className="flex flex-col gap-2">
                {['Pomoć', 'Kontakt', 'Pravila korišćenja', 'Privatnost'].map(l => (
                  <span key={l} className="text-xs text-slate-500 hover:text-slate-300 cursor-pointer transition-colors">{l}</span>
                ))}
              </div>
            </div>
            <div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">Prati nas</p>
              <div className="flex gap-3">
                {['𝕏', 'f', 'in', '📷'].map(s => (
                  <span key={s} className="w-8 h-8 rounded border border-border flex items-center justify-center text-xs text-slate-500 hover:text-slate-300 hover:border-border cursor-pointer transition-colors">{s}</span>
                ))}
              </div>
            </div>
          </div>
          <div className="border-t border-border pt-5 flex flex-col sm:flex-row items-center justify-between gap-2">
            <p className="text-xs text-slate-600">© 2024 KlikZarada. Sva prava zadržana.</p>
            <div className="flex gap-4">
              <span className="text-xs text-slate-600 hover:text-slate-400 cursor-pointer">Uslovi</span>
              <span className="text-xs text-slate-600 hover:text-slate-400 cursor-pointer">Privatnost</span>
              <span className="text-xs text-slate-600 hover:text-slate-400 cursor-pointer">Kolačići</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
