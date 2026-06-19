import re
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

router = APIRouter(prefix="/uploads", tags=["uploads"])

UPLOAD_DIR = Path(__file__).resolve().parents[1] / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_MIME_PREFIX = "image/"


def _detect_image_type(raw: bytes) -> str | None:
    if raw.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if raw.startswith(b"GIF87a") or raw.startswith(b"GIF89a"):
        return "gif"
    if len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "webp"
    return None


def _safe_extension(filename: str, content_type: str | None, detected: str) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix in ALLOWED_EXTENSIONS:
        return suffix
    if detected == "png":
        return ".png"
    if detected == "webp":
        return ".webp"
    if detected == "gif":
        return ".gif"
    return ".jpg"


@router.post("/image", response_model=dict)
async def upload_image(file: UploadFile = File(...)):
    content_type = file.content_type or ""
    if not content_type.startswith(ALLOWED_MIME_PREFIX):
        raise HTTPException(status_code=400, detail="Dozvoljene su samo slike")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Prazan fajl")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Slika je prevelika. Maksimalno 5MB")

    detected = _detect_image_type(raw)
    if detected not in {"jpeg", "png", "webp", "gif"}:
        raise HTTPException(status_code=400, detail="Fajl ne izgleda kao podržana slika")

    ext = _safe_extension(file.filename or "offer.jpg", content_type, detected)
    original_stem = Path(file.filename or "slika").stem
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", original_stem).strip("-")[:40] or "slika"
    filename = f"{uuid.uuid4().hex[:12]}-{slug}{ext}"
    target = UPLOAD_DIR / filename
    target.write_bytes(raw)

    return {
        "filename": filename,
        "image_url": f"/uploads/{filename}",
        "content_type": content_type,
        "size_bytes": len(raw),
    }
