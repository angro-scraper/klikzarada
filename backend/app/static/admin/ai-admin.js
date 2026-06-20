const $ = (id) => document.getElementById(id);
let knowledge = null;

async function request(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) {
    let text = await res.text();
    try { text = JSON.parse(text).detail || text; } catch (_) {}
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}

function setStatus(text) { $('knowledgeStatus').textContent = text; }
function escapeHtml(str) { return String(str ?? '').replace(/[&<>'"]/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c])); }
function formDataJson(form) { return Object.fromEntries(new FormData(form).entries()); }
function checkbox(form, name) { return !!form.querySelector(`[name="${name}"]`)?.checked; }
function normalizeDiscoveryMessage(message) {
  const text = String(message || '').trim();
  const lower = text.toLowerCase();
  if (
    lower.includes('import u prodavce nije uspeo') ||
    lower.includes('import u prodavce trenutno nije uspeo') ||
    lower.includes('duplicate key value') ||
    lower.includes('ix_sources_url') ||
    lower.includes('uniqueviolation') ||
    lower.includes('already exists')
  ) {
    return 'Neki izvori su već postojali u bazi, pa su duplikati preskočeni bez prekida pretrage.';
  }
  if (
    lower.includes('insert into sources') ||
    lower.includes('parameters:') ||
    lower.includes('psycopg') ||
    lower.includes('sqlalchemy') ||
    lower.includes('traceback') ||
    lower.includes('background on this error') ||
    text.length > 700
  ) {
    return 'Pretraga je vratila tehničko upozorenje. Osveži stranicu i probaj ponovo sa manjim limitom ili užim kriterijumom.';
  }
  if (lower.includes('internal server error')) {
    return 'AI pretraga je naišla na serversku grešku. Probaj ponovo za minut ili sa manjim limitom.';
  }
  return text;
}
function isBenignDiscoveryMessage(message) {
  const text = normalizeDiscoveryMessage(message).toLowerCase();
  return text.includes('duplikati preskočeni') || text.includes('već postojali u bazi');
}
function normalizeDiscoveryWarnings(list) {
  const unique = [];
  const seen = new Set();
  for (const item of (list || [])) {
    const normalized = normalizeDiscoveryMessage(item);
    if (!normalized || seen.has(normalized)) continue;
    seen.add(normalized);
    unique.push(normalized);
  }
  return unique;
}
function renderSellerDiscoveryError(message) {
  $('sellerDiscoveryResult').innerHTML = `
    <div class="status-box warning" style="background:#fff8e8;color:#103b2f !important;border:1px solid rgba(198,140,0,.24);">
      <strong style="display:block;color:#103b2f;">AI pretraga nije završena</strong>
      <p style="margin:8px 0 6px;color:#103b2f;">${escapeHtml(normalizeDiscoveryMessage(message) || 'Došlo je do greške tokom AI pretrage prodavaca.')}</p>
      <small style="color:#5f6f68;">Osveži stranicu ili pokreni novu pretragu sa manjim limitom.</small>
    </div>
  `;
}
function setBusy(btn, on = true) {
  if (!btn) return;
  if (on) {
    btn.dataset.oldText = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Radim...';
  } else {
    btn.disabled = false;
    btn.textContent = btn.dataset.oldText || btn.textContent;
  }
}

function renderSellerDiscovery(data) {
  const items = data.leads?.length ? data.leads : (data.candidates || []);
  const warningsList = normalizeDiscoveryWarnings(data.warnings || []);
  const blockingWarnings = warningsList.filter((warning) => !isBenignDiscoveryMessage(warning));
  const benignWarnings = warningsList.filter((warning) => isBenignDiscoveryMessage(warning));
  const warnings = blockingWarnings.map((warning) => `<li>${escapeHtml(warning)}</li>`).join('');
  const notes = benignWarnings.map((warning) => `<li>${escapeHtml(warning)}</li>`).join('');
  const rows = items.map((candidate) => `
    <tr style="background:#fff;color:#103b2f;">
      <td style="background:#fff;color:#103b2f !important;vertical-align:top;">
        <strong style="color:#103b2f !important;">${escapeHtml(candidate.name)}</strong><br>
        <small style="color:#60776d !important;">${escapeHtml(candidate.note || candidate.ai_reason || '')}</small>
      </td>
      <td style="background:#fff;color:#103b2f !important;vertical-align:top;">
        ${escapeHtml(candidate.city || '')}<br>
        <small style="color:#60776d !important;">${escapeHtml(candidate.category || '')}</small>
      </td>
      <td style="background:#fff;color:#103b2f !important;vertical-align:top;word-break:break-word;">
        ${escapeHtml(candidate.contact || candidate.source_url || '-')}<br>
        <small style="color:#60776d !important;">slika: ${candidate.image_evidence ? 'da' : 'ne'} · akcija: ${candidate.discount_evidence ? 'da' : 'ne'} · cena: ${candidate.price_evidence ? 'da' : 'ne'} · hrana: ${candidate.food_evidence ? 'da' : 'ne'} · dubinski pregled: ${candidate.deep_checked ? 'da' : 'ne'}</small>
      </td>
      <td style="background:#fff;color:#103b2f !important;vertical-align:top;"><strong style="color:#103b2f !important;">${escapeHtml(candidate.score || 0)}</strong></td>
      <td style="background:#fff;color:#103b2f !important;vertical-align:top;"><span class="keywords" style="background:#eef8f3;color:#103b2f !important;border:1px solid rgba(16,59,47,.12);">${escapeHtml(candidate.status || candidate.kind || 'lead')}</span></td>
      <td style="background:#fff;color:#103b2f !important;vertical-align:top;">${candidate.id ? `<button type="button" class="secondary" data-lead-contact="${escapeHtml(candidate.id)}">Odobri kontakt</button>` : '<span class="help-text" style="color:#60776d !important;">Nema lead ID</span>'}</td>
    </tr>
  `).join('');
  $('sellerDiscoveryResult').innerHTML = `
    <div style="color:#103b2f !important;">
    <strong style="display:block;color:#103b2f !important;">${escapeHtml(data.message || 'AI pretraga prodavaca je završena.')}</strong>
    <p style="margin:8px 0 12px;color:#103b2f !important;">${escapeHtml(data.ai_summary || '')}</p>
    ${warnings ? `<div class="status-box warning" style="background:#fff8e8;color:#103b2f !important;border:1px solid rgba(198,140,0,.24);"><strong style="color:#103b2f !important;">Upozorenja</strong><ul style="color:#103b2f !important;">${warnings}</ul></div>` : ''}
    ${notes ? `<div class="status-box info" style="background:#eff9f3;color:#103b2f !important;border:1px solid rgba(20,106,82,.18);"><strong style="color:#103b2f !important;">Napomene</strong><ul style="color:#103b2f !important;">${notes}</ul></div>` : ''}
    <small style="display:block;color:#60776d;">Leadovi: +${data.summary?.leads_created || 0} novih, ${data.summary?.leads_updated || 0} ažuriranih · Prodavci: +${data.summary?.created_stores || 0} · Izvori: +${data.summary?.created_sources || 0} · Preskočeni duplikati izvora: ${data.summary?.skipped_sources || 0} · OpenAI: ${data.ai_used ? 'da' : 'ne'} · Web: ${data.web_search_enabled ? 'uključen' : 'isključen'}</small>
    <div class="table-wrap compact-table seller-discovery-table-v104" style="margin-top:.75rem;color:#103b2f;background:#fff;border-radius:18px;overflow:auto;">
      <table style="width:100%;border-collapse:collapse;background:#fff;color:#103b2f;">
        <thead><tr><th style="background:#eef8f3;color:#103b2f;">Kandidat</th><th style="background:#eef8f3;color:#103b2f;">Grad</th><th style="background:#eef8f3;color:#103b2f;">Kontakt/izvor</th><th style="background:#eef8f3;color:#103b2f;">Score</th><th style="background:#eef8f3;color:#103b2f;">Status</th><th style="background:#eef8f3;color:#103b2f;">Akcija</th></tr></thead>
        <tbody>${rows || '<tr><td colspan="6">Nema kandidata za ove kriterijume.</td></tr>'}</tbody>
      </table>
    </div>
    <p class="help-text" style="margin-top:12px;color:#60776d;">Predlozi za ručno proveravanje: ${escapeHtml((data.search_queries || []).join(' · '))}. Kandidati se traže kroz restorane, pekare, prodavnice, maloprodaje i domaću radinost. U pretragu prolaze samo tragovi koji pokazuju hranu, slike proizvoda, cenu i signal popusta ili akcije. Domaća radinost i fizička lica se uvek proveravaju pre kontakta i registracije.</p>
    </div>
  `;
}

async function approveLeadContact(leadId) {
  const result = await request(`/scale-api/leads/${encodeURIComponent(leadId)}/approve-contact`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ channel: 'auto' }),
  });
  alert(result.message || 'Lead je odobren za kontakt.');
}

