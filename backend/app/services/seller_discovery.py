from __future__ import annotations

import json
import os
import re
import unicodedata
from collections import Counter
from datetime import datetime
from typing import Any
from urllib.parse import urlencode, urlparse

import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from .. import models
from .json_store import read_json, write_json, append_json_row

LEADS_FILE = "growth_leads.json"
RUNS_FILE = "seller_discovery_runs.json"

DEFAULT_CITIES = ["Beograd", "Novi Sad", "Nis", "Kragujevac", "Subotica", "Cacak", "Kraljevo", "Zrenjanin"]
DEFAULT_ZONES = ["centar", "naselje", "pijaca", "poslovna zona", "studentska zona", "glavna ulica"]
CATEGORY_ALIASES = {
    "pekara": ["pekara", "pekar", "pecivo", "hleb", "burek", "kifla"],
    "restoran": ["restoran", "gotova jela", "rucak", "ručak", "meni", "dnevni meni"],
    "market": ["market", "prodavnica", "prehrana", "mini market", "supermarket"],
    "poslastice": ["poslastice", "kolaci", "kolači", "torte", "slatko"],
    "zdrava hrana": ["zdrava hrana", "salate", "vege", "bio", "organic"],
    "domaca hrana": ["domaca hrana", "domaća hrana", "domaca radinost", "domaća radinost", "kuvana jela", "porudzbine hrane"],
    "domaca radinost": ["domaca radinost", "domaća radinost", "zimnica", "ajvar", "kolaci po porudzbini", "torte po porudzbini"],
    "kucna kuhinja": ["kucna kuhinja", "kućna kuhinja", "domaca kuhinja", "domaća kuhinja", "rucak za poneti"],
    "mali proizvodjaci": ["mali proizvodjaci hrane", "gazdinstvo", "OPG", "domaci proizvodi", "pijaca"],
}


def _ascii_key(value: str | None) -> str:
    value = value or ""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _tokens(value: str | None) -> set[str]:
    return {x for x in _ascii_key(value).split() if len(x) >= 3}


def _clean(value: Any, limit: int = 255) -> str | None:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit] if text else None


def _canonical_lead_key(row: dict[str, Any]) -> str:
    parts = [
        _ascii_key(row.get("name")),
        _ascii_key(row.get("city")),
        _ascii_key(row.get("contact")),
        _ascii_key(row.get("source_url")),
    ]
    return "|".join(parts)


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
    category = _clean(category, 80) or "hrana"
    query = _clean(query, 180)
    aliases = CATEGORY_ALIASES.get(_ascii_key(category), [category])
    base_terms: list[str] = []
    for alias in aliases[:3]:
        base_terms.extend([
            f"{alias} {city} kontakt",
            f"{alias} {city} instagram",
            f"{alias} {city} jelovnik",
            f"{alias} {city} radno vreme",
            f"{alias} {city} dostava",
            f"{alias} {city} porudžbine",
            f"{alias} {city} domaća radinost",
            f"{alias} {city} facebook",
        ])
    if query:
        base_terms.insert(0, f"{category} {city} {query}")
    return list(dict.fromkeys(base_terms))[:limit]


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
    return max(0, min(score, 100))


def _existing_store_candidates(db: Session, city: str | None, category: str | None, query: str | None, limit: int) -> list[dict[str, Any]]:
    stores = db.query(models.Store).order_by(models.Store.created_at.desc()).limit(2000).all()
    city_key = _ascii_key(city)
    category_tokens = _tokens(category)
    query_tokens = _tokens(query)
    candidates: list[dict[str, Any]] = []
    for store in stores:
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
            "note": f"Zadatak za pronalazak realnih prodavaca i domaće radinosti. Pretraži: {search}. Skupi kontakt, pa admin ručno odobrava slanje ponude.",
        }
        rows.append(row)
    return rows


def _web_search_candidates(city: str | None, category: str | None, query: str | None, limit: int) -> list[dict[str, Any]]:
    if os.getenv("SELLER_DISCOVERY_WEB_ENABLED", "false").lower() not in {"1", "true", "yes", "da", "on"}:
        return []
    timeout = float(os.getenv("SELLER_DISCOVERY_TIMEOUT_SECONDS", "10"))
    candidates: list[dict[str, Any]] = []
    for search_query in build_search_queries(city, category, query, limit=4):
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
        for result in soup.select(".result")[:limit]:
            link = result.select_one(".result__a")
            snippet = result.select_one(".result__snippet")
            title = _clean(link.get_text(" ", strip=True) if link else "", 180)
            href = _clean(link.get("href") if link else "", 500)
            if not title or not href:
                continue
            parsed = urlparse(href)
            if not parsed.scheme.startswith("http"):
                continue
            row = {
                "kind": "web_result",
                "name": title,
                "city": city,
                "category": category,
                "contact": href,
                "source": "web_search",
                "source_url": href,
                "status": "new",
                "note": _clean(snippet.get_text(" ", strip=True) if snippet else f"Web rezultat za: {search_query}", 300),
            }
            row["score"] = _score_candidate(row, city, category, query)
            candidates.append(row)
            if len(candidates) >= limit:
                return candidates
    return candidates[:limit]


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
        return db.query(models.Store).filter(models.Store.website == website).first()
    return None


