const api = {
  stores: '/stores',
  seller: '/seller-api',
  uploadImage: '/uploads/image',
};

const $ = (id) => document.getElementById(id);
let stores = [];
let selectedStoreId = null;
let sellerPin = '';
let isLoggedIn = false;
let products = [];
let reservations = [];
let cameraStream = null;
let capturedImageBlob = null;
let capturedImagePreviewUrl = null;
let qrScannerStream = null;
let qrScannerTimer = null;
let qrDetector = null;

function toast(message) {
  const el = $('toast');
  el.textContent = message;
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 2800);
}

async function request(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}

function escapeHtml(str) {
  return String(str ?? '').replace(/[&<>'"]/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
}

function moneyPlain(amount, currency = 'RSD') {
  return `${Number(amount || 0).toLocaleString('sr-RS', { maximumFractionDigits: 2 })} ${currency}`;
}

function paymentStatusLabel(status) {
  const labels = { unpaid: 'Čeka plaćanje', payment_pending: 'Plaćanje pokrenuto', paid: 'Plaćeno online', pay_on_pickup: 'Plaćanje pri preuzimanju', refunded: 'Refundirano', failed: 'Neuspešno' };
  return labels[status] || status || '-';
}


async function uploadImageBlob(blob, filename = 'kamera-ponuda.jpg') {
  if (!blob) return null;
  const uploadData = new FormData();
  uploadData.append('file', blob, filename);
  const uploaded = await request(api.uploadImage, { method: 'POST', body: uploadData });
  return uploaded.image_url;
}

async function uploadImageFromForm(formData, fieldName = 'product_image') {
  if (capturedImageBlob) {
    return uploadImageBlob(capturedImageBlob, `kamera-ponuda-${Date.now()}.jpg`);
  }
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

function valueOrNull(value) {
  if (value === undefined || value === null || value === '') return null;
  return value;
}

function numberOrNull(value) {
  if (value === undefined || value === null || value === '') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function money(product) {
  const oldPrice = product.original_price ? `${product.original_price} ${product.currency}` : '';
  const newPrice = product.discounted_price ? `${product.discounted_price} ${product.currency}` : '';
  if (oldPrice && newPrice && oldPrice !== newPrice) return `${oldPrice} → ${newPrice}`;
  return newPrice || oldPrice || '-';
}

function selectedStore() {
  return stores.find((s) => Number(s.id) === Number(selectedStoreId));
}

function storageKeyForPin(storeId) {
  return `foodSaverSellerPin_${storeId}`;
}

function setProtectedVisible(visible) {
  document.querySelectorAll('[data-seller-protected]').forEach((el) => {
    el.classList.toggle('hidden', !visible);
  });
}

function fillStoreSelect() {
  const select = $('sellerStoreSelect');
  select.innerHTML = '';
  if (!stores.length) {
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = 'Nema prodavaca u bazi — dodaj ih u admin panelu';
    select.appendChild(opt);
    return;
  }
  for (const store of stores) {
    const opt = document.createElement('option');
    opt.value = store.id;
    opt.textContent = `${store.name}${store.city ? ` — ${store.city}` : ''}`;
    select.appendChild(opt);
  }
  if (selectedStoreId) select.value = selectedStoreId;
}

function setSelectedStore(storeId) {
  selectedStoreId = Number(storeId) || null;
  isLoggedIn = false;
  products = [];
  reservations = [];
  if (selectedStoreId) {
    localStorage.setItem('foodSaverSellerStoreId', String(selectedStoreId));
    const savedPin = localStorage.getItem(storageKeyForPin(selectedStoreId)) || '';
    $('sellerPinInput').value = savedPin;
    const url = new URL(window.location.href);
    url.searchParams.set('store_id', String(selectedStoreId));
    history.replaceState(null, '', url.toString());
  }
  renderSellerInfo();
  renderStoreLocationStatus();
  renderProducts();
  renderReservations();
}

function renderSellerInfo() {
  const store = selectedStore();
  if (!store) {
    $('sellerInfo').innerHTML = '<p class="help-text">Izaberi prodavca i unesi PIN da vidiš njegove artikle i rezervacije.</p>';
    setProtectedVisible(false);
    return;
  }
  $('sellerInfo').innerHTML = `
    <div class="seller-card-mini">
      <strong>${escapeHtml(store.name)}</strong>
      <span>${escapeHtml(store.city || '-')} ${store.address ? `• ${escapeHtml(store.address)}` : ''}</span>
      <span>${store.phone ? `Tel: ${escapeHtml(store.phone)}` : ''}</span>
      <span>${store.latitude && store.longitude ? `GPS: ${Number(store.latitude).toFixed(5)}, ${Number(store.longitude).toFixed(5)}` : 'GPS lokacija nije upisana'}</span>
      <span class="status">${isLoggedIn ? 'PIN potvrđen' : 'Potrebna prijava'}</span>
    </div>
  `;
  setProtectedVisible(isLoggedIn);
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

async function saveSellerLocation(lat, lng) {
  if (!selectedStoreId || !sellerPin || !isLoggedIn) return toast('Prvo potvrdi PIN');
  const latNum = Number(lat);
  const lngNum = Number(lng);
  if (!Number.isFinite(latNum) || !Number.isFinite(lngNum)) return toast('Unesi ispravne GPS koordinate');
  const updated = await request(`${api.seller}/location`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      store_id: selectedStoreId,
      pin: sellerPin,
      latitude: latNum,
      longitude: lngNum,
    }),
  });
  stores = stores.map((s) => Number(s.id) === Number(updated.id) ? updated : s);
  $('sellerManualLat').value = Number(updated.latitude).toFixed(6);
  $('sellerManualLng').value = Number(updated.longitude).toFixed(6);
  renderSellerInfo();
  renderStoreLocationStatus();
  toast('GPS lokacija prodavnice je sačuvana');
  return updated;
}

async function saveSellerManualLocation() {
  await saveSellerLocation($('sellerManualLat').value, $('sellerManualLng').value);
}

function renderStoreLocationStatus() {
  const el = $('sellerLocationResult');
  if (!el) return;
  const store = selectedStore();
  if (!store) {
    el.textContent = 'Izaberi prodavca.';
    return;
  }
  if (store.latitude && store.longitude) {
    if ($('sellerManualLat')) $('sellerManualLat').value = Number(store.latitude).toFixed(6);
    if ($('sellerManualLng')) $('sellerManualLng').value = Number(store.longitude).toFixed(6);
    el.textContent = `Lokacija prodavnice: ${Number(store.latitude).toFixed(6)}, ${Number(store.longitude).toFixed(6)}\nKupci sada mogu da vide ovu prodavnicu na mapi i u pretrazi u blizini.`;
  } else {
    el.textContent = 'GPS lokacija još nije upisana. Klikni dugme iznad dok si u prodavnici.';
  }
}

async function saveSellerGpsLocation() {
  if (!selectedStoreId || !sellerPin || !isLoggedIn) return toast('Prvo potvrdi PIN');
  if (!navigator.geolocation) {
    const msg = 'Browser ne podržava GPS lokaciju. Unesi Latitude/Longitude ručno.';
    $('sellerLocationResult').textContent = msg;
    return toast(msg);
  }
  if (!window.isSecureContext && !['localhost', '127.0.0.1', '::1'].includes(window.location.hostname)) {
    const msg = geolocationProblemMessage();
    $('sellerLocationResult').textContent = msg;
    return toast(msg);
  }
  toast('Tražim GPS lokaciju prodavnice...');
  $('sellerLocationResult').textContent = 'Tražim GPS lokaciju prodavnice...';
  navigator.geolocation.getCurrentPosition(async (pos) => {
    try {
      await saveSellerLocation(pos.coords.latitude, pos.coords.longitude);
    } catch (err) {
      toast(`Greška: ${err.message}`);
    }
  }, (err) => {
    const msg = geolocationProblemMessage(err);
    $('sellerLocationResult').textContent = msg;
    toast(msg);
  }, { enableHighAccuracy: true, timeout: 20000, maximumAge: 60000 });
}

function openStoreMap() {
  const store = selectedStore();
  if (!store || !store.latitude || !store.longitude) return toast('Prodavnica još nema GPS lokaciju');
  window.open(`https://www.openstreetmap.org/?mlat=${store.latitude}&mlon=${store.longitude}#map=18/${store.latitude}/${store.longitude}`, '_blank', 'noopener,noreferrer');
}

async function loadStores() {
  stores = await request(api.stores);
  const params = new URLSearchParams(window.location.search);
  const fromUrl = params.get('store_id');
  const fromStorage = localStorage.getItem('foodSaverSellerStoreId');
  selectedStoreId = Number(fromUrl || fromStorage || stores[0]?.id || 0) || null;
  fillStoreSelect();
  if (selectedStoreId) {
    $('sellerStoreSelect').value = selectedStoreId;
    $('sellerPinInput').value = localStorage.getItem(storageKeyForPin(selectedStoreId)) || '';
  }
  renderSellerInfo();
  renderStoreLocationStatus();
}

async function loginSeller() {
  selectedStoreId = Number($('sellerStoreSelect').value) || null;
  sellerPin = $('sellerPinInput').value.trim();
  if (!selectedStoreId) return toast('Izaberi prodavca');
  if (!sellerPin) return toast('Unesi PIN');
  await request(`${api.seller}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ store_id: selectedStoreId, pin: sellerPin }),
  });
  isLoggedIn = true;
  localStorage.setItem('foodSaverSellerStoreId', String(selectedStoreId));
  localStorage.setItem(storageKeyForPin(selectedStoreId), sellerPin);
  const url = new URL(window.location.href);
  url.searchParams.set('store_id', String(selectedStoreId));
  history.replaceState(null, '', url.toString());
  renderSellerInfo();
  renderStoreLocationStatus();
  await refreshSellerData();
  toast('Prodavac prijavljen');
}

function logoutSeller() {
  if (selectedStoreId) localStorage.removeItem(storageKeyForPin(selectedStoreId));
  sellerPin = '';
  $('sellerPinInput').value = '';
  isLoggedIn = false;
  products = [];
  reservations = [];
  renderSellerInfo();
  renderStoreLocationStatus();
  renderProducts();
  renderReservations();
  toast('Odjavljen prodavac');
}

function productUrl() {
  if (!selectedStoreId || !sellerPin || !isLoggedIn) return null;
  const params = new URLSearchParams({ store_id: String(selectedStoreId), pin: sellerPin });
  const status = $('sellerProductStatusFilter').value;
  if (status) params.set('status', status);
  return `${api.seller}/products?${params.toString()}`;
}

function reservationUrl() {
  if (!selectedStoreId || !sellerPin || !isLoggedIn) return null;
  const params = new URLSearchParams({ store_id: String(selectedStoreId), pin: sellerPin, limit: '200' });
  const status = $('sellerReservationStatusFilter').value;
  if (status) params.set('status', status);
  return `${api.seller}/reservations?${params.toString()}`;
}

async function loadProducts() {
  const url = productUrl();
  products = url ? await request(url) : [];
  renderProducts();
}

async function loadReservations() {
  const url = reservationUrl();
  reservations = url ? await request(url) : [];
  renderReservations();
}

function renderStats() {
  const activeProducts = products.filter((p) => !['hidden', 'expired'].includes(p.status)).length;
  const nearExpiry = products.filter((p) => p.status === 'near_expiry').length;
  const availableUnits = products.reduce((sum, p) => sum + (Number.isFinite(Number(p.available_quantity)) ? Number(p.available_quantity) : 0), 0);
  const pending = reservations.filter((r) => r.status === 'pending').length;
  const confirmed = reservations.filter((r) => r.status === 'confirmed').length;
  const pickedUp = reservations.filter((r) => r.status === 'picked_up').length;
  const cards = [
    [activeProducts, 'Aktivnih artikala'],
    [nearExpiry, 'Pred istek'],
    [availableUnits, 'Dostupnih komada'],
    [pending, 'Rezervacije čekaju'],
    [confirmed, 'Potvrđene'],
    [pickedUp, 'Preuzeto'],
  ];
  $('sellerStatsGrid').innerHTML = cards.map(([value, label]) => `
    <div class="stat-card"><strong>${value}</strong><span>${label}</span></div>
  `).join('');
}

function renderProducts() {
  const tbody = $('sellerProductsTable');
  if (!selectedStoreId || !isLoggedIn) {
    tbody.innerHTML = '<tr><td colspan="9" class="empty">Prvo izaberi prodavca i potvrdi PIN.</td></tr>';
    renderStats();
    return;
  }
  if (!products.length) {
    tbody.innerHTML = '<tr><td colspan="9" class="empty">Ovaj prodavac još nema artikle.</td></tr>';
    renderStats();
    return;
  }
  tbody.innerHTML = products.map((p) => `
    <tr>
      <td>${p.id}</td>
      <td>${imageThumb(p.image_url)}</td>
      <td>${escapeHtml(p.name)}</td>
      <td>${escapeHtml(p.category || '-')}</td>
      <td>${money(p)}</td>
      <td>${p.available_quantity ?? p.quantity ?? 'bez limita'}</td>
      <td>${p.expiry_date || '-'}</td>
      <td><span class="status">${escapeHtml(p.status)}</span></td>
      <td class="actions">
        <button data-status="seller_verified" data-id="${p.id}">Aktivno</button>
        <button data-status="near_expiry" data-id="${p.id}" class="secondary">Pred istek</button>
        <button data-status="hidden" data-id="${p.id}" class="danger">Sakrij</button>
      </td>
    </tr>
  `).join('');
  renderStats();
}

function renderReservations() {
  const tbody = $('sellerReservationsTable');
  if (!selectedStoreId || !isLoggedIn) {
    tbody.innerHTML = '<tr><td colspan="10" class="empty">Prvo izaberi prodavca i potvrdi PIN.</td></tr>';
    renderStats();
    return;
  }
  if (!reservations.length) {
    tbody.innerHTML = '<tr><td colspan="10" class="empty">Nema rezervacija za ovog prodavca.</td></tr>';
    renderStats();
    return;
  }
  tbody.innerHTML = reservations.map((r) => `
    <tr>
      <td><strong>${escapeHtml(r.reservation_code)}</strong></td>
      <td>${escapeHtml(r.product_name || `#${r.product_id}`)}</td>
      <td>${escapeHtml(r.customer_name)}</td>
      <td>${escapeHtml(r.customer_phone)}</td>
      <td>${r.quantity}</td>
      <td><span class="status">${escapeHtml(r.status)}</span></td>
      <td><span class="status">${escapeHtml(paymentStatusLabel(r.payment_status))}</span><br><strong>${moneyPlain(r.payable_amount, r.currency || 'RSD')}</strong></td>
      <td>${moneyPlain(r.seller_net_amount, r.currency || 'RSD')}<br><span class="note">posle 25% provizije</span></td>
      <td>${new Date(r.created_at).toLocaleString('sr-RS')}</td>
      <td class="actions">
        <button data-res-status="confirmed" data-id="${r.id}">Potvrdi</button>
        <button data-res-status="picked_up" data-id="${r.id}" class="secondary">Preuzeto</button>
        <button data-res-status="cancelled" data-id="${r.id}" class="danger">Otkaži</button>
      </td>
    </tr>
  `).join('');
  renderStats();
}


function reservationStatusLabel(status) {
  const labels = { pending: 'Čeka potvrdu', confirmed: 'Potvrđeno', picked_up: 'Preuzeto', cancelled: 'Otkazano', expired: 'Isteklo' };
  return labels[status] || status || '-';
}

async function updateSellerReservationStatus(reservationId, status) {
  await request(`${api.seller}/reservations/${reservationId}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ store_id: selectedStoreId, pin: sellerPin, status }),
  });
  await refreshSellerData();
  toast(`Status rezervacije: ${status}`);
}

