from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session

from . import models
from .database import get_db
from .routes.products import VISIBLE_STATUSES, product_available_quantity

router = APIRouter(tags=["V71 Javni dizajn"])
SUPPORT_EMAIL = "kontakt@sacuvaj-hranu.rs"

CSS = """
:root{--green:#0f3d2e;--green2:#14533d;--mint:#4fbf9f;--mint2:#aee8c9;--cream:#f7f4ed;--yellow:#f2b13d;--brown:#6b5e52;--text:#12352a;--muted:#6d7b73;--line:#e9dfcf;--shadow:0 18px 45px rgba(20,83,61,.12);--shadow-soft:0 8px 26px rgba(20,83,61,.08);--radius:22px}*{box-sizing:border-box}html,body{margin:0;background:radial-gradient(circle at top left,#fffaf0 0,#f7f4ed 52%,#fbf8f1 100%);color:var(--text);font-family:Inter,Segoe UI,Arial,sans-serif}a{color:inherit;text-decoration:none}.wrap{max-width:1240px;margin:0 auto;padding:24px}.nav{position:sticky;top:0;z-index:20;background:rgba(247,244,237,.88);backdrop-filter:blur(16px);border-bottom:1px solid rgba(233,223,207,.8)}.nav-inner{max-width:1240px;margin:0 auto;padding:14px 24px;display:flex;align-items:center;justify-content:space-between;gap:20px}.brand{display:flex;align-items:center;gap:12px}.mark{width:50px;height:50px;border-radius:17px;background:linear-gradient(135deg,var(--green),#082c20);box-shadow:var(--shadow-soft);display:grid;place-items:center;color:white;font-weight:900;font-size:24px;position:relative}.mark:after{content:'✓';position:absolute;right:-7px;bottom:-6px;background:var(--mint);color:white;width:25px;height:25px;border-radius:999px;display:grid;place-items:center;border:3px solid var(--cream)}.brand-title{font-weight:900;letter-spacing:-.04em;line-height:.92;font-size:26px}.brand-title span{color:var(--mint)}.brand-sub{font-size:12px;color:var(--muted);font-weight:700;margin-top:3px}.nav-links{display:flex;align-items:center;gap:7px;flex-wrap:wrap}.nav-links a{padding:10px 13px;border-radius:999px;color:#28483e;font-weight:800;font-size:14px}.nav-links a.active,.nav-links a:hover{background:#eaf5ee;color:var(--green)}.btn{display:inline-flex;align-items:center;justify-content:center;border:0;border-radius:14px;background:var(--green);color:white;font-weight:900;padding:12px 16px;box-shadow:var(--shadow-soft);cursor:pointer}.btn.secondary{background:white;color:var(--green);border:1px solid #cfe3d6;box-shadow:none}.hero{display:grid;grid-template-columns:1.05fr .95fr;gap:28px;align-items:center;margin:22px 0 28px}.hero-card{background:rgba(255,255,255,.84);border:1px solid var(--line);border-radius:32px;padding:34px;box-shadow:var(--shadow)}h1{font-size:58px;line-height:.98;letter-spacing:-.055em;margin:0 0 16px;color:var(--green)}h1 span{color:var(--mint)}h2{font-size:30px;letter-spacing:-.035em;margin:0 0 14px;color:var(--green)}h3{margin:0 0 10px;color:var(--green)}p{line-height:1.55}.lead{font-size:18px;color:#406259;max-width:620px}.searchbar{margin-top:22px;background:white;border:1px solid var(--line);border-radius:22px;padding:10px;display:flex;gap:10px;box-shadow:var(--shadow-soft)}.searchbar input,.field{border:1px solid #eadfce;background:#fffdf8;border-radius:14px;padding:13px 14px;min-width:0;color:#233e36}.searchbar input{flex:1}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-top:20px}.stat,.kpi{background:rgba(255,255,255,.88);border:1px solid var(--line);border-radius:18px;padding:16px}.stat b,.kpi b{display:block;font-size:23px;color:var(--green)}.visual{background:linear-gradient(145deg,#fff,#fff5df);border:1px solid var(--line);border-radius:34px;min-height:410px;box-shadow:var(--shadow);padding:24px;position:relative;overflow:hidden}.food-img{height:275px;border-radius:28px;background:radial-gradient(circle at 35% 40%,#f6be4b 0 8%,transparent 9%),radial-gradient(circle at 52% 42%,#c56b29 0 9%,transparent 10%),radial-gradient(circle at 62% 58%,#7abf72 0 10%,transparent 11%),radial-gradient(circle at 45% 62%,#f0d07b 0 10%,transparent 11%),linear-gradient(135deg,#e7c79e,#fff6de);box-shadow:inset 0 0 0 10px rgba(255,255,255,.35)}.badge{display:inline-flex;align-items:center;gap:6px;background:#fff2c8;color:#795100;border:1px solid #f5d98b;border-radius:999px;padding:7px 11px;font-weight:900;font-size:13px}.section{margin:28px 0}.section-head{display:flex;justify-content:space-between;align-items:end;gap:16px;margin-bottom:14px}.grid{display:grid;gap:16px}.grid.cards{grid-template-columns:repeat(3,1fr)}.grid.two{grid-template-columns:1fr 1fr}.grid.four{grid-template-columns:repeat(4,1fr)}.card{background:rgba(255,255,255,.88);border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow-soft);overflow:hidden}.card-body{padding:16px}.offer-img{height:155px;background:linear-gradient(135deg,#f6d599,#fff2d0);position:relative}.offer-img:before{content:'';position:absolute;inset:24px;border-radius:999px;background:radial-gradient(circle at 35% 45%,#cb6d28 0 12%,transparent 13%),radial-gradient(circle at 52% 42%,#f5b339 0 11%,transparent 12%),radial-gradient(circle at 60% 58%,#77bd6f 0 13%,transparent 14%),radial-gradient(circle at 44% 62%,#8fbf61 0 10%,transparent 11%);filter:drop-shadow(0 10px 18px rgba(0,0,0,.1))}.discount{position:absolute;top:12px;left:12px}.price{display:flex;align-items:baseline;gap:8px;margin-top:10px}.price strong{font-size:22px;color:var(--green)}.price del{color:#8a8f89}.meta{display:grid;gap:8px;margin:12px 0;color:#506b61;font-size:14px}.chip{display:inline-flex;align-items:center;gap:6px;border-radius:999px;background:#eef8f1;color:var(--green);padding:8px 11px;font-weight:800;font-size:13px}.layout{display:grid;grid-template-columns:250px 1fr;gap:20px}.sidebar{background:linear-gradient(180deg,var(--green),#073024);border-radius:26px;padding:18px;color:white;min-height:680px;box-shadow:var(--shadow)}.side-link{display:flex;gap:10px;padding:12px;border-radius:14px;color:#d9f4e8;font-weight:800;margin:4px 0}.side-link.active,.side-link:hover{background:rgba(255,255,255,.14)}.detail{background:#fffdf8;border:1px solid var(--line);border-radius:24px;padding:20px}.status{border-radius:999px;padding:6px 9px;font-size:12px;font-weight:900;white-space:nowrap}.paid{background:#ddf6e7;color:#11623e}.due{background:#ffe2d9;color:#b13d2f}.part{background:#fff0c8;color:#815400}.bottom-bar{background:linear-gradient(90deg,var(--green),#0b513b);color:white;border-radius:22px;padding:20px 26px;display:grid;grid-template-columns:repeat(4,1fr);gap:18px;box-shadow:var(--shadow);margin:28px 0}.bottom-bar div{border-right:1px solid rgba(255,255,255,.2);font-weight:900}.bottom-bar div:last-child{border-right:0}.muted{color:var(--muted)}.mini{font-size:13px;color:var(--muted)}.status-title{display:flex;align-items:center;justify-content:space-between;gap:10px}.hero-mini{display:grid;grid-template-columns:1fr 320px;gap:18px}.pillnav{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}.pillnav span{background:white;border:1px solid var(--line);border-radius:999px;padding:9px 12px;font-weight:800;color:var(--green)}.avatar{width:42px;height:42px;border-radius:50%;background:var(--mint);color:white;display:grid;place-items:center;font-weight:900}@media(max-width:900px){.hero,.grid.cards,.grid.two,.grid.four,.layout,.hero-mini{grid-template-columns:1fr}.sidebar{min-height:auto}.stats{grid-template-columns:repeat(2,1fr)}h1{font-size:42px}.bottom-bar{grid-template-columns:1fr}.bottom-bar div{border-right:0;border-bottom:1px solid rgba(255,255,255,.2);padding-bottom:12px}.nav-inner{align-items:flex-start;flex-direction:column}.wrap{padding:16px}}
"""
CSS += """
.brand-logo{width:56px;height:56px;display:block;object-fit:contain;filter:drop-shadow(0 10px 20px rgba(15,61,46,.16))}.brand-title{font-size:28px}.nav{box-shadow:0 8px 28px rgba(15,61,46,.06)}.nav-links a.btn{color:#fff}.nav-links a.btn.secondary{color:var(--green)}.app-footer{max-width:1240px;margin:20px auto 34px;padding:0 24px}.motto-panel{position:relative;overflow:hidden;background:linear-gradient(100deg,#0f3d2e,#14533d 62%,#246f55);color:white;border-radius:28px;padding:24px 26px 26px;box-shadow:var(--shadow)}.motto-panel:before{content:"";position:absolute;width:260px;height:260px;border-radius:50%;left:-90px;bottom:-150px;background:rgba(242,177,61,.18)}.motto-panel:after{content:"";position:absolute;width:240px;height:240px;border-radius:50%;right:-64px;top:-84px;background:rgba(174,232,201,.16)}.motto-brand{position:relative;z-index:1;display:flex;align-items:center;gap:14px;margin-bottom:20px}.motto-brand img{width:62px;height:62px;background:rgba(255,255,255,.12);border-radius:22px;padding:7px}.motto-title{font-weight:950;font-size:28px;line-height:1.05}.motto-sub{font-size:14px;color:#f0fff8;font-weight:900;margin-top:8px}.motto-grid{position:relative;z-index:1;display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.motto-item{background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.11);border-radius:20px;padding:18px 18px 20px;font-weight:950;line-height:1.25;min-height:126px}.motto-icon{font-size:26px;margin-bottom:8px}.motto-item small{display:block;margin-top:10px;color:#cfe5db;font-weight:800;line-height:1.5}.gps-panel{display:grid;grid-template-columns:1fr 1.15fr;gap:18px;align-items:stretch}.map-card{min-height:360px;border-radius:30px;border:1px solid var(--line);box-shadow:var(--shadow);overflow:hidden;background:#edf7ee;position:relative}.map-canvas{position:absolute;inset:0;background:linear-gradient(135deg,rgba(174,232,201,.5),rgba(255,250,240,.88)),repeating-linear-gradient(35deg,rgba(15,61,46,.08) 0 2px,transparent 2px 58px),repeating-linear-gradient(125deg,rgba(79,191,159,.16) 0 3px,transparent 3px 70px)}.map-road{position:absolute;background:#fff8e8;border:1px solid rgba(15,61,46,.08);box-shadow:0 6px 18px rgba(15,61,46,.08)}.road-a{width:120%;height:38px;left:-10%;top:45%;transform:rotate(-13deg)}.road-b{width:42px;height:120%;left:58%;top:-10%;transform:rotate(8deg)}.road-c{width:80%;height:30px;left:8%;top:68%;transform:rotate(20deg)}.pin{position:absolute;transform:translate(-50%,-100%);display:grid;place-items:center;width:44px;height:44px;border-radius:999px 999px 999px 10px;background:var(--green);color:white;font-weight:950;box-shadow:0 14px 24px rgba(15,61,46,.25);rotate:-45deg}.pin span{rotate:45deg}.pin.one{left:24%;top:40%}.pin.two{left:63%;top:34%;background:var(--mint)}.pin.three{left:76%;top:72%;background:var(--yellow);color:#3b2b04}.map-info{position:absolute;left:18px;right:18px;bottom:18px;background:rgba(255,255,255,.92);border:1px solid var(--line);border-radius:20px;padding:14px;display:grid;grid-template-columns:1fr auto;gap:10px;align-items:center}.gps-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:16px}.location-list{display:grid;gap:12px;margin-top:16px}.location-row{display:grid;grid-template-columns:42px 1fr auto;gap:12px;align-items:center;background:#fffdf8;border:1px solid var(--line);border-radius:16px;padding:12px}.location-row b{display:block;color:var(--green)}.location-row small{color:var(--muted);font-weight:700}.bottom-bar{display:none}.page-spacer{min-height:16px}@media(max-width:1000px){.motto-grid{grid-template-columns:1fr 1fr}.gps-panel{grid-template-columns:1fr}}@media(max-width:640px){.brand-title{font-size:24px}.brand-logo{width:50px;height:50px}.motto-grid{grid-template-columns:1fr}.motto-title{font-size:24px}.app-footer{padding:0 16px}.map-info{grid-template-columns:1fr}.searchbar{flex-direction:column}.searchbar input{width:100%}}
"""
CSS += """
.live-map{position:absolute;inset:0;width:100%;height:100%;border:0;z-index:0;filter:saturate(.92) contrast(.96)}.map-card .map-canvas,.map-card .map-road{display:none}.map-card .pin{z-index:2}.map-card .map-info{z-index:3}.map-status{font-size:13px;color:var(--muted);font-weight:800;margin-top:10px}
"""
CSS += """
.legal-text h2{margin-top:18px}.legal-text h2:first-child{margin-top:0}.trust-list{display:grid;gap:12px}.trust-row{display:grid;grid-template-columns:44px 1fr;gap:12px;align-items:start;background:#fffdf8;border:1px solid var(--line);border-radius:18px;padding:14px}.support-form textarea{resize:vertical;min-height:130px}.wide-field{grid-column:1/-1}.form-result{background:#fffdf8;border:1px solid var(--line);border-radius:16px;padding:14px;color:var(--green);font-weight:800;white-space:pre-wrap}
"""
CSS += """
.ops-list{display:grid;gap:12px}.ops-row{background:#fffdf8;border:1px solid var(--line);border-radius:18px;padding:14px;display:grid;grid-template-columns:1fr auto;gap:12px;align-items:center}.ops-row small{display:block;color:var(--muted);font-weight:700}.ops-code{font-size:18px;color:var(--green);font-weight:950}.ops-actions{display:flex;gap:8px;flex-wrap:wrap}.ops-kpi b{font-size:26px}.compact-input{width:100%;border:1px solid #eadfce;background:#fffdf8;border-radius:14px;padding:12px 13px;color:#233e36}
"""
CSS += """
.ai-home{margin-top:22px;background:white;border:1px solid var(--line);border-radius:22px;padding:14px;box-shadow:var(--shadow-soft);display:grid;gap:10px}.ai-home textarea{width:100%;min-height:84px;resize:vertical;border:1px solid #eadfce;background:#fffdf8;border-radius:16px;padding:14px;color:#233e36;font:inherit;line-height:1.45}.ai-home-actions{display:flex;gap:10px;flex-wrap:wrap;align-items:center}.ai-chip{border:1px solid #d8eadf;background:#f4fbf7;color:var(--green);border-radius:999px;padding:8px 11px;font-weight:900;cursor:pointer}.ai-result{display:none;background:#f8fbf7;border:1px solid #dceee4;border-radius:16px;padding:14px;white-space:pre-wrap;color:#21473c;font-weight:750;line-height:1.5}.ai-result.show{display:block}.ai-products{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.ai-product{display:block;background:#fffdf8;border:1px solid var(--line);border-radius:14px;padding:12px;font-weight:900}.ai-product small{display:block;color:var(--muted);font-weight:800;margin-top:4px}.category-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}.category-button{background:rgba(255,255,255,.9);border:1px solid var(--line);border-radius:22px;padding:18px 16px;box-shadow:var(--shadow-soft);display:grid;gap:8px;min-height:146px;transition:transform .15s ease,box-shadow .15s ease,border-color .15s ease}.category-button:hover{transform:translateY(-2px);box-shadow:var(--shadow);border-color:#b8dec8}.category-icon{font-size:48px;line-height:1}.category-button b{font-size:24px;color:var(--green);display:block}.category-button span{color:var(--muted);font-weight:850}.app-footer{margin:14px auto 22px}.motto-panel{border-radius:20px;padding:12px 16px 14px}.motto-panel:before{width:150px;height:150px;left:-70px;bottom:-95px}.motto-panel:after{width:150px;height:150px;right:-45px;top:-58px}.motto-brand{gap:10px;margin-bottom:10px}.motto-brand img{width:38px;height:38px;border-radius:14px;padding:4px}.motto-title{font-size:20px}.motto-sub{font-size:11px;margin-top:3px}.motto-grid{gap:8px}.motto-item{border-radius:14px;padding:9px 11px;min-height:64px;font-size:13px;line-height:1.18}.motto-icon{font-size:18px;margin-bottom:3px}.motto-item small{margin-top:4px;font-size:10px;line-height:1.25}@media(max-width:900px){.ai-products,.category-grid{grid-template-columns:1fr 1fr}}@media(max-width:640px){.category-grid{grid-template-columns:1fr 1fr}.category-button{min-height:128px}.category-icon{font-size:40px}.category-button b{font-size:20px}.motto-grid{grid-template-columns:1fr 1fr}.motto-item small{display:none}}
"""

