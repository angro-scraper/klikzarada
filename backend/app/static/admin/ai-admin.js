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
function renderSellerDiscoveryError(message) {
  $('sellerDiscoveryResult').innerHTML = `
    <div class="status-box warning">
      <strong>AI pretraga nije završena</strong>
      <p>${escapeHtml(message || 'Došlo je do greške tokom AI pretrage prodavaca.')}</p>
      <small>Osveži stranicu ili pokreni novu pretragu sa manjim limitom.</small>
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
  const warnings = (data.warnings || []).map((warning) => `<li>${escapeHtml(warning)}</li>`).join('');
  const rows = items.map((candidate) => `
    <tr>
      <td><strong>${escapeHtml(candidate.name)}</strong><br><small>${escapeHtml(candidate.note || candidate.ai_reason || '')}</small></td>
      <td>${escapeHtml(candidate.city || '')}<br><small>${escapeHtml(candidate.category || '')}</small></td>
      <td>${escapeHtml(candidate.contact || candidate.source_url || '-')}</td>
      <td><strong>${escapeHtml(candidate.score || 0)}</strong></td>
      <td><span class="keywords">${escapeHtml(candidate.status || candidate.kind || 'lead')}</span></td>
      <td>${candidate.id ? `<button type="button" class="secondary" data-lead-contact="${escapeHtml(candidate.id)}">Odobri kontakt</button>` : '<span class="help-text">Nema lead ID</span>'}</td>
    </tr>
  `).join('');
  $('sellerDiscoveryResult').innerHTML = `
    <strong>${escapeHtml(data.message || 'AI pretraga prodavaca je završena.')}</strong>
    <p>${escapeHtml(data.ai_summary || '')}</p>
    ${warnings ? `<div class="status-box warning"><strong>Upozorenja</strong><ul>${warnings}</ul></div>` : ''}
    <small>Leadovi: +${data.summary?.leads_created || 0} novih, ${data.summary?.leads_updated || 0} ažuriranih · Prodavci: +${data.summary?.created_stores || 0} · Izvori: +${data.summary?.created_sources || 0} · OpenAI: ${data.ai_used ? 'da' : 'ne'} · Web: ${data.web_search_enabled ? 'uključen' : 'isključen'}</small>
    <div class="table-wrap compact-table seller-discovery-table-v104">
      <table>
        <thead><tr><th>Kandidat</th><th>Grad</th><th>Kontakt/izvor</th><th>Score</th><th>Status</th><th>Akcija</th></tr></thead>
        <tbody>${rows || '<tr><td colspan="6">Nema kandidata za ove kriterijume.</td></tr>'}</tbody>
      </table>
    </div>
    <p class="help-text">Predlozi za ručno proveravanje: ${escapeHtml((data.search_queries || []).join(' · '))}. Domaća radinost i fizička lica se uvek proveravaju pre kontakta i registracije.</p>
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
