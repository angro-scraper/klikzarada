from __future__ import annotations

import io
import json
import re
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover - optional dependency fallback
    PdfReader = None

# Supports common Serbian price formats:
# 129 din, 129,99 din, 1.299 RSD, RSD 249.99, 99.- din, 55.00 RSD
PRICE_RE = re.compile(
    r"(?:RSD\s*)?(?P<price>\d{1,3}(?:[\.\s]\d{3})*(?:[,.]\d{1,2})?|\d+)(?:\s*[-–.]?)\s*(?:RSD|din\.?|dinara|rsd|дин\.?|рсд)",
    re.IGNORECASE,
)
DISCOUNT_RE = re.compile(r"(?P<discount>\d{1,2})\s*%", re.IGNORECASE)

BAKERY_HINTS = [
    "pekara", "pekar", "pekarski", "pekarstvo", "hleb", "hleba", "kifle", "kiflice", "peciva", "pecivo",
    "pogača", "pogaca", "pogačica", "pogacica", "kifla", "burek", "pita", "kroasan", "croissant",
    "đevrek", "djevrek", "perec", "proja", "lepinja", "somun", "baget", "ciabatta", "mantija", "žužu", "zuzu",
    "puž", "puz", "lisnato", "lisnata", "rolnica", "viršla", "virsla", "pizza", "pica", "sendvič", "sendvic",
    "slatko pecivo", "slano pecivo", "kolač", "kolac", "torta", "cheesecake", "štrudla", "strudla", "baklava",
    "krempita", "krofna", "krofne", "mafin", "muffin", "tiramisu", "tri leće", "tri lece", "moskva", "vanilice",
    "gibanica", "heljda", "heljdopita", "savijača", "savijaca", "projice", "mantije", "pizza parče", "pizza parce",
]

FOOD_HINTS = [
    "akcija", "sniženje", "snizenje", "popust", "super cena", "specijalna cena",
    *BAKERY_HINTS,
    "jogurt", "mleko", "sir", "pavlaka", "meso", "piletina", "kobasica", "salama", "šunka", "sunka",
    "voće", "voce", "povrće", "povrce", "jabuka", "banana", "paradajz", "krompir",
    "kafa", "čokolada", "cokolada", "keks", "sok", "voda", "obrok", "ručak", "rucak",
    "ulje", "brašno", "brasno", "šećer", "secer", "pirinač", "pirinac", "testenina",
]

NEGATIVE_HINTS = [
    "cookie", "privatnost", "newsletter", "prijavi se", "uslovi korišćenja", "uslovi koriscenja",
    "dostava", "korpa", "login", "registracija", "facebook", "instagram", "linkedin",
    "politika privatnosti", "karijera", "zaposlenje", "kontakt forma", "dodaj u omiljene",
]

DISCOVERY_KEYWORDS = [
    "akcija", "akcije", "katalog", "katalozi", "letak", "ponuda", "ponude", "snizenje", "sniženje",
    "prehrana", "hrana", "market", "online-letak", "aktuelno", "promo",
    "pekara", "pekare", "pekar", "peciva", "proizvodi", "product", "product-category", "shop", "cenovnik",
    "lokacije", "objekti", "kontakt", "hleb", "kifle", "kroasan", "burek", "kolaci", "kolači", "torte",
    "category", "kategorija", "preporuka", "pecivo-kilogramsko", "slane", "slatke",
    "items", "menu", "meni", "jelovnik", "dostava", "stores", "venue", "restaurant", "place", "prodaja", "naruci", "naruči",
]

PRODUCT_CARD_SELECTORS = [
    "li.product", ".product", ".product-item", ".product-card", ".products .item", ".woocommerce-LoopProduct-link",
    ".wc-block-grid__product", ".elementor-post", ".jet-woo-products__item",
    "[data-testid*=product]", "[data-test*=product]", "[class*=Product]", "[class*=product]", "[class*=menu]", "[class*=Menu]",
    "article", "li", "div", "section", "tr",
]


@dataclass
class CrawledItem:
    name: str
    original_price: float | None = None
    discounted_price: float | None = None
    discount_percent: float | None = None
    image_url: str | None = None
    source_url: str | None = None
    raw_text: str | None = None


@dataclass
class CrawlDebug:
    url: str
    status: str
    content_type: str | None = None
    html_length: int = 0
    price_matches: int = 0
    image_matches: int = 0
    blocks_checked: int = 0
    product_blocks: int = 0
    links_discovered: int = 0
    rendered_js: bool = False
    errors: list[str] | None = None
    require_image: bool = False
    bakery_only: bool = False