def logo():
    return """<a class='brand' href='/pocetna'><img class='brand-logo' src='/admin-assets/brand/logo-mark.svg' alt='Sačuvaj Hranu'><div><div class='brand-title'>Sačuvaj <span>Hranu</span></div><div class='brand-sub'>Uštedi novac. Sačuvaj obrok. Smanji bacanje.</div></div></a>"""

def nav(active="pocetna"):
    items=[("pocetna","/pocetna","Početna"),("ponude","/ponude","Ponude"),("rezervacije","/moje-rezervacije","Rezervacije"),("partner","/partner/kontrolna-tabla","Partneri"),("finansije","/admin/finance-console","Finansije"),("dizajn","/dizajn-sistem","Dizajn sistem")]
    links="".join([f"<a class='{ 'active' if k==active else '' }' href='{href}'>{label}</a>" for k,href,label in items])
    return f"<div class='nav'><div class='nav-inner'>{logo()}<div class='nav-links'>{links}<a class='btn secondary' href='/profil'>Profil</a><a class='btn secondary' href='/ponude'>Pronađi obrok</a></div></div></div>"

def footer():
    return f"""<footer class='app-footer'><section class='motto-panel'><div class='motto-brand'><img src='/admin-assets/brand/logo-mark.svg' alt='Sačuvaj Hranu'><div><div class='motto-title'>Sačuvaj Hranu</div><div class='motto-sub'>Naše obećanje za svaku rezervaciju · <a href='mailto:{SUPPORT_EMAIL}'>{SUPPORT_EMAIL}</a></div></div></div><div class='motto-grid'><div class='motto-item'><div class='motto-icon'>🛡️</div>Proverene prodavnice i restorani<small>Partneri i ponude prolaze pregled pre prikaza.</small></div><div class='motto-item'><div class='motto-icon'>🔒</div>Sigurne rezervacije i plaćanja<small>Jasan tok rezervacije, QR potvrda i plaćanje pri preuzimanju.</small></div><div class='motto-item'><div class='motto-icon'>🤝</div>Zajednica koja pravi razliku<small>Kupci, partneri i grad zajedno smanjuju bacanje hrane.</small></div><div class='motto-item'><div class='motto-icon'>🍃</div>Za bolju budućnost bez bacanja hrane<small>Svaki spašen obrok je mali korak ka boljem sistemu.</small></div></div></section></footer>"""

def page(title, body, active="pocetna"):
    pwa_head = """<link rel='manifest' href='/admin-assets/manifest.webmanifest'><meta name='theme-color' content='#0f3d2e'><meta name='apple-mobile-web-app-capable' content='yes'><meta name='apple-mobile-web-app-title' content='Sačuvaj Hranu'><link rel='apple-touch-icon' href='/admin-assets/icons/icon-192.png'>"""
    pwa_script = """<script>if('serviceWorker' in navigator){window.addEventListener('load',function(){navigator.serviceWorker.register('/sw.js').catch(function(){});});}</script>"""
    html=f"""<!doctype html><html lang='sr'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'><title>{title} — Sačuvaj Hranu</title>{pwa_head}<style>{CSS}</style></head><body>{nav(active)}<main class='wrap'>{body}</main>{footer()}{pwa_script}</body></html>"""
    return HTMLResponse(html, headers={"Cache-Control":"no-store, max-age=0"})

