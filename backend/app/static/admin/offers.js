const $ = (id) => document.getElementById(id);
const statusLabels = {
  public_discount: 'Akcijska cena',
  seller_verified: 'Potvrđeno',
  near_expiry: 'Pred istek',
  candidate: 'Kandidat',
  needs_review: 'Provera',
  expired: 'Isteklo',
  hidden: 'Sakriveno',
};
const reservationStatusLabels = {
  pending: 'Čeka potvrdu',
  confirmed: 'Potvrđeno',
  picked_up: 'Preuzeto',
  cancelled: 'Otkazano',
  expired: 'Isteklo',
};

let userLocation = null;
let offersMap = null;
let offerMarkers = [];
let lastLoadedOffers = [];
let lastAiProducts = [];
let currentReservationProduct = null;

function toast(message) {
  const el = $('toast');
  el.textContent = message;
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 3200);
}

function setButtonLoading(button, loadingText = 'Radim...') {
  if (!button) return () => {};
  const original = button.innerHTML;
  button.disabled = true;
  button.classList.add('is-loading');
  button.innerHTML = `<span class="spinner-dot"></span>${loadingText}`;
  return () => {
    button.disabled = false;
    button.classList.remove('is-loading');
    button.innerHTML = original;
  };
}

function escapeHtml(str) {
  return String(str ?? '').replace(/[&<>'"]/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
}

function money(product) {
  const currency = product.currency || 'RSD';
  const oldPrice = product.original_price ? `${Number(product.original_price).toLocaleString('sr-RS')} ${currency}` : '';
  const newPrice = product.discounted_price ? `${Number(product.discounted_price).toLocaleString('sr-RS')} ${currency}` : '';
  if (oldPrice && newPrice && oldPrice !== newPrice) return `<span class="old-price">${oldPrice}</span> <strong>${newPrice}</strong>`;
  return newPrice || oldPrice || '-';
}
function moneyPlain(amount, currency = 'RSD') {
  const value = Number(amount || 0);
  return `${value.toLocaleString('sr-RS', { maximumFractionDigits: 2 })} ${currency}`;
}

function paymentStatusLabel(status) {
  const labels = { unpaid: 'Čeka plaćanje', paid: 'Plaćeno online', refunded: 'Refundirano', failed: 'Neuspešno', refund_pending: 'Refund u toku' };
  return labels[status] || status || '-';
}

function paymentSummaryHtml(data, { showPlatformFee = false, showSellerNet = false } = {}) {
  if (!data) return '';
  const currency = data.currency || 'RSD';
  return `
    <div class="payment-box-v28">
      <div class="payment-row-v28"><span>Ukupno proizvodi</span><strong>${moneyPlain(data.gross_amount, currency)}</strong></div>
      <div class="payment-row-v28"><span>Popust za stalne kupce</span><strong>${Number(data.loyalty_discount_percent || 0).toFixed(0)}% · -${moneyPlain(data.loyalty_discount_amount, currency)}</strong></div>
      <div class="payment-row-v28 total"><span>Za online plaćanje</span><strong>${moneyPlain(data.payable_amount, currency)}</strong></div>
      ${showPlatformFee ? `<div class="payment-row-v28"><span>Provizija platforme</span><strong>${Number(data.platform_fee_percent || 25).toFixed(0)}% · ${moneyPlain(data.platform_fee_amount, currency)}</strong></div>` : ''}
      ${showSellerNet ? `<div class="payment-row-v28"><span>Neto prodavcu</span><strong>${moneyPlain(data.seller_net_amount, currency)}</strong></div>` : ''}
      ${data.message ? `<p class="payment-note-v28">${escapeHtml(data.message)}</p>` : ''}
    </div>`;
}

async function loadPaymentQuote() {
  if (!currentReservationProduct) return;
  const formEl = $('reservationForm');
  const preview = $('paymentPreview');
  const quantity = Number(formEl.elements.quantity.value || 1);
  const phone = formEl.elements.customer_phone.value || '';
  if (!quantity || quantity < 1) return;
  preview.innerHTML = 'Računam cenu...';
  try {
    const quote = await request('/payments/quote', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ product_id: Number($('reservationProductId').value), quantity, customer_phone: phone || null }),
    });
    preview.innerHTML = paymentSummaryHtml(quote);
  } catch (err) {
    preview.innerHTML = `<span class="danger-text">${escapeHtml(err.message)}</span>`;
  }
}

