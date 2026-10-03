export type RewardTask = {
  reward_rsd: number
  estimated_minutes: number
  total_slots: number
  used_slots: number
  status: string
  repeat_interval_hours: number
  requires_tester_enrollment: boolean
  tester_duration_days: number
  tester_daily_minutes: number
  tester_daily_reward_rsd: number
}

export function formatRsd(amount: number): string {
  return `${amount.toLocaleString('sr-RS')} RSD`
}

export function taskRewardDetails(task: RewardTask) {
  const places = Math.max(0, task.total_slots - task.used_slots)
  const available = task.status === 'active' && places > 0
  if (task.requires_tester_enrollment) {
    const days = task.tester_duration_days
    const daily = task.tester_daily_reward_rsd
    const dailyMinutes = task.tester_daily_minutes
    const calculatedTotal = days * daily
    const reliable = days > 0 && daily > 0 && dailyMinutes > 0 && Math.abs(calculatedTotal - task.reward_rsd) < 0.01
    return {
      total: reliable ? `${formatRsd(calculatedTotal)} ukupno za ${days} dana` : 'Ukupna nagrada zahteva proveru uslova',
      unit: daily > 0 ? `${formatRsd(daily)} po odobrenom danu` : 'Dnevna nagrada nije navedena',
      time: dailyMinutes > 0 && days > 0 ? `Najmanje ${dailyMinutes} min dnevno tokom ${days} dana` : 'Trajanje proveri u uslovima',
      approval: 'Svaki dnevni izveštaj se posebno pregleda i odobrava.',
      participation: 'Jedna prijava po korisniku za ovu kampanju.',
      places,
      available,
      reliable,
    }
  }
  return {
    total: task.reward_rsd > 0 ? `${formatRsd(task.reward_rsd)} po odobrenom izvršenju` : 'Nagrada nije navedena',
    unit: task.repeat_interval_hours > 0 ? `Ponovljivo nakon ${task.repeat_interval_hours} h, ako je dostupno` : 'Jedno izvršenje po korisniku',
    time: task.estimated_minutes > 0 ? `Oko ${task.estimated_minutes} min po izvršenju` : 'Trajanje proveri u uslovima',
    approval: 'Nagrada se obračunava nakon pregleda i odobrenja dokaza.',
    participation: task.repeat_interval_hours > 0 ? 'Ponovno izvršenje zavisi od pravila zadatka i slobodnih mesta.' : 'Jedno izvršenje po korisniku.',
    places,
    available,
    reliable: task.reward_rsd > 0,
  }
}
