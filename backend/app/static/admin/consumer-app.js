const state45 = {
  offers: [], facets: {}, userLocation: null, map: null, markers: [], selectedOffer: null,
  cityCenters: { 'Beograd':[44.8125,20.4612], 'Novi Sad':[45.2671,19.8335], 'Niš':[43.3209,21.8958], 'Kragujevac':[44.0128,20.9114], 'Subotica':[46.1005,19.6651], 'Čačak':[43.8914,20.3497], 'Kraljevo':[43.7234,20.6870], 'Leskovac':[42.9981,21.9461], 'Valjevo':[44.2751,19.8982], 'Zrenjanin':[45.3836,20.3819], 'Pančevo':[44.8708,20.6403], 'Šabac':[44.7562,19.6922], 'Sombor':[45.7733,19.1151], 'Užice':[43.8586,19.8442], 'Kruševac':[43.5800,21.3267], 'Smederevo':[44.6659,20.9335] },
};
const $45 = (id) => document.getElementById(id);
const STATUS45 = { public_discount:'Akcijska ponuda', seller_verified:'Potvrđeno', near_expiry:'Pred istek roka', candidate:'Kandidat' };
const CATEGORY_WORDS45 = ['pekara','restoran','market','mlečni proizvodi','voće i povrće','mesara','ribarnica','poslastice','gotova jela','zdrava hrana','delikates','pića','smrznuta hrana','sendviči','salate','kafa i doručak','korpa iznenađenja'];
function escape45(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function money45(n,c='RSD'){return `${Number(n||0).toLocaleString('sr-RS',{maximumFractionDigits:0})} ${c}`;}
function toast45(msg){const t=$45('toast45'); if(!t) return; t.textContent=msg; t.classList.add('show'); clearTimeout(window.__t45); window.__t45=setTimeout(()=>t.classList.remove('show'),3600);}
function loading45(btn,text='Radim...'){if(!btn)return()=>{};const old=btn.innerHTML;btn.disabled=true;btn.innerHTML=`<span class="fs45-spinner"></span>${escape45(text)}`;return()=>{btn.innerHTML=old;btn.disabled=false;};}
async function api45(url,opt={}){const r=await fetch(url,opt); if(!r.ok){let txt=await r.text(); try{txt=JSON.parse(txt).detail||txt}catch(_){} throw new Error(txt||`HTTP ${r.status}`)} return r.json();}
function favs45(){try{return JSON.parse(localStorage.getItem('fs45_favorites')||'[]').map(Number)}catch(_){return[]}}
function saveFavs45(x){localStorage.setItem('fs45_favorites',JSON.stringify([...new Set(x.map(Number))]));}
function isFav45(id){return favs45().includes(Number(id));}
function savedSearches45(){try{return JSON.parse(localStorage.getItem('fs45_searches')||'[]')}catch(_){return[]}}
function setSavedSearches45(x){localStorage.setItem('fs45_searches',JSON.stringify(x.slice(0,12)));}
function field45(id){return $45(id)?.value ?? ''}
function setField45(id,v){const el=$45(id); if(el) el.value=v??'';}
function checkbox45(id){return !!$45(id)?.checked;}

async function init45(){
  addEvents45();
  initMap45();
  await loadFacets45();
  renderCityChips45();
  renderQuickChips45();
  await loadReadiness45();
  await loadOffers45();
  initChat45();
  setTimeout(()=>state45.map?.invalidateSize(),250);
}
function addEvents45(){
  $45('searchBtn45').addEventListener('click',()=>loadOffers45().catch(e=>toast45(e.message)));
  $45('resetBtn45').addEventListener('click',resetFilters45);
  $45('aiSearchBtn45').addEventListener('click',()=>aiSearch45());
  $45('aiQuery45').addEventListener('keydown',e=>{if(e.key==='Enter')aiSearch45();});
  $45('gpsBtn45').addEventListener('click',requestGps45);
  $45('manualLocBtn45').addEventListener('click',()=>{const lat=Number(field45('manualLat45')),lng=Number(field45('manualLng45')); if(Number.isFinite(lat)&&Number.isFinite(lng)) applyLocation45(lat,lng,'ručni unos'); else toast45('Unesi validne koordinate');});
  $45('centerMapBtn45').addEventListener('click',centerMap45);
  $45('saveSearchBtn45').addEventListener('click',saveSearch45);
  if($45('seedBtn45')) $45('seedBtn45').addEventListener('click',seedDatabase45);
  $45('closeReserve45').addEventListener('click',()=>hideReserve45());
  $45('closeDrawer45').addEventListener('click',()=>hideDrawer45());
  $45('chatSend45').addEventListener('click',sendChat45);
  $45('chatInput45').addEventListener('keydown',e=>{if(e.key==='Enter')sendChat45();});
  ['city45','district45','category45','maxPrice45','minDiscount45','expiring45','radius45','sort45','hasImage45'].forEach(id=>{
    $45(id).addEventListener('change',()=>loadOffers45().catch(e=>toast45(e.message)));
  });
}

async function loadFacets45(){
  const f=await api45('/products/facets'); state45.facets=f;
  fillSelect45('city45',f.cities||[],'Svi gradovi'); fillSelect45('category45',f.categories||[],'Sve kategorije');
  $45('districtList45').innerHTML=(f.belgrade_districts||[]).map(x=>`<option value="${escape45(x)}"></option>`).join('');
}
function fillSelect45(id,items,ph){const el=$45(id); const cur=el.value; el.innerHTML=`<option value="">${escape45(ph)}</option>`+(items||[]).map(x=>`<option value="${escape45(x)}">${escape45(x)}</option>`).join(''); if([...el.options].some(o=>o.value===cur))el.value=cur;}
async function loadReadiness45(){try{const r=await api45('/v45/consumer-readiness'); $45('readinessScore45').textContent=`${r.readiness_score}%`; $45('readinessMsg45').textContent=r.message; if($45('seedBtn45')) $45('seedBtn45').style.display='inline-flex';}catch(e){$45('readinessScore45').textContent='—'; $45('readinessMsg45').textContent='Baza nije proverena';}}
function renderCityChips45(){
  const top=['Beograd','Novi Sad','Niš','Kragujevac','Subotica','Pančevo','Čačak','Kraljevo'];
  const el=$45('cityChips45'); if(!el) return;
  el.innerHTML=top.map(c=>`<button type="button" data-city-chip="${escape45(c)}">${escape45(c)}</button>`).join('');
  el.querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>{setField45('city45',b.dataset.cityChip); centerMap45(); loadOffers45().catch(e=>toast45(e.message));}));
}
function renderQuickChips45(){
  const chips=['Pekara do 250 din','Burek u Vračaru','Ponude blizu mene','Gotova jela u Novom Sadu','Niš sa slikom','Korpa iznenađenja','Najveći popusti','Rok danas','Slatko u blizini'];
  $45('quickChips45').innerHTML=chips.map(c=>`<button type="button" data-ai="${escape45(c)}">${escape45(c)}</button>`).join('');
  $45('quickChips45').querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>{setField45('aiQuery45',b.dataset.ai);aiSearch45();}));
}

