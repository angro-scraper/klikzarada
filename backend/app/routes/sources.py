from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/sources", tags=["sources"])

SERBIA_SEED_SOURCES = [
    # Official / primary sources first. These are safer for a real MVP seed database.
    {"name": "DIS - aktuelne ponude", "url": "https://www.dis.rs/", "city": "Srbija", "source_type": "official_catalog", "crawl_frequency": "daily", "active": True},
    {"name": "Maxi - nedeljna akcija", "url": "https://www.maxi.rs/maxi-nedeljna-akcija", "city": "Srbija", "source_type": "official_catalog", "crawl_frequency": "daily", "active": True},
    {"name": "Lidl Srbija - online letak", "url": "https://www.lidl.rs/c/online-letak/s10019338", "city": "Srbija", "source_type": "official_catalog", "crawl_frequency": "daily", "active": True},
    {"name": "Idea - katalozi", "url": "https://www.idea.rs/Akcije/Katalozi", "city": "Srbija", "source_type": "official_catalog", "crawl_frequency": "daily", "active": True},
    {"name": "Roda - akcije", "url": "https://roda.rs/akcije--p-5", "city": "Srbija", "source_type": "official_catalog", "crawl_frequency": "daily", "active": True},
    {"name": "Univerexport - katalozi", "url": "https://univerexport.rs/sr/katalozi", "city": "Srbija", "source_type": "official_catalog", "crawl_frequency": "daily", "active": True},
    {"name": "Aman - akcijske ponude", "url": "https://www2.aman.co.rs/akcijske-ponude", "city": "Srbija", "source_type": "official_catalog", "crawl_frequency": "daily", "active": True},
    {"name": "Aman - katalozi", "url": "https://www2.aman.co.rs/katalog", "city": "Srbija", "source_type": "official_catalog", "crawl_frequency": "daily", "active": True},
    {"name": "Super Vero - ponude", "url": "https://www.supervero.rs/super-vero-ponude/", "city": "Srbija", "source_type": "official_catalog", "crawl_frequency": "daily", "active": True},
    {"name": "Gomex - početna", "url": "https://gomex.rs/", "city": "Srbija", "source_type": "official_catalog", "crawl_frequency": "daily", "active": True},

    # Aggregator/discovery pages. Use them as discovery candidates, not as proof of near-expiry.
    {"name": "Snizenje.rs - prehrana akcije", "url": "https://snizenje.rs/prehrana-akcije", "city": "Srbija", "source_type": "aggregator_catalog", "crawl_frequency": "daily", "active": True},
    {"name": "Cenoteka - katalozi", "url": "https://cenoteka.rs/katalozi/", "city": "Srbija", "source_type": "aggregator_catalog", "crawl_frequency": "daily", "active": True},
    {"name": "Eponuda - katalozi i akcije", "url": "https://www.eponuda.com/katalog-akcije", "city": "Srbija", "source_type": "aggregator_catalog", "crawl_frequency": "daily", "active": True},
    {"name": "Kuda u kupovinu - akcije katalozi", "url": "https://www.kudaukupovinu.rs/akcije-katalozi", "city": "Srbija", "source_type": "aggregator_catalog", "crawl_frequency": "daily", "active": True},
    {"name": "Oferlo - katalozi", "url": "https://www.oferlo.rs/", "city": "Srbija", "source_type": "aggregator_catalog", "crawl_frequency": "daily", "active": True},
    {"name": "Ustedite.rs - akcije", "url": "https://ustedite.rs/", "city": "Srbija", "source_type": "aggregator_catalog", "crawl_frequency": "daily", "active": True},
    {"name": "Pametno.rs - katalozi", "url": "https://www.pametno.rs/katalozi", "city": "Srbija", "source_type": "aggregator_catalog", "crawl_frequency": "daily", "active": True},
    {"name": "Lisica.rs - akcijski katalozi Srbija", "url": "https://lisica.rs/akcijski-katalozi/srbija", "city": "Srbija", "source_type": "aggregator_catalog", "crawl_frequency": "daily", "active": True},
    {"name": "Akcije Katalozi - Srbija", "url": "https://akcijekatalozi.com/", "city": "Srbija", "source_type": "aggregator_catalog", "crawl_frequency": "daily", "active": True},
    {"name": "Retail.rs - katalozi marketa", "url": "https://retail.rs/katalozi/katalozi-marketa", "city": "Srbija", "source_type": "aggregator_catalog", "crawl_frequency": "daily", "active": True},
]


