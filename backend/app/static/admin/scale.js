const $ = (id) => document.getElementById(id);
function toast(msg){ const t=$('toast'); if(!t) return; t.textContent=msg; t.classList.add('show'); setTimeout(()=>t.classList.remove('show'),2600); }
function stat(label,value,note=''){ return `<div class="stat-card"><strong>${value}</strong><span>${label}</span>${note?`<small>${note}</small>`:''}</div>`; }
async function api(url, opts={}){ const res=await fetch(url,{credentials:'include',headers:{'Content-Type':'application/json',...(opts.headers||{})},...opts}); if(res.redirected){ location.href=res.url; return; } if(!res.ok){ throw new Error(await res.text()); } return res.json(); }
function formDataJson(form){ return Object.fromEntries(new FormData(form).entries()); }
function setBusy(btn, on=true){ if(!btn) return; if(on){ btn.dataset.old=btn.textContent; btn.disabled=true; btn.textContent='Radim...'; } else { btn.disabled=false; btn.textContent=btn.dataset.old || btn.textContent; } }
async function withBusy(btn, fn){ try{ setBusy(btn,true); await fn(); } catch(e){ toast(e.message); } finally{ setBusy(btn,false); } }

async function loadOverview(){
  const o=await api('/scale-api/overview');
  $('scaleStats').innerHTML = [
    stat('Javne ponude', o.visible_offers, `${o.image_coverage_percent}% sa slikom`),
    stat('Prodavci', `${o.verified_stores}/${o.stores_total}`, 'verifikovani / ukupno'),
    stat('Rezervacije', o.reservations_total, `${o.active_reservations} aktivno`),
    stat('Plaćen promet', `${o.paid_amount} RSD`),
    stat('Provizija', `${o.platform_fee} RSD`),
    stat('Kampanje', `${o.active_campaigns}/${o.campaigns}`, 'aktivne / ukupno'),
    stat('Potražnja', o.demand_requests),
    stat('Leadovi', o.leads),
  ].join('');
}
async function loadCities(){
  const rows=await api('/scale-api/cities');
  $('citiesBody').innerHTML = rows.map(r=>`<tr><td><strong>${r.city}</strong><br><small>${r.note||''}</small></td><td><span class="status">${r.status}</span></td><td>${r.target_partners} partnera<br><small>${r.categories||''}</small></td><td>${r.stores_current||0} prod. / ${r.offers_current||0} ponuda / ${r.reservations_current||0} rez.</td><td class="actions"><button data-city="${r.id}" data-status="active_pilot">Pilot</button><button class="secondary" data-city="${r.id}" data-status="paused">Pauza</button><button class="secondary" data-city="${r.id}" data-status="launched">Launch</button></td></tr>`).join('') || '<tr><td colspan="5">Nema planova gradova.</td></tr>';
  document.querySelectorAll('[data-city]').forEach(b=>b.addEventListener('click',()=>withBusy(b,async()=>{await api(`/scale-api/cities/${b.dataset.city}`,{method:'PATCH',body:JSON.stringify({status:b.dataset.status})}); await loadCities(); toast('Status grada promenjen');})));
}
async function loadCampaigns(){
  const rows=await api('/scale-api/campaigns');
  $('campaignsBody').innerHTML = rows.map(r=>`<tr><td><strong>${r.name}</strong><br><small>${r.city||''} · ${r.category||''} · ${r.channel||''}</small><br><small>${r.goal||''}</small></td><td>${r.coupon_code||'-'}</td><td>${r.discount_percent||0}%</td><td><span class="status">${r.status}</span></td><td class="actions"><button data-campaign="${r.id}" data-status="active">Aktiviraj</button><button class="secondary" data-campaign="${r.id}" data-status="paused">Pauziraj</button><button class="secondary" data-campaign="${r.id}" data-status="finished">Završi</button></td></tr>`).join('') || '<tr><td colspan="5">Nema kampanja.</td></tr>';
  document.querySelectorAll('[data-campaign]').forEach(b=>b.addEventListener('click',()=>withBusy(b,async()=>{await api(`/scale-api/campaigns/${b.dataset.campaign}`,{method:'PATCH',body:JSON.stringify({status:b.dataset.status})}); await loadCampaigns(); await loadOverview(); toast('Status kampanje promenjen');})));
}
async function loadDemand(){
  const d=await api('/scale-api/demand');
  const cityStats=(d.by_city||[]).slice(0,4).map(x=>stat(x[0],x[1],'zahteva')).join('');
  const catStats=(d.by_category||[]).slice(0,4).map(x=>stat(x[0],x[1],'zahteva')).join('');
  $('demandSummary').innerHTML = stat('Ukupno zahteva', d.total) + cityStats + catStats;
  $('demandBody').innerHTML = (d.latest||[]).map(r=>`<tr><td>${r.query||''}</td><td>${r.city||''}</td><td>${r.category||''}</td><td>${r.phone||''}</td><td>${r.created_at||''}</td></tr>`).join('') || '<tr><td colspan="5">Nema zahteva.</td></tr>';
}
async function loadLeads(){
  const rows=await api('/scale-api/leads');
  $('leadsBody').innerHTML = rows.map(r=>`<tr><td><strong>${r.name}</strong><br><small>${r.contact||''}</small><br><small>${r.note||''}</small></td><td>${r.city||''}<br><small>${r.category||''}</small></td><td><span class="status">${r.status}</span></td><td>${r.score||0}</td><td class="actions"><button data-lead="${r.id}" data-status="contacted">Kontaktiran</button><button class="secondary" data-lead="${r.id}" data-status="meeting">Sastanak</button><button data-lead="${r.id}" data-status="approved">Odobren</button></td></tr>`).join('') || '<tr><td colspan="5">Nema leadova.</td></tr>';
  document.querySelectorAll('[data-lead]').forEach(b=>b.addEventListener('click',()=>withBusy(b,async()=>{await api(`/scale-api/leads/${b.dataset.lead}`,{method:'PATCH',body:JSON.stringify({status:b.dataset.status})}); await loadLeads(); toast('Lead ažuriran');})));
}
async function loadAiActions(){
  const r=await api('/scale-api/ai/next-actions');
  $('aiActions').innerHTML = `<h3>AI sledeći potezi</h3><div class="scale-ai-grid">${r.actions.map(a=>`<div class="mini-card priority-${a.priority}"><strong>${a.area}</strong><p>${a.action}</p><small>${a.why}</small></div>`).join('')}</div>`;
}
async function init(){ await loadOverview(); await loadCities(); await loadCampaigns(); await loadDemand(); await loadLeads(); }
$('refreshBtn')?.addEventListener('click',(e)=>withBusy(e.target,async()=>{await init(); toast('Osveženo');}));
$('aiActionsBtn')?.addEventListener('click',(e)=>withBusy(e.target,async()=>{await loadAiActions(); toast('AI preporuke spremne');}));
$('seedCitiesBtn')?.addEventListener('click',(e)=>withBusy(e.target,async()=>{const r=await api('/scale-api/cities/seed',{method:'POST'}); await loadCities(); toast(r.message);}));
$('seedCampaignsBtn')?.addEventListener('click',(e)=>withBusy(e.target,async()=>{const r=await api('/scale-api/campaigns/seed',{method:'POST'}); await loadCampaigns(); await loadOverview(); toast(r.message);}));
$('loadDemandBtn')?.addEventListener('click',(e)=>withBusy(e.target,async()=>{await loadDemand(); toast('Potražnja osvežena');}));
$('cityForm')?.addEventListener('submit',(e)=>{e.preventDefault(); withBusy(e.submitter,async()=>{await api('/scale-api/cities',{method:'POST',body:JSON.stringify(formDataJson(e.target))}); e.target.reset(); await loadCities(); toast('Grad dodat');});});
$('campaignForm')?.addEventListener('submit',(e)=>{e.preventDefault(); withBusy(e.submitter,async()=>{const data=formDataJson(e.target); data.discount_percent=Number(data.discount_percent||0); data.budget_rsd=Number(data.budget_rsd||0); await api('/scale-api/campaigns',{method:'POST',body:JSON.stringify(data)}); await loadCampaigns(); await loadOverview(); toast('Kampanja dodata');});});
$('demandForm')?.addEventListener('submit',(e)=>{e.preventDefault(); withBusy(e.submitter,async()=>{await api('/scale-api/demand',{method:'POST',body:JSON.stringify(formDataJson(e.target))}); e.target.reset(); await loadDemand(); await loadOverview(); toast('Zahtev dodat');});});
$('leadForm')?.addEventListener('submit',(e)=>{e.preventDefault(); withBusy(e.submitter,async()=>{const data=formDataJson(e.target); data.score=Number(data.score||0); await api('/scale-api/leads',{method:'POST',body:JSON.stringify(data)}); e.target.reset(); await loadLeads(); await loadOverview(); toast('Lead dodat');});});
$('sellerAdviceForm')?.addEventListener('submit',(e)=>{e.preventDefault(); withBusy(e.submitter,async()=>{const fd=formDataJson(e.target); const r=await api(`/scale-api/seller-advice?store_id=${encodeURIComponent(fd.store_id)}`); $('sellerAdvice').innerHTML = `<strong>${r.store.name}</strong><br>Javne ponude: ${r.visible_offers} · Rezervacije: ${r.reservations} · Prosečan popust: ${r.average_discount}%<ul>${r.advice.map(x=>`<li>${x}</li>`).join('')}</ul>`; toast('Analiza spremna');});});
$('seoBtn')?.addEventListener('click',(e)=>withBusy(e.target,async()=>{const rows=await api('/scale-api/seo-pages'); $('seoBody').innerHTML = rows.map(r=>`<tr><td>${r.title}</td><td><code>${r.url}</code></td><td>${r.type}</td></tr>`).join('') || '<tr><td colspan="3">Nema predloga.</td></tr>'; toast('SEO predlozi generisani');}));
init().catch(e=>toast(e.message));