async function payReservation(code, phone, triggerButton = null) {
  const done = setButtonLoading(triggerButton, 'Otvaram plaćanje...');
  try {
    await request(`/payments/reservations/${encodeURIComponent(code)}/checkout`);
    window.location.href = `/checkout?code=${encodeURIComponent(code)}`;
  } catch (err) {
    toast(`Plaćanje nije spremno: ${err.message}`);
  } finally {
    done();
  }
}


function statusLabel(status) { return statusLabels[status] || status || '-'; }
function reservationStatusLabel(status) { return reservationStatusLabels[status] || status || '-'; }

function geolocationProblemMessage(err) {
  if (!window.isSecureContext && !['localhost', '127.0.0.1', '::1'].includes(window.location.hostname)) {
    return 'GPS je blokiran jer stranica nije HTTPS. Otvori preko http://127.0.0.1:8000 ili kasnije preko HTTPS adrese.';
  }
  if (!err) return 'GPS nije dostupan u ovom browseru.';
  if (err.code === 1) return 'GPS dozvola je odbijena. U browseru dozvoli Location za ovu stranicu.';
  if (err.code === 2) return 'Lokacija trenutno nije dostupna. Probaj Wi‑Fi/GPS ili unesi koordinate ručno.';
  if (err.code === 3) return 'GPS je istekao pre nego što je našao lokaciju. Probaj ponovo ili unesi koordinate ručno.';
  return `GPS greška: ${err.message || 'nepoznata greška'}`;
}

function applyUserLocation(lat, lng, sourceLabel = 'GPS') {
  const latNum = Number(lat);
  const lngNum = Number(lng);
  if (!Number.isFinite(latNum) || !Number.isFinite(lngNum)) return toast('Unesi ispravne GPS koordinate');
  userLocation = { lat: Number(latNum.toFixed(6)), lng: Number(lngNum.toFixed(6)) };
  if (!$('radiusFilter').value) $('radiusFilter').value = '5';
  $('sortFilter').value = 'distance_asc';
  $('manualLatFilter').value = userLocation.lat;
  $('manualLngFilter').value = userLocation.lng;
  $('locationStatus').textContent = `${sourceLabel}: ${userLocation.lat}, ${userLocation.lng}`;
  loadOffers().catch((err) => toast(`Greška: ${err.message}`));
}

function setManualLocation() { applyUserLocation($('manualLatFilter').value, $('manualLngFilter').value, 'Ručna lokacija'); }

function useMyLocation() {
  if (!navigator.geolocation) {
    const msg = 'Browser ne podržava GPS lokaciju. Unesi Lat/Lng ručno ili klikni na mapu.';
    $('locationStatus').textContent = msg;
    return toast(msg);
  }
  if (!window.isSecureContext && !['localhost', '127.0.0.1', '::1'].includes(window.location.hostname)) {
    const msg = geolocationProblemMessage();
    $('locationStatus').textContent = msg;
    return toast(msg);
  }
  const done = setButtonLoading($('useLocationBtn'), 'Tražim lokaciju...');
  $('locationStatus').textContent = 'Tražim GPS lokaciju...';
  navigator.geolocation.getCurrentPosition((pos) => {
    done();
    applyUserLocation(pos.coords.latitude, pos.coords.longitude, 'GPS');
  }, (err) => {
    done();
    const msg = geolocationProblemMessage(err);
    $('locationStatus').textContent = msg;
    toast(msg);
  }, { enableHighAccuracy: true, timeout: 20000, maximumAge: 60000 });
}

async function request(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) {
    let text = await res.text();
    try { text = JSON.parse(text).detail || text; } catch (_) {}
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}