BELGRADE_BAKERY_SEED_SOURCES = [
    # Official bakery sources / primary pages
    {"name": "Hleb & Kifle - početna", "url": "https://hlebikifle.rs/", "city": "Beograd", "source_type": "bakery_belgrade_official", "crawl_frequency": "daily", "active": True},
    {"name": "Hleb & Kifle - lokacije", "url": "https://hlebikifle.rs/lokacije/", "city": "Beograd", "source_type": "bakery_belgrade_official", "crawl_frequency": "weekly", "active": True},
    {"name": "Hleb & Kifle - kontakt", "url": "https://hlebikifle.rs/kontakt/", "city": "Beograd", "source_type": "bakery_belgrade_official", "crawl_frequency": "weekly", "active": True},
    {"name": "Skroz dobra pekara - početna", "url": "https://skrozdobrapekara.rs/", "city": "Beograd", "source_type": "bakery_belgrade_official", "crawl_frequency": "daily", "active": True},
    {"name": "Skroz dobra pekara - objekti", "url": "https://skrozdobrapekara.rs/objekti/", "city": "Beograd", "source_type": "bakery_belgrade_official", "crawl_frequency": "weekly", "active": True},
    {"name": "Skroz dobra pekara - proizvodi", "url": "https://skrozdobrapekara.rs/proizvodi/", "city": "Beograd", "source_type": "bakery_belgrade_official", "crawl_frequency": "daily", "active": True},
    {"name": "Skroz dobra pekara - kontakt PDF", "url": "https://skrozdobrapekara.rs/wp-content/uploads/2023/07/Kontakt-telefoni-objekata.pdf", "city": "Beograd", "source_type": "bakery_belgrade_official", "crawl_frequency": "weekly", "active": True},
    {"name": "Lulu pekare - početna", "url": "https://pekaralulu.com/", "city": "Beograd", "source_type": "bakery_belgrade_official", "crawl_frequency": "daily", "active": True},
    {"name": "Lulu pekare - lokacije", "url": "https://pekaralulu.com/lokacije/", "city": "Beograd", "source_type": "bakery_belgrade_official", "crawl_frequency": "weekly", "active": True},
    {"name": "Lulu pekare - kontakt", "url": "https://pekaralulu.com/kontakt/", "city": "Beograd", "source_type": "bakery_belgrade_official", "crawl_frequency": "weekly", "active": True},
    {"name": "Lulu pekare - proizvodi", "url": "https://pekaralulu.com/proizvodi/", "city": "Beograd", "source_type": "bakery_belgrade_official", "crawl_frequency": "daily", "active": True},
    {"name": "Trpković - početna", "url": "https://pekaratrpkovic.rs/", "city": "Beograd", "source_type": "bakery_belgrade_official", "crawl_frequency": "daily", "active": True},
    {"name": "Trpković - kontakt/lokacije", "url": "https://pekaratrpkovic.rs/kontakt/", "city": "Beograd", "source_type": "bakery_belgrade_official", "crawl_frequency": "weekly", "active": True},
    {"name": "Trpković - o nama", "url": "https://pekaratrpkovic.rs/o-nama/", "city": "Beograd", "source_type": "bakery_belgrade_official", "crawl_frequency": "weekly", "active": True},
    {"name": "Pekara GAK - početna", "url": "https://pekaragak.rs/", "city": "Beograd", "source_type": "bakery_belgrade_official", "crawl_frequency": "daily", "active": True},
    {"name": "Pekara GAK - lokacije", "url": "https://pekaragak.rs/lokacije/", "city": "Beograd", "source_type": "bakery_belgrade_official", "crawl_frequency": "weekly", "active": True},
    {"name": "Pekara GAK - proizvodi/kategorije", "url": "https://pekaragak.rs/kategorije/", "city": "Beograd", "source_type": "bakery_belgrade_official", "crawl_frequency": "daily", "active": True},
    {"name": "Pekara GAK - peciva", "url": "https://pekaragak.rs/peciva/", "city": "Beograd", "source_type": "bakery_belgrade_official", "crawl_frequency": "daily", "active": True},
    {"name": "Pekara GAK - roštilj", "url": "https://pekaragak.rs/rostilj/", "city": "Beograd", "source_type": "bakery_belgrade_official", "crawl_frequency": "daily", "active": True},
    {"name": "Pekara-ketering Radulović - zvanični sajt", "url": "https://pekaraketringradulovic.com/", "city": "Beograd", "source_type": "bakery_belgrade_official", "crawl_frequency": "weekly", "active": True},

    # Bakery directories/discovery pages. These are for finding sellers/leads, not proof of price or expiry.
    {"name": "011info - pekare Beograd", "url": "https://www.011info.com/pekare-oprema-za-pekare", "city": "Beograd", "source_type": "bakery_belgrade_directory", "crawl_frequency": "weekly", "active": True},
    {"name": "011info - pekare blizu mene", "url": "https://www.011info.com/pekare-oprema-za-pekare/blizu-mene", "city": "Beograd", "source_type": "bakery_belgrade_directory", "crawl_frequency": "weekly", "active": True},
    {"name": "011info - pekare Voždovac", "url": "https://www.011info.com/pekare-oprema-za-pekare/vozdovac--cela-opstina", "city": "Beograd", "source_type": "bakery_belgrade_directory", "crawl_frequency": "weekly", "active": True},
    {"name": "011info - Pekara Radulović", "url": "https://www.011info.com/pekare-oprema-za-pekare/pekara-i-ketering-radulovic", "city": "Beograd", "source_type": "bakery_belgrade_directory", "crawl_frequency": "weekly", "active": True},
    {"name": "011info - Pekara Sara", "url": "https://www.011info.com/pekare-oprema-za-pekare/pekara-sara-", "city": "Beograd", "source_type": "bakery_belgrade_directory", "crawl_frequency": "weekly", "active": True},
    {"name": "011info - Pekara Salaš DD", "url": "https://www.011info.com/pekare-oprema-za-pekare/pekara-salas-dd", "city": "Beograd", "source_type": "bakery_belgrade_directory", "crawl_frequency": "weekly", "active": True},
    {"name": "PlanPlus - pekare Beograd strana 1", "url": "https://www.planplus.rs/beograd/pekare", "city": "Beograd", "source_type": "bakery_belgrade_directory", "crawl_frequency": "weekly", "active": True},
]