async function sellerLookupReservationByCode() {
  if (!selectedStoreId || !sellerPin || !isLoggedIn) return toast('Prvo potvrdi PIN');
  const input = $('sellerReservationCodeInput');
  const code = (input?.value || '').trim().toUpperCase();
  if (!code) return toast('Unesi kod rezervacije');
  const result = $('sellerReservationCheckResult');
  result.innerHTML = 'Proveravam kod...';
  try {
    const r = await request(`${api.seller}/reservations/code/${encodeURIComponent(code)}?store_id=${selectedStoreId}&pin=${encodeURIComponent(sellerPin)}`);
    result.innerHTML = `
      <div class="seller-ticket-card-v26">
        <div>
          <span class="section-kicker">Kod</span>
          <h3>${escapeHtml(r.reservation_code)}</h3>
        </div>
        <div class="seller-ticket-grid-v26">
          <p><strong>Artikal:</strong> ${escapeHtml(r.product_name || `#${r.product_id}`)}</p>
          <p><strong>Kupac:</strong> ${escapeHtml(r.customer_name)}</p>
          <p><strong>Telefon:</strong> ${escapeHtml(r.customer_phone)}</p>
          <p><strong>Količina:</strong> ${escapeHtml(r.quantity)}</p>
          <p><strong>Status:</strong> <span class="status">${escapeHtml(reservationStatusLabel(r.status))}</span></p>
          <p><strong>Plaćanje:</strong> ${escapeHtml(paymentStatusLabel(r.payment_status))} · ${moneyPlain(r.payable_amount, r.currency || 'RSD')}</p>
          <p><strong>Neto prodavcu:</strong> ${moneyPlain(r.seller_net_amount, r.currency || 'RSD')}</p>
        </div>
        <div class="actions">
          <button data-check-res-status="confirmed" data-id="${r.id}">Potvrdi</button>
          <button data-check-res-status="picked_up" data-id="${r.id}" class="secondary">Označi preuzeto</button>
          <button data-check-res-status="cancelled" data-id="${r.id}" class="danger">Otkaži</button>
          <a class="link-button secondary-link" href="/reservation?code=${encodeURIComponent(r.reservation_code)}" target="_blank">Karta kupca</a>
        </div>
      </div>`;
  } catch (err) {
    result.innerHTML = `<div class="empty">${escapeHtml(err.message)}</div>`;
    toast(err.message);
  }
}


function qrStatus(message) {
  const el = $('qrScannerStatus');
  if (el) el.textContent = message;
}

function extractReservationCodeFromQr(text) {
  const raw = String(text || '').trim();
  if (!raw) return '';
  try {
    const url = new URL(raw);
    const direct = url.searchParams.get('code') || url.searchParams.get('reservation_code');
    if (direct) return direct.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 16);
    const matchPath = url.pathname.match(/([A-Z0-9]{6,16})(?:\.svg)?$/i);
    if (matchPath) return matchPath[1].toUpperCase();
  } catch (_) {}
  const match = raw.toUpperCase().match(/[A-Z0-9]{8,12}/);
  return match ? match[0] : '';
}

async function handleScannedQrText(text) {
  const code = extractReservationCodeFromQr(text);
  if (!code) {
    qrStatus(`QR je pročitan, ali ne liči na Sačuvaj Hranu kod: ${text}`);
    return;
  }
  $('sellerReservationCodeInput').value = code;
  qrStatus(`QR pročitan: ${code}. Proveravam rezervaciju...`);
  await stopQrScanner();
  await sellerLookupReservationByCode();
}

async function initQrDetector() {
  if ('BarcodeDetector' in window) {
    try {
      qrDetector = qrDetector || new BarcodeDetector({ formats: ['qr_code'] });
      return qrDetector;
    } catch (_) {}
  }
  return null;
}

async function scanQrFrame() {
  const video = $('qrScannerVideo');
  const detector = await initQrDetector();
  if (!video || !detector || !qrScannerStream) return;
  try {
    if (video.readyState >= 2) {
      const codes = await detector.detect(video);
      if (codes && codes.length) {
        await handleScannedQrText(codes[0].rawValue || codes[0].rawData || '');
        return;
      }
    }
  } catch (err) {
    qrStatus(`Greška skeniranja: ${err.message || err}`);
  }
  qrScannerTimer = setTimeout(scanQrFrame, 350);
}

async function startQrScanner() {
  if (!selectedStoreId || !sellerPin || !isLoggedIn) return toast('Prvo potvrdi PIN');
  const detector = await initQrDetector();
  if (!detector) {
    qrStatus('Ovaj browser ne podržava QR skener direktno. Učitaj sliku QR koda ili ručno unesi kod. Najbolje radi u Chrome/Edge na HTTPS ili localhost adresi.');
    return;
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    qrStatus('Kamera nije dostupna u ovom browseru. Probaj telefon, Chrome/Edge ili HTTPS adresu.');
    return;
  }
  try {
    qrScannerStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' } }, audio: false });
    const video = $('qrScannerVideo');
    video.srcObject = qrScannerStream;
    video.classList.remove('hidden');
    $('startQrScanBtn').disabled = true;
    $('stopQrScanBtn').disabled = false;
    qrStatus('Skener je uključen. Usmeri kameru ka QR kodu sa digitalne karte kupca.');
    await video.play();
    scanQrFrame();
  } catch (err) {
    qrStatus(geolocationProblemMessage(err).replace('GPS', 'Kamera'));
    toast('Kamera nije dozvoljena ili nije dostupna');
  }
}

async function stopQrScanner() {
  if (qrScannerTimer) clearTimeout(qrScannerTimer);
  qrScannerTimer = null;
  if (qrScannerStream) {
    qrScannerStream.getTracks().forEach((track) => track.stop());
    qrScannerStream = null;
  }
  const video = $('qrScannerVideo');
  if (video) {
    video.pause?.();
    video.srcObject = null;
    video.classList.add('hidden');
  }
  if ($('startQrScanBtn')) $('startQrScanBtn').disabled = false;
  if ($('stopQrScanBtn')) $('stopQrScanBtn').disabled = true;
}

async function scanQrImageFile(file) {
  if (!file) return;
  const detector = await initQrDetector();
  if (!detector) {
    qrStatus('Browser ne podržava čitanje QR slike. Ručno unesi kod koji piše na digitalnoj karti.');
    return;
  }
  try {
    const bitmap = await createImageBitmap(file);
    const codes = await detector.detect(bitmap);
    if (codes && codes.length) await handleScannedQrText(codes[0].rawValue || '');
    else qrStatus('Na slici nije pronađen QR kod. Probaj jasniju sliku ili ručni unos koda.');
  } catch (err) {
    qrStatus(`Ne mogu da pročitam QR sliku: ${err.message || err}`);
  }
}

async function refreshSellerData() {
  await Promise.all([loadProducts(), loadReservations()]);
  renderStats();
}


function setCameraButtons(active) {
  const snap = $('snapCameraBtn');
  if (snap) snap.disabled = !active;
}

function clearCapturedImage() {
  capturedImageBlob = null;
  if (capturedImagePreviewUrl) URL.revokeObjectURL(capturedImagePreviewUrl);
  capturedImagePreviewUrl = null;
  const previewWrap = $('cameraPreviewWrap');
  const preview = $('cameraPreview');
  if (preview) preview.removeAttribute('src');
  if (previewWrap) previewWrap.classList.add('hidden');
}

function stopCamera() {
  if (cameraStream) {
    cameraStream.getTracks().forEach((track) => track.stop());
    cameraStream = null;
  }
  const video = $('cameraVideo');
  if (video) {
    video.pause();
    video.srcObject = null;
    video.classList.add('hidden');
  }
  setCameraButtons(false);
}

async function startCamera() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    toast('Browser ne podržava kameru. Koristi polje “Slika ponude”.');
    return;
  }
  stopCamera();
  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: { ideal: 'environment' },
        width: { ideal: 1280 },
        height: { ideal: 720 },
      },
      audio: false,
    });
    const video = $('cameraVideo');
    video.srcObject = cameraStream;
    video.classList.remove('hidden');
    await video.play();
    setCameraButtons(true);
    toast('Kamera je uključena. Namesti proizvod i klikni “Slikaj proizvod”.');
  } catch (err) {
    toast(`Kamera nije dostupna: ${err.message}`);
  }
}

async function captureCameraImage() {
  const video = $('cameraVideo');
  if (!cameraStream || !video || !video.videoWidth) {
    toast('Prvo uključi kameru');
    return;
  }
  const canvas = $('cameraCanvas');
  const maxWidth = 1280;
  const ratio = video.videoHeight / video.videoWidth;
  const width = Math.min(video.videoWidth, maxWidth);
  const height = Math.round(width * ratio);
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(video, 0, 0, width, height);
  const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.84));
  if (!blob) {
    toast('Ne mogu da sačuvam sliku iz kamere');
    return;
  }
  clearCapturedImage();
  capturedImageBlob = blob;
  capturedImagePreviewUrl = URL.createObjectURL(blob);
  $('cameraPreview').src = capturedImagePreviewUrl;
  $('cameraPreviewWrap').classList.remove('hidden');
  const fileInput = $('sellerProductForm').product_image;
  if (fileInput) fileInput.value = '';
  stopCamera();
  toast('Slika je spremna. Proveri podatke i objavi ponudu.');
}

function applySellerTemplate(templateName, openCamera = false) {
  const form = $('sellerProductForm');
  const today = new Date().toISOString().slice(0, 10);
  const templates = {
    bakery: { name: 'Korpa peciva', category: 'pekara', original_price: 500, discounted_price: 250, quantity: 5, pickup_window: 'danas 18-21h', status: 'seller_verified', expiry_type: 'best_before' },
    lunch: { name: 'Dnevni meni višak', category: 'gotova jela', original_price: 800, discounted_price: 450, quantity: 4, pickup_window: 'danas 16-18h', status: 'seller_verified', expiry_type: 'use_by' },
    market: { name: 'Artikal kraćeg roka', category: 'market', original_price: 300, discounted_price: 180, quantity: 10, pickup_window: 'danas do 21h', status: 'near_expiry', expiry_type: 'best_before' },
  };
  const t = templates[templateName];
  if (!t) return;
  form.name.value = t.name;
  form.category.value = t.category;
  form.original_price.value = t.original_price;
  form.discounted_price.value = t.discounted_price;
  form.quantity.value = t.quantity;
  form.pickup_window.value = t.pickup_window;
  form.status.value = t.status;
  form.expiry_type.value = t.expiry_type;
  form.expiry_date.value = today;
  calculateDiscount();
  toast(openCamera ? 'Šablon popunjen. Kamera se otvara.' : 'Šablon popunjen');
  if (openCamera) startCamera();
}

function calculateDiscount() {
  const form = $('sellerProductForm');
  const oldPrice = numberOrNull(form.original_price.value);
  const newPrice = numberOrNull(form.discounted_price.value);
  if (oldPrice && newPrice && oldPrice > newPrice) {
    form.discount_percent.value = Math.round(((oldPrice - newPrice) / oldPrice) * 100);
  }
}


function dateToInputValue(date) {
  return date.toISOString().slice(0, 10);
}

function plusDays(days) {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return dateToInputValue(d);
}

function parseSerbianDate(text) {
  const lower = text.toLowerCase();
  if (/\b(danas|today)\b/.test(lower)) return plusDays(0);
  if (/\b(sutra|tomorrow)\b/.test(lower)) return plusDays(1);
  if (/\b(prekosutra)\b/.test(lower)) return plusDays(2);
  const m = lower.match(/\b(\d{1,2})[\.\/\-](\d{1,2})(?:[\.\/\-](\d{2,4}))?\b/);
  if (!m) return null;
  const day = Number(m[1]);
  const month = Number(m[2]);
  let year = m[3] ? Number(m[3]) : new Date().getFullYear();
  if (year < 100) year += 2000;
  if (day < 1 || day > 31 || month < 1 || month > 12) return null;
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
}

function detectCategory(text) {
  const lower = text.toLowerCase();
  const rules = [
    ['pekara', /(hleb|hljeb|peciv|burek|kifla|krofna|pogač|pogac|baget|sendvič|sendvic|proja)/],
    ['gotova jela', /(meni|ručak|rucak|obrok|porcija|pasta|pizza|pica|supa|čorba|corba|salata|grill|roštilj|rostilj)/],
    ['mlečni proizvodi', /(mleko|mlijeko|jogurt|sir|pavlaka|kajmak|kefir|mocarela|mozzarella)/],
    ['voće i povrće', /(jabuk|banan|paradajz|krastav|salat|krompir|luk|šargarep|sargarep|voće|voce|povrće|povrce)/],
    ['meso', /(meso|kobasic|šunka|sunka|pilet|junet|svinj|ćevap|cevap|pljeskavic)/],
    ['slatkiši', /(kolač|kolac|torta|čokolad|cokolad|mafin|cookie|keks|sladoled)/],
  ];
  for (const [category, regex] of rules) {
    if (regex.test(lower)) return category;
  }
  return 'market';
}

function extractPriceAfter(labelRegex, text) {
  const match = text.match(labelRegex);
  if (!match) return null;
  return numberOrNull(match[1].replace(',', '.'));
}

function inferNameFromCommand(text) {
  let cleaned = text
    .replace(/\b(stara|star[aoe]?\s*cena|redovna|nova|snižena|snizena|akcijska|cena|popust|kom|komada|porcija|količina|kolicina|rok|ističe|istice|preuzimanje|danas|sutra|prekosutra|do)\b/gi, ' ')
    .replace(/\b\d{1,2}[\.\/\-]\d{1,2}(?:[\.\/\-]\d{2,4})?\b/g, ' ')
    .replace(/\b\d{1,2}\s*[-–]\s*\d{1,2}h?\b/gi, ' ')
    .replace(/\b\d+(?:[,.]\d+)?\s*(din|rsd|kom|komada|porcija|kg|g|gr|l|ml|%)?\b/gi, ' ')
    .replace(/\s+/g, ' ')
    .trim();
  if (!cleaned) cleaned = 'Brza ponuda';
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}

function parseQuickCommand(rawText) {
  const text = String(rawText || '').trim();
  if (!text) throw new Error('Unesi kratak opis ponude');
  const lower = text.toLowerCase();

  let originalPrice = extractPriceAfter(/(?:stara|star[aoe]?\s*cena|redovna)\s*[:=]?\s*(\d+(?:[,.]\d+)?)/i, text);
  let discountedPrice = extractPriceAfter(/(?:nova|snižena|snizena|akcijska)\s*[:=]?\s*(\d+(?:[,.]\d+)?)/i, text);

  const allNumbers = [...text.matchAll(/\b\d+(?:[,.]\d+)?\b/g)].map((m) => ({ value: Number(m[0].replace(',', '.')), raw: m[0], index: m.index }));
  const numbersForPrice = allNumbers
    .filter((n) => !/\b(kom|komada|porcija|kg|g|gr|l|ml|%)\b/i.test(text.slice(n.index + n.raw.length, n.index + n.raw.length + 8)))
    .filter((n) => n.value >= 10);
  if (!originalPrice && numbersForPrice[0]) originalPrice = numbersForPrice[0].value;
  if (!discountedPrice && numbersForPrice[1]) discountedPrice = numbersForPrice[1].value;

  const quantityMatch = lower.match(/\b(\d+)\s*(kom|komada|porcija|porcije|pak|kutija)\b/);
  const quantity = quantityMatch ? Number(quantityMatch[1]) : 1;

  let pickupWindow = null;
  const interval = lower.match(/\b(\d{1,2})\s*[-–]\s*(\d{1,2})\s*h?\b/);
  if (interval) pickupWindow = `danas ${interval[1]}-${interval[2]}h`;
  const until = lower.match(/\bdo\s*(\d{1,2})\s*h\b/);
  if (!pickupWindow && until) pickupWindow = `danas do ${until[1]}h`;
  if (!pickupWindow) pickupWindow = 'danas 18-21h';

  const category = detectCategory(text);
  const expiryDate = parseSerbianDate(text);
  const nearExpiryWords = /(rok|ističe|istice|kratk|kraći|kraci|pred istek)/i.test(text);
  const expiryType = category === 'gotova jela' ? 'use_by' : 'best_before';

  return {
    name: inferNameFromCommand(text),
    category,
    original_price: originalPrice,
    discounted_price: discountedPrice,
    quantity,
    expiry_date: expiryDate,
    expiry_type: expiryDate ? expiryType : 'unknown',
    pickup_window: pickupWindow,
    status: nearExpiryWords || expiryDate ? 'near_expiry' : 'seller_verified',
  };
}

function fillFormFromParsed(parsed) {
  const form = $('sellerProductForm');
  if (parsed.name) form.name.value = parsed.name;
  if (parsed.category) form.category.value = parsed.category;
  if (parsed.original_price !== null && parsed.original_price !== undefined) form.original_price.value = parsed.original_price;
  if (parsed.discounted_price !== null && parsed.discounted_price !== undefined) form.discounted_price.value = parsed.discounted_price;
  if (parsed.quantity !== null && parsed.quantity !== undefined) form.quantity.value = parsed.quantity;
  if (parsed.expiry_date) form.expiry_date.value = parsed.expiry_date;
  if (parsed.expiry_type) form.expiry_type.value = parsed.expiry_type;
  if (parsed.pickup_window) form.pickup_window.value = parsed.pickup_window;
  if (parsed.status) form.status.value = parsed.status;
  calculateDiscount();
}

function handleQuickCommand() {
  try {
    const parsed = parseQuickCommand($('quickCommandText').value);
    fillFormFromParsed(parsed);
    $('quickCommandResult').textContent = JSON.stringify(parsed, null, 2);
    toast('Forma je popunjena iz kratke komande');
  } catch (err) {
    $('quickCommandResult').textContent = `Greška: ${err.message}`;
    toast(err.message);
  }
}

function startVoiceQuickCommand() {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) {
    toast('Ovaj browser ne podržava diktiranje. Upiši komandu ručno.');
    return;
  }
  const recognition = new Recognition();
  recognition.lang = 'sr-RS';
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;
  recognition.onstart = () => toast('Slušam... izgovori ponudu');
  recognition.onerror = (event) => toast(`Diktiranje nije uspelo: ${event.error || 'greška'}`);
  recognition.onresult = (event) => {
    const text = event.results?.[0]?.[0]?.transcript || '';
    $('quickCommandText').value = text;
    handleQuickCommand();
  };
  recognition.start();
}

function saveLastOfferDraft(body) {
  const draft = { ...body };
  delete draft.pin;
  delete draft.store_id;
  delete draft.image_url;
  delete draft.source_url;
  localStorage.setItem('foodSaverLastOfferDraft', JSON.stringify(draft));
}

function repeatLastOfferDraft() {
  const raw = localStorage.getItem('foodSaverLastOfferDraft');
  if (!raw) return toast('Još nema poslednje ponude za ponavljanje');
  const draft = JSON.parse(raw);
  fillFormFromParsed(draft);
  $('quickCommandResult').textContent = JSON.stringify(draft, null, 2);
  toast('Poslednja ponuda je popunjena. Dodaj novu sliku i objavi.');
}


$('parseQuickCommandBtn').addEventListener('click', handleQuickCommand);
$('voiceQuickCommandBtn').addEventListener('click', startVoiceQuickCommand);
$('repeatLastOfferBtn').addEventListener('click', repeatLastOfferDraft);

document.querySelectorAll('[data-quick-expiry]').forEach((btn) => {
  btn.addEventListener('click', () => {
    const form = $('sellerProductForm');
    form.expiry_date.value = btn.dataset.quickExpiry === 'tomorrow' ? plusDays(1) : plusDays(0);
    form.expiry_type.value = form.category.value === 'gotova jela' ? 'use_by' : 'best_before';
    form.status.value = 'near_expiry';
    toast(btn.dataset.quickExpiry === 'tomorrow' ? 'Rok podešen na sutra' : 'Rok podešen na danas');
  });
});

document.querySelectorAll('[data-quick-pickup]').forEach((btn) => {
  btn.addEventListener('click', () => {
    $('sellerProductForm').pickup_window.value = btn.dataset.quickPickup;
    toast(`Preuzimanje: ${btn.dataset.quickPickup}`);
  });
});

$('sellerProductForm').original_price.addEventListener('input', calculateDiscount);
$('sellerProductForm').discounted_price.addEventListener('input', calculateDiscount);

$('openCameraBtn').addEventListener('click', startCamera);
$('snapCameraBtn').addEventListener('click', captureCameraImage);
$('clearCapturedImageBtn').addEventListener('click', () => {
  clearCapturedImage();
  stopCamera();
  const fileInput = $('sellerProductForm').product_image;
  if (fileInput) fileInput.value = '';
  toast('Slika uklonjena');
});
$('sellerProductForm').product_image.addEventListener('change', () => {
  if ($('sellerProductForm').product_image.files.length) {
    clearCapturedImage();
    stopCamera();
    toast('Slika izabrana');
  }
});
window.addEventListener('beforeunload', stopCamera);

$('sellerStoreSelect').addEventListener('change', () => setSelectedStore($('sellerStoreSelect').value));
$('useStoreBtn').addEventListener('click', async () => loginSeller().catch((err) => toast(`Greška: ${err.message}`)));
$('logoutSellerBtn').addEventListener('click', logoutSeller);

$('refreshBtn').addEventListener('click', async () => {
  if (!isLoggedIn) return toast('Prvo potvrdi PIN');
  await refreshSellerData();
  toast('Podaci osveženi');
});

$('applyProductFilterBtn').addEventListener('click', loadProducts);
$('applyReservationFilterBtn').addEventListener('click', loadReservations);

$('copySellerLinkBtn').addEventListener('click', async () => {
  if (!selectedStoreId) return toast('Prvo izaberi prodavca');
  const url = `${window.location.origin}/seller?store_id=${selectedStoreId}`;
  await navigator.clipboard.writeText(url);
  toast('Link za prodavca kopiran. PIN pošalji odvojeno.');
});

$('sellerUseGpsBtn').addEventListener('click', () => saveSellerGpsLocation());
$('sellerSaveManualGpsBtn').addEventListener('click', () => saveSellerManualLocation().catch((err) => toast(`Greška: ${err.message}`)));
$('sellerOpenMapBtn').addEventListener('click', () => openStoreMap());

$('sellerProductForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!selectedStoreId || !sellerPin || !isLoggedIn) return toast('Prvo potvrdi PIN');
  const form = new FormData(event.target);
  const body = {
    store_id: selectedStoreId,
    pin: sellerPin,
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
    confidence_score: 0.98,
    status: form.get('status') || 'seller_verified',
  };
  saveLastOfferDraft(body);
  const created = await request(`${api.seller}/products`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  $('sellerResult').textContent = JSON.stringify(created, null, 2);
  event.target.reset();
  clearCapturedImage();
  stopCamera();
  await refreshSellerData();
  toast('Ponuda objavljena');
});

$('sellerProductsTable').addEventListener('click', async (event) => {
  const btn = event.target.closest('button[data-status]');
  if (!btn) return;
  await request(`${api.seller}/products/${btn.dataset.id}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ store_id: selectedStoreId, pin: sellerPin, status: btn.dataset.status }),
  });
  await refreshSellerData();
  toast(`Status artikla: ${btn.dataset.status}`);
});

