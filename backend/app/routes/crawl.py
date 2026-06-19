from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..services.crawler_service import crawl_url, crawl_debug
from ..ai_agent.normalizer import normalize_product

router = APIRouter(prefix="/crawl", tags=["crawl"])


def _find_or_create_store(db: Session, name: str, city: str | None, website: str | None) -> models.Store:
    store = db.query(models.Store).filter(models.Store.name == name).first()
    if store:
        if city and not store.city:
            store.city = city
        if website and not store.website:
            store.website = website
        db.commit()
        db.refresh(store)
        return store

    store = models.Store(name=name, city=city, website=website, verified=False)
    db.add(store)
    db.commit()
    db.refresh(store)
    return store


def _product_exists(db: Session, store_id: int | None, name: str, source_url: str | None, discounted_price: float | None) -> bool:
    query = db.query(models.Product).filter(models.Product.name == name)
    if store_id is not None:
        query = query.filter(models.Product.store_id == store_id)
    if source_url:
        query = query.filter(models.Product.source_url == source_url)
    if discounted_price is not None:
        query = query.filter(models.Product.discounted_price == discounted_price)
    return db.query(query.exists()).scalar()


def _source_is_deep_bakery(source: models.Source | None) -> bool:
    return bool(source and source.source_type in {"bakery_product_deep", "bakery_product_super_deep", "bakery_belgrade_product_catalog"})


def _crawl_source_into_db(
    db: Session,
    *,
    target_url: str,
    source: models.Source | None = None,
    store_name: str | None = None,
    city: str | None = None,
    require_image: bool | None = None,
    bakery_only: bool | None = None,
    deep_products: bool | None = None,
    render_js: bool | None = None,
    max_pages: int | None = None,
    max_items: int | None = None,
) -> dict:
    job = models.CrawlJob(source_id=source.id if source else None, status="running", started_at=datetime.utcnow())
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        is_deep = _source_is_deep_bakery(source)
        require_image_flag = is_deep if require_image is None else require_image
        bakery_only_flag = is_deep if bakery_only is None else bakery_only
        deep_products_flag = is_deep if deep_products is None else deep_products
        render_js_flag = bool(render_js) or bool(deep_products_flag and source and source.source_type == "bakery_product_super_deep")
        crawled_items = crawl_url(
            target_url,
            discover=True,
            max_pages=max_pages or (120 if deep_products_flag else 8),
            max_items=max_items or (1200 if deep_products_flag else 300),
            require_image=require_image_flag,
            bakery_only=bakery_only_flag,
            deep_products=deep_products_flag,
            render_js=render_js_flag,
        )
        created_count = 0
        skipped_duplicates = 0

        resolved_store_name = store_name or (source.name if source else "Nepoznat izvor")
        resolved_city = city or (source.city if source else None)
        store = _find_or_create_store(
            db=db,
            name=resolved_store_name,
            city=resolved_city,
            website=target_url,
        )

        for item in crawled_items:
            normalized = normalize_product({
                "name": item.name,
                "original_price": item.original_price,
                "discounted_price": item.discounted_price,
                "discount_percent": item.discount_percent,
                "source_url": item.source_url,
                "raw_text": item.raw_text,
            })

            # Deep bakery product database rule: no image + price, no insert.
            if (require_image_flag or deep_products_flag) and (not item.image_url or not normalized.discounted_price):
                continue

            if _product_exists(db, store.id, normalized.name, item.source_url, normalized.discounted_price):
                skipped_duplicates += 1
                continue

            product = models.Product(
                store_id=store.id,
                name=normalized.name,
                category=normalized.category,
                original_price=normalized.original_price,
                discounted_price=normalized.discounted_price,
                discount_percent=normalized.discount_percent,
                image_url=item.image_url,
                source_url=item.source_url,
                confidence_score=normalized.confidence_score,
                # Public website/crawler data is only a public discount candidate.
                # It must not become near_expiry until a seller confirms expiry info.
                status="public_discount" if normalized.discounted_price else normalized.status,
            )
            db.add(product)
            created_count += 1

        if source:
            source.last_checked_at = datetime.utcnow()

        job.status = "finished"
        job.items_found = created_count
        job.finished_at = datetime.utcnow()
        db.commit()

        return {
            "job_id": job.id,
            "source_id": source.id if source else None,
            "source_name": source.name if source else None,
            "items_found": created_count,
            "duplicates_skipped": skipped_duplicates,
            "url": target_url,
            "status": "finished",
            "mode": {
                "require_image": require_image_flag,
                "bakery_only": bakery_only_flag,
                "deep_products": deep_products_flag,
                "render_js": render_js_flag,
                "max_pages": max_pages or (120 if deep_products_flag else 8),
                "max_items": max_items or (1200 if deep_products_flag else 300),
            },
        }

    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)
        job.finished_at = datetime.utcnow()
        db.commit()
        return {
            "job_id": job.id,
            "source_id": source.id if source else None,
            "source_name": source.name if source else None,
            "items_found": 0,
            "duplicates_skipped": 0,
            "url": target_url,
            "status": "failed",
            "error": str(exc),
        }


