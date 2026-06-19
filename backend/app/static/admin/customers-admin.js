const customersState = {
  status: '',
  limit: 500,
  rows: [],
};

const $ = (selector) => document.querySelector(selector);

function escapeHtml(value) {
  return String(value == null ? '' : value).replace(/[&<>"']/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  }[char]));
}

function formatDate(value) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return escapeHtml(value);
  return date.toLocaleString('sr-RS', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function setResult(message, type = 'info') {
  const box = $('#customersResult');
  if (!box) return;
  box.textContent = message;
  box.className = `result compact-result status-panel ${type}`;
}

async function customerApi(path, options = {}) {
  const response = await fetch(path, {
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  const text = await response.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch (error) {
    data = { detail: text || response.statusText };
  }
  if (!response.ok) {
    throw new Error(data.detail || data.message || `HTTP ${response.status}`);
  }
  return data;
}

function statusBadge(customer) {
  if (customer.is_blocked || customer.status === 'blocked') {
    return '<span class="status status-open">Blokiran</span>';
  }
  return '<span class="status status-resolved">Aktivan</span>';
}

function renderStats(payload) {
  const rows = payload.customers || [];
  const blocked = Number(payload.blocked_customers_total || 0);
  const active = rows.filter((item) => item.status === 'active').length;
  const cancellations = rows.reduce((sum, item) => sum + Number(item.cancelled_reservations || 0), 0);
  const thresholdRow = rows.find((item) => item.cancel_block_threshold);
  const threshold = (thresholdRow && thresholdRow.cancel_block_threshold) || 3;
  $('#customersStats').innerHTML = [
    ['Ukupno kupaca', payload.customers_total == null ? rows.length : payload.customers_total],
    ['Aktivni u prikazu', active],
    ['Blokirani ukupno', blocked],
    ['Ukupno otkazivanja', cancellations],
    ['Prag blokade', `${threshold} otkazivanja`],
  ].map(([label, value]) => `<div class="stat"><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)}</span></div>`).join('');
}

function renderCustomers(payload) {
  const rows = payload.customers || [];
  customersState.rows = rows;
  renderStats(payload);
  if (!rows.length) {
    $('#customersWrap').innerHTML = '<div class="empty-state">Nema kupaca za izabrani filter.</div>';
    return;
  }

  $('#customersWrap').innerHTML = `
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>Kupac</th>
          <th>Status</th>
          <th>Rezervacije</th>
          <th>Otkazivanja</th>
          <th>Blokada</th>
          <th>Poslednja aktivnost</th>
          <th>Akcije</th>
        </tr>
      </thead>
      <tbody>
        ${rows.map((customer) => {
          const cancelled = Number(customer.cancelled_reservations || 0);
          const threshold = Number(customer.cancel_block_threshold || 3);
          const remaining = Number(customer.remaining_cancellations_before_block || 0);
          const cancelText = customer.is_blocked
            ? `${cancelled}/${threshold} - blokiran`
            : `${cancelled}/${threshold} - jos ${remaining}`;
          const contact = [
            customer.name ? `<strong>${escapeHtml(customer.name)}</strong>` : '<strong>Kupac bez imena</strong>',
            customer.phone ? escapeHtml(customer.phone) : '',
            customer.email ? escapeHtml(customer.email) : '',
          ].filter(Boolean).join('<br>');
          const blockInfo = customer.is_blocked
            ? `${formatDate(customer.blocked_at)}<br><small>${escapeHtml(customer.block_reason || 'Automatska blokada')}</small>`
            : '<small>Nema blokade</small>';
          const action = customer.is_blocked
            ? `<button data-unblock="${customer.id}">Odblokiraj</button>`
            : '<button class="secondary" disabled>Aktivan</button>';
          return `
            <tr>
              <td>${escapeHtml(customer.id)}</td>
              <td>${contact}</td>
              <td>${statusBadge(customer)}</td>
              <td>
                <strong>${escapeHtml(customer.total_reservations || 0)}</strong> ukupno<br>
                <small>${escapeHtml(customer.completed_reservations || 0)} preuzeto</small>
              </td>
              <td>${escapeHtml(cancelText)}</td>
              <td>${blockInfo}</td>
              <td>${formatDate(customer.last_reservation_at || customer.updated_at)}</td>
              <td class="actions">${action}</td>
            </tr>
          `;
        }).join('')}
      </tbody>
    </table>
  `;
}

async function loadCustomers() {
  const params = new URLSearchParams({ limit: String(customersState.limit) });
  if (customersState.status) params.set('status', customersState.status);
  setResult('Ucitavam kupce...', 'loading');
  const payload = await customerApi(`/customers/database?${params.toString()}`);
  renderCustomers(payload);
  setResult(`Ucitano ${(payload.customers || []).length} kupaca.`, 'ok');
}

async function unblockCustomer(customerId) {
  if (!confirm('Odblokirati ovog kupca?')) return;
  setResult('Odblokiram kupca...', 'loading');
  const payload = await customerApi(`/customers/${customerId}/unblock`, { method: 'POST' });
  setResult(payload.message || 'Kupac je odblokiran.', 'ok');
  await loadCustomers();
}

async function rebuildCustomers() {
  if (!confirm('Obnoviti korisnicku bazu iz svih rezervacija?')) return;
  setResult('Obnavljam korisnicku bazu...', 'loading');
  const payload = await customerApi('/customers/database/rebuild', { method: 'POST' });
  setResult(payload.message || 'Korisnicka baza je obnovljena.', 'ok');
  await loadCustomers();
}

document.addEventListener('click', (event) => {
  const unblockButton = event.target.closest('[data-unblock]');
  if (unblockButton) {
    unblockCustomer(unblockButton.dataset.unblock).catch((error) => setResult(error.message, 'error'));
  }
});

$('#refreshCustomersBtn').addEventListener('click', () => {
  loadCustomers().catch((error) => setResult(error.message, 'error'));
});

$('#rebuildCustomersBtn').addEventListener('click', () => {
  rebuildCustomers().catch((error) => setResult(error.message, 'error'));
});

$('#statusFilter').addEventListener('change', (event) => {
  customersState.status = event.target.value;
  loadCustomers().catch((error) => setResult(error.message, 'error'));
});

loadCustomers().catch((error) => setResult(error.message, 'error'));
