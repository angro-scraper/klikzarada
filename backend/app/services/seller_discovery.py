from __future__ import annotations

import json
import os
import re
import unicodedata
from collections import Counter
from datetime import datetime
from typing import Any
from urllib.parse import urlencode, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models
from .json_store import read_json, write_json, append_json_row

LEADS_FILE = "growth_leads.json"
RUNS_FILE = "seller_discovery_runs.json"

DEFAULT_CITIES = ["Beograd", "Novi Sad", "Nis", "Kragujevac", "Subotica", "Cacak", "Kraljevo", "Zrenjanin"]
DEFAULT_ZONES = ["centar", "naselje", "pijaca", "poslovna zona", "studentska zona", "glavna ulica", "opstina", "lokal", "dostava", "porudzbine"]
CATEGORY_ALIASES = {
    "prodavci hrane": ["pekara", "restoran", "market", "prodavnica", "maloprodaja", "domaca hrana", "domaca radinost", "bistro", "fast food", "catering", "poslasticarnica", "picerija", "mesara", "delikates", "samoposluga", "kućna kuhinja", "rostiljnica", "sendvicara", "burger", "salaterija", "gotova jela", "mini market", "supermarket", "diskont"],
    "prodavac hrane": ["pekara", "restoran", "market", "prodavnica", "maloprodaja", "domaca hrana", "domaca radinost", "bistro", "fast food", "catering", "poslasticarnica", "picerija", "mesara", "delikates", "samoposluga", "kućna kuhinja", "rostiljnica", "sendvicara", "burger", "salaterija", "gotova jela", "mini market", "supermarket", "diskont"],
    "svi prodavci": ["pekara", "restoran", "market", "prodavnica", "maloprodaja", "domaca hrana", "domaca radinost", "bistro", "fast food", "catering", "poslasticarnica", "picerija", "mesara", "delikates", "samoposluga", "kućna kuhinja", "rostiljnica", "sendvicara", "burger", "salaterija", "gotova jela", "mini market", "supermarket", "diskont"],
    "sve kategorije": ["pekara", "restoran", "market", "prodavnica", "maloprodaja", "domaca hrana", "domaca radinost", "bistro", "fast food", "catering", "poslasticarnica", "picerija", "mesara", "delikates", "samoposluga", "kućna kuhinja", "rostiljnica", "sendvicara", "burger", "salaterija", "gotova jela", "mini market", "supermarket", "diskont"],
    "hrana": ["pekara", "restoran", "market", "prodavnica", "maloprodaja", "domaca hrana", "domaca radinost", "bistro", "fast food", "catering", "poslasticarnica", "picerija", "mesara", "delikates", "samoposluga", "kućna kuhinja", "rostiljnica", "sendvicara", "burger", "salaterija", "gotova jela", "mini market", "supermarket", "diskont"],
    "pekara": ["pekara", "pekar", "pecivo", "hleb", "burek", "kifla"],
    "pekare": ["pekara", "pekar", "pecivo", "hleb", "burek", "kifla"],
    "restoran": ["restoran", "gotova jela", "rucak", "ručak", "meni", "dnevni meni", "bistro", "gril", "rostilj", "dostava hrane", "picerija", "rostilj", "kuhinja", "rostiljnica", "burger", "sendvicara", "salaterija"],
    "restorani": ["restoran", "gotova jela", "rucak", "ručak", "meni", "dnevni meni", "bistro", "gril", "rostilj", "dostava hrane", "picerija", "rostilj", "kuhinja", "rostiljnica", "burger", "sendvicara", "salaterija"],
    "market": ["market", "prodavnica", "prehrana", "mini market", "supermarket", "lokalna radnja", "diskont", "samoposluga", "delikates", "maloprodaja", "trgovina"],
    "marketi": ["market", "prodavnica", "prehrana", "mini market", "supermarket", "lokalna radnja", "diskont", "samoposluga", "delikates", "maloprodaja", "trgovina"],
    "prodavnica": ["prodavnica", "mini market", "market", "prehrana", "samousluga", "lokalna radnja", "samoposluga", "delikates", "maloprodaja", "trgovina"],
    "prodavnice": ["prodavnica", "mini market", "market", "prehrana", "samousluga", "lokalna radnja", "samoposluga", "delikates", "maloprodaja", "trgovina"],
    "maloprodaja": ["maloprodaja", "prodavnica", "market", "lanac", "lokalna radnja", "diskont", "supermarket", "samoposluga", "delikates", "trgovina", "mini market"],
    "maloprodaje": ["maloprodaja", "prodavnica", "market", "lanac", "lokalna radnja", "diskont", "supermarket", "samoposluga", "delikates", "trgovina", "mini market"],
    "poslastice": ["poslastice", "kolaci", "kolači", "torte", "slatko", "poslasticarnica"],
    "zdrava hrana": ["zdrava hrana", "salate", "vege", "bio", "organic", "sokovi", "fit obroci"],
    "domaca hrana": ["domaca hrana", "domaća hrana", "domaca radinost", "domaća radinost", "kuvana jela", "porudzbine hrane", "domaca kuhinja", "rucak za poneti", "kucna kuhinja", "zimnica", "domaci kolaci", "domaca trpeza", "slana pita", "torte po porudzbini"],
    "domaca radinost": ["domaca radinost", "domaća radinost", "zimnica", "ajvar", "kolaci po porudzbini", "torte po porudzbini", "domaci proizvodi", "domaca kuhinja", "kucna kuhinja", "domaci rucak", "domaca trpeza", "slatki program"],
    "kucna kuhinja": ["kucna kuhinja", "kućna kuhinja", "domaca kuhinja", "domaća kuhinja", "rucak za poneti", "porucivanje hrane", "domaci kolaci", "zimnica", "gotova jela", "porodicni obrok"],
    "mali proizvodjaci": ["mali proizvodjaci hrane", "gazdinstvo", "opg", "domaci proizvodi", "pijaca", "domaca radinost", "zimnica", "domaci kolaci", "porodicna proizvodnja", "mala proizvodnja hrane"],
}
DISCOUNT_TERMS = (
    "akcija",
    "akcijska cena",
    "akcijske cene",
    "akcijska ponuda",
    "popust",
    "sniženje",
    "snizenje",
    "sale",
    "happy hour",
    "specijalna cena",
    "na sniženju",
    "na snizenju",
    "ušteda",
    "usted",
)
IMAGE_TERMS = (
    "galerija",
    "slika",
    "slike",
    "fotografija",
    "fotografije",
    "instagram",
    "meni",
    "jelovnik",
    "ponuda",
)
FOOD_TERMS = (
    "hrana",
    "obrok",
    "ručak",
    "rucak",
    "večera",
    "vecera",
    "pecivo",
    "hleb",
    "burek",
    "kifla",
    "kolač",
    "kolac",
    "torta",
    "pekara",
    "restoran",
    "kuhinja",
    "meni",
    "jelovnik",
    "pizza",
    "sendvič",
    "sendvic",
    "burger",
    "roštilj",
    "rostilj",
    "market",
    "prodavnica",
    "prehrana",
)
DEEP_LINK_HINTS = (
    "kontakt",
    "o-nama",
    "o nama",
    "meni",
    "jelovnik",
    "ponuda",
    "akcija",
    "popust",
    "snizen",
    "snižen",
    "proizvod",
    "katalog",
    "cenovnik",
    "cena",
    "dostava",
    "naruci",
    "naruči",
    "korpa",
    "shop",
    "proizvodi",
    "artikli",
    "obroci",
    "akcije",
    "popusti",
    "radnja",
)
DEEP_PRIORITY_HINTS = {
    "meni": 6,
    "jelovnik": 6,
    "ponuda": 6,
    "akcija": 7,
    "popust": 7,
    "proizvod": 6,
    "katalog": 6,
    "cenovnik": 5,
    "cena": 5,
    "kontakt": 4,
    "dostava": 4,
    "shop": 4,
    "radnja": 4,
}
SEARCH_SOURCE_HINTS = (
    "site:glovoapp.com",
    "site:wolt.com",
    "site:donesi.com",
    "site:011info.com",
    "site:planplus.rs",
    "site:mapa.rs",
    "site:restorani.rs",
    "site:restoranibeograd.com",
    "site:cenoteka.rs",
    "site:akcijeikatalozi.rs",
    "site:kudaukupovinu.rs",
    "site:kupinapopustu.com",
    "site:kliklak.rs",
    "site:dijaspora.shop",
    "site:halooglasi.com",
    "site:kupujemprodajem.com",
    "site:mojagajbica.rs",
    "site:ananas.rs",
    "site:shoppster.rs",
    "site:instagram.com",
    "site:facebook.com",
    "site:tripadvisor.com",
)
PILOT_TEXT_MARKERS = (
    "pilot",
    "test",
    "demo",
    "sample",
    "seed",
    "primer",
    "probni",
)
PILOT_URL_MARKERS = (
    "seed://",
    "seed://v",
    "example.com/pilot",
    "example.com/pilot-partner",
    "example.com/sacuvaj-hranu-demo",
    "/admin-assets/seed-images/",
    "sacuvaj-hranu.local",
    "127.0.0.1",
    "localhost",
    "onrender.com",
    "/pilot/",
    "pilot-live",
    "partner-live",
    "partner-panel",
    "pilot-partner-onboarding",
)