function parseAi45(text){
  const t=(text||'').toLowerCase();
  const cities=state45.facets.cities||Object.keys(state45.cityCenters);
  for(const c of cities){ if(t.includes(c.toLowerCase())) setField45('city45',c); }
  const districts=state45.facets.belgrade_districts||[];
  for(const d of districts){ if(t.includes(d.toLowerCase())) setField45('district45',d); }
  for(const c of CATEGORY_WORDS45){ if(t.includes(c.toLowerCase())) setField45('category45',c); }
  if(t.includes('burek')||t.includes('kif')||t.includes('hleb')||t.includes('peciv')) setField45('category45','pekara');
  if(t.includes('ručak')||t.includes('rucak')||t.includes('gotov')||t.includes('meni')) setField45('category45','gotova jela');
  if(t.includes('sendvi')) setField45('category45','sendviči');
  if(t.includes('salat')) setField45('category45','salate');
  if(t.includes('kolac')||t.includes('kolač')||t.includes('slat')) setField45('category45','poslastice');
  const price=t.match(/do\s*(\d{2,5})/); if(price) setField45('maxPrice45',price[1]);
  if(t.includes('slik')) $45('hasImage45').checked=true;
  if(t.includes('danas')) setField45('expiring45','0'); else if(t.includes('sutra')) setField45('expiring45','1');
  if(t.includes('popust')) setField45('sort45','discount_desc');
  if(t.includes('najbli')||t.includes('blizu')) { setField45('sort45','distance_asc'); if(!field45('radius45')) setField45('radius45','5'); }
  setField45('aiQuery45', text);
  setField45('q45', '');
}
function aiSearch45(){parseAi45(field45('aiQuery45')); loadOffers45().catch(e=>toast45(e.message)); addChat45('user',field45('aiQuery45')); addChat45('bot','Primeniću filtere i prikazati najrelevantnije ponude. Možeš odmah uključiti GPS za rezultate u blizini.');}
function resetFilters45(){['aiQuery45','district45','maxPrice45','minDiscount45','expiring45','radius45'].forEach(id=>setField45(id,'')); setField45('city45',''); setField45('category45',''); setField45('sort45','distance_asc'); $45('hasImage45').checked=true; loadOffers45().catch(e=>toast45(e.message));}
function buildUrl45(){
  const p=new URLSearchParams();
  const map={city:'city45',district:'district45',category:'category45',max_price:'maxPrice45',min_discount:'minDiscount45',expiring_days:'expiring45',sort:'sort45'};
  for(const [k,id] of Object.entries(map)){const v=field45(id); if(v) p.set(k,v);}
  const ai=field45('aiQuery45').trim(); if(ai && !state45.facets.cities?.some(c=>ai.toLowerCase().includes(c.toLowerCase()))) p.set('q',ai);
  p.set('public_only','true'); p.set('only_active','true'); p.set('only_available','true');
  if(checkbox45('hasImage45')) p.set('has_image','true');
  if(state45.userLocation && field45('radius45')){p.set('lat',state45.userLocation.lat);p.set('lng',state45.userLocation.lng);p.set('radius_km',field45('radius45'));}
  return `/products?${p.toString()}`;
}
function renderSkeleton45(){ $45('offersGrid45').innerHTML=Array.from({length:6}).map(()=>`<div class="fs45-offer fs45-skeleton"></div>`).join(''); }
async function loadOffers45(){
  renderSkeleton45(); renderActiveFilters45();
  const data=await api45(buildUrl45()); state45.offers=data; renderOffers45(data); renderMap45(data); renderStats45(data); renderSaved45();
}
function renderStats45(data){
  const cities=new Set(data.map(p=>p.store_city).filter(Boolean));
  $45('statOffers45').textContent=data.length; $45('statCities45').textContent=cities.size; $45('statImages45').textContent=data.filter(p=>p.image_url).length;
  $45('resultsMeta45').textContent=data.length?`${data.length} ponuda pronađeno. Rezervacija, QR plaćanje i digitalna karta su dostupni na kartici ponude.`:'Nema rezultata za ove filtere.';
}
function renderActiveFilters45(){
  const rows=[['Grad','city45'],['Naselje','district45'],['Kategorija','category45'],['Cena do','maxPrice45'],['Popust od','minDiscount45'],['Rok','expiring45'],['Radius','radius45']];
  const chips=[]; for(const [l,id] of rows){const v=field45(id); if(v) chips.push(`<span>${escape45(l)}: ${escape45(v)}</span>`);} if(state45.userLocation) chips.push(`<span>GPS uključen</span>`); if(checkbox45('hasImage45')) chips.push('<span>Samo sa slikom</span>');
  $45('activeFilters45').innerHTML=chips.join('');
}
function priceHtml45(p){return `<span class="fs45-new-price">${money45(p.discounted_price,p.currency)}</span>${p.original_price?`<span class="fs45-old-price">${money45(p.original_price,p.currency)}</span>`:''}`;}
function card45(p){
  const dist=p.distance_km!=null?`<span>📍 ${p.distance_km} km</span>`:''; const fav=isFav45(p.id)?'♥':'♡';
  const urgency=p.expiry_date?`Rok ${escape45(p.expiry_date)}`:'Rok nije potvrđen';
  return `<article class="fs45-offer" data-card-id="${p.id}">
    <div class="fs45-img"><img src="${escape45(p.image_url||'/admin-assets/seed-images/pecivo-mix.svg')}" alt="${escape45(p.name)}" loading="lazy"/><div class="fs45-badge-row"><span class="fs45-badge fs45-discount">-${Math.round(p.discount_percent||0)}%</span><button class="fs45-fav" data-fav="${p.id}" title="Omiljeno">${fav}</button></div><div class="fs45-img-bottom">${escape45(STATUS45[p.status]||p.status)}</div></div>
    <div class="fs45-offer-body"><div class="fs45-card-top"><span>${escape45(p.category||'ostalo')}</span><span>${p.available_quantity??'—'} kom</span></div><h3>${escape45(p.name)}</h3><p class="fs45-store">${escape45(p.store_name||'Prodavac')} · ${escape45(p.store_city||'')}</p><p class="fs45-address">${escape45(p.store_address||'')}</p><div class="fs45-price">${priceHtml45(p)}</div><div class="fs45-meta"><span>${urgency}</span><span>${escape45(p.pickup_window||'preuzimanje dogovor')}</span>${dist}</div><div class="fs45-card-actions"><button data-reserve="${p.id}">Rezerviši</button><button data-drawer="${p.id}" class="fs45-soft">Pregled</button></div></div>
  </article>`;
}
function renderOffers45(data){
  const empty=$45('emptyState45'); empty.classList.toggle('hidden',data.length>0);
  if(!data.length){empty.innerHTML=`<h3>Nema ponuda za izabrane filtere</h3><p>Probaj širi radius, drugi grad ili učitaj pilot bazu da testiraš aplikaciju sa mapom, plaćanjem i preuzimanjem.</p><button id="emptySeed45" class="fs45-primary">Učitaj pilot bazu</button> <button id="emptyReset45" class="fs45-ghost">Prikaži sve</button>`; $45('offersGrid45').innerHTML=''; $45('emptySeed45').onclick=seedDatabase45; $45('emptyReset45').onclick=resetFilters45; return;}
  empty.innerHTML=''; $45('offersGrid45').innerHTML=data.map(card45).join('');
  document.querySelectorAll('[data-reserve]').forEach(b=>b.onclick=()=>openReserve45(Number(b.dataset.reserve)));
  document.querySelectorAll('[data-fav]').forEach(b=>b.onclick=()=>toggleFav45(Number(b.dataset.fav)));
  document.querySelectorAll('[data-drawer]').forEach(b=>b.onclick=()=>openDrawer45(Number(b.dataset.drawer)));
}