def parse_price(value: str) -> float | None:
    if not value:
        return None
    cleaned = value.strip().replace("\xa0", " ").replace(" ", "")
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    else:
        if re.search(r"\.\d{1,2}$", cleaned):
            pass
        else:
            cleaned = cleaned.replace(".", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def extract_prices(text: str) -> list[float]:
    prices: list[float] = []
    for match in PRICE_RE.finditer(text or ""):
        price = parse_price(match.group("price"))
        if price is not None and 1 <= price <= 200000:
            prices.append(price)
    return prices


def extract_discount(text: str) -> float | None:
    match = DISCOUNT_RE.search(text or "")
    if not match:
        return None
    try:
        value = float(match.group("discount"))
        return value if 0 < value < 95 else None
    except ValueError:
        return None


def _has_bakery_hint(text: str) -> bool:
    lowered = (text or "").lower()
    return any(word in lowered for word in BAKERY_HINTS)


def looks_like_product_block(text: str, *, bakery_only: bool = False) -> bool:
    lowered = (text or "").lower()
    if len(text) < 6 or len(text) > 2200:
        return False
    if any(hint in lowered for hint in NEGATIVE_HINTS):
        # Keep WooCommerce cards containing korpa only when they also clearly look like product + price.
        if not ("poruči" in lowered or "poruci" in lowered or "rsd" in lowered or "din" in lowered):
            return False
    has_price = bool(PRICE_RE.search(text))
    if not has_price:
        return False
    if bakery_only:
        return _has_bakery_hint(text)
    has_food_hint = any(word in lowered for word in FOOD_HINTS)
    return has_food_hint or len(text) < 300


def choose_name(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    parts = PRICE_RE.split(text, maxsplit=1)
    candidate = parts[0] if parts else text
    candidate = re.sub(
        r"(?i)\b(akcija|sniženje|snizenje|popust|super cena|specijalna cena|novo|redovna cena|stara cena|nova cena|poruči veće količine|poruci vece kolicine|detaljnije|opis)\b",
        " ",
        candidate,
    )
    candidate = re.sub(r"\s+", " ", candidate).strip(" -–|,:;•")
    if 4 <= len(candidate) <= 140:
        return candidate[:255]

    chunks = re.split(r"[|•\n]", text)
    for chunk in chunks:
        chunk = re.sub(r"\s+", " ", chunk).strip(" -–|,:;")
        if 4 <= len(chunk) <= 140 and not PRICE_RE.search(chunk):
            return chunk[:255]
    return text[:140].strip(" -–|,:;")


def _is_safe_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _normalize_url(url: str) -> str:
    parsed = urlparse(url)
    return parsed._replace(fragment="").geturl()


def _same_domain_or_subdomain(base_url: str, candidate_url: str) -> bool:
    base = urlparse(base_url).netloc.lower().removeprefix("www.")
    cand = urlparse(candidate_url).netloc.lower().removeprefix("www.")
    return cand == base or cand.endswith("." + base)


def _best_src_from_srcset(srcset: str | None) -> str | None:
    if not srcset:
        return None
    parts = [p.strip().split(" ")[0] for p in srcset.split(",") if p.strip()]
    return parts[-1] if parts else None


def _extract_img_src(img_tag) -> str | None:
    if not img_tag:
        return None
    for attr in ["data-large_image", "data-src", "data-original", "data-lazy-src", "src"]:
        value = img_tag.get(attr)
        if value:
            return value
    return _best_src_from_srcset(img_tag.get("data-srcset") or img_tag.get("srcset"))


def _is_valid_product_image(url: str | None) -> bool:
    if not url:
        return False
    lowered = url.lower()
    if lowered.startswith("data:"):
        return False
    bad_words = ["logo", "placeholder", "avatar", "icon", "facebook", "instagram", "spinner", "loader", "blank", "transparent", "svg"]
    if any(word in lowered for word in bad_words):
        return False
    return lowered.startswith("http://") or lowered.startswith("https://")


def _page_fallback_image(soup: BeautifulSoup, url: str) -> str | None:
    for selector in [
        'meta[property="og:image"]', 'meta[name="twitter:image"]', 'link[rel="image_src"]'
    ]:
        tag = soup.select_one(selector)
        value = tag.get("content") if tag and tag.has_attr("content") else tag.get("href") if tag else None
        if value:
            abs_url = urljoin(url, value)
            if _is_valid_product_image(abs_url):
                return abs_url
    # WooCommerce single product main image
    img = soup.select_one(".woocommerce-product-gallery img, .wp-post-image, img.wp-post-image")
    if img:
        src = _extract_img_src(img)
        if src:
            abs_url = urljoin(url, src)
            if _is_valid_product_image(abs_url):
                return abs_url
    return None


def _price_from_json_ld(offer) -> tuple[float | None, float | None]:
    if isinstance(offer, list) and offer:
        offer = offer[0]
    if not isinstance(offer, dict):
        return None, None
    price = offer.get("price") or offer.get("lowPrice")
    high = offer.get("highPrice")
    discounted = parse_price(str(price)) if price is not None else None
    original = parse_price(str(high)) if high is not None else None
    return original, discounted


def _walk_json_ld(obj):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from _walk_json_ld(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk_json_ld(item)


def _extract_items_from_json_ld(soup: BeautifulSoup, url: str, *, require_image: bool = False, bakery_only: bool = False) -> list[CrawledItem]:
    items: list[CrawledItem] = []
    for script in soup.find_all("script", attrs={"type": re.compile("ld\\+json", re.I)}):
        raw = script.string or script.get_text(" ", strip=True)
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue
        for node in _walk_json_ld(data):
            node_type = node.get("@type") or node.get("type")
            types = node_type if isinstance(node_type, list) else [node_type]
            types = [str(t).lower() for t in types if t]
            if "product" not in types:
                continue
            name = str(node.get("name") or "").strip()
            image = node.get("image")
            if isinstance(image, list):
                image = image[0] if image else None
            if isinstance(image, dict):
                image = image.get("url")
            image_url = urljoin(url, str(image)) if image else _page_fallback_image(soup, url)
            if require_image and not _is_valid_product_image(image_url):
                continue
            original, discounted = _price_from_json_ld(node.get("offers"))
            raw_text = " ".join(str(v) for v in [name, discounted, original, node.get("description")] if v)
            if not discounted and not original:
                continue
            if bakery_only and not _has_bakery_hint(raw_text):
                # Some product names are generic on bakery category pages, but single-product JSON-LD can be exact.
                # If source URL itself is a bakery product page, allow product with name and price.
                if not any(k in url.lower() for k in ["pekara", "product", "pecivo", "hleb", "kiflice"]):
                    continue
            items.append(CrawledItem(
                name=name or choose_name(raw_text),
                original_price=original,
                discounted_price=discounted or original,
                discount_percent=extract_discount(raw_text),
                image_url=image_url if _is_valid_product_image(image_url) else None,
                source_url=url,
                raw_text=raw_text[:1600],
            ))
    return items



def _deep_get_first(obj, keys: set[str]):
    """Return first value matching any key inside a nested dict/list."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if str(key).lower() in keys and value not in (None, ""):
                return value
        for value in obj.values():
            found = _deep_get_first(value, keys)
            if found not in (None, ""):
                return found
    elif isinstance(obj, list):
        for item in obj[:20]:
            found = _deep_get_first(item, keys)
            if found not in (None, ""):
                return found
    return None


def _value_to_price(value) -> float | None:
    """Parse common JSON/app-state price forms."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        # Some APIs store money in cents/para. Prefer realistic RSD prices.
        v = float(value)
        if 1 <= v <= 50000:
            return v
        if 100 <= v <= 5000000:
            return round(v / 100, 2)
        return None
    if isinstance(value, str):
        direct = parse_price(value)
        if direct is not None:
            return direct
        prices = extract_prices(value)
        return prices[0] if prices else None
    if isinstance(value, dict):
        for key in ["price", "amount", "value", "lowPrice", "current", "discounted", "unitPrice", "floatValue"]:
            if key in value:
                parsed = _value_to_price(value.get(key))
                if parsed is not None:
                    return parsed
        # Wolt/Glovo-like nested money objects sometimes have amount + currency.
        for val in value.values():
            parsed = _value_to_price(val)
            if parsed is not None:
                return parsed
    return None


def _extract_image_from_any(obj, base_url: str) -> str | None:
    image_keys = {"image", "images", "imageurl", "image_url", "img", "photo", "picture", "thumbnail", "thumbnailurl", "url"}
    raw = _deep_get_first(obj, image_keys)
    candidates: list[str] = []
    if isinstance(raw, str):
        candidates.append(raw)
    elif isinstance(raw, dict):
        for key in ["url", "src", "href", "imageUrl", "image_url"]:
            if isinstance(raw.get(key), str):
                candidates.append(raw[key])
    elif isinstance(raw, list):
        for entry in raw[:5]:
            if isinstance(entry, str):
                candidates.append(entry)
            elif isinstance(entry, dict):
                for key in ["url", "src", "href", "imageUrl", "image_url"]:
                    if isinstance(entry.get(key), str):
                        candidates.append(entry[key])
    for candidate in candidates:
        abs_url = urljoin(base_url, candidate)
        if _is_valid_product_image(abs_url):
            return abs_url
    return None


def _extract_name_from_any(obj) -> str | None:
    name_keys = {"name", "title", "productname", "displayname", "label"}
    raw = _deep_get_first(obj, name_keys)
    if raw is None:
        return None
    if isinstance(raw, dict):
        raw = raw.get("text") or raw.get("value") or raw.get("name")
    if not isinstance(raw, str):
        raw = str(raw)
    name = re.sub(r"\s+", " ", raw).strip(" -–|,:;•")
    if 3 <= len(name) <= 160 and not PRICE_RE.search(name):
        return name[:255]
    return None


def _extract_price_from_any(obj) -> tuple[float | None, float | None]:
    """Return (original, discounted) from generic app-state JSON."""
    if not isinstance(obj, dict):
        return None, None
    price_keys = [
        "discountedprice", "discounted_price", "currentprice", "current_price", "price", "unitprice",
        "amount", "value", "finalprice", "final_price", "sellingprice", "selling_price", "pricevalue"
    ]
    old_keys = ["originalprice", "original_price", "oldprice", "old_price", "regularprice", "regular_price", "previousprice", "listprice"]
    discounted = None
    original = None
    for key, value in obj.items():
        lk = str(key).lower()
        if discounted is None and lk in price_keys:
            discounted = _value_to_price(value)
        if original is None and lk in old_keys:
            original = _value_to_price(value)
    if discounted is None:
        # Search one level deeper first, but avoid gathering unrelated quantities from huge containers.
        for value in list(obj.values())[:30]:
            if isinstance(value, dict):
                _, maybe = _extract_price_from_any(value)
                if maybe is not None:
                    discounted = maybe
                    break
    if original is None:
        for key in old_keys:
            raw = _deep_get_first(obj, {key})
            parsed = _value_to_price(raw)
            if parsed is not None:
                original = parsed
                break
    return original, discounted


def _extract_items_from_any_json_obj(obj, url: str, *, require_image: bool = False, bakery_only: bool = False) -> list[CrawledItem]:
    items: list[CrawledItem] = []
    for node in _walk_json_ld(obj):
        if not isinstance(node, dict):
            continue
        name = _extract_name_from_any(node)
        if not name:
            continue
        image_url = _extract_image_from_any(node, url)
        if require_image and not _is_valid_product_image(image_url):
            continue
        original, discounted = _extract_price_from_any(node)
        if discounted is None and original is None:
            # Try text inside the node as fallback, useful for app state payloads with formattedPrice.
            small_text = " ".join(str(v) for k, v in list(node.items())[:30] if isinstance(v, (str, int, float)))
            prices = extract_prices(small_text)
            if prices:
                discounted = min(prices)
                original = max(prices) if len(prices) > 1 and max(prices) != discounted else None
        if discounted is None and original is None:
            continue
        raw_text = " ".join(str(v) for k, v in list(node.items())[:30] if isinstance(v, (str, int, float)))[:1600]
        if bakery_only and not _has_bakery_hint(f"{name} {raw_text} {url}"):
            continue
        items.append(CrawledItem(
            name=name,
            original_price=original,
            discounted_price=discounted or original,
            discount_percent=extract_discount(raw_text),
            image_url=image_url if _is_valid_product_image(image_url) else None,
            source_url=url,
            raw_text=raw_text,
        ))
    return items


def _extract_json_from_scripts(soup: BeautifulSoup) -> list[object]:
    payloads: list[object] = []
    for script in soup.find_all("script"):
        raw = script.string or script.get_text(" ", strip=True)
        if not raw or len(raw) < 20:
            continue
        raw_stripped = raw.strip()
        script_id = (script.get("id") or "").lower()
        script_type = (script.get("type") or "").lower()
        candidates: list[str] = []
        if script_id in {"__next_data__", "__nuxt_data__"} or "application/json" in script_type or "ld+json" in script_type:
            candidates.append(raw_stripped)
        elif ("rsd" in raw_stripped.lower() or "din" in raw_stripped.lower() or "price" in raw_stripped.lower()) and ("name" in raw_stripped.lower() or "title" in raw_stripped.lower()):
            # Try common JS assignments: window.__NUXT__={...}; window.__INITIAL_STATE__={...}
            m = re.search(r"=\s*(\{.*\}|\[.*\])\s*;?\s*$", raw_stripped, flags=re.S)
            if m and len(m.group(1)) < 5_000_000:
                candidates.append(m.group(1))
        for cand in candidates:
            try:
                payloads.append(json.loads(cand))
            except Exception:
                continue
    return payloads


def _extract_items_from_app_json(soup: BeautifulSoup, url: str, *, require_image: bool = False, bakery_only: bool = False) -> list[CrawledItem]:
    items: list[CrawledItem] = []
    for payload in _extract_json_from_scripts(soup):
        items.extend(_extract_items_from_any_json_obj(payload, url, require_image=require_image, bakery_only=bakery_only))
    return items


def _nearest_valid_image(block, base_url: str) -> str | None:
    if not block:
        return None
    # Current block, then nearby siblings, then parent.
    candidates = []
    try:
        candidates.extend(block.find_all("img") if hasattr(block, "find_all") else [])
    except Exception:
        pass
    for sib_getter in ["find_previous", "find_next"]:
        try:
            sib = getattr(block, sib_getter)("img")
            if sib:
                candidates.append(sib)
        except Exception:
            pass
    try:
        parent = block.parent
        if parent:
            candidates.extend(parent.find_all("img", limit=3))
    except Exception:
        pass
    for img in candidates:
        src = _extract_img_src(img)
        if src:
            abs_url = urljoin(base_url, src)
            if _is_valid_product_image(abs_url):
                return abs_url
    return None


def _extract_items_from_image_neighborhood(soup: BeautifulSoup, url: str, *, require_image: bool = False, bakery_only: bool = False) -> list[CrawledItem]:
    items: list[CrawledItem] = []
    for img in soup.find_all("img"):
        img_src = _extract_img_src(img)
        image_url = urljoin(url, img_src) if img_src else None
        if require_image and not _is_valid_product_image(image_url):
            continue
        alt = " ".join([img.get("alt") or "", img.get("title") or "", img.get("aria-label") or ""]).strip()
        if alt.lower() in {"image", "slika", ""} or len(alt) > 160:
            alt = ""
        for level in range(1, 6):
            block = img
            for _ in range(level):
                block = getattr(block, "parent", None)
                if block is None:
                    break
            if block is None:
                continue
            text = " ".join(block.get_text(" ", strip=True).split())
            if not PRICE_RE.search(text):
                continue
            name_text = f"{alt} {text}" if alt else text
            item = _make_item_from_text(name_text, url, image_url=image_url, require_image=require_image, bakery_only=bakery_only)
            if item:
                if alt and len(alt) >= 3 and not PRICE_RE.search(alt):
                    item.name = alt[:255]
                items.append(item)
                break
    return items


def _extract_items_from_price_heading_pairs(soup: BeautifulSoup, url: str, *, require_image: bool = False, bakery_only: bool = False) -> list[CrawledItem]:
    items: list[CrawledItem] = []
    price_tags = []
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "p", "span", "div", "li"]):
        text = " ".join(tag.get_text(" ", strip=True).split())
        if PRICE_RE.search(text) and len(text) <= 400:
            price_tags.append(tag)
    for tag in price_tags[:500]:
        price_text = " ".join(tag.get_text(" ", strip=True).split())
        name = None
        # Search headings/short text before price in document order and within parent.
        for prev in tag.find_all_previous(["h1", "h2", "h3", "h4", "strong", "b", "p", "span"], limit=8):
            t = " ".join(prev.get_text(" ", strip=True).split())
            if 3 <= len(t) <= 140 and not PRICE_RE.search(t) and not any(bad in t.lower() for bad in NEGATIVE_HINTS):
                name = t
                break
        if not name:
            continue
        block = tag.parent or tag
        image_url = _nearest_valid_image(block, url)
        item = _make_item_from_text(f"{name} {price_text}", url, image_url=image_url, require_image=require_image, bakery_only=bakery_only)
        if item:
            item.name = name[:255]
            items.append(item)
    return items

def _make_item_from_text(
    text: str,
    source_url: str,
    image_url: str | None = None,
    *,
    require_image: bool = False,
    bakery_only: bool = False,
) -> CrawledItem | None:
    text = " ".join((text or "").split())
    if not looks_like_product_block(text, bakery_only=bakery_only):
        return None
    if require_image and not _is_valid_product_image(image_url):
        return None
    prices = extract_prices(text)
    if not prices:
        return None
    discounted = min(prices)
    original = max(prices) if len(prices) >= 2 and max(prices) != discounted else None
    discount_percent = extract_discount(text)
    name = choose_name(text)
    if not name or len(name) < 3:
        return None
    return CrawledItem(
        name=name,
        original_price=original,
        discounted_price=discounted,
        discount_percent=discount_percent,
        image_url=image_url if _is_valid_product_image(image_url) else None,
        source_url=source_url,
        raw_text=text[:1600],
    )


def _candidate_blocks(soup: BeautifulSoup):
    seen = set()
    for selector in PRODUCT_CARD_SELECTORS:
        for block in soup.select(selector):
            key = id(block)
            if key in seen:
                continue
            seen.add(key)
            yield block


def _extract_items_from_html(
    html: str,
    url: str,
    debug: CrawlDebug | None = None,
    *,
    require_image: bool = False,
    bakery_only: bool = False,
) -> list[CrawledItem]:
    if debug is not None:
        debug.html_length = len(html or "")
        debug.price_matches = len(PRICE_RE.findall(html or ""))
    soup = BeautifulSoup(html, "lxml")
    if debug is not None:
        debug.image_matches = len([img for img in soup.find_all("img") if _is_valid_product_image(urljoin(url, _extract_img_src(img) or ""))])
    for tag in soup(["script", "style", "noscript", "svg"]):
        # JSON-LD is handled before removal by reparsing below, so keep script out of this decompose loop.
        if tag.name == "script":
            continue
        tag.decompose()

    # JSON-LD needs scripts, so parse it on the original soup before decomposing scripts.
    soup_for_json = BeautifulSoup(html, "lxml")
    candidates: list[CrawledItem] = _extract_items_from_json_ld(
        soup_for_json, url, require_image=require_image, bakery_only=bakery_only
    )
    candidates.extend(_extract_items_from_app_json(
        soup_for_json, url, require_image=require_image, bakery_only=bakery_only
    ))
    candidates.extend(_extract_items_from_image_neighborhood(
        soup, url, require_image=require_image, bakery_only=bakery_only
    ))
    candidates.extend(_extract_items_from_price_heading_pairs(
        soup, url, require_image=require_image, bakery_only=bakery_only
    ))
    seen_keys: set[str] = set()
    for item in candidates:
        seen_keys.add(f"{item.name.lower()}|{item.discounted_price}|{item.original_price}|{item.image_url}|{url}")

    page_image = _page_fallback_image(soup, url)
    blocks = list(_candidate_blocks(soup))
    if debug is not None:
        debug.blocks_checked += len(blocks)

    for block in blocks:
        text = " ".join(block.get_text(" ", strip=True).split())
        img_tag = block.find("img")
        image_url = None
        if img_tag:
            img_src = _extract_img_src(img_tag)
            if img_src:
                image_url = urljoin(url, img_src)
        if not image_url and len(blocks) == 1:
            image_url = page_image

        item = _make_item_from_text(
            text,
            source_url=url,
            image_url=image_url,
            require_image=require_image,
            bakery_only=bakery_only,
        )
        if not item:
            continue

        key = f"{item.name.lower()}|{item.discounted_price}|{item.original_price}|{item.image_url}|{url}"
        if key in seen_keys:
            continue
        seen_keys.add(key)
        candidates.append(item)
        if debug is not None:
            debug.product_blocks += 1

    return candidates


def _link_priority(link: str) -> int:
    lowered = link.lower()
    score = 0
    priority_terms = [
        "product-category", "product/", "proizvodi", "cenovnik", "pecivo", "hleb", "kiflice", "kroasan",
        "burek", "kolaci", "kolači", "preporuka", "shop", "page/2", "page/3", "page/4"
    ]
    for i, term in enumerate(priority_terms):
        if term in lowered:
            score += max(1, 30 - i)
    if any(bad in lowered for bad in ["kontakt", "lokacije", "o-nama", "zaposlenje", "privacy", "facebook", "instagram"]):
        score -= 20
    return score



def _extract_urls_from_sitemap_xml(xml_text: str) -> list[str]:
    # Simple namespace-tolerant extraction.
    return [m.group(1).strip() for m in re.finditer(r"<loc>\s*([^<]+?)\s*</loc>", xml_text, flags=re.I)]


def _sitemap_seed_links(base_url: str, timeout: int = 12, max_links: int = 80, *, deep_products: bool = False) -> list[str]:
    """Discover product/category pages from robots.txt and sitemap XML."""
    parsed = urlparse(base_url)
    root = f"{parsed.scheme}://{parsed.netloc}/"
    sitemap_urls = {urljoin(root, "sitemap.xml"), urljoin(root, "sitemap_index.xml"), urljoin(root, "wp-sitemap.xml")}
    try:
        robots = _fetch(urljoin(root, "robots.txt"), timeout)
        for line in robots.text.splitlines():
            if line.lower().startswith("sitemap:"):
                sitemap_urls.add(line.split(":", 1)[1].strip())
    except Exception:
        pass
    discovered: list[str] = []
    seen_sitemaps: set[str] = set()
    queue = list(sitemap_urls)
    while queue and len(seen_sitemaps) < 15 and len(discovered) < max_links:
        sm_url = queue.pop(0)
        if sm_url in seen_sitemaps:
            continue
        seen_sitemaps.add(sm_url)
        try:
            response = _fetch(sm_url, timeout)
        except Exception:
            continue
        locs = _extract_urls_from_sitemap_xml(response.text)
        for loc in locs:
            loc = _normalize_url(loc)
            lower = loc.lower()
            if lower.endswith(".xml") and len(seen_sitemaps) < 15:
                queue.append(loc)
                continue
            if not _is_safe_url(loc) or not _same_domain_or_subdomain(base_url, loc):
                continue
            haystack = lower
            if any(k in haystack for k in DISCOVERY_KEYWORDS):
                discovered.append(loc)
                if len(discovered) >= max_links:
                    break
    discovered = sorted(set(discovered), key=_link_priority, reverse=True)
    return discovered[:max_links]

def _extract_discovery_links(html: str, base_url: str, max_links: int = 12, *, deep_products: bool = False) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    collected: dict[str, int] = {}
    for a in soup.find_all("a", href=True):
        href = a.get("href") or ""
        text = " ".join(a.get_text(" ", strip=True).split()).lower()
        abs_url = _normalize_url(urljoin(base_url, href))
        if not _is_safe_url(abs_url) or not _same_domain_or_subdomain(base_url, abs_url):
            continue
        haystack = f"{abs_url.lower()} {text}"
        if not any(k in haystack for k in DISCOVERY_KEYWORDS):
            continue
        if abs_url == _normalize_url(base_url):
            continue
        score = _link_priority(haystack)
        if deep_products and ("product" in haystack or "proizvod" in haystack or "peciv" in haystack or "hleb" in haystack or "kif" in haystack):
            score += 20
        collected[abs_url] = max(collected.get(abs_url, -999), score)
    links = sorted(collected, key=lambda link: collected[link], reverse=True)
    return links[:max_links]


def _extract_items_from_pdf_bytes(data: bytes, url: str, debug: CrawlDebug | None = None) -> list[CrawledItem]:
    if PdfReader is None:
        raise ValueError("PDF podrška nije instalirana. Pokreni pip install -r requirements.txt")
    reader = PdfReader(io.BytesIO(data))
    text_parts: list[str] = []
    for page in reader.pages[:12]:
        try:
            text_parts.append(page.extract_text() or "")
        except Exception:
            continue
    text = "\n".join(text_parts)
    lines = [" ".join(line.split()) for line in text.splitlines() if line.strip()]
    items: list[CrawledItem] = []
    seen: set[str] = set()
    for i in range(len(lines)):
        chunk = " ".join(lines[i:i + 4])
        item = _make_item_from_text(chunk, source_url=url)
        if not item:
            continue
        key = f"{item.name.lower()}|{item.discounted_price}|{item.original_price}|{url}"
        if key in seen:
            continue
        seen.add(key)
        items.append(item)
        if debug is not None:
            debug.product_blocks += 1
    if debug is not None:
        debug.blocks_checked += len(lines)
    return items[:100]


def _fetch(url: str, timeout: int) -> requests.Response:
    headers = {
        "User-Agent": "SacuvajHranuSerbiaMVP/0.6 (+controlled bakery product crawler; contact: admin@example.com)",
        "Accept-Language": "sr,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
    }
    response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
    response.raise_for_status()
    return response


def _render_html_with_browser(url: str, timeout: int = 35, *, deep_products: bool = False) -> tuple[str, str]:
    """Render JavaScript-heavy pages with Playwright if available.

    Many delivery/marketplace pages do not expose product cards in plain HTML.
    This helper is optional: it requires `pip install -r requirements.txt` and
    `python -m playwright install chromium`. If Chromium is not installed, the
    caller falls back to static requests and reports a clear diagnostic message.
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
    except Exception as exc:  # pragma: no cover - optional dependency
        raise RuntimeError("Playwright nije instaliran. Pokreni: pip install -r requirements.txt, pa: python -m playwright install chromium") from exc

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            locale="sr-RS",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
            ),
            viewport={"width": 1366, "height": 1600},
        )
        page = context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
            # Try common cookie/consent buttons without failing the run.
            for label in ["Prihvatam", "Prihvati", "Accept", "Accept all", "Slažem se", "Slazem se", "U redu"]:
                try:
                    page.get_by_text(label, exact=False).first.click(timeout=1200)
                    break
                except Exception:
                    pass
            try:
                page.wait_for_load_state("networkidle", timeout=min(timeout * 1000, 18000))
            except PlaywrightTimeoutError:
                pass
            scroll_steps = 8 if deep_products else 4
            for _ in range(scroll_steps):
                page.mouse.wheel(0, 1800)
                page.wait_for_timeout(650)
            # Some lazy-loaded menus need one more top/bottom cycle.
            if deep_products:
                page.evaluate("window.scrollTo(0, 0)")
                page.wait_for_timeout(400)
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(900)
            html = page.content()
            final_url = page.url
            return html, final_url
        finally:
            context.close()
            browser.close()


def crawl_url(
    url: str,
    timeout: int = 25,
    *,
    discover: bool = True,
    max_pages: int = 8,
    max_items: int = 300,
    require_image: bool = False,
    bakery_only: bool = False,
    deep_products: bool = False,
    render_js: bool = False,
) -> list[CrawledItem]:
    """Crawl one URL and optionally follow same-domain product/category links.

    Controlled behavior:
    - only follows a limited number of same-domain links;
    - in deep bakery mode, only keeps products that have BOTH a price and a usable image;
    - never marks public products as near-expiry automatically.
    """
    if not _is_safe_url(url):
        raise ValueError("URL mora početi sa http:// ili https://")

    visited: set[str] = set()
    to_visit: list[str] = [_normalize_url(url)]
    if deep_products:
        for sm_link in _sitemap_seed_links(url, timeout=10, max_links=min(max_pages * 2, 120), deep_products=True):
            if sm_link not in to_visit and len(to_visit) < max_pages:
                to_visit.append(sm_link)
        to_visit.sort(key=_link_priority, reverse=True)
    all_items: list[CrawledItem] = []
    global_seen: set[str] = set()
    errors: list[str] = []

    while to_visit and len(visited) < max_pages and len(all_items) < max_items:
        current_url = to_visit.pop(0)
        if current_url in visited:
            continue
        visited.add(current_url)

        rendered_html = None
        rendered_url = current_url
        render_error = None
        if render_js and not current_url.lower().endswith(".pdf"):
            try:
                rendered_html, rendered_url = _render_html_with_browser(current_url, timeout=max(timeout, 35), deep_products=deep_products)
            except Exception as exc:
                render_error = str(exc)
                errors.append(f"{current_url}: browser render nije uspeo ({render_error}); probam statički HTML")

        if rendered_html is not None:
            content_type = "text/html; rendered"
            items = _extract_items_from_html(
                rendered_html,
                rendered_url,
                require_image=require_image,
                bakery_only=bakery_only,
            )
            if discover:
                room = max(0, max_pages - len(visited) - len(to_visit))
                link_limit = min(max_pages * 2, max(0, room + 12 if deep_products else room))
                for link in _extract_discovery_links(rendered_html, rendered_url, max_links=link_limit, deep_products=deep_products):
                    if link not in visited and link not in to_visit and len(visited) + len(to_visit) < max_pages:
                        to_visit.append(link)
                if deep_products:
                    to_visit.sort(key=_link_priority, reverse=True)
        else:
            try:
                response = _fetch(current_url, timeout)
            except Exception as exc:
                errors.append(f"{current_url}: {exc}")
                continue

            content_type = response.headers.get("content-type", "").lower()
            is_pdf = "application/pdf" in content_type or current_url.lower().endswith(".pdf")
            if is_pdf:
                # PDF text can give prices, but usually not extractable product images. In require_image mode, skip PDFs.
                items = [] if require_image else _extract_items_from_pdf_bytes(response.content, current_url)
            elif "text/html" in content_type or "application/xhtml" in content_type or not content_type:
                items = _extract_items_from_html(
                    response.text,
                    current_url,
                    require_image=require_image,
                    bakery_only=bakery_only,
                )
                if discover:
                    room = max(0, max_pages - len(visited) - len(to_visit))
                    link_limit = min(max_pages * 2, max(0, room + 8 if deep_products else room))
                    for link in _extract_discovery_links(response.text, current_url, max_links=link_limit, deep_products=deep_products):
                        if link not in visited and link not in to_visit and len(visited) + len(to_visit) < max_pages:
                            to_visit.append(link)
                    if deep_products:
                        to_visit.sort(key=_link_priority, reverse=True)
            else:
                errors.append(f"{current_url}: nepodržan Content-Type {content_type}")
                continue

        for item in items:
            if require_image and not _is_valid_product_image(item.image_url):
                continue
            if bakery_only and not _has_bakery_hint(f"{item.name} {item.raw_text or ''} {current_url}"):
                continue
            key = f"{item.name.lower()}|{item.discounted_price}|{item.original_price}|{item.image_url}|{item.source_url}"
            if key in global_seen:
                continue
            global_seen.add(key)
            all_items.append(item)

    if not all_items:
        reason = "Nema pronađenih proizvoda sa traženim uslovima"
        if require_image:
            reason += " (naziv + cena + validna slika)"
        if render_js:
            reason += "; browser render je bio uključen"
        if errors:
            reason += ". Detalji: " + " | ".join(errors[:6])
        raise ValueError(reason)
    return all_items[:max_items]


def crawl_debug(
    url: str,
    timeout: int = 25,
    *,
    discover: bool = True,
    max_pages: int = 8,
    require_image: bool = False,
    bakery_only: bool = False,
    deep_products: bool = False,
    render_js: bool = False,
) -> dict:
    if not _is_safe_url(url):
        return {"url": url, "status": "failed", "error": "URL mora početi sa http:// ili https://"}
    debug_rows: list[dict] = []
    visited: set[str] = set()
    to_visit: list[str] = [_normalize_url(url)]
    if deep_products:
        for sm_link in _sitemap_seed_links(url, timeout=10, max_links=min(max_pages * 2, 120), deep_products=True):
            if sm_link not in to_visit and len(to_visit) < max_pages:
                to_visit.append(sm_link)
        to_visit.sort(key=_link_priority, reverse=True)
    total_items = 0
    sample_items: list[dict] = []

    while to_visit and len(visited) < max_pages:
        current_url = to_visit.pop(0)
        if current_url in visited:
            continue
        visited.add(current_url)
        row = CrawlDebug(url=current_url, status="running", errors=[], require_image=require_image, bakery_only=bakery_only)
        try:
            rendered_html = None
            rendered_url = current_url
            if render_js and not current_url.lower().endswith(".pdf"):
                try:
                    rendered_html, rendered_url = _render_html_with_browser(current_url, timeout=max(timeout, 35), deep_products=deep_products)
                    row.rendered_js = True
                    row.content_type = "text/html; rendered"
                except Exception as exc:
                    row.errors = [f"Browser render nije uspeo: {exc}. Probam statički HTML."]

            if rendered_html is not None:
                items = _extract_items_from_html(
                    rendered_html,
                    rendered_url,
                    row,
                    require_image=require_image,
                    bakery_only=bakery_only,
                )
                if discover:
                    links = _extract_discovery_links(rendered_html, rendered_url, max_links=max_pages * 2, deep_products=deep_products)
                    row.links_discovered = len(links)
                    for link in links:
                        if link not in visited and link not in to_visit and len(visited) + len(to_visit) < max_pages:
                            to_visit.append(link)
                    if deep_products:
                        to_visit.sort(key=_link_priority, reverse=True)
            else:
                response = _fetch(current_url, timeout)
                row.content_type = response.headers.get("content-type", "")
                is_pdf = "application/pdf" in (row.content_type or "").lower() or current_url.lower().endswith(".pdf")
                if is_pdf:
                    items = [] if require_image else _extract_items_from_pdf_bytes(response.content, current_url, row)
                elif "text/html" in (row.content_type or "").lower() or "application/xhtml" in (row.content_type or "").lower() or not row.content_type:
                    items = _extract_items_from_html(
                        response.text,
                        current_url,
                        row,
                        require_image=require_image,
                        bakery_only=bakery_only,
                    )
                    if discover:
                        links = _extract_discovery_links(response.text, current_url, max_links=max_pages * 2, deep_products=deep_products)
                        row.links_discovered = len(links)
                        for link in links:
                            if link not in visited and link not in to_visit and len(visited) + len(to_visit) < max_pages:
                                to_visit.append(link)
                        if deep_products:
                            to_visit.sort(key=_link_priority, reverse=True)
                else:
                    items = []
                    row.status = "unsupported"
                    row.errors = [f"Nepodržan Content-Type: {row.content_type}"]
            total_items += len(items)
            for item in items[:5]:
                if len(sample_items) < 20:
                    sample_items.append(item.__dict__)
            if row.status == "running":
                row.status = "ok"
        except Exception as exc:
            row.status = "failed"
            row.errors = [str(exc)]
        debug_rows.append(row.__dict__)

    return {
        "start_url": url,
        "pages_checked": len(visited),
        "items_found_estimate": total_items,
        "sample_items": sample_items,
        "pages": debug_rows,
        "mode": {
            "require_image": require_image,
            "bakery_only": bakery_only,
            "deep_products": deep_products,
            "render_js": render_js,
            "max_pages": max_pages,
        },
        "note": "Uslov je strog: naziv + cena + validna slika. Ako je 0, pogledaj pages[].price_matches i image_matches. Ako plain HTML ima 0 cena/slika, uključi Browser/JS režim. Ako i browser režim ima 0, izvor verovatno traži API/geolokaciju/login ili blokira crawler.",
    }
