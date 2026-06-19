from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .. import models
from ..database import get_db

router = APIRouter(prefix="/crawl-jobs", tags=["crawl jobs"])


@router.get("", response_model=list[dict])
def list_jobs(limit: int = 30, db: Session = Depends(get_db)):
    jobs = db.query(models.CrawlJob).order_by(models.CrawlJob.id.desc()).limit(limit).all()
    return [
        {
            "id": job.id,
            "source_id": job.source_id,
            "status": job.status,
            "items_found": job.items_found,
            "error_message": job.error_message,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
        }
        for job in jobs
    ]
