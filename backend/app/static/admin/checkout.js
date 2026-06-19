const $ = (id) => document.getElementById(id);
let reservation = null;
let checkout = null;

const reservationStatusLabels = { pending: 'Čeka potvrdu', confirmed: 'Potvrđeno', picked_up: 'Preuzeto', cancelled: 'Otkazano', expired: 'Isteklo' };
const paymentStatusLabels = { unpaid: 'Čeka plaćanje', payment_pending: 'Plaćanje pokrenuto', pay_on_pickup: 'Plaćanje pri preuzimanju', paid: 'Plaćeno', refunded: 'Refundirano', failed: 'Neuspešno' };

function toast(message) {
  const el = $('toast');
  el.textContent = message;
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 3200);
}
function escapeHtml(str) { return String(str ?? '').replace(/[&<>'"]/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c])); }
function money(amount, currency='RSD') { return `${Number(amount || 0).toLocaleString('sr-RS', { maximumFractionDigits: 2 })} ${currency}`; }
function rLabel(s) { return reservationStatusLabels[s] || s || '-'; }
function pLabel(s) { return paymentStatusLabels[s] || s || '-'; }

async function request(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) {
    let text = await res.text();
    try { text = JSON.parse(text).detail || text; } catch (_) {}
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}
function setButtonLoading(btn, text) {
  if (!btn) return () => {};
  const old = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<span class="spinner"></span>${escapeHtml(text)}`;
  return () => { btn.disabled = false; btn.innerHTML = old; };
}

function renderQr(box, url, alt) {
  box.innerHTML = url ? `<img class="real-qr-v29" src="${escapeHtml(url)}" alt="${escapeHtml(alt)}" />` : '<div class="qr-missing-v29">QR nije dostupan</div>';
}

async function loadCheckout() {
  const code = $('checkoutCodeInput').value.trim().toUpperCase();
  if (!code) return toast('Unesi kod rezervacije');
  const done = setButtonLoading($('loadCheckoutBtn'), 'Učitavam...');
  try {
    reservation = await request(`/reservations/code/${encodeURIComponent(code)}`);
    checkout = await request(`/payments/reservations/${encodeURIComponent(code)}/checkout`);
    renderCheckout();
    history.replaceState({}, '', `/checkout?code=${encodeURIComponent(code)}`);
  } catch (err) {
    $('checkoutPanel').classList.add('hidden');
    $('checkoutMessage').textContent = `Greška: ${err.message}`;
    toast(err.message);
  } finally { done(); }
}

function renderCheckout() {
  $('checkoutPanel').classList.remove('hidden');
  $('checkoutCode').textContent = reservation.reservation_code;
  $('checkoutProduct').textContent = reservation.product_name || `Artikal #${reservation.product_id}`;
  $('checkoutAmount').textContent = money(checkout.amount, checkout.currency);
  $('checkoutStore').textContent = reservation.store_name || '-';
  $('checkoutReservationStatus').textContent = rLabel(reservation.status);
  $('checkoutPaymentStatus').textContent = pLabel(reservation.payment_status);
  $('checkoutProvider').textContent = `${checkout.provider} · ${checkout.method}`;
  $('paymentInstructions').textContent = checkout.instructions || '-';
  $('openReservationLink').href = checkout.reservation_url;
  $('checkoutMessage').innerHTML = `Plaćanje je učitano za rezervaciju <strong>${escapeHtml(reservation.reservation_code)}</strong>.`;

  renderQr($('ticketQrBox'), checkout.reservation_qr_url, 'QR digitalne karte');
  renderQr($('paymentQrBox'), checkout.payment_qr_url, 'QR za plaćanje');

  $('providerNotice').classList.toggle('hidden', checkout.provider_ready);
  $('providerNotice').innerHTML = checkout.provider_ready ? '' : `<strong>Provider nije potpuno podešen.</strong><br>${escapeHtml(checkout.provider_message || 'Proveri .env podešavanja.')}`;

  $('ipsPayloadDetails').classList.toggle('hidden', !checkout.ips_payload);
  $('ipsPayloadText').textContent = checkout.ips_payload || '';

  $('demoPayBtn').classList.toggle('hidden', checkout.provider !== 'demo');

  const isPaypal = checkout.provider === 'paypal' && checkout.provider_redirect_url;
  $('paypalBox').classList.toggle('hidden', !isPaypal);
  if (isPaypal) {
    $('paypalPayBtn').href = checkout.provider_redirect_url;
    const providerAmount = checkout.provider_amount ? money(checkout.provider_amount, checkout.provider_currency || 'EUR') : money(checkout.amount, checkout.currency);
    $('paypalAmountText').textContent = `PayPal iznos: ${providerAmount}. Nakon plaćanja vrati se na digitalnu kartu.`;
  }
  $('payOnPickupBtn').classList.toggle('hidden', checkout.can_pay_on_pickup === false);
}


async function copyCheckoutLink() {
  if (!checkout) return toast('Prvo učitaj plaćanje');
  await navigator.clipboard.writeText(checkout.checkout_url);
  toast('Link plaćanja je kopiran');
}

async function refreshStatus() {
  if (!reservation) return;
  const code = reservation.reservation_code;
  reservation = await request(`/reservations/code/${encodeURIComponent(code)}`);
  checkout = await request(`/payments/reservations/${encodeURIComponent(code)}/checkout`);
  renderCheckout();
  toast('Status osvežen');
}

async function payOnPickup() {
  if (!reservation) return;
  const phone = reservation.customer_phone || '';
  const done = setButtonLoading($('payOnPickupBtn'), 'Čuvam...');
  try {
    reservation = await request(`/payments/reservations/${encodeURIComponent(reservation.reservation_code)}/pay-on-pickup`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ customer_phone: phone, payment_method: 'pay_on_pickup' })
    });
    if (checkout) {
      checkout.provider = 'pay_on_pickup';
      checkout.method = 'Plaćanje pri preuzimanju';
      checkout.provider_ready = true;
      checkout.provider_message = 'Kupac plaća direktno prodavcu. Platformska provizija se vodi kao dug prodavca prema platformi.';
      checkout.instructions = 'Plaćanje je izabrano pri preuzimanju. Prodavac naplaćuje kupcu, a provizija platforme se obračunava prodavcu kroz finance modul.';
    }
    renderCheckout();
    toast('Plaćanje pri preuzimanju je izabrano');
  } catch (err) { toast(err.message); } finally { done(); }
}