# Add PlanPlus pagination as separate seed sources. PlanPlus currently exposes many result pages for Beograd bakeries.
for page in range(2, 16):
    BELGRADE_BAKERY_SEED_SOURCES.append({
        "name": f"PlanPlus - pekare Beograd strana {page}",
        "url": f"https://www.planplus.rs/beograd/pekare/{page}",
        "city": "Beograd",
        "source_type": "bakery_belgrade_directory",
        "crawl_frequency": "weekly",
        "active": True,
    })

BELGRADE_BAKERY_SEED_SOURCES.extend([
    {"name": "PlanPlus - pekare Novi Beograd", "url": "https://www.planplus.rs/novi-beograd/pekare", "city": "Beograd", "source_type": "bakery_belgrade_directory", "crawl_frequency": "weekly", "active": True},
    {"name": "PlanPlus - Hleb & Kifle lokacije", "url": "https://www.planplus.rs/beograd/firma/pekara-hleb-kifle/535", "city": "Beograd", "source_type": "bakery_belgrade_directory", "crawl_frequency": "weekly", "active": True},
    {"name": "PlanPlus - Lulu lokacije", "url": "https://www.planplus.rs/beograd/firma/pekara-lulu/530", "city": "Beograd", "source_type": "bakery_belgrade_directory", "crawl_frequency": "weekly", "active": True},
    {"name": "PlanPlus - Trpković lokacije", "url": "https://www.planplus.rs/beograd/firma/pekara-trpkovic/989", "city": "Beograd", "source_type": "bakery_belgrade_directory", "crawl_frequency": "weekly", "active": True},
    {"name": "PlanPlus - Sara", "url": "https://www.planplus.rs/pekara-sara/104094", "city": "Beograd", "source_type": "bakery_belgrade_directory", "crawl_frequency": "weekly", "active": True},
    {"name": "PlanPlus - Radulović", "url": "https://www.planplus.rs/pekara-radulovic/142938", "city": "Beograd", "source_type": "bakery_belgrade_directory", "crawl_frequency": "weekly", "active": True},
    {"name": "PlanPlus - Pekara Dušan", "url": "https://www.planplus.rs/pekara-dusan/21721", "city": "Beograd", "source_type": "bakery_belgrade_directory", "crawl_frequency": "weekly", "active": True},
    {"name": "PlanPlus - Skroz dobra pekara", "url": "https://www.planplus.rs/skroz-dobra-pekara/131352", "city": "Beograd", "source_type": "bakery_belgrade_directory", "crawl_frequency": "weekly", "active": True},
    {"name": "Firme Srbije - pekare i poslastičarnice Beograd", "url": "https://www.firmesrbije.rs/lokacije/pekare-palacinkarnice-poslasticarnice-beograd/", "city": "Beograd", "source_type": "bakery_belgrade_directory", "crawl_frequency": "weekly", "active": True},
    {"name": "Firme Srbije - Pekara Banjica", "url": "https://www.firmesrbije.rs/turizam-i-ugostiteljstvo/pekare-palacinkarnice-i-poslasticarnice/51338/pekara-banjica/", "city": "Beograd", "source_type": "bakery_belgrade_directory", "crawl_frequency": "weekly", "active": True},
    {"name": "NaVidiku - Pekara Banjica", "url": "https://www.navidiku.rs/firme/pekare-beograd/pekara-banjica", "city": "Beograd", "source_type": "bakery_belgrade_directory", "crawl_frequency": "weekly", "active": True},
    {"name": "NaVidiku - Pekara Sara", "url": "https://www.navidiku.rs/firme/pekare-beograd/pekara-sara", "city": "Beograd", "source_type": "bakery_belgrade_directory", "crawl_frequency": "weekly", "active": True},
    {"name": "Radio Pingvin - pekare Beograd", "url": "https://www.radiopingvin.com/lokacije/pekare-beograd", "city": "Beograd", "source_type": "bakery_belgrade_directory", "crawl_frequency": "weekly", "active": True},
])


