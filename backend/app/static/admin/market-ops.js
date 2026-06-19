const toastEl = document.getElementById('toast');
function toast(msg){ toastEl.textContent = msg; toastEl.classList.add('show'); setTimeout(()=>toastEl.classList.remove('show'), 2600); }
async function api(path, opts={}){
  const res = await fetch(path, {headers:{'Content-Type':'application/json'}, ...opts});
  if(res.status === 401 || res.redirected){ location.href = '/admin-login?next=/market-ops'; return null; }
  if(!res.ok){ throw new Error(await res.text()); }
  return res.json();
}
function fmt(n){ return (n ?? 0).toLocaleString('sr-RS'); }
function money(n){ return `${fmt(Math.round(Number(n||0)))} RSD`; }
function row(title, meta, body, tag=''){
  return `<article class="v40-row"><div class="table-header"><h3>${title}</h3>${tag?`<span class="tag">${tag}</span>`:''}</div>${meta?`<p><strong>${meta}</strong></p>`:''}${body?`<p>${body}</p>`:''}</article>`;
}
function renderKpis(m){
  const items = [
    ['Javne ponude', fmt(m.visible_offers), `${fmt(m.offers_with_image)} sa slikom`],
    ['Slike', `${m.image_coverage_percent}%`, `${fmt(m.offers_without_image)} bez slike`],
    ['Prodavci', fmt(m.verified_stores), `${fmt(m.stores_total)} ukupno`],
    ['Rezervacije', fmt(m.reservations_total), `${fmt(m.active_orders)} aktivno`],
    ['Plaćeno', money(m.paid_amount), `Provizija ${money(m.platform_fee)}`],
    ['Impact', `${m.estimated_kg_saved} kg`, `${m.estimated_co2e_saved} kg CO₂e`],
  ];
  document.getElementById('kpis').innerHTML = items.map(([a,b,c])=>`<div class="stat-card"><span>${a}</span><strong>${b}</strong><span>${c}</span></div>`).join('');
}
function renderChecks(checks){
  document.getElementById('checks').innerHTML = checks.map(c=>`<div class="check-card ${c.ok?'ok':'bad'}"><span class="tag ${c.ok?'ok':'bad'}">${c.ok?'OK':'Treba rad'}</span><h3>${c.name}</h3><p><b>${c.current}</b> / cilj: ${c.target}</p><p>${c.fix}</p></div>`).join('');
}
async function loadOverview(){
  const data = await api('/v40-api/overview'); if(!data) return;
  renderKpis(data.metrics); renderChecks(data.checks);
}
async function loadLists(){
  const [cities, plans, contracts, journeys, content, risks, pipelines, okrs] = await Promise.all([
    api('/v40-api/city-launch'), api('/v40-api/merchant-plans'), api('/v40-api/contracts'), api('/v40-api/notification-journeys'), api('/v40-api/content-calendar'), api('/v40-api/risk-rules'), api('/v40-api/data-pipelines'), api('/v40-api/okrs')
  ]);
  document.getElementById('cities').innerHTML = (cities||[]).map(x=>row(x.city, `Prioritet ${x.priority} · cilj ${x.target_verified_sellers} prodavaca · ${x.target_public_offers} ponuda`, `${x.pilot_areas || ''}<br>${x.note || ''}`, x.status)).join('') || '<p class="muted-note">Nema podataka. Klikni “Učitaj komplet V40”.</p>';
  document.getElementById('plans').innerHTML = (plans||[]).map(x=>row(x.name, `${money(x.monthly_fee_rsd)} mesečno · provizija ${x.commission_percent}%`, `${x.best_for}. ${x.note || ''}`, x.status)).join('') || '<p class="muted-note">Nema podataka.</p>';
  document.getElementById('contracts').innerHTML = (contracts||[]).map(x=>row(x.title, x.type, x.body, x.required?'obavezno':'draft')).join('') || '<p class="muted-note">Nema podataka.</p>';
  document.getElementById('journeys').innerHTML = (journeys||[]).map(x=>row(x.name, `${x.audience} · ${x.trigger} · ${x.channels}`, x.message)).join('') || '<p class="muted-note">Nema podataka.</p>';
  document.getElementById('content').innerHTML = (content||[]).map(x=>row(`Dan ${x.day}: ${x.topic}`, `${x.channel} · CTA: ${x.cta}`, x.hook)).join('') || '<p class="muted-note">Nema podataka.</p>';
  document.getElementById('risks').innerHTML = (risks||[]).map(x=>row(x.name, `${x.severity} · ${x.rule}`, `Akcija: ${x.action}`, x.status)).join('') || '<p class="muted-note">Nema podataka.</p>';
  document.getElementById('pipelines').innerHTML = (pipelines||[]).map(x=>row(x.name, `${x.source} · ${x.frequency} · ${x.owner}`, x.note, x.status)).join('') || '<p class="muted-note">Nema podataka.</p>';
  document.getElementById('okrBody').innerHTML = (okrs||[]).map(x=>`<tr><td>${x.objective}</td><td>${x.key_result}</td><td>${x.target}</td><td>${x.current}</td><td>${x.owner}</td><td><span class="status">${x.status}</span></td></tr>`).join('') || '<tr><td colspan="6">Nema OKR podataka.</td></tr>';
}
async function seedAll(){
  const btn = document.getElementById('seedBtn'); btn.disabled = true; btn.textContent = 'Učitavam...';
  try{ const res = await api('/v40-api/seed/all', {method:'POST'}); toast('V40 komplet učitan'); await refreshAll(); }
  finally{ btn.disabled = false; btn.textContent = 'Učitaj komplet V40'; }
}
async function aiBoard(){
  const data = await api('/v40-api/ai-board'); if(!data) return;
  const el = document.getElementById('aiBoard');
  el.innerHTML = `<div class="v40-row"><h3>Strategija</h3><p>${data.one_sentence_strategy}</p></div>` +
    data.priorities.map(p=>`<div class="ai-priority"><h3>${p.priority}: ${p.action}</h3><p>${p.why}</p><p><b>Sledeći korak:</b> ${p.next_step}</p></div>`).join('') +
    `<div class="v40-grid">${data['90_day_plan'].map(x=>`<div class="v40-row"><h3>${x.phase}</h3><p>${x.focus}</p><p>${x.targets}</p></div>`).join('')}</div>`;
}
async function investor(){
  const data = await api('/v40-api/investor-snapshot'); if(!data) return;
  document.getElementById('investorBox').textContent = JSON.stringify(data, null, 2);
}
async function hideNoImage(){
  if(!confirm('Sakriti sve javne ponude bez slike?')) return;
  const data = await api('/v40-api/quality/enforce-no-image', {method:'POST'}); if(!data) return;
  toast(`Sakriveno: ${data.hidden}`); await refreshAll();
}
async function refreshAll(){ await loadOverview(); await loadLists(); }
document.getElementById('seedBtn').addEventListener('click', seedAll);
document.getElementById('refreshBtn').addEventListener('click', refreshAll);
document.getElementById('aiBtn').addEventListener('click', aiBoard);
document.getElementById('investorBtn').addEventListener('click', investor);
document.getElementById('hideNoImageBtn').addEventListener('click', hideNoImage);
refreshAll().catch(e=>toast(e.message));
