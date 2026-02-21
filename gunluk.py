import os
from datetime import date, time, datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, JWTError

from db import get_pool

router = APIRouter(prefix="/gunluk", tags=["gunluk"])

JWT_SECRET    = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"

security = HTTPBearer()

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS gunluk_kayitlar (
    id            SERIAL PRIMARY KEY,
    liman_id      INT REFERENCES limanlar(id) ON DELETE CASCADE,
    tekne_id      INT REFERENCES tekneler(id) ON DELETE SET NULL,
    tekne_adi     VARCHAR(255) NOT NULL,
    kullanici_id  INT REFERENCES kullanicilar(id) ON DELETE SET NULL,
    bolge         VARCHAR(100),
    hareket_tipi  VARCHAR(10) NOT NULL CHECK (hareket_tipi IN ('giris', 'cikis')),
    tarih         DATE NOT NULL DEFAULT CURRENT_DATE,
    saat          TIME NOT NULL DEFAULT CURRENT_TIME,
    yolcu_sayisi  INT DEFAULT 0,
    bilgi_notu    TEXT,
    olusturuldu   TIMESTAMPTZ DEFAULT NOW()
);
"""


async def ensure_table():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(CREATE_TABLE_SQL)


def decode_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Geçersiz token.")


class GunlukCreate(BaseModel):
    liman_id:      int
    tekne_id:      Optional[int] = None
    tekne_adi:     str
    bolge:         Optional[str] = None
    hareket_tipi:  str
    tarih:         date
    saat:          time
    yolcu_sayisi:  int = 0
    bilgi_notu:    Optional[str] = None


class GunlukUpdate(BaseModel):
    tekne_adi:     Optional[str] = None
    bolge:         Optional[str] = None
    hareket_tipi:  Optional[str] = None
    tarih:         Optional[date] = None
    saat:          Optional[time] = None
    yolcu_sayisi:  Optional[int] = None
    bilgi_notu:    Optional[str] = None


def row_to_dict(row) -> dict:
    return {
        "id":           row["id"],
        "liman_id":     row["liman_id"],
        "tekne_id":     row["tekne_id"],
        "tekne_adi":    row["tekne_adi"],
        "kullanici_id": row["kullanici_id"],
        "bolge":        row["bolge"],
        "hareket_tipi": row["hareket_tipi"],
        "tarih":        str(row["tarih"]),
        "saat":         str(row["saat"])[:5],
        "yolcu_sayisi": row["yolcu_sayisi"],
        "bilgi_notu":   row["bilgi_notu"],
        "olusturuldu":  row["olusturuldu"].isoformat() if row["olusturuldu"] else None,
    }


@router.on_event("startup")
async def startup():
    await ensure_table()


@router.get("/tekneler/ara")
async def ara_tekneler(
    q:     str  = Query("", min_length=0),
    token: dict = Depends(decode_token),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, ad, uzunluk_m, genislik_m, tip FROM tekneler WHERE LOWER(ad) LIKE LOWER($1) AND aktif = TRUE ORDER BY ad LIMIT 20",
            f"%{q}%"
        )
    return [{"id": r["id"], "ad": r["ad"], "uzunluk_m": r["uzunluk_m"], "genislik_m": r["genislik_m"], "tip": r["tip"]} for r in rows]


@router.get("/limanlar")
async def list_limanlar(token: dict = Depends(decode_token)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, ad FROM limanlar WHERE aktif = TRUE ORDER BY ad"
        )
    return [{"id": r["id"], "ad": r["ad"]} for r in rows]


@router.get("")
async def list_gunluk(
    liman_id: Optional[int]  = Query(None),
    tarih:    Optional[date]  = Query(None),
    page:     int             = Query(1, ge=1),
    per_page: int             = Query(20, ge=1, le=100),
    token:    dict            = Depends(decode_token),
):
    await ensure_table()

    rol     = token.get("rol")
    user_id = int(token.get("sub"))

    conditions = []
    params     = []
    idx        = 1

    if rol != "admin":
        pass

    if liman_id:
        conditions.append(f"liman_id = ${idx}")
        params.append(liman_id)
        idx += 1

    if tarih:
        conditions.append(f"tarih = ${idx}")
        params.append(tarih)
        idx += 1

    where  = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    offset = (page - 1) * per_page

    pool = await get_pool()
    async with pool.acquire() as conn:
        total = await conn.fetchval(
            f"SELECT COUNT(*) FROM gunluk_kayitlar {where}", *params
        )
        rows = await conn.fetch(
            f"""
            SELECT * FROM gunluk_kayitlar
            {where}
            ORDER BY tarih DESC, saat DESC
            LIMIT ${idx} OFFSET ${idx + 1}
            """,
            *params, per_page, offset
        )

    return {
        "toplam":   total,
        "sayfa":    page,
        "per_page": per_page,
        "kayitlar": [row_to_dict(r) for r in rows],
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_gunluk(
    body:  GunlukCreate,
    token: dict = Depends(decode_token),
):
    await ensure_table()

    if body.hareket_tipi not in ("giris", "cikis"):
        raise HTTPException(status_code=422, detail="hareket_tipi 'giris' veya 'cikis' olmalı.")

    user_id = int(token.get("sub"))

    pool = await get_pool()
    async with pool.acquire() as conn:
        tekne_id = body.tekne_id

        if not tekne_id and body.tekne_adi:
            existing = await conn.fetchrow(
                "SELECT id FROM tekneler WHERE LOWER(ad) = LOWER($1)", body.tekne_adi
            )
            if existing:
                tekne_id = existing["id"]
            else:
                new_tekne = await conn.fetchrow(
                    "INSERT INTO tekneler (ad) VALUES ($1) RETURNING id",
                    body.tekne_adi
                )
                tekne_id = new_tekne["id"]

        row = await conn.fetchrow(
            """
            INSERT INTO gunluk_kayitlar
                (liman_id, tekne_id, tekne_adi, kullanici_id, bolge,
                 hareket_tipi, tarih, saat, yolcu_sayisi, bilgi_notu)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
            RETURNING *
            """,
            body.liman_id, tekne_id, body.tekne_adi, user_id, body.bolge,
            body.hareket_tipi, body.tarih, body.saat,
            body.yolcu_sayisi, body.bilgi_notu
        )

    return row_to_dict(row)


@router.put("/{kayit_id}")
async def update_gunluk(
    kayit_id: int,
    body:     GunlukUpdate,
    token:    dict = Depends(decode_token),
):
    await ensure_table()

    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT * FROM gunluk_kayitlar WHERE id = $1", kayit_id
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Kayıt bulunamadı.")

        updated = await conn.fetchrow(
            """
            UPDATE gunluk_kayitlar SET
                tekne_adi    = COALESCE($1, tekne_adi),
                bolge        = COALESCE($2, bolge),
                hareket_tipi = COALESCE($3, hareket_tipi),
                tarih        = COALESCE($4, tarih),
                saat         = COALESCE($5, saat),
                yolcu_sayisi = COALESCE($6, yolcu_sayisi),
                bilgi_notu   = COALESCE($7, bilgi_notu)
            WHERE id = $8
            RETURNING *
            """,
            body.tekne_adi, body.bolge, body.hareket_tipi,
            body.tarih, body.saat, body.yolcu_sayisi,
            body.bilgi_notu, kayit_id
        )

    return row_to_dict(updated)


@router.delete("/{kayit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gunluk(
    kayit_id: int,
    token:    dict = Depends(decode_token),
):
    await ensure_table()

    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM gunluk_kayitlar WHERE id = $1", kayit_id
        )
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Kayıt bulunamadı.")