BELGRADE_BAKERY_PRODUCT_DEEP_SOURCES = [
    # Deep product sources: keep only items with price + image.
    # Official bakery / shop pages first.
    {"name": "Baba Višnjine kiflice - prodavnica", "url": "https://kiflice.rs/prodavnica/", "city": "Beograd", "source_type": "bakery_product_deep", "crawl_frequency": "daily", "active": True},
    {"name": "Baba Višnjine kiflice - slane kiflice", "url": "https://kiflice.rs/slane-kiflice/", "city": "Beograd", "source_type": "bakery_product_deep", "crawl_frequency": "daily", "active": True},
    {"name": "Baba Višnjine kiflice - početna", "url": "https://kiflice.rs/", "city": "Beograd", "source_type": "bakery_product_deep", "crawl_frequency": "daily", "active": True},
    {"name": "Domaće kiflice - početna", "url": "https://domacekiflice.rs/", "city": "Beograd", "source_type": "bakery_product_deep", "crawl_frequency": "daily", "active": True},
    {"name": "Domaće kiflice - cenovnik", "url": "https://domacekiflice.rs/cenovnik/", "city": "Beograd", "source_type": "bakery_product_deep", "crawl_frequency": "daily", "active": True},
    {"name": "Pekara GAK - peciva", "url": "https://pekaragak.rs/peciva/", "city": "Beograd", "source_type": "bakery_product_deep", "crawl_frequency": "daily", "active": True},
    {"name": "Pekara GAK - kategorije", "url": "https://pekaragak.rs/kategorije/", "city": "Beograd", "source_type": "bakery_product_deep", "crawl_frequency": "daily", "active": True},
    {"name": "Lulu pekare - proizvodi", "url": "https://pekaralulu.com/proizvodi/", "city": "Beograd", "source_type": "bakery_product_deep", "crawl_frequency": "daily", "active": True},
    {"name": "Lulu pekare - slatko pecivo", "url": "https://pekaralulu.com/proizvodi/slatko-pecivo/", "city": "Beograd", "source_type": "bakery_product_deep", "crawl_frequency": "daily", "active": True},
    {"name": "Lulu pekare - poslastičarstvo", "url": "https://pekaralulu.com/proizvodi/poslasticarstvo/", "city": "Beograd", "source_type": "bakery_product_deep", "crawl_frequency": "daily", "active": True},

    # Delivery/menu sources can expose much deeper product lists with images and prices.
    {"name": "Glovo - Skroz dobra pekara Beograd", "url": "https://glovoapp.com/sr/rs/belgrade/stores/skroz-dobra-pekara-beg", "city": "Beograd", "source_type": "bakery_product_deep", "crawl_frequency": "daily", "active": True},
    {"name": "Glovo - Pekara Kirćanski", "url": "https://glovoapp.com/sr/rs/belgrade/stores/pekara-kircanski", "city": "Beograd", "source_type": "bakery_product_deep", "crawl_frequency": "daily", "active": True},
    {"name": "Glovo - Pekara na Bulevaru", "url": "https://glovoapp.com/sr/rs/belgrade/stores/pekaranabulevaru", "city": "Beograd", "source_type": "bakery_product_deep", "crawl_frequency": "daily", "active": True},
    {"name": "MisterD - Skroz dobra pekara Novi Beograd", "url": "https://misterd.rs/place/skroz-dobra-pekara-novi-beograd-dostava", "city": "Beograd", "source_type": "bakery_product_deep", "crawl_frequency": "daily", "active": True},
    {"name": "MisterD - Pekara Trpković", "url": "https://misterd.rs/place/pekara-trpkovic-dostava", "city": "Beograd", "source_type": "bakery_product_deep", "crawl_frequency": "daily", "active": True},
    {"name": "MisterD - Pekara Trpković Zvezdara", "url": "https://misterd.rs/place/pekara-trpkovic-zvezdara-dostava", "city": "Beograd", "source_type": "bakery_product_deep", "crawl_frequency": "daily", "active": True},
    {"name": "MisterD - Pekara Panificio Verde", "url": "https://misterd.rs/place/pekara-panificio-verde-dostava", "city": "Beograd", "source_type": "bakery_product_deep", "crawl_frequency": "daily", "active": True},
    {"name": "MisterD - Pekara Vir", "url": "https://misterd.rs/place/pekara-vir-dostava", "city": "Beograd", "source_type": "bakery_product_deep", "crawl_frequency": "daily", "active": True},
    {"name": "MisterD - Pekara Kirćanski NBG", "url": "https://misterd.rs/place/pekara-kircanski-nbg-dostava", "city": "Beograd", "source_type": "bakery_product_deep", "crawl_frequency": "daily", "active": True},
    {"name": "MisterD - Pekara Zdravljak", "url": "https://misterd.rs/place/pekara-zdravljak-dostava", "city": "Beograd", "source_type": "bakery_product_deep", "crawl_frequency": "daily", "active": True},
    {"name": "Wolt - Pekarica Collina", "url": "https://wolt.com/sr/srb/belgrade/restaurant/pekarica-collina", "city": "Beograd", "source_type": "bakery_product_deep", "crawl_frequency": "daily", "active": True},
    {"name": "Wolt - Mi Hleb", "url": "https://wolt.com/sr/srb/belgrade/restaurant/mi-hleb", "city": "Beograd", "source_type": "bakery_product_deep", "crawl_frequency": "daily", "active": True},
    {"name": "Wolt - Skroz Dobra Pekara Novi Beograd", "url": "https://wolt.com/sr/srb/belgrade/venue/skroz-dobra-pekara-novi-beograd", "city": "Beograd", "source_type": "bakery_product_deep", "crawl_frequency": "daily", "active": True},
]


