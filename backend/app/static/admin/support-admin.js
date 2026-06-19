const statusLabels = {
  open: 'Otvoreno',
  in_progress: 'U radu',
  waiting_customer: 'Čeka kupca',
  resolved: 'Rešeno',
  closed: 'Zatvoreno'
};

const priorityLabels = {
  urgent: 'Hitno',
  high: 'Visoko',
  normal: 'Normalno',
  low: 'Nisko'
};

function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, ch => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[ch]));
}

function queryParams() {
  const params = new URLSearchParams();
  const status = document.getElementById('statusFilter')?.value;
  const priority = document.getElementById('priorityFilter')?.value;
  const topic = document.getElementById('topicFilter')?.value;
  const q = document.getElementById('searchFilter')?.value.trim();
  if (status) params.set('status', status);
  if (priority) params.set('priority', priority);
  if (topic) params.set('topic', topic);
  if (q) params.set('q', q);
  return params.toString();
}

async function loadSummary() {
  const summary = await fetch('/support-tickets/summary').then(r => r.json());
  document.getElementById('supportSummary').innerHTML = [
    ['Otvoreno', summary.open],
    ['Hitno', summary.urgent_open],
    ['Čeka kupca', summary.waiting_customer],
    ['Rešeno', summary.resolved],
    ['Vezano za rezervaciju', summary.linked_reservations],
    ['Najstariji otvoren', `${summary.oldest_open_minutes || 0} min`]
  ].map(([label, value]) => `<div class="stat-card"><strong>${esc(value)}</strong><span>${esc(label)}</span></div>`).join('');
}

function reservationBlock(ticket) {
  const r = ticket.reservation;
  if (!r) {
    return ticket.reservation_code
      ? `<span class="status">Kod nije nađen</span><br><small>${esc(ticket.reservation_code)}</small>`
      : '<span class="muted">Bez koda</span>';
  }
  return `<strong>${esc(r.reservation_code)}</strong><br>
    <small>${esc(r.product_name)} · ${esc(r.store_name)}</small><br>
    <span class="status">${esc(r.reservation_status)}</span>
    <span class="status">${esc(r.payment_status)}</span><br>
    <a href="${esc(r.ticket_url)}" target="_blank" rel="noopener">Otvori kartu</a>`;
}

function actionButtons(ticket) {
  const id = esc(ticket.id);
  return `<div class="actions">
    <button onclick="setTicket('${id}','in_progress')">U radu</button>
    <button class="secondary" onclick="setTicket('${id}','waiting_customer')">Čeka kupca</button>
    <button onclick="setTicket('${id}','resolved')">Rešeno</button>
    <button class="secondary" onclick="setPriority('${id}')">Prioritet</button>
    <button class="secondary" onclick="noteTicket('${id}')">Napomena</button>
  </div>`;
}

function ticketRow(ticket) {
  const priority = ticket.priority || 'normal';
  const status = ticket.status || 'open';
  return `<tr>
    <td><strong>${esc(ticket.id)}</strong><br><small>${esc(ticket.created_at || '')}</small><br><small>${ticket.age_minutes == null ? '' : esc(ticket.age_minutes + ' min otvoren')}</small></td>
    <td><span class="status status-${esc(status)}">${esc(statusLabels[status] || status)}</span><br><span class="status priority-${esc(priority)}">${esc(priorityLabels[priority] || priority)}</span></td>
    <td>${esc(ticket.topic || '')}<br><small>${esc(ticket.source_page || '')}</small></td>
    <td><strong>${esc(ticket.name || '')}</strong><br>${esc(ticket.phone || '')}<br>${esc(ticket.email || '')}</td>
    <td>${reservationBlock(ticket)}</td>
    <td>${esc(ticket.message || '')}<br><small>${esc(ticket.internal_note || '')}</small></td>
    <td>${actionButtons(ticket)}</td>
  </tr>`;
}

async function loadTickets() {
  await loadSummary();
  const qs = queryParams();
  const rows = await fetch(`/support-tickets${qs ? `?${qs}` : ''}`).then(r => r.json());
  const html = rows.length
    ? `<table><thead><tr><th>ID</th><th>Status</th><th>Tema</th><th>Kontakt</th><th>Rezervacija</th><th>Poruka</th><th>Akcije</th></tr></thead><tbody>${rows.map(ticketRow).join('')}</tbody></table>`
    : '<div class="empty">Nema ticket-a za izabrani filter.</div>';
  document.getElementById('ticketsWrap').innerHTML = html;
}

async function patchTicket(id, body) {
  const r = await fetch(`/support-tickets/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body)
  });
  if (!r.ok) {
    const data = await r.json().catch(() => ({}));
    alert(data.detail || 'Izmena nije uspela.');
  }
  await loadTickets();
}

async function setTicket(id, status) {
  await patchTicket(id, {status});
}

async function setPriority(id) {
  const priority = prompt('Prioritet: urgent, high, normal, low', 'high');
  if (!priority) return;
  await patchTicket(id, {status: 'in_progress', priority});
}

async function noteTicket(id) {
  const internal_note = prompt('Interna napomena:');
  if (internal_note === null) return;
  await patchTicket(id, {status: 'in_progress', internal_note});
}

document.getElementById('loadTicketsBtn').onclick = loadTickets;
['statusFilter', 'priorityFilter', 'topicFilter'].forEach(id => {
  document.getElementById(id)?.addEventListener('change', loadTickets);
});
document.getElementById('searchFilter')?.addEventListener('input', () => {
  clearTimeout(window.supportSearchTimer);
  window.supportSearchTimer = setTimeout(loadTickets, 250);
});
loadTickets();