def offer_card(title="Domaći ručak", seller="Restoran Zeleno", price="360 RSD", old="600 RSD", badge="-40%", product_id=None, pickup="18:30 – 19:00", address="Vojvode Stepe 123, Beograd"):
    action = f"<a class='btn' style='margin-top:12px;width:100%' href='/rezervisi/{product_id}'>Rezerviši</a>" if product_id else ""
    return f"""<article class='card'><div class='offer-img'><span class='badge discount'>{badge}</span></div><div class='card-body'><div class='status-title'><h3>{title}</h3><span>♡</span></div><div class='mini'>{seller}</div><div class='meta'><span>⏱ Preuzimanje {pickup}</span><span>📍 {address}</span></div><div class='price'><strong>{price}</strong><del>{old}</del></div>{action}</div></article>"""

def product_offer_card(db: Session, product: models.Product):
    old = f"{int(product.original_price or 0)} {product.currency or 'RSD'}"
    price = f"{int(product.discounted_price or product.original_price or 0)} {product.currency or 'RSD'}"
    discount = int(product.discount_percent or 0)
    badge = f"-{discount}%" if discount else "Ponuda"
    store = product.store.name if product.store else "Sačuvaj Hranu partner"
    address = product.store.address if product.store and product.store.address else "Beograd"
    available = product_available_quantity(db, product)
    pickup = product.pickup_window or "Danas"
    card = offer_card(product.name, store, price, old, badge, product.id, pickup, address)
    if available is not None:
        card = card.replace("</div></article>", f"<div class='mini' style='margin-top:10px'>Dostupno: {available}</div></div></article>")
    return card

def live_map_script():
    return """<script>
function useLiveLocation(){
  var s=document.getElementById('mapStatus');
  var f=document.getElementById('liveMap');
  var title=document.getElementById('mapTitle');
  var sub=document.getElementById('mapSubtitle');
  if(!navigator.geolocation){
    if(s) s.textContent='Browser ne podržava GPS lokaciju.';
    return;
  }
  if(s) s.textContent='Tražim tvoju lokaciju...';
  navigator.geolocation.getCurrentPosition(function(pos){
    var lat=pos.coords.latitude;
    var lon=pos.coords.longitude;
    var d=0.035;
    var bbox=(lon-d).toFixed(5)+'%2C'+(lat-d).toFixed(5)+'%2C'+(lon+d).toFixed(5)+'%2C'+(lat+d).toFixed(5);
    f.src='https://www.openstreetmap.org/export/embed.html?bbox='+bbox+'&layer=mapnik&marker='+lat.toFixed(5)+'%2C'+lon.toFixed(5);
    if(title) title.textContent='Tvoja lokacija • ponude u blizini';
    if(sub) sub.textContent='Mapa je pomerena na tvoju GPS poziciju';
    if(s) s.textContent='GPS lokacija učitana. Mapu možeš da pomeraš i zumiraš.';
  }, function(){
    if(s) s.textContent='Nismo dobili GPS dozvolu. Prikazujemo Beograd kao početnu lokaciju.';
  }, {enableHighAccuracy:true,timeout:8000,maximumAge:60000});
}
</script>"""

def home_ai_script():
    return """<script>
function escapeHomeAiHtml(value){
  return String(value == null ? '' : value).replace(/[&<>"']/g, function(ch){
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch];
  });
}
function setAiPrompt(text){
  var input = document.getElementById('aiQuestion');
  if(input){ input.value = text; }
  askHomeAi();
}
function aiProductHtml(product){
  var name = product.name || 'Ponuda';
  var store = product.store_name || 'Sačuvaj Hranu partner';
  var price = product.discounted_price || product.price || product.original_price || '';
  var href = product.id ? '/rezervisi/' + encodeURIComponent(product.id) : '/ponude';
  var meta = store + (price ? ' • ' + Math.round(Number(price)) + ' RSD' : '');
  return '<a class="ai-product" href="' + href + '">' + escapeHomeAiHtml(name) + '<small>' + escapeHomeAiHtml(meta) + '</small></a>';
}
async function askHomeAi(){
  var input = document.getElementById('aiQuestion');
  var city = document.getElementById('aiCity');
  var result = document.getElementById('aiResult');
  var products = document.getElementById('aiProducts');
  var message = (input && input.value ? input.value : '').trim();
  if(!message){
    result.className = 'ai-result show';
    result.textContent = 'Napiši šta tražiš, na primer: ručak do 400 RSD ili pekara blizu mene.';
    return;
  }
  result.className = 'ai-result show';
  result.textContent = 'AI traži najbolje ponude...';
  products.innerHTML = '';
  try{
    var response = await fetch('/buyer-ai/home-assistant', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({message:message, city:(city && city.value ? city.value : 'Beograd'), limit:6})
    });
    var data = await response.json();
    if(!response.ok){ throw new Error(data.detail || 'AI trenutno nije dostupan'); }
    result.textContent = data.reply || 'Nema odgovora za ovaj upit.';
    products.innerHTML = (data.products || []).slice(0,4).map(aiProductHtml).join('');
  }catch(error){
    result.textContent = 'AI trenutno ne može da odgovori. Otvori sve ponude ili probaj šire pitanje.';
  }
}
</script>"""

@router.get("/", response_class=HTMLResponse)
def root_page():
    return home_page()

@router.get("/offline", response_class=HTMLResponse)
def offline_page():
    body="""<section class='detail'><span class='badge'>Offline režim</span><h1 style='font-size:42px'>Nema internet veze</h1><p class='lead'>Aplikacija je sačuvala osnovne stranice. Kada se veza vrati, ponude, rezervacije i mapa će se ponovo osvežiti.</p><div class='gps-actions'><a class='btn' href='/pocetna'>Početna</a><a class='btn secondary' href='/ponude'>Ponude</a><a class='btn secondary' href='/partner/preuzimanje'>Partner preuzimanje</a></div></section>"""
    return page("Offline", body, "pocetna")

@router.get("/pocetna", response_class=HTMLResponse)
def home_page():
    body=f"""
    <section class='hero'><div class='hero-card'><span class='badge'>🌱 Spasi obrok danas</span><h1>Uštedi novac.<br>Sačuvaj obrok.<br><span>Smanji bacanje.</span></h1><p class='lead'>Pronađi odlične obroke po nižim cenama iz restorana, pekara i prodavnica u tvom kraju. Rezerviši za nekoliko sekundi i preuzmi u dogovorenom terminu.</p><div class='ai-home'><textarea id='aiQuestion' placeholder='Pitaj AI pomoćnika: pecivo do 200 din u Beogradu, ručak blizu mene, najveći popusti danas...'>Šta ima danas blizu mene do 400 RSD?</textarea><div class='ai-home-actions'><input class='field' id='aiCity' value='Beograd' style='max-width:170px' placeholder='Grad'><button class='btn' type='button' onclick='askHomeAi()'>Pitaj AI</button><button class='ai-chip' type='button' onclick="setAiPrompt('Pekara do 200 din u Beogradu')">Pekara do 200</button><button class='ai-chip' type='button' onclick="setAiPrompt('Najveći popusti danas')">Najveći popusti</button></div><div id='aiResult' class='ai-result'>Napiši šta tražiš i AI će predložiti ponude.</div><div id='aiProducts' class='ai-products'></div></div><div class='stats'><div class='stat'><b>10.000+</b><span>spašenih obroka</span></div><div class='stat'><b>200+</b><span>partnera</span></div><div class='stat'><b>50.000+</b><span>zadovoljnih korisnika</span></div><div class='stat'><b>12</b><span>gradova u Srbiji</span></div></div></div><div class='visual'><div class='food-img'></div><h2>Domaći ručak danas</h2><p class='muted'>Rezervisano u tvom kraju • Ušteda do 40%</p><a class='btn' href='/ponude'>Pogledaj ponude</a></div></section>
    <section class='section gps-panel'><div class='detail'><span class='badge'>GPS ponude u blizini</span><h2>Mapa obroka oko tebe</h2><p class='lead'>Na početnoj strani kupac odmah vidi gde se nalaze najbliže ponude. Mapa je uživo: možeš da je pomeraš, zumiraš i prebaciš na svoju lokaciju.</p><div class='gps-actions'><button class='btn' type='button' onclick='useLiveLocation()'>Koristi moju lokaciju</button><a class='btn secondary' href='/ponude'>Otvori sve ponude</a></div><div id='mapStatus' class='map-status'>Mapa prikazuje aktivne demo partnere u Beogradu.</div><div class='location-list'><div class='location-row'><span class='chip'>1</span><div><b>Restoran Zeleno</b><small>1,2 km • domaći ručak • 360 RSD</small></div><span class='status paid'>-40%</span></div><div class='location-row'><span class='chip'>2</span><div><b>Picerija Napoli</b><small>1,8 km • pizza parče • 280 RSD</small></div><span class='status part'>-30%</span></div><div class='location-row'><span class='chip'>3</span><div><b>Pekara Hleb i Kvasac</b><small>2,4 km • pekarski miks • 150 RSD</small></div><span class='status due'>-25%</span></div></div></div><div class='map-card' aria-label='GPS mapa ponuda'><iframe id='liveMap' class='live-map' title='Mapa ponuda uživo' loading='lazy' referrerpolicy='no-referrer-when-downgrade' src='https://www.openstreetmap.org/export/embed.html?bbox=20.405%2C44.765%2C20.525%2C44.845&amp;layer=mapnik'></iframe><div class='map-info'><div><b id='mapTitle'>Beograd • ponude u krugu od 3 km</b><br><span class='muted' id='mapSubtitle'>3 partnera dostupna za preuzimanje danas</span></div><a class='btn' href='/ponude'>Prikaži na listi</a></div></div></section>{live_map_script()}{home_ai_script()}
    <section class='section'><div class='section-head'><h2>Istraži ponude po kategorijama</h2><a class='chip' href='/ponude'>Prikaži sve</a></div><div class='category-grid'><a class='category-button' href='/ponude?category=restoran'><span class='category-icon'>🍽</span><b>Restorani</b><span>Domaći obroci</span></a><a class='category-button' href='/ponude?category=market'><span class='category-icon'>🛒</span><b>Prodavnice</b><span>Paketi namirnica</span></a><a class='category-button' href='/ponude?category=pekara'><span class='category-icon'>🥐</span><b>Pekare</b><span>Peciva i hleb</span></a><a class='category-button' href='/ponude?category=kafa'><span class='category-icon'>☕</span><b>Kafići</b><span>Piće i deserti</span></a></div></section>
    <section class='section'><div class='section-head'><h2>Izdvojene ponude</h2><a class='chip' href='/ponude'>Pogledaj sve ponude</a></div><div class='grid cards'>{offer_card()}{offer_card('Pizza parče','Picerija Napoli','280 RSD','400 RSD','-30%')}{offer_card('Pekarski miks','Pekara Hleb i Kvasac','150 RSD','200 RSD','-25%')}</div></section>"""
    return page("Početna", body, "pocetna")

