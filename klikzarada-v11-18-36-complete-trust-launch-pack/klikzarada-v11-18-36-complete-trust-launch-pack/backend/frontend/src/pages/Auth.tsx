import { useState } from 'react'
import { Btn, Input, Alert } from '../components/ui'

type Mode = 'login' | 'register' | 'advertiser-login' | 'advertiser-register'

export default function Auth({
  initialMode = 'login',
  onNavigate,
}: {
  initialMode?: Mode
  onNavigate: (id: string) => void
}) {
  const [mode, setMode] = useState<Mode>(initialMode)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [referral, setReferral] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [error] = useState('')

  const isAdvertiser = mode === 'advertiser-login' || mode === 'advertiser-register'
  const isRegister = mode === 'register' || mode === 'advertiser-register'

  function handleSubmit() {
    if (!email || !password) return
    setSubmitted(true)
    setTimeout(() => {
      if (isAdvertiser) onNavigate('advertiser')
      else onNavigate('dashboard')
    }, 800)
  }

  return (
    <div className="min-h-screen bg-navy-900 flex flex-col">
      {/* Top bar */}
      <header className="border-b border-border bg-navy-950">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center gap-3">
          <button onClick={() => onNavigate('home')} className="flex items-center gap-2 cursor-pointer">
            <div className="w-7 h-7 bg-blue-500 rounded-md flex items-center justify-center font-bold text-white text-xs">K</div>
            <span className="font-semibold text-slate-100 text-sm">KlikZarada</span>
          </button>
        </div>
      </header>

      <div className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-sm">
          {/* Role switcher */}
          <div className="flex rounded-lg border border-border overflow-hidden mb-6">
            <button
              onClick={() => setMode(isRegister ? 'register' : 'login')}
              className={`flex-1 py-2 text-sm font-medium transition-colors cursor-pointer ${
                !isAdvertiser ? 'bg-blue-500 text-white' : 'bg-navy-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              Korisnik
            </button>
            <button
              onClick={() => setMode(isRegister ? 'advertiser-register' : 'advertiser-login')}
              className={`flex-1 py-2 text-sm font-medium transition-colors cursor-pointer ${
                isAdvertiser ? 'bg-blue-500 text-white' : 'bg-navy-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              Oglašivač
            </button>
          </div>

          <div className="bg-surface-2 border border-border rounded-lg p-6">
            <h1 className="text-lg font-semibold text-slate-100 mb-1">
              {isRegister
                ? isAdvertiser ? 'Registracija oglašivača' : 'Kreiraj nalog'
                : isAdvertiser ? 'Prijava oglašivača' : 'Prijavi se'}
            </h1>
            <p className="text-sm text-slate-400 mb-5">
              {isRegister
                ? 'Registracija je besplatna i traje manje od 2 minuta.'
                : 'Dobrodošao/la natrag.'}
            </p>

            {error && <Alert type="error">{error}</Alert>}

            <div className="flex flex-col gap-4">
              {isRegister && (
                <Input
                  label={isAdvertiser ? 'Naziv firme' : 'Ime i prezime'}
                  placeholder={isAdvertiser ? 'Moja Firma d.o.o.' : 'Marko Marković'}
                  value={name}
                  onChange={setName}
                />
              )}
              <Input label="Email adresa" type="email" placeholder="email@primer.rs" value={email} onChange={setEmail} />
              <Input label="Lozinka" type="password" placeholder="••••••••" value={password} onChange={setPassword} />
              {isRegister && !isAdvertiser && (
                <Input label="Referral kod (opciono)" placeholder="npr. USER123" value={referral} onChange={setReferral} />
              )}

              <Btn
                onClick={handleSubmit}
                disabled={submitted}
                className="w-full justify-center"
              >
                {submitted
                  ? '⏳ Učitavam...'
                  : isRegister ? 'Kreiraj nalog' : 'Prijavi se'}
              </Btn>
            </div>

            <div className="mt-5 pt-5 border-t border-border text-center">
              {isRegister ? (
                <p className="text-sm text-slate-400">
                  Već imaš nalog?{' '}
                  <button
                    onClick={() => setMode(isAdvertiser ? 'advertiser-login' : 'login')}
                    className="text-blue-400 hover:text-blue-300 cursor-pointer"
                  >
                    Prijavi se
                  </button>
                </p>
              ) : (
                <p className="text-sm text-slate-400">
                  Nemaš nalog?{' '}
                  <button
                    onClick={() => setMode(isAdvertiser ? 'advertiser-register' : 'register')}
                    className="text-blue-400 hover:text-blue-300 cursor-pointer"
                  >
                    Registruj se
                  </button>
                </p>
              )}
            </div>
          </div>

          <p className="text-center text-xs text-slate-600 mt-4">
            Prijavom prihvataš{' '}
            <span className="text-slate-500 cursor-pointer hover:text-slate-400">Uslove korišćenja</span>
            {' '}i{' '}
            <span className="text-slate-500 cursor-pointer hover:text-slate-400">Politiku privatnosti</span>.
          </p>
        </div>
      </div>
    </div>
  )
}
