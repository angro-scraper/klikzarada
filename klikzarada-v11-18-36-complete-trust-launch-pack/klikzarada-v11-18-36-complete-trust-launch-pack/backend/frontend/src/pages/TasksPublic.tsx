import { useState } from 'react'
import { Btn, Card, StatusBadge, EmptyState, Select } from '../components/ui'

const tasks = [
  { id: 1, title: 'Lajkuj i komentiraj objavu na Instagram-u', cat: 'Društvene mreže', catColor: 'bg-blue-100 text-blue-700', reward: '35 RSD', time: '5 min', proof: 'Screenshot', level: 'Explorer', status: 'aktivno' },
  { id: 2, title: 'Popuni anketu o navikama u kupovini', cat: 'Ankete', catColor: 'bg-violet-100 text-violet-700', reward: '80 RSD', time: '10 min', proof: 'Kod potvrde', level: 'Explorer', status: 'aktivno' },
  { id: 3, title: 'Ostavi recenziju aplikacije na Google Play-u', cat: 'Recenzije', catColor: 'bg-teal-100 text-teal-700', reward: '120 RSD', time: '8 min', proof: 'Screenshot + link', level: 'Trusted', status: 'aktivno' },
  { id: 4, title: 'Pogledaj video reklamu i odgovori na pitanja', cat: 'Video', catColor: 'bg-emerald-100 text-emerald-700', reward: '50 RSD', time: '6 min', proof: 'Screenshot', level: 'Explorer', status: 'aktivno' },
  { id: 5, title: 'Registruj se na sajtu partnera i potvrdi email', cat: 'Web zadaci', catColor: 'bg-amber-100 text-amber-700', reward: '200 RSD', time: '15 min', proof: 'Screenshot emaila', level: 'Trusted', status: 'aktivno' },
  { id: 6, title: 'Podeli objavu na Facebook-u', cat: 'Društvene mreže', catColor: 'bg-blue-100 text-blue-700', reward: '40 RSD', time: '4 min', proof: 'Screenshot', level: 'Explorer', status: 'aktivno' },
]

export default function TasksPublic({ onNavigate }: { onNavigate: (id: string) => void }) {
  const [cat, setCat] = useState('')
  const [level, setLevel] = useState('')

  const filtered = tasks.filter(t => {
    if (cat && t.cat !== cat) return false
    if (level && t.level !== level) return false
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
              { value: 'Društvene mreže', label: 'Društvene mreže' },
              { value: 'Ankete', label: 'Ankete' },
              { value: 'Recenzije', label: 'Recenzije' },
              { value: 'Video', label: 'Video' },
              { value: 'Web zadaci', label: 'Web zadaci' },
            ]}
            value={cat}
            onChange={setCat}
          />
          <Select
            options={[
              { value: '', label: 'Svi nivoi' },
              { value: 'Explorer', label: 'Explorer' },
              { value: 'Trusted', label: 'Trusted' },
              { value: 'Pro', label: 'Pro' },
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
        {filtered.length === 0 ? (
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
                      <span className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${task.catColor}`}>{task.cat}</span>
                      <span className="text-[11px] text-ink-3 bg-gray-100 px-2 py-0.5 rounded-full">Nivo: {task.level}</span>
                      <StatusBadge status={task.status} />
                    </div>
                    <h3 className="font-semibold text-ink">{task.title}</h3>
                    <div className="flex flex-wrap gap-4 mt-2">
                      <span className="text-xs text-ink-3">⏱ {task.time}</span>
                      <span className="text-xs text-ink-3">📎 {task.proof}</span>
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="font-mono font-bold text-emerald-600 text-lg">{task.reward}</p>
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