function productUrl() {
  const params = new URLSearchParams();
  const fields = {
    q: $('qFilter').value.trim(),
    city: $('cityFilter').value,
    district: $('districtFilter').value.trim(),
    category: $('categoryFilter').value,
    status: $('statusFilter').value,
    sort: $('sortFilter').value,
    min_discount: $('minDiscountFilter').value,
    max_price: $('maxPriceFilter').value,
    expiring_days: $('expiringDaysFilter').value,
  };
  for (const [key, value] of Object.entries(fields)) {
    if (value !== '' && value !== null && value !== undefined) params.set(key, value);
  }
  if ($('hasImageFilter').checked) params.set('has_image', 'true');
  const radius = $('radiusFilter').value;
  if (userLocation && radius) {
    params.set('lat', userLocation.lat);
    params.set('lng', userLocation.lng);
    params.set('radius_km', radius);
  }
  params.set('only_active', 'true');
  params.set('only_available', 'true');
  params.set('public_only', 'true');
  return `/products?${params.toString()}`;
}

function updateUrlFromFilters() {
  const params = new URLSearchParams();
  const mapping = {
    q: 'qFilter', city: 'cityFilter', district: 'districtFilter', category: 'categoryFilter', status: 'statusFilter', sort: 'sortFilter',
    minDiscount: 'minDiscountFilter', maxPrice: 'maxPriceFilter', expiringDays: 'expiringDaysFilter', radius: 'radiusFilter',
  };
  for (const [key, id] of Object.entries(mapping)) {
    const el = $(id);
    if (el && el.value) params.set(key, el.value);
  }
  if ($('hasImageFilter').checked) params.set('hasImage', 'true');
  history.replaceState({}, '', `${location.pathname}${params.toString() ? '?' + params.toString() : ''}`);
}

function readFiltersFromUrl() {
  const params = new URLSearchParams(location.search);
  const mapping = {
    q: 'qFilter', city: 'cityFilter', district: 'districtFilter', category: 'categoryFilter', status: 'statusFilter', sort: 'sortFilter',
    minDiscount: 'minDiscountFilter', maxPrice: 'maxPriceFilter', expiringDays: 'expiringDaysFilter', radius: 'radiusFilter',
  };
  for (const [key, id] of Object.entries(mapping)) if (params.has(key) && $(id)) $(id).value = params.get(key);
  if (params.get('hasImage') === 'true' || params.get('has_image') === 'true') $('hasImageFilter').checked = true;
}

function renderActiveFilters() {
  const chips = [];
  const pairs = [
    ['qFilter', 'Pretraga'], ['cityFilter', 'Grad'], ['districtFilter', 'Naselje'], ['categoryFilter', 'Kategorija'], ['statusFilter', 'Status'],
    ['minDiscountFilter', 'Min. popust'], ['maxPriceFilter', 'Max cena'], ['expiringDaysFilter', 'Rok'], ['radiusFilter', 'Blizina'],
  ];
  for (const [id, label] of pairs) {
    const value = $(id)?.value;
    if (!value) continue;
    const readable = id === 'statusFilter' ? statusLabel(value) : value;
    chips.push(`<span class="filter-chip">${label}: ${escapeHtml(readable)}</span>`);
  }
  if ($('hasImageFilter').checked) chips.push('<span class="filter-chip">Samo sa slikom</span>');
  if (userLocation) chips.push(`<span class="filter-chip">Moja lokacija: ${Number(userLocation.lat).toFixed(4)}, ${Number(userLocation.lng).toFixed(4)}</span>`);
  $('activeFilters').innerHTML = chips.join('');
}

async function loadFacets() {
  const facets = await request('/products/facets');
  fillSelect('cityFilter', facets.cities || [], 'Svi gradovi');
  fillSelect('categoryFilter', facets.categories || [], 'Sve kategorije');
  fillDatalist('districtOptions', facets.belgrade_districts || []);
  renderTaxonomyChips('cityChips', (facets.cities || []).slice(0, 12), 'city');
  const preferredCategories = ['pekara','restoran','market','gotova jela','mlečni proizvodi','voće i povrće','mesara','poslastice','korpa iznenađenja','zdrava hrana'];
  renderTaxonomyChips('categoryChips', preferredCategories.filter(c => (facets.categories || []).includes(c)).concat((facets.categories || []).filter(c => !preferredCategories.includes(c)).slice(0, 6)), 'category');
  readFiltersFromUrl();
}

