const $ = (id) => document.getElementById(id);
const REQUIRED_CHECKS = [
  ['agreement_accepted', 'Prihvati uslove korišćenja i ugovor prodavca.'],
  ['liability_accepted', 'Potvrdi odgovornost za opis, kvalitet, rok, alergene i bezbednost hrane.'],
  ['food_photo_required_accepted', 'Potvrdi pravilo da svaki artikal mora imati stvarnu sliku, opis, rok i vreme preuzimanja.'],
  ['commission_terms_accepted', 'Prihvati proviziju platforme za rezervacije.'],
  ['invoice_terms_accepted', 'Prihvati rok plaćanja fakture za proviziju.'],
];

function result(message, type = 'info') {
  const out = $('partnerResult');
  if (!out) return;
  out.textContent = message;
  out.dataset.state = type;
}

async function errorMessage(response) {
  const text = await response.text();
  try {
    const data = JSON.parse(text);
    return data.detail || data.message || text;
  } catch (_) {
    return text;
  }
}

$('usePartnerGps')?.addEventListener('click', () => {
  if (!navigator.geolocation) {
    alert('GPS nije podržan');
    return;
  }
  navigator.geolocation.getCurrentPosition(
    (position) => {
      $('latInput').value = position.coords.latitude;
      $('lngInput').value = position.coords.longitude;
    },
    (error) => alert(`GPS greška: ${error.message}`),
    { enableHighAccuracy: true, timeout: 15000 },
  );
});

function checkboxValue(form, name) {
  return Boolean(form.querySelector(`[name="${name}"]`)?.checked);
}

function validatePartnerForm(formEl) {
  const missingField = Array.from(formEl.querySelectorAll('[required]'))
    .find((field) => field.type !== 'checkbox' && !String(field.value || '').trim());
  if (missingField) {
    const label = missingField.closest('label')?.textContent?.trim() || 'obavezno polje';
    missingField.focus();
    result(`Popuni obavezno polje: ${label}.`, 'error');
    return false;
  }
  const missingCheck = REQUIRED_CHECKS.find(([name]) => !checkboxValue(formEl, name));
  if (missingCheck) {
    formEl.querySelector(`[name="${missingCheck[0]}"]`)?.focus();
    result(missingCheck[1], 'error');
    return false;
  }
  return true;
}

$('partnerForm')?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const formEl = event.target;
  if (!validatePartnerForm(formEl)) return;
  const fd = new FormData(formEl);
  const body = Object.fromEntries(fd.entries());
  ['latitude', 'longitude'].forEach((key) => {
    body[key] = body[key] ? Number(body[key]) : null;
  });
  [
    'agreement_accepted',
    'liability_accepted',
    'commission_terms_accepted',
    'food_photo_required_accepted',
    'invoice_terms_accepted',
    'home_producer_acknowledged',
  ].forEach((key) => {
    body[key] = checkboxValue(formEl, key);
  });

  const btn = formEl.querySelector('button[type="submit"]');
  const oldText = btn?.textContent || 'Pošalji prijavu';
  if (btn) {
    btn.disabled = true;
    btn.textContent = 'Šaljem...';
  }
  result('Šaljem prijavu prodavca...', 'info');
  try {
    const response = await fetch('/seller-applications', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!response.ok) throw new Error(await errorMessage(response));
    const data = await response.json();
    result(`Prijava poslata. ID: ${data.application.id}. Admin proverava podatke pre odobrenja.`, 'success');
    formEl.reset();
  } catch (err) {
    result(`Greška: ${err.message}`, 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = oldText;
    }
  }
});
