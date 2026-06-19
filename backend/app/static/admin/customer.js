const $ = (id) => document.getElementById(id);

let pendingPhone = '';
let currentToken = '';

function toast(message) {
  const el = $('toast');
  if (!el) return;
  el.textContent = message;
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 3200);
}
function escapeHtml(str) {
  return String(str ?? '').replace(/[&<>'"]/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
}
function money(value, currency='RSD') {
  return `${Number(value || 0).toLocaleString('sr-RS', { maximumFractionDigits: 2 })} ${currency}`;
}
function statusLabel(status) {
  return ({pending:'Čeka potvrdu', confirmed:'Potvrđeno', picked_up:'Preuzeto', cancelled:'Otkazano', expired:'Isteklo'}[status] || status || '-');
}
function paymentLabel(status) {
  return ({unpaid:'Nije plaćeno', payment_pending:'Čeka potvrdu uplate', paid:'Plaćeno', refunded:'Refundirano', failed:'Neuspešno'}[status] || status || '-');
}
function setButtonLoading(button, loadingText = 'Radim...') {
  if (!button) return () => {};
  const original = button.innerHTML;
  button.disabled = true;
  button.classList.add('is-loading');
  button.innerHTML = `<span class="spinner-dot"></span>${loadingText}`;
  return () => { button.disabled = false; button.classList.remove('is-loading'); button.innerHTML = original; };
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
function jsonPost(url, body) {
  return request(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
}
function storageKey(phone) {
  const clean = String(phone || '').replace(/\D/g, '');
  return `foodSaverCustomerToken:${clean}`;
}
function setStep(step) {
  $('phoneStep')?.classList.toggle('active', step === 'phone');
  $('otpStep')?.classList.toggle('active', step === 'otp');
}
function saveToken(phone, token) {
  localStorage.setItem(storageKey(phone), token);
}
function readToken(phone) {
  return localStorage.getItem(storageKey(phone)) || '';
}

async function requestOtp(phone, submitButton=null) {
  const clean = String(phone || '').trim();
  if (!clean) return toast('Unesi telefon');
  const done = setButtonLoading(submitButton, 'Šaljem kod...');
  try {
    const data = await jsonPost('/customers/otp/request', { phone: clean });
    pendingPhone = clean;
    const devCode = data.dev_otp ? `<strong class="dev-code-v32">${escapeHtml(data.dev_otp)}</strong>` : '<strong>poslat SMS-om</strong>';
    $('otpInfo').innerHTML = `Kod za ${escapeHtml(data.phone_masked)} je ${devCode}.`;
    setStep('otp');
    $('customerOtpInput').focus();
    toast('Kod je generisan');
  } catch (err) {
    toast(`Greška: ${err.message}`);
  } finally {
    done();
  }
}

async function verifyOtp(button=null) {
  const code = $('customerOtpInput').value.trim();
  if (!pendingPhone) return toast('Prvo unesi telefon');
  if (!code) return toast('Unesi kod');
  const done = setButtonLoading(button, 'Proveravam...');
  try {
    const data = await jsonPost('/customers/otp/verify', { phone: pendingPhone, code });
    currentToken = data.token;
    saveToken(pendingPhone, currentToken);
    toast('Telefon je potvrđen');
    await loadCustomer(pendingPhone, null, currentToken);
  } catch (err) {
    toast(`Greška: ${err.message}`);
  } finally {
    done();
  }
}

function renderStats(data) {
  const items = [
    ['Rezervacije', data.total_reservations, 'ukupno'],
    ['Aktivne', data.active_reservations, 'čekaju/preuzimanje'],
    ['Preuzeto', data.picked_up_count, 'loyalty osnova'],
    ['Plaćeno', money(data.total_paid_amount, data.currency), 'online promet'],
    ['Ušteda', money(data.total_loyalty_saved, data.currency), 'loyalty popust'],
    ['Popust', `${Number(data.loyalty.current_discount_percent || 0).toFixed(0)}%`, 'trenutni nivo'],
  ];
  $('customerStats').innerHTML = items.map(([label, value, sub]) => `<div class="stat-card"><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)} · ${escapeHtml(sub)}</span></div>`).join('');
}

function renderLoyalty(data) {
  const l = data.loyalty || {};
  const current = Number(l.current_discount_percent || 0);
  $('loyaltyTitle').textContent = `Tvoj popust: ${current.toFixed(0)}%`;
  $('loyaltyText').textContent = l.max_reached
    ? 'Dostigao/la si maksimalni loyalty nivo od 5%. Taj popust se automatski primenjuje pri sledećoj online rezervaciji.'
    : `Još ${l.remaining_pickups} uspešno preuzetih rezervacija do nivoa ${Number(l.next_discount_percent || 0).toFixed(0)}%.`;
  $('loyaltyMeter').style.width = `${Math.min((current / 5) * 100, 100)}%`;

  const cats = (data.top_categories || []).map(x => `<span>${escapeHtml(x.name)} · ${x.count}</span>`).join('');
  const stores = (data.top_stores || []).map(x => `<span>${escapeHtml(x.name)} · ${x.count}</span>`).join('');
  $('customerInsights').innerHTML = `
    <div class="insight-card-v31"><strong>Omiljene kategorije</strong><div>${cats || '<span>Još nema podataka</span>'}</div></div>
    <div class="insight-card-v31"><strong>Najčešći prodavci</strong><div>${stores || '<span>Još nema podataka</span>'}</div></div>`;
}

function reservationCard(r) {
  const date = r.created_at ? new Date(r.created_at).toLocaleString('sr-RS') : '-';
  const payAction = r.payment_status !== 'paid' && r.status !== 'cancelled'
    ? `<a class="link-button" href="${escapeHtml(r.checkout_url)}">Plati / QR</a>` : '';
  return `<article class="customer-reservation-card-v31">
    <div>
      <span class="section-kicker">${escapeHtml(r.reservation_code)}</span>
      <h3>${escapeHtml(r.product_name || 'Ponuda')}</h3>
      <p><strong>${escapeHtml(r.store_name || 'Prodavac')}</strong>${r.store_city ? ` · ${escapeHtml(r.store_city)}` : ''}</p>
      ${r.store_address ? `<p class="help-text">${escapeHtml(r.store_address)}</p>` : ''}
      <p class="help-text">Kreirano: ${escapeHtml(date)} · Količina: ${escapeHtml(r.quantity)}</p>
    </div>
    <div class="customer-reservation-side-v31">
      <span class="status">${escapeHtml(statusLabel(r.status))}</span>
      <span class="status">${escapeHtml(paymentLabel(r.payment_status))}</span>
      <strong>${money(r.payable_amount, r.currency)}</strong>
      ${Number(r.loyalty_discount_amount || 0) > 0 ? `<small>Ušteda: ${money(r.loyalty_discount_amount, r.currency)}</small>` : ''}
      <div class="actions"><a class="link-button secondary-link" href="${escapeHtml(r.ticket_url)}">Digitalna karta</a>${payAction}</div>
    </div>
  </article>`;
}

function renderReservations(data) {
  $('customerReservationCount').textContent = `${data.reservations.length} prikazano`;
  $('customerReservations').innerHTML = data.reservations.length
    ? data.reservations.map(reservationCard).join('')
    : `<div class="empty-state-v21"><h3>Nema rezervacija za ovaj telefon</h3><p>Rezerviši prvu ponudu i ovde će se pojaviti istorija.</p><a class="link-button" href="/offers">Pogledaj ponude</a></div>`;
}

async function loadCustomer(phone, submitButton=null, token=null) {
  const clean = String(phone || '').trim();
  const authToken = token || currentToken || readToken(clean);
  if (!clean) return toast('Unesi telefon');
  if (!authToken) {
    pendingPhone = clean;
    return requestOtp(clean, submitButton);
  }
  const done = setButtonLoading(submitButton, 'Učitavam...');
  try {
    const data = await request(`/customers/profile-secure?phone=${encodeURIComponent(clean)}&token=${encodeURIComponent(authToken)}`);
    currentToken = authToken;
    $('customerEmpty').classList.add('hidden');
    $('customerDashboard').classList.remove('hidden');
    $('customerTitle').textContent = `Nalog ${data.phone_masked}`;
    $('customerPrivacy').textContent = data.privacy_note || '';
    renderStats(data);
    renderLoyalty(data);
    renderReservations(data);
    const url = new URL(location.href);
    url.searchParams.set('phone', clean);
    history.replaceState({}, '', url.toString());
    setStep('phone');
    toast('Nalog je učitan');
  } catch (err) {
    localStorage.removeItem(storageKey(clean));
    currentToken = '';
    pendingPhone = clean;
    setStep('otp');
    $('otpInfo').innerHTML = 'Sesija je istekla. Zatraži novi kod za potvrdu telefona.';
    toast(`Potrebna je potvrda: ${err.message}`);
  } finally {
    done();
  }
}

function bindCustomerActions() {
  $('customerLookupForm')?.addEventListener('submit', (event) => {
    event.preventDefault();
    const phone = $('customerPhoneInput').value;
    const existing = readToken(phone);
    if (existing) loadCustomer(phone, event.submitter, existing);
    else requestOtp(phone, event.submitter);
  });
  $('verifyOtpBtn')?.addEventListener('click', (event) => verifyOtp(event.currentTarget));
  $('resendOtpBtn')?.addEventListener('click', (event) => requestOtp(pendingPhone || $('customerPhoneInput').value, event.currentTarget));
  $('customerOtpInput')?.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') { event.preventDefault(); verifyOtp($('verifyOtpBtn')); }
  });
}

(function init() {
  bindCustomerActions();
  const params = new URLSearchParams(location.search);
  if (params.get('phone')) {
    $('customerPhoneInput').value = params.get('phone');
    const token = readToken(params.get('phone'));
    if (token) loadCustomer(params.get('phone'), null, token).catch(() => {});
  }
})();