function initMap45(){
  if(!window.L){$45('map45').innerHTML='Mapa nije učitana.';return;}
  state45.map=L.map('map45',{zoomControl:true}).setView([44.8125,20.4612],12);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap'}).addTo(state45.map);
  state45.map.on('click',e=>applyLocation45(e.latlng.lat,e.latlng.lng,'klik na mapu'));
}
function markerIcon45(type='offer'){return L.divIcon({className:'',html:`<div class="fs45-marker ${type==='user'?'user':''}">${type==='user'?'●':'🥐'}</div>`,iconSize:[32,32],iconAnchor:[16,16]});}
function clearMap45(){state45.markers.forEach(m=>m.remove()); state45.markers=[];}
function renderMap45(data){
  if(!state45.map) return; clearMap45(); const pts=[];
  if(state45.userLocation){const m=L.marker([state45.userLocation.lat,state45.userLocation.lng],{icon:markerIcon45('user')}).addTo(state45.map).bindPopup('Tvoja lokacija'); state45.markers.push(m); pts.push([state45.userLocation.lat,state45.userLocation.lng]);}
  data.filter(p=>p.store_latitude!=null&&p.store_longitude!=null).forEach(p=>{const m=L.marker([p.store_latitude,p.store_longitude],{icon:markerIcon45('offer')}).addTo(state45.map).bindPopup(`<div class="fs45-popup"><strong>${escape45(p.name)}</strong>${escape45(p.store_name||'')}<br>${money45(p.discounted_price,p.currency)}<br><button onclick="window.__reserve45(${p.id})">Rezerviši</button></div>`); state45.markers.push(m); pts.push([p.store_latitude,p.store_longitude]);});
  if(pts.length>1) state45.map.fitBounds(pts,{padding:[35,35],maxZoom:14}); else if(pts.length===1) state45.map.setView(pts[0],14); else centerMap45();
}
window.__reserve45=(id)=>openReserve45(id);
function centerMap45(){
  if(!state45.map)return; const city=field45('city45'); if(state45.userLocation) state45.map.setView([state45.userLocation.lat,state45.userLocation.lng],14); else if(city&&state45.cityCenters[city]) state45.map.setView(state45.cityCenters[city],12); else state45.map.setView([44.8125,20.4612],7);
}
function requestGps45(){
  if(!navigator.geolocation){toast45('Browser ne podržava GPS. Unesi lokaciju ručno ili klikni na mapu.');return;}
  const done=loading45($45('gpsBtn45'),'Tražim GPS...');
  navigator.geolocation.getCurrentPosition(pos=>{done(); applyLocation45(pos.coords.latitude,pos.coords.longitude,'GPS'); if(!field45('radius45')) setField45('radius45','5'); setField45('sort45','distance_asc'); loadOffers45().catch(e=>toast45(e.message));},err=>{done(); toast45(gpsMessage45(err)); $45('locationStatus45').textContent=gpsMessage45(err)+' Možeš kliknuti na mapu ili uneti koordinate.';},{enableHighAccuracy:true,timeout:18000,maximumAge:60000});
}
function gpsMessage45(err){if(err.code===1)return'GPS dozvola je odbijena.'; if(err.code===2)return'GPS lokacija nije dostupna.'; if(err.code===3)return'GPS je istekao. Probaj ponovo.'; return'GPS nije uspeo.';}
function applyLocation45(lat,lng,source){state45.userLocation={lat:Number(lat),lng:Number(lng)}; setField45('manualLat45',Number(lat).toFixed(6)); setField45('manualLng45',Number(lng).toFixed(6)); $45('locationStatus45').textContent=`Lokacija podešena (${source}): ${Number(lat).toFixed(5)}, ${Number(lng).toFixed(5)}`; renderActiveFilters45(); renderMap45(state45.offers);}

