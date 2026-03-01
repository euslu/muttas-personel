from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from db import get_pool
from permissions import decode_token, require_admin

router = APIRouter(prefix="/vekaletler", tags=["vekaletler"])


class VekaletCreate(BaseModel):
    veren_kullanici_id: int
    alan_kullanici_id: int
    baslangic: date
    bitis: date
    notlar: Optional[str] = None


class VekaletUpdate(BaseModel):
    aktif: bool


@router.get("")
async def list_vekaletler(token: dict = Depends(require_admin)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT v.id, v.baslangic, v.bitis, v.aktif, v.notlar, v.olusturuldu,
                   veren.id as veren_id, veren.ad as veren_ad, veren.soyad as veren_soyad, veren.rol as veren_rol,
                   alan.id as alan_id, alan.ad as alan_ad, alan.soyad as alan_soyad, alan.rol as alan_rol
            FROM vekaletler v
            JOIN kullanicilar veren ON veren.id = v.veren_kullanici_id
            JOIN kullanicilar alan ON alan.id = v.alan_kullanici_id
            ORDER BY v.id DESC
        """)
        return [dict(r) for r in rows]


@router.post("", status_code=201)
async def create_vekalet(body: VekaletCreate, token: dict = Depends(require_admin)):
    if body.veren_kullanici_id == body.alan_kullanici_id:
        raise HTTPException(status_code=400, detail="Kullanıcı kendisine vekalet veremez.")
    if body.bitis < body.baslangic:
        raise HTTPException(status_code=400, detail="Bitiş tarihi başlangıçtan önce olamaz.")

    pool = await get_pool()
    async with pool.acquire() as conn:
        veren = await conn.fetchrow("SELECT id, rol FROM kullanicilar WHERE id = $1 AND aktif = true", body.veren_kullanici_id)
        if not veren:
            raise HTTPException(status_code=404, detail="Vekalet veren kullanıcı bulunamadı.")
        alan = await conn.fetchrow("SELECT id FROM kullanicilar WHERE id = $1 AND aktif = true", body.alan_kullanici_id)
        if not alan:
            raise HTTPException(status_code=404, detail="Vekalet alan kullanıcı bulunamadı.")

        existing = await conn.fetchval("""
            SELECT id FROM vekaletler
            WHERE veren_kullanici_id = $1 AND aktif = true
              AND baslangic <= $3 AND bitis >= $2
        """, body.veren_kullanici_id, body.baslangic, body.bitis)
        if existing:
            raise HTTPException(status_code=400, detail="Bu kullanıcının aynı tarih aralığında aktif bir vekaleti var.")

        row = await conn.fetchrow("""
            INSERT INTO vekaletler (veren_kullanici_id, alan_kullanici_id, baslangic, bitis, notlar)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id
        """, body.veren_kullanici_id, body.alan_kullanici_id, body.baslangic, body.bitis, body.notlar)
        return {"ok": True, "id": row["id"]}


@router.put("/{vid}")
async def update_vekalet(vid: int, body: VekaletUpdate, token: dict = Depends(require_admin)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        exists = await conn.fetchval("SELECT id FROM vekaletler WHERE id = $1", vid)
        if not exists:
            raise HTTPException(status_code=404, detail="Vekalet bulunamadı.")
        await conn.execute("UPDATE vekaletler SET aktif = $2 WHERE id = $1", vid, body.aktif)
        return {"ok": True}


@router.delete("/{vid}")
async def delete_vekalet(vid: int, token: dict = Depends(require_admin)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        exists = await conn.fetchval("SELECT id FROM vekaletler WHERE id = $1", vid)
        if not exists:
            raise HTTPException(status_code=404, detail="Vekalet bulunamadı.")
        await conn.execute("DELETE FROM vekaletler WHERE id = $1", vid)
        return {"ok": True}


async def get_vekalet_rolleri(kullanici_id: int) -> set:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT DISTINCT k.rol FROM vekaletler v
            JOIN kullanicilar k ON k.id = v.veren_kullanici_id
            WHERE v.alan_kullanici_id = $1
              AND v.aktif = true
              AND v.baslangic <= CURRENT_DATE
              AND v.bitis >= CURRENT_DATE
        """, kullanici_id)
        return {r["rol"] for r in rows}
