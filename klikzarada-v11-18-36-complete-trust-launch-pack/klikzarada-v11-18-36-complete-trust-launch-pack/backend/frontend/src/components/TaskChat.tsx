import { useEffect, useRef, useState } from 'react'
import { api, type TaskChatThread } from '../lib/api'

function messageContent(body: string) {
  return body.split(/(https?:\/\/[^\s]+)/g).map((part, index) => {
    if (!/^https?:\/\//i.test(part)) return <span key={index}>{part}</span>
    try {
      const url = new URL(part)
      if (url.protocol === 'https:' || url.protocol === 'http:') {
        return <a key={index} href={url.href} target="_blank" rel="noopener noreferrer" className="font-semibold underline underline-offset-2 break-all">{part}</a>
      }
    } catch { /* Neispravan link ostaje običan tekst. */ }
    return <span key={index}>{part}</span>
  })
}

export function TaskChat({ taskId, participantId, onClose }: { taskId: number; participantId: number; onClose: () => void }) {
  const [thread, setThread] = useState<TaskChatThread | null>(null)
  const [draft, setDraft] = useState('')
  const [error, setError] = useState('')
  const [sending, setSending] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let active = true
    const refresh = async () => {
      try {
        const result = await api.taskChat(taskId, participantId)
        if (active) { setThread(result); setError('') }
      } catch (reason) {
        if (active) setError(reason instanceof Error ? reason.message : 'Razgovor trenutno nije dostupan.')
      }
    }
    void refresh()
    const timer = window.setInterval(() => { if (document.visibilityState === 'visible') void refresh() }, 15000)
    const onKeyDown = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKeyDown)
    return () => { active = false; window.clearInterval(timer); window.removeEventListener('keydown', onKeyDown) }
  }, [taskId, participantId, onClose])

  useEffect(() => { endRef.current?.scrollIntoView({ block: 'end' }) }, [thread?.messages.length])

  const send = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const body = draft.trim()
    if (!body || sending) return
    setSending(true)
    setError('')
    try {
      await api.sendTaskChatMessage(taskId, participantId, body)
      setDraft('')
      setThread(await api.taskChat(taskId, participantId))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Poruka nije poslata. Pokušaj ponovo.')
    } finally {
      setSending(false)
    }
  }

  return <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6">
    <button type="button" aria-label="Zatvori razgovor" className="absolute inset-0 bg-slate-950/60 backdrop-blur-sm" onClick={onClose} />
    <section role="dialog" aria-modal="true" aria-label="Razgovor uz zadatak" className="relative flex h-[min(680px,90vh)] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-frame bg-white shadow-2xl">
      <header className="flex items-start justify-between gap-3 border-b border-frame bg-mint-50 px-5 py-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-blue-700">Razgovor uz zadatak</p>
          <h2 className="mt-1 text-lg font-bold text-ink">{thread?.task_title || 'Učitavanje razgovora...'}</h2>
          {thread && <p className="text-sm text-ink-2">{thread.participant_name} i oglašivač</p>}
        </div>
        <button type="button" onClick={onClose} aria-label="Zatvori" className="rounded-lg px-2 py-1 text-xl text-ink-2 hover:bg-white hover:text-ink">×</button>
      </header>
      <div className="flex-1 space-y-3 overflow-y-auto bg-slate-50/70 p-4 sm:p-5" aria-live="polite">
        {!thread && !error && <p className="text-center text-sm text-ink-2">Učitavanje poruka...</p>}
        {thread?.messages.length === 0 && <p className="rounded-xl border border-dashed border-blue-200 bg-white p-5 text-center text-sm text-ink-2">Još nema poruka. Ovde možeš poslati pitanje ili test link koji se odnosi samo na ovaj zadatak.</p>}
        {thread?.messages.map(message => {
          const mine = message.sender_id === thread.current_user_id
          return <div key={message.id} className={`flex ${mine ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[88%] rounded-2xl px-4 py-3 shadow-sm ${mine ? 'bg-blue-600 text-white' : 'border border-frame bg-white text-ink'}`}>
              <p className="mb-1 text-xs font-bold opacity-75">{mine ? 'Ti' : 'Druga strana'}</p>
              <p className="whitespace-pre-wrap break-words text-sm leading-6">{messageContent(message.body)}</p>
              {message.created_at && <p className="mt-1 text-right text-[11px] opacity-70">{new Intl.DateTimeFormat('sr-RS', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(message.created_at))}</p>}
            </div>
          </div>
        })}
        <div ref={endRef} />
      </div>
      <form onSubmit={send} className="border-t border-frame bg-white p-4">
        {error && <p role="alert" className="mb-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
        <label htmlFor="task-chat-message" className="mb-2 block text-sm font-semibold text-ink">Poruka</label>
        <div className="flex items-end gap-2">
          <textarea id="task-chat-message" rows={2} maxLength={2000} value={draft} onChange={event => setDraft(event.target.value)} placeholder="Napiši poruku ili nalepi test link..." className="min-w-0 flex-1 resize-none rounded-xl border border-frame px-3 py-2 text-sm text-ink outline-none focus:border-blue-500" />
          <button type="submit" disabled={!thread || !draft.trim() || sending} className="rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-50">{sending ? 'Šaljem...' : 'Pošalji'}</button>
        </div>
        <p className="mt-2 text-xs text-ink-3">Samo za dogovor oko ovog zadatka. Dokazi i odobrenja se i dalje šalju kroz zadatak.</p>
      </form>
    </section>
  </div>
}