async function demoPay() {
  if (!reservation) return;
  const phone = reservation.customer_phone || '';
  const done = setButtonLoading($('demoPayBtn'), 'Potvrđujem...');
  try {
    reservation = await request(`/payments/reservations/${encodeURIComponent(reservation.reservation_code)}/pay`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ customer_phone: phone, payment_method: 'demo' })
    });
    if (checkout) { checkout.provider = 'demo'; checkout.provider_ready = true; checkout.method = 'Demo plaćanje'; }
    renderCheckout();
    toast('Demo plaćanje potvrđeno');
  } catch (err) { toast(err.message); } finally { done(); }
}

$('loadCheckoutBtn').addEventListener('click', loadCheckout);
$('checkoutCodeInput').addEventListener('keydown', (e) => { if (e.key === 'Enter') loadCheckout(); });
$('copyCheckoutLinkBtn').addEventListener('click', copyCheckoutLink);
$('refreshCheckoutBtn').addEventListener('click', () => refreshStatus().catch((err) => toast(err.message)));
$('demoPayBtn').addEventListener('click', demoPay);
$('payOnPickupBtn').addEventListener('click', payOnPickup);

const params = new URLSearchParams(location.search);
const code = params.get('code');
if (code) { $('checkoutCodeInput').value = code.toUpperCase(); loadCheckout(); }