BELGRADE_BAKERY_PRODUCT_SUPER_DEEP_SOURCES = [
    # Super-deep list: delivery/menu/category URLs that usually expose many items with image + price.
    {"name": "Glovo - Hleb & Kifle Beograd", "url": "https://glovoapp.com/sr/rs/belgrade/stores/hleb-kifle-beg", "city": "Beograd", "source_type": "bakery_product_super_deep", "crawl_frequency": "daily", "active": True},
    {"name": "Glovo - Pekara Gvozden", "url": "https://glovoapp.com/sr/rs/belgrade/stores/pekara-gvozden", "city": "Beograd", "source_type": "bakery_product_super_deep", "crawl_frequency": "daily", "active": True},
    {"name": "Glovo - Pekara Trpković", "url": "https://glovoapp.com/sr/rs/belgrade/stores/trpkovic-s-beg", "city": "Beograd", "source_type": "bakery_product_super_deep", "crawl_frequency": "daily", "active": True},
    {"name": "Glovo - Pekara Kirćanski", "url": "https://glovoapp.com/sr/rs/belgrade/stores/pekara-kircanski", "city": "Beograd", "source_type": "bakery_product_super_deep", "crawl_frequency": "daily", "active": True},
    {"name": "Glovo - Pekara na Bulevaru", "url": "https://glovoapp.com/sr/rs/belgrade/stores/pekaranabulevaru", "city": "Beograd", "source_type": "bakery_product_super_deep", "crawl_frequency": "daily", "active": True},
    {"name": "Glovo - Kiflizza Vračar", "url": "https://glovoapp.com/sr/rs/belgrade/stores/kiflizza-vracar-beg", "city": "Beograd", "source_type": "bakery_product_super_deep", "crawl_frequency": "daily", "active": True},
    {"name": "Wolt - Skroz Dobra Pekara Novi Beograd - kolači", "url": "https://wolt.com/sr/srb/belgrade/venue/skroz-dobra-pekara-novi-beograd/items/kolaci-8", "city": "Beograd", "source_type": "bakery_product_super_deep", "crawl_frequency": "daily", "active": True},
    {"name": "Wolt - Pekara Zanat - peciva", "url": "https://wolt.com/sr/srb/belgrade/venue/pekara-zanat/items/peciva-4", "city": "Beograd", "source_type": "bakery_product_super_deep", "crawl_frequency": "daily", "active": True},
    {"name": "Wolt - Pekara Ključ - kolači", "url": "https://wolt.com/sr/srb/belgrade/venue/pekara-klju/items/kolaci-9", "city": "Beograd", "source_type": "bakery_product_super_deep", "crawl_frequency": "daily", "active": True},
    {"name": "Wolt - Hipermarket Beograd - pekara", "url": "https://wolt.com/sr/srb/belgrade/venue/hipermarket-beograd/items/pekara-181", "city": "Beograd", "source_type": "bakery_product_super_deep", "crawl_frequency": "daily", "active": True},
    {"name": "Wolt - Aman Ustanička - hleb i peciva", "url": "https://wolt.com/sr/srb/belgrade/venue/aman-ustanicka/items/hleb-i-peciva-98", "city": "Beograd", "source_type": "bakery_product_super_deep", "crawl_frequency": "daily", "active": True},
    {"name": "MisterD - Pekara Trpković Zvezdara - kiflice", "url": "https://misterd.rs/place/pekara-trpkovic-zvezdara-dostava/kiflice-sa-kremom-itemid-1332773", "city": "Beograd", "source_type": "bakery_product_super_deep", "crawl_frequency": "daily", "active": True},
    {"name": "Pekara GAK - hleb i peciva", "url": "https://pekaragak.rs/peciva/", "city": "Beograd", "source_type": "bakery_product_super_deep", "crawl_frequency": "daily", "active": True},
    {"name": "Pekara GAK - pice", "url": "https://pekaragak.rs/pice/", "city": "Beograd", "source_type": "bakery_product_super_deep", "crawl_frequency": "daily", "active": True},
    {"name": "Pekara GAK - sendviči", "url": "https://pekaragak.rs/sendvici/", "city": "Beograd", "source_type": "bakery_product_super_deep", "crawl_frequency": "daily", "active": True},
    {"name": "Pekara GAK - torte i kolači", "url": "https://pekaragak.rs/torte-i-kolaci/", "city": "Beograd", "source_type": "bakery_product_super_deep", "crawl_frequency": "daily", "active": True},
    {"name": "Domaće kiflice", "url": "https://domacekiflice.rs/", "city": "Beograd", "source_type": "bakery_product_super_deep", "crawl_frequency": "daily", "active": True},
    {"name": "Kiflice Petreski", "url": "https://www.kiflicepetreski.com/", "city": "Beograd", "source_type": "bakery_product_super_deep", "crawl_frequency": "daily", "active": True},
    {"name": "Wolt - Pekare Voždovac directory", "url": "https://wolt.com/sr/srb/belgrade/district/vozdovac/pekare%3Abelgrade", "city": "Beograd", "source_type": "bakery_product_super_deep", "crawl_frequency": "daily", "active": True},
    {"name": "Wolt - Pekare Zvezdara directory", "url": "https://wolt.com/sr/srb/belgrade/district/zvezdara/pekare", "city": "Beograd", "source_type": "bakery_product_super_deep", "crawl_frequency": "daily", "active": True},
    {"name": "Wolt - Pekarica Collina", "url": "https://wolt.com/sr/srb/belgrade/restaurant/pekarica-collina", "city": "Beograd", "source_type": "bakery_product_super_deep", "crawl_frequency": "daily", "active": True},
    {"name": "Wolt - Mi Hleb restaurant", "url": "https://wolt.com/sr/srb/belgrade/restaurant/mi-hleb", "city": "Beograd", "source_type": "bakery_product_super_deep", "crawl_frequency": "daily", "active": True},
    {"name": "Glovo - Pekara Mladost", "url": "https://glovoapp.com/sr/rs/belgrade/stores/pekara-mladost-beg", "city": "Beograd", "source_type": "bakery_product_super_deep", "crawl_frequency": "daily", "active": True},
    {"name": "Glovo - Pekara Croquant Artisan Bakery", "url": "https://glovoapp.com/sr/rs/belgrade/stores/pekara-croquant-artisan-bakery-beg", "city": "Beograd", "source_type": "bakery_product_super_deep", "crawl_frequency": "daily", "active": True},
    {"name": "Glovo - Furuna Libanska Pekara", "url": "https://glovoapp.com/sr/rs/belgrade/stores/furuna-libanska-pekara-beg", "city": "Beograd", "source_type": "bakery_product_super_deep", "crawl_frequency": "daily", "active": True},
    {"name": "MisterD - Skroz dobra pekara Novi Beograd", "url": "https://misterd.rs/place/skroz-dobra-pekara-novi-beograd-dostava", "city": "Beograd", "source_type": "bakery_product_super_deep", "crawl_frequency": "daily", "active": True},
    {"name": "MisterD - Pekara Trpković", "url": "https://misterd.rs/place/pekara-trpkovic-dostava", "city": "Beograd", "source_type": "bakery_product_super_deep", "crawl_frequency": "daily", "active": True},
    {"name": "MisterD - Pekara Panificio Verde", "url": "https://misterd.rs/place/pekara-panificio-verde-dostava", "city": "Beograd", "source_type": "bakery_product_super_deep", "crawl_frequency": "daily", "active": True},
    {"name": "MisterD - Pekara Vir", "url": "https://misterd.rs/place/pekara-vir-dostava", "city": "Beograd", "source_type": "bakery_product_super_deep", "crawl_frequency": "daily", "active": True},
    {"name": "MisterD - Pekara Kirćanski NBG", "url": "https://misterd.rs/place/pekara-kircanski-nbg-dostava", "city": "Beograd", "source_type": "bakery_product_super_deep", "crawl_frequency": "daily", "active": True},
]


