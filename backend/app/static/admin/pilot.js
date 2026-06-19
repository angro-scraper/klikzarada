const $ = (id) => document.getElementById(id);
function toast(msg){ const t=$('toast'); if(!t) return; t.textContent=msg; t.classList.add('show'); setTimeout(()=>t.classList.remove('show'),2500); }
function stat(label, value, note=''){ return `<div class="stat-card"><strong>${value}</strong><span>${label}</span>${note?`<small>${note}</small>`:''}</div>`; }
async function api(url, opts={}){ const res=await fetch(url, {credentials:'include', ...opts}); if(res.redirected){ location.href=res.url; return; } if(!res.ok){ throw new Error(await res.text()); } return res.json(); }
async function loadSummary(){
  const s=await api('/pilot-api/summary');
  $('pilotStats').innerHTML = [
    stat('Javne ponude', s.visible_products, `${s.image_coverage_percent}% sa slikom`),
    stat('Prodavci', `${s.verified_stores}/${s.stores_total}`, 'verifikovani / ukupno'),
    stat('Rezervacije danas', s.reservations_today),
    stat('Provizija platforme', `${s.platform_fee_total} RSD`),
    stat('Refundi otvoreno', s.refund_open),
    stat('Ocene', `${s.avg_rating || 0} ★`, `${s.reviews_count} ocena`),
    stat('Preuzeto', s.picked_up_count),
    stat('No show', s.no_show_count),
  ].join('');
}
async function loadQuality(){
  const q=await api('/pilot-api/quality');
  const p=q.product_issues.map(x=>`<tr><td>#${x.id}</td><td>${x.name}</td><td>${x.store||''}</td><td>${x.status}</td><td>${x.issues.join(', ')}</td></tr>`).join('');
  const st=q.store_issues.map(x=>`<tr><td>#${x.id}</td><td>${x.name}</td><td>${x.city||''}</td><td>${x.issues.join(', ')}</td></tr>`).join('');
  $('qualityBox').innerHTML = `<div class="stats-grid">${stat('Problemi proizvoda',q.product_issues_count)}${stat('Problemi prodavaca',q.store_issues_count)}</div><h3>Proizvodi</h3><div class="table-wrap"><table><thead><tr><th>ID</th><th>Naziv</th><th>Prodavac</th><th>Status</th><th>Problem</th></tr></thead><tbody>${p || '<tr><td colspan="5">Nema problema.</td></tr>'}</tbody></table></div><h3>Prodavci</h3><div class="table-wrap"><table><thead><tr><th>ID</th><th>Naziv</th><th>Grad</th><th>Problem</th></tr></thead><tbody>${st || '<tr><td colspan="4">Nema problema.</td></tr>'}</tbody></table></div>`;
}
async function dailyReport(){ const r=await api('/pilot-api/daily-report'); $('reportBox').textContent=r.report_markdown; }
$('refreshPilot')?.addEventListener('click',()=>loadSummary().then(()=>toast('Osveženo')).catch(e=>toast(e.message)));
$('qualityBtn')?.addEventListener('click',()=>loadQuality().then(()=>toast('Kvalitet proveren')).catch(e=>toast(e.message)));
$('dailyReportBtn')?.addEventListener('click',()=>dailyReport().then(()=>toast('Izveštaj spreman')).catch(e=>toast(e.message)));
$('expireBtn')?.addEventListener('click',async()=>{ if(!confirm('Sakriti istekle ponude?')) return; const r=await api('/pilot-api/maintenance/expire-offers',{method:'POST'}); toast(r.message); loadSummary(); });
$('importForm')?.addEventListener('submit', async (e)=>{ e.preventDefault(); const fd=new FormData(e.target); try{ const res=await fetch('/pilot-api/import/excel',{method:'POST',body:fd,credentials:'include'}); const data=await res.json(); $('importResult').textContent=JSON.stringify(data,null,2); toast('Import završen'); loadSummary(); }catch(err){ toast(err.message); }});
loadSummary().catch(e=>toast(e.message));
