const toastEl = document.getElementById('toast');
function toast(msg){ toastEl.textContent = msg; toastEl.classList.add('show'); setTimeout(()=>toastEl.classList.remove('show'), 3000); }
async function api(path, opts={}){
  const res = await fetch(path, {headers:{'Content-Type':'application/json'}, ...opts});
  if(res.status === 401 || res.redirected){ location.href = '/admin-login?next=/real-data'; return null; }
  if(!res.ok) throw new Error(await res.text());
  return res.json();
}
function fmt(n){ return (n ?? 0).toLocaleString('sr-RS'); }
function money(n){ return `${fmt(Math.round(Number(n||0)))} RSD`; }
function tag(v){ return `<span class="tag ${String(v||'').toLowerCase().replaceAll('_','-')}">${v||''}</span>`; }
function card(title, meta='', body='', extra=''){
  return `<article class="exec-row"><div class="table-header"><h3>${title}</h3>${extra}</div>${meta?`<p><b>${meta}</b></p>`:''}${body?`<p>${body}</p>`:''}</article>`;
}
function setLoading(btn, on, text){ if(!btn) return; btn.disabled = on; btn.dataset.oldText ||= btn.textContent; btn.textContent = on ? text : btn.dataset.oldText; }

async function dashboard(){
  const d = await api('/v42-api/dashboard'); if(!d) return;
  const kpis = [
    ['Real katalog proizvodi', fmt(d.real_catalog_products), `${fmt(d.real_with_image)} sa slikom`],
    ['Cena + izvor', fmt(d.real_with_price), 'reference cene'],
    ['Prodavci', fmt(d.stores_total), `${fmt(d.verified_stores)} verifikovanih`],
    ['Live ponude', fmt(d.visible_offers), `${fmt(d.near_expiry_offers)} pred istek`],
    ['Readiness', `${d.readiness_score}/100`, 'real data score'],
  ];
  document.getElementById('kpis').innerHTML = kpis.map(([a,b,c])=>`<div class="stat-card"><span>${a}</span><strong>${b}</strong><span>${c}</span></div>`).join('');
}

async function products(){
  const rows = await api('/v42-api/products?limit=200'); if(!rows) return;
  document.getElementById('products').innerHTML = rows.map(p=>`
    <article class="offer-card mini-offer">
      <div class="offer-image-wrap">${p.image_url?`<img src="${p.image_url}" alt="${p.name}" loading="lazy" onerror="this.closest('.offer-image-wrap').classList.add('image-error');this.remove();">`:'<div class="image-placeholder">Nema slike</div>'}</div>
      <div class="offer-body">
        <div class="table-header"><h3>${p.name}</h3>${tag(p.status)}</div>
        <p><b>${p.store_name||'-'}</b> · ${p.store_city||'-'} · ${p.category||'-'}</p>
        <p class="price-line">${money(p.price)}</p>
        <p>Quality: <b>${p.quality.score}/100</b> · ${p.quality.issues.length ? p.quality.issues.join(', ') : 'OK'}</p>
        <a class="link-button secondary-link" target="_blank" rel="noopener" href="${p.source_url}">Izvor</a>
      </div>
    </article>`).join('') || '<p class="muted">Nema realnih proizvoda. Klikni “Učitaj realne kataloge”.</p>';
}

async function audit(){
  const d = await api('/v42-api/ai-audit'); if(!d) return;
  document.getElementById('recommendations').innerHTML = (d.recommendations||[]).map(r=>card(r.title, r.priority, r.action, tag(r.priority))).join('');
  const issueRows = Object.entries(d.issues || {}).map(([issue,count])=>{
    const ex = (d.examples[issue]||[]).map(e=>`${e.product} (${e.store||'-'})`).join('<br>');
    return card(issue, `${count} problema`, ex || 'Nema primera', tag(count ? 'review' : 'ok'));
  }).join('');
  const checks = (d.checks||[]).map(c=>card(c.name, c.severity, c.rule, tag(c.severity))).join('');
  document.getElementById('audit').innerHTML = issueRows + checks;
}

async function tasks(){
  const rows = await api('/v42-api/tasks'); if(!rows) return;
  document.getElementById('tasks').innerHTML = rows.map(t=>card(t.title, `${t.owner} · ${t.priority} · ${t.status} · rok ${t.due_date||'-'}`, t.script || t.note || '', tag(t.status))).join('') || '<p class="muted">Nema taskova. Klikni “Napravi outreach taskove”.</p>';
}

async function merchantActions(){
  const rows = await api('/v42-api/ai/merchant-next-actions', {method:'POST'}); if(!rows) return;
  document.getElementById('merchantActions').innerHTML = rows.map(x=>card(`${x.store} · ${x.products} proizvoda`, `${x.verified?'verifikovan':'lead'} · ready ref: ${x.public_ready_reference_products}`, `${x.next_action}<br>Predlog: ${x.suggested_discount_percent}% posle ${x.suggested_discount_window}`, tag(x.verified?'verified':'lead'))).join('') || '<p class="muted">Nema podataka.</p>';
}

async function seed(){ const b=document.getElementById('seedBtn'); setLoading(b,true,'Učitavam realne podatke...'); try{ const r=await api('/v42-api/seed/real-bakery-catalog',{method:'POST'}); toast(`Dodato: ${r.created_stores} prodavaca, ${r.created_products} proizvoda`); await refreshAll(); } finally{ setLoading(b,false); } }
async function makeTasks(){ const b=document.getElementById('tasksBtn'); setLoading(b,true,'Pravim taskove...'); try{ const r=await api('/v42-api/tasks/create-from-real-data',{method:'POST'}); toast(`Taskovi: +${r.added}, ukupno ${r.total}`); await tasks(); } finally{ setLoading(b,false); } }
async function convertCandidates(){ if(!confirm('Ovo prebacuje real katalog u candidate status, ali ne objavljuje live. Nastaviti?')) return; const r=await api('/v42-api/convert/catalog-to-candidates?max_items=100',{method:'POST'}); toast(r.message); await refreshAll(); }
async function refreshAll(){ await Promise.all([dashboard(), products(), audit(), tasks()]); }

document.getElementById('seedBtn').addEventListener('click', seed);
document.getElementById('auditBtn').addEventListener('click', audit);
document.getElementById('tasksBtn').addEventListener('click', makeTasks);
document.getElementById('candidateBtn').addEventListener('click', convertCandidates);
document.getElementById('refreshBtn').addEventListener('click', refreshAll);
document.getElementById('merchantAiBtn').addEventListener('click', merchantActions);
refreshAll().catch(e=>toast(e.message));
