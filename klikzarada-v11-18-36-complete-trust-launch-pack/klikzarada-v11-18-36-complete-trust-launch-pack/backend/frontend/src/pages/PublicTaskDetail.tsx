import { useEffect, useState } from 'react'
import { Card } from '../components/ui'
import { api, type Task } from '../lib/api'
import { taskRewardDetails } from '../lib/taskPresentation'

export function proofName(value: string): string {
  if (value?.trim().toLowerCase() === 'screenshot') return 'Snimak ekrana'
  if (value?.trim().toLowerCase() === 'text') return 'Pisani izveštaj'
  return value || 'Proveri uslove zadatka'
}

export default function PublicTaskDetail({ taskId }: { taskId: number }) {
  const [task, setTask] = useState<Task | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    void api.publicTask(taskId).then(result => {
      if (!active) return
      if (!result?.task || typeof result.task.title !== 'string' || typeof result.task.reward_rsd !== 'number') throw new Error('Uslovi zadatka trenutno nisu dostupni.')
      setTask(result.task)
    })
      .catch(caught => { if (active) setError(caught instanceof Error ? caught.message : 'Zadatak nije dostupan.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [attempt, taskId])

  useEffect(() => {
    const previous = document.title
    document.title = task ? `${task.title} | KlikZarada` : 'Uslovi zadatka | KlikZarada'
    return () => { document.title = previous }
  }, [task])

  const reward = task ? taskRewardDetails(task) : null
  const descriptionParts = task?.description.split(/\r?\n\s*\r?\n/) ?? []
  const firstParagraph = descriptionParts[0] ?? ''
  const summary = firstParagraph.length > 350 ? `${firstParagraph.slice(0, 347)}...` : firstParagraph
  const additionalDescription = [firstParagraph.length > 350 ? firstParagraph.slice(347) : '', ...descriptionParts.slice(1)].filter(Boolean).join('\n\n')
  const hasFullSpecification = Boolean(task && additionalDescription.trim())
  return <div className="min-h-screen bg-mint-50 text-ink">
    <header className="sticky top-0 z-40 border-b border-frame bg-white/95"><div className="mx-auto flex h-16 max-w-6xl items-center gap-3 px-4"><a href="/" className="flex items-center gap-2 font-bold"><span className="grid h-8 w-8 place-items-center rounded-lg bg-blue-600 text-sm text-white">K</span>KlikZarada</a><div className="flex-1" /><a className="text-sm font-semibold text-blue-700" href={`/prijava?task=${taskId}`}>Prijava</a></div></header>
    <main className="mx-auto max-w-6xl px-4 py-8 md:py-12">
      <a href="/zadaci" className="text-sm font-semibold text-blue-700 hover:underline">← Svi dostupni zadaci</a>
      {loading ? <p className="mt-8" role="status">Učitavanje uslova zadatka...</p> : error || !task ? <Card className="mt-8 p-6"><h1 className="text-xl font-bold">Zadatak nije dostupan</h1><p className="mt-2 text-sm text-ink-2">{error || 'Kampanja je možda završena.'}</p><button onClick={() => setAttempt(value => value + 1)} className="mt-4 min-h-11 rounded-lg bg-blue-600 px-4 text-sm font-semibold text-white">Pokušaj ponovo</button></Card> : <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
        <div className="space-y-5">
          <div><p className="text-xs font-bold uppercase tracking-widest text-blue-700">{task.category}</p><h1 className="mt-2 text-3xl font-extrabold leading-tight md:text-4xl">{task.title}</h1><p className="mt-4 whitespace-pre-line leading-7 text-ink-2">{summary}</p></div>
          {hasFullSpecification && <Card className="p-5 md:p-6"><h2 className="text-lg font-bold">Opis i specifikacija</h2><p className="mt-4 whitespace-pre-line text-sm leading-7 text-ink-2">{additionalDescription}</p></Card>}
          <Card className="p-5 md:p-6"><h2 className="text-lg font-bold">Koraci i pristup</h2>{task.requires_tester_enrollment ? <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm leading-7 text-ink-2"><li>Pročitaj uslove i prijavi email za poziv na testiranje.</li><li>Sačekaj da oglašivač potvrdi pristup. Prijava sama ne otvara test-link.</li><li>Po potvrdi otvori link sa svog naloga. {reward?.reliable ? `Testiraj najmanje ${task.tester_daily_minutes} minuta dnevno tokom ${task.tester_duration_days} dana.` : 'Trajanje proveri sa oglašivačem pre početka.'}</li><li>Pošalji dnevni izveštaj; svaki dan se odobrava zasebno.</li></ol> : <p className="mt-3 whitespace-pre-line text-sm leading-7 text-ink-2">{task.instructions || 'Koraci nisu navedeni u javnim uslovima. Zatraži pojašnjenje pre početka.'}</p>}</Card>
          <Card className="p-5 md:p-6"><h2 className="text-lg font-bold">Dokaz i odobravanje</h2><p className="mt-3 whitespace-pre-line text-sm leading-7 text-ink-2">Traženi dokaz: {proofName(task.proof_required)}.</p>{task.example_proof && <p className="mt-2 text-sm leading-6 text-ink-2">Primer: {task.example_proof}</p>}<p className="mt-2 text-sm leading-6 text-ink-2">{reward?.approval} Odluku i eventualni zahtev za dopunu vidiš na nalogu.</p>{!task.requires_tester_enrollment && <p className="mt-2 text-sm leading-6 text-ink-2">Rok za slanje dokaza nakon početka: {task.submission_deadline_hours} h. Dozvoljene dopune: {task.max_proof_revisions}.</p>}<p className="mt-2 text-sm leading-6 text-ink-2">Kod spora ili izostanka odgovora obrati se podršci kroz tiket. Rok pregleda nije naveden u uslovima ove kampanje.</p></Card>
          <Card className="p-5 md:p-6"><h2 className="text-lg font-bold">Uslovi učešća</h2><dl className="mt-4 grid gap-4 text-sm sm:grid-cols-2"><div><dt className="font-semibold">Uređaj i sistem</dt><dd className="text-ink-2">{task.tester_store === 'ios' ? 'iPhone ili iPad sa podržanim iOS/iPadOS i TestFlight aplikacijom' : task.tester_store === 'android' ? 'Android uređaj i odgovarajući Google Play nalog' : 'Prema opisu zadatka'}</dd></div><div><dt className="font-semibold">Lokacija</dt><dd className="text-ink-2">{task.target_city || 'Nije posebno navedena'}</dd></div><div><dt className="font-semibold">Jezik</dt><dd className="text-ink-2">Nije posebno naveden u uslovima kampanje</dd></div><div><dt className="font-semibold">Uzrast</dt><dd className="text-ink-2">{task.target_age_group || 'Nije posebno naveden'}</dd></div><div><dt className="font-semibold">Nivo</dt><dd className="text-ink-2">{task.min_user_level || 'Nije naveden'}</dd></div><div><dt className="font-semibold">Početak</dt><dd className="text-ink-2">{task.requires_tester_enrollment ? 'Po pojedinačnoj potvrdi pristupa' : task.starts_at ? new Date(task.starts_at).toLocaleDateString('sr-RS') : 'Kada preuzmeš dostupan zadatak'}</dd></div><div><dt className="font-semibold">Učešće</dt><dd className="text-ink-2">{reward?.participation}</dd></div><div><dt className="font-semibold">Dodatni uslovi</dt><dd className="text-ink-2">{task.target_interests || 'Nisu posebno navedeni'}</dd></div><div><dt className="font-semibold">Rok kampanje</dt><dd className="text-ink-2">{task.deadline_text || 'Nije posebno naveden'}</dd></div><div><dt className="font-semibold">Propušten dan</dt><dd className="text-ink-2">Pravila nisu posebno navedena; obrati se oglašivaču pre prekida testa.</dd></div><div><dt className="font-semibold">Oglašivač</dt><dd className="text-ink-2">{task.advertiser_name || 'Oglašivač na platformi'}</dd></div></dl></Card>
        </div>
        <aside className="order-first lg:order-last"><Card className="p-5 lg:sticky lg:top-24"><p className="mb-3 text-sm font-semibold text-ink lg:hidden">{task.title}</p><p className="text-xs font-bold uppercase tracking-widest text-ink-3">Moguća nagrada</p><p className="mt-2 text-2xl font-extrabold text-emerald-700">{reward?.total}</p><p className="mt-3 font-semibold">{reward?.unit}</p><p className="mt-2 text-sm text-ink-2">{reward?.time}</p><p className="mt-4 border-t border-frame pt-4 text-sm text-ink-2">{reward?.available ? `${reward.places} slobodnih mesta` : 'Trenutno nema slobodnih mesta'}</p>{reward?.available && <div className="mt-5 grid gap-2"><a href={`/registracija?task=${task.id}`} className="grid min-h-11 place-items-center rounded-lg bg-blue-600 px-4 text-center text-sm font-bold text-white hover:bg-blue-700">Registruj se i nastavi</a><a href={`/prijava?task=${task.id}`} className="grid min-h-11 place-items-center rounded-lg border border-blue-200 px-4 text-center text-sm font-bold text-blue-700 hover:bg-blue-50">Već imam nalog</a></div>}<p className="mt-4 text-xs leading-5 text-ink-3">Pre prijave pročitaj punu specifikaciju ispod. Prijava nije odobrenje: kod zatvorenog testa pristup potvrđuje oglašivač, a odobreni dani obračunavaju se pojedinačno.</p></Card></aside>
      </div>}
    </main>
    <footer className="border-t border-frame bg-white px-4 py-6 text-center text-xs"><a href="/pomoc" className="font-semibold text-blue-700">Pomoć</a> · <a href="/pravila" className="font-semibold text-blue-700">Pravila i privatnost</a></footer>
  </div>
}