function toggleFav45(id){const f=favs45(); const n=Number(id); const next=f.includes(n)?f.filter(x=>x!==n):f.concat(n); saveFavs45(next); renderOffers45(state45.offers); renderSaved45();}
function saveSearch45(){const snap={label:[field45('aiQuery45'),field45('city45'),field45('category45'),field45('maxPrice45')?`do ${field45('maxPrice45')} RSD`:'' ].filter(Boolean).join(' · ')||'Pretraga', city:field45('city45'),district:field45('district45'),category:field45('category45'),maxPrice:field45('maxPrice45'),minDiscount:field45('minDiscount45'),expiring:field45('expiring45'),radius:field45('radius45'),q:field45('aiQuery45')}; setSavedSearches45([snap,...savedSearches45()]); renderSaved45(); toast45('Pretraga je sačuvana');}
function applySaved45(s){setField45('aiQuery45',s.q);setField45('city45',s.city);setField45('district45',s.district);setField45('category45',s.category);setField45('maxPrice45',s.maxPrice);setField45('minDiscount45',s.minDiscount);setField45('expiring45',s.expiring);setField45('radius45',s.radius);loadOffers45().catch(e=>toast45(e.message));}
function renderSaved45(){
  const searches=savedSearches45(); $45('savedSearches45').innerHTML=searches.length?searches.map((s,i)=>`<button data-saved="${i}">${escape45(s.label)}</button>`).join(''):'<small>Nema sačuvanih pretraga.</small>';
  $45('savedSearches45').querySelectorAll('[data-saved]').forEach(b=>b.onclick=()=>applySaved45(searches[Number(b.dataset.saved)]));
  const ids=favs45(); const favOffers=state45.offers.filter(p=>ids.includes(Number(p.id))); $45('favorites45').innerHTML=favOffers.length?favOffers.map(p=>`<button data-favopen="${p.id}">${escape45(p.name)} · ${money45(p.discounted_price,p.currency)}</button>`).join(''):'<small>Sačuvaj ponude klikom na srce.</small>';
  $45('favorites45').querySelectorAll('[data-favopen]').forEach(b=>b.onclick=()=>openDrawer45(Number(b.dataset.favopen)));
}

