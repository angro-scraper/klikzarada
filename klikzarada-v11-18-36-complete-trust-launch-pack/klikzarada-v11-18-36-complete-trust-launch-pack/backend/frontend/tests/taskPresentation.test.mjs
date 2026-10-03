import test from 'node:test'
import assert from 'node:assert/strict'
import { taskRewardDetails } from '../src/lib/taskPresentation.ts'

const beta = {
  reward_rsd: 280, estimated_minutes: 5, total_slots: 20, used_slots: 2,
  status: 'active', repeat_interval_hours: 0, requires_tester_enrollment: true,
  tester_duration_days: 14, tester_daily_minutes: 5, tester_daily_reward_rsd: 20,
}

test('beta test separates total, daily payout, and daily effort', () => {
  const result = taskRewardDetails(beta)
  assert.match(result.total, /280 RSD ukupno za 14 dana/)
  assert.match(result.unit, /20 RSD po odobrenom danu/)
  assert.equal(result.time, 'Najmanje 5 min dnevno tokom 14 dana')
  assert.equal(result.places, 18)
})

test('one-off task has one approval, not a daily projection', () => {
  const result = taskRewardDetails({ ...beta, requires_tester_enrollment: false, reward_rsd: 50, estimated_minutes: 8 })
  assert.match(result.total, /50 RSD po odobrenom izvršenju/)
  assert.equal(result.unit, 'Jedno izvršenje po korisniku')
  assert.equal(result.time, 'Oko 8 min po izvršenju')
})

test('inconsistent beta data cannot advertise a reliable total', () => {
  const result = taskRewardDetails({ ...beta, reward_rsd: 100 })
  assert.equal(result.reliable, false)
  assert.match(result.total, /proveru/)
})

test('missing daily data cannot invent a reward or time', () => {
  const result = taskRewardDetails({ ...beta, tester_daily_reward_rsd: 0, tester_daily_minutes: 0 })
  assert.equal(result.reliable, false)
  assert.match(result.unit, /nije navedena/)
  assert.match(result.time, /proveri/)
})

test('full, inactive, and limited tasks are not advertised as available', () => {
  assert.equal(taskRewardDetails({ ...beta, used_slots: 20 }).available, false)
  assert.equal(taskRewardDetails({ ...beta, status: 'paused' }).available, false)
  assert.equal(taskRewardDetails({ ...beta, used_slots: 19 }).places, 1)
  const repeating = taskRewardDetails({ ...beta, requires_tester_enrollment: false, repeat_interval_hours: 24 })
  assert.match(repeating.participation, /slobodnih mesta/)
})
