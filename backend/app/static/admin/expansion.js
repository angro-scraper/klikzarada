const $ = (id) => document.getElementById(id);
function toast(msg){ const t=$('toast'); if(!t) return; t.textContent=msg; t.classList.add('show'); setTimeout(()=>t.classList.remove('show'),2800); }
function stat(label,value,note=''){ return `<div class="stat-card"><strong>${value}</strong><span>${label}</span>${note?`<small>${note}</small>`:''}</div>`; }
async function api(url, opts={}){ const res=await fetch(url,{credentials:'include',headers:{'Content-Type':'application/json',...(opts.headers||{})},...opts}); if(res.redirected){ location.href=res.url; return; } if(!res.ok){ throw new Error(await res.text()); } return res.json(); }
function data(form){ const obj=Object.fromEntries(new FormData(form).entries()); ['employees','radius_km','fee_rsd'].forEach(k=>{ if(obj[k]!==undefined && obj[k]!== '') obj[k]=Number(obj[k]); }); return obj; }
function busy(btn,on=true){ if(!btn) return; if(on){ btn.dataset.old=btn.textContent; btn.disabled=true; btn.textContent='Radim...'; } else { btn.disabled=false; btn.textContent=btn.dataset.old||btn.textContent; } }
async function withBusy(btn, fn){ try{ busy(btn,true); await fn(); } catch(e){ toast(e.message); } finally{ busy(btn,false); } }
function rowActions(type,id){ return `<button data-type="${type}" data-id="${id}" data-status="active">Aktivno</button><button class="secondary" data-type="${type}" data-id="${id}" data-status="paused">Pauza</button>`; }
async function patch(type,id,status){
  const urlMap={corporate:'/expansion-api/corporate-clients', donation:'/expansion-api/donation-partners', courier:'/expansion-api/courier-zones', automation:'/expansion-api/automation-rules', experiment:'/expansion-api/experiments'};
  await api(`${urlMap[type]}/${id}`,{method:'PATCH',body:JSON.stringify({status})});
  await loadAll(); toast('Status ažuriran');
}
function bindActions(){ document.querySelectorAll('[data-type]').forEach(b=>b.addEventListener('click',()=>withBusy(b,()=>patch(b.dataset.type,b.dataset.id,b.dataset.status)))); }
async function loadOverview(){
  const o=await api('/expansion-api/overview');
  $('overviewStats').innerHTML = [
    stat('Javne ponude', o.visible_offers, `${o.image_coverage_percent}% sa slikom`),
    stat('Prodavci', `${o.verified_stores}/${o.stores_total}`, 'verifikovani / ukupno'),
    stat('Rezervacije', o.reservations_total, `${o.active_reservations} aktivno`),
    stat('Plaćen promet', `${o.paid_amount} RSD`),
    stat('B2B leadovi', o.corporate_clients),
    stat('Donacije', o.donation_partners),
    stat('Dostavne zone', o.courier_zones),
    stat('Automatizacije', o.automation_rules),
    stat('Eksperimenti', o.experiments),
    stat('Playbooks', o.playbooks),
  ].join('');
}
async function loadAutomation(){ const rows=await api('/expansion-api/automation-rules'); $('automationBody').innerHTML=rows.map(r=>`<tr><td><strong>${r.name}</strong><br><small>${r.action||''}</small><br><small>${r.note||''}</small></td><td>${r.trigger||''}</td><td><span class="status">${r.status}</span><br><small>${r.risk||''}</small></td><td>${rowActions('automation',r.id)}</td></tr>`).join('')||'<tr><td colspan="4">Nema pravila.</td></tr>'; }
async function loadCorporate(){ const rows=await api('/expansion-api/corporate-clients'); $('corporateBody').innerHTML=rows.map(r=>`<tr><td><strong>${r.name}</strong><br><small>${r.contact||''}</small><br><small>${r.employees||0} ljudi</small></td><td>${r.city||''}</td><td>${r.category_interest||''}</td><td><span class="status">${r.status}</span></td><td>${rowActions('corporate',r.id)}</td></tr>`).join('')||'<tr><td colspan="5">Nema B2B leadova.</td></tr>'; }
async function loadDonation(){ const rows=await api('/expansion-api/donation-partners'); $('donationBody').innerHTML=rows.map(r=>`<tr><td><strong>${r.name}</strong><br><small>${r.contact||''}</small><br><small>${r.pickup_window||''}</small></td><td>${r.city||''}</td><td>${r.category_accepts||''}</td><td><span class="status">${r.status}</span></td><td>${rowActions('donation',r.id)}</td></tr>`).join('')||'<tr><td colspan="5">Nema donacionih partnera.</td></tr>'; }
async function loadCourier(){ const rows=await api('/expansion-api/courier-zones'); $('courierBody').innerHTML=rows.map(r=>`<tr><td><strong>${r.name}</strong><br><small>${r.coverage_note||''}</small></td><td>${r.city||''}</td><td>${r.radius_km||0} km<br><small>${r.fee_rsd||0} RSD</small></td><td><span class="status">${r.status}</span></td><td>${rowActions('courier',r.id)}</td></tr>`).join('')||'<tr><td colspan="5">Nema zona.</td></tr>'; }
async function loadExperiments(){ const rows=await api('/expansion-api/experiments'); $('experimentBody').innerHTML=rows.map(r=>`<tr><td><strong>${r.name}</strong><br><small>${r.goal||''}</small></td><td>A: ${r.variant_a||'-'}<br>B: ${r.variant_b||'-'}</td><td>${r.metric||''}</td><td><span class="status">${r.status}</span></td><td>${rowActions('experiment',r.id)}</td></tr>`).join('')||'<tr><td colspan="5">Nema eksperimenata.</td></tr>'; }
async function loadPlaybooks(){ const rows=await api('/expansion-api/playbooks'); $('playbookBody').innerHTML=rows.map(r=>`<tr><td><strong>${r.title}</strong></td><td>${r.type||''}</td><td><span class="status">${r.status||''}</span></td><td>${r.body||''}</td></tr>`).join('')||'<tr><td colspan="4">Nema playbook tekstova.</td></tr>'; }
async function loadAll(){ await loadOverview(); await Promise.all([loadAutomation(),loadCorporate(),loadDonation(),loadCourier(),loadExperiments(),loadPlaybooks()]); bindActions(); }
async function aiPlan(){ const r=await api('/expansion-api/ai-expansion-plan'); $('aiPlan').innerHTML=`<h3>AI expansion plan</h3><div class="scale-ai-grid">${r.actions.map(a=>`<div class="mini-card priority-${a.priority}"><strong>${a.area}</strong><p>${a.action}</p><small>${a.why}</small></div>`).join('')}</div>`; }
async function riskAudit(){ const r=await api('/expansion-api/risk-audit'); $('riskStats').innerHTML=[stat('Ponude bez slike',r.no_image_visible_offers),stat('Nizak confidence',r.low_confidence_products),stat('Mismatch plaćanja',r.payment_status_mismatch),stat('No-show',r.no_show_count),stat('Refund/otkazano',r.refund_like_count)].join(''); $('riskRecommendations').innerHTML=r.recommendations.map(x=>`<div class="mini-card priority-medium"><strong>Preporuka</strong><p>${x}</p></div>`).join(''); }
async function routePlan(){ const r=await api('/expansion-api/route-plan'); $('routePlan').innerHTML = r.routes.length ? r.routes.map(route=>`<div class="mini-card"><strong>${route.city}</strong><p>${route.note}</p><ol>${route.stops.map(s=>`<li>${s.name} — ${s.offers} ponuda</li>`).join('')}</ol></div>`).join('') : 'Nema dovoljno prodavnica sa GPS lokacijom i aktivnim ponudama za predlog rute.'; }
async function boardMemo(){ const r=await api('/expansion-api/board-memo'); $('boardMemo').textContent=r.memo; }
['automation','corporate','donation','courier','experiment'].forEach(type=>{
  const form=$(type+'Form'); if(!form) return;
  const url={automation:'/expansion-api/automation-rules',corporate:'/expansion-api/corporate-clients',donation:'/expansion-api/donation-partners',courier:'/expansion-api/courier-zones',experiment:'/expansion-api/experiments'}[type];
  form.addEventListener('submit',(e)=>{e.preventDefault(); withBusy(e.submitter,async()=>{ await api(url,{method:'POST',body:JSON.stringify(data(form))}); form.reset(); await loadAll(); toast('Dodato'); });});
});
$('seedAllBtn')?.addEventListener('click',(e)=>withBusy(e.target,async()=>{ const r=await api('/expansion-api/seed-all',{method:'POST'}); await loadAll(); toast(r.message); }));
$('refreshBtn')?.addEventListener('click',(e)=>withBusy(e.target,async()=>{ await loadAll(); toast('Osveženo'); }));
$('aiPlanBtn')?.addEventListener('click',(e)=>withBusy(e.target,async()=>{ await aiPlan(); toast('AI plan spreman'); }));
$('memoBtn')?.addEventListener('click',(e)=>withBusy(e.target,async()=>{ await boardMemo(); toast('Memo spreman'); }));
$('riskBtn')?.addEventListener('click',(e)=>withBusy(e.target,async()=>{ await riskAudit(); toast('Audit gotov'); }));
$('routeBtn')?.addEventListener('click',(e)=>withBusy(e.target,async()=>{ await routePlan(); toast('Predlog ruta gotov'); }));
loadAll().catch(e=>toast(e.message));
