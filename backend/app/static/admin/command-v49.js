const $49=id=>document.getElementById(id);
const toast49=(m)=>{const t=$49('toast49');t.textContent=m;t.classList.add('show');clearTimeout(window.__t49);window.__t49=setTimeout(()=>t.classList.remove('show'),3200)};
const log49=(m,d)=>{$49('log49').textContent=`[${new Date().toLocaleTimeString()}] ${m}\n${d?JSON.stringify(d,null,2):''}\n\n`+$49('log49').textContent};
async function api49(path,opt={}){const r=await fetch(path,opt);const data=await r.json().catch(()=>({detail:r.statusText}));if(!r.ok)throw new Error(data.detail||r.statusText);return data}
function setLoading49(btn,on){if(!btn)return; if(on){btn.dataset.old=btn.innerHTML;btn.classList.add('loading');btn.innerHTML='<span class="spin49"></span> Radim...';btn.disabled=true}else{btn.classList.remove('loading');btn.innerHTML=btn.dataset.old||btn.innerHTML;btn.disabled=false}}
function metric49(label,value,note=''){return `<div class="metric49"><b>${value??'—'}</b><span>${label}</span>${note?`<small>${note}</small>`:''}</div>`}
function renderStatus49(d){
  const score=d.score??0; document.documentElement.style.setProperty('--score',score); $49('score49').textContent=score;
  const missing=d.missing||[]; $49('missing49').textContent=missing.length?`Još za sređivanje: ${missing.slice(0,4).join(' · ')}`:'Spremno za sledeću fazu. Fokus: realni prodavci i test uplate.';
  const m=d.metrics||{};
  $49('metrics49').innerHTML=[
    metric49('Javne ponude',m.public_products,'cilj 250+'),
    metric49('Sa slikom',m.products_with_image,'slika je obavezna'),
    metric49('GPS ponude',m.products_with_gps,'za mapu i blizinu'),
    metric49('Gradovi',m.cities_with_offers,'pokrivenost tržišta'),
    metric49('Prodavci',m.verified_stores,'verifikovani'),
    metric49('Rezervacije',m.reservations,'test tokova'),
    metric49('Plaćen promet',`${m.paid_revenue||0} RSD`,'IPS/checkout'),
    metric49('Naša provizija',`${m.platform_fee||0} RSD`,'25% platforma'),
  ].join('');
  renderAlerts49(d); renderGrowth49(d.state||{});
}
function renderAlerts49(d){const m=d.metrics||{}; const alerts=[];
  const imgRatio=m.public_products?Math.round((m.products_with_image||0)/(m.public_products||1)*100):0;
  const gpsRatio=m.public_products?Math.round((m.products_with_gps||0)/(m.public_products||1)*100):0;
  alerts.push({t:imgRatio>=95?'ok':imgRatio>=70?'warn':'danger',title:'Slike ponuda',body:`${imgRatio}% ponuda ima sliku. Za live cilj je 95%+.`});
  alerts.push({t:gpsRatio>=90?'ok':gpsRatio>=70?'warn':'danger',title:'GPS i mapa',body:`${gpsRatio}% ponuda ima GPS. Bez toga pretraga u blizini slabi.`});
  alerts.push({t:(m.cities_with_offers||0)>=10?'ok':'warn',title:'Gradovi',body:`Aktivno ${m.cities_with_offers||0} gradova. Fokusiraj 1–3 grada za pravi pilot.`});
  alerts.push({t:(m.reservations||0)>=10?'ok':'warn',title:'Test rezervacije',body:`${m.reservations||0} rezervacija. Pre live-a proći ceo tok: rezervacija → QR → preuzimanje.`});
  $49('alerts49').innerHTML=alerts.map(a=>`<div class="alert49"><i class="dot49 ${a.t==='ok'?'':a.t}"></i><div><strong>${a.title}</strong><p>${a.body}</p></div></div>`).join('');
}
function renderGrowth49(state){const blocks=[];(state.campaigns||[]).forEach(c=>blocks.push(`<div class="card49"><strong>${c.code}</strong> — ${c.title}<br><span class="pill49">${c.discount}%</span><span class="pill49">${c.status}</span><span class="pill49">${c.target}</span></div>`));(state.journeys||[]).forEach(j=>blocks.push(`<div class="card49"><strong>${j.name}</strong><br>${j.trigger}<br><span class="pill49">${j.channel}</span></div>`));(state.experiments||[]).forEach(e=>blocks.push(`<div class="card49"><strong>${e.name}</strong><br>${e.hypothesis||''}<br><span class="pill49">${e.status}</span></div>`));$49('growth49').innerHTML=blocks.length?blocks.join(''):'<div class="card49 empty49">Growth sistem još nije aktiviran.</div>'}
async function refresh49(){const d=await api49('/v48/status');renderStatus49(d);log49('Status osvežen',d.metrics)}
async function seed49(){try{await api49('/v45/seed-consumer-database',{method:'POST'})}catch(e){} const d=await api49('/v48/seed-super-database',{method:'POST'});log49('Velika baza učitana',d);toast49('Baza učitana');await refresh49()}
async function growth49(){const d=await api49('/v48/activate-growth-system',{method:'POST'});log49('Growth sistem aktiviran',d);toast49('Growth aktiviran');await refresh49()}
async function plan49(){const d=await api49('/v48/ai-master-plan');$49('plan49').innerHTML=d.plan.map(p=>`<div class="card49"><strong>${p.area}</strong> <span class="pill49">${p.priority}</span><p>${p.action}</p></div>`).join('')||'<div class="card49 empty49">Nema plana.</div>';log49('AI plan generisan',d)}
async function cities49(){const d=await api49('/v48/city-dashboard');$49('cities49').innerHTML=(d.cities||[]).map(c=>`<div class="row49"><div><strong>${c.city}</strong><br><span class="pill49">${c.offers} ponuda</span><span class="pill49">${c.stores} prodavaca</span><span class="pill49">${c.next_action}</span></div><b>${c.readiness}%</b></div>`).join('')||'<div class="card49 empty49">Nema gradova.</div>';log49('Gradovi osveženi',{count:(d.cities||[]).length})}
async function pricing49(){const d=await api49('/v48/dynamic-pricing');$49('pricing49').innerHTML=(d.suggestions||[]).map(s=>`<div class="row49"><div><strong>${s.product}</strong><br>${s.store||''}<p>${s.reason}</p></div><b>${s.suggested_price} RSD</b></div>`).join('')||'<div class="card49 empty49">Nema hitnih korekcija cena.</div>';log49('Dynamic pricing izračunat',{count:d.count})}
async function dataroom49(){const d=await api49('/v48/data-room');$49('dataroom49').innerHTML=(d.sections||[]).map(sec=>`<div class="card49"><strong>${sec.title}</strong><br>${(sec.items||[]).map(i=>`<span class="pill49">${i}</span>`).join('')}</div>`).join('')||'<div class="card49 empty49">Nema data room podataka.</div>';log49('Data room prikazan',d)}
const actions49={refresh:refresh49,seed:seed49,growth:growth49,plan:plan49,cities:cities49,pricing:pricing49,dataroom:dataroom49,'clear-log':async()=>{$49('log49').textContent='Očišćeno.'}};
document.addEventListener('click',async e=>{const b=e.target.closest('[data-action]'); if(!b)return; const a=b.dataset.action; setLoading49(b,true); try{await (actions49[a]||refresh49)()}catch(err){toast49(err.message);log49('Greška',err.message)}finally{setLoading49(b,false)}});
refresh49().then(()=>Promise.allSettled([plan49(),cities49(),pricing49(),dataroom49()]));