@router.get("/ponude", response_class=HTMLResponse)
def listing_page(category: str | None = Query(default=None), db: Session = Depends(get_db)):
    category = (category or "").strip().lower()
    category_labels = {
        "restoran": "Restorani",
        "market": "Prodavnice",
        "prodavnica": "Prodavnice",
        "pekara": "Pekare",
        "kafa": "Kafići",
    }
    category_aliases = {
        "restoran": ["restoran", "gotova jela", "ručak", "rucak"],
        "market": ["market", "prodavnica", "namirnice"],
        "prodavnica": ["market", "prodavnica", "namirnice"],
        "pekara": ["pekara", "pecivo", "hleb", "kroasan"],
        "kafa": ["kafa", "doručak", "dorucak", "pića", "pica", "poslastice"],
    }
    query = db.query(models.Product).outerjoin(models.Store).filter(
        models.Product.status.in_(list(VISIBLE_STATUSES))
    )
    if category:
        category_filter = None
        for alias in category_aliases.get(category, [category]):
            needle = f"%{alias}%"
            clause = or_(models.Product.category.ilike(needle), models.Product.name.ilike(needle), models.Store.name.ilike(needle))
            category_filter = clause if category_filter is None else or_(category_filter, clause)
        query = query.filter(category_filter)
    products = query.order_by(models.Product.updated_at.desc()).limit(12).all()
    cards = "".join(product_offer_card(db, product) for product in products)
    if not cards:
        cards="".join([offer_card(),offer_card('Supa + hleb','Kuhinja Doma','210 RSD','300 RSD','-30%'),offer_card('Voćna salata','Zeleni Kutak','150 RSD','200 RSD','-25%'),offer_card('Pekarski miks','Pekara Hleb i Kvasac','105 RSD','150 RSD','-30%')])
    heading = category_labels.get(category, "Ponude u tvojoj blizini") if category else "Ponude u tvojoj blizini"
    count_label = f"{len(products)} ponuda pronađeno" if products else "Prikazujemo preporučene ponude"
    selected = {
        "restoran": "Restorani",
        "market": "Prodavnice",
        "pekara": "Pekare",
        "kafa": "Kafići",
    }.get(category, "Sve kategorije")
    body=f"""<div class='section-head'><div><h1 style='font-size:42px'>{heading}</h1><p class='lead'>Filtriraj po lokaciji, vremenu preuzimanja, kategoriji i popustu.</p></div><a class='btn' href='/ponude/1'>Probaj detalj ponude</a></div><div class='layout'><aside class='card' style='padding:18px'><h3>Filteri</h3><div class='grid'><input class='field' value='Beograd'><select class='field' onchange="if(this.value) location.href=this.value"><option>{selected}</option><option value='/ponude'>Sve kategorije</option><option value='/ponude?category=restoran'>Restorani</option><option value='/ponude?category=market'>Prodavnice</option><option value='/ponude?category=pekara'>Pekare</option><option value='/ponude?category=kafa'>Kafići</option></select><select class='field'><option>Danas</option><option>Sutra</option></select><label class='chip'><input type='checkbox'> Samo dostupno</label><label class='chip'><input type='checkbox'> Omiljeni partneri</label><a class='btn' href='/ponude'>Resetuj filtere</a></div></aside><section><div class='section-head'><h2>{count_label}</h2><span class='chip'>Sortiranje: Najnovije</span></div><div class='grid two'>{cards}</div><p style='text-align:center'><a class='btn secondary' href='/ponude'>Učitaj sve</a></p></section></div>"""
    return page("Ponude", body, "ponude")

@router.get("/rezervisi/{product_id}", response_class=HTMLResponse)
def reserve_product_page(product_id: int, db: Session = Depends(get_db)):
    product = db.get(models.Product, product_id)
    if not product:
        return page("Rezervacija", "<section class='detail'><h1 style='font-size:42px'>Ponuda nije pronađena</h1><p class='lead'>Vrati se na listu ponuda i izaberi drugu dostupnu ponudu.</p><a class='btn' href='/ponude'>Nazad na ponude</a></section>", "ponude")
    available = product_available_quantity(db, product)
    store = product.store.name if product.store else "Sačuvaj Hranu partner"
    address = product.store.address if product.store and product.store.address else "Beograd"
    price = int(product.discounted_price or product.original_price or 0)
    old = int(product.original_price or price)
    body=f"""<section class='hero-mini'><div class='detail'><span class='badge'>Rezervacija ponude</span><h1 style='font-size:42px'>{product.name}</h1><p class='lead'>{store}<br>{address}</p><div class='grid two'><div class='stat'><b>{price} RSD</b><span>cena za preuzimanje</span></div><div class='stat'><b>{old} RSD</b><span>redovna cena</span></div><div class='stat'><b>{available if available is not None else 'Dostupno'}</b><span>preostala količina</span></div><div class='stat'><b>{product.pickup_window or 'Danas'}</b><span>vreme preuzimanja</span></div></div></div><aside class='detail'><h2>Podaci kupca</h2><div class='grid'><input class='field' id='customerName' value='Pilot Kupac' placeholder='Ime i prezime'><input class='field' id='customerPhone' value='+38160111000' placeholder='Telefon'><input class='field' id='customerEmail' value='pilot@sacuvaj-hranu.local' placeholder='Email'><input class='field' id='quantity' type='number' min='1' value='1'><button class='btn' type='button' onclick='reserveNow()'>Potvrdi rezervaciju</button><button class='btn secondary' id='pickupBtn' type='button' onclick='payOnPickup()' disabled>Plati pri preuzimanju</button><button class='btn secondary' id='demoPayBtn' type='button' onclick='demoPay()' disabled>Demo online plaćanje</button><div id='reserveStatus' class='map-status'>Rezervacija još nije poslata.</div></div></aside></section><script>
let reservationCode = null;
async function reserveNow(){{
  const payload = {{product_id:{product.id}, customer_name:document.getElementById('customerName').value, customer_phone:document.getElementById('customerPhone').value, customer_email:document.getElementById('customerEmail').value, quantity:Number(document.getElementById('quantity').value || 1)}};
  const s = document.getElementById('reserveStatus');
  s.textContent = 'Šaljem rezervaciju...';
  const r = await fetch('/reservations', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify(payload)}});
  const data = await r.json();
  if(!r.ok){{ s.textContent = data.detail || 'Rezervacija nije uspela.'; return; }}
  reservationCode = data.reservation_code;
  document.getElementById('pickupBtn').disabled = false;
  document.getElementById('demoPayBtn').disabled = false;
  s.innerHTML = 'Rezervacija je kreirana: <b>'+reservationCode+'</b><br><a class="chip" href="/reservation?code='+reservationCode+'">Digitalna karta</a> <a class="chip" href="/qr/reservation/'+reservationCode+'.svg">QR potvrda</a> <a class="chip" href="/moje-rezervacije">Moje rezervacije</a>';
}}
async function payOnPickup(){{
  if(!reservationCode) return;
  const phone = document.getElementById('customerPhone').value;
  const r = await fetch('/payments/reservations/'+reservationCode+'/pay-on-pickup', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{customer_phone:phone,payment_method:'pay_on_pickup'}})}});
  const data = await r.json();
  document.getElementById('reserveStatus').innerHTML = r.ok ? 'Potvrđeno plaćanje pri preuzimanju. Status: <b>'+data.status+'</b>' : (data.detail || 'Greška pri potvrdi.');
}}
async function demoPay(){{
  if(!reservationCode) return;
  const phone = document.getElementById('customerPhone').value;
  const r = await fetch('/payments/reservations/'+reservationCode+'/pay', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:JSON.stringify({{customer_phone:phone,payment_method:'pilot_demo_card'}})}});
  const data = await r.json();
  document.getElementById('reserveStatus').innerHTML = r.ok ? 'Demo plaćanje završeno. Kod: <b>'+data.reservation_code+'</b>' : (data.detail || 'Greška pri plaćanju.');
}}
</script>"""
    return page("Rezerviši", body, "ponude")

@router.get("/reservation", response_class=HTMLResponse)
def reservation_ticket_legacy(code: str | None = Query(default=None), db: Session = Depends(get_db)):
    return reservation_ticket_page(code or "", db)

@router.get("/rezervacija/{reservation_code}", response_class=HTMLResponse)
def reservation_ticket_by_path(reservation_code: str, db: Session = Depends(get_db)):
    return reservation_ticket_page(reservation_code, db)

