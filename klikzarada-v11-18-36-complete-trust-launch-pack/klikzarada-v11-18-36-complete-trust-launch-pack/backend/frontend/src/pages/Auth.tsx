import { useState } from 'react'
import { Btn, Input, Alert } from '../components/ui'
import { api, deviceFingerprint } from '../lib/api'

type Mode = 'login' | 'register' | 'advertiser-login' | 'advertiser-register' | 'admin-login'

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
  const [phone, setPhone] = useState('')
  const [advertiserType, setAdvertiserType] = useState<'business' | 'private'>('business')
  const [referral, setReferral] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')

  const isAdvertiser = mode === 'advertiser-login' || mode === 'advertiser-register'
  const isRegister = mode === 'register' || mode === 'advertiser-register'
  const isAdmin = mode === 'admin-login'

  async function handleSubmit() {
    if (!email || !password || (isRegister && !name)) return
    setSubmitted(true)
    setError('')
    try {
      const result = isRegister
        ? await api.register({
            full_name: name,
            email,
            password,
            role: isAdvertiser ? 'oglasivac' : 'korisnik',
            advertiser_type: isAdvertiser ? advertiserType : undefined,
            referral_code: referral || undefined,
            phone: isAdvertiser ? undefined : phone,
            device_fingerprint: deviceFingerprint(),
          })
        : await api.login(email, password)
      if (result.user.role === 'admin') onNavigate('admin')
      else onNavigate(result.user.role === 'oglasivac' ? 'advertiser' : 'dashboard')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Prijava nije uspela.')
    } finally {
      setSubmitted(false)
    }
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
          {isAdmin ? (
            <div className="rounded-lg border border-violet-200 bg-violet-50 px-4 py-2.5 text-center text-sm font-semibold text-violet-800 mb-6">
              Administratorski pristup
            </div>
          ) : <div className="flex rounded-lg border border-border overflow-hidden mb-6">
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
          </div>}

          <div className="bg-surface-2 border border-border rounded-lg p-6">
            <h1 className="text-lg font-semibold text-slate-100 mb-1">
              {isRegister
                ? isAdvertiser ? 'Registracija oglašivača' : 'Kreiraj nalog'
                : isAdmin ? 'Admin prijava' : isAdvertiser ? 'Prijava oglašivača' : 'Prijavi se'}
            </h1>
            <p className="text-sm text-slate-400 mb-5">
              {isRegister
                ? 'Registracija je besplatna i traje manje od 2 minuta.'
                : isAdmin ? 'Pristup je dozvoljen samo ovlašćenom administratoru.' : 'Dobrodošao/la natrag.'}
            </p>

            {error && <Alert type="error">{error}</Alert>}

            <div className="flex flex-col gap-4">
              {isRegister && isAdvertiser && (
                <div className="flex flex-col gap-1.5">
                  <span className="text-xs font-semibold text-ink-2 uppercase tracking-wide">Tip oglašivača</span>
                  <div className="grid grid-cols-2 gap-2">
                    <button onClick={() => setAdvertiserType('business')} className={`rounded-lg border px-3 py-2 text-sm font-semibold cursor-pointer transition-colors ${advertiserType === 'business' ? 'border-blue-500 bg-blue-50 text-blue-700' : 'border-frame bg-white text-ink-2 hover:border-blue-200'}`}>Firma</button>
                    <button onClick={() => setAdvertiserType('private')} className={`rounded-lg border px-3 py-2 text-sm font-semibold cursor-pointer transition-colors ${advertiserType === 'private' ? 'border-blue-500 bg-blue-50 text-blue-700' : 'border-frame bg-white text-ink-2 hover:border-blue-200'}`}>Privatno lice</button>
                  </div>
                  <p className="text-xs text-ink-3">Privatno lice koristi svoje ime i prezime; firma koristi registrovani naziv.</p>
                </div>
              )}
              {isRegister && (
                <Input
                  label={isAdvertiser ? advertiserType === 'business' ? 'Naziv firme' : 'Ime i prezime' : 'Ime i prezime'}
                  placeholder={isAdvertiser && advertiserType === 'business' ? 'Moja Firma d.o.o.' : 'Marko Marković'}
                  value={name}
                  onChange={setName}
                />
              )}
              <Input label="Email adresa" type="email" placeholder="email@primer.rs" value={email} onChange={setEmail} />
              {isRegister && !isAdvertiser && (
                <Input label="Telefon za proveru naloga" type="tel" placeholder="npr. +381 60 123 4567" value={phone} onChange={setPhone} />
              )}
              <Input label="Lozinka" type="password" placeholder="••••••••" value={password} onChange={setPassword} />
              {isRegister && !isAdvertiser && (
                <Input label="Referral kod (opciono)" placeholder="npr. USER123" value={referral} onChange={setReferral} />
              )}

              <Btn
                onClick={handleSubmit}
                disabled={submitted || (isRegister && !isAdvertiser && phone.trim().length < 7)}
                className="w-full justify-center"
              >
                {submitted
                  ? '⏳ Učitavam...'
                  : isRegister ? 'Kreiraj nalog' : 'Prijavi se'}
              </Btn>
            </div>

            <div className="mt-5 pt-5 border-t border-border text-center">
              {isAdmin ? (
                <p className="text-sm text-slate-400">Admin nalog kreira vlasnik platforme kroz zaštićena Render podešavanja.</p>
              ) : isRegister ? (
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
