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
$('faqList').addEventListener('click', async (event) => {
  const btn = event.target.closest('[data-delete-faq]');
  if (!btn) return;
  knowledge = collectKnowledge();
  knowledge.faqs.splice(Number(btn.dataset.deleteFaq), 1);
  await saveKnowledge();
});

loadKnowledge().catch(err => setStatus(`Greška: ${err.message}`));
