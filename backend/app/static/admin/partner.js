const $ = (id) => document.getElementById(id);

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

$('partnerForm')?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const formEl = event.target;
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
  btn.disabled = true;
  btn.textContent = 'Šaljem...';
  try {
    const response = await fetch('/seller-applications', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!response.ok) throw new Error(await response.text());
    const data = await response.json();
    $('partnerResult').textContent = `Prijava poslata. ID: ${data.application.id}. Admin proverava podatke pre odobrenja.`;
    formEl.reset();
  } catch (err) {
    $('partnerResult').textContent = `Greška: ${err.message}`;
  } finally {
    btn.disabled = false;
    btn.textContent = 'Pošalji prijavu';
  }
});