function fillDatalist(id, items) {
  const list = $(id);
  if (!list) return;
  list.innerHTML = (items || []).map((item) => `<option value="${escapeHtml(item)}"></option>`).join('');
}

function renderTaxonomyChips(id, items, type) {
  const wrap = $(id);
  if (!wrap) return;
  wrap.innerHTML = (items || []).slice(0, 16).map((item) => `<button type="button" data-taxonomy-type="${type}" data-taxonomy-value="${escapeHtml(item)}">${escapeHtml(item)}</button>`).join('');
}

function fillSelect(id, items, placeholder) {
  const select = $(id);
  const current = select.value;
  select.innerHTML = `<option value="">${placeholder}</option>`;
  for (const item of items) {
    const option = document.createElement('option');
    option.value = item;
    option.textContent = item;
    select.appendChild(option);
  }
  if ([...select.options].some(o => o.value === current)) select.value = current;
}

function initMap() {
  const mapEl = $('offersMap');
  if (!mapEl || !window.L) {
    if (mapEl) mapEl.innerHTML = '<div class="map-placeholder">Mapa se nije učitala. Proveri internet konekciju ili koristi listu ponuda.</div>';
    return null;
  }
  if (offersMap) return offersMap;
  mapEl.innerHTML = '';
  offersMap = L.map('offersMap').setView([44.8125, 20.4612], 12);
  offersMap.on('click', (e) => applyUserLocation(e.latlng.lat, e.latlng.lng, 'Lokacija sa mape'));
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors',
  }).addTo(offersMap);
  return offersMap;
}

function clearMapMarkers() {
  if (!offersMap) return;
  for (const marker of offerMarkers) marker.remove();
  offerMarkers = [];
}

function renderOffersMap(products) {
  const map = initMap();
  if (!map) return;
  clearMapMarkers();
  const points = [];
  if (userLocation) {
    const userMarker = L.circleMarker([userLocation.lat, userLocation.lng], { radius: 9 }).addTo(map);
    userMarker.bindPopup('Moja lokacija');
    offerMarkers.push(userMarker);
    points.push([userLocation.lat, userLocation.lng]);
  }
  for (const p of products) {
    if (p.store_latitude === null || p.store_latitude === undefined || p.store_longitude === null || p.store_longitude === undefined) continue;
    const marker = L.marker([p.store_latitude, p.store_longitude]).addTo(map);
    const distance = p.distance_km !== null && p.distance_km !== undefined ? `<p>Udaljenost: <b>${p.distance_km} km</b></p>` : '';
    marker.bindPopup(`
      <strong>${escapeHtml(p.name)}</strong>
      <p>${escapeHtml(p.store_name || 'Prodavac')}</p>
      <p>${money(p)}</p>
      ${distance}
      <p><a href="/offer?id=${p.id}">Detalji</a></p>
      <p><button onclick="window.dispatchEvent(new CustomEvent('reserve-offer-from-map',{detail:{id:${p.id},max:'${p.available_quantity ?? ''}'}}))">Rezerviši</button></p>
    `);
    offerMarkers.push(marker);
    points.push([p.store_latitude, p.store_longitude]);
  }
  if (points.length) map.fitBounds(points, { padding: [28, 28], maxZoom: 15 });
  else map.setView([44.8125, 20.4612], 12);
}

