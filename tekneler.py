import os
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, JWTError

from db import get_pool

router = APIRouter(prefix="/tekneler", tags=["tekneler"])

JWT_SECRET    = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
security      = HTTPBearer()


def decode_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        return jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Geçersiz token.")


class TekneCreate(BaseModel):
    ad: str
    tip: Optional[str] = None
    uzunluk_m: Optional[float] = None
    genislik_m: Optional[float] = None
    sicil_no: Optional[str] = None
    bayrak_ulke: Optional[str] = "TR"


class TekneUpdate(BaseModel):
    ad: Optional[str] = None
    tip: Optional[str] = None
    uzunluk_m: Optional[float] = None
    genislik_m: Optional[float] = None
    sicil_no: Optional[str] = None
    bayrak_ulke: Optional[str] = None
    aktif: Optional[bool] = None


@router.get("")
async def list_tekneler(
    q: Optional[str] = Query(None),
    tip: Optional[str] = Query(None),
    aktif: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    token: dict = Depends(decode_token),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        conditions = []
        params = []

        if q:
            params.append(f"%{q}%")
            conditions.append(f"(ad ILIKE ${len(params)} OR sicil_no ILIKE ${len(params)})")

        if tip:
            params.append(tip)
            conditions.append(f"tip = ${len(params)}")

        if aktif is not None:
            params.append(aktif)
            conditions.append(f"aktif = ${len(params)}")
        else:
            conditions.append("aktif = TRUE")

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        total = await conn.fetchval(f"SELECT COUNT(*) FROM tekneler {where}", *params)

        offset = (page - 1) * per_page
        params_paginated = params + [per_page, offset]
        rows = await conn.fetch(
            f"""SELECT id, ad, tip, uzunluk_m, genislik_m, sicil_no, bayrak_ulke, aktif
                FROM tekneler {where}
                ORDER BY ad
                LIMIT ${len(params_paginated) - 1} OFFSET ${len(params_paginated)}""",
            *params_paginated,
        )

        tekneler = []
        for r in rows:
            tekneler.append({
                "id": r["id"],
                "ad": r["ad"],
                "tip": r["tip"],
                "uzunluk_m": float(r["uzunluk_m"]) if r["uzunluk_m"] else None,
                "genislik_m": float(r["genislik_m"]) if r["genislik_m"] else None,
                "sicil_no": r["sicil_no"],
                "bayrak_ulke": r["bayrak_ulke"],
                "aktif": r["aktif"],
            })

        return {
            "tekneler": tekneler,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
        }


@router.get("/tipler")
async def tekne_tipler(token: dict = Depends(decode_token)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT DISTINCT tip FROM tekneler WHERE tip IS NOT NULL ORDER BY tip"
        )
        return {"tipler": [r["tip"] for r in rows]}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_tekne(body: TekneCreate, token: dict = Depends(decode_token)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow("SELECT id FROM tekneler WHERE ad ILIKE $1", body.ad)
        if existing:
            raise HTTPException(status_code=409, detail="Bu isimde bir tekne zaten kayıtlı.")
        row = await conn.fetchrow(
            """INSERT INTO tekneler (ad, tip, uzunluk_m, genislik_m, sicil_no, bayrak_ulke)
               VALUES ($1,$2,$3,$4,$5,$6) RETURNING id""",
            body.ad, body.tip, body.uzunluk_m, body.genislik_m, body.sicil_no, body.bayrak_ulke,
        )
    return {"id": row["id"], "mesaj": "Tekne eklendi."}


@router.put("/{tekne_id}")
async def update_tekne(tekne_id: int, body: TekneUpdate, token: dict = Depends(decode_token)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow("SELECT id FROM tekneler WHERE id=$1", tekne_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Tekne bulunamadı.")

        fields = []
        params = []
        for field, val in body.model_dump(exclude_none=True).items():
            params.append(val)
            fields.append(f"{field} = ${len(params)}")

        if not fields:
            raise HTTPException(status_code=400, detail="Güncellenecek alan belirtilmedi.")

        params.append(tekne_id)
        await conn.execute(
            f"UPDATE tekneler SET {', '.join(fields)} WHERE id = ${len(params)}",
            *params,
        )
    return {"mesaj": "Tekne güncellendi."}


@router.delete("/{tekne_id}")
async def delete_tekne(tekne_id: int, token: dict = Depends(decode_token)):
    if token.get("rol") != "admin":
        raise HTTPException(status_code=403, detail="Yetkiniz yok.")
    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow("SELECT id FROM tekneler WHERE id=$1", tekne_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Tekne bulunamadı.")
        await conn.execute("UPDATE tekneler SET aktif=FALSE WHERE id=$1", tekne_id)
    return {"mesaj": "Tekne pasife alındı."}