$('sellerReservationsTable').addEventListener('click', async (event) => {
  const btn = event.target.closest('button[data-res-status]');
  if (!btn) return;
  await updateSellerReservationStatus(btn.dataset.id, btn.dataset.resStatus);
});

document.querySelectorAll('[data-template]').forEach((btn) => {
  btn.addEventListener('click', () => applySellerTemplate(btn.dataset.template, false));
});

document.querySelectorAll('[data-quick-camera]').forEach((btn) => {
  btn.addEventListener('click', () => applySellerTemplate(btn.dataset.quickCamera, true));
});


$('sellerLookupReservationBtn')?.addEventListener('click', sellerLookupReservationByCode);
$('sellerReservationCodeInput')?.addEventListener('keydown', (event) => { if (event.key === 'Enter') sellerLookupReservationByCode(); });
$('startQrScanBtn')?.addEventListener('click', startQrScanner);
$('stopQrScanBtn')?.addEventListener('click', stopQrScanner);
$('qrImageFileInput')?.addEventListener('change', (event) => scanQrImageFile(event.target.files?.[0]));
$('sellerReservationCheckResult')?.addEventListener('click', async (event) => {
  const btn = event.target.closest('button[data-check-res-status]');
  if (!btn) return;
  await updateSellerReservationStatus(btn.dataset.id, btn.dataset.checkResStatus);
  await sellerLookupReservationByCode();
});

async function init() {
  await loadStores();
  setProtectedVisible(false);
  renderStoreLocationStatus();
  renderProducts();
  renderReservations();
}

init().catch((err) => toast(`Greška: ${err.message}`));
