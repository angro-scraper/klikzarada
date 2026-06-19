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
let currentProduct = null;

function toast(message) {
  const el = $('toast');
  el.textContent = message;
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 2800);
}

function escapeHtml(str) {
  return String(str ?? '').replace(/[&<>'"]/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
}

function money(product) {
  const oldPrice = product.original_price ? `${product.original_price} ${product.currency}` : '';
  const newPrice = product.discounted_price ? `${product.discounted_price} ${product.currency}` : '';
  if (oldPrice && newPrice && oldPrice !== newPrice) return `<span class="old-price">${oldPrice}</span> <strong>${newPrice}</strong>`;
  return newPrice || oldPrice || '-';
}

function statusLabel(status) {
  return statusLabels[status] || status || '-';
}

function reservationStatusLabel(status) {
  return reservationStatusLabels[status] || status || '-';
}

async function request(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}

function renderDetail(product) {
  const availableText = product.available_quantity === null || product.available_quantity === undefined ? 'dostupno' : `${product.available_quantity} kom dostupno`;
  const phone = product.store_phone ? `<a class="link-button" href="tel:${escapeHtml(product.store_phone)}">Pozovi prodavca</a>` : '';
  const source = product.source_url ? `<a class="link-button secondary-link" href="${escapeHtml(product.source_url)}" target="_blank" rel="noreferrer">Otvori izvor</a>` : '';
  $('pageTitle').textContent = product.name;
  $('reservationProductId').value = product.id;
  $('reservationProductText').textContent = `Rezervacija za: ${product.name}`;
  const quantityInput = $('reservationForm').elements.quantity;
  if (product.available_quantity !== null && product.available_quantity !== undefined) quantityInput.max = product.available_quantity;
  $('detailBox').innerHTML = `
    <div class="detail-grid">
      <div>
        ${product.image_url ? `<img class="detail-image" src="${escapeHtml(product.image_url)}" alt="${escapeHtml(product.name)}" />` : `<div class="detail-image placeholder-image">Bez slike</div>`}
        <span class="status status-${escapeHtml(product.status)}">${escapeHtml(statusLabel(product.status))}</span>
        <h2>${escapeHtml(product.name)}</h2>
        <p class="category">${escapeHtml(product.category || 'bez kategorije')}</p>
        <p class="price detail-price">${money(product)}</p>
        <div class="detail-actions">${phone}${source}</div>
      </div>
      <div class="detail-facts">
        <p><b>Prodavac:</b> ${escapeHtml(product.store_name || '-')}</p>
        <p><b>Grad:</b> ${escapeHtml(product.store_city || '-')}</p>
        <p><b>Adresa:</b> ${escapeHtml(product.store_address || '-')}</p>
        <p><b>Telefon:</b> ${escapeHtml(product.store_phone || '-')}</p>
        <p><b>Popust:</b> ${product.discount_percent ? `${escapeHtml(product.discount_percent)}%` : '-'}</p>
        <p><b>Rok:</b> ${escapeHtml(product.expiry_date || 'nije potvrđen')}</p>
        <p><b>Tip roka:</b> ${escapeHtml(product.expiry_type || 'unknown')}</p>
        <p><b>Preuzimanje:</b> ${escapeHtml(product.pickup_window || 'dogovor sa prodavcem')}</p>
        <p><b>Dostupno:</b> ${escapeHtml(availableText)}</p>
      </div>
    </div>
  `;
}

async function loadProduct() {
  const id = new URLSearchParams(location.search).get('id');
  if (!id) throw new Error('Nedostaje ID ponude u URL-u');
  currentProduct = await request(`/products/${encodeURIComponent(id)}`);
  renderDetail(currentProduct);
}

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
  const reservation = await request('/reservations', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  $('reservationResult').textContent = `Rezervacija poslata. Kod rezervacije: ${reservation.reservation_code}\nStatus: ${reservationStatusLabel(reservation.status)}\nSačekaj potvrdu prodavca/admina.`;
  event.target.reset();
  toast(`Rezervacija kreirana: ${reservation.reservation_code}`);
  await loadProduct();
});

loadProduct().catch((err) => {
  $('detailBox').innerHTML = `<p class="empty">Greška: ${escapeHtml(err.message)}</p>`;
  toast(`Greška: ${err.message}`);
});
