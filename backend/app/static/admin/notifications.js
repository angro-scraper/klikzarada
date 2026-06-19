const $ = (id) => document.getElementById(id);
function escapeHtml(str) { return String(str ?? '').replace(/[&<>'"]/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c])); }
function toast(message) { const el = $('toast'); el.textContent = message; el.classList.add('show'); setTimeout(() => el.classList.remove('show'), 3200); }
function setButtonLoading(btn, text) { const old = btn.innerHTML; btn.disabled = true; btn.innerHTML = `<span class="spinner"></span>${escapeHtml(text)}`; return () => { btn.disabled = false; btn.innerHTML = old; }; }
async function request(url, options={}) { const res = await fetch(url, options); if (!res.ok) { let text = await res.text(); try { text = JSON.parse(text).detail || text; } catch (_) {} throw new Error(text || `HTTP ${res.status}`); } return res.json(); }
function badge(text, cls='') { return `<span class="status ${cls}">${escapeHtml(text)}</span>`; }

function renderStatus(data) {
  const items = [
    ['SMS uključen', data.sms_enabled ? 'DA' : 'NE', data.sms_enabled ? 'Poruke se obrađuju' : 'SMS_ENABLED=false'],
    ['Provider', data.sms_provider || '-', data.configured ? 'Podešen' : 'Nedostaje konfiguracija'],
    ['Dry-run', data.sms_dry_run ? 'DA' : 'NE', data.sms_dry_run ? 'Ne šalje stvaran SMS' : 'Može slati stvarno'],
    ['Kupac SMS', data.customer_sms_notifications ? 'DA' : 'NE', 'OTP i rezervacije'],
    ['Prodavac SMS', data.seller_sms_notifications ? 'DA' : 'NE', 'Kasnije za seller notifikacije'],
    ['Status', data.configured ? 'OK' : 'NIJE PODEŠENO', (data.missing || []).join(', ') || 'Spremno'],
  ];
  $('notificationStatus').innerHTML = items.map(([label, value, sub]) => `<div class="stat-card"><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)} · ${escapeHtml(sub)}</span></div>`).join('');
  $('notificationConfigHelp').textContent = `Primer .env podešavanja:\n\nSMS_ENABLED=true\nSMS_PROVIDER=mock\nSMS_DRY_RUN=true\nCUSTOMER_SMS_NOTIFICATIONS=true\nDEV_SHOW_OTP=true\n\nZa realan HTTP SMS gateway:\nSMS_PROVIDER=http_api\nSMS_DRY_RUN=false\nSMS_HTTP_URL=https://sms-provider.example/send\nSMS_HTTP_TOKEN=...\nSMS_SENDER=SacuvajHranu\n\nLog fajl: ${data.log_file || '-'}`;
}

function renderLog(rows) {
  $('notificationsBody').innerHTML = rows.length ? rows.map(r => `
    <tr>
      <td>${escapeHtml((r.created_at || '').replace('T', ' ').replace('Z', ''))}</td>
      <td>${escapeHtml(r.channel || '-')}</td>
      <td>${escapeHtml(r.provider || '-')}</td>
      <td>${escapeHtml(r.purpose || '-')}</td>
      <td>${escapeHtml(r.to || '-')}</td>
      <td>${badge(r.status || '-', `notice-${r.status || ''}`)}</td>
      <td style="max-width:420px">${escapeHtml(r.message || '')}</td>
      <td>${escapeHtml(r.error || '')}</td>
    </tr>`).join('') : '<tr><td colspan="8" class="empty">Još nema SMS/notification zapisa.</td></tr>';
}

async function loadStatus() {
  const data = await request('/notifications/status');
  renderStatus(data);
}

async function loadLog(showToast=false) {
  const params = new URLSearchParams();
  const purpose = $('notificationPurposeFilter').value;
  const status = $('notificationStatusFilter').value;
  if (purpose) params.set('purpose', purpose);
  if (status) params.set('status', status);
  params.set('limit', '200');
  const rows = await request(`/notifications/log?${params}`);
  renderLog(rows);
  if (showToast) toast('Log je osvežen');
}

async function refreshAll() {
  const done = setButtonLoading($('refreshNotificationsBtn'), 'Osvežavam...');
  try { await loadStatus(); await loadLog(); $('notificationMessage').textContent = 'Notification center je osvežen.'; }
  catch (err) { toast(err.message); }
  finally { done(); }
}

$('sendTestSmsBtn').addEventListener('click', async () => {
  const phone = $('testSmsPhone').value.trim();
  const message = $('testSmsMessage').value.trim() || 'Sačuvaj Hranu test SMS poruka.';
  if (!phone) return toast('Unesi telefon');
  const done = setButtonLoading($('sendTestSmsBtn'), 'Šaljem...');
  try {
    const result = await request('/notifications/test-sms', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ phone, message }) });
    $('notificationMessage').textContent = `Test poruka: ${result.notification.status}. Ako je mock/dry-run, poruka je samo u logu.`;
    await loadLog(); await loadStatus();
  } catch (err) { toast(err.message); }
  finally { done(); }
});
$('loadNotificationsBtn').addEventListener('click', () => loadLog(true).catch(err => toast(err.message)));
$('refreshNotificationsBtn').addEventListener('click', refreshAll);

refreshAll();