async function runSellerDiscovery(event) {
  event.preventDefault();
  const form = event.target;
  const btn = event.submitter;
  const payload = formDataJson(form);
  payload.limit = Number(payload.limit || 12);
  payload.include_existing = checkbox(form, 'include_existing');
  payload.include_research_tasks = checkbox(form, 'include_research_tasks');
  payload.import_to_stores = checkbox(form, 'import_to_stores');
  payload.web_search = checkbox(form, 'web_search');
  payload.require_image_evidence = checkbox(form, 'require_image_evidence');
  payload.require_discount_signal = checkbox(form, 'require_discount_signal');
  payload.require_price_evidence = checkbox(form, 'require_price_evidence');
  payload.deep_search = checkbox(form, 'deep_search');
  $('sellerDiscoveryResult').textContent = 'AI traži prodavce i priprema leadove...';
  try {
    setBusy(btn, true);
    const data = await request('/scale-api/seller-discovery/search', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload),
    });
    renderSellerDiscovery(data);
  } catch (err) {
    renderSellerDiscoveryError(err.message);
  } finally {
    setBusy(btn, false);
  }
}

async function loadSellerDiscoveryRuns() {
  $('sellerDiscoveryResult').textContent = 'Učitavam istoriju AI pretraga...';
  try {
    const rows = await request('/scale-api/seller-discovery/runs');
    $('sellerDiscoveryResult').innerHTML = `
      <strong>Istorija AI pretraga prodavaca</strong>
      <div class="table-wrap compact-table seller-discovery-table-v104">
        <table>
          <thead><tr><th>Vreme</th><th>Kriterijumi</th><th>Kandidati</th><th>Leadovi</th><th>AI/Web</th></tr></thead>
          <tbody>${(rows || []).map((row) => `
            <tr>
              <td>${escapeHtml(row.created_at || row.updated_at || '')}</td>
              <td>${escapeHtml(row.criteria?.city || '')} · ${escapeHtml(row.criteria?.category || '')}<br><small>${escapeHtml(row.criteria?.query || '')}</small></td>
              <td>${escapeHtml(row.candidates || 0)}</td>
              <td>+${escapeHtml(row.leads_created || 0)} / ${escapeHtml(row.leads_updated || 0)} ažur.</td>
              <td>AI: ${row.ai_used ? 'da' : 'ne'}<br>Web: ${row.web_search_enabled ? 'da' : 'ne'}</td>
            </tr>
          `).join('') || '<tr><td colspan="5">Još nema AI pretraga.</td></tr>'}</tbody>
        </table>
      </div>
    `;
  } catch (err) {
    renderSellerDiscoveryError(err.message);
  }
}

