import test from 'node:test';
import assert from 'node:assert/strict';
import { taskTerms } from '../src/taskTerms.ts';

const beta = {
  requires_tester_enrollment: true,
  reward_rsd: 280,
  estimated_minutes: 5,
  tester_duration_days: 14,
  tester_daily_minutes: 5,
  tester_daily_reward_rsd: 20,
};

test('beta test separates total reward, daily reward and daily time', () => {
  const terms = taskTerms(beta);
  assert.match(terms.total, /280 RSD ukupno za 14 dana/);
  assert.match(terms.daily, /20 RSD po odobrenom danu/);
  assert.equal(terms.time, 'Najmanje 5 min dnevno tokom 14 dana');
});

test('missing daily reward never falls back to total as daily reward', () => {
  const terms = taskTerms({ ...beta, tester_daily_reward_rsd: 0 });
  assert.match(terms.total, /zahteva proveru/);
  assert.equal(terms.daily, 'Dnevna nagrada nije navedena');
});

test('inconsistent total does not advertise an unreliable amount', () => {
  const terms = taskTerms({ ...beta, reward_rsd: 100 });
  assert.match(terms.total, /zahteva proveru/);
  assert.match(terms.daily, /20 RSD/);
});

test('one-off task has no daily reward or daily time', () => {
  const terms = taskTerms({ ...beta, requires_tester_enrollment: false, reward_rsd: 50, estimated_minutes: 8 });
  assert.match(terms.total, /50 RSD po odobrenom izvršenju/);
  assert.equal(terms.daily, '');
  assert.equal(terms.time, 'Oko 8 min po izvršenju');
});