def _normalize_discovery_warning_text(message: str | None, fallback: str = "AI pretraga trenutno nije završena.") -> str:
    text = str(message or "").strip()
    lower = text.lower()
    if ("duplicate key value" in lower or "uniqueviolation" in lower or "already exists" in lower) and (
        "ix_sources_url" in lower or "source" in lower or "url" in lower
    ):
        return "Neki izvori i prodavci su već postojali u bazi, pa su duplikati preskočeni bez prekida pretrage."
    if "integrityerror" in lower and ("source" in lower or "url" in lower):
        return "Jedan deo AI uvoza je preskočen jer isti izvor već postoji u bazi."
    if "openai" in lower and ("api" in lower or "quota" in lower or "rate" in lower):
        return "OpenAI odgovor trenutno nije dostupan. Pokušaj ponovo za minut."
    if "internal server error" in lower:
        return "AI pretraga je naišla na serversku grešku. Probaj ponovo za minut ili sa manjim limitom."
    if "timeout" in lower or "timed out" in lower:
        return "Pretraga je istekla pre završetka. Pokušaj sa manjim limitom ili bez web pretrage."
    if "connection" in lower or "network" in lower:
        return "Mrežna veza za AI pretragu trenutno nije stabilna. Probaj ponovo."
    if "psycopg" in lower or "sqlalchemy" in lower:
        return "AI pretraga je preskočila deo tehničkih duplikata ili veza. Osveži stranicu i nastavi sa užim kriterijumom ako treba."
    if "sql" in lower or "parameters:" in lower or "traceback" in lower or len(text) > 700:
        return "AI pretraga je vratila tehničko upozorenje. Osveži stranicu i probaj ponovo sa manjim limitom ili užim kriterijumom."
    return text or fallback


def friendly_discovery_error(exc: Exception, fallback: str = "AI pretraga trenutno nije završena.") -> str:
    return _normalize_discovery_warning_text(str(exc or "").strip(), fallback)


def _ascii_key(value: str | None) -> str:
    value = value or ""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _tokens(value: str | None) -> set[str]:
    return {x for x in _ascii_key(value).split() if len(x) >= 3}


def _category_aliases(category: str | None) -> list[str]:
    cleaned = _clean(category, 80) or "prodavci hrane"
    aliases = CATEGORY_ALIASES.get(_ascii_key(cleaned))
    if aliases:
        return list(dict.fromkeys([cleaned, *aliases]))
    return [cleaned]


def _clean(value: Any, limit: int = 255) -> str | None:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit] if text else None