def reservation_ticket_page(reservation_code: str, db: Session):
    reservation = db.query(models.Reservation).filter(
        models.Reservation.reservation_code == reservation_code.strip().upper()
    ).first()
    if not reservation:
        body = """<section class='detail'><span class='badge'>Digitalna karta</span><h1 style='font-size:42px'>Unesi kod rezervacije</h1><p class='lead'>Ako si otvorio QR ili link iz potvrde, kod će se učitati automatski. Možeš ga uneti i ručno.</p><div class='searchbar'><input id='ticketCode' placeholder='Kod rezervacije'><button class='btn' onclick='openTicket()'>Otvori</button></div></section><script>function openTicket(){var c=document.getElementById('ticketCode').value.trim().toUpperCase(); if(c) location.href='/reservation?code='+encodeURIComponent(c);}</script>"""
        return page("Digitalna karta", body, "rezervacije")
    product = reservation.product
    store = product.store if product else None
    status_labels = {"pending":"Čeka potvrdu","confirmed":"Potvrđeno","picked_up":"Preuzeto","cancelled":"Otkazano","expired":"Isteklo"}
    payment_labels = {"unpaid":"Nije plaćeno","pay_on_pickup":"Plaćanje pri preuzimanju","paid":"Plaćeno","payment_pending":"Plaćanje u toku","refunded":"Refundirano"}
    store_id = store.id if store else ""
    body=f"""<section class='hero-mini'><div class='detail'><span class='badge'>Digitalna karta</span><h1 style='font-size:42px'>{reservation.reservation_code}</h1><p class='lead'>{reservation.product.name if reservation.product else 'Rezervacija'}<br>{store.name if store else 'Sačuvaj Hranu partner'}</p><div class='grid two'><div class='stat'><b>{status_labels.get(reservation.status, reservation.status)}</b><span>status rezervacije</span></div><div class='stat'><b>{payment_labels.get(reservation.payment_status, reservation.payment_status)}</b><span>plaćanje</span></div><div class='stat'><b>{int(reservation.payable_amount or 0)} RSD</b><span>za plaćanje</span></div><div class='stat'><b>{reservation.quantity}</b><span>količina</span></div></div><p class='muted'>Kupac: {reservation.customer_name} • {reservation.customer_phone}</p><div class='gps-actions'><a class='btn' href='/qr/reservation/{reservation.reservation_code}.svg'>Otvori QR</a><a class='btn secondary' href='/payments/reservations/{reservation.reservation_code}/checkout'>Checkout API</a><a class='btn secondary' href='/ponude'>Nazad na ponude</a></div></div><aside class='detail'><h2>Partner potvrda</h2><p class='muted'>Partner unosi svoj PIN i potvrđuje preuzimanje kada kupac pokaže kod ili QR.</p><div class='grid'><input class='field' id='storeId' value='{store_id}' placeholder='ID partnera'><input class='field' id='pin' value='111111' placeholder='PIN partnera'><input class='field' id='code' value='{reservation.reservation_code}' placeholder='Kod rezervacije'><button class='btn' type='button' onclick='confirmPickup()'>Potvrdi preuzimanje</button><div id='pickupStatus' class='map-status'>Spremno za proveru kod partnera.</div></div></aside></section><script>
async function confirmPickup(){{
  const payload={{store_id:Number(document.getElementById('storeId').value),pin:document.getElementById('pin').value,reservation_code:document.getElementById('code').value}};
  const s=document.getElementById('pickupStatus');
  s.textContent='Proveravam kod...';
  const r=await fetch('/pilot-live/confirm-pickup',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(payload)}});
  const data=await r.json();
  if(!r.ok){{s.textContent=data.detail||'Potvrda nije uspela.';return;}}
  s.innerHTML='Preuzimanje potvrđeno. Status: <b>'+data.reservation.status+'</b><br><a class="chip" href="/pilot-live/daily-report">Dnevni izveštaj</a>';
}}
</script>"""
    return page("Digitalna karta", body, "rezervacije")

@router.get("/partner/preuzimanje", response_class=HTMLResponse)
def partner_pickup_page():
    body="""<section class='detail'><span class='badge'>Partner PIN potvrda</span><h1 style='font-size:42px'>Potvrdi preuzimanje</h1><p class='lead'>Kada kupac pokaže QR ili kod rezervacije, partner unosi ID prodavnice, PIN i kod. Sistem odmah beleži preuzimanje i finansijski status.</p><div class='grid two'><input class='field' id='storeId' placeholder='ID partnera'><input class='field' id='pin' placeholder='PIN'><input class='field' id='code' placeholder='Kod rezervacije'><button class='btn' type='button' onclick='confirmPickup()'>Potvrdi</button></div><div id='pickupStatus' class='map-status'>Čeka unos.</div></section><script>
async function confirmPickup(){
  const payload={store_id:Number(document.getElementById('storeId').value),pin:document.getElementById('pin').value,reservation_code:document.getElementById('code').value};
  const s=document.getElementById('pickupStatus');
  s.textContent='Proveravam...';
  const r=await fetch('/pilot-live/confirm-pickup',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  const data=await r.json();
  s.innerHTML=r.ok?'Preuzimanje potvrđeno za kod <b>'+data.reservation.reservation_code+'</b>.':(data.detail||'Greška.');
}
</script>"""
    return page("Partner preuzimanje", body, "partner")

@router.get("/partner/onboarding", response_class=HTMLResponse)
def partner_onboarding_page():
    body="""<section class='hero-mini'><div class='detail'><span class='badge'>Pilot partner onboarding</span><h1 style='font-size:42px'>Uključi lokal za nekoliko minuta</h1><p class='lead'>Za zatvoreni pilot partner odmah dobija ID, PIN i prvu javnu ponudu. Kasnije admin može da uradi dodatnu proveru i finansijski ugovor.</p><div class='grid two'><div class='stat'><b>1</b><span>prijava lokala</span></div><div class='stat'><b>PIN</b><span>ulaz u partner panel</span></div><div class='stat'><b>QR</b><span>potvrda preuzimanja</span></div><div class='stat'><b>25%</b><span>pilot provizija</span></div></div></div><aside class='detail'><h2>Podaci partnera</h2><div class='grid'><input class='field' id='businessName' value='Pilot Lokal Novi' placeholder='Naziv lokala'><select class='field' id='category'><option value='restoran'>Restoran</option><option value='pekara'>Pekara</option><option value='market'>Market</option><option value='voće i povrće'>Voće i povrće</option></select><input class='field' id='city' value='Beograd' placeholder='Grad'><input class='field' id='address' value='Knez Mihailova 10' placeholder='Adresa'><input class='field' id='contactName' value='Partner Kontakt' placeholder='Kontakt osoba'><input class='field' id='phone' value='+38160111666' placeholder='Telefon'><input class='field' id='email' value='partner@sacuvaj.local' placeholder='Email'><input class='field' id='offerName' value='Prva pilot ponuda' placeholder='Naziv prve ponude'><input class='field' id='originalPrice' type='number' value='600' placeholder='Stara cena'><input class='field' id='discountedPrice' type='number' value='360' placeholder='Nova cena'><input class='field' id='quantity' type='number' value='5' placeholder='Količina'><input class='field' id='pickupWindow' value='18:00 - 19:00' placeholder='Vreme preuzimanja'><button class='btn secondary' type='button' onclick='usePartnerGps()'>Uzmi GPS</button><button class='btn' type='button' onclick='onboardPartner()'>Uključi partnera</button><div id='onboardStatus' class='map-status'>Spremno za unos.</div></div></aside></section><script>
let partnerLat=null, partnerLng=null;
function usePartnerGps(){
  const s=document.getElementById('onboardStatus');
  if(!navigator.geolocation){s.textContent='Browser ne podržava GPS.';return;}
  s.textContent='Tražim GPS lokaciju...';
  navigator.geolocation.getCurrentPosition(function(pos){partnerLat=pos.coords.latitude;partnerLng=pos.coords.longitude;s.textContent='GPS lokacija je učitana.';},function(){s.textContent='GPS dozvola nije data. Može i bez GPS-a za prvi unos.';});
}
async function onboardPartner(){
  const body={business_name:businessName.value,category:category.value,city:city.value,address:address.value,contact_name:contactName.value,phone:phone.value,email:email.value,latitude:partnerLat,longitude:partnerLng,first_offer_name:offerName.value,original_price:Number(originalPrice.value||0),discounted_price:Number(discountedPrice.value||0),quantity:Number(quantity.value||1),pickup_window:pickupWindow.value};
  const s=document.getElementById('onboardStatus');
  s.textContent='Kreiram partnera i prvu ponudu...';
  const r=await fetch('/pilot-live/partner-onboard',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const data=await r.json();
  if(!r.ok){s.textContent=data.detail||'Onboarding nije uspeo.';return;}
  s.innerHTML='Partner uključen: <b>ID '+data.store.id+'</b>, PIN <b>'+data.store.pin+'</b><br><a class="chip" href="'+data.links.partner_panel+'">Otvori partner panel</a> <a class="chip" href="/ponude">Vidi ponude</a>';
}
</script>"""
    return page("Partner onboarding", body, "partner")

