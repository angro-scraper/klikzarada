const $ = (id) => document.getElementById(id);
const reservationStatusLabels = {
  pending: 'Čeka potvrdu',
  confirmed: 'Potvrđeno',
  picked_up: 'Preuzeto',
  cancelled: 'Otkazano',
  expired: 'Isteklo',
};
const paymentStatusLabels = { unpaid: 'Čeka plaćanje', payment_pending: 'Plaćanje pokrenuto', paid: 'Plaćeno online', pay_on_pickup: 'Plaćanje pri preuzimanju', refunded: 'Refundirano', failed: 'Neuspešno' };

let currentReservation = null;

function toast(message) {
  const el = $('toast');
  el.textContent = message;
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 3000);
}

function escapeHtml(str) {
  return String(str ?? '').replace(/[&<>'"]/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
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

function statusLabel(status) { return reservationStatusLabels[status] || status || '-'; }
function paymentStatusLabel(status) { return paymentStatusLabels[status] || status || '-'; }
function moneyPlain(amount, currency = 'RSD') {
  return `${Number(amount || 0).toLocaleString('sr-RS', { maximumFractionDigits: 2 })} ${currency}`;
}
function paymentSummaryHtml(r) {
  const currency = r.currency || 'RSD';
  return `
    <div class="payment-box-v28">
      <div class="payment-row-v28"><span>Ukupno</span><strong>${moneyPlain(r.gross_amount, currency)}</strong></div>
      <div class="payment-row-v28"><span>Popust za stalne kupce</span><strong>${Number(r.loyalty_discount_percent || 0).toFixed(0)}% · -${moneyPlain(r.loyalty_discount_amount, currency)}</strong></div>
      <div class="payment-row-v28 total"><span>Online plaćeno / za plaćanje</span><strong>${moneyPlain(r.payable_amount, currency)}</strong></div>
      <p class="payment-note-v28">Status plaćanja: ${paymentStatusLabel(r.payment_status)}${r.payment_reference ? ` · Ref: ${escapeHtml(r.payment_reference)}` : ''}</p>
    </div>`;
}
async function payTicket() {
  if (!currentReservation) return toast('Prvo učitaj rezervaciju');
  window.location.href = `/checkout?code=${encodeURIComponent(currentReservation.reservation_code)}`;
}


function buildVisualCode(code) {
  const chars = String(code || '').split('');
  if (!chars.length) return '';
  return chars.map((ch, index) => {
    const width = 4 + ((ch.charCodeAt(0) + index) % 5) * 3;
    return `<span style="width:${width}px"></span>`;
  }).join('');
}

function renderTicket(r) {
  currentReservation = r;
  $('ticketPanel').classList.remove('hidden');
  $('ticketCodeBig').textContent = r.reservation_code;
  $('ticketStatus').textContent = statusLabel(r.status);
  $('ticketStatus').className = `ticket-status-v26 ticket-status-${r.status}`;
  $('visualCode').innerHTML = `<img class="real-qr-v29" src="/qr/reservation/${encodeURIComponent(r.reservation_code)}.svg" alt="QR digitalne karte" />`;
  $('ticketProduct').textContent = r.product_name || `#${r.product_id}`;
  $('ticketStore').textContent = r.store_name || '-';
  $('ticketQuantity').textContent = `${r.quantity} kom`;
  $('ticketCustomer').textContent = r.customer_name || '-';
  $('ticketPhone').textContent = r.customer_phone || '-';
  $('ticketPaymentStatus').textContent = paymentStatusLabel(r.payment_status);
  $('ticketPayable').textContent = moneyPlain(r.payable_amount, r.currency || 'RSD');
  $('ticketLoyalty').textContent = `${Number(r.loyalty_discount_percent || 0).toFixed(0)}%`;
  $('ticketCreated').textContent = r.created_at ? new Date(r.created_at).toLocaleString('sr-RS') : '-';
  $('ticketPaymentBox').innerHTML = paymentSummaryHtml(r) + (r.payment_status !== 'paid' && r.status !== 'cancelled' ? '<div class="actions"><button id="payTicketBtn">Otvori plaćanje</button></div>' : '');
  $('payTicketBtn')?.addEventListener('click', payTicket);
  $('ticketMessage').innerHTML = `Rezervacija je pronađena. Status: <strong>${escapeHtml(statusLabel(r.status))}</strong>. Plaćanje: <strong>${escapeHtml(paymentStatusLabel(r.payment_status))}</strong>.`;
  history.replaceState({}, '', `/reservation?code=${encodeURIComponent(r.reservation_code)}`);
}

async function loadTicket() {
  const code = $('ticketCodeInput').value.trim().toUpperCase();
  if (!code) return toast('Unesi kod rezervacije');
  const btn = $('loadTicketBtn');
  const original = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Učitavam...';
  try {
    const r = await request(`/reservations/code/${encodeURIComponent(code)}`);
    renderTicket(r);
  } catch (err) {
    $('ticketPanel').classList.add('hidden');
    $('ticketMessage').textContent = `Greška: ${err.message}`;
    toast(err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = original;
  }
}

async function copyLink() {
  if (!currentReservation) return toast('Prvo učitaj rezervaciju');
  const url = `${window.location.origin}/reservation?code=${encodeURIComponent(currentReservation.reservation_code)}`;
  await navigator.clipboard.writeText(url);
  toast('Link rezervacije je kopiran');
}

async function shareTicket() {
  if (!currentReservation) return toast('Prvo učitaj rezervaciju');
  const url = `${window.location.origin}/reservation?code=${encodeURIComponent(currentReservation.reservation_code)}`;
  const text = `Sačuvaj Hranu rezervacija ${currentReservation.reservation_code} — ${currentReservation.product_name || 'ponuda'}`;
  if (navigator.share) {
    await navigator.share({ title: 'Sačuvaj Hranu rezervacija', text, url });
  } else {
    await navigator.clipboard.writeText(`${text}\n${url}`);
    toast('Browser ne podržava share, link je kopiran');
  }
}

async function cancelTicket() {
  if (!currentReservation) return toast('Prvo učitaj rezervaciju');
  const phone = $('cancelPhoneInput').value.trim();
  if (!phone) return toast('Unesi telefon korišćen za rezervaciju');
  if (!confirm('Da li sigurno želiš da otkažeš rezervaciju?')) return;
  try {
    const r = await request(`/reservations/code/${encodeURIComponent(currentReservation.reservation_code)}/cancel?phone=${encodeURIComponent(phone)}`, { method: 'PATCH' });
    renderTicket(r);
    toast('Rezervacija je otkazana');
  } catch (err) {
    toast(`Greška: ${err.message}`);
  }
}

$('loadTicketBtn').addEventListener('click', loadTicket);
$('ticketCodeInput').addEventListener('keydown', (event) => { if (event.key === 'Enter') loadTicket(); });
$('copyTicketLinkBtn').addEventListener('click', copyLink);
$('shareTicketBtn').addEventListener('click', () => shareTicket().catch((err) => toast(err.message)));
$('printTicketBtn').addEventListener('click', () => window.print());
$('cancelTicketBtn').addEventListener('click', cancelTicket);

const params = new URLSearchParams(location.search);
const code = params.get('code');
if (code) {
  $('ticketCodeInput').value = code.toUpperCase();
  loadTicket();
}
