from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from db import get_pool
from permissions import decode_token, IK_EDITORS

router = APIRouter(prefix="/ayarlar", tags=["ayarlar"])

AYAR_ROLLER = IK_EDITORS


def require_ayar_editor(token: dict = Depends(decode_token)) -> dict:
    if token.get("rol") not in AYAR_ROLLER:
        raise HTTPException(status_code=403, detail="Bu işlem için yetkiniz yok.")
    return token


class CalismaGunuGuncelle(BaseModel):
    unvan:     str
    gun_sayisi: int


class KsAtamaEkle(BaseModel):
    ks_personel_id: int
    personel_id: int


class YoneticiUnvanBody(BaseModel):
    unvan: str


@router.get("/calisma-gunleri")
async def get_calisma_gunleri(token: dict = Depends(decode_token)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT unvan, gun_sayisi FROM unvan_calisma_gunu ORDER BY unvan"
        )
        return {r["unvan"]: r["gun_sayisi"] for r in rows}


@router.put("/calisma-gunleri")
async def update_calisma_gunu(
    body: CalismaGunuGuncelle,
    token: dict = Depends(require_ayar_editor),
):
    if body.gun_sayisi not in (5, 6):
        raise HTTPException(status_code=400, detail="gun_sayisi 5 veya 6 olmalıdır.")
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO unvan_calisma_gunu (unvan, gun_sayisi, guncellendi)
            VALUES ($1, $2, NOW())
            ON CONFLICT (unvan) DO UPDATE
              SET gun_sayisi = EXCLUDED.gun_sayisi,
                  guncellendi = NOW()
            """,
            body.unvan,
            body.gun_sayisi,
        )
    return {"ok": True}


@router.get("/yonetici-unvanlar")
async def get_yonetici_unvanlar(token: dict = Depends(decode_token)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT unvan FROM yonetici_unvanlar ORDER BY unvan"
        )
    return [r["unvan"] for r in rows]


@router.post("/yonetici-unvanlar", status_code=201)
async def add_yonetici_unvan(
    body: YoneticiUnvanBody,
    token: dict = Depends(require_ayar_editor),
):
    unvan = body.unvan.strip().upper()
    if not unvan:
        raise HTTPException(status_code=400, detail="Unvan boş olamaz.")
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO yonetici_unvanlar (unvan) VALUES ($1) ON CONFLICT DO NOTHING",
            unvan,
        )
    return {"ok": True}


@router.delete("/yonetici-unvanlar")
async def remove_yonetici_unvan(
    body: YoneticiUnvanBody,
    token: dict = Depends(require_ayar_editor),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM yonetici_unvanlar WHERE unvan = $1", body.unvan
        )
    return {"ok": True}


@router.get("/ks-listesi")
async def get_ks_listesi(token: dict = Depends(require_ayar_editor)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT p.id AS personel_id, p.ad_soyad
            FROM kullanicilar k
            JOIN personel p ON LOWER(REPLACE(p.tc_kimlik,' ','')) = k.email
            WHERE k.rol = 'koordinasyon_sorumlusu' AND k.aktif = TRUE AND p.aktif = TRUE
            ORDER BY p.ad_soyad
        """)
        return [{"personel_id": r["personel_id"], "ad_soyad": r["ad_soyad"]} for r in rows]


@router.get("/ks-atama/{ks_personel_id}")
async def get_ks_atama(ks_personel_id: int, token: dict = Depends(require_ayar_editor)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT a.id, p.id AS personel_id, p.ad_soyad, p.bolum, p.unvan
            FROM ks_personel_atama a
            JOIN personel p ON p.id = a.personel_id
            WHERE a.ks_personel_id = $1
            ORDER BY p.ad_soyad
        """, ks_personel_id)
        return [dict(r) for r in rows]


@router.post("/ks-atama", status_code=201)
async def add_ks_atama(body: KsAtamaEkle, token: dict = Depends(require_ayar_editor)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        ks = await conn.fetchval(
            "SELECT id FROM personel WHERE id = $1 AND aktif = TRUE", body.ks_personel_id
        )
        if not ks:
            raise HTTPException(status_code=404, detail="KS personel bulunamadı.")
        p = await conn.fetchval(
            "SELECT id FROM personel WHERE id = $1 AND aktif = TRUE", body.personel_id
        )
        if not p:
            raise HTTPException(status_code=404, detail="Personel bulunamadı.")
        try:
            row = await conn.fetchrow("""
                INSERT INTO ks_personel_atama (ks_personel_id, personel_id)
                VALUES ($1, $2)
                ON CONFLICT (ks_personel_id, personel_id) DO NOTHING
                RETURNING id
            """, body.ks_personel_id, body.personel_id)
        except Exception:
            raise HTTPException(status_code=400, detail="Bu personel zaten ekli.")
        return {"id": row["id"] if row else None}


@router.delete("/ks-atama/{aid}")
async def remove_ks_atama(aid: int, token: dict = Depends(require_ayar_editor)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        exists = await conn.fetchval("SELECT id FROM ks_personel_atama WHERE id = $1", aid)
        if not exists:
            raise HTTPException(status_code=404, detail="Kayıt bulunamadı.")
        await conn.execute("DELETE FROM ks_personel_atama WHERE id = $1", aid)
    return {"ok": True}


@router.get("/personel-havuzu")
async def get_personel_havuzu(q: str = "", token: dict = Depends(require_ayar_editor)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        yonetici_rows = await conn.fetch(
            "SELECT unvan FROM yonetici_unvanlar"
        )
        yonetici_unvanlar = [r["unvan"] for r in yonetici_rows]
        rows = await conn.fetch("""
            SELECT p.id, p.ad_soyad, p.bolum, p.unvan
            FROM personel p
            WHERE p.aktif = TRUE
              AND p.unvan != ALL($1::varchar[])
              AND ($2 = '' OR p.ad_soyad ILIKE $3)
            ORDER BY p.ad_soyad
            LIMIT 30
        """, yonetici_unvanlar, q, f"%{q}%")
        return [dict(r) for r in rows]