@router.get("/partner/moj-panel", response_class=HTMLResponse)
def partner_live_panel_page(store_id: int | None = Query(default=None), pin: str | None = Query(default=None), db: Session = Depends(get_db)):
    if not store_id or not pin:
        body="""<section class='detail'><span class='badge'>Partner panel</span><h1 style='font-size:42px'>Unesi ID i PIN</h1><p class='lead'>Partner dobija ID i PIN posle onboarding prijave.</p><div class='searchbar'><input id='sid' placeholder='Store ID'><input id='pin' placeholder='PIN'><button class='btn' onclick='openPanel()'>Otvori</button></div></section><script>function openPanel(){if(sid.value&&pin.value)location.href='/partner/moj-panel?store_id='+encodeURIComponent(sid.value)+'&pin='+encodeURIComponent(pin.value);}</script>"""
        return page("Partner panel", body, "partner")
    store = db.get(models.Store, store_id)
    if not store or str(store.seller_pin) != str(pin):
        return page("Partner panel", "<section class='detail'><h1 style='font-size:42px'>PIN nije ispravan</h1><p class='lead'>Proveri ID partnera i PIN.</p><a class='btn' href='/partner/moj-panel'>Pokušaj ponovo</a></section>", "partner")
    products = db.query(models.Product).filter(models.Product.store_id == store.id).order_by(models.Product.updated_at.desc()).limit(12).all()
    reservations = db.query(models.Reservation).join(models.Product).filter(models.Product.store_id == store.id).order_by(models.Reservation.created_at.desc()).limit(12).all()
    product_rows = "".join([f"<div class='card'><div class='card-body'><h3>{p.name}</h3><p class='muted'>{int(p.discounted_price or 0)} RSD • {p.status} • dostupno {product_available_quantity(db,p)}</p></div></div>" for p in products]) or "<div class='detail'>Nema ponuda.</div>"
    reservation_rows = "".join([f"<div class='card'><div class='card-body'><h3>{r.reservation_code}</h3><p class='muted'>{r.product.name if r.product else ''} • {r.customer_name} • {r.status} • {r.payment_status}</p><a class='chip' href='/reservation?code={r.reservation_code}'>Karta</a></div></div>" for r in reservations]) or "<div class='detail'>Nema rezervacija.</div>"
    body=f"""<div class='layout'><aside class='sidebar'><h3 style='color:white'>{store.name}</h3><a class='side-link active'>Pregled</a><a class='side-link' href='/partner/preuzimanje'>Preuzimanje</a><a class='side-link' href='/ponude'>Javne ponude</a><a class='side-link' href='/partner/onboarding'>Novi partner</a><p style='color:#d9f4e8'>ID: {store.id}<br>PIN: {store.seller_pin}</p></aside><section><div class='section-head'><div><h1 style='font-size:42px'>Partner panel</h1><p class='lead'>Upravljaj ponudama i prati rezervacije za zatvoreni pilot.</p></div><a class='btn' href='/partner/preuzimanje'>Potvrdi preuzimanje</a></div><div class='grid four'><div class='kpi'><b>{len(products)}</b>Ponude</div><div class='kpi'><b>{len(reservations)}</b>Rezervacije</div><div class='kpi'><b>{sum(1 for r in reservations if r.status=='picked_up')}</b>Preuzeto</div><div class='kpi'><b>{int(sum(r.platform_fee_amount or 0 for r in reservations if r.seller_payout_status=='commission_due'))}</b>RSD provizija</div></div><section class='section detail'><h2>Dodaj novu ponudu</h2><div class='grid two'><input class='field' id='name' value='Nova ponuda' placeholder='Naziv'><input class='field' id='cat' value='restoran' placeholder='Kategorija'><input class='field' id='old' type='number' value='600'><input class='field' id='price' type='number' value='360'><input class='field' id='qty' type='number' value='5'><input class='field' id='pickup' value='18:00 - 19:00'><button class='btn' onclick='addOffer()'>Objavi ponudu</button><div id='offerStatus' class='map-status'>Spremno.</div></div></section><section class='section'><div class='section-head'><h2>Ponude</h2></div><div class='grid two' id='products'>{product_rows}</div></section><section class='section'><div class='section-head'><h2>Rezervacije</h2></div><div class='grid two'>{reservation_rows}</div></section></section></div><script>
async function addOffer(){{
 const body={{store_id:{store.id},pin:'{store.seller_pin}',name:name.value,category:cat.value,original_price:Number(old.value||0),discounted_price:Number(price.value||0),discount_percent:Math.round((Number(old.value)-Number(price.value))/Number(old.value)*100),currency:'RSD',expiry_type:'seller_confirmed',quantity:Number(qty.value||1),pickup_window:pickup.value,image_url:'/admin-assets/seed-images/topli-obrok.svg',source_url:'partner-panel',confidence_score:1,status:'public_discount'}};
 const s=document.getElementById('offerStatus');
 s.textContent='Objavljujem...';
 const r=await fetch('/seller-api/products',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(body)}});
 const data=await r.json();
 s.innerHTML=r.ok?'Ponuda objavljena: <b>'+data.name+'</b>. Osveži stranicu za prikaz.':(data.detail||'Greška.');
}}
</script>"""
    return page("Partner panel", body, "partner")

@router.get("/partner/live", response_class=HTMLResponse)
def partner_live_ops_page(store_id: int | None = Query(default=None), pin: str | None = Query(default=None)):
    sid = store_id or ""
    spin = pin or ""
    body=f"""<div class='layout'><aside class='sidebar'><h3 style='color:white'>Partner live smena</h3><a class='side-link active'>Danas</a><a class='side-link' href='/partner/preuzimanje'>Brza potvrda</a><a class='side-link' href='/partner/onboarding'>Onboarding</a><a class='side-link' href='/ponude'>Javne ponude</a><p style='color:#d9f4e8'>Jedan ekran za ponude, rezervacije, preuzimanje i dnevnu proviziju.</p></aside><section><div class='section-head'><div><h1 style='font-size:42px'>Partner operacije</h1><p class='lead'>Unesi ID i PIN partnera. Sistem učitava aktivne ponude, rezervacije i finansijski status za smenu.</p></div><a class='btn secondary' href='/partner/moj-panel?store_id={sid}&pin={spin}'>Stari panel</a></div><section class='detail'><div class='grid four'><input class='compact-input' id='storeId' value='{sid}' placeholder='ID partnera'><input class='compact-input' id='pin' value='{spin}' placeholder='PIN'><button class='btn' onclick='loadOps()'>Učitaj smenu</button><button class='btn secondary' onclick='saveLogin()'>Zapamti lokalno</button></div><div id='opsStatus' class='map-status'>Spremno.</div></section><section class='grid four section' id='opsKpis'><div class='kpi ops-kpi'><b>—</b>Aktivne ponude</div><div class='kpi ops-kpi'><b>—</b>Rezervacije danas</div><div class='kpi ops-kpi'><b>—</b>Za preuzimanje</div><div class='kpi ops-kpi'><b>—</b>Provizija</div></section><section class='grid two section'><div class='detail'><h2>Brza potvrda kupca</h2><p class='muted'>Kupac pokaže QR ili kod rezervacije. Partner unosi kod i sistem beleži preuzimanje.</p><div class='grid'><input class='field' id='reservationCode' placeholder='Kod rezervacije'><button class='btn' onclick='confirmPickupLive()'>Potvrdi preuzimanje</button><div id='pickupResult' class='form-result'>Čeka kod.</div></div></div><div class='detail'><h2>Dodaj ponudu za danas</h2><div class='grid two'><input class='field' id='offerName' value='Dnevna live ponuda' placeholder='Naziv'><input class='field' id='category' value='restoran' placeholder='Kategorija'><input class='field' id='originalPrice' type='number' value='600'><input class='field' id='discountedPrice' type='number' value='360'><input class='field' id='quantity' type='number' value='5'><input class='field' id='pickupWindow' value='18:00 - 19:00'><button class='btn' onclick='addLiveOffer()'>Objavi</button><div id='offerResult' class='form-result'>Spremno.</div></div></div></section><section class='grid two section'><div class='detail'><h2>Aktivne rezervacije</h2><div id='activeReservations' class='ops-list'>Učitaj smenu.</div></div><div class='detail'><h2>Ponude partnera</h2><div id='partnerProducts' class='ops-list'>Učitaj smenu.</div></div></section><section class='detail section'><h2>Operativne napomene</h2><div id='opsAlerts' class='ops-list'>Učitaj smenu.</div></section></section></div><script>
function creds(){{return {{store_id:Number(storeId.value||localStorage.getItem('sh_partner_store_id')||0),pin:pin.value||localStorage.getItem('sh_partner_pin')||''}}}}
function saveLogin(){{localStorage.setItem('sh_partner_store_id',storeId.value);localStorage.setItem('sh_partner_pin',pin.value);opsStatus.textContent='ID i PIN su zapamćeni u ovom browseru.';}}
function money(v){{return Number(v||0).toLocaleString('sr-RS')+' RSD'}}
function row(title,meta,side){{return '<div class="ops-row"><div><b>'+title+'</b><small>'+meta+'</small></div><div>'+side+'</div></div>'}}
async function loadOps(){{
  const c=creds(); if(!c.store_id||!c.pin){{opsStatus.textContent='Unesi ID partnera i PIN.';return;}}
  opsStatus.textContent='Učitavam smenu...';
  const r=await fetch('/pilot-live/partner-ops?store_id='+encodeURIComponent(c.store_id)+'&pin='+encodeURIComponent(c.pin));
  const data=await r.json();
  if(!r.ok){{opsStatus.textContent=data.detail||'Greška pri učitavanju.';return;}}
  opsStatus.innerHTML='Učitano: <b>'+data.store.name+'</b> · '+(data.store.address||'');
  opsKpis.innerHTML=[
    ['Aktivne ponude',data.stats.active_products],
    ['Rezervacije danas',data.stats.reservations_today],
    ['Za preuzimanje',data.stats.active_reservations],
    ['Provizija',money(data.stats.commission_due)]
  ].map(x=>'<div class="kpi ops-kpi"><b>'+x[1]+'</b>'+x[0]+'</div>').join('');
  activeReservations.innerHTML=(data.active_reservations||[]).map(r=>row('<span class="ops-code">'+r.reservation_code+'</span>',(r.product_name||'Ponuda')+' · '+(r.customer_name||'Kupac')+' · '+(r.payment_status||''),'<button class="btn secondary" onclick="reservationCode.value=\\''+r.reservation_code+'\\';confirmPickupLive()">Potvrdi</button>')).join('')||'<div class="muted">Nema aktivnih rezervacija.</div>';
  partnerProducts.innerHTML=(data.products||[]).map(p=>row(p.name,(p.store_name||data.store.name)+' · '+(p.pickup_window||'Danas')+' · dostupno '+(p.available_quantity??'—'),'<span class="status paid">'+money(p.discounted_price||p.original_price||0)+'</span>')).join('')||'<div class="muted">Nema ponuda.</div>';
  opsAlerts.innerHTML=(data.alerts||[]).map(a=>'<div class="trust-row"><span class="chip">!</span><div><b>'+a+'</b></div></div>').join('');
}}
async function confirmPickupLive(){{
  const c=creds(); const code=reservationCode.value.trim().toUpperCase(); if(!code){{pickupResult.textContent='Unesi kod rezervacije.';return;}}
  pickupResult.textContent='Potvrđujem kod...';
  const r=await fetch('/pilot-live/confirm-pickup',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{store_id:c.store_id,pin:c.pin,reservation_code:code}})}});
  const data=await r.json();
  pickupResult.innerHTML=r.ok?'Preuzimanje potvrđeno: <b>'+data.reservation.reservation_code+'</b>':(data.detail||'Greška.');
  if(r.ok) loadOps();
}}
async function addLiveOffer(){{
  const c=creds(); const old=Number(originalPrice.value||0); const price=Number(discountedPrice.value||0);
  const body={{store_id:c.store_id,pin:c.pin,name:offerName.value,category:category.value,original_price:old,discounted_price:price,discount_percent:old?Math.round((old-price)/old*100):0,currency:'RSD',expiry_type:'seller_confirmed',quantity:Number(quantity.value||1),pickup_window:pickupWindow.value,image_url:'/admin-assets/seed-images/topli-obrok.svg',source_url:'partner-live',confidence_score:1,status:'public_discount'}};
  offerResult.textContent='Objavljujem ponudu...';
  const r=await fetch('/seller-api/products',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(body)}});
  const data=await r.json();
  offerResult.innerHTML=r.ok?'Ponuda objavljena: <b>'+data.name+'</b>':(data.detail||'Greška.');
  if(r.ok) loadOps();
}}
window.addEventListener('load',function(){{if(!storeId.value&&localStorage.getItem('sh_partner_store_id'))storeId.value=localStorage.getItem('sh_partner_store_id');if(!pin.value&&localStorage.getItem('sh_partner_pin'))pin.value=localStorage.getItem('sh_partner_pin');if(storeId.value&&pin.value)loadOps();}});
</script>"""
    return page("Partner live operacije", body, "partner")

