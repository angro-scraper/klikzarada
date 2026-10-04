import type { Task } from './api';

type TermsTask = Pick<Task, 'requires_tester_enrollment' | 'reward_rsd' | 'estimated_minutes' | 'tester_duration_days' | 'tester_daily_minutes' | 'tester_daily_reward_rsd'>;

const money = (value: number) => `${value.toLocaleString('sr-RS')} RSD`;

export function taskTerms(task: TermsTask) {
  if (!task.requires_tester_enrollment) {
    return {
      total: task.reward_rsd > 0 ? `${money(task.reward_rsd)} po odobrenom izvršenju` : 'Nagrada nije navedena',
      daily: '',
      time: task.estimated_minutes > 0 ? `Oko ${task.estimated_minutes} min po izvršenju` : 'Trajanje proveri u uslovima',
    };
  }

  const days = task.tester_duration_days || 0;
  const dailyReward = task.tester_daily_reward_rsd || 0;
  const dailyMinutes = task.tester_daily_minutes || 0;
  const reliable = days > 0 && dailyReward > 0 && dailyMinutes > 0 && Math.abs(days * dailyReward - task.reward_rsd) < 0.01;
  return {
    total: reliable ? `${money(task.reward_rsd)} ukupno za ${days} dana` : 'Ukupna nagrada zahteva proveru',
    daily: dailyReward > 0 ? `${money(dailyReward)} po odobrenom danu` : 'Dnevna nagrada nije navedena',
    time: dailyMinutes > 0 && days > 0 ? `Najmanje ${dailyMinutes} min dnevno tokom ${days} dana` : 'Trajanje proveri u uslovima',
  };
}
