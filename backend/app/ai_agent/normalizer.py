import re
from dataclasses import dataclass

CATEGORY_KEYWORDS = {
    "pekara": ["hleb", "hleba", "kifla", "kifle", "kiflice", "pecivo", "peciva", "burek", "pita", "pogača", "pogaca", "somun", "baget", "kroasan", "sendvič", "sendvic", "projara", "gibanica", "štapić", "stapic", "rolnica"],
    "mlecni_proizvodi": ["mleko", "jogurt", "sir", "kajmak", "pavlaka", "kefir", "puter"],
    "meso_i_suhomesnato": ["piletina", "svinjetina", "junetina", "kobasica", "šunka", "sunka", "salama", "kulen"],
    "voce_i_povrce": ["jabuka", "banana", "paradajz", "krastavac", "paprika", "krompir", "luk", "salata"],
    "gotova_jela": ["porcija", "ručak", "rucak", "obrok", "pasta", "pizza", "pica", "supa", "salata"],
    "slatkisi": ["čokolada", "cokolada", "keks", "torta", "kolač", "kolac", "bombone"],
    "pice": ["sok", "voda", "pivo", "napitak", "cola", "kafa", "čaj", "caj"],
}

EXPIRY_KEYWORDS = [
    "pred istek", "kratak rok", "kraći rok", "kraci rok", "rok do",
    "upotrebiti do", "najbolje upotrebiti do", "best before", "use by"
]


@dataclass
class NormalizedProduct:
    name: str
    category: str | None
    original_price: float | None
    discounted_price: float | None
    discount_percent: float | None
    confidence_score: float
    status: str


def clean_name(raw_name: str) -> str:
    name = re.sub(r"\s+", " ", raw_name or "").strip()
    name = re.sub(r"(?i)\b(akcija|snizenje|sniženje|popust|super cena)\b", "", name)
    return re.sub(r"\s+", " ", name).strip(" -–|,")


def guess_category(name: str) -> str | None:
    lowered = name.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return category
    return None


def calculate_discount(original_price: float | None, discounted_price: float | None) -> float | None:
    if not original_price or not discounted_price or original_price <= 0 or discounted_price >= original_price:
        return None
    return round(((original_price - discounted_price) / original_price) * 100, 2)


def infer_status(text: str) -> str:
    lowered = text.lower()
    if any(keyword in lowered for keyword in EXPIRY_KEYWORDS):
        return "needs_review"
    if any(word in lowered for word in ["akcija", "sniženje", "snizenje", "popust"]):
        return "public_discount"
    return "candidate"


def normalize_product(raw: dict) -> NormalizedProduct:
    raw_name = raw.get("name") or raw.get("title") or "Nepoznat proizvod"
    text_blob = " ".join(str(v) for v in raw.values() if v is not None)
    name = clean_name(raw_name)
    category = guess_category(name)
    original_price = raw.get("original_price")
    discounted_price = raw.get("discounted_price")
    discount_percent = raw.get("discount_percent") or calculate_discount(original_price, discounted_price)

    confidence = 0.45
    if name and name != "Nepoznat proizvod":
        confidence += 0.15
    if discounted_price:
        confidence += 0.15
    if original_price:
        confidence += 0.10
    if category:
        confidence += 0.10
    if raw.get("source_url"):
        confidence += 0.05

    return NormalizedProduct(
        name=name or raw_name,
        category=category,
        original_price=original_price,
        discounted_price=discounted_price,
        discount_percent=discount_percent,
        confidence_score=min(round(confidence, 2), 0.95),
        status=infer_status(text_blob),
    )
