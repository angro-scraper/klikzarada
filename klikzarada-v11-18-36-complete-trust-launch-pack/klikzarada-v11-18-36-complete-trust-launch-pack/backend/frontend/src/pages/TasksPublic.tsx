import { useEffect, useState } from 'react'
import { Btn, Card, StatusBadge, EmptyState, Select } from '../components/ui'
import { api, formatRsd } from '../lib/api'

type Task = { id: number; title: string; category: string; reward_rsd: number; estimated_minutes: number; proof_required: string; min_user_level: string; status: string }

export default function TasksPublic({ onNavigate }: { onNavigate: (id: string) => void }) {
  const [cat, setCat] = useState('')
  const [level, setLevel] = useState('')
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api<{ tasks: Task[] }>('/public/tasks')
      .then(result => setTasks(result.tasks))
      .finally(() => setLoading(false))
  }, [])

  const filtered = tasks.filter(t => {
    if (cat && t.category !== cat) return false
    if (level && t.min_user_level !== level) return false
    return true
  })

  return (
    <div className="min-h-screen bg-mint-50 text-ink">
      <header className="bg-white border-b border-frame sticky top-0 z-40 shadow-sm">
        <div className="max-w-5xl mx-auto px-4 h-14 flex items-center gap-3">
          <button onClick={() => onNavigate('home')} className="flex items-center gap-2 cursor-pointer">
            <div className="w-7 h-7 bg-blue-600 rounded-lg flex items-center justify-center font-bold text-white text-xs shadow-sm">K</div>
            <span className="font-bold text-ink text-sm">KlikZarada</span>
          </button>
          <div className="flex-1" />
          <Btn onClick={() => onNavigate('login')} variant="ghost" size="sm">Prijava</Btn>
          <Btn onClick={() => onNavigate('register')} size="sm">Registruj se</Btn>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-4 py-8">
        <div className="mb-6">
          <h1 className="text-2xl font-extrabold text-ink">Aktivni zadaci</h1>
          <p className="text-ink-2 text-sm mt-1">Prijavi se da bi mogao/la da preuzimaš zadatke i zarađuješ.</p>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3 mb-5">
          <Select
            options={[
              { value: '', label: 'Sve kategorije' },
              ...Array.from(new Set(tasks.map(task => task.category))).map(value => ({ value, label: value })),
            ]}
            value={cat}
            onChange={setCat}
          />
          <Select
            options={[
              { value: '', label: 'Svi nivoi' },
              ...Array.from(new Set(tasks.map(task => task.min_user_level))).map(value => ({ value, label: value })),
            ]}
            value={level}
            onChange={setLevel}
          />
        </div>

        {/* Guest notice */}
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-5 flex flex-col sm:flex-row items-start sm:items-center gap-3">
          <span className="text-blue-800 text-sm flex-1">
            🔐 <strong>Prijavljivanje obavezno.</strong> Registruj se besplatno da bi mogao/la da preuzimaš zadatke i primaš isplate na račun.
          </span>
          <Btn onClick={() => onNavigate('register')} size="sm">Registruj se besplatno</Btn>
        </div>

        {/* Task list */}
        {loading ? <p className="text-sm text-ink-3">Učitavam dostupne zadatke...</p> : filtered.length === 0 ? (
          <EmptyState
            icon="📭"
            title="Nema zadataka za odabrane filtere"
            description="Pokušaj sa drugačijim filterima ili se vrati malo kasnije."
          />
        ) : (
          <div className="flex flex-col gap-3">
            {filtered.map(task => (
              <Card key={task.id} className="p-5 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-1.5">
                      <span className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">{task.category}</span>
                      <span className="text-[11px] text-ink-3 bg-gray-100 px-2 py-0.5 rounded-full">Nivo: {task.min_user_level}</span>
                      <StatusBadge status={task.status === 'active' ? 'aktivno' : task.status} />
                    </div>
                    <h3 className="font-semibold text-ink">{task.title}</h3>
                    <div className="flex flex-wrap gap-4 mt-2">
                      <span className="text-xs text-ink-3">⏱ {task.estimated_minutes} min</span>
                      <span className="text-xs text-ink-3">📎 {task.proof_required}</span>
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="font-mono font-bold text-emerald-600 text-lg">{formatRsd(task.reward_rsd)}</p>
                    <Btn onClick={() => onNavigate('register')} size="sm" className="mt-2">Preuzmi</Btn>
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