function findOffer45(id){return state45.offers.find(p=>Number(p.id)===Number(id));}
function openDrawer45(id){const p=findOffer45(id); if(!p)return; $45('drawerContent45').innerHTML=`<img src="${escape45(p.image_url||'/admin-assets/seed-images/pecivo-mix.svg')}" alt="${escape45(p.name)}"><h2>${escape45(p.name)}</h2><p>${escape45(p.store_name)} · ${escape45(p.store_city)} · ${escape45(p.store_address||'')}</p><div class="fs45-price">${priceHtml45(p)}</div><div class="fs45-meta"><span>${escape45(p.category)}</span><span>${p.available_quantity??'—'} kom</span><span>Rok: ${escape45(p.expiry_date||'nije potvrđen')}</span><span>Preuzimanje: ${escape45(p.pickup_window||'dogovor')}</span></div><button class="fs45-primary" onclick="window.__reserve45(${p.id})">Rezerviši sada</button>`; $45('offerDrawer45').classList.remove('hidden');}
function hideDrawer45(){ $45('offerDrawer45').classList.add('hidden'); }
function hideReserve45(){ $45('reserveModal45').classList.add('hidden'); }
function openReserve45(id){const p=findOffer45(id); if(!p)return; state45.selectedOffer=p; renderReserveForm45(p); $45('reserveModal45').classList.remove('hidden');}
function renderReserveForm45(p){
  $45('reserveContent45').innerHTML=`<div class="fs45-reserve-head"><img src="${escape45(p.image_url||'/admin-assets/seed-images/pecivo-mix.svg')}" alt="${escape45(p.name)}"><div><h2 id="reserveTitle45">${escape45(p.name)}</h2><p>${escape45(p.store_name)} · ${escape45(p.store_city)}</p><div class="fs45-price">${priceHtml45(p)}</div></div></div><div class="fs45-stepper"><span class="active"></span><span></span><span></span></div><div class="fs45-form-grid"><label>Ime<input id="resName45" placeholder="Ime i prezime" autocomplete="name"></label><label>Telefon<input id="resPhone45" placeholder="06..." autocomplete="tel"></label><label>Količina<input id="resQty45" type="number" min="1" max="${p.available_quantity||50}" value="1"></label><label>Email opciono<input id="resEmail45" type="email" placeholder="email@..." autocomplete="email"></label><textarea id="resNote45" placeholder="Napomena za prodavca"></textarea></div><div id="quoteBox45" class="fs45-quote">Unesi telefon za loyalty obračun.</div><div class="fs45-actions-row"><button id="quoteBtn45" class="fs45-ghost">Izračunaj cenu</button><button id="createReservationBtn45" class="fs45-primary">Rezerviši i nastavi na plaćanje</button></div><p class="fs45-small-note">Plaćanje ide kroz checkout/QR ekran. Po uspešnoj rezervaciji dobijaš digitalnu kartu sa kodom za preuzimanje.</p>`;
  $45('quoteBtn45').onclick=()=>loadQuote45(); $45('createReservationBtn45').onclick=()=>createReservation45(); ['resPhone45','resQty45'].forEach(id=>$45(id).addEventListener('change',()=>loadQuote45().catch(()=>{})));
  loadQuote45().catch(()=>{});
}
async function loadQuote45(){const p=state45.selectedOffer; if(!p)return; const qty=Number(field45('resQty45')||1); const phone=field45('resPhone45'); const q=await api45('/payments/quote',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({product_id:p.id,quantity:qty,customer_phone:phone})}); $45('quoteBox45').innerHTML=`<div class="fs45-quote-row"><span>Ukupno</span><strong>${money45(q.gross_amount,q.currency)}</strong></div><div class="fs45-quote-row"><span>Loyalty popust ${q.loyalty_discount_percent||0}%</span><strong>-${money45(q.loyalty_discount_amount,q.currency)}</strong></div><div class="fs45-quote-row"><span>Za plaćanje</span><strong>${money45(q.payable_amount,q.currency)}</strong></div><div class="fs45-quote-row"><span>Prethodna preuzimanja</span><span>${q.previous_successful_pickups}</span></div>`;}
async function createReservation45(){
  const p=state45.selectedOffer; if(!p)return; const btn=$45('createReservationBtn45'); const done=loading45(btn,'Kreiram rezervaciju...');
  try{const body={product_id:p.id,customer_name:field45('resName45'),customer_phone:field45('resPhone45'),customer_email:field45('resEmail45')||null,quantity:Number(field45('resQty45')||1),note:field45('resNote45')||null}; const r=await api45('/reservations',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}); renderReservationSuccess45(r); setTimeout(()=>loadOffers45().catch(()=>{}),250);}catch(e){toast45(e.message)}finally{done();}
}
function renderReservationSuccess45(r){
  $45('reserveContent45').innerHTML=`<div class="fs45-success"><h2>Rezervacija je kreirana</h2><p>Kod pokaži prodavcu pri preuzimanju. Možeš odmah otvoriti QR plaćanje ili digitalnu kartu.</p><div class="fs45-code">${escape45(r.reservation_code)}</div><div class="fs45-quote"><div class="fs45-quote-row"><span>Status</span><strong>${escape45(r.status)}</strong></div><div class="fs45-quote-row"><span>Za plaćanje</span><strong>${money45(r.payable_amount,r.currency)}</strong></div><div class="fs45-quote-row"><span>Loyalty popust</span><strong>${r.loyalty_discount_percent}%</strong></div></div><div class="fs45-success-actions"><a href="/checkout?code=${encodeURIComponent(r.reservation_code)}">Otvori QR plaćanje</a><a href="/reservation?code=${encodeURIComponent(r.reservation_code)}">Digitalna karta</a><button id="copyCode45">Kopiraj kod</button></div></div>`;
  $45('copyCode45').onclick=()=>navigator.clipboard.writeText(r.reservation_code).then(()=>toast45('Kod kopiran'));
}
async function seedDatabase45(){const done=loading45($45('seedBtn45'),'Učitavam bazu Srbije...'); try{const r=await api45('/v45/seed-consumer-database',{method:'POST'}); const r2=await api45('/v48/seed-super-database',{method:'POST'}).catch(()=>null); toast45((r2&&r2.message)||r.message||'Baza učitana'); await loadFacets45(); await loadReadiness45(); await loadOffers45();}catch(e){toast45(e.message)}finally{done();}}