def _canonical_source_url(value: str | None) -> str | None:
    raw = _clean(value, 500)
    if not raw or not raw.startswith(("http://", "https://")):
        return raw
    try:
        parsed = urlparse(raw)
    except Exception:
        return raw.rstrip("/")
    scheme = (parsed.scheme or "https").lower()
    host = (parsed.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = re.sub(r"/{2,}", "/", parsed.path or "").rstrip("/")
    if not host:
        return raw.rstrip("/")
    return f"{scheme}://{host}{path}"


def _source_url_match_keys(value: str | None) -> set[str]:
    normalized = _canonical_source_url(value)
    if not normalized or not normalized.startswith(("http://", "https://")):
        return {normalized} if normalized else set()
    parsed = urlparse(normalized)
    host = parsed.netloc.lower()
    path = (parsed.path or "").rstrip("/")
    if path == "/":
        path = ""
    hosts = {host}
    if host.startswith("www."):
        hosts.add(host[4:])
    else:
        hosts.add(f"www.{host}")
    keys: set[str] = set()
    for scheme in {parsed.scheme.lower()}:
        for variant_host in hosts:
            base = f"{scheme}://{variant_host}{path}"
            keys.add(base)
            keys.add(f"{base}/")
    return {key for key in keys if key}


def _to_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except Exception:
        return None


def _canonical_lead_key(row: dict[str, Any]) -> str:
    parts = [
        _ascii_key(row.get("name")),
        _ascii_key(row.get("city")),
        _ascii_key(row.get("contact")),
        _ascii_key(row.get("source_url")),
    ]
    return "|".join(parts)


def _candidate_source_key(candidate: dict[str, Any]) -> str | None:
    normalized = _canonical_source_url(candidate.get("source_url"))
    if normalized and normalized.startswith(("http://", "https://")):
        return normalized
    contact = _clean(candidate.get("contact"), 500)
    if contact and contact.startswith(("http://", "https://")):
        return _canonical_source_url(contact)
    return None


def _candidate_source_group_key(candidate: dict[str, Any]) -> str | None:
    source_key = _candidate_source_key(candidate)
    if not source_key:
        return None
    variants = sorted(_source_url_match_keys(source_key))
    if not variants:
        return source_key
    return "|".join(variants)


def _candidate_identity_key(candidate: dict[str, Any]) -> str:
    source_key = _candidate_source_group_key(candidate) or _candidate_source_key(candidate)
    if source_key:
        return f"url::{source_key}"
    return "|".join(
        [
            "entity",
            _ascii_key(candidate.get("name")),
            _ascii_key(candidate.get("city")),
            _ascii_key(candidate.get("contact")),
            _ascii_key(candidate.get("category")),
        ]
    )


def _contains_pilot_marker(*values: Any) -> bool:
    haystack = " ".join(str(value or "").strip().lower() for value in values)
    return any(marker in haystack for marker in PILOT_TEXT_MARKERS)


def _contains_pilot_url(*values: Any) -> bool:
    haystack = " ".join(str(value or "").strip().lower() for value in values)
    return any(marker in haystack for marker in PILOT_URL_MARKERS)


def _is_local_test_email(value: str | None) -> bool:
    return str(value or "").strip().lower().endswith(".local")


def _is_pilot_candidate(candidate: dict[str, Any]) -> bool:
    return (
        _contains_pilot_marker(
            candidate.get("name"),
            candidate.get("city"),
            candidate.get("category"),
            candidate.get("note"),
            candidate.get("ai_reason"),
        )
        or _contains_pilot_url(candidate.get("source_url"), candidate.get("contact"))
        or _is_local_test_email(candidate.get("contact"))
    )


def _merge_candidate_rows(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    base, other = (left, right)
    if int(right.get("score") or 0) > int(left.get("score") or 0):
        base, other = right, left
    merged = dict(base)
    for key in ("name", "city", "category", "contact", "source", "source_url", "status", "kind", "store_id"):
        if not merged.get(key) and other.get(key):
            merged[key] = other.get(key)
    merged["score"] = max(int(left.get("score") or 0), int(right.get("score") or 0))
    merged["image_evidence"] = bool(left.get("image_evidence") or right.get("image_evidence"))
    merged["discount_evidence"] = bool(left.get("discount_evidence") or right.get("discount_evidence"))
    merged["food_evidence"] = bool(left.get("food_evidence") or right.get("food_evidence"))
    merged["deep_checked"] = bool(left.get("deep_checked") or right.get("deep_checked"))
    merged["price_evidence"] = bool(left.get("price_evidence") or right.get("price_evidence"))
    notes = []
    for value in (left.get("ai_reason"), left.get("note"), right.get("ai_reason"), right.get("note")):
        cleaned = _clean(value, 260)
        if cleaned and cleaned not in notes:
            notes.append(cleaned)
    if notes:
        merged["note"] = " | ".join(notes[:2])
    if left.get("ai_reason") or right.get("ai_reason"):
        merged["ai_reason"] = _clean(" | ".join(filter(None, [left.get("ai_reason"), right.get("ai_reason")])), 260)
    return merged


def _store_category(db: Session, store_id: int) -> str | None:
    rows = (
        db.query(models.Product.category)
        .filter(models.Product.store_id == store_id, models.Product.category.isnot(None), models.Product.category != "")
        .limit(80)
        .all()
    )
    counter = Counter(str(row[0] or "").lower() for row in rows if row[0])
    return counter.most_common(1)[0][0] if counter else None


def build_search_queries(city: str | None, category: str | None, query: str | None, limit: int = 8) -> list[str]:
    city = _clean(city, 80) or "Srbija"
    category = _clean(category, 80) or "prodavci hrane"
    query = _clean(query, 180)
    aliases = _category_aliases(category)
    base_terms: list[str] = []
    for alias in aliases[:8]:
        base_terms.extend([
            f"{alias} {city} kontakt",
            f"{alias} {city} instagram",
            f"{alias} {city} jelovnik",
            f"{alias} {city} radno vreme",
            f"{alias} {city} dostava",
            f"{alias} {city} porudžbine",
            f"{alias} {city} domaća radinost",
            f"{alias} {city} domaća kuhinja",
            f"{alias} {city} kućna kuhinja",
            f"{alias} {city} gotova jela",
            f"{alias} {city} jelovnik sa slikama",
            f"{alias} {city} meni sa slikama i cenama",
            f"{alias} {city} akcijski meni sa cenama",
            f"{alias} {city} dnevni meni popust",
            f"{alias} {city} proizvodi na popustu sa slikom",
            f"{alias} {city} artikli sa slikama i cenama",
            f"{alias} {city} snizenje proizvoda sa slikama",
            f"{alias} {city} akcijska ponuda sa cenama",
            f"{alias} {city} katalozi akcija hrana",
            f"{alias} {city} maloprodaja hrane akcija",
            f"{alias} {city} restoran proizvodi sa slikom i cenom",
            f"{alias} {city} pekara proizvodi sa slikom i cenom",
            f"{alias} {city} market proizvodi sa slikom i cenom",
            f"{alias} {city} prodavnica prehrane akcija slika cena",
            f"{alias} {city} facebook",
            f"{alias} {city} akcija",
            f"{alias} {city} popust",
            f"{alias} {city} sniženje",
            f"{alias} {city} slike",
            f"{alias} {city} galerija",
            f"{alias} {city} meni akcija",
            f"{alias} {city} ponuda fotografije",
            f"{alias} {city} proizvodi sa slikom",
            f"{alias} {city} proizvodi na akciji",
            f"{alias} {city} snizeni proizvodi",
            f"{alias} {city} fotografije proizvoda",
            f"{alias} {city} glovo",
            f"{alias} {city} wolt",
            f"{alias} {city} proizvodi na snizenju sa slikom",
            f"{alias} {city} akcijska ponuda sa slikama",
            f"{alias} {city} dostava akcija meni",
            f"{alias} {city} dnevna ponuda popust",
            f"{alias} {city} domaca hrana akcija",
            f"{alias} {city} proizvodi sa cenama i slikama",
            f"{alias} {city} snizeni obroci fotografije",
            f"{alias} {city} akcijski meni sa slikama",
            f"{alias} {city} proizvod katalog popust",
            f"{alias} {city} cenovnik pdf akcija hrana",
            f"{alias} {city} katalog pdf snizenje hrane",
            f"{alias} {city} meni pdf slike cene",
            f"{alias} {city} restoran pekara market popust slika",
            f"{alias} {city} domaca radinost hrana slike kontakt",
            f"{alias} {city} maloprodaja prehrana akcija slike",
            f"{alias} {city} proizvodi sa slikom i cenom",
            f"{alias} {city} proizvodi na popustu sa cenom",
            f"{alias} {city} proizvodi na snizenju sa cenom",
            f"{alias} {city} artikli sa slikom i popustom",
            f"{alias} {city} artikli sa slikom i cenom na akciji",
            f"{alias} {city} artikli na snizenju sa fotografijom",
            f"{alias} {city} restoran akcijski meni slike cena",
            f"{alias} {city} pekara akcijska ponuda slike cena",
            f"{alias} {city} prodavnica prehrana popust slike cena",
            f"{alias} {city} maloprodaja hrane snizenje slike cena",
            f"{alias} {city} supermarket prehrana slike cena popust",
            f"{alias} {city} mini market akcija slike cena",
            f"{alias} {city} diskont ponuda slike cena popust",
            f"{alias} {city} domaca radinost hrana slike cena",
            f"{alias} {city} kucna kuhinja slike cena kontakt",
            f"{alias} {city} domaci kolaci slike cena porudzbina",
            f"{alias} {city} gotova jela slike cena kontakt",
            f"{alias} {city} ketering slike cena kontakt",
            f"{alias} {city} poslastičarnica slike cena popust",
            f"{alias} {city} market dnevna akcija cena slika",
            f"{alias} {city} diskont prehrana akcija slike cena",
            f"{alias} {city} restoran akcije slike cena kontakt",
            f"{alias} {city} pekara akcije slike cena kontakt",
            f"{alias} {city} prodavnica hrane akcija kontakt slike",
            f"{alias} {city} maloprodaja prehrana katalog kontakt",
        ])
        for source_hint in SEARCH_SOURCE_HINTS:
            base_terms.extend([
                f"{source_hint} {alias} {city}",
                f"{source_hint} {alias} {city} akcija",
                f"{source_hint} {alias} {city} popust",
                f"{source_hint} {alias} {city} fotografije",
                f"{source_hint} {alias} {city} slike cena",
                f"{source_hint} {alias} {city} popust cena",
                f"{source_hint} {alias} {city} snizenje cena",
                f"{source_hint} {alias} {city} akcija slika cena",
                f"{source_hint} {alias} {city} proizvodi na popustu sa slikom",
                f"{source_hint} {alias} {city} jelovnik sa slikama i cenama",
            ])
    if query:
        base_terms.insert(0, f"{category} {city} {query}")
        base_terms.insert(1, f"{category} {city} {query} slika popust")
        base_terms.insert(2, f"{category} {city} {query} slika cena popust")
        base_terms.insert(3, f"{category} {city} {query} na snizenju sa slikom i cenom")
    max_queries = min(max(limit * 8, 48), 120)
    return list(dict.fromkeys(base_terms))[:max_queries]


def _score_candidate(candidate: dict[str, Any], city: str | None, category: str | None, query: str | None) -> int:
    score = 45
    blob = " ".join(str(candidate.get(k) or "") for k in ["name", "city", "category", "contact", "source_url", "note"])
    hay = _ascii_key(blob)
    if city and _ascii_key(city) in hay:
        score += 18
    cat_tokens = _tokens(category)
    if cat_tokens and cat_tokens & _tokens(blob):
        score += 16
    query_tokens = _tokens(query)
    if query_tokens:
        score += min(18, 6 * len(query_tokens & _tokens(blob)))
    if candidate.get("source_url"):
        score += 6
    if candidate.get("contact"):
        score += 6
    if candidate.get("kind") == "existing_store":
        score += 8
    if candidate.get("image_evidence"):
        score += 12
    if candidate.get("discount_evidence"):
        score += 12
    if candidate.get("price_evidence"):
        score += 10
    if candidate.get("food_evidence"):
        score += 10
    if candidate.get("deep_checked"):
        score += 6
    return max(0, min(score, 100))


def _store_has_discounted_products(
    db: Session,
    store_id: int,
    require_image_evidence: bool,
    require_discount_signal: bool,
    require_price_evidence: bool,
) -> bool:
    products = (
        db.query(models.Product)
        .filter(models.Product.store_id == store_id, models.Product.status.in_(("public_discount", "seller_verified", "near_expiry")))
        .limit(80)
        .all()
    )
    if not products:
        return False
    for product in products:
        has_image = bool(str(product.image_url or "").strip())
        original = _to_float(product.original_price)
        discounted = _to_float(product.discounted_price)
        discount_percent = _to_float(product.discount_percent)
        has_discount = bool(
            discount_percent and discount_percent > 0
            or (original is not None and discounted is not None and discounted < original)
            or discounted is not None
        )
        has_price = original is not None or discounted is not None
        if require_image_evidence and not has_image:
            continue
        if require_discount_signal and not has_discount:
            continue
        if require_price_evidence and not has_price:
            continue
        return True
    return False


def _existing_store_candidates(
    db: Session,
    city: str | None,
    category: str | None,
    query: str | None,
    limit: int,
    require_image_evidence: bool,
    require_discount_signal: bool,
    require_price_evidence: bool,
) -> list[dict[str, Any]]:
    stores = db.query(models.Store).order_by(models.Store.created_at.desc()).limit(2000).all()
    city_key = _ascii_key(city)
    category_tokens: set[str] = set()
    for alias in _category_aliases(category):
        category_tokens.update(_tokens(alias))
    query_tokens = _tokens(query)
    candidates: list[dict[str, Any]] = []
    for store in stores:
        if (
            _contains_pilot_marker(store.name, store.address, store.blocked_reason)
            or _contains_pilot_url(store.website)
            or _is_local_test_email(store.website)
        ):
            continue
        inferred_category = _store_category(db, store.id)
        blob = " ".join([
            store.name or "",
            store.city or "",
            store.address or "",
            store.website or "",
            store.phone or "",
            inferred_category or "",
        ])
        tokens = _tokens(blob)
        if city_key and city_key not in _ascii_key(blob):
            continue
        if category_tokens and not (category_tokens & tokens):
            continue
        if query_tokens and not (query_tokens & tokens):
            continue
        if not _store_has_discounted_products(
            db,
            store.id,
            require_image_evidence,
            require_discount_signal,
            require_price_evidence,
        ):
            continue
        row = {
            "kind": "existing_store",
            "name": store.name,
            "city": store.city,
            "category": inferred_category or category,
            "contact": store.phone or store.website or "",
            "source_url": store.website or "",
            "status": "approved" if store.verified else "new",
            "note": f"Postoji u bazi prodavaca kao Store #{store.id}; verified={bool(store.verified)}.",
            "store_id": store.id,
            "image_evidence": True,
            "discount_evidence": True,
            "food_evidence": True,
            "price_evidence": True,
        }
        row["score"] = _score_candidate(row, city, category, query)
        candidates.append(row)
    return sorted(candidates, key=lambda x: int(x.get("score") or 0), reverse=True)[:limit]


def _research_task_candidates(city: str | None, category: str | None, query: str | None, limit: int) -> list[dict[str, Any]]:
    city = _clean(city, 80) or "Srbija"
    category = _clean(category, 80) or "hrana"
    queries = build_search_queries(city, category, query, limit=max(limit, 4))
    rows: list[dict[str, Any]] = []
    for idx, search in enumerate(queries[:limit], start=1):
        zone = DEFAULT_ZONES[(idx - 1) % len(DEFAULT_ZONES)]
        row = {
            "kind": "research_task",
            "name": f"AI pretraga: {category} {city} - {zone}",
            "city": city,
            "category": category,
            "contact": "",
            "source": "ai_research_task",
            "source_url": "",
            "status": "needs_review",
            "score": max(58, 78 - idx * 3),
            "note": f"Zadatak za pronalazak realnih prodavaca: restorani, pekare, prodavnice, maloprodaja i domaća radinost. Pretraži: {search}. Potvrdi da imaju slike proizvoda, jasnu cenu i aktivan popust, pa admin ručno odobrava slanje ponude.",
        }
        rows.append(row)
    return rows


def _find_contacts(text: str) -> list[str]:
    contacts: list[str] = []
    seen: set[str] = set()
    for match in re.findall(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", text or ""):
        if match not in seen:
            seen.add(match)
            contacts.append(match)
    for match in re.findall(r"(\+?\d[\d\s()./-]{6,}\d)", text or ""):
        clean = re.sub(r"\s+", " ", match).strip()
        if clean not in seen:
            seen.add(clean)
            contacts.append(clean)
    return contacts


def _collect_deep_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    base_domain = urlparse(base_url).netloc.lower()
    scored_links: list[tuple[int, str]] = []
    seen: set[str] = set()
    for anchor in soup.select("a[href]"):
        href = anchor.get("href") or ""
        label = " ".join(filter(None, [anchor.get_text(" ", strip=True), href])).lower()
        if not any(hint in label for hint in DEEP_LINK_HINTS):
            continue
        absolute = urljoin(base_url, href)
        parsed = urlparse(absolute)
        if not parsed.scheme.startswith("http"):
            continue
        if parsed.netloc.lower() != base_domain:
            continue
        normalized = absolute.split("#", 1)[0]
        if normalized in seen:
            continue
        seen.add(normalized)
        score = sum(weight for hint, weight in DEEP_PRIORITY_HINTS.items() if hint in label)
        score += max(0, 4 - normalized.count("/"))
        scored_links.append((score, normalized))
    scored_links.sort(key=lambda item: (-item[0], item[1]))
    return [url for _, url in scored_links[:18]]


def _page_evidence(url: str, timeout: float, deep_search: bool) -> dict[str, Any]:
    headers = {"User-Agent": "SacuvajHranuSellerDiscovery/1.0 (+kontakt@sacuvaj-hranu.rs)"}
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")
    text_parts = soup.stripped_strings
    raw_text = " ".join(list(text_parts)[:900])
    text = _ascii_key(raw_text)
    combined_text = text
    image_hits = 0
    price_hits = len(re.findall(r"\b\d{2,6}\s?(?:rsd|din|eur|€)\b", raw_text, flags=re.IGNORECASE))
    for img in soup.select("img")[:40]:
        src = (img.get("src") or "").lower()
        alt = (img.get("alt") or "").lower()
        if any(term in src or term in alt for term in FOOD_TERMS + IMAGE_TERMS):
            image_hits += 1
    for meta in soup.select('meta[property="og:image"], meta[name="twitter:image"], meta[itemprop="image"]')[:8]:
        content = (meta.get("content") or "").lower()
        if content.startswith(("http://", "https://")):
            image_hits += 1
    contacts = _find_contacts(raw_text)
    deep_checked = False
    if deep_search:
        for link in _collect_deep_links(soup, url):
            try:
                nested = requests.get(link, headers=headers, timeout=timeout)
                nested.raise_for_status()
                nested_soup = BeautifulSoup(nested.text, "lxml")
                nested_text = " ".join(list(nested_soup.stripped_strings)[:500])
                nested_key = _ascii_key(nested_text)
                combined_text += " " + nested_key
                price_hits += len(re.findall(r"\b\d{2,6}\s?(?:rsd|din|eur|€)\b", nested_text, flags=re.IGNORECASE))
                image_hits += sum(
                    1
                    for img in nested_soup.select("img")[:25]
                    if any(term in (img.get("src") or "").lower() or term in (img.get("alt") or "").lower() for term in FOOD_TERMS + IMAGE_TERMS)
                )
                image_hits += sum(
                    1
                    for meta in nested_soup.select('meta[property="og:image"], meta[name="twitter:image"], meta[itemprop="image"]')[:6]
                    if (meta.get("content") or "").lower().startswith(("http://", "https://"))
                )
                contacts.extend(_find_contacts(nested_text))
                deep_checked = True
            except Exception:
                continue
    image_evidence = image_hits > 0
    discount_evidence = any(term in combined_text for term in DISCOUNT_TERMS) or bool(re.search(r"\b\d{1,2}\s?%\b", combined_text))
    food_evidence = any(term in combined_text for term in FOOD_TERMS)
    uniq_contacts = []
    seen_contacts: set[str] = set()
    for contact in contacts:
        if contact in seen_contacts:
            continue
        seen_contacts.add(contact)
        uniq_contacts.append(contact)
    return {
        "title": _clean(soup.title.get_text(" ", strip=True) if soup.title else "", 180),
        "contact": uniq_contacts[0] if uniq_contacts else None,
        "note": _clean(raw_text, 320),
        "image_evidence": image_evidence,
        "discount_evidence": discount_evidence,
        "food_evidence": food_evidence,
        "deep_checked": deep_checked,
        "price_evidence": price_hits > 0,
    }


def _web_search_candidates(
    city: str | None,
    category: str | None,
    query: str | None,
    limit: int,
    require_image_evidence: bool,
    require_discount_signal: bool,
    require_price_evidence: bool,
    deep_search: bool,
) -> list[dict[str, Any]]:
    if os.getenv("SELLER_DISCOVERY_WEB_ENABLED", "true").lower() not in {"1", "true", "yes", "da", "on"}:
        return []
    timeout = float(os.getenv("SELLER_DISCOVERY_TIMEOUT_SECONDS", "12"))
    candidates: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    query_budget = max(24, min(max(limit, 1) * 8, 96))
    max_candidate_pool = max(limit * 6, 36)
    search_queries = build_search_queries(city, category, query, limit=query_budget)
    for query_index, search_query in enumerate(search_queries[:query_budget], start=1):
        url = "https://duckduckgo.com/html/?" + urlencode({"q": search_query})
        try:
            response = requests.get(
                url,
                headers={"User-Agent": "SacuvajHranuSellerDiscovery/1.0 (+kontakt@sacuvaj-hranu.rs)"},
                timeout=timeout,
            )
            response.raise_for_status()
        except Exception:
            continue
        soup = BeautifulSoup(response.text, "lxml")
        max_results_per_query = min(max(limit * 4, 24), 48)
        for result in soup.select(".result")[:max_results_per_query]:
            link = result.select_one(".result__a")
            snippet = result.select_one(".result__snippet")
            title = _clean(link.get_text(" ", strip=True) if link else "", 180)
            href = _clean(link.get("href") if link else "", 500)
            if not title or not href:
                continue
            parsed = urlparse(href)
            if not parsed.scheme.startswith("http"):
                continue
            normalized_href = _canonical_source_url(href)
            if not normalized_href:
                continue
            if normalized_href in seen_urls:
                continue
            if _contains_pilot_marker(title, snippet.get_text(" ", strip=True) if snippet else "") or _contains_pilot_url(normalized_href):
                continue
            try:
                evidence = _page_evidence(normalized_href, timeout=timeout, deep_search=deep_search)
            except Exception:
                evidence = {
                    "title": title,
                    "contact": None,
                    "note": _clean(snippet.get_text(" ", strip=True) if snippet else f"Web rezultat za: {search_query}", 300),
                    "image_evidence": False,
                    "discount_evidence": False,
                    "food_evidence": bool(category and _ascii_key(category) in _ascii_key(title)),
                    "deep_checked": False,
                    "price_evidence": False,
                }
            if deep_search and not evidence["deep_checked"]:
                continue
            if require_image_evidence and not evidence["image_evidence"]:
                continue
            if require_discount_signal and not evidence["discount_evidence"]:
                continue
            if require_price_evidence and not evidence.get("price_evidence"):
                continue
            if not evidence["food_evidence"]:
                continue
            row = {
                "kind": "web_result",
                "name": evidence.get("title") or title,
                "city": city,
                "category": category,
                "contact": evidence.get("contact") or href,
                "source": "web_search",
                "source_url": normalized_href,
                "status": "new",
                "note": evidence.get("note") or _clean(snippet.get_text(" ", strip=True) if snippet else f"Web rezultat za: {search_query}", 300),
                "image_evidence": evidence["image_evidence"],
                "discount_evidence": evidence["discount_evidence"],
                "food_evidence": evidence["food_evidence"],
                "deep_checked": evidence["deep_checked"],
                "price_evidence": evidence.get("price_evidence", False),
            }
            if _is_pilot_candidate(row):
                continue
            row["score"] = _score_candidate(row, city, category, query)
            candidates.append(row)
            seen_urls.add(normalized_href)
            if len(candidates) >= max_candidate_pool:
                break
        if len(candidates) >= max_candidate_pool and query_index >= min(12, query_budget):
            break
    return sorted(candidates, key=lambda item: int(item.get("score") or 0), reverse=True)[:max_candidate_pool]


def _collapse_candidates_by_source(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    collapsed: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        identity_key = _candidate_source_group_key(candidate) or _candidate_identity_key(candidate)
        existing = collapsed.get(identity_key)
        collapsed[identity_key] = _merge_candidate_rows(existing, candidate) if existing else dict(candidate)
    return sorted(collapsed.values(), key=lambda x: int(x.get("score") or 0), reverse=True)


def _is_benign_warning_message(message: str | None) -> bool:
    lower = str(message or "").strip().lower()
    if not lower:
        return True
    return (
        "duplikati preskočeni" in lower
        or "duplikati preskoceni" in lower
        or "već postojali u bazi" in lower
        or "vec postojali u bazi" in lower
    )


def _openai_rank_candidates(criteria: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key or not candidates:
        return {"used": False, "summary": "OpenAI ključ nije podešen ili nema kandidata za AI rangiranje.", "candidates": candidates}
    model = os.getenv("OPENAI_MODEL", os.getenv("AI_ASSISTANT_MODEL", "gpt-4o-mini")).strip() or "gpt-4o-mini"
    timeout = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "12"))
    system = (
        "Ti si B2B growth asistent za aplikaciju Sačuvaj Hranu u Srbiji. "
        "Rangiraš postojeće kandidate za prodavce hrane. Ne smeš izmišljati nove firme, telefone, mejlove ili URL adrese. "
        "Vrati isključivo validan JSON sa poljima summary i candidates. candidates je lista istih kandidata sa score 0-100 i kratkim reason."
    )
    payload = {
        "criteria": criteria,
        "candidates": candidates[:25],
        "rules": [
            "Prednost imaju prodavci hrane sa jasnim kontaktom, gradom i kategorijom.",
            "Novi prodavac ne ide javno dok nije ručno proveren i verified=true.",
            "Ako je kandidat samo research_task, koristi ga kao zadatak, ne kao realnog prodavca.",
        ],
    }
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
                "temperature": 0.2,
                "max_tokens": 1800,
                "response_format": {"type": "json_object"},
            },
            timeout=timeout,
        )
        response.raise_for_status()
        content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "{}")
        data = json.loads(content)
    except Exception:
        return {"used": False, "summary": "AI rangiranje nije uspelo; korišćeno je lokalno bodovanje.", "candidates": candidates}

    ranked = data.get("candidates") if isinstance(data, dict) else None
    if not isinstance(ranked, list):
        return {"used": False, "summary": "AI odgovor nije imao listu kandidata; korišćeno je lokalno bodovanje.", "candidates": candidates}
    by_name = {_ascii_key(c.get("name")): c for c in candidates}
    merged: list[dict[str, Any]] = []
    for item in ranked:
        if not isinstance(item, dict):
            continue
        base = by_name.get(_ascii_key(item.get("name")))
        if not base:
            continue
        row = dict(base)
        if item.get("score") is not None:
            try:
                row["score"] = max(0, min(int(float(item.get("score"))), 100))
            except Exception:
                pass
        if item.get("reason"):
            row["ai_reason"] = _clean(item.get("reason"), 260)
        merged.append(row)
    seen = {_canonical_lead_key(x) for x in merged}
    for item in candidates:
        if _canonical_lead_key(item) not in seen:
            merged.append(item)
    return {
        "used": True,
        "summary": _clean(data.get("summary"), 600) or "AI je rangirao kandidate za kontaktiranje.",
        "candidates": sorted(merged, key=lambda x: int(x.get("score") or 0), reverse=True),
    }


