const $ = (id) => document.getElementById(id);
function escapeHtml(str){return String(str ?? '').replace(/[&<>'"]/g,(c)=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));}
function money(amount,currency='RSD'){return `${Number(amount||0).toLocaleString('sr-RS',{maximumFractionDigits:2})} ${currency}`;}
function toast(message){const el=$('toast');el.textContent=message;el.classList.add('show');setTimeout(()=>el.classList.remove('show'),3200);}
function setButtonLoading(btn,text){const old=btn.innerHTML;btn.disabled=true;btn.innerHTML=`<span class="spinner"></span>${escapeHtml(text)}`;return()=>{btn.disabled=false;btn.innerHTML=old;};}
async function request(url,options={}){const res=await fetch(url,options);if(!res.ok){let text=await res.text();try{text=JSON.parse(text).detail||text}catch(_){}throw new Error(text||`HTTP ${res.status}`)}return res.json();}
function statusBadge(status){const labels={commission_due:'Provizija za naplatu',invoice_sent:'Obračun poslat',commission_paid:'Naplaćeno'};return `<span class="status status-${escapeHtml(status)}">${escapeHtml(labels[status]||status)}</span>`;}
let activeStoreId=null;
function renderStats(data){const items=[['Otvorena provizija',money(data.open_amount),`${data.open_count||0} stavki`],['Obračun poslato',money(data.invoice_sent_amount),`${data.invoice_sent_count||0} stavki`],['Naplaćeno',money(data.paid_amount),`${data.paid_count||0} stavki`],['Model','25%','PayPal ili plaćanje pri preuzimanju']];$('commissionStats').innerHTML=items.map(([label,value,sub])=>`<div class="stat-card"><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)} · ${escapeHtml(sub)}</span></div>`).join('');}
function renderSellers(rows){$('commissionSellersBody').innerHTML=rows.length?rows.map(s=>`
<tr>
<td><strong>${escapeHtml(s.store_name)}</strong><br><small>Seller ID: ${s.store_id} · PIN: ${escapeHtml(s.seller_pin||'-')}</small></td>
<td>${escapeHtml(s.city||'-')}</td>
<td><strong>${money(s.open_amount)}</strong><br><small>${s.open_count} stavki</small></td>
<td>${money(s.invoice_sent_amount)}<br><small>${s.invoice_sent_count} stavki</small></td>
<td>${money(s.paid_amount)}<br><small>${s.paid_count} stavki</small></td>
<td><small>${escapeHtml(s.latest_invoice_reference||'-')}</small></td>
<td class="actions">
<button data-view="${s.store_id}" class="secondary">Stavke</button>
${s.open_count>0?`<button data-invoice="${s.store_id}">Kreiraj obračun</button>`:''}
${s.latest_invoice_reference&&s.invoice_sent_count>0?`<button data-paid="${escapeHtml(s.latest_invoice_reference)}" class="secondary">Označi naplaćeno</button>`:''}
</td>
</tr>`).join(''):'<tr><td colspan="7" class="empty">Još nema provizije za naplatu.</td></tr>';}
function renderItems(rows){$('commissionItemsBody').innerHTML=rows.length?rows.map(r=>`
<tr>
<td><strong>${escapeHtml(r.reservation_code)}</strong><br><a href="/reservation?code=${encodeURIComponent(r.reservation_code)}">karta</a></td>
<td>${escapeHtml(r.customer_name)}<br><small>${escapeHtml(r.customer_phone)}</small></td>
<td>${escapeHtml(r.payment_status)}</td>
<td>${statusBadge(r.commission_status)}</td>
<td>${money(r.payable_amount)}</td>
<td><strong>${money(r.platform_fee_amount)}</strong></td>
<td><small>${escapeHtml(r.invoice_reference||'-')}</small></td>
<td><small>${escapeHtml((r.created_at||'').slice(0,10))}</small></td>
</tr>`).join(''):'<tr><td colspan="8" class="empty">Nema stavki za ovog partnera.</td></tr>';}
async function loadCommission(){const done=setButtonLoading($('refreshCommissionBtn'),'Osvežavam...');try{const [summary,sellers]=await Promise.all([request('/commission/summary'),request('/commission/sellers')]);renderStats(summary);renderSellers(sellers);if(activeStoreId){await loadItems(activeStoreId,false);} }catch(err){toast(err.message)}finally{done();}}
async function loadItems(storeId,showToast=true){activeStoreId=storeId;const rows=await request(`/commission/sellers/${encodeURIComponent(storeId)}/items?include_paid=true`);renderItems(rows);$('commissionItemsTitle').textContent=`Stavke za partnera ID ${storeId}.`;if(showToast)toast('Stavke učitane');}
async function createInvoice(storeId){if(!confirm('Kreirati obračun za sve otvorene stavke ovog partnera?'))return;const data=await request(`/commission/sellers/${encodeURIComponent(storeId)}/invoice`,{method:'POST'});toast(`Obračun kreiran: ${data.invoice_reference} · ${money(data.commission_total)}`);activeStoreId=storeId;await loadCommission();}
async function markPaid(ref){if(!confirm(`Označiti obračun ${ref} kao naplaćen?`))return;const data=await request(`/commission/invoices/${encodeURIComponent(ref)}/mark-paid`,{method:'PATCH'});toast(`Naplaćeno: ${data.invoice_reference} · ${money(data.commission_total)}`);await loadCommission();}
$('refreshCommissionBtn').addEventListener('click',loadCommission);
$('commissionSellersBody').addEventListener('click',async(e)=>{try{const view=e.target.getAttribute('data-view');const inv=e.target.getAttribute('data-invoice');const paid=e.target.getAttribute('data-paid');if(view)await loadItems(view);if(inv)await createInvoice(inv);if(paid)await markPaid(paid);}catch(err){toast(err.message)}});
loadCommission();
