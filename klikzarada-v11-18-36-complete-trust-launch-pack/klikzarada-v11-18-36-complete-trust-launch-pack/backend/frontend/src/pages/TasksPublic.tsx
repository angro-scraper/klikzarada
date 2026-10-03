import { useEffect, useState } from 'react'
import { Btn, Card, EmptyState, Select } from '../components/ui'
import { api, type Task } from '../lib/api'
import PublicTaskDetail, { proofName } from './PublicTaskDetail'
import { taskRewardDetails } from '../lib/taskPresentation'

const categoryColors = ['bg-blue-100 text-blue-700', 'bg-violet-100 text-violet-700', 'bg-teal-100 text-teal-700', 'bg-emerald-100 text-emerald-700', 'bg-amber-100 text-amber-700']

function taskView(task: Task) {
  return {
    ...task,
    cat: task.category,
    catColor: categoryColors[task.id % categoryColors.length],
    reward: taskRewardDetails(task).total,
    time: taskRewardDetails(task).time,
    proof: proofName(task.proof_required),
    level: task.min_user_level,
  }
}

export default function TasksPublic({ onNavigate }: { onNavigate: (id: string) => void }) {
  const [cat, setCat] = useState('')
  const [level, setLevel] = useState('')
  const [query, setQuery] = useState('')
  // Banneri mogu voditi direktno na jedan objavljen zadatak.
  const selectedTaskId = Number(window.location.pathname.match(/^\/zadaci\/(\d+)\/?$/)?.[1] || new URLSearchParams(window.location.search).get('task')) || 0
  const [sort, setSort] = useState<'recommended' | 'reward' | 'time'>('recommended')
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (selectedTaskId) return
    let active = true
    api.publicTasks()
      .then(result => {
        if (!active) return
        if (!Array.isArray(result?.tasks)) throw new Error('Lista zadataka trenutno nije dostupna.')
        setTasks(result.tasks)
      })
      .catch(caught => { if (active) setError(caught instanceof Error ? caught.message : 'Zadaci nisu učitani.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [selectedTaskId])

  const filtered = tasks.map(taskView).filter(t => {
    if (cat && t.cat !== cat) return false
    if (level && t.level !== level) return false
    const searchable = `${t.title} ${t.description} ${t.cat}`.toLocaleLowerCase('sr')
    if (query.trim() && !searchable.includes(query.trim().toLocaleLowerCase('sr'))) return false
    return true
  }).sort((left, right) => {
    if (sort === 'reward') return right.reward_rsd - left.reward_rsd
    if (sort === 'time') return left.estimated_minutes - right.estimated_minutes
    return Number(right.sponsored) - Number(left.sponsored) || Number(right.featured) - Number(left.featured) || right.reward_rsd - left.reward_rsd
  })
  const categories = [...new Set(tasks.map(task => task.category).filter(Boolean))].sort()
  const levels = [...new Set(tasks.map(task => task.min_user_level).filter(Boolean))].sort()
  const hasFilters = Boolean(cat || level || query.trim())

  if (selectedTaskId) return <PublicTaskDetail taskId={selectedTaskId} />

  return (
    <div className="min-h-screen bg-mint-50 text-ink">
      <header className="bg-white border-b border-frame sticky top-0 z-40 shadow-sm">
        <div className="w-full max-w-none px-4 sm:px-6 xl:px-8 2xl:px-10 h-14 flex items-center gap-3">
          <button onClick={() => onNavigate('home')} className="flex items-center gap-2 cursor-pointer">
            <div className="w-7 h-7 bg-blue-600 rounded-lg flex items-center justify-center font-bold text-white text-xs shadow-sm">K</div>
            <span className="font-bold text-ink text-sm">KlikZarada</span>
          </button>
          <div className="flex-1" />
          <Btn onClick={() => onNavigate('login')} variant="ghost" size="sm">Prijava</Btn>
          <Btn onClick={() => onNavigate('register')} size="sm">Registruj se</Btn>
        </div>
      </header>

      <div className="w-full max-w-none px-4 py-8 sm:px-6 xl:px-8 2xl:px-10">
        <div className="mb-6">
          <h1 className="text-2xl font-extrabold text-ink">Aktivni zadaci</h1>
          <p className="text-ink-2 text-sm mt-1">Prijavi se da bi mogao/la da preuzimaš zadatke i zarađuješ.</p>
        </div>

        {/* Filters */}
          <div className="grid gap-3 mb-5 sm:grid-cols-2 lg:grid-cols-4">
          <label className="sr-only" htmlFor="task-search">Pretraži zadatke</label>
          <input id="task-search" value={query} onChange={event => setQuery(event.target.value)} placeholder="Pretraži zadatke" className="w-full rounded-lg border border-frame bg-white px-3 py-2 text-sm text-ink outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100" />
          <Select
            label="Kategorija"
            options={[
              { value: '', label: 'Sve kategorije' },
              ...categories.map(category => ({ value: category, label: category })),
            ]}
            value={cat}
            onChange={setCat}
          />
          <Select
            label="Nivo"
            options={[
              { value: '', label: 'Svi nivoi' },
              ...levels.map(item => ({ value: item, label: item })),
            ]}
            value={level}
            onChange={setLevel}
          />
          <Select label="Redosled" value={sort} onChange={value => setSort(value as typeof sort)} options={[{ value: 'recommended', label: 'Preporučeni redosled' }, { value: 'reward', label: 'Najveća nagrada' }, { value: 'time', label: 'Najkraće trajanje' }]} />
          </div>

        {/* Guest notice */}
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-5 flex flex-col sm:flex-row items-start sm:items-center gap-3">
          <span className="text-blue-800 text-sm flex-1">
            🔐 <strong>Prijavljivanje obavezno.</strong> Registruj se besplatno da bi mogao/la da preuzimaš zadatke, pratiš dokaze i zatražiš isplatu na sačuvanu PayPal adresu.
          </span>
          <Btn onClick={() => onNavigate('register')} size="sm">Registruj se besplatno</Btn>
        </div>

        {error && <div className="mb-5 rounded-xl border border-coral-200 bg-coral-50 p-4 text-sm text-coral-700" role="alert">{error}</div>}
        {!loading && !error && <div className="mb-4 flex items-center gap-4 text-sm text-ink-2"><span>{filtered.length} rezultata</span>{hasFilters && <button onClick={() => { setCat(''); setLevel(''); setQuery('') }} className="font-semibold text-blue-700 underline">Poništi filtere</button>}</div>}

        {/* Task list */}
        {loading ? (
          <div className="py-14 text-center text-sm text-ink-2">Učitavanje zadataka...</div>
        ) : error ? <button onClick={() => window.location.reload()} className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white">Pokušaj ponovo</button> : filtered.length === 0 ? (
          <EmptyState
            icon="📭"
            title={hasFilters ? 'Nema zadataka za odabrane filtere' : 'Trenutno nema dostupnih zadataka'}
            description={hasFilters ? 'Poništi filtere ili promeni pretragu.' : 'Proveri ponovo kasnije.'}
          />
        ) : (
          <div className="flex flex-col gap-3">
            {filtered.map(task => (
              <Card key={task.id} className="p-5 hover:shadow-md transition-shadow">
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-1.5">
                      <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${task.catColor}`}>{task.cat}</span>
                      {task.sponsored && <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-violet-100 text-violet-700 border border-violet-200">Sponzorisano · {task.promotion_type === 'featured' ? 'Istaknuto' : 'Prioritet'}</span>}
                      <span className="text-[11px] text-ink-3 bg-gray-100 px-2 py-0.5 rounded-full">Nivo: {task.level}</span>
                      <span className="text-[11px] font-semibold text-emerald-700">Dostupno</span>
                    </div>
                    <h3 className="font-semibold text-ink">{task.title}</h3>
                    <div className="flex flex-wrap gap-4 mt-2">
                      <span className="text-xs text-ink-3">⏱ {task.time}</span>
                      {task.requires_tester_enrollment && <span className="text-xs text-ink-3">{taskRewardDetails(task).unit}</span>}
                      <span className="text-xs text-ink-3">📎 {task.proof}</span>
                      {task.target_city && <span className="text-xs text-ink-3">📍 {task.target_city}</span>}
                    </div>
                  </div>
                  <div className="sm:text-right sm:shrink-0">
                    <p className="font-mono font-bold text-emerald-600 text-lg">{task.reward}</p>
                    <a href={`/zadaci/${task.id}`} className="mt-2 inline-flex min-h-11 items-center rounded-lg bg-blue-600 px-3 text-xs font-bold text-white hover:bg-blue-700">Puni uslovi</a>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