def _upsert_leads(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    rows = read_json(LEADS_FILE, [])
    if not isinstance(rows, list):
        rows = []
    index = {_canonical_lead_key(row): idx for idx, row in enumerate(rows) if isinstance(row, dict)}
    created = 0
    updated = 0
    saved: list[dict[str, Any]] = []
    now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    for candidate in candidates:
        if _is_pilot_candidate(candidate):
            continue
        row = {
            "name": _clean(candidate.get("name"), 180) or "AI lead",
            "city": _clean(candidate.get("city"), 80),
            "category": _clean(candidate.get("category"), 80),
            "contact": _clean(candidate.get("contact") or candidate.get("source_url"), 500),
            "source": _clean(candidate.get("source") or candidate.get("kind") or "ai_seller_discovery", 80),
            "source_url": _clean(candidate.get("source_url"), 500),
            "status": _clean(candidate.get("status"), 40) or "needs_review",
            "score": int(candidate.get("score") or 50),
            "note": _clean(candidate.get("ai_reason") or candidate.get("note"), 500),
            "kind": _clean(candidate.get("kind"), 80),
            "store_id": candidate.get("store_id"),
        }
        key = _canonical_lead_key(row)
        if key in index:
            existing = dict(rows[index[key]])
            existing.update({k: v for k, v in row.items() if v not in (None, "")})
            existing["updated_at"] = now
            rows[index[key]] = existing
            saved.append(existing)
            updated += 1
        else:
            row["id"] = f"{int(datetime.utcnow().timestamp() * 1000)}-{created}"
            row["created_at"] = now
            row["updated_at"] = now
            rows.append(row)
            saved.append(row)
            created += 1
    write_json(LEADS_FILE, rows[-5000:])
    return {"created": created, "updated": updated, "leads": saved}


def _store_exists(db: Session, name: str, city: str | None, website: str | None) -> models.Store | None:
    query = db.query(models.Store).filter(models.Store.name == name)
    if city:
        query = query.filter(models.Store.city == city)
    store = query.first()
    if store:
        return store
    if website:
        website_variants = list(_source_url_match_keys(website))
        return (
            db.query(models.Store)
            .filter(
                models.Store.website.in_(website_variants)
            )
            .first()
        )
    return None


def _import_candidates_to_stores(db: Session, candidates: list[dict[str, Any]], create_sources: bool = True) -> dict[str, int]:
    candidates = _collapse_candidates_by_source(candidates)
    deduped_candidates: dict[str, dict[str, Any]] = {}
    passthrough_candidates: list[dict[str, Any]] = []
    for candidate in candidates:
        source_key = _candidate_source_group_key(candidate)
        if source_key:
            existing = deduped_candidates.get(source_key)
            deduped_candidates[source_key] = _merge_candidate_rows(existing, candidate) if existing else dict(candidate)
        else:
            passthrough_candidates.append(candidate)
    candidates = [*deduped_candidates.values(), *passthrough_candidates]
    created_stores = 0
    updated_stores = 0
    created_sources = 0
    skipped_sources = 0
    seen_source_urls: set[str] = set()
    existing_source_urls: set[str] = set()
    for (url,) in db.query(models.Source.url).filter(models.Source.url.isnot(None)).all():
        existing_source_urls.update(_source_url_match_keys(str(url or "")))
    for candidate in candidates:
        if candidate.get("kind") == "research_task":
            continue
        if _is_pilot_candidate(candidate):
            skipped_sources += 1
            continue
        name = _clean(candidate.get("name"), 180)
        if not name:
            continue
        city = _clean(candidate.get("city"), 80)
        website = _clean(candidate.get("source_url") or candidate.get("contact"), 500)
        normalized_website = _canonical_source_url(website)
        phone = None if website and website.startswith("http") else _clean(candidate.get("contact"), 80)
        store = _store_exists(db, name, city, normalized_website)
        if store:
            changed = False
            if city and not store.city:
                store.city = city
                changed = True
            if normalized_website and not store.website and normalized_website.startswith("http"):
                store.website = normalized_website
                changed = True
            if phone and not store.phone:
                store.phone = phone
                changed = True
            updated_stores += 1 if changed else 0
        else:
            store = models.Store(name=name, city=city, website=normalized_website if normalized_website and normalized_website.startswith("http") else None, phone=phone, verified=False, seller_type="home_producer" if "domac" in _ascii_key(candidate.get("category")) else "business")
            db.add(store)
            db.flush()
            created_stores += 1
        if create_sources and normalized_website and normalized_website.startswith("http"):
            website_keys = _source_url_match_keys(normalized_website)
            if website_keys & seen_source_urls or website_keys & existing_source_urls:
                skipped_sources += 1
                continue
            seen_source_urls.update(website_keys)
            try:
                with db.begin_nested():
                    source = (
                        db.query(models.Source)
                        .filter(models.Source.url.in_(list(website_keys)))
                        .first()
                    )
                    if not source:
                        source = models.Source(
                            name=name,
                            url=normalized_website,
                            city=city,
                            source_type="ai_seller_discovery",
                            crawl_frequency="weekly",
                            active=True,
                        )
                        db.add(source)
                        db.flush([source])
                        created_sources += 1
            except IntegrityError:
                skipped_sources += 1
            except Exception:
                skipped_sources += 1
            existing_source_urls.update(website_keys)
    db.commit()
    return {
        "created_stores": created_stores,
        "updated_stores": updated_stores,
        "created_sources": created_sources,
        "skipped_sources": skipped_sources,
    }


def discover_sellers(
    db: Session,
    *,
    city: str | None,
    category: str | None,
    query: str | None,
    limit: int = 12,
    include_existing: bool = True,
    include_research_tasks: bool = True,
    web_search: bool = True,
    import_to_stores: bool = False,
    create_sources: bool = True,
    require_image_evidence: bool = True,
    require_discount_signal: bool = True,
    require_price_evidence: bool = True,
    deep_search: bool = True,
) -> dict[str, Any]:
    limit = max(1, min(int(limit or 12), 50))
    criteria = {
        "city": _clean(city, 80),
        "category": _clean(category, 80),
        "query": _clean(query, 240),
        "limit": limit,
        "require_image_evidence": bool(require_image_evidence),
        "require_discount_signal": bool(require_discount_signal),
        "require_price_evidence": bool(require_price_evidence),
        "deep_search": bool(deep_search),
    }
    warnings: list[str] = []
    candidates: list[dict[str, Any]] = []
    if include_existing:
        try:
            candidates.extend(
                _existing_store_candidates(
                    db,
                    city,
                    category,
                    query,
                    limit=limit,
                    require_image_evidence=require_image_evidence,
                    require_discount_signal=require_discount_signal,
                    require_price_evidence=require_price_evidence,
                )
            )
        except Exception as exc:
            db.rollback()
            warnings.append(friendly_discovery_error(exc, "Postojeći prodavci trenutno nisu učitani."))
    if web_search:
        try:
            candidates.extend(
                _web_search_candidates(
                    city,
                    category,
                    query,
                    limit=limit,
                    require_image_evidence=require_image_evidence,
                    require_discount_signal=require_discount_signal,
                    require_price_evidence=require_price_evidence,
                    deep_search=deep_search,
                )
            )
        except Exception as exc:
            warnings.append(friendly_discovery_error(exc, "Web pretraga nije završena za ovaj zahtev."))
    if include_research_tasks and len(candidates) < limit:
        try:
            candidates.extend(_research_task_candidates(city, category, query, limit=limit - len(candidates)))
        except Exception as exc:
            warnings.append(friendly_discovery_error(exc, "Zadaci za ručnu pretragu trenutno nisu napravljeni."))

    deduped: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        if _is_pilot_candidate(candidate):
            continue
        try:
            candidate["score"] = _score_candidate(candidate, city, category, query)
            key = _candidate_identity_key(candidate)
            existing = deduped.get(key)
            deduped[key] = _merge_candidate_rows(existing, candidate) if existing else dict(candidate)
        except Exception as exc:
            warnings.append(friendly_discovery_error(exc, "Jedan kandidat je preskočen tokom bodovanja."))
    candidates = _collapse_candidates_by_source(list(deduped.values()))[:limit]

    try:
        ai = _openai_rank_candidates(criteria, candidates)
    except Exception as exc:
        warnings.append(friendly_discovery_error(exc, "AI rangiranje nije uspelo za ovaj zahtev."))
        ai = {"used": False, "summary": "AI rangiranje nije uspelo; prikazani su lokalno rangirani kandidati.", "candidates": candidates}
    final_candidates = _collapse_candidates_by_source(
        [candidate for candidate in ai["candidates"] if not _is_pilot_candidate(candidate)]
    )[:limit]
    try:
        lead_result = _upsert_leads(final_candidates)
    except Exception as exc:
        warnings.append(friendly_discovery_error(exc, "Leadovi trenutno nisu snimljeni."))
        lead_result = {"created": 0, "updated": 0, "leads": []}
    if import_to_stores:
        try:
            import_result = _import_candidates_to_stores(db, final_candidates, create_sources=create_sources)
        except Exception as exc:
            warnings.append(friendly_discovery_error(exc, "Import u prodavce trenutno nije uspeo."))
            db.rollback()
            import_result = {"created_stores": 0, "updated_stores": 0, "created_sources": 0, "skipped_sources": 0}
    else:
        import_result = {"created_stores": 0, "updated_stores": 0, "created_sources": 0, "skipped_sources": 0}
    run_payload = {
        "criteria": criteria,
        "candidates": len(final_candidates),
        "leads_created": lead_result["created"],
        "leads_updated": lead_result["updated"],
        "import_to_stores": import_to_stores,
        "created_stores": import_result["created_stores"],
        "created_sources": import_result["created_sources"],
        "ai_used": ai["used"],
        "web_search_requested": bool(web_search),
        "web_search_enabled": os.getenv("SELLER_DISCOVERY_WEB_ENABLED", "true").lower() in {"1", "true", "yes", "da", "on"},
        "warnings": warnings,
    }
    try:
        run = append_json_row(RUNS_FILE, run_payload, max_rows=500)
    except Exception as exc:
        warnings.append(friendly_discovery_error(exc, "Istorija pretrage trenutno nije sačuvana."))
        run = {**run_payload, "id": None}
    visible_warnings = []
    seen_warning_messages: set[str] = set()
    for warning in warnings:
        normalized = _normalize_discovery_warning_text(warning)
        if not normalized or normalized in seen_warning_messages:
            continue
        seen_warning_messages.add(normalized)
        visible_warnings.append(normalized)
    blocking_warnings = [warning for warning in visible_warnings if not _is_benign_warning_message(warning)]
    return {
        "ok": not blocking_warnings,
        "criteria": criteria,
        "search_queries": build_search_queries(city, category, query),
        "ai_used": ai["used"],
        "ai_summary": ai["summary"],
        "web_search_enabled": run["web_search_enabled"],
        "summary": {
            "candidates": len(final_candidates),
            "leads_created": lead_result["created"],
            "leads_updated": lead_result["updated"],
            **import_result,
        },
        "warnings": visible_warnings,
        "candidates": final_candidates,
        "leads": lead_result["leads"],
        "run_id": run["id"],
        "message": (
            "AI pretraga prodavaca je završena. Kriterijumi su strogi: traže se slike proizvoda, cena, signal sniženja i dublja provera stranica kroz restorane, pekare, prodavnice, maloprodaju i domaću radinost. "
            "Novi kandidati su leadovi; prodavci ostaju neverifikovani dok ih ručno ne odobrimo."
            if not blocking_warnings
            else "AI pretraga je završena u sigurnom režimu. Pogledaj upozorenja, ali stranica više ne puca."
        ),
    }
