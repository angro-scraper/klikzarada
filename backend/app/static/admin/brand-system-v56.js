
(() => {
  const SLOGAN = 'Uštedi novac. Sačuvaj obrok. Smanji bacanje.';
  const BRAND = 'Sačuvaj Hranu';
  const logo = '<span class="sh56-logo small" aria-hidden="true"></span>';
  const values = [
    ['💸','Uštedi novac','Odlični obroci po nižim cenama.'],
    ['🥗','Sačuvaj obrok','Kvalitetna hrana zaslužuje da se pojede.'],
    ['🌿','Smanji bacanje','Zajedno čuvamo hranu i našu planetu.']
  ];
  const trust = [
    ['🛡️','Proverene prodavnice i restorani','Proveravamo kvalitet partnera.'],
    ['🔒','Sigurne rezervacije i plaćanja','Vaša kupovina je bezbedna.'],
    ['🤝','Zajednica koja pravi razliku','Hiljade korisnika već učestvuje.'],
    ['🌿','Za bolju budućnost bez bacanja hrane','Manje otpada, više smisla.']
  ];
  function valueHTML(items, cls='sh56-values'){
    return `<section class="${cls}" data-sh56="values">${items.map(([ic,t,d])=>`<article class="sh56-value"><span class="sh56-icon">${ic}</span><b>${t}</b><p>${d}</p></article>`).join('')}</section>`;
  }
  function normalizeBrand(el){
    if(!el || el.dataset.sh56Normalized) return;
    el.dataset.sh56Normalized = '1';
    el.innerHTML = `<span class="sh56-logo small" aria-hidden="true"></span><span class="sh56-wordmark-text"><strong>Sačuvaj Hranu</strong><small>${SLOGAN}</small></span>`;
  }
  function normalizeTopbar(){
    document.querySelectorAll('.sh55-brand,.brand-lockup,.sh55-ticket-brand').forEach(normalizeBrand);
    const top = document.querySelector('.sh55-topbar,.ticket-header-v26,.checkout-header-v29');
    if(top && !top.querySelector('.brand-slogan-v56')){
      top.classList.add('sh56-topbar');
    }
  }
  function cleanDuplicateMiniValues(){
    document.querySelectorAll('.sh55-mini-values').forEach(box=>{
      if(box.dataset.sh56Clean) return;
      box.dataset.sh56Clean='1';
      const labels = Array.from(box.children).map(x=>x.textContent.trim());
      const unique=[];
      Array.from(box.children).forEach(child=>{
        const tx=child.textContent.trim().replace(/\s+/g,' ');
        if(unique.includes(tx)){ child.remove(); } else unique.push(tx);
      });
    });
  }
  function ensureTopbarForPlainPage(){
    const hasTop = document.querySelector('.sh55-topbar,.ticket-header-v26,.checkout-header-v29,.sidebar49,.fs45-top');
    if(hasTop || document.body.dataset.sh56Topbar) return;
    document.body.dataset.sh56Topbar='1';
    const nav = document.createElement('nav');
    nav.className='sh56-topbar';
    nav.innerHTML = `<a class="sh56-wordmark" href="/app">${logo}<span class="sh56-wordmark-text"><strong>${BRAND}</strong><small>${SLOGAN}</small></span></a><div class="sh56-nav"><a href="/app">Ponude</a><a href="/customer">Kupac</a><a href="/seller">Prodavac</a><a href="/support">Pomoć</a></div>`;
    document.body.insertBefore(nav, document.body.firstChild);
  }
  function ensurePageIdentity(){
    if(document.body.classList.contains('sh55-command') || document.querySelector('.sh55-hero,.fs45-top') || document.querySelector('[data-sh56="identity"]')) return;
    const pageTitle = (document.title || BRAND).replace(/Sačuvaj Hranu|—|V\d+|Admin/g,'').trim() || BRAND;
    const id = document.createElement('section');
    id.className='sh56-page-identity';
    id.dataset.sh56='identity';
    id.innerHTML = `<span class="sh56-logo large"></span><div><span class="sh56-kicker">Sačuvaj Hranu</span><h1>${pageTitle}</h1><p class="sh56-slogan is-header">${SLOGAN}</p></div>`;
    const afterTop = document.querySelector('.sh56-topbar,.sh55-topbar,.ticket-header-v26,.checkout-header-v29');
    if(afterTop && afterTop.nextSibling) afterTop.parentNode.insertBefore(id, afterTop.nextSibling); else document.body.insertBefore(id, document.body.firstChild);
  }
  function ensureGlobalValues(){
    const main = document.querySelector('main') || document.body;
    const important = location.pathname.match(/^\/(customer|seller|checkout|reservation|partner|support|offers|offer|finance|admin|ops|settings-admin|notifications-admin|partners-admin|customers-admin|seller-pro|customer-plus|refund|terms|privacy|food-safety|pilot|launch|expansion|market-ops|execution|real-data|ai-market|live-launch|scale|growth)$/);
    if(!important || document.querySelector('[data-sh56="values"]')) return;
    main.insertAdjacentHTML('afterbegin', valueHTML(values, 'sh56-values three'));
  }
  function ensureTrust(){
    const main = document.querySelector('main') || document.body;
    const important = location.pathname.match(/^\/(customer|seller|checkout|reservation|partner|support|offers|offer|finance|admin|ops|settings-admin|notifications-admin|partners-admin|customers-admin|seller-pro|customer-plus|refund|terms|privacy|food-safety|pilot|launch|expansion|market-ops|execution|real-data|ai-market|live-launch|scale|growth|app|u)$/);
    if(!important || document.querySelector('[data-sh56="trust"],.sh55-trustbar,.sh55-brand-trust')) return;
    main.insertAdjacentHTML('beforeend', valueHTML(trust, 'sh56-trust'));
    const last = main.querySelector('.sh56-trust:last-of-type'); if(last) last.dataset.sh56='trust';
  }
  function fixCommand(){
    if(!document.body.classList.contains('sh55-command')) return;
    const brand = document.querySelector('.brand49');
    if(brand){ brand.innerHTML = `<img src="/admin-assets/brand/logo-mark.svg" alt="Sačuvaj Hranu"/><span class="sh55-command-name"><strong>${BRAND}</strong><small>${SLOGAN}</small></span>`; }
    const top = document.querySelector('.top49 > div');
    if(top && !top.querySelector('.sh56-command-slogan')){
      const p=document.createElement('p'); p.className='sh56-slogan is-hero sh56-command-slogan'; p.textContent=SLOGAN;
      const h1=top.querySelector('h1'); if(h1) h1.insertAdjacentElement('afterend', p);
    }
    const menu=[['🏠','Dashboard'],['🛍️','Korisnička aplikacija'],['🏪','Seller Pro'],['💰','Finansije'],['🚀','Live readiness'],['📍','Market ops'],['✨','AI Market'],['🛟','Support']];
    document.querySelectorAll('.nav49 a').forEach((a,i)=>{ const m=menu[i]; if(m) a.innerHTML=`<span>${m[0]}</span><span>${m[1]}</span>`; });
  }
  function fixConsumerApp(){
    document.querySelectorAll('.fs45-brand, .consumer-brand').forEach(el=>{
      if(el.dataset.sh56Normalized) return; el.dataset.sh56Normalized='1';
      el.innerHTML = `<span class="sh56-logo small"></span><span><strong>${BRAND}</strong><small class="brand-slogan-v56">${SLOGAN}</small></span>`;
    });
  }
  function fixTicketCopy(){
    if(!document.body.classList.contains('sh55-ticket')) return;
    const shell=document.querySelector('.ticket-shell-v26,.checkout-shell-v29') || document.querySelector('main') || document.body;
    if(!document.querySelector('[data-sh56="ticket-help"]')){
      const guide=document.createElement('section'); guide.className='sh56-values'; guide.dataset.sh56='ticket-help';
      guide.innerHTML = `
        <article class="sh56-value"><span class="sh56-icon">1</span><b>Unesi kod</b><p>Pronađi rezervaciju ili plaćanje.</p></article>
        <article class="sh56-value"><span class="sh56-icon">2</span><b>Prikaži kartu</b><p>Digitalna karta ostaje dokaz rezervacije.</p></article>
        <article class="sh56-value"><span class="sh56-icon">3</span><b>Pokaži QR</b><p>Prodavac potvrđuje preuzimanje.</p></article>
        <article class="sh56-value"><span class="sh56-icon">✓</span><b>Preuzmi obrok</b><p>Uštedi novac i smanji bacanje.</p></article>`;
      shell.appendChild(guide);
    }
  }
  function run(){ normalizeTopbar(); ensureTopbarForPlainPage(); ensurePageIdentity(); ensureGlobalValues(); ensureTrust(); cleanDuplicateMiniValues(); fixCommand(); fixConsumerApp(); fixTicketCopy(); }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded', run); else run();
})();
