import { useEffect, useState } from 'react'
import { api } from '../lib/api'

type Terms = Awaited<ReturnType<typeof api.publicServiceTerms>>

export function ServiceTerms() {
  const [terms, setTerms] = useState<Terms | null>(null)
  const [error, setError] = useState(false)
  useEffect(() => {
    let active = true
    void api.publicServiceTerms().then(value => {
      if (!active) return
      if (typeof value?.min_withdrawal_rsd !== 'number' || !Number.isFinite(value.min_withdrawal_rsd) || typeof value?.wallet_currency !== 'string' || typeof value?.support_email !== 'string') {
        setError(true)
        return
      }
      setTerms(value)
    }).catch(() => { if (active) setError(true) })
    return () => { active = false }
  }, [])
  return <div className="rounded-2xl border border-blue-200 bg-blue-50/70 p-5 text-sm leading-6 text-ink-2" role="status">
    <h2 className="text-lg font-bold text-ink">Nagrade i isplate</h2>
    {terms ? <>
      <p className="mt-2">Saldo se vodi u {terms.wallet_currency}. Minimalni iznos za zahtev za isplatu je <strong className="text-ink">{terms.min_withdrawal_rsd.toLocaleString('sr-RS')} RSD</strong>; potrebna je sačuvana PayPal adresa. Dnevna nagrada prelazi u raspoloživ saldo tek po odobrenju dokaza.</p>
      <p className="mt-2">Rok pregleda dokaza i rok obrade isplate još nisu objavljeni kao garantovani rokovi. Za status, prigovor ili problem sa pristupom piši na <a className="font-semibold text-blue-700 underline" href={`mailto:${terms.support_email}`}>{terms.support_email}</a>.</p>
    </> : <p className="mt-2">{error ? 'Trenutno ne možemo učitati pravila isplate. Proveri u novčaniku ili kontaktiraj podršku.' : 'Učitavanje potvrđenih pravila isplate...'}</p>}
  </div>
}