function renderForm() {
  $('assistantName').value = knowledge.assistant_name || 'Sačuvaj Hranu AI';
  $('tone').value = knowledge.tone || '';
  $('quickReplies').value = (knowledge.quick_replies || []).join(', ');
  $('businessRules').value = (knowledge.business_rules || []).join('\n');
  renderFaqs();
}

function renderFaqs() {
  const faqs = knowledge.faqs || [];
  if (!faqs.length) {
    $('faqList').innerHTML = '<p>Nema FAQ stavki.</p>';
    return;
  }
  $('faqList').innerHTML = faqs.map((faq, index) => `
    <div class="faq-item">
      <strong>${escapeHtml(faq.question)}</strong>
      <p>${escapeHtml(faq.answer)}</p>
      <span class="keywords">${escapeHtml((faq.keywords || []).join(', ') || 'bez ključnih reči')}</span>
      <div><button class="secondary" data-delete-faq="${index}">Obriši</button></div>
    </div>
  `).join('');
}

function collectKnowledge() {
  return {
    assistant_name: $('assistantName').value.trim() || 'Sačuvaj Hranu AI',
    tone: $('tone').value.trim(),
    quick_replies: $('quickReplies').value.split(',').map(x => x.trim()).filter(Boolean),
    business_rules: $('businessRules').value.split('\n').map(x => x.trim()).filter(Boolean),
    faqs: knowledge.faqs || [],
  };
}