def _create_or_get_source(db: Session, payload: dict) -> tuple[models.Source, bool]:
    existing = db.query(models.Source).filter(models.Source.url == payload["url"]).first()
    if existing:
        # Keep existing user edits, but ensure it is active for seeded runs.
        return existing, False
    source = models.Source(**payload)
    db.add(source)
    db.commit()
    db.refresh(source)
    return source, True


@router.post("", response_model=schemas.SourceOut)
def create_source(payload: schemas.SourceCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Source).filter(models.Source.url == payload.url).first()
    if existing:
        return existing
    source = models.Source(**payload.model_dump())
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.post("/seed-serbia", response_model=dict)
def seed_serbia_sources(db: Session = Depends(get_db)):
    created = 0
    existing = 0
    source_ids: list[int] = []
    for payload in SERBIA_SEED_SOURCES:
        source, was_created = _create_or_get_source(db, payload)
        source_ids.append(source.id)
        if was_created:
            created += 1
        else:
            existing += 1
    return {
        "created": created,
        "existing": existing,
        "total_seed_sources": len(SERBIA_SEED_SOURCES),
        "source_ids": source_ids,
        "note": "Ovo su izvori za javne akcijske kandidate. Status artikala nije 'pred istek' dok prodavac ne potvrdi rok.",
    }


