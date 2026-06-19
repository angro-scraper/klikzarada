import random
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/stores", tags=["stores"])


BELGRADE_BAKERY_STORE_SEEDS = [
    # Major chains / official or directory-confirmed locations. verified=False until owner confirms.
    {"name": "Skroz dobra pekara - Kolarčeva", "city": "Beograd", "address": "Kolarčeva 6-8, Stari grad", "website": "https://skrozdobrapekara.rs/objekti/", "phone": "064 8481 079"},
    {"name": "Skroz dobra pekara - Vojvode Micka Krstića", "city": "Beograd", "address": "Vojvode Micka Krstića 24v, Palilula", "website": "https://skrozdobrapekara.rs/objekti/", "phone": "064 8481 058"},
    {"name": "Skroz dobra pekara - Save Maškovića", "city": "Beograd", "address": "Save Maškovića 5, Voždovac", "website": "https://skrozdobrapekara.rs/objekti/", "phone": "064 8481 079"},
    {"name": "Skroz dobra pekara - Bulevar kralja Aleksandra 74", "city": "Beograd", "address": "Bulevar kralja Aleksandra 74, Zvezdara", "website": "https://skrozdobrapekara.rs/objekti/", "phone": "064 8481 059"},
    {"name": "Skroz dobra pekara - Marijane Gregoran", "city": "Beograd", "address": "Marijane Gregoran 83A", "website": "https://skrozdobrapekara.rs/wp-content/uploads/2023/07/Kontakt-telefoni-objekata.pdf", "phone": "0648481056"},
    {"name": "Skroz dobra pekara - Pane Đukić", "city": "Beograd", "address": "Pane Đukić 5A", "website": "https://skrozdobrapekara.rs/wp-content/uploads/2023/07/Kontakt-telefoni-objekata.pdf", "phone": "0648481057"},
    {"name": "Skroz dobra pekara - Solunska", "city": "Beograd", "address": "Solunska 9", "website": "https://skrozdobrapekara.rs/wp-content/uploads/2023/07/Kontakt-telefoni-objekata.pdf", "phone": "0648481067"},
    {"name": "Skroz dobra pekara - Bulevar despota Stefana 43", "city": "Beograd", "address": "Bulevar despota Stefana 43", "website": "https://skrozdobrapekara.rs/wp-content/uploads/2023/07/Kontakt-telefoni-objekata.pdf", "phone": "0648481086"},
    {"name": "Skroz dobra pekara - Bulevar despota Stefana 3", "city": "Beograd", "address": "Bulevar despota Stefana 3", "website": "https://skrozdobrapekara.rs/wp-content/uploads/2023/07/Kontakt-telefoni-objekata.pdf", "phone": "0648031015"},
    {"name": "Skroz dobra pekara - Zeleni Venac", "city": "Beograd", "address": "Zeleni Venac 10", "website": "https://skrozdobrapekara.rs/wp-content/uploads/2023/07/Kontakt-telefoni-objekata.pdf", "phone": "0648481073"},

    {"name": "Hleb & Kifle - Sremska", "city": "Beograd", "address": "Sremska 2, Stari Grad", "website": "https://hlebikifle.rs/lokacije/", "phone": None},
    {"name": "Hleb & Kifle - Vase Čarapića", "city": "Beograd", "address": "Vase Čarapića 9, Stari Grad", "website": "https://hlebikifle.rs/lokacije/", "phone": None},
    {"name": "Hleb & Kifle - Kneza Mihaila", "city": "Beograd", "address": "Kneza Mihaila 34, Stari Grad", "website": "https://hlebikifle.rs/lokacije/", "phone": None},
    {"name": "Hleb & Kifle - Cara Dušana 94", "city": "Beograd", "address": "Cara Dušana 94, Stari Grad", "website": "https://hlebikifle.rs/lokacije/", "phone": None},
    {"name": "Hleb & Kifle - Gospodar Jovanova", "city": "Beograd", "address": "Gospodar Jovanova 31, Stari Grad", "website": "https://hlebikifle.rs/lokacije/", "phone": None},
    {"name": "Hleb & Kifle - Cara Dušana 14", "city": "Beograd", "address": "Cara Dušana 14, Stari Grad", "website": "https://hlebikifle.rs/lokacije/", "phone": None},
    {"name": "Hleb & Kifle - Kralja Milana", "city": "Beograd", "address": "Kralja Milana 23, Vračar", "website": "https://hlebikifle.rs/lokacije/", "phone": None},
    {"name": "Hleb & Kifle - 27. marta", "city": "Beograd", "address": "27. marta 18, Palilula", "website": "https://hlebikifle.rs/lokacije/", "phone": None},
    {"name": "Hleb & Kifle - Sarajevska", "city": "Beograd", "address": "Sarajevska 16, Savski Venac", "website": "https://hlebikifle.rs/lokacije/", "phone": None},

    {"name": "Lulu pekara - Braće Jugovića", "city": "Beograd", "address": "Braće Jugovića 23, Stari Grad", "website": "https://pekaralulu.com/lokacije/", "phone": "011/3373-584"},
    {"name": "Lulu pekara - Džordža Vašingtona", "city": "Beograd", "address": "Džordža Vašingtona 2, Stari Grad", "website": "https://pekaralulu.com/lokacije/", "phone": None},
    {"name": "Lulu pekara - Bulevar kralja Aleksandra", "city": "Beograd", "address": "Bulevar kralja Aleksandra 70, Vračar", "website": "https://pekaralulu.com/lokacije/", "phone": "011/770-9230"},
    {"name": "Lulu pekara - Kneginje Zorke", "city": "Beograd", "address": "Kneginje Zorke 53, Vračar", "website": "https://pekaralulu.com/lokacije/", "phone": "011/243-7090"},
    {"name": "Lulu pekara - Novopazarska", "city": "Beograd", "address": "Novopazarska 36, Vračar", "website": "https://pekaralulu.com/lokacije/", "phone": None},
    {"name": "Lulu pekara - Petra Martinovića", "city": "Beograd", "address": "Petra Martinovića 37, Banovo brdo", "website": "https://pekaralulu.com/kontakt/", "phone": "+391 62 565 837"},
    {"name": "Lulu pekara - Luke Ćelovića Trebinjca", "city": "Beograd", "address": "Luke Ćelovića Trebinjca 25, Beograd na vodi", "website": "https://pekaralulu.com/aktuelno/nova-pekara-u-beogradu-na-vodi/", "phone": None},

    {"name": "Pekara Trpković - Nemanjina", "city": "Beograd", "address": "Nemanjina 32, Savski Venac", "website": "https://pekaratrpkovic.rs/kontakt/", "phone": "011/361-1268"},
    {"name": "Pekara Trpković - Dimitrija Tucovića", "city": "Beograd", "address": "Dimitrija Tucovića 60, Zvezdara", "website": "https://pekaratrpkovic.rs/kontakt/", "phone": "011 2415222"},
    {"name": "Pekara Trpković - Milorada Bondžulića", "city": "Beograd", "address": "Milorada Bondžulića 6, Voždovac", "website": "https://pekaratrpkovic.rs/kontakt/", "phone": "011/2457-821"},

    {"name": "Pekara GAK - Bulevar Zorana Đinđića 197e", "city": "Beograd", "address": "Bulevar Zorana Đinđića 197e, Novi Beograd", "website": "https://pekaragak.rs/lokacije/", "phone": "+381 63 39 46 40"},
    {"name": "Pekara GAK - Ismeta Mujezinovića", "city": "Beograd", "address": "Ismeta Mujezinovića 23d, Bežanijska Kosa", "website": "https://pekaragak.rs/lokacije/", "phone": "+381 63 298 640"},
    {"name": "Pekara GAK - Bulevar Zorana Đinđića 195", "city": "Beograd", "address": "Bulevar Zorana Đinđića 195, Novi Beograd", "website": "https://pekaragak.rs/lokacije/", "phone": "+381 63 563 640"},
    {"name": "Pekara GAK - Bulevar umetnosti", "city": "Beograd", "address": "Bulevar umetnosti 27, Novi Beograd", "website": "https://pekaragak.rs/lokacije/", "phone": "+381636646400"},

    {"name": "Pekara Banjica", "city": "Beograd", "address": "Paunova 1-1a, Voždovac", "website": "https://www.firmesrbije.rs/turizam-i-ugostiteljstvo/pekare-palacinkarnice-i-poslasticarnice/51338/pekara-banjica/", "phone": "069/377 11 00"},
    {"name": "Pekara Sara - Ignjata Joba", "city": "Beograd", "address": "Ignjata Joba 6, Voždovac", "website": "https://www.011info.com/pekare-oprema-za-pekare/pekara-sara-", "phone": "0113974319"},
    {"name": "Pekara Sara - Bulevar oslobođenja", "city": "Beograd", "address": "Bulevar oslobođenja 61, Vračar", "website": "https://www.planplus.rs/pekara-sara/104094", "phone": None},
    {"name": "Pekara Sara - Balkanska", "city": "Beograd", "address": "Balkanska 48", "website": "https://www.halooglasi.com/posao/ponuda-poslova-ugostiteljstvo-i-turizam?search_text=Pekar", "phone": None},
    {"name": "Pekara Sara - Bulevar kralja Aleksandra", "city": "Beograd", "address": "Bulevar kralja Aleksandra 461", "website": "https://www.halooglasi.com/posao/ponuda-poslova-ugostiteljstvo-i-turizam?search_text=Pekar", "phone": None},
    {"name": "Pekara Radulović - Grčića Milenka", "city": "Beograd", "address": "Grčića Milenka 73a, Voždovac", "website": "https://pekaraketringradulovic.com/", "phone": "065/431-2113"},
    {"name": "Bred Pita 011", "city": "Beograd", "address": "Višnjička 49, Karaburma", "website": "https://www.011info.com/pekare-oprema-za-pekare", "phone": None},
    {"name": "Blok 33 pekara", "city": "Beograd", "address": "Bulevar Zorana Đinđića 153a, Novi Beograd", "website": "https://www.011info.com/pekare-oprema-za-pekare", "phone": "011/7131-641"},
    {"name": "Panta pita - domaće pite", "city": "Beograd", "address": "Nehruova 51A, Novi Beograd", "website": "https://www.planplus.rs/novi-beograd/pekare", "phone": "064/953-1000"},
    {"name": "Patisserie Nina", "city": "Beograd", "address": "Španskih boraca 22G, Novi Beograd", "website": "https://www.planplus.rs/novi-beograd/pekare", "phone": "011/3132-481"},
    {"name": "Pekara 30", "city": "Beograd", "address": "Bulevar Mihajla Pupina 141, Novi Beograd", "website": "https://www.planplus.rs/novi-beograd/pekare", "phone": "011/213-5527"},
    {"name": "Pekara Akademac", "city": "Beograd", "address": "Studentska 2, Novi Beograd", "website": "https://www.planplus.rs/novi-beograd/pekare", "phone": "011/260-2141"},
    {"name": "Pekara Platan 2", "city": "Beograd", "address": "Miška Kranjca 10, Rakovica", "website": "https://www.planplus.rs/beograd/pekare/13", "phone": "011/356-4733"},
    {"name": "Pekara Podrinje", "city": "Beograd", "address": "Miloša Zečevića 7, Zvezdara", "website": "https://www.planplus.rs/beograd/pekare/13", "phone": None},
    {"name": "Pekara Salaš DD", "city": "Beograd", "address": "Kokanova 18, Banjica", "website": "https://www.011info.com/pekare-oprema-za-pekare/pekara-salas-dd", "phone": "065/22-22-065"},
]