async function loadKnowledge() {
  knowledge = await request('/buyer-ai/knowledge');
  renderForm();
  setStatus(`Trening baza učitana. FAQ stavki: ${(knowledge.faqs || []).length}.`);
}

async function saveKnowledge() {
  knowledge = collectKnowledge();
  knowledge = await request('/buyer-ai/knowledge', {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(knowledge)
  });
  renderForm();
  setStatus('Sačuvano. AI chat odmah koristi nova pravila.');
}

async function resetKnowledge() {
  if (!confirm('Da vratim podrazumevanu AI trening bazu?')) return;
  knowledge = await request('/buyer-ai/knowledge/reset', { method: 'POST' });
  renderForm();
  setStatus(`Vraćeno na podrazumevano. FAQ stavki: ${(knowledge.faqs || []).length}.`);
}

async function seedExpandedKnowledge() {
  setStatus('Učitavam proširenu FAQ bazu...');
  knowledge = collectKnowledge();
  await request('/buyer-ai/knowledge', {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(knowledge)
  });
  knowledge = await request('/buyer-ai/knowledge/seed-expanded', { method: 'POST' });
  renderForm();
  setStatus(`Proširena FAQ baza je učitana. Ukupno FAQ stavki: ${(knowledge.faqs || []).length}.`);
}

async function addFaq() {
  const question = $('faqQuestion').value.trim();
  const answer = $('faqAnswer').value.trim();
  const keywords = $('faqKeywords').value.split(',').map(x => x.trim()).filter(Boolean);
  if (!question || !answer) return setStatus('Unesi pitanje i odgovor.');
  knowledge = collectKnowledge();
  knowledge.faqs.push({ question, answer, keywords });
  await saveKnowledge();
  $('faqQuestion').value = '';
  $('faqAnswer').value = '';
  $('faqKeywords').value = '';
  setStatus('FAQ je dodat i sačuvan.');
}

async function testAI(endpoint) {
  const message = $('testMessage').value.trim();
  if (!message) return $('testResult').textContent = 'Unesi poruku za test.';
  $('testResult').textContent = 'AI razmišlja...';
  try {
    const res = await request(endpoint, {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ message, limit: 5 })
    });
    const products = (res.products || []).map(p => `- ${p.name} (${p.discounted_price || '-'} ${p.currency || 'RSD'})`).join('\n');
    $('testResult').textContent = `Intent: ${res.intent}\n\nOdgovor:\n${res.reply}\n\nFilteri:\n${JSON.stringify(res.filters, null, 2)}${products ? `\n\nProizvodi:\n${products}` : ''}`;
  } catch (err) {
    $('testResult').textContent = `Greška: ${err.message}`;
  }
}

$('saveKnowledgeBtn').addEventListener('click', saveKnowledge);
$('resetKnowledgeBtn').addEventListener('click', resetKnowledge);
$('seedExpandedBtn').addEventListener('click', seedExpandedKnowledge);
$('addFaqBtn').addEventListener('click', addFaq);
$('testChatBtn').addEventListener('click', () => testAI('/buyer-ai/chat'));
$('testSearchBtn').addEventListener('click', () => testAI('/buyer-ai/parse'));
$('sellerDiscoveryForm')?.addEventListener('submit', runSellerDiscovery);
$('loadSellerDiscoveryRunsBtn')?.addEventListener('click', loadSellerDiscoveryRuns);
$('sellerDiscoveryResult')?.addEventListener('click', async (event) => {
  const btn = event.target.closest('[data-lead-contact]');
  if (!btn) return;
  setBusy(btn, true);
  try {
    await approveLeadContact(btn.dataset.leadContact);
  } catch (err) {
    alert(`Greška: ${err.message}`);
  } finally {
    setBusy(btn, false);
  }
});
$('faqList').addEventListener('click', async (event) => {
  const btn = event.target.closest('[data-delete-faq]');
  if (!btn) return;
  knowledge = collectKnowledge();
  knowledge.faqs.splice(Number(btn.dataset.deleteFaq), 1);
  await saveKnowledge();
});

loadKnowledge().catch(err => setStatus(`Greška: ${err.message}`));