@router.post("/seed-belgrade-bakeries", response_model=dict)
def seed_belgrade_bakery_sources(db: Session = Depends(get_db)):
    created = 0
    existing = 0
    source_ids: list[int] = []
    for payload in BELGRADE_BAKERY_SEED_SOURCES:
        source, was_created = _create_or_get_source(db, payload)
        source_ids.append(source.id)
        if was_created:
            created += 1
        else:
            existing += 1
    return {
        "created": created,
        "existing": existing,
        "total_seed_sources": len(BELGRADE_BAKERY_SEED_SOURCES),
        "source_ids": source_ids,
        "official_sources": len([s for s in BELGRADE_BAKERY_SEED_SOURCES if s["source_type"] == "bakery_belgrade_official"]),
        "directory_sources": len([s for s in BELGRADE_BAKERY_SEED_SOURCES if s["source_type"] == "bakery_belgrade_directory"]),
        "note": "Dodati su izvori samo za pekare u Beogradu. Koristi ih za bazu prodavaca/leads i javne akcijske kandidate; rok trajanja se ne potvrđuje automatski.",
    }


@router.post("/seed-belgrade-bakery-products-deep", response_model=dict)
def seed_belgrade_bakery_product_deep_sources(db: Session = Depends(get_db)):
    created = 0
    existing = 0
    source_ids: list[int] = []
    for payload in BELGRADE_BAKERY_PRODUCT_DEEP_SOURCES:
        source, was_created = _create_or_get_source(db, payload)
        source_ids.append(source.id)
        if was_created:
            created += 1
        else:
            existing += 1
    return {
        "created": created,
        "existing": existing,
        "total_seed_sources": len(BELGRADE_BAKERY_PRODUCT_DEEP_SOURCES),
        "source_ids": source_ids,
        "source_type": "bakery_product_deep",
        "rule": "Deep crawler za ove izvore upisuje samo proizvode koji imaju cenu i validnu sliku.",
        "note": "Ovo je baza javnih pekarskih proizvoda sa slikom i cenom. Nije dokaz da je proizvod pred istekom roka dok prodavac ne potvrdi rok.",
    }


