const $ = (id) => document.getElementById(id);
const paymentLabels = { unpaid: 'Neplaćeno', payment_pending: 'Plaćanje pokrenuto', paid: 'Plaćeno', refunded: 'Refundirano', failed: 'Neuspešno' };
const payoutLabels = { not_ready: 'Nije spremno', pending: 'Čeka isplatu', paid: 'Isplaćeno', blocked: 'Blokirano', commission_due: 'Provizija za naplatu', invoice_sent: 'Obračun poslat', commission_paid: 'Provizija naplaćena' };

function escapeHtml(str) { return String(str ?? '').replace(/[&<>'"]/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c])); }
function money(amount, currency='RSD') { return `${Number(amount || 0).toLocaleString('sr-RS', { maximumFractionDigits: 2 })} ${currency}`; }
function toast(message) { const el = $('toast'); el.textContent = message; el.classList.add('show'); setTimeout(() => el.classList.remove('show'), 3200); }
function setButtonLoading(btn, text) { const old = btn.innerHTML; btn.disabled = true; btn.innerHTML = `<span class="spinner"></span>${escapeHtml(text)}`; return () => { btn.disabled = false; btn.innerHTML = old; }; }
async function request(url, options={}) { const res = await fetch(url, options); if (!res.ok) { let text = await res.text(); try { text = JSON.parse(text).detail || text; } catch (_) {} throw new Error(text || `HTTP ${res.status}`); } return res.json(); }
function badge(text, cls='') { return `<span class="status ${cls}">${escapeHtml(text)}</span>`; }

function renderStats(data) {
  const items = [
    ['Plaćen promet', money(data.paid_turnover), 'Ukupno kroz aplikaciju'],
    ['Naša provizija', money(data.platform_fee_total), '25% od plaćenih rezervacija'],
    ['Prodavcima neto', money(data.seller_net_total), 'Ukupno neto iznos'],
    ['Čeka isplatu', money(data.pending_payout_amount), `${data.pending_payout_count || 0} rezervacija`],
    ['Plaćene rez.', data.paid_count || 0, 'Status paid'],
    ['IPS u toku', data.payment_pending_count || 0, 'Čeka ručnu potvrdu'],
    ['Isplaćeno', money(data.paid_payout_amount), `${data.paid_payout_count || 0} stavki`],
    ['Blokirano', data.blocked_payout_count || 0, 'Otkazano/refundirano/sporno'],
    ['Plaćanje kod prodavca', money(data.pay_on_pickup_turnover), `${data.pay_on_pickup_count || 0} rezervacija`],
    ['Provizija za naplatu', money(data.commission_due_total), `${data.commission_due_count || 0} stavki`],
  ];
  $('financeStats').innerHTML = items.map(([label, value, sub]) => `<div class="stat-card"><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)} · ${escapeHtml(sub)}</span></div>`).join('');
}

function renderSellers(rows) {
  $('sellerSettlementsBody').innerHTML = rows.length ? rows.map(s => `
    <tr>
      <td><strong>${escapeHtml(s.store_name)}</strong></td>
      <td>${escapeHtml(s.city || '-')}</td>
      <td>${s.reservations_total}</td>
      <td>${s.paid_count}</td>
      <td>${money(s.paid_turnover)}</td>
      <td>${money(s.platform_fee_total)}</td>
      <td>${money(s.seller_net_total)}</td>
      <td><strong>${money(s.pending_payout_amount)}</strong><br><small>${s.pending_payout_count} stavki</small></td>
      <td>${money(s.paid_payout_amount)}<br><small>${s.paid_payout_count} stavki</small><br><small>Provizija za naplatu: <strong>${money(s.commission_due_total || 0)}</strong></small></td>
    </tr>`).join('') : '<tr><td colspan="9" class="empty">Još nema obračuna za prodavce.</td></tr>';
}

function renderCloseout(data) {
  const t = data.totals || {};
  const items = [
    ['Ukupno rez.', t.reservations_total || 0, 'svi partneri'],
    ['Preuzeto', t.picked_up || 0, 'realizovano'],
    ['Plaćeno online', money(t.paid_turnover), 'kroz aplikaciju'],
    ['Kod partnera', money(t.pay_on_pickup_turnover), 'naplata pri preuzimanju'],
    ['Provizija za naplatu', money(t.commission_due), 'za slanje partnerima'],
    ['Čeka isplatu', money(t.seller_payout_pending), 'neto za partnere'],
  ];
  $('closeoutStats').innerHTML = items.map(([label, value, sub]) => `<div class="stat-card"><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)} · ${escapeHtml(sub)}</span></div>`).join('');
  const rows = data.partners || [];
  $('closeoutBody').innerHTML = rows.length ? rows.map(row => `
    <tr>
      <td><strong>${escapeHtml(row.store_name)}</strong><br><small>${escapeHtml(row.city || '')}</small></td>
      <td>${row.reservations_total}</td>
      <td>${row.picked_up}</td>
      <td>${money(row.paid_turnover)}</td>
      <td>${money(row.pay_on_pickup_turnover)}</td>
      <td><strong>${money(row.commission_due)}</strong><br><small>${row.commission_due_count || 0} stavki</small></td>
      <td>${money(row.invoice_sent)}</td>
      <td class="actions">
        ${Number(row.commission_due || 0) > 0 ? `<button data-commission-sent="${row.store_id}">Obračun poslat</button>` : '<span class="muted">Nema duga</span>'}
      </td>
    </tr>`).join('') : '<tr><td colspan="8" class="empty">Nema partnera za closeout.</td></tr>';
}

function renderReservations(rows) {
  $('financeReservationsBody').innerHTML = rows.length ? rows.map(r => `
    <tr>
      <td><strong>${escapeHtml(r.reservation_code)}</strong><br><a href="/checkout?code=${encodeURIComponent(r.reservation_code)}">checkout</a></td>
      <td>${escapeHtml(r.product_name || '-') }</td>
      <td>${escapeHtml(r.store_name || '-')}</td>
      <td>${escapeHtml(r.customer_name)}<br><small>${escapeHtml(r.customer_phone)}</small></td>
      <td>${badge(paymentLabels[r.payment_status] || r.payment_status, `pay-${r.payment_status}`)}<br><small>${escapeHtml(r.payment_reference || '-')}</small></td>
      <td>${money(r.payable_amount, r.currency)}</td>
      <td>${money(r.platform_fee_amount, r.currency)}</td>
      <td><strong>${money(r.seller_net_amount, r.currency)}</strong></td>
      <td>${badge(payoutLabels[r.seller_payout_status] || r.seller_payout_status, `payout-${r.seller_payout_status}`)}<br><small>${escapeHtml(r.seller_payout_reference || '')}</small></td>
      <td class="actions">
        ${r.payment_status !== 'paid' ? `<button data-confirm-ips="${escapeHtml(r.reservation_code)}">Potvrdi IPS</button>` : ''}
        ${r.payment_status === 'paid' && r.seller_payout_status !== 'paid' ? `<button data-payout-paid="${escapeHtml(r.reservation_code)}" class="secondary">Isplaćeno</button>` : ''}
        ${r.seller_payout_status !== 'blocked' ? `<button data-payout-block="${escapeHtml(r.reservation_code)}" class="danger">Blokiraj</button>` : ''}
      </td>
    </tr>`).join('') : '<tr><td colspan="10" class="empty">Nema rezervacija za izabrane filtere.</td></tr>';
}

async function loadFinance() {
  const done = setButtonLoading($('refreshFinanceBtn'), 'Osvežavam...');
  try {
    const [summary, sellers] = await Promise.all([request('/finance/summary'), request('/finance/seller-settlements')]);
    renderStats(summary); renderSellers(sellers); await loadCloseout(false); await loadReservations(false);
    $('financeMessage').textContent = 'Finansijski podaci su osveženi.';
  } catch (err) { toast(err.message); } finally { done(); }
}

async function loadCloseout(showToast=true) {
  const data = await request('/finance/live-closeout');
  renderCloseout(data);
  if (showToast) toast('Closeout osvežen');
}

async function markCommissionSent(storeId) {
  const reference = prompt('Referenca obračuna:', `COMMISSION-${storeId}-${new Date().toISOString().slice(0,10).replaceAll('-','')}`);
  if (reference === null) return;
  await request(`/finance/stores/${encodeURIComponent(storeId)}/commission-sent?reference=${encodeURIComponent(reference)}`, { method: 'PATCH' });
}

async function loadReservations(showToast=true) {
  const params = new URLSearchParams();
  const ps = $('paymentStatusFilter').value; const po = $('payoutStatusFilter').value;
  if (ps) params.set('payment_status', ps); if (po) params.set('payout_status', po); params.set('limit', '200');
  const rows = await request(`/finance/reservations?${params}`);
  renderReservations(rows); if (showToast) toast('Rezervacije učitane');
}

async function confirmIps(code, reference='', note='') {
  const body = { provider: 'ips_qr', reference: reference || `IPS-${code}`, note };
  await request(`/finance/reservations/${encodeURIComponent(code)}/confirm-ips`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
}

async function updatePayout(code, status) {
  const reference = status === 'paid' ? prompt('Referenca isplate prodavcu / broj naloga:', `ISPLATA-${code}`) : '';
  if (status === 'paid' && reference === null) return;
  const note = status === 'blocked' ? prompt('Razlog blokiranja isplate:', 'Spornost / refund / provera') : '';
  if (status === 'blocked' && note === null) return;
  await request(`/finance/reservations/${encodeURIComponent(code)}/payout`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ seller_payout_status: status, reference, note }) });
}

$('confirmIpsBtn').addEventListener('click', async () => {
  const code = $('financeCodeInput').value.trim().toUpperCase();
  if (!code) return toast('Unesi kod rezervacije');
  const done = setButtonLoading($('confirmIpsBtn'), 'Potvrđujem...');
  try { await confirmIps(code, $('financeReferenceInput').value.trim(), $('financeNoteInput').value.trim()); $('financeMessage').textContent = `Uplata za ${code} je potvrđena. Isplata prodavcu je sada u statusu “čeka isplatu”.`; await loadFinance(); }
  catch (err) { toast(err.message); }
  finally { done(); }
});

$('loadFinanceReservationsBtn').addEventListener('click', () => loadReservations().catch(err => toast(err.message)));
$('loadCloseoutBtn').addEventListener('click', () => loadCloseout().catch(err => toast(err.message)));
$('refreshFinanceBtn').addEventListener('click', loadFinance);
$('closeoutBody').addEventListener('click', async (e) => {
  const storeId = e.target.getAttribute('data-commission-sent');
  if (!storeId) return;
  try {
    await markCommissionSent(storeId);
    await loadFinance();
    toast('Obračun provizije je označen kao poslat');
  } catch (err) {
    toast(err.message);
  }
});
$('financeReservationsBody').addEventListener('click', async (e) => {
  const confirmCode = e.target.getAttribute('data-confirm-ips');
  const paidCode = e.target.getAttribute('data-payout-paid');
  const blockCode = e.target.getAttribute('data-payout-block');
  try {
    if (confirmCode) { if (!confirm(`Potvrditi IPS uplatu za ${confirmCode}?`)) return; await confirmIps(confirmCode); }
    if (paidCode) { await updatePayout(paidCode, 'paid'); }
    if (blockCode) { await updatePayout(blockCode, 'blocked'); }
    await loadFinance(); toast('Status je sačuvan');
  } catch (err) { toast(err.message); }
});

loadFinance();
