import { useEffect, useState } from 'react'
import { Btn, Input, Alert } from '../components/ui'
import { ApiRequestError, api, deviceFingerprint, type RegistrationFailureReason } from '../lib/api'

type Mode = 'login' | 'register' | 'advertiser-login' | 'advertiser-register' | 'admin-login'

function registrationFailureReason(caught: unknown): RegistrationFailureReason {
  if (caught instanceof ApiRequestError) {
    if (caught.status === 0) return 'network_error'
    if (caught.status >= 500) return 'server_error'
    if (caught.status === 422) return 'validation'
  }
  const message = (caught instanceof Error ? caught.message : '').toLocaleLowerCase('sr-RS')
  if (message.includes('email adresa je već registrovana')) return 'email_taken'
  if (message.includes('broj telefona je već povezan')) return 'phone_taken'
  if (message.includes('moraš prihvatiti')) return 'terms_missing'
  if (message.includes('telefon') && message.includes('7 cifara')) return 'invalid_phone'
  if (message.includes('referral')) return 'invalid_referral'
  if (message.includes('422') || message.includes('valid')) return 'validation'
  return 'request_error'
}

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
  const [referralFromLink, setReferralFromLink] = useState(false)
  const [acceptTerms, setAcceptTerms] = useState(false)
  const [website, setWebsite] = useState('')
  const [forgotPassword, setForgotPassword] = useState(false)
  const [resetToken, setResetToken] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [notice, setNotice] = useState('')

  const isAdvertiser = mode === 'advertiser-login' || mode === 'advertiser-register'
  const isRegister = mode === 'register' || mode === 'advertiser-register'
  const isAdmin = mode === 'admin-login'
  const selectedTaskId = Number(new URLSearchParams(window.location.search).get('task')) || 0

  function clearFieldError(field: string) {
    setFieldErrors(current => {
      if (!current[field]) return current
      const next = { ...current }
      delete next[field]
      return next
    })
  }

  function navigateAuth(destination: string) {
    if (selectedTaskId && (destination === 'login' || destination === 'register')) {
      window.location.assign(`/${destination === 'login' ? 'prijava' : 'registracija'}?task=${selectedTaskId}`)
    } else onNavigate(destination)
  }

  // Route changes reuse this component, so its selected role must follow the URL.
  useEffect(() => {
    setMode(initialMode)
  }, [initialMode])

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

  useEffect(() => {
    if (!isRegister) return
    // This is intentionally non-blocking: an analytics outage must never stop registration.
    void api.trackPublicFunnel('registration_opened').catch(() => undefined)
  }, [isRegister])

  useEffect(() => {
    if (!isRegister || isAdvertiser) return
    const rawCode = new URLSearchParams(window.location.search).get('ref') || ''
    const code = rawCode.toUpperCase().replace(/[^A-Z0-9]/g, '')
    if (code.length < 2) return
    setReferral(code)
    setReferralFromLink(true)
  }, [isAdvertiser, isRegister])

  async function handleSubmit() {
    const missing: Record<string, string> = {}
    if (!email.trim()) missing.email = 'Unesi email adresu.'
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) missing.email = 'Unesi ispravnu email adresu.'
    if (!password) missing.password = 'Unesi lozinku.'
    else if (isRegister && password.length < 8) missing.password = 'Lozinka mora imati najmanje 8 znakova.'
    if (isRegister) {
      if (!name.trim()) missing.name = isAdvertiser && advertiserType === 'business' ? 'Unesi naziv firme.' : 'Unesi ime i prezime.'
      if (!acceptTerms) missing.terms = 'Prihvati uslove korišćenja da bi nastavio/la.'
    }
    if (Object.keys(missing).length) {
      setFieldErrors(missing)
      setError(isRegister ? 'Za registraciju još nedostaje: proveri označena polja.' : 'Proveri označena polja.')
      return
    }
    setSubmitted(true)
    setError('')
    setFieldErrors({})
    try {
      if (isRegister) void api.trackPublicFunnel('registration_submitted').catch(() => undefined)
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
            website,
          })
        : await api.login(email, password)
      if (!isRegister && ((isAdmin && result.user.role !== 'admin') || (isAdvertiser && result.user.role === 'korisnik') || (!isAdmin && !isAdvertiser && result.user.role !== 'korisnik'))) {
        await api.logout().catch(() => undefined)
        setError(`Nalog ${result.user.email} je ${result.user.role === 'admin' ? 'administratorski' : result.user.role === 'oglasivac' ? 'oglašivački' : 'korisnički'}. Prijavi se kroz odgovarajuću sekciju; uloge se ne menjaju izborom obrasca.`)
        return
      }
      if (result.user.role === 'admin') onNavigate('admin')
      else if (result.user.role === 'korisnik' && selectedTaskId) window.location.assign(`/korisnik/zadaci/${selectedTaskId}`)
      else onNavigate(result.user.role === 'oglasivac' ? 'advertiser' : 'dashboard')
    } catch (caught) {
      if (isRegister) {
        const reason = registrationFailureReason(caught)
        void api.trackPublicFunnel('registration_failed', registrationFailureReason(caught)).catch(() => undefined)
        const field = reason === 'email_taken' ? 'email' : ['phone_taken', 'invalid_phone'].includes(reason) ? 'phone' : reason === 'invalid_referral' ? 'referral' : reason === 'terms_missing' ? 'terms' : ''
        if (field) setFieldErrors({ [field]: caught instanceof Error ? caught.message : 'Proveri ovo polje.' })
      }
      setError(caught instanceof Error ? caught.message : 'Prijava nije uspela.')
    } finally {
      setSubmitted(false)
    }
  }

  async function handlePasswordReset() {
    if (password.length < 8) {
      setFieldErrors({ password: 'Nova lozinka mora imati najmanje 8 znakova.' })
      return
    }
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
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      setFieldErrors({ email: 'Unesi ispravnu email adresu.' })
      return
    }
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
              onClick={() => navigateAuth(isRegister ? 'register' : 'login')}
              className={`flex-1 py-2 text-sm font-medium transition-colors cursor-pointer ${
                !isAdvertiser ? 'bg-blue-500 text-white' : 'bg-navy-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              Korisnik
            </button>
            <button
              onClick={() => onNavigate(isRegister ? 'advertiser-register' : 'advertiser-login')}
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

            <form noValidate onSubmit={event => { event.preventDefault(); void (resetToken ? handlePasswordReset() : forgotPassword ? requestReset() : handleSubmit()) }} className="flex flex-col gap-4">
              {!resetToken && !forgotPassword && isRegister && isAdvertiser && (
                <div className="flex flex-col gap-1.5">
                  <span className="text-xs font-semibold text-ink-2 uppercase tracking-wide">Tip oglašivača</span>
                  <div className="grid grid-cols-2 gap-2">
                    <button type="button" onClick={() => setAdvertiserType('business')} className={`rounded-lg border px-3 py-2 text-sm font-semibold cursor-pointer transition-colors ${advertiserType === 'business' ? 'border-blue-500 bg-blue-50 text-blue-700' : 'border-frame bg-white text-ink-2 hover:border-blue-200'}`}>Firma</button>
                    <button type="button" onClick={() => setAdvertiserType('private')} className={`rounded-lg border px-3 py-2 text-sm font-semibold cursor-pointer transition-colors ${advertiserType === 'private' ? 'border-blue-500 bg-blue-50 text-blue-700' : 'border-frame bg-white text-ink-2 hover:border-blue-200'}`}>Privatno lice</button>
                  </div>
                  <p className="text-xs text-ink-3">Privatno lice koristi svoje ime i prezime; firma koristi registrovani naziv.</p>
                </div>
              )}
              {!resetToken && !forgotPassword && isRegister && (
                <Input
                  label={isAdvertiser ? advertiserType === 'business' ? 'Naziv firme' : 'Ime i prezime' : 'Ime i prezime'}
                  placeholder={isAdvertiser && advertiserType === 'business' ? 'Moja Firma d.o.o.' : 'Marko Marković'}
                  value={name}
                  onChange={value => { setName(value); clearFieldError('name') }}
                  autoComplete={isAdvertiser && advertiserType === 'business' ? 'organization' : 'name'}
                  error={fieldErrors.name}
                />
              )}
              {!resetToken && <Input label="Email adresa" type="email" placeholder="email@primer.rs" value={email} onChange={value => { setEmail(value); clearFieldError('email') }} autoComplete="email" error={fieldErrors.email} />}
              {!resetToken && !forgotPassword && isRegister && !isAdvertiser && (
                <Input label="Telefon (opciono)" type="tel" placeholder="npr. +381 60 123 4567" value={phone} onChange={value => { setPhone(value); clearFieldError('phone') }} autoComplete="tel" error={fieldErrors.phone} />
              )}
              {!forgotPassword && <Input label={resetToken ? 'Nova lozinka' : 'Lozinka'} type="password" placeholder="••••••••" value={password} onChange={value => { setPassword(value); clearFieldError('password') }} autoComplete={resetToken || isRegister ? 'new-password' : 'current-password'} error={fieldErrors.password} />}
              {(resetToken || isRegister) && !forgotPassword && <p className="-mt-2 text-xs text-slate-400">Lozinka mora imati najmanje 8 znakova.</p>}
              {!resetToken && !forgotPassword && isRegister && !isAdvertiser && (
                <>
                  <Input label="Referral kod (opciono)" placeholder="Unesi kod iz referral linka ili ostavi prazno" value={referral} onChange={value => { setReferral(value.toUpperCase()); setReferralFromLink(false); clearFieldError('referral') }} error={fieldErrors.referral} />
                  {referralFromLink && <p className="-mt-2 text-xs text-emerald-700">Referral kod je preuzet iz prijateljevog linka i biće proveren pri kreiranju naloga.</p>}
                  {!referralFromLink && <p className="-mt-2 text-xs text-ink-3">Nemaš kod? Ostavi polje prazno. Ne unosi primer ili nasumičan tekst.</p>}
                </>
              )}

              {!resetToken && !forgotPassword && isRegister && (
                <div className="absolute -left-[10000px]" aria-hidden="true">
                  <label htmlFor="registration-website">Website</label>
                  <input id="registration-website" name="website" tabIndex={-1} autoComplete="off" value={website} onChange={event => setWebsite(event.target.value)} />
                </div>
              )}
              {!resetToken && !forgotPassword && isRegister && (
                <label className="flex gap-2 items-start text-xs text-slate-400 cursor-pointer">
                  <input type="checkbox" checked={acceptTerms} onChange={event => { setAcceptTerms(event.target.checked); clearFieldError('terms') }} className="mt-0.5" aria-invalid={Boolean(fieldErrors.terms)} />
                  <span>Prihvatam <a href="/pravila" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300">Uslove korišćenja i Politiku privatnosti</a>.</span>
                </label>
              )}
              {fieldErrors.terms && <p className="-mt-2 text-xs font-semibold text-red-500">{fieldErrors.terms}</p>}

              <Btn
                type="submit"
                disabled={submitted}
                className="w-full justify-center"
              >
                {submitted
                  ? '⏳ Učitavam...'
                  : resetToken ? 'Sačuvaj novu lozinku' : forgotPassword ? 'Pošalji link za reset' : isRegister ? 'Kreiraj nalog' : 'Prijavi se'}
              </Btn>
            </form>

            <div className="mt-5 pt-5 border-t border-border text-center">
              {resetToken || forgotPassword ? (
                <button onClick={() => { setResetToken(''); setForgotPassword(false); setError('') }} className="text-sm text-blue-400 hover:text-blue-300 cursor-pointer">Nazad na prijavu</button>
              ) : isAdmin ? (
                <p className="text-sm text-slate-400">Admin nalog kreira vlasnik platforme kroz zaštićena Render podešavanja.</p>
              ) : isRegister ? (
                <p className="text-sm text-slate-400">
                  Već imaš nalog?{' '}
                  <button
                    onClick={() => navigateAuth(isAdvertiser ? 'advertiser-login' : 'login')}
                    className="text-blue-400 hover:text-blue-300 cursor-pointer"
                  >
                    Prijavi se
                  </button>
                </p>
              ) : (
                <p className="text-sm text-slate-400">
                  Nemaš nalog?{' '}
                  <button
                    onClick={() => navigateAuth(isAdvertiser ? 'advertiser-register' : 'register')}
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
            <a href="/pravila" target="_blank" rel="noopener noreferrer" className="text-slate-500 hover:text-slate-400">Uslove korišćenja</a>
            {' '}i{' '}
            <a href="/pravila" target="_blank" rel="noopener noreferrer" className="text-slate-500 hover:text-slate-400">Politiku privatnosti</a>.
          </p>
        </div>
      </div>
    </div>
  )
}
