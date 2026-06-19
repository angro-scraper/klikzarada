const api = {
  stores: '/stores',
  products: '/products',
  sources: '/sources',
  seedSerbiaSources: '/sources/seed-serbia',
  seedBelgradeBakerySources: '/sources/seed-belgrade-bakeries',
  seedBelgradeBakeryProductDeepSources: '/sources/seed-belgrade-bakery-products-deep',
  seedBelgradeBakeryProductSuperDeepSources: '/sources/seed-belgrade-bakery-products-super-deep',
  seedBelgradeBakeryStores: '/stores/seed-belgrade-bakeries',
  crawl: '/crawl/run',
  crawlActive: '/crawl/run-active',
  crawlDebug: '/crawl/debug',
  stats: '/stats',
  jobs: '/crawl-jobs',
  reservations: '/reservations',
  expireOld: '/products/expire-old',
  uploadImage: '/uploads/image',
  qualityReport: '/database/quality-report',
  sourceReport: '/database/source-report',
  cleanupDuplicates: '/database/cleanup-duplicates',
  hideLowQuality: '/database/hide-low-quality',
  promoteDiscounts: '/database/promote-discounts',
  excelStatus: '/excel-database/status',
  excelSave: '/excel-database/save',
  excelImport: '/excel-database/import',
  excelUploadImport: '/excel-database/upload-import',
};

const $ = (id) => document.getElementById(id);
let stores = [];
let sources = [];
let products = [];
let reservations = [];
let activeButton = null;
let requestDepth = 0;

function nowTime() { return new Date().toLocaleTimeString('sr-RS', { hour: '2-digit', minute: '2-digit', second: '2-digit' }); }

function logActivity(message, type = 'info') {
  const el = $('activityLog');
  if (!el) return;
  const row = document.createElement('div');
  row.className = `log-row ${type}`;
  row.innerHTML = `<span>${nowTime()}</span><strong>${escapeHtml(message)}</strong>`;
  el.prepend(row);
  while (el.children.length > 10) el.removeChild(el.lastChild);
}

function setCrawlStatus(state, message, meta = '') {
  const el = $('crawlStatus');
  if (!el) return;
  el.className = `status-panel ${state}`;
  el.innerHTML = `<strong>${escapeHtml(message)}</strong>${meta ? `<span>${escapeHtml(meta)}</span>` : ''}`;
}

function setButtonLoading(button, loading) {
  if (!button) return;
  if (loading) {
    if (!button.dataset.originalText) button.dataset.originalText = button.textContent;
    button.classList.add('loading');
    button.disabled = true;
  } else {
    button.classList.remove('loading');
    button.disabled = false;
  }
}

document.addEventListener('click', (event) => {
  const btn = event.target.closest('button');
  if (!btn) return;
  activeButton = btn;
  btn.classList.add('pressed');
  setTimeout(() => btn.classList.remove('pressed'), 180);
});

document.addEventListener('submit', (event) => {
  activeButton = event.submitter || event.target.querySelector('button[type="submit"]');
});

function toast(message) {
  const el = $('toast');
  el.textContent = message;
  el.classList.add('show');
  logActivity(message);
  setTimeout(() => el.classList.remove('show'), 3200);
}

function valueOrNull(value) {
  if (value === undefined || value === null || value === '') return null;
  return value;
}

function numberOrNull(value) {
  if (value === undefined || value === null || value === '') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}


function geolocationProblemMessage(err) {
  if (!window.isSecureContext && !['localhost', '127.0.0.1', '::1'].includes(window.location.hostname)) {
    return 'GPS je blokiran jer stranica nije HTTPS. Otvori preko http://127.0.0.1:8000 ili kasnije preko HTTPS adrese.';
  }
  if (!err) return 'GPS nije dostupan u ovom browseru.';
  if (err.code === 1) return 'GPS dozvola je odbijena. U browseru otvori Site settings / Permissions i dozvoli Location.';
  if (err.code === 2) return 'Lokacija trenutno nije dostupna. Probaj Wi-Fi/GPS ili unesi koordinate ručno.';
  if (err.code === 3) return 'GPS je istekao pre nego što je našao lokaciju. Probaj ponovo ili unesi koordinate ručno.';
  return `GPS greška: ${err.message || 'nepoznata greška'}`;
}