@router.post("/run", response_model=dict)
def run_crawl(
    payload: schemas.CrawlRequest,
    deep_products: bool = Query(default=False),
    require_image: bool = Query(default=False),
    bakery_only: bool = Query(default=False),
    render_js: bool = Query(default=False),
    max_pages: int = Query(default=8, ge=1, le=150),
    max_items: int = Query(default=300, ge=1, le=2000),
    db: Session = Depends(get_db),
):
    source = None
    target_url = payload.url

    if payload.source_id:
        source = db.get(models.Source, payload.source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Izvor nije pronađen")
        target_url = source.url

    if not target_url:
        raise HTTPException(status_code=400, detail="Pošalji source_id ili url")

    result = _crawl_source_into_db(
        db,
        target_url=target_url,
        source=source,
        store_name=payload.store_name,
        city=payload.city,
        require_image=require_image or None,
        bakery_only=bakery_only or None,
        deep_products=deep_products or None,
        render_js=render_js or None,
        max_pages=max_pages,
        max_items=max_items,
    )
    # Return crawler failures as structured JSON so the admin panel can show the exact reason
    # instead of looking like the button does nothing.
    return result


@router.post("/run-active", response_model=dict)
def run_active_sources(
    limit: int = Query(default=10, ge=1, le=50),
    source_type: str | None = Query(default=None),
    deep_products: bool = Query(default=False),
    require_image: bool = Query(default=False),
    bakery_only: bool = Query(default=False),
    render_js: bool = Query(default=False),
    max_pages: int = Query(default=60, ge=1, le=150),
    max_items: int = Query(default=1000, ge=1, le=2000),
    db: Session = Depends(get_db),
):
    query = db.query(models.Source).filter(models.Source.active == True)  # noqa: E712
    if source_type:
        query = query.filter(models.Source.source_type == source_type)
    sources = query.order_by(models.Source.last_checked_at.isnot(None), models.Source.last_checked_at.asc(), models.Source.id.asc()).limit(limit).all()

    results = []
    total_created = 0
    total_duplicates = 0
    failed = 0
    for source in sources:
        source_deep = _source_is_deep_bakery(source) or deep_products
        result = _crawl_source_into_db(
            db,
            target_url=source.url,
            source=source,
            require_image=(require_image or source_deep),
            bakery_only=(bakery_only or source_deep),
            deep_products=source_deep,
            render_js=(render_js or (source.source_type == "bakery_product_super_deep")),
            max_pages=max_pages if source_deep else 8,
            max_items=max_items if source_deep else 300,
        )
        results.append(result)
        total_created += int(result.get("items_found") or 0)
        total_duplicates += int(result.get("duplicates_skipped") or 0)
        if result.get("status") == "failed":
            failed += 1

    return {
        "sources_attempted": len(sources),
        "items_found": total_created,
        "duplicates_skipped": total_duplicates,
        "failed_sources": failed,
        "results": results,
        "note": "Crawler pravi javne akcijske kandidate. Za 'pred istek roka' potrebna je potvrda prodavca.",
    }


@router.get("/debug", response_model=dict)
def debug_crawl_url(
    url: str = Query(..., min_length=8),
    discover: bool = Query(default=True),
    max_pages: int = Query(default=8, ge=1, le=150),
    deep_products: bool = Query(default=False),
    require_image: bool = Query(default=False),
    bakery_only: bool = Query(default=False),
    render_js: bool = Query(default=False),
):
    """Diagnose why a source returns zero items without writing to the database."""
    return crawl_debug(
        url,
        discover=discover,
        max_pages=max_pages,
        deep_products=deep_products,
        require_image=require_image or deep_products,
        bakery_only=bakery_only or deep_products,
        render_js=render_js,
    )