@router.get("/ponude/{offer_id}", response_class=HTMLResponse)
def offer_detail_page(offer_id:int):
    body=f"""<div class='hero-mini'><section class='card'><div class='offer-img' style='height:360px'><span class='badge discount'>-40%</span></div><div class='card-body'><h1 style='font-size:44px'>Domaći ručak</h1><p class='lead'>Sveže pripremljen domaći obrok: pileći file, povrće, krompir i sezonska salata.</p><div class='grid two'><div class='stat'>⏱ <b>Preuzimanje</b><span>Danas 18:30 – 19:00</span></div><div class='stat'>📍 <b>Lokacija</b><span>Vojvode Stepe 123, Beograd</span></div><div class='stat'>🍽 <b>Kategorija</b><span>Restorani</span></div><div class='stat'>🛍 <b>Količina</b><span>Još 3 porcije</span></div></div></div></section><aside class='detail'><span class='badge'>Rezervacija</span><h2>360 RSD <del class='muted'>600 RSD</del></h2><p class='muted'>Ušteda 240 RSD</p><button class='btn' style='width:100%'>Rezerviši odmah</button><button class='btn secondary' style='width:100%;margin-top:10px'>Prikaži QR kod</button><hr style='border:0;border-top:1px solid var(--line);margin:18px 0'><h3>Prodavac / Partner</h3><p><b>Restoran Zeleno</b><br><span class='muted'>⭐ 4.8 (120 ocena)</span></p><a class='chip' href='/ponude'>Pogledaj sve ponude</a></aside></div>"""
    return page("Detalj ponude", body, "ponude")

@router.get("/moje-rezervacije", response_class=HTMLResponse)
def reservations_page():
    body="""<div class='layout'><aside class='sidebar'><div class='avatar'>K</div><h3 style='color:white'>Kupac live</h3><a class='side-link active'>Moje rezervacije</a><a class='side-link' href='/ponude'>Nove ponude</a><a class='side-link' href='/podrska'>Podrška</a><a class='side-link' href='/bezbednost-hrane'>Bezbednost hrane</a><p style='color:#d9f4e8'>Pronađi rezervacije po telefonu, otvori QR kartu ili prijavi problem.</p></aside><section><div class='section-head'><div><h1 style='font-size:42px'>Moje rezervacije</h1><p class='lead'>Unesi telefon korišćen pri rezervaciji. Za pilot je dovoljno poklapanje zadnjih cifara telefona.</p></div><a class='btn' href='/ponude'>Pronađi obrok</a></div><section class='detail'><div class='searchbar'><input id='phone' value='+38160111000' placeholder='Telefon kupca'><button class='btn' onclick='loadCustomerReservations()'>Prikaži</button></div><div id='customerStatus' class='map-status'>Spremno.</div></section><section class='grid four section' id='customerKpis'><div class='kpi'><b>—</b>Ukupno</div><div class='kpi'><b>—</b>Aktivne</div><div class='kpi'><b>—</b>Preuzeto</div><div class='kpi'><b>—</b>Ušteda</div></section><section class='section'><div class='section-head'><h2>Rezervacije</h2><span class='chip'>Digitalna karta + QR</span></div><div class='grid' id='customerReservations'>Unesi telefon i učitaj rezervacije.</div></section></section></div><script>
const statusLabels={pending:'Čeka potvrdu',confirmed:'Potvrđeno',picked_up:'Preuzeto',cancelled:'Otkazano',expired:'Isteklo'};
const paymentLabels={unpaid:'Nije plaćeno',pay_on_pickup:'Plaćanje pri preuzimanju',paid:'Plaćeno',payment_pending:'Plaćanje u toku',refunded:'Refundirano'};
function money(v){return Number(v||0).toLocaleString('sr-RS')+' RSD'}
function esc(v){return String(v??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]))}
function reservationCard(r){
  const status=statusLabels[r.status]||r.status;
  const pay=paymentLabels[r.payment_status]||r.payment_status;
  const cancel=r.can_cancel?`<button class='btn secondary' onclick="cancelReservation('${esc(r.reservation_code)}')">Otkaži</button>`:'';
  return `<div class='card'><div class='card-body' style='display:grid;grid-template-columns:120px 1fr auto;gap:16px;align-items:center'><div class='offer-img' style='height:92px;border-radius:16px'></div><div><h3>${esc(r.product_name||'Rezervacija')}</h3><p class='muted'><b>${esc(r.reservation_code)}</b> · ${esc(r.store_name||'Partner')}<br>${esc(r.store_address||'')} · ${esc(r.pickup_window||'Danas')}<br>${esc(pay)} · ${money(r.payable_amount)}</p><div class='ops-actions'><a class='chip' href='${esc(r.ticket_url)}'>Digitalna karta</a><a class='chip' href='${esc(r.qr_url)}'>QR</a><a class='chip' href='/podrska?code=${encodeURIComponent(r.reservation_code)}'>Podrška</a></div></div><div><span class='status paid'>${esc(status)}</span><p class='ops-actions' style='justify-content:flex-end'><a class='btn secondary' href='${esc(r.checkout_url)}'>Checkout</a>${cancel}</p></div></div></div>`;
}
async function loadCustomerReservations(){
  const p=phone.value.trim();
  if(!p){customerStatus.textContent='Unesi telefon.';return;}
  localStorage.setItem('sh_customer_phone',p);
  customerStatus.textContent='Učitavam rezervacije...';
  const r=await fetch('/reservations/customer?phone='+encodeURIComponent(p));
  const data=await r.json();
  if(!r.ok){customerStatus.textContent=data.detail||'Nije moguće učitati rezervacije.';return;}
  customerStatus.innerHTML='Pronađeno za telefon koji se završava na <b>'+data.phone_tail+'</b>.';
  customerKpis.innerHTML=[
    ['Ukupno',data.stats.total],
    ['Aktivne',data.stats.active],
    ['Preuzeto',data.stats.picked_up],
    ['Ušteda',money(data.stats.total_saved)]
  ].map(x=>`<div class='kpi'><b>${x[1]}</b>${x[0]}</div>`).join('');
  customerReservations.innerHTML=(data.reservations||[]).map(reservationCard).join('')||'<section class="detail"><h2>Nema rezervacija</h2><p class="muted">Napravi prvu rezervaciju preko stranice Ponude.</p><a class="btn" href="/ponude">Otvori ponude</a></section>';
}
async function cancelReservation(code){
  if(!confirm('Da otkažemo rezervaciju '+code+'?')) return;
  const p=phone.value.trim();
  const r=await fetch('/reservations/code/'+encodeURIComponent(code)+'/cancel?phone='+encodeURIComponent(p),{method:'PATCH'});
  const data=await r.json();
  customerStatus.textContent=r.ok?'Rezervacija '+data.reservation_code+' je otkazana.':(data.detail||'Otkazivanje nije uspelo.');
  if(r.ok) loadCustomerReservations();
}
window.addEventListener('load',function(){const saved=localStorage.getItem('sh_customer_phone'); if(saved) phone.value=saved; if(phone.value) loadCustomerReservations();});
</script>"""
    return page("Moje rezervacije", body, "rezervacije")

@router.get("/profil", response_class=HTMLResponse)
def profile_page():
    return page("Profil", """<div class='layout'><aside class='sidebar'><div class='avatar'>IT</div><h3 style='color:white'>Moj profil</h3><a class='side-link active'>Lični podaci</a><a class='side-link'>Načini plaćanja</a><a class='side-link'>Obaveštenja</a></aside><section><h1 style='font-size:42px'>Profil korisnika</h1><div class='grid two'><div class='detail'><h2>Lični podaci</h2><p><b>Ime:</b> Korisnik Sačuvaj Hranu</p><p><b>Email:</b> korisnik@example.com</p><button class='btn'>Sačuvaj izmene</button></div><div class='detail'><h2>Tvoj uticaj</h2><div class='stats'><div class='stat'><b>12</b>spašenih obroka</div><div class='stat'><b>2.640 RSD</b>uštede</div></div></div></div></section></div>""", "rezervacije")

@router.get("/podrska", response_class=HTMLResponse)
@router.get("/support", response_class=HTMLResponse)
def support_page():
    body="""<section class='hero-mini'><div class='detail'><span class='badge'>Podrška</span><h1 style='font-size:42px'>Prijavi problem ili postavi pitanje</h1><p class='lead'>Za rezervaciju, plaćanje, preuzimanje, prodavca, bezbednost hrane ili tehnički problem. Prijava odmah ulazi u admin support listu. Direktan kontakt: <a class='chip' href='mailto:__SUPPORT_EMAIL__'>__SUPPORT_EMAIL__</a></p><div class='trust-list'><div class='trust-row'><span class='chip'>1</span><div><b>Rezervacija i QR</b><p class='muted'>Pošalji kod rezervacije ako ga imaš, da tim odmah pronađe slučaj.</p></div></div><div class='trust-row'><span class='chip'>2</span><div><b>Hrana i preuzimanje</b><p class='muted'>Ako postoji sumnja u ispravnost hrane, nemoj preuzimati proizvod i odmah pošalji prijavu.</p></div></div><div class='trust-row'><span class='chip'>3</span><div><b>Partner ili plaćanje</b><p class='muted'>Support beleži status i prosleđuje slučaj partneru, finansijama ili adminu.</p></div></div></div></div><aside class='detail'><h2>Nova prijava</h2><form id='supportForm' class='grid support-form'><input class='field' name='name' value='Pilot Kupac' placeholder='Ime i prezime' required><input class='field' name='phone' value='+38160111000' placeholder='Telefon'><input class='field' name='email' value='pilot@sacuvaj-hranu.local' placeholder='Email'><input class='field' name='reservation_code' placeholder='Kod rezervacije, opciono'><select class='field' name='topic'><option value='reservation'>Rezervacija</option><option value='payment'>Plaćanje</option><option value='pickup'>Preuzimanje</option><option value='seller'>Prodavac</option><option value='food_safety'>Bezbednost hrane</option><option value='technical'>Tehnički problem</option><option value='general'>Ostalo</option></select><textarea class='field wide-field' name='message' placeholder='Opiši šta se desilo' required>Test prijava za pilot podršku.</textarea><button class='btn' type='submit'>Pošalji prijavu</button><div id='supportResult' class='form-result wide-field'>Spremno.</div></form></aside></section><script>
document.getElementById('supportForm').addEventListener('submit',async function(e){
  e.preventDefault();
  const body=Object.fromEntries(new FormData(e.target).entries());
  body.source_page=location.pathname;
  const btn=e.target.querySelector('button');
  const out=document.getElementById('supportResult');
  btn.disabled=true; btn.textContent='Šaljem...'; out.textContent='Šaljem prijavu podršci...';
  try{
    const r=await fetch('/support-tickets',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    const data=await r.json();
    if(!r.ok) throw new Error(data.detail || 'Prijava nije poslata.');
    out.innerHTML='Prijava je poslata. ID: <b>'+data.ticket.id+'</b><br>Status: '+data.ticket.status;
    e.target.reset();
  }catch(err){out.textContent='Greška: '+err.message;}
  finally{btn.disabled=false; btn.textContent='Pošalji prijavu';}
});
</script>"""
    body = body.replace("__SUPPORT_EMAIL__", SUPPORT_EMAIL)
    return page("Podrška", body, "pocetna")

