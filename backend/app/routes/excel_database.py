from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..services.excel_database import EXCEL_PATH, DATA_DIR, excel_status, export_database_to_excel, import_excel_to_database

router = APIRouter(prefix="/excel-database", tags=["excel database"])


@router.get("/status", response_model=dict)
def status(db: Session = Depends(get_db)):
    return excel_status(db)


@router.post("/save", response_model=dict)
def save_excel_database(db: Session = Depends(get_db)):
    path = export_database_to_excel(db)
    return {"saved": True, **excel_status(db), "message": f"Excel baza sačuvana: {path}"}


@router.get("/download")
def download_excel_database(db: Session = Depends(get_db)):
    if not EXCEL_PATH.exists():
        export_database_to_excel(db)
    return FileResponse(
        EXCEL_PATH,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=EXCEL_PATH.name,
    )


@router.post("/import", response_model=dict)
def import_saved_excel_database(db: Session = Depends(get_db)):
    try:
        result = import_excel_to_database(db)
        export_database_to_excel(db)
        return {"imported": True, **result, "status": excel_status(db)}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Excel import greška: {exc}") from exc


@router.post("/upload-import", response_model=dict)
async def upload_and_import_excel_database(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Pošalji .xlsx fajl")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = DATA_DIR / "uploaded_import.xlsx"
    with temp_path.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    try:
        result = import_excel_to_database(db, temp_path)
        export_database_to_excel(db)
        return {"imported": True, **result, "status": excel_status(db)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Excel import greška: {exc}") from exc