function offerCard(p, compact = false) {
  const availableText = p.available_quantity === null || p.available_quantity === undefined ? 'dostupno' : `${p.available_quantity} kom dostupno`;
  const phoneLink = p.store_phone ? `<a class="link-button secondary-link" href="tel:${escapeHtml(p.store_phone)}">Pozovi</a>` : '';
  const detailUrl = `/offer?id=${p.id}`;
  const distanceText = p.distance_km !== null && p.distance_km !== undefined ? `<p class="note">${p.distance_km} km od tebe</p>` : '';
  const mapLink = p.store_latitude && p.store_longitude ? `<a class="link-button secondary-link" href="https://www.openstreetmap.org/?mlat=${p.store_latitude}&mlon=${p.store_longitude}#map=18/${p.store_latitude}/${p.store_longitude}" target="_blank" rel="noreferrer">Mapa</a>` : '';
  const discountBadge = p.discount_percent ? `<span class="discount-pill-v21">-${Math.round(p.discount_percent)}%</span>` : '';
  return `
    <article class="offer-card-v21 ${compact ? 'compact-offer-v21' : ''}">
      <a href="${detailUrl}" class="image-link-v21">
        ${p.image_url ? `<img class="offer-image-v21" src="${escapeHtml(p.image_url)}" alt="${escapeHtml(p.name)}" loading="lazy" />` : `<div class="offer-image-v21 placeholder-image">Bez slike</div>`}
        ${discountBadge}
      </a>
      <div class="offer-body-v21">
        <div class="offer-top-v21">
          <span class="status status-${escapeHtml(p.status)}">${escapeHtml(statusLabel(p.status))}</span>
          <span class="availability-v21">${escapeHtml(availableText)}</span>
        </div>
        <h3><a href="${detailUrl}">${escapeHtml(p.name)}</a></h3>
        <p class="category">${escapeHtml(p.category || 'bez kategorije')}</p>
        <p class="price-v21">${money(p)}</p><p class="payment-badge-v28">Plaćanje online u aplikaciji</p>
        <p class="store-line-v21"><strong>${escapeHtml(p.store_name || 'Nepoznat prodavac')}</strong>${p.store_city ? ` · ${escapeHtml(p.store_city)}` : ''}</p>
        ${p.store_address ? `<p class="note">${escapeHtml(p.store_address)}</p>` : ''}
        ${distanceText}
        <div class="offer-meta-v21">
          <span>Rok: ${escapeHtml(p.expiry_date || 'nije potvrđen')}</span>
          <span>Preuzimanje: ${escapeHtml(p.pickup_window || 'dogovor')}</span>
        </div>
        <div class="actions offer-actions-v21">
          <button data-reserve-id="${p.id}" data-product-name="${escapeHtml(p.name)}" data-max="${p.available_quantity ?? ''}">Rezerviši</button>
          <a class="link-button secondary-link" href="${detailUrl}">Detalji</a>
          ${phoneLink}${mapLink}
        </div>
      </div>
    </article>
  `;
}

function renderLoadingCards() {
  $('offersGrid').innerHTML = Array.from({length: 6}).map(() => `
    <article class="offer-card-v21 skeleton-card-v21">
      <div class="skeleton skeleton-img"></div>
      <div class="skeleton skeleton-line"></div>
      <div class="skeleton skeleton-line small"></div>
      <div class="skeleton skeleton-line"></div>
    </article>
  `).join('');
}

async function loadOffers() {
  updateUrlFromFilters();
  renderActiveFilters();
  renderLoadingCards();
  const products = await request(productUrl());
  lastLoadedOffers = products;
  renderOffersMap(products);
  $('offersCount').textContent = `${products.length} ponuda`;
  const grid = $('offersGrid');
  if (!products.length) {
    grid.innerHTML = `
      <div class="empty-state-v21">
        <h3>Nema ponuda za ove filtere</h3>
        <p>Probaj širi radius, ukloni rok ili pitaj AI: “pokaži sve pekarske ponude”.</p>
        <button data-prompt="Pokaži sve ponude u Beogradu">AI proširi pretragu</button>
      </div>`;
    return;
  }
  grid.innerHTML = products.map((p) => offerCard(p)).join('');
}