def _store_seed_key(payload: dict) -> tuple[str, str]:
    return ((payload.get("name") or "").strip().lower(), (payload.get("address") or "").strip().lower())


@router.post("", response_model=schemas.StoreOut)
def create_store(payload: schemas.StoreCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    if not data.get("seller_pin"):
        data["seller_pin"] = str(random.randint(100000, 999999))
    store = models.Store(**data)
    db.add(store)
    db.commit()
    db.refresh(store)
    return store


@router.post("/seed-belgrade-bakeries", response_model=dict)
def seed_belgrade_bakery_stores(db: Session = Depends(get_db)):
    created = 0
    existing = 0
    store_ids: list[int] = []
    for payload in BELGRADE_BAKERY_STORE_SEEDS:
        name_key, address_key = _store_seed_key(payload)
        existing_store = db.query(models.Store).filter(
            models.Store.name.ilike(payload["name"]),
            models.Store.address.ilike(payload["address"]),
        ).first()
        if existing_store:
            existing += 1
            store_ids.append(existing_store.id)
            continue
        data = dict(payload)
        data["verified"] = False
        data["seller_pin"] = str(random.randint(100000, 999999))
        store = models.Store(**data)
        db.add(store)
        db.commit()
        db.refresh(store)
        created += 1
        store_ids.append(store.id)
    return {
        "created": created,
        "existing": existing,
        "total_seed_stores": len(BELGRADE_BAKERY_STORE_SEEDS),
        "store_ids": store_ids,
        "note": "Ovo su inicijalni lead/prodavac zapisi za pekare u Beogradu. verified=False dok ih vlasnik ne potvrdi.",
    }


@router.get("", response_model=list[schemas.StorePublicOut])
def list_stores(city: str | None = None, db: Session = Depends(get_db)):
    query = db.query(models.Store)
    if city:
        query = query.filter(models.Store.city.ilike(f"%{city}%"))
    return query.order_by(models.Store.created_at.desc()).all()


@router.get("/{store_id}", response_model=schemas.StorePublicOut)
def get_store(store_id: int, db: Session = Depends(get_db)):
    store = db.get(models.Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Prodavac nije pronađen")
    return store


@router.patch("/{store_id}/pin", response_model=schemas.StoreOut)
def update_store_pin(store_id: int, seller_pin: str | None = None, db: Session = Depends(get_db)):
    store = db.get(models.Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Prodavac nije pronađen")
    store.seller_pin = seller_pin or str(random.randint(100000, 999999))
    db.commit()
    db.refresh(store)
    return store


@router.patch("/{store_id}/location", response_model=schemas.StorePublicOut)
def update_store_location(store_id: int, payload: schemas.StoreLocationUpdate, db: Session = Depends(get_db)):
    store = db.get(models.Store, store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Prodavac nije pronađen")
    store.latitude = payload.latitude
    store.longitude = payload.longitude
    db.commit()
    db.refresh(store)
    return store