async function request(url, options = {}) {
  const btn = activeButton;
  requestDepth += 1;
  setButtonLoading(btn, true);
  try {
    const res = await fetch(url, options);
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || `HTTP ${res.status}`);
    }
    return res.json();
  } finally {
    requestDepth = Math.max(0, requestDepth - 1);
    if (requestDepth === 0) {
      setButtonLoading(btn, false);
      activeButton = null;
    }
  }
}


async function uploadImageFromForm(formData, fieldName = 'product_image') {
  const file = formData.get(fieldName);
  if (!file || !file.name) return null;
  const uploadData = new FormData();
  uploadData.append('file', file);
  const uploaded = await request(api.uploadImage, { method: 'POST', body: uploadData });
  return uploaded.image_url;
}

function imageThumb(url) {
  return url ? `<img class="table-thumb" src="${escapeHtml(url)}" alt="Slika artikla" loading="lazy" />` : '<span class="muted">—</span>';
}

function fillSelect(select, items, placeholder) {
  select.innerHTML = '';
  const empty = document.createElement('option');
  empty.value = '';
  empty.textContent = placeholder;
  select.appendChild(empty);
  for (const item of items) {
    const opt = document.createElement('option');
    opt.value = item.id;
    opt.textContent = `${item.name}${item.city ? ` — ${item.city}` : ''}`;
    select.appendChild(opt);
  }
}

async function loadStats() {
  const stats = await request(api.stats);
  const labels = [
    ['products_total', 'Artikala ukupno'],
    ['stores_total', 'Prodavaca'],
    ['sources_total', 'Izvora'],
    ['near_expiry_total', 'Pred istek'],
    ['public_discount_total', 'Javne akcije'],
    ['needs_review_total', 'Čeka proveru'],
    ['reservations_pending_total', 'Rezervacije čekaju'],
    ['reservations_confirmed_total', 'Potvrđene rezervacije'],
    ['reservations_paid_total', 'Plaćeno online'],
    ['platform_fee_total', 'Naša provizija RSD'],
    ['seller_net_total', 'Neto prodavcima RSD'],
    ['expired_waiting_total', 'Isteklo, nije sakriveno'],
    ['average_discount_percent', 'Prosečan popust %'],
  ];
  $('statsGrid').innerHTML = labels.map(([key, label]) => `
    <div class="stat-card"><strong>${stats[key] ?? '-'}</strong><span>${label}</span></div>
  `).join('');
}

async function loadJobs() {
  const jobs = await request(api.jobs);
  $('jobsResult').textContent = jobs.length ? JSON.stringify(jobs.slice(0, 8), null, 2) : 'Još nema crawler poslova.';
}

async function loadStores() {
  stores = await request(api.stores);
  fillSelect($('storeSelect'), stores, 'Bez prodavca');
}

async function loadSources() {
  sources = await request(api.sources);
  fillSelect($('sourceSelect'), sources, 'Izaberi izvor');
}

function productUrl() {
  const params = new URLSearchParams();
  const city = $('cityFilter').value.trim();
  const category = $('categoryFilter').value.trim();
  const status = $('statusFilter').value;
  if (city) params.set('city', city);
  if (category) params.set('category', category);
  if (status) params.set('status', status);
  return `${api.products}${params.toString() ? `?${params.toString()}` : ''}`;
}

async function loadProducts() {
  products = await request(productUrl());
  renderProducts();
}

function reservationUrl() {
  const params = new URLSearchParams();
  const status = $('reservationStatusFilter').value;
  if (status) params.set('status', status);
  return `${api.reservations}${params.toString() ? `?${params.toString()}` : ''}`;
}

async function loadReservations() {
  reservations = await request(reservationUrl());
  renderReservations();
}

function money(product) {
  const oldPrice = product.original_price ? `${product.original_price} ${product.currency}` : '';
  const newPrice = product.discounted_price ? `${product.discounted_price} ${product.currency}` : '';
  if (oldPrice && newPrice && oldPrice !== newPrice) return `${oldPrice} → ${newPrice}`;
  return newPrice || oldPrice || '-';
}