function openReservation(productId, productName, max) {
  currentReservationProduct = lastLoadedOffers.find((p) => Number(p.id) === Number(productId)) || lastAiProducts.find((p) => Number(p.id) === Number(productId)) || null;
  $('reservationProductId').value = productId;
  $('reservationProductText').textContent = `Rezervacija za: ${productName || 'ponudu'} · plaćanje ide online kroz aplikaciju.`;
  const quantityInput = $('reservationForm').elements.quantity;
  quantityInput.value = '1';
  quantityInput.removeAttribute('max');
  if (max) quantityInput.max = max;
  $('reservationResult').textContent = '';
  $('paymentPreview').innerHTML = 'Unesi telefon i količinu da vidiš cenu, loyalty popust i iznos za online plaćanje.';
  $('reservationPanel').classList.remove('hidden');
  loadPaymentQuote().catch(() => {});
  $('reservationForm').scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function handleReserveClick(event) {
  const btn = event.target.closest('button[data-reserve-id]');
  if (!btn) return;
  openReservation(btn.dataset.reserveId, btn.dataset.productName, btn.dataset.max);
}

function applyFiltersFromAI(filters) {
  if (!filters) return;
  if (filters.q !== undefined) $('qFilter').value = filters.q || '';
  if (filters.city !== undefined) $('cityFilter').value = filters.city || '';
  if (filters.district !== undefined) $('districtFilter').value = filters.district || '';
  if (filters.category !== undefined) $('categoryFilter').value = filters.category || '';
  if (filters.has_image !== undefined && filters.has_image !== null) $('hasImageFilter').checked = Boolean(filters.has_image);
  if (filters.status !== undefined) $('statusFilter').value = filters.status || '';
  if (filters.sort !== undefined) $('sortFilter').value = filters.sort || 'updated';
  if (filters.min_discount !== undefined && filters.min_discount !== null) $('minDiscountFilter').value = filters.min_discount;
  if (filters.max_price !== undefined && filters.max_price !== null) $('maxPriceFilter').value = filters.max_price;
  if (filters.expiring_days !== undefined && filters.expiring_days !== null) $('expiringDaysFilter').value = filters.expiring_days;
  if (filters.radius_km !== undefined && filters.radius_km !== null) $('radiusFilter').value = filters.radius_km;
}

function aiPayload(message) {
  return {
    message,
    lat: userLocation?.lat ?? null,
    lng: userLocation?.lng ?? null,
    radius_km: $('radiusFilter').value ? Number($('radiusFilter').value) : null,
    city: $('cityFilter').value || null,
    limit: 6,
  };
}

function renderAIRecommended(products) {
  const wrap = $('aiRecommendedProducts');
  lastAiProducts = products || [];
  if (!lastAiProducts.length) {
    wrap.classList.add('hidden');
    wrap.innerHTML = '';
    return;
  }
  wrap.classList.remove('hidden');
  wrap.innerHTML = `
    <div class="section-title-row-v21">
      <div><span class="section-kicker">AI preporuka</span><h2>Najbolje poklapanje</h2></div>
      <button class="secondary" id="hideAiRecommendationsBtn">Sakrij</button>
    </div>
    <div class="ai-product-row-v21">${lastAiProducts.slice(0,3).map((p) => offerCard(p, true)).join('')}</div>
  `;
  $('hideAiRecommendationsBtn')?.addEventListener('click', () => wrap.classList.add('hidden'));
}

async function runAISearch(promptText, triggerButton = null) {
  const message = (promptText ?? $('aiSearchInput').value).trim();
  if (!message) return toast('Napiši šta tražiš');
  const done = setButtonLoading(triggerButton || $('aiSearchBtn'), 'AI traži...');
  try {
    const response = await request('/buyer-ai/parse', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(aiPayload(message)),
    });
    applyFiltersFromAI(response.filters);
    $('aiSearchResult').innerHTML = `<strong>AI rezultat:</strong> ${escapeHtml(response.reply)}${response.tips?.length ? `<ul>${response.tips.map(t => `<li>${escapeHtml(t)}</li>`).join('')}</ul>` : ''}`;
    renderAIRecommended(response.products || []);
    await loadOffers();
    toast('AI je podesio pretragu');
  } catch (err) {
    toast(`AI greška: ${err.message}`);
  } finally {
    done();
  }
}

function appendChat(role, text) {
  const messages = $('aiChatMessages');
  const div = document.createElement('div');
  div.className = `chat-bubble ${role}`;
  div.textContent = text;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}

function renderQuickReplies(items = []) {
  const wrap = $('aiQuickReplies');
  wrap.innerHTML = (items || []).slice(0, 4).map((item) => `<button type="button" data-chat-prompt="${escapeHtml(item)}">${escapeHtml(item)}</button>`).join('');
}

