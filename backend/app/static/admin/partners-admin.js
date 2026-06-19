function esc(value) {
  return String(value ?? '').replace(/[&<>'"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[c]));
}

function sellerTypeLabel(value) {
  return {
    business: 'Firma',
    home_producer: 'Domaća radinost',
    individual: 'Fizičko lice',
    farm: 'Gazdinstvo',
    other: 'Drugo',
  }[value || 'business'] || value || '-';
}

function agreementStatus(app) {
  const ok = app.agreement_accepted && app.liability_accepted && app.commission_terms_accepted && app.food_photo_required_accepted && app.invoice_terms_accepted;
  return ok ? '<span class="status">Uslovi prihvaćeni</span>' : '<span class="status danger">Fale uslovi</span>';
}

async function loadApps() {
  const rows = await fetch('/seller-applications').then((r) => r.json());
  document.getElementById('appsWrap').innerHTML = `
    <table>
      <thead>
        <tr><th>ID</th><th>Status</th><th>Prodavac</th><th>Tip/ugovor</th><th>Kontakt</th><th>Adresa</th><th>Akcije</th></tr>
      </thead>
      <tbody>${rows.map((app) => `
        <tr>
          <td>${esc(app.id)}<br><small>${esc(app.created_at || '')}</small></td>
          <td><span class="status">${esc(app.status)}</span></td>
          <td><strong>${esc(app.business_name)}</strong><br>${esc(app.category || '')}<br><small>${esc(app.company_identifier || '')}</small></td>
          <td>${esc(sellerTypeLabel(app.seller_type))}<br>${agreementStatus(app)}<br><small>${esc(app.agreement_version || '')}</small></td>
          <td>${esc(app.contact_name || '')}<br>${esc(app.phone || '')}<br>${esc(app.email || '')}<br>${esc(app.website || '')}</td>
          <td>${esc(app.city || '')}<br>${esc(app.address || '')}</td>
          <td class="actions">
            <button onclick="approveApp('${esc(app.id)}')">Odobri</button>
            <button class="secondary" onclick="setApp('${esc(app.id)}','contacted')">Kontaktiran</button>
            <button class="danger" onclick="setApp('${esc(app.id)}','rejected')">Odbij</button>
            ${app.store_id ? `<br><small>Store #${esc(app.store_id)}, PIN ${esc(app.seller_pin)}</small>` : ''}
          </td>
        </tr>
      `).join('') || '<tr><td colspan="7">Nema prijava.</td></tr>'}</tbody>
    </table>
  `;
}

async function setApp(id, status) {
  await fetch(`/seller-applications/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  });
  loadApps();
}

async function approveApp(id) {
  const response = await fetch(`/seller-applications/${id}/approve`, { method: 'POST' });
  const data = await response.json();
  alert(data.ok ? `Odobreno. Store ID: ${data.store_id}, PIN: ${data.seller_pin}` : JSON.stringify(data));
  loadApps();
}

document.getElementById('loadAppsBtn').onclick = loadApps;
loadApps();
