const $ = (id) => document.getElementById(id);
const log = (msg, data) => { $('log').textContent = `[${new Date().toLocaleTimeString()}] ${msg}\n` + (data ? JSON.stringify(data, null, 2) : '') + '\n\n' + $('log').textContent; };
async function api(path, opts={}){ const r = await fetch(path, opts); const data = await r.json(); if(!r.ok) throw new Error(data.detail || r.statusText); return data; }
function metric(label, value){ return `<div class="metric"><b>${value ?? '—'}</b><span>${label}</span></div>`; }
function renderStatus(d){
  $('score').textContent = d.score ?? '—';
  $('missing').textContent = (d.missing || []).slice(0,4).join(' · ');
  const m=d.metrics||{};
  $('metrics').innerHTML = metric('Ponude',m.public_products)+metric('Sa slikom',m.products_with_image)+metric('Gradovi',m.cities_with_offers)+metric('Verifikovani prodavci',m.verified_stores)+metric('GPS ponude',m.products_with_gps)+metric('Rezervacije',m.reservations)+metric('Plaćen promet',`${m.paid_revenue||0} RSD`)+metric('Naša provizija',`${m.platform_fee||0} RSD`);
  renderGrowth(d.state||{});
}
function renderGrowth(state){
  const blocks=[];
  (state.campaigns||[]).forEach(c=>blocks.push(`<div class="card"><strong>${c.code}</strong> — ${c.title}<br><span class="pill">${c.discount}%</span><span class="pill">${c.status}</span><span class="pill">${c.target}</span></div>`));
  (state.journeys||[]).forEach(j=>blocks.push(`<div class="card"><strong>${j.name}</strong><br>${j.trigger}<br><span class="pill">${j.channel}</span></div>`));
  $('growthState').innerHTML = blocks.length ? blocks.join('') : '<div class="card">Growth sistem nije aktiviran.</div>';
}
async function refresh(){ const d=await api('/v48/status'); renderStatus(d); log('Status osvežen', d.metrics); }
async function seed(){ const d=await api('/v48/seed-super-database',{method:'POST'}); log('Super baza učitana', d); await refresh(); }
async function growth(){ const d=await api('/v48/activate-growth-system',{method:'POST'}); log('Growth sistem aktiviran', d); await refresh(); }
async function plan(){ const d=await api('/v48/ai-master-plan'); $('plan').innerHTML = d.plan.map(p=>`<div class="card"><strong>${p.area}</strong> <span class="pill">${p.priority}</span><br>${p.action}</div>`).join(''); log('AI master plan generisan', d); }
async function cities(){ const d=await api('/v48/city-dashboard'); $('cities').innerHTML = d.cities.map(c=>`<div class="row"><div><strong>${c.city}</strong><br><span class="pill">${c.offers} ponuda</span><span class="pill">${c.stores} prodavaca</span><span class="pill">${c.next_action}</span></div><b>${c.readiness}%</b></div>`).join('') || '<div class="card">Nema gradova.</div>'; log('City dashboard', d); }
async function pricing(){ const d=await api('/v48/dynamic-pricing'); $('pricing').innerHTML = d.suggestions.map(s=>`<div class="row"><div><strong>${s.product}</strong><br>${s.store||''}<br>${s.reason}</div><b>${s.suggested_price} RSD</b></div>`).join('') || '<div class="card">Nema hitnih korekcija cena.</div>'; log('Dynamic pricing', {count:d.count}); }
async function dataroom(){ const d=await api('/v48/data-room'); $('dataroom').innerHTML = d.sections.map(sec=>`<div class="card"><strong>${sec.title}</strong><br>${sec.items.map(i=>`<span class="pill">${i}</span>`).join('')}</div>`).join(''); log('Data room prikazan', d); }
document.addEventListener('click', e=>{ const a=e.target.closest('[data-action]'); if(!a) return; const action=a.dataset.action; a.disabled=true; const old=a.textContent; a.textContent='Radim...'; ({refresh,seed,growth,plan,cities,pricing,dataroom}[action]||refresh)().catch(err=>log('Greška',err.message)).finally(()=>{a.disabled=false;a.textContent=old;}); });
refresh().then(()=>{plan();cities();pricing();dataroom();});