async function sendChat(message, triggerButton = null) {
  const text = message.trim();
  if (!text) return;
  appendChat('user', text);
  $('aiChatInput').value = '';
  const done = setButtonLoading(triggerButton, 'Šaljem...');
  try {
    const response = await request('/buyer-ai/chat', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(aiPayload(text)),
    });
    appendChat('ai', response.reply);
    renderQuickReplies(response.quick_replies || []);
    if (response.intent === 'search') {
      applyFiltersFromAI(response.filters);
      renderAIRecommended(response.products || []);
      await loadOffers();
    }
  } catch (err) {
    appendChat('ai', `Imam problem sa odgovorom: ${err.message}`);
  } finally {
    done();
  }
}

async function lookupReservation() {
  const code = $('reservationCodeInput').value.trim().toUpperCase();
  if (!code) return toast('Unesi kod rezervacije');
  const done = setButtonLoading($('lookupReservationBtn'), 'Proveravam...');
  try {
    const r = await request(`/reservations/code/${encodeURIComponent(code)}`);
    $('reservationLookupPanel').classList.remove('hidden');
    $('reservationLookupResult').innerHTML = `
      <div class="lookup-card-v21">
        <strong>${escapeHtml(r.product_name || 'Ponuda')}</strong>
        <p>Kod: <b>${escapeHtml(r.reservation_code)}</b></p>
        <p>Status: <span class="status">${escapeHtml(reservationStatusLabel(r.status))}</span></p>
        <p>Prodavac: ${escapeHtml(r.store_name || '-')}</p>
        <p>Količina: ${escapeHtml(r.quantity)}</p>
        <p>Ime: ${escapeHtml(r.customer_name)}</p>
        <div class="actions"><a class="link-button" href="/reservation?code=${encodeURIComponent(r.reservation_code)}">Otvori digitalnu kartu</a></div>
      </div>`;
  } catch (err) {
    toast(`Greška: ${err.message}`);
  } finally {
    done();
  }
}

$('offersGrid').addEventListener('click', handleReserveClick);
$('aiRecommendedProducts').addEventListener('click', handleReserveClick);
$('offersGrid').addEventListener('click', (event) => {
  const btn = event.target.closest('button[data-prompt]');
  if (btn) runAISearch(btn.dataset.prompt, btn);
});

window.addEventListener('reserve-offer-from-map', (event) => {
  const { id, max } = event.detail || {};
  if (!id) return;
  const product = lastLoadedOffers.find((p) => Number(p.id) === Number(id)) || lastAiProducts.find((p) => Number(p.id) === Number(id));
  openReservation(id, product?.name || 'ponudu', max);
});

$('cancelReservationBtn').addEventListener('click', () => $('reservationPanel').classList.add('hidden'));
$('reservationPanel').addEventListener('click', (event) => {
  if (event.target.id === 'reservationPanel') $('reservationPanel').classList.add('hidden');
});

$('reservationForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  const body = {
    product_id: Number(form.get('product_id')),
    customer_name: form.get('customer_name'),
    customer_phone: form.get('customer_phone'),
    customer_email: form.get('customer_email') || null,
    quantity: Number(form.get('quantity') || 1),
    note: form.get('note') || null,
  };
  const submitBtn = event.submitter || event.target.querySelector('button[type="submit"]');
  const done = setButtonLoading(submitBtn, 'Šaljem...');
  try {
    const reservation = await request('/reservations', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    });
    $('reservationResult').innerHTML = `
      <div class="reservation-success-v26">
        <span class="section-kicker">Rezervacija kreirana</span>
        <h3>Kod: ${escapeHtml(reservation.reservation_code)}</h3>
        <p>Status: <strong>${escapeHtml(reservationStatusLabel(reservation.status))}</strong> · ${escapeHtml(paymentStatusLabel(reservation.payment_status))}</p>
        ${paymentSummaryHtml(reservation)}
        <p>Za potvrdu rezervacije otvori stranicu plaćanja. Ako je podešen IPS račun, dobićeš stvaran IPS QR kod za m-banking.</p>
        <div class="actions">
          <button data-pay-code="${escapeHtml(reservation.reservation_code)}" data-pay-phone="${escapeHtml(body.customer_phone)}">Otvori plaćanje</button>
          <a class="link-button secondary-link" href="/reservation?code=${encodeURIComponent(reservation.reservation_code)}">Otvori digitalnu kartu</a>
          <a class="link-button secondary-link" href="/customer?phone=${encodeURIComponent(body.customer_phone)}">Moj nalog</a>
        </div>
      </div>`;
    $('reservationCodeInput').value = reservation.reservation_code;
    event.target.reset();
    await loadOffers();
    toast(`Rezervacija kreirana: ${reservation.reservation_code}`);
  } catch (err) {
    toast(`Greška: ${err.message}`);
  } finally {
    done();
  }
});