@router.get("/uslovi-koriscenja", response_class=HTMLResponse)
@router.get("/terms", response_class=HTMLResponse)
def terms_public_page():
    body=f"""<section class='detail legal-text'><span class='badge'>Pravni okvir</span><h1 style='font-size:42px'>Uslovi korišćenja</h1><p class='lead'>Ovo je produkcioni nacrt za pilot. Pre javnog marketinga tekst treba da proveri pravnik, ali aplikacija sada ima jasno mesto za pravila usluge.</p><h2>Osnovno</h2><p>Sačuvaj Hranu povezuje kupce i proverene prodavce hrane na sniženju. Kupac rezerviše ponudu, a prodavac potvrđuje dostupnost, uslove preuzimanja i tačnost podataka o proizvodu.</p><h2>Rezervacije i preuzimanje</h2><p>Rezervacija važi za navedenu količinu i vremenski prozor preuzimanja. Kupac pokazuje digitalnu kartu ili QR kod, a partner potvrđuje preuzimanje kroz svoj PIN tok.</p><h2>Plaćanje i provizija</h2><p>Za prvi pilot podržano je plaćanje pri preuzimanju i demo online tok. Platforma može obračunavati proviziju od 25% na realizovane rezervacije, uz prikaz u finansijama.</p><h2>Odgovornost za hranu</h2><p>Prodavac je odgovoran za rok, alergene, uslove čuvanja, deklaracije i bezbednost hrane. Platforma prikazuje ponude i tok rezervacije, ali ne zamenjuje obaveze prodavca prema kupcu.</p><h2>Kontakt</h2><p>Za pitanja o usluzi i podršci piši na <a href='mailto:{SUPPORT_EMAIL}'>{SUPPORT_EMAIL}</a>.</p><div class='gps-actions'><a class='btn' href='/privatnost'>Privatnost</a><a class='btn secondary' href='/bezbednost-hrane'>Bezbednost hrane</a><a class='btn secondary' href='/podrska'>Podrška</a></div></section>"""
    return page("Uslovi korišćenja", body, "pocetna")

@router.get("/privatnost", response_class=HTMLResponse)
@router.get("/privacy", response_class=HTMLResponse)
def privacy_public_page():
    body=f"""<section class='detail legal-text'><span class='badge'>Podaci korisnika</span><h1 style='font-size:42px'>Privatnost</h1><p class='lead'>Jasno prikazujemo koje podatke aplikacija koristi za rezervaciju, podršku, mapu i pilot operacije.</p><h2>Podaci koje obrađujemo</h2><p>Za rezervaciju se čuvaju ime, telefon, opciono email, kod rezervacije, odabrana ponuda, količina, status plaćanja i status preuzimanja.</p><h2>Lokacija i GPS</h2><p>GPS se koristi samo kada korisnik klikne da dozvoli lokaciju. Lokacija pomera mapu na ponude u blizini i ne mora biti obavezna za korišćenje aplikacije.</p><h2>Plaćanje</h2><p>Aplikacija ne čuva podatke o kartici. U pilotu je primarni model plaćanje pri preuzimanju, dok se realni payment provider uključuje tek kada bude izabran i testiran.</p><h2>Podrška i brisanje podataka</h2><p>Korisnik može preko podrške ili na <a href='mailto:{SUPPORT_EMAIL}'>{SUPPORT_EMAIL}</a> zatražiti proveru, ispravku ili brisanje podataka, u skladu sa poslovnim i zakonskim obavezama.</p><div class='gps-actions'><a class='btn' href='/podrska'>Pošalji zahtev podršci</a><a class='btn secondary' href='/uslovi-koriscenja'>Uslovi</a></div></section>"""
    return page("Privatnost", body, "pocetna")

@router.get("/bezbednost-hrane", response_class=HTMLResponse)
@router.get("/food-safety", response_class=HTMLResponse)
def food_safety_public_page():
    body="""<section class='hero-mini'><div class='detail legal-text'><span class='badge'>Trust & Safety</span><h1 style='font-size:42px'>Bezbednost hrane</h1><p class='lead'>Ovo je javna trust strana za kupce i partnere: šta sme u ponudu, šta kupac proverava i kako se prijavljuje problem.</p><h2>Rokovi</h2><p>Proizvodi sa oznakom „upotrebljivo do” ne smeju biti ponuđeni nakon isteka. Proizvodi sa oznakom „najbolje upotrebiti do” zahtevaju procenu kvaliteta i uslova čuvanja od strane prodavca.</p><h2>Alergeni i deklaracije</h2><p>Kupac treba da proveri alergene kod prodavca pre preuzimanja. Prodavac je odgovoran za tačnost deklaracija i informacija o alergenima.</p><h2>Prijava problema</h2><p>Ako proizvod ne odgovara opisu ili postoji sumnja u ispravnost, kupac ne treba da preuzme proizvod i treba odmah da pošalje prijavu kroz podršku.</p></div><aside class='detail'><h2>Pravila za partnere</h2><div class='trust-list'><div class='trust-row'><span class='chip'>✓</span><div><b>Tačan opis</b><p class='muted'>Naziv, količina, cena, rok i vreme preuzimanja moraju biti jasni.</p></div></div><div class='trust-row'><span class='chip'>✓</span><div><b>Bez rizičnih ponuda</b><p class='muted'>Hrana sumnjivog kvaliteta ili van bezbednosnog roka ne ide u aplikaciju.</p></div></div><div class='trust-row'><span class='chip'>✓</span><div><b>Brza reakcija</b><p class='muted'>Partner i support moraju reagovati na prijavu kupca pre zatvaranja slučaja.</p></div></div></div><div class='gps-actions'><a class='btn' href='/podrska'>Prijavi problem</a><a class='btn secondary' href='/ponude'>Nazad na ponude</a></div></aside></section>"""
    return page("Bezbednost hrane", body, "pocetna")

@router.get("/partner/kontrolna-tabla", response_class=HTMLResponse)
def partner_dashboard_page():
    return page("Partner kontrolna tabla", """<div class='layout'><aside class='sidebar'><h3 style='color:white'>Restoran Zeleno</h3><a class='side-link active'>Pregled</a><a class='side-link'>Ponude</a><a class='side-link'>Rezervacije</a><a class='side-link'>Finansije</a></aside><section><div class='section-head'><h1 style='font-size:42px'>Partner kontrolna tabla</h1><a class='btn' href='/admin/finance-console'>Finansije</a></div><div class='grid four'><div class='kpi'><b>128.450 RSD</b>Ukupan promet</div><div class='kpi'><b>324</b>Rezervacije</div><div class='kpi'><b>4.8</b>Ocena partnera</div><div class='kpi'><b>846</b>Sačuvani obroci</div></div><div class='grid two section'><div class='detail'><h2>Promet po danima</h2><div style='height:230px;border-radius:18px;background:linear-gradient(160deg,#e6f7ec,#fff7df);display:grid;place-items:center;color:var(--green);font-weight:900'>Grafikon prometa</div></div><div class='detail'><h2>Trenutna dugovanja</h2><p><b>Faktura #2024-045</b><br><span class='muted'>Dospeva: 25.05.2024</span><br><span class='status part'>18.560 RSD</span></p><button class='btn'>Vidi sva dugovanja</button></div></div></section></div>""", "partner")

@router.get("/dizajn-sistem", response_class=HTMLResponse)
def design_system_page():
    swatches="".join([f"<div><div style='height:70px;border-radius:18px;background:{c};border:1px solid var(--line)'></div><b>{c}</b></div>" for c in ['#0f3d2e','#14533d','#4fbf9f','#aee8c9','#f7f4ed','#f2b13d','#6b5e52']])
    body=f"""<h1 style='font-size:42px'>Dizajn sistem</h1><p class='lead'>Jedinstven vizuelni pravac za svaku stranicu aplikacije Sačuvaj Hranu.</p><section class='detail'><h2>Paleta boja</h2><div class='grid four'>{swatches}</div></section><section class='grid two section'><div class='detail'><h2>Tipografija</h2><h1 style='font-size:42px'>Uštedi novac.</h1><h2>Sačuvaj obrok.</h2><h3>Smanji bacanje.</h3><p>Body Regular 16/24 — tekst za opise, kartice, tabele i forme.</p></div><div class='detail'><h2>Komponente</h2><p><button class='btn'>Primarno dugme</button> <button class='btn secondary'>Sekundarno dugme</button></p><p><span class='status paid'>Plaćeno</span> <span class='status part'>Delimično plaćeno</span> <span class='status due'>Dospelo</span></p><div class='searchbar'><input placeholder='Pretraži...'><button class='btn'>Traži</button></div></div></section>"""
    return page("Dizajn sistem", body, "dizajn")
