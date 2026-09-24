import { useEffect, useState } from 'react'
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
  const [acceptTerms, setAcceptTerms] = useState(false)
  const [forgotPassword, setForgotPassword] = useState(false)
  const [resetToken, setResetToken] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const isAdvertiser = mode === 'advertiser-login' || mode === 'advertiser-register'
  const isRegister = mode === 'register' || mode === 'advertiser-register'
  const isAdmin = mode === 'admin-login'

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const verificationToken = params.get('verify')
    const passwordToken = params.get('reset')
    if (passwordToken) {
      setResetToken(passwordToken)
      setForgotPassword(false)
      return
    }
    if (!verificationToken) return
    void api.verifyEmail(verificationToken)
      .then(() => setNotice('Email adresa je potvrđena. Sada možeš da se prijaviš.'))
      .catch(caught => setError(caught instanceof Error ? caught.message : 'Email nije potvrđen.'))
      .finally(() => window.history.replaceState({}, '', '/prijava'))
  }, [])

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
            accept_terms: acceptTerms,
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

  async function handlePasswordReset() {
    if (!password) return
    setSubmitted(true)
    setError('')
    try {
      await api.confirmPasswordReset(resetToken, password)
      setResetToken('')
      setNotice('Lozinka je promenjena. Sada se prijavi novom lozinkom.')
      window.history.replaceState({}, '', '/prijava')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Lozinka nije promenjena.')
    } finally {
      setSubmitted(false)
    }
  }

  async function requestReset() {
    if (!email) return
    setSubmitted(true)
    setError('')
    try {
      await api.requestPasswordReset(email)
      setNotice('Ako nalog postoji, poslat je link za postavljanje nove lozinke.')
      setForgotPassword(false)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Zahtev nije poslat.')
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
              {resetToken
                ? 'Postavi novu lozinku'
                : forgotPassword ? 'Reset lozinke'
                : isRegister
                ? isAdvertiser ? 'Registracija oglašivača' : 'Kreiraj nalog'
                : isAdmin ? 'Admin prijava' : isAdvertiser ? 'Prijava oglašivača' : 'Prijavi se'}
            </h1>
            <p className="text-sm text-slate-400 mb-5">
              {resetToken
                ? 'Unesi novu lozinku od najmanje 8 karaktera.'
                : forgotPassword ? 'Unesi email adresu i poslaćemo bezbedan link ako nalog postoji.'
                : isRegister
                ? 'Registracija je besplatna i traje manje od 2 minuta.'
                : isAdmin ? 'Pristup je dozvoljen samo ovlašćenom administratoru.' : 'Dobrodošao/la natrag.'}
            </p>

            {error && <Alert type="error">{error}</Alert>}
            {notice && <Alert type="success">{notice}</Alert>}

            <div className="flex flex-col gap-4">
              {!resetToken && !forgotPassword && isRegister && isAdvertiser && (
                <div className="flex flex-col gap-1.5">
                  <span className="text-xs font-semibold text-ink-2 uppercase tracking-wide">Tip oglašivača</span>
                  <div className="grid grid-cols-2 gap-2">
                    <button onClick={() => setAdvertiserType('business')} className={`rounded-lg border px-3 py-2 text-sm font-semibold cursor-pointer transition-colors ${advertiserType === 'business' ? 'border-blue-500 bg-blue-50 text-blue-700' : 'border-frame bg-white text-ink-2 hover:border-blue-200'}`}>Firma</button>
                    <button onClick={() => setAdvertiserType('private')} className={`rounded-lg border px-3 py-2 text-sm font-semibold cursor-pointer transition-colors ${advertiserType === 'private' ? 'border-blue-500 bg-blue-50 text-blue-700' : 'border-frame bg-white text-ink-2 hover:border-blue-200'}`}>Privatno lice</button>
                  </div>
                  <p className="text-xs text-ink-3">Privatno lice koristi svoje ime i prezime; firma koristi registrovani naziv.</p>
                </div>
              )}
              {!resetToken && !forgotPassword && isRegister && (
                <Input
                  label={isAdvertiser ? advertiserType === 'business' ? 'Naziv firme' : 'Ime i prezime' : 'Ime i prezime'}
                  placeholder={isAdvertiser && advertiserType === 'business' ? 'Moja Firma d.o.o.' : 'Marko Marković'}
                  value={name}
                  onChange={setName}
                />
              )}
              {!resetToken && <Input label="Email adresa" type="email" placeholder="email@primer.rs" value={email} onChange={setEmail} />}
              {!resetToken && !forgotPassword && isRegister && !isAdvertiser && (
                <Input label="Telefon za proveru naloga" type="tel" placeholder="npr. +381 60 123 4567" value={phone} onChange={setPhone} />
              )}
              {!forgotPassword && <Input label={resetToken ? 'Nova lozinka' : 'Lozinka'} type="password" placeholder="••••••••" value={password} onChange={setPassword} />}
              {!resetToken && !forgotPassword && isRegister && !isAdvertiser && (
                <Input label="Referral kod (opciono)" placeholder="npr. USER123" value={referral} onChange={setReferral} />
              )}

              {!resetToken && !forgotPassword && isRegister && (
                <label className="flex gap-2 items-start text-xs text-slate-400 cursor-pointer">
                  <input type="checkbox" checked={acceptTerms} onChange={event => setAcceptTerms(event.target.checked)} className="mt-0.5" />
                  <span>Prihvatam <button type="button" onClick={() => onNavigate('legal')} className="text-blue-400 hover:text-blue-300">Uslove korišćenja i Politiku privatnosti</button>.</span>
                </label>
              )}

              <Btn
                onClick={resetToken ? handlePasswordReset : forgotPassword ? requestReset : handleSubmit}
                disabled={submitted || (!resetToken && !forgotPassword && isRegister && (!acceptTerms || (!isAdvertiser && phone.trim().length < 7)))}
                className="w-full justify-center"
              >
                {submitted
                  ? '⏳ Učitavam...'
                  : resetToken ? 'Sačuvaj novu lozinku' : forgotPassword ? 'Pošalji link za reset' : isRegister ? 'Kreiraj nalog' : 'Prijavi se'}
              </Btn>
            </div>

            <div className="mt-5 pt-5 border-t border-border text-center">
              {resetToken || forgotPassword ? (
                <button onClick={() => { setResetToken(''); setForgotPassword(false); setError('') }} className="text-sm text-blue-400 hover:text-blue-300 cursor-pointer">Nazad na prijavu</button>
              ) : isAdmin ? (
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
              {!isRegister && !isAdmin && <button onClick={() => { setForgotPassword(true); setNotice(''); setError('') }} className="mt-3 text-xs text-slate-500 hover:text-slate-300 cursor-pointer">Zaboravili ste lozinku?</button>}
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