def _import_candidates_to_stores(db: Session, candidates: list[dict[str, Any]], create_sources: bool = True) -> dict[str, int]:
    created_stores = 0
    updated_stores = 0
    created_sources = 0
    for candidate in candidates:
        if candidate.get("kind") == "research_task":
            continue
        name = _clean(candidate.get("name"), 180)
        if not name:
            continue
        city = _clean(candidate.get("city"), 80)
        website = _clean(candidate.get("source_url") or candidate.get("contact"), 500)
        phone = None if website and website.startswith("http") else _clean(candidate.get("contact"), 80)
        store = _store_exists(db, name, city, website)
        if store:
            changed = False
            if city and not store.city:
                store.city = city
                changed = True
            if website and not store.website and website.startswith("http"):
                store.website = website
                changed = True
            if phone and not store.phone:
                store.phone = phone
                changed = True
            updated_stores += 1 if changed else 0
        else:
            store = models.Store(name=name, city=city, website=website if website and website.startswith("http") else None, phone=phone, verified=False, seller_type="home_producer" if "domac" in _ascii_key(candidate.get("category")) else "business")
            db.add(store)
            db.flush()
            created_stores += 1
        if create_sources and website and website.startswith("http"):
            source = db.query(models.Source).filter(models.Source.url == website).first()
            if not source:
                db.add(models.Source(name=name, url=website, city=city, source_type="ai_seller_discovery", crawl_frequency="weekly", active=True))
                created_sources += 1
    db.commit()
    return {"created_stores": created_stores, "updated_stores": updated_stores, "created_sources": created_sources}


def discover_sellers(
    db: Session,
    *,
    city: str | None,
    category: str | None,
    query: str | None,
    limit: int = 12,
    include_existing: bool = True,
    include_research_tasks: bool = True,
    web_search: bool = False,
    import_to_stores: bool = False,
    create_sources: bool = True,
) -> dict[str, Any]:
    limit = max(1, min(int(limit or 12), 50))
    criteria = {
        "city": _clean(city, 80),
        "category": _clean(category, 80),
        "query": _clean(query, 240),
        "limit": limit,
    }
    warnings: list[str] = []
    candidates: list[dict[str, Any]] = []
    if include_existing:
        try:
            candidates.extend(_existing_store_candidates(db, city, category, query, limit=limit))
        except Exception as exc:
            db.rollback()
            warnings.append(f"Postojeći prodavci nisu učitani: {exc}")
    if web_search:
        try:
            candidates.extend(_web_search_candidates(city, category, query, limit=limit))
        except Exception as exc:
            warnings.append(f"Web pretraga nije završena: {exc}")
    if include_research_tasks and len(candidates) < limit:
        try:
            candidates.extend(_research_task_candidates(city, category, query, limit=limit - len(candidates)))
        except Exception as exc:
            warnings.append(f"Zadaci za ručnu pretragu nisu napravljeni: {exc}")

    deduped: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        try:
            candidate["score"] = _score_candidate(candidate, city, category, query)
            key = _canonical_lead_key(candidate)
            if key not in deduped or int(candidate.get("score") or 0) > int(deduped[key].get("score") or 0):
                deduped[key] = candidate
        except Exception as exc:
            warnings.append(f"Jedan kandidat je preskočen pri bodovanju: {exc}")
    candidates = sorted(deduped.values(), key=lambda x: int(x.get("score") or 0), reverse=True)[:limit]

    try:
        ai = _openai_rank_candidates(criteria, candidates)
    except Exception as exc:
        warnings.append(f"AI rangiranje nije uspelo: {exc}")
        ai = {"used": False, "summary": "AI rangiranje nije uspelo; prikazani su lokalno rangirani kandidati.", "candidates": candidates}
    final_candidates = ai["candidates"][:limit]
    try:
        lead_result = _upsert_leads(final_candidates)
    except Exception as exc:
        warnings.append(f"Leadovi nisu snimljeni: {exc}")
        lead_result = {"created": 0, "updated": 0, "leads": []}
    if import_to_stores:
        try:
            import_result = _import_candidates_to_stores(db, final_candidates, create_sources=create_sources)
        except Exception as exc:
            warnings.append(f"Import u prodavce nije uspeo: {exc}")
            db.rollback()
            import_result = {"created_stores": 0, "updated_stores": 0, "created_sources": 0}
    else:
        import_result = {"created_stores": 0, "updated_stores": 0, "created_sources": 0}
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
        "web_search_enabled": os.getenv("SELLER_DISCOVERY_WEB_ENABLED", "false").lower() in {"1", "true", "yes", "da", "on"},
        "warnings": warnings,
    }
    try:
        run = append_json_row(RUNS_FILE, run_payload, max_rows=500)
    except Exception as exc:
        warnings.append(f"Istorija pretrage nije snimljena: {exc}")
        run = {**run_payload, "id": None}
    return {
        "ok": not warnings,
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
        "warnings": warnings,
        "candidates": final_candidates,
        "leads": lead_result["leads"],
        "run_id": run["id"],
        "message": "AI pretraga prodavaca je završena. Novi kandidati su leadovi; prodavci ostaju neverifikovani dok ih ručno ne odobrimo." if not warnings else "AI pretraga je završena u sigurnom režimu. Pogledaj upozorenja, ali stranica više ne puca.",
    }