function renderProducts() {
  const tbody = $('productsTable');
  tbody.innerHTML = '';
  for (const p of products) {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${p.id}</td>
      <td>${imageThumb(p.image_url)}</td>
      <td>${p.source_url ? `<a href="${p.source_url}" target="_blank" rel="noreferrer">${escapeHtml(p.name)}</a>` : escapeHtml(p.name)}</td>
      <td>${escapeHtml(p.category || '-')}</td>
      <td>${money(p)}</td>
      <td>${p.available_quantity ?? p.quantity ?? 'bez limita'}</td>
      <td>${p.discount_percent ?? '-'}</td>
      <td>${p.expiry_date || '-'}</td>
      <td><span class="status">${escapeHtml(p.status)}</span></td>
      <td>${Number(p.confidence_score ?? 0).toFixed(2)}</td>
      <td class="actions">
        <button class="secondary" data-status="seller_verified" data-id="${p.id}">Odobri</button>
        <button data-status="near_expiry" data-id="${p.id}">Pred istek</button>
        <button class="danger" data-status="hidden" data-id="${p.id}">Sakrij</button>
      </td>
    `;
    tbody.appendChild(tr);
  }
}

function renderReservations() {
  const tbody = $('reservationsTable');
  tbody.innerHTML = '';
  if (!reservations.length) {
    tbody.innerHTML = '<tr><td colspan="11" class="empty">Još nema rezervacija.</td></tr>';
    return;
  }
  for (const r of reservations) {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${r.id}</td>
      <td><strong>${escapeHtml(r.reservation_code)}</strong></td>
      <td>${escapeHtml(r.product_name || `#${r.product_id}`)}${r.store_name ? `<br><span class="note">${escapeHtml(r.store_name)}</span>` : ''}</td>
      <td>${escapeHtml(r.customer_name)}</td>
      <td>${escapeHtml(r.customer_phone)}</td>
      <td>${r.quantity}</td>
      <td><span class="status">${escapeHtml(r.status)}</span></td>
      <td><span class="status">${escapeHtml(paymentStatusLabel(r.payment_status))}</span><br><strong>${moneyPlain(r.payable_amount, r.currency || 'RSD')}</strong></td>
      <td>${moneyPlain(r.platform_fee_amount, r.currency || 'RSD')}<br><span class="note">${Number(r.platform_fee_percent || 25).toFixed(0)}%</span></td>
      <td>${new Date(r.created_at).toLocaleString('sr-RS')}</td>
      <td class="actions">
        <button data-res-status="confirmed" data-id="${r.id}">Potvrdi</button>
        <button class="secondary" data-res-status="picked_up" data-id="${r.id}">Preuzeto</button>
        <button class="danger" data-res-status="cancelled" data-id="${r.id}">Otkaži</button>
      </td>
    `;
    tbody.appendChild(tr);
  }
}

function escapeHtml(str) {
  return String(str).replace(/[&<>'"]/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
}

function moneyPlain(amount, currency = 'RSD') {
  return `${Number(amount || 0).toLocaleString('sr-RS', { maximumFractionDigits: 2 })} ${currency}`;
}

function paymentStatusLabel(status) {
  const labels = { unpaid: 'Čeka plaćanje', paid: 'Plaćeno', refunded: 'Refundirano', failed: 'Neuspešno' };
  return labels[status] || status || '-';
}

function showCrawlSummary(result, label = 'Crawler') {
  const total = Number(result.items_found || result.items_found_estimate || 0);
  const failed = Number(result.failed_sources || 0);
  const attempted = Number(result.sources_attempted || (result.results ? result.results.length : 1));
  if (total > 0) {
    setCrawlStatus('ok', `${label}: pronađeno ${total} proizvoda`, `Izvora provereno: ${attempted}. Duplikata: ${result.duplicates_skipped || 0}.`);
    return;
  }
  const firstError = result.error || (result.results || []).find(r => r.error)?.error || '';
  let hint = 'Nema proizvoda koji imaju i cenu i validnu sliku.';
  if (firstError) hint += ` Razlog: ${firstError.slice(0, 240)}`;
  if (failed) hint += ` Neuspelih izvora: ${failed}.`;
  setCrawlStatus('warn', `${label}: 0 proizvoda`, hint);
}

async function refreshAll() {
  await Promise.all([loadStores(), loadSources(), loadStats(), loadJobs()]);
  await Promise.all([loadProducts(), loadReservations()]);
}

$('refreshBtn').addEventListener('click', async () => {
  await refreshAll();
  toast('Podaci osveženi');
});

$('applyFiltersBtn').addEventListener('click', loadProducts);
$('applyReservationFiltersBtn').addEventListener('click', loadReservations);

$('expireOldBtn').addEventListener('click', async () => {
  const result = await request(api.expireOld, { method: 'POST' });
  await refreshAll();
  toast(`Sakriveno isteklih artikala: ${result.expired_count}`);
});

$('addDemoSourceBtn').addEventListener('click', async () => {
  const origin = window.location.origin;
  const data = {
    name: 'Demo katalog Beograd',
    url: `${origin}/admin-assets/sample-catalog.html`,
    city: 'Beograd',
    source_type: 'demo_html',
    crawl_frequency: 'manual',
    active: true,
  };
  await request(api.sources, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
  await loadSources();
  toast('Demo izvor dodat. Izaberi ga i pokreni crawler.');
});

$('seedSerbiaSourcesBtn').addEventListener('click', async () => {
  const result = await request(api.seedSerbiaSources, { method: 'POST' });
  await loadSources();
  await loadStats();
  $('crawlResult').textContent = JSON.stringify(result, null, 2);
  toast(`Dodati izvori za Srbiju: ${result.created} novih, ${result.existing} već postoji`);
});



$('seedBelgradeBakerySourcesBtn').addEventListener('click', async () => {
  const result = await request(api.seedBelgradeBakerySources, { method: 'POST' });
  await loadSources();
  await loadStats();
  $('crawlResult').textContent = JSON.stringify(result, null, 2);
  toast(`Dodati izvori za pekare BG: ${result.created} novih, ${result.existing} već postoji`);
});

$('seedBelgradeBakeryProductDeepSourcesBtn').addEventListener('click', async () => {
  const result = await request(api.seedBelgradeBakeryProductDeepSources, { method: 'POST' });
  await loadSources();
  await loadStats();
  $('crawlResult').textContent = JSON.stringify(result, null, 2);
  toast(`Dodati DUBOKI izvori za proizvode: ${result.created} novih, ${result.existing} već postoji`);
});



$('seedBelgradeBakeryProductSuperDeepSourcesBtn').addEventListener('click', async () => {
  const result = await request(api.seedBelgradeBakeryProductSuperDeepSources, { method: 'POST' });
  await loadSources();
  await loadStats();
  $('crawlResult').textContent = JSON.stringify(result, null, 2);
  toast(`Dodati SUPER DUBOKI izvori: ${result.created} novih, ${result.existing} već postoji`);
});

$('seedBelgradeBakeryStoresBtn').addEventListener('click', async () => {
  const result = await request(api.seedBelgradeBakeryStores, { method: 'POST' });
  await loadStores();
  await loadStats();
  $('storeResult').textContent = JSON.stringify(result, null, 2);
  toast(`Dodate pekare BG: ${result.created} novih, ${result.existing} već postoji`);
});

$('adminUseGpsBtn').addEventListener('click', () => {
  if (!navigator.geolocation) return toast('Browser ne podržava GPS lokaciju. Unesi Latitude/Longitude ručno.');
  if (!window.isSecureContext && !['localhost', '127.0.0.1', '::1'].includes(window.location.hostname)) return toast(geolocationProblemMessage());
  toast('Tražim GPS lokaciju...');
  navigator.geolocation.getCurrentPosition((pos) => {
    const form = $('storeForm');
    form.latitude.value = pos.coords.latitude.toFixed(6);
    form.longitude.value = pos.coords.longitude.toFixed(6);
    toast('GPS lokacija upisana u formu prodavca');
  }, (err) => {
    toast(geolocationProblemMessage(err));
  }, { enableHighAccuracy: true, timeout: 20000, maximumAge: 60000 });
});

$('storeForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.target).entries());
  data.verified = false;
  data.seller_pin = valueOrNull(data.seller_pin);
  data.latitude = numberOrNull(data.latitude);
  data.longitude = numberOrNull(data.longitude);
  const created = await request(api.stores, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
  $('storeResult').textContent = `Prodavac sačuvan. ID: ${created.id}\nPIN za prodavca: ${created.seller_pin}\nSeller link: ${window.location.origin}/seller?store_id=${created.id}`;
  event.target.reset();
  await refreshAll();
  toast(`Prodavac sačuvan. PIN: ${created.seller_pin}`);
});

$('productForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  const body = {
    store_id: numberOrNull(form.get('store_id')),
    name: form.get('name'),
    category: valueOrNull(form.get('category')),
    original_price: numberOrNull(form.get('original_price')),
    discounted_price: numberOrNull(form.get('discounted_price')),
    discount_percent: numberOrNull(form.get('discount_percent')),
    currency: 'RSD',
    expiry_date: valueOrNull(form.get('expiry_date')),
    expiry_type: form.get('expiry_type') || 'unknown',
    quantity: numberOrNull(form.get('quantity')),
    pickup_window: valueOrNull(form.get('pickup_window')),
    image_url: await uploadImageFromForm(form),
    source_url: null,
    confidence_score: 0.95,
    status: form.get('status') || 'candidate',
  };
  await request(api.products, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  event.target.reset();
  await refreshAll();
  toast('Artikal sačuvan');
});

$('sourceForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.target).entries());
  data.active = true;
  data.crawl_frequency = 'daily';
  await request(api.sources, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
  event.target.reset();
  await refreshAll();
  toast('Izvor sačuvan');
});

$('crawlSelectedBtn').addEventListener('click', async () => {
  try {
    const sourceId = Number($('sourceSelect').value);
    if (!sourceId) return toast('Izaberi izvor');
    setCrawlStatus('running', 'Crawler radi za izabrani izvor...', 'Sačekaj da se dugme vrati iz loading stanja.');
    toast('Crawler radi za izabrani izvor...');
    const result = await request(api.crawl, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ source_id: sourceId }) });
    $('crawlResult').textContent = JSON.stringify(result, null, 2);
    showCrawlSummary(result, 'Izabrani izvor');
    await refreshAll();
    toast(result.status === 'failed' ? `Crawler nije našao artikle: ${result.error || 'pogledaj rezultat'}` : `Crawler završen: ${result.items_found} novih artikala`);
  } catch (err) {
    $('crawlResult').textContent = err.message;
    setCrawlStatus('error', 'Crawler greška', err.message);
    toast(`Crawler greška: ${err.message}`);
  }
});

$('crawlActiveBtn').addEventListener('click', async () => {
  try {
    const limit = Number($('batchCrawlLimit').value || 10);
    const sourceType = $('batchSourceType').value;
    const params = new URLSearchParams();
    params.set('limit', String(limit));
    if (sourceType) params.set('source_type', sourceType);
    setCrawlStatus('running', 'Batch crawler radi...', 'Ne zatvaraj prozor dok se rezultat ne prikaže.');
    toast('Batch crawler radi... može potrajati.');
    const result = await request(`${api.crawlActive}?${params.toString()}`, { method: 'POST' });
    $('crawlResult').textContent = JSON.stringify(result, null, 2);
    showCrawlSummary(result, 'Batch');
    await refreshAll();
    toast(`Batch završen: ${result.items_found} novih artikala, greške: ${result.failed_sources}`);
  } catch (err) {
    $('crawlResult').textContent = err.message;
    setCrawlStatus('error', 'Batch crawler greška', err.message);
    toast(`Batch crawler greška: ${err.message}`);
  }
});

$('crawlDeepBakeryBtn').addEventListener('click', async () => {
  try {
    const limit = Number($('batchCrawlLimit').value || 5);
    const params = new URLSearchParams();
    params.set('limit', String(limit));
    params.set('source_type', 'bakery_product_super_deep');
    params.set('deep_products', 'true');
    params.set('require_image', 'true');
    params.set('bakery_only', 'true');
    params.set('max_pages', '120');
    params.set('max_items', '1800');
    params.set('render_js', 'true');
    setCrawlStatus('running', 'SUPER duboko + Browser/JS skeniranje radi...', 'Traži naziv + cenu + validnu sliku. Ovo može trajati duže.');
    toast('SUPER duboko pretraživanje radi... browser + sitemap + JSON + slika/cena.');
    const result = await request(`${api.crawlActive}?${params.toString()}`, { method: 'POST' });
    $('crawlResult').textContent = JSON.stringify(result, null, 2);
    showCrawlSummary(result, 'Deep crawler');
    await refreshAll();
    toast(`Deep crawler završen: ${result.items_found} novih proizvoda, greške: ${result.failed_sources}`);
  } catch (err) {
    $('crawlResult').textContent = err.message;
    setCrawlStatus('error', 'Deep crawler greška', err.message);
    toast(`Deep crawler greška: ${err.message}`);
  }
});

$('crawlUrlForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    const data = Object.fromEntries(new FormData(event.target).entries());
    toast('Crawler radi za direktan URL...');
    const result = await request(api.crawl, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) });
    $('crawlResult').textContent = JSON.stringify(result, null, 2);
    await refreshAll();
    toast(result.status === 'failed' ? `Crawler nije našao artikle: ${result.error || 'pogledaj rezultat'}` : `Crawler završen: ${result.items_found} novih artikala`);
  } catch (err) {
    $('crawlResult').textContent = err.message;
    setCrawlStatus('error', 'Crawler greška', err.message);
    toast(`Crawler greška: ${err.message}`);
  }
});

$('crawlDebugDeepBtn').addEventListener('click', async () => {
  try {
    const form = $('crawlDebugForm');
    const data = Object.fromEntries(new FormData(form).entries());
    if (!data.url) return toast('Unesi URL za deep proveru');
    const params = new URLSearchParams({ url: data.url, discover: 'true', max_pages: '120', deep_products: 'true', require_image: 'true', bakery_only: 'true', render_js: 'true' });
    setCrawlStatus('running', 'Deep debug provera radi...', 'Browser/JS režim je uključen.');
    toast('Deep provera radi: tražim samo slika+cena...');
    const result = await request(`${api.crawlDebug}?${params.toString()}`);
    $('crawlResult').textContent = JSON.stringify(result, null, 2);
    showCrawlSummary(result, 'Deep provera');
    toast(`Deep provera završena: ${result.items_found_estimate || 0} proizvoda sa slikom i cenom`);
  } catch (err) {
    $('crawlResult').textContent = err.message;
    setCrawlStatus('error', 'Deep debug greška', err.message);
    toast(`Deep debug greška: ${err.message}`);
  }
});

$('crawlDebugForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  try {
    const data = Object.fromEntries(new FormData(event.target).entries());
    const params = new URLSearchParams({ url: data.url, discover: 'true', max_pages: '8' });
    setCrawlStatus('running', 'Proveravam URL bez upisa...', 'Ovo ne upisuje proizvode u bazu.');
    toast('Proveravam URL bez upisa u bazu...');
    const result = await request(`${api.crawlDebug}?${params.toString()}`);
    $('crawlResult').textContent = JSON.stringify(result, null, 2);
    toast(`Provera završena: procena ${result.items_found_estimate || 0} artikala`);
  } catch (err) {
    $('crawlResult').textContent = err.message;
    setCrawlStatus('error', 'Debug greška', err.message);
    toast(`Debug greška: ${err.message}`);
  }
});

$('productsTable').addEventListener('click', async (event) => {
  const btn = event.target.closest('button[data-status]');
  if (!btn) return;
  const id = btn.dataset.id;
  const status = btn.dataset.status;
  await request(`${api.products}/${id}/status?status=${encodeURIComponent(status)}`, { method: 'PATCH' });
  await refreshAll();
  toast(`Status promenjen u ${status}`);
});

$('reservationsTable').addEventListener('click', async (event) => {
  const btn = event.target.closest('button[data-res-status]');
  if (!btn) return;
  const id = btn.dataset.id;
  const status = btn.dataset.resStatus;
  await request(`${api.reservations}/${id}/status?status=${encodeURIComponent(status)}`, { method: 'PATCH' });
  await refreshAll();
  toast(`Rezervacija promenjena u ${status}`);
});



function databaseResult(data) {
  $('databaseToolsResult').textContent = JSON.stringify(data, null, 2);
}



$('excelStatusBtn').addEventListener('click', async () => {
  const result = await request(api.excelStatus);
  databaseResult(result);
  toast(result.exists ? `Excel baza postoji: ${result.filename}` : 'Excel baza još nije napravljena');
});

$('excelSaveBtn').addEventListener('click', async () => {
  const result = await request(api.excelSave, { method: 'POST' });
  databaseResult(result);
  toast('Baza je snimljena u Excel');
});

$('excelImportBtn').addEventListener('click', async () => {
  const input = $('excelImportFile');
  if (input.files && input.files.length) {
    const form = new FormData();
    form.append('file', input.files[0]);
    const result = await request(api.excelUploadImport, { method: 'POST', body: form });
    databaseResult(result);
    await refreshAll();
    toast('Excel fajl je importovan u aplikaciju');
    input.value = '';
    return;
  }
  if (!confirm('Importovati trenutno sačuvani backend/data/food_saver_database.xlsx u aplikaciju?')) return;
  const result = await request(api.excelImport, { method: 'POST' });
  databaseResult(result);
  await refreshAll();
  toast('Sačuvani Excel je importovan u aplikaciju');
});

$('qualityReportBtn').addEventListener('click', async () => {
  const result = await request(api.qualityReport);
  databaseResult(result);
  toast('Izveštaj kvaliteta učitan');
});

$('sourceReportBtn').addEventListener('click', async () => {
  const result = await request(api.sourceReport);
  databaseResult(result);
  toast('Izveštaj izvora učitan');
});

$('duplicatesDryRunBtn').addEventListener('click', async () => {
  const result = await request(`${api.cleanupDuplicates}?dry_run=true`, { method: 'POST' });
  databaseResult(result);
  toast(`Provera duplikata: ${result.products_to_hide} za sakrivanje`);
});

$('duplicatesApplyBtn').addEventListener('click', async () => {
  if (!confirm('Sakriti duplikate? Prvo je najbolje uraditi dry run.')) return;
  const result = await request(`${api.cleanupDuplicates}?dry_run=false`, { method: 'POST' });
  databaseResult(result);
  await refreshAll();
  toast(`Duplikati sakriveni: ${result.products_to_hide}`);
});

$('lowQualityDryRunBtn').addEventListener('click', async () => {
  const minConfidence = Number($('qualityMinConfidence').value || 0.45);
  const result = await request(`${api.hideLowQuality}?dry_run=true&min_confidence=${encodeURIComponent(minConfidence)}`, { method: 'POST' });
  databaseResult(result);
  toast(`Slabi kandidati za sakrivanje: ${result.products_to_hide}`);
});

$('lowQualityApplyBtn').addEventListener('click', async () => {
  if (!confirm('Sakriti slabe kandidate? Prvo je najbolje uraditi dry run.')) return;
  const minConfidence = Number($('qualityMinConfidence').value || 0.45);
  const result = await request(`${api.hideLowQuality}?dry_run=false&min_confidence=${encodeURIComponent(minConfidence)}`, { method: 'POST' });
  databaseResult(result);
  await refreshAll();
  toast(`Slabi kandidati sakriveni: ${result.products_to_hide}`);
});

$('promoteDiscountsBtn').addEventListener('click', async () => {
  const minConfidence = Number($('qualityMinConfidence').value || 0.55);
  const result = await request(`${api.promoteDiscounts}?min_confidence=${encodeURIComponent(minConfidence)}`, { method: 'POST' });
  databaseResult(result);
  await refreshAll();
  toast(`Promovisano javnih akcija: ${result.promoted_to_public_discount}`);
});

refreshAll().catch((err) => toast(`Greška: ${err.message}`));