@router.post("/seed-belgrade-bakery-products-super-deep", response_model=dict)
def seed_belgrade_bakery_product_super_deep_sources(db: Session = Depends(get_db)):
    created = 0
    existing = 0
    source_ids: list[int] = []
    all_sources = BELGRADE_BAKERY_PRODUCT_DEEP_SOURCES + BELGRADE_BAKERY_PRODUCT_SUPER_DEEP_SOURCES
    for payload in all_sources:
        source, was_created = _create_or_get_source(db, payload)
        source_ids.append(source.id)
        if was_created:
            created += 1
        else:
            existing += 1
    return {
        "created": created,
        "existing": existing,
        "total_seed_sources": len(all_sources),
        "source_ids": source_ids,
        "source_type": "bakery_product_super_deep",
        "rule": "Super-deep crawler prati sitemap, JSON app-state, product/category linkove i upisuje samo proizvode sa cenom i validnom slikom.",
        "note": "Javne cene i slike su kandidati za bazu. Rok trajanja i dostupnost mora potvrditi prodavac.",
    }


@router.get("", response_model=list[schemas.SourceOut])
def list_sources(active: bool | None = None, db: Session = Depends(get_db)):
    query = db.query(models.Source)
    if active is not None:
        query = query.filter(models.Source.active == active)
    return query.order_by(models.Source.id.desc()).all()


@router.delete("/{source_id}", response_model=dict)
def delete_source(source_id: int, db: Session = Depends(get_db)):
    source = db.get(models.Source, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Izvor nije pronađen")
    db.delete(source)
    db.commit()
    return {"deleted": True}
