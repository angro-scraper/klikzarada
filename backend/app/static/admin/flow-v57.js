let demo57 = null;
const $57 = (id)=>document.getElementById(id);
function toast57(msg){const t=$57('toast57');t.textContent=msg;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),3200)}
async function api57(path, opts={}){const r=await fetch(path, opts); const data=await r.json().catch(()=>({})); if(!r.ok) throw new Error(data.detail||data.message||'Greška'); return data;}
function money57(v){return `${Math.round(Number(v||0)).toLocaleString('sr-RS')} RSD`;}
async function loadStatus57(){
  const s=await api57('/flow/status');
  $57('score57').textContent=`${s.ready_percent}%`;
  $57('scoreMsg57').textContent=s.message;
  $57('checks57').innerHTML=s.checks.map(c=>`<div class="flow57-check ${c.ok?'ok':'no'}"><b>${c.ok?'✓':'!'} ${c.label}</b><span>${c.detail}</span></div>`).join('');
  const c=s.counts;
  $57('counts57').innerHTML=[
    ['Aktivne ponude',c.active_products],['Prodavci',`${c.verified_stores}/${c.stores}`],['Rezervacije',c.reservations],['Pri preuzimanju',c.pay_on_pickup],['Provizija za naplatu',money57(c.commission_due_total)],['Preuzeto',c.picked_up],['Plaćeno',c.paid],['Neplaćeno',c.unpaid],['Promet',money57(c.turnover_total)],['Otvoreno',c.pending_or_confirmed]
  ].map(x=>`<span><small>${x[0]}</small><b>${x[1]}</b></span>`).join('');
}
function renderDemo57(d){
  demo57=d;
  const r=d.reservation;
  $57('demoPanel57').classList.remove('hidden');
  $57('demoMessage57').textContent=d.message;
  $57('demoCode57').textContent=r.reservation_code;
  $57('demoStore57').textContent=d.seller_test.store_name || '—';
  $57('demoPin57').textContent=d.seller_test.pin || '—';
  $57('buyerLinks57').innerHTML=`<a href="${d.links.app}">Otvori /app</a><a href="${d.links.checkout}">Checkout</a><a href="${d.links.reservation}">Digitalna karta</a>`;
  $57('ticketLinks57').innerHTML=`<a href="${d.links.reservation}">Otvori digitalnu kartu</a><a href="${d.links.checkout}">Otvori plaćanje</a>`;
  $57('sellerBox57').innerHTML=`<b>Store ID:</b> ${d.seller_test.store_id}<br><b>PIN:</b> ${d.seller_test.pin}<br><b>Kod:</b> ${r.reservation_code}`;
}
async function createDemo57(){
  const b=$57('createDemo57'); const old=b.textContent; b.textContent='Kreiram...'; b.disabled=true;
  try{const d=await api57('/flow/demo-reservation',{method:'POST'}); renderDemo57(d); toast57('Demo rezervacija kreirana'); await loadStatus57();}
  catch(e){toast57(e.message)} finally{b.textContent=old; b.disabled=false;}
}
async function payPickup57(){if(!demo57)return toast57('Prvo kreiraj demo rezervaciju'); const code=demo57.reservation.reservation_code; const d=await api57(`/flow/demo-reservation/${code}/pay-on-pickup`,{method:'POST'}); demo57.reservation=d.reservation; toast57('Plaćanje pri preuzimanju podešeno'); await loadStatus57();}
async function pickedUp57(){if(!demo57)return toast57('Prvo kreiraj demo rezervaciju'); const code=demo57.reservation.reservation_code; const d=await api57(`/flow/demo-reservation/${code}/picked-up`,{method:'POST'}); demo57.reservation=d.reservation; toast57('Preuzimanje potvrđeno'); await loadStatus57();}
async function copyDemo57(){if(!demo57)return toast57('Nema koda'); await navigator.clipboard.writeText(demo57.reservation.reservation_code); toast57('Kod kopiran');}
document.addEventListener('DOMContentLoaded',()=>{
  $57('createDemo57').onclick=createDemo57;
  $57('refresh57').onclick=()=>loadStatus57().catch(e=>toast57(e.message));
  $57('pickupPay57').onclick=()=>payPickup57().catch(e=>toast57(e.message));
  $57('pickedUp57').onclick=()=>pickedUp57().catch(e=>toast57(e.message));
  $57('copyDemo57').onclick=()=>copyDemo57().catch(e=>toast57(e.message));
  loadStatus57().catch(e=>toast57(e.message));
});