$('reservationForm').addEventListener('input', (event) => {
  if (event.target.name === 'quantity' || event.target.name === 'customer_phone') {
    clearTimeout(window.__paymentQuoteTimer);
    window.__paymentQuoteTimer = setTimeout(() => loadPaymentQuote().catch(() => {}), 350);
  }
});
$('reservationResult').addEventListener('click', (event) => {
  const btn = event.target.closest('button[data-pay-code]');
  if (!btn) return;
  payReservation(btn.dataset.payCode, btn.dataset.payPhone, btn);
});
$('lookupReservationBtn').addEventListener('click', lookupReservation);
$('reservationCodeInput').addEventListener('keydown', (event) => { if (event.key === 'Enter') lookupReservation(); });
$('applyFiltersBtn').addEventListener('click', () => loadOffers().catch((err) => toast(`Greška: ${err.message}`)));
$('useLocationBtn').addEventListener('click', useMyLocation);
$('setManualLocationBtn').addEventListener('click', setManualLocation);
$('clearFiltersBtn').addEventListener('click', () => {
  for (const id of ['qFilter','cityFilter','districtFilter','categoryFilter','statusFilter','minDiscountFilter','maxPriceFilter','expiringDaysFilter','radiusFilter']) $(id).value = '';
  $('sortFilter').value = 'updated';
  $('aiSearchInput').value = '';
  $('hasImageFilter').checked = false;
  renderAIRecommended([]);
  loadOffers().catch((err) => toast(`Greška: ${err.message}`));
});
for (const id of ['qFilter','cityFilter','districtFilter','categoryFilter','statusFilter','sortFilter','minDiscountFilter','maxPriceFilter','expiringDaysFilter','radiusFilter']) {
  $(id).addEventListener('change', () => loadOffers().catch((err) => toast(`Greška: ${err.message}`)));
}
$('qFilter').addEventListener('keydown', (event) => { if (event.key === 'Enter') loadOffers().catch((err) => toast(`Greška: ${err.message}`)); });
$('aiSearchBtn').addEventListener('click', () => runAISearch(null, $('aiSearchBtn')));
$('aiSearchInput').addEventListener('keydown', (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') runAISearch(null, $('aiSearchBtn'));
});
document.querySelectorAll('[data-prompt]').forEach((btn) => btn.addEventListener('click', () => {
  $('aiSearchInput').value = btn.dataset.prompt;
  runAISearch(btn.dataset.prompt, btn);
}));
$('aiChatForm').addEventListener('submit', (event) => {
  event.preventDefault();
  sendChat($('aiChatInput').value, event.submitter);
});
$('aiQuickReplies').addEventListener('click', (event) => {
  const btn = event.target.closest('[data-chat-prompt]');
  if (btn) sendChat(btn.dataset.chatPrompt, btn);
});
$('hasImageFilter').addEventListener('change', () => loadOffers().catch((err) => toast(`Greška: ${err.message}`)));
$('cityChips')?.addEventListener('click', (event) => {
  const btn = event.target.closest('[data-taxonomy-value]');
  if (!btn) return;
  $('cityFilter').value = btn.dataset.taxonomyValue;
  loadOffers().catch((err) => toast(`Greška: ${err.message}`));
});
$('categoryChips')?.addEventListener('click', (event) => {
  const btn = event.target.closest('[data-taxonomy-value]');
  if (!btn) return;
  $('categoryFilter').value = btn.dataset.taxonomyValue;
  loadOffers().catch((err) => toast(`Greška: ${err.message}`));
});

(async function init() {
  try {
    await loadFacets();
    await loadOffers();
    renderQuickReplies(['Šta ima blizu mene?', 'Pekara do 200 din', 'Kako radi rezervacija?', 'Šta znači pred istek?']);
  } catch (err) {
    toast(`Greška: ${err.message}`);
  }
})();