function initChat45(){addChat45('bot','Zdravo! Mogu da pronađem ponude po gradu, radiusu, ceni i kategoriji. Mogu i da objasnim rezervaciju, QR plaćanje i preuzimanje.');}
function addChat45(who,text){const box=$45('chatBox45'); box.insertAdjacentHTML('beforeend',`<div class="fs45-msg ${who==='user'?'user':'bot'}">${escape45(text)}</div>`); box.scrollTop=box.scrollHeight;}
function sendChat45(){const text=field45('chatInput45').trim(); if(!text)return; setField45('chatInput45',''); addChat45('user',text); const t=text.toLowerCase(); let ans='Mogu da ti pomognem da pronađeš ponudu, objasnim plaćanje, digitalnu kartu, preuzimanje, loyalty ili bezbednost hrane. Napiši grad, kategoriju ili cenu, npr. “pekara u Nišu do 250 din”.'; if(t.includes('plać')||t.includes('qr')) ans='Posle rezervacije dobijaš checkout link. Na njemu je QR za plaćanje i digitalna karta. Kod pokazuješ prodavcu pri preuzimanju.'; else if(t.includes('preuz')) ans='Na kartici ponude piše vreme preuzimanja. Kada stigneš, pokažeš digitalnu kartu ili kod rezervacije.'; else if(t.includes('gps')||t.includes('lokac')) ans='Klikni “Uključi GPS”. Ako browser blokira lokaciju, klikni na mapu ili ručno unesi latitude/longitude.'; else if(t.includes('rok')||t.includes('istek')) ans='Ponude sa kraćim rokom imaju jasno prikazan rok. Aplikacija razlikuje javnu akciju i ponudu pred istek koju prodavac potvrđuje.'; else if(t.includes('nema')||t.includes('ponud')) ans='Ako nema rezultata, proširi radius, ukloni maksimalnu cenu ili promeni grad. Za test možeš učitati pilot bazu.'; else if(t.includes('rezerv')) ans='Klikneš Rezerviši, uneseš ime, telefon i količinu. Dobijaš kod i digitalnu kartu. Zatim možeš otvoriti QR plaćanje i pri preuzimanju pokazuješ kod prodavcu.'; else if(t.includes('loyal')||t.includes('popust')) ans='Stalni kupci dobijaju loyalty popust 1–5%. Sistem ga računa po telefonu pri rezervaciji i prikazuje pre plaćanja.'; else if(t.includes('slika')||t.includes('kvalitet')) ans='Javne ponude treba da imaju sliku, cenu, količinu, rok i vreme preuzimanja. To je deo kontrole kvaliteta pre izlaska uživo.'; addChat45('bot',ans);}

document.addEventListener('DOMContentLoaded',()=>init45().catch(e=>toast45(e.message)));
