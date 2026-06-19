const $ = (id) => document.getElementById(id);
function log(obj){ $('log').textContent = typeof obj === 'string' ? obj : JSON.stringify(obj, null, 2); }
async function api(path, opts={}){ const r = await fetch('/live-launch-api'+path, opts); const data = await r.json(); if(!r.ok) throw data; return data; }
function checkDot(ok){ return `<span class="dot ${ok?'ok':'bad'}">${ok?'✓':'!'}</span>`; }
async function loadStatus(){
  try{
    const s = await api('/status');
    $('score').textContent = s.readiness_score;
    $('scoreText').textContent = s.readiness_score >= 80 ? 'Spremno za zatvoreni pilot' : 'Još treba priprema';
    $('mProducts').textContent = s.metrics.public_products;
    $('mImages').textContent = `${s.metrics.products_with_image} (${s.metrics.image_rate}%)`;
    $('mGps').textContent = `${s.metrics.products_with_gps} (${s.metrics.gps_rate}%)`;
    $('mStores').textContent = s.metrics.active_stores;
    $('missing').innerHTML = s.missing.length ? s.missing.map(x=>`<span class="pill">${x}</span>`).join('') : '<span class="pill okpill">Nema velikih blokera</span>';
    $('recs').innerHTML = s.recommended_next.map(x=>`<div class="check">${checkDot(false)}<div><b>Preporuka</b><small>${x}</small></div></div>`).join('') || '<div class="check">'+checkDot(true)+'<div><b>Dobro izgleda</b><small>Može zatvoreni pilot.</small></div></div>';
    $('envChecks').innerHTML = s.env_checks.map(c=>`<div class="env-row"><b>${c.key}</b><span>${c.ok?'✅ OK':'⚠️ Proveri'}</span><small>${c.message}<br><b>Vrednost:</b> ${c.value}</small></div>`).join('');
    log(s);
  }catch(e){ log(e); }
}
async function makeBackup(){ try{ log('Pravim backup...'); log(await api('/backup',{method:'POST'})); }catch(e){ log(e); } }
async function makeEnv(){ try{ const data = await api('/production-env'); log(data.content); }catch(e){ log(e); } }
async function makeSitemap(){ try{ log(await api('/sitemap-preview')); }catch(e){ log(e); } }
async function seedChecklist(){
  try{
    const data = await api('/seed-launch-checklist',{method:'POST'});
    $('checklist').innerHTML = data.items.map(i=>`<div class="check">${checkDot(false)}<div><b>${i.area}</b><small>${i.task}<br>Owner: ${i.owner} · Status: ${i.status}</small></div></div>`).join('');
    log(data);
  }catch(e){ log(e); }
}
loadStatus();
