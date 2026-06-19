const fmt = new Intl.NumberFormat('sr-RS');
const money = (v) => `${fmt.format(Number(v||0))} RSD`;
function card(label, value, note='') { return `<div class="stat-card"><strong>${value}</strong><span>${label}</span>${note?`<small>${note}</small>`:''}</div>`; }
async function loadOps(){
  const statsEl=document.getElementById('opsStats'); const readyEl=document.getElementById('readinessBox');
  statsEl.innerHTML='<div class="status-panel loading">Učitavam...</div>';
  const [summary, readiness] = await Promise.all([fetch('/operations/summary').then(r=>r.json()), fetch('/operations/readiness').then(r=>r.json())]);
  statsEl.innerHTML = [
    card('Ukupno proizvoda', fmt.format(summary.products_total)),
    card('Javne ponude', fmt.format(summary.public_products)),
    card('Slike u bazi', `${summary.image_coverage_percent}%`, `${fmt.format(summary.products_with_images)} proizvoda`),
    card('Prodavci', fmt.format(summary.stores_total), `${fmt.format(summary.stores_verified)} potvrđenih`),
    card('Rezervacije', fmt.format(summary.reservations_total), `${fmt.format(summary.reservations_pending)} na čekanju`),
    card('Plaćen promet', money(summary.paid_total)),
    card('Naša provizija', money(summary.platform_fee_total)),
    card('Otvorena podrška', fmt.format(summary.support_open)),
  ].join('');
  readyEl.innerHTML = `<h3>Readiness score: ${readiness.score}%</h3>` + readiness.checks.map(c => `<div class="check-row-v35 ${c.ok?'ok':'bad'}"><span>${c.ok?'✓':'!'}</span><div><strong>${c.label}</strong><p>${c.ok?'Spremno':c.fix}</p></div></div>`).join('');
}
document.getElementById('refreshOpsBtn')?.addEventListener('click', loadOps); loadOps().catch(e=>{document.getElementById('opsStats').textContent='Greška: '+e.message});