const toastEl = document.getElementById('toast');
function toast(msg){ toastEl.textContent = msg; toastEl.classList.add('show'); setTimeout(()=>toastEl.classList.remove('show'), 2800); }
async function api(path, opts={}){
  const res = await fetch(path, {headers:{'Content-Type':'application/json'}, ...opts});
  if(res.status === 401 || res.redirected){ location.href = '/admin-login?next=/execution'; return null; }
  if(!res.ok) throw new Error(await res.text());
  return res.json();
}
function fmt(n){ return (n ?? 0).toLocaleString('sr-RS'); }
function money(n){ return `${fmt(Math.round(Number(n||0)))} RSD`; }
function tag(v){ return `<span class="tag ${String(v||'').toLowerCase()}">${v||''}</span>`; }
function row(title, meta='', body='', extra=''){
  return `<article class="exec-row"><div class="table-header"><h3>${title}</h3>${extra}</div>${meta?`<p><b>${meta}</b></p>`:''}${body?`<p>${body}</p>`:''}</article>`;
}
function renderDashboard(data){
  const m = data.metrics;
  document.querySelector('#scoreBox strong').textContent = m.readiness_score;
  const kpis = [
    ['Javne ponude', fmt(m.visible_offers), `${fmt(m.offers_with_image)} sa slikom`],
    ['Slike', `${m.image_coverage_percent}%`, `${fmt(m.offers_without_image)} bez slike`],
    ['Prodavci', fmt(m.verified_stores), `${fmt(m.stores_total)} ukupno`],
    ['Rezervacije', fmt(m.reservations_total), `${fmt(m.picked_up)} preuzeto`],
    ['Plaćeno', money(m.paid_amount), `Provizija ${money(m.platform_fee)}`],
    ['Open taskovi', fmt(data.open_tasks), data.next_phase],
  ];
  document.getElementById('kpis').innerHTML = kpis.map(([a,b,c])=>`<div class="stat-card"><span>${a}</span><strong>${b}</strong><span>${c}</span></div>`).join('');
  document.getElementById('gaps').innerHTML = (data.gaps||[]).map(g=>row(g.title, `${g.lane} · ${g.current}/${g.target}`, g.note, tag(g.priority))).join('') || row('Nema kritičnih gapova', 'Pilot je blizu spremnosti', 'Nastavi sa quality i finance proverama.', tag('done'));
}
async function loadDashboard(){ const data = await api('/v41-api/dashboard'); if(data) renderDashboard(data); }
async function loadTasks(){
  const tasks = await api('/v41-api/tasks'); if(!tasks) return;
  const ordered = [...tasks].sort((a,b)=>{
    const p = {high:0, medium:1, low:2}; return (p[a.priority]??5)-(p[b.priority]??5) || String(a.due_date||'').localeCompare(String(b.due_date||''));
  });
  document.getElementById('tasks').innerHTML = ordered.map(t=>`
    <article class="exec-row ${t.priority==='high'?'warning-card':''}">
      <div class="table-header"><h3>${t.title}</h3><div>${tag(t.priority)} ${tag(t.status)}</div></div>
      <p><b>${t.lane}</b> · owner: ${t.owner||'-'} · rok: ${t.due_date||'-'} · playbook: ${t.playbook||t.created_from||'-'}</p>
      <p>${t.note||''}</p>
      <div class="task-controls">
        <button class="secondary" onclick="patchTask('${t.id}','doing')">U radu</button>
        <button onclick="patchTask('${t.id}','done')">Done</button>
        <button class="secondary" onclick="patchTask('${t.id}','open')">Open</button>
      </div>
    </article>`).join('') || '<p class="muted">Nema taskova. Klikni “Učitaj V41 komplet”.</p>';
}
async function patchTask(id,status){ await api(`/v41-api/tasks/${id}`, {method:'PATCH', body:JSON.stringify({status})}); toast('Task ažuriran'); await Promise.all([loadTasks(), loadDashboard()]); }
async function seedAll(){ const btn=document.getElementById('seedBtn'); btn.disabled=true; btn.textContent='Učitavam...'; try{ const r=await api('/v41-api/seed/all',{method:'POST'}); toast(`V41 učitan · taskovi +${r.tasks_added}`); await refreshAll(); } finally{ btn.disabled=false; btn.textContent='Učitaj V41 komplet'; } }
async function generateTasks(){ const r=await api('/v41-api/tasks/generate-from-metrics',{method:'POST'}); toast(`Dodato taskova: ${r.added}`); await refreshAll(); }
async function runAutomation(dry=true){
  if(!dry && !confirm('Primeni bezbedne provere? Istekle ponude i javne ponude bez slike mogu biti sakrivene.')) return;
  const r=await api(`/v41-api/automations/run-safe-checks?dry_run=${dry?'true':'false'}`,{method:'POST'});
  toast(`${dry?'Provera':'Primena'}: expired ${r.found.expired}, bez slike ${r.found.no_image}, ekstreman popust ${r.found.extreme_discount}`);
  await refreshAll();
}
async function sellers(){
  const data = await api('/v41-api/seller-scorecards'); if(!data) return;
  const cards = [...(data.needs_attention||[]), ...(data.top||[]).slice(0,5)];
  document.getElementById('sellerCards').innerHTML = cards.map(s=>row(`${s.name} · score ${s.score}`, `${s.city||'-'} · ${s.visible_offers} ponuda · slike ${s.image_coverage_percent}% · rez ${s.reservations}`, s.recommended_action, tag(s.verified?'verified':'lead'))).join('') || '<p class="muted">Nema prodavaca.</p>';
}
async function cities(){
  const data = await api('/v41-api/city-readiness'); if(!data) return;
  document.getElementById('cityCards').innerHTML = data.map(c=>row(`${c.city} · ${c.readiness_score}/100`, `${c.verified} verifikovanih · ${c.offers} ponuda · slike ${c.image_coverage_percent}%`, `Rezervacije: ${c.reservations}, plaćeno: ${c.paid}`, tag(c.stage))).join('') || '<p class="muted">Nema gradova.</p>';
}
async function playbooks(){
  const data = await api('/v41-api/playbooks'); if(!data) return;
  document.getElementById('playbooks').innerHTML = data.map(p=>row(p.name, `${p.audience} · metrika: ${p.success_metric}`, `<ol>${(p.steps||[]).map(s=>`<li>${s}</li>`).join('')}</ol>`)).join('') || '<p class="muted">Nema playbook-a.</p>';
}
async function sla(){
  const data = await api('/v41-api/sla'); if(!data) return;
  document.getElementById('sla').innerHTML = data.map(x=>row(x.name, `${x.target_minutes} min · ${x.owner}`, `Escalation: ${x.escalation}`, tag(x.severity))).join('') || '<p class="muted">Nema SLA pravila.</p>';
}
async function brief(){ const data = await api('/v41-api/weekly-brief'); if(data) document.getElementById('briefBox').textContent = JSON.stringify(data,null,2); }
async function refreshAll(){ await Promise.all([loadDashboard(), loadTasks(), playbooks(), sla()]); }
document.getElementById('seedBtn').addEventListener('click', seedAll);
document.getElementById('generateBtn').addEventListener('click', generateTasks);
document.getElementById('automationDryBtn').addEventListener('click', ()=>runAutomation(true));
document.getElementById('automationRunBtn').addEventListener('click', ()=>runAutomation(false));
document.getElementById('refreshBtn').addEventListener('click', refreshAll);
document.getElementById('sellerBtn').addEventListener('click', sellers);
document.getElementById('cityBtn').addEventListener('click', cities);
document.getElementById('briefBtn').addEventListener('click', brief);
refreshAll().catch(e=>toast(e.message));
