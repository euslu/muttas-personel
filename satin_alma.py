from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from db import get_pool
from permissions import decode_token, IK_EDITORS

router = APIRouter(prefix="/satin-alma", tags=["satin-alma"])

SATIN_ALMA_EDITORS = IK_EDITORS | {"mudur"}


def require_sa_editor(token: dict = Depends(decode_token)) -> dict:
    if token.get("rol") not in SATIN_ALMA_EDITORS:
        raise HTTPException(status_code=403, detail="Bu işlem için yetkiniz yok.")
    return token


# ── Modeller ────────────────────────────────────────────────────────────────

class SatinAlmaCreate(BaseModel):
    sayi:       Optional[str]  = None
    konu:       str
    tur:        str            = "dogrudan_temin"
    durum:      str            = "hazirlaniyor"
    tarih:      Optional[date] = None
    aciklama:   Optional[str]  = None


class KalemCreate(BaseModel):
    sira:   int             = 1
    ad:     str
    miktar: float           = 1
    birim:  str             = "Adet"
    fiyat1: Optional[float] = None
    fiyat2: Optional[float] = None
    fiyat3: Optional[float] = None
    fiyat4: Optional[float] = None


class FirmaCreate(BaseModel):
    sira:      int = 1
    firma_adi: str


class KomisyonCreate(BaseModel):
    komisyon_turu: str
    gorev:         str = "uye"
    ad_soyad:      str
    unvan:         Optional[str] = None


# ── Yardımcı ────────────────────────────────────────────────────────────────

def _fmt(d):
    return d.isoformat() if d else None


def _row(r):
    return {k: (_fmt(v) if isinstance(v, date) else v) for k, v in dict(r).items()}


# ── Satın Alma CRUD ─────────────────────────────────────────────────────────

@router.get("")
async def list_satin_alma(
    q:        Optional[str] = Query(None),
    tur:      Optional[str] = Query(None),
    durum:    Optional[str] = Query(None),
    page:     int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    token: dict = Depends(decode_token),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        wheres, params = [], []
        if q:
            params.append(f"%{q}%")
            wheres.append(f"(s.konu ILIKE ${len(params)} OR s.sayi ILIKE ${len(params)})")
        if tur:
            params.append(tur)
            wheres.append(f"s.tur = ${len(params)}")
        if durum:
            params.append(durum)
            wheres.append(f"s.durum = ${len(params)}")
        where = ("WHERE " + " AND ".join(wheres)) if wheres else ""
        params.append(per_page)
        params.append((page - 1) * per_page)
        rows = await conn.fetch(f"""
            SELECT s.*,
                   COUNT(*) OVER() AS toplam,
                   (SELECT COUNT(*) FROM satin_alma_kalemler WHERE satin_alma_id = s.id) AS kalem_sayisi
            FROM satin_alma s
            {where}
            ORDER BY s.created_at DESC
            LIMIT ${len(params)-1} OFFSET ${len(params)}
        """, *params)
        toplam = rows[0]["toplam"] if rows else 0
        return {"toplam": int(toplam), "kayitlar": [_row(r) for r in rows]}


@router.post("", status_code=201)
async def create_satin_alma(body: SatinAlmaCreate, token: dict = Depends(require_sa_editor)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO satin_alma (sayi, konu, tur, durum, tarih, aciklama, olusturan_ad)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            RETURNING *
        """, body.sayi, body.konu, body.tur, body.durum,
             body.tarih or date.today(), body.aciklama,
             token.get("ad", "") + " " + token.get("soyad", ""))
        return _row(row)


@router.get("/{sid}")
async def get_satin_alma(sid: int, token: dict = Depends(decode_token)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM satin_alma WHERE id = $1", sid)
        if not row:
            raise HTTPException(404, "Kayıt bulunamadı.")
        kalemler  = await conn.fetch("SELECT * FROM satin_alma_kalemler  WHERE satin_alma_id=$1 ORDER BY sira", sid)
        firmalar  = await conn.fetch("SELECT * FROM satin_alma_firmalar  WHERE satin_alma_id=$1 ORDER BY sira", sid)
        komisyon  = await conn.fetch("SELECT * FROM satin_alma_komisyon  WHERE satin_alma_id=$1 ORDER BY komisyon_turu, gorev DESC", sid)
        return {
            **_row(row),
            "kalemler": [dict(r) for r in kalemler],
            "firmalar": [dict(r) for r in firmalar],
            "komisyon": [dict(r) for r in komisyon],
        }


@router.put("/{sid}")
async def update_satin_alma(sid: int, body: SatinAlmaCreate, token: dict = Depends(require_sa_editor)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            UPDATE satin_alma SET sayi=$1, konu=$2, tur=$3, durum=$4, tarih=$5, aciklama=$6
            WHERE id=$7 RETURNING *
        """, body.sayi, body.konu, body.tur, body.durum,
             body.tarih or date.today(), body.aciklama, sid)
        if not row:
            raise HTTPException(404, "Kayıt bulunamadı.")
        return _row(row)


@router.delete("/{sid}", status_code=204)
async def delete_satin_alma(sid: int, token: dict = Depends(require_sa_editor)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        r = await conn.execute("DELETE FROM satin_alma WHERE id=$1", sid)
        if r == "DELETE 0":
            raise HTTPException(404, "Kayıt bulunamadı.")


# ── Kalemler ────────────────────────────────────────────────────────────────

@router.put("/{sid}/kalemler")
async def upsert_kalemler(sid: int, kalemler: List[KalemCreate], token: dict = Depends(require_sa_editor)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM satin_alma_kalemler WHERE satin_alma_id=$1", sid)
        for k in kalemler:
            await conn.execute("""
                INSERT INTO satin_alma_kalemler (satin_alma_id, sira, ad, miktar, birim, fiyat1, fiyat2, fiyat3, fiyat4)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
            """, sid, k.sira, k.ad, k.miktar, k.birim, k.fiyat1, k.fiyat2, k.fiyat3, k.fiyat4)
        rows = await conn.fetch("SELECT * FROM satin_alma_kalemler WHERE satin_alma_id=$1 ORDER BY sira", sid)
        return [dict(r) for r in rows]


# ── Firmalar ─────────────────────────────────────────────────────────────────

@router.put("/{sid}/firmalar")
async def upsert_firmalar(sid: int, firmalar: List[FirmaCreate], token: dict = Depends(require_sa_editor)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM satin_alma_firmalar WHERE satin_alma_id=$1", sid)
        for f in firmalar:
            await conn.execute("""
                INSERT INTO satin_alma_firmalar (satin_alma_id, sira, firma_adi) VALUES ($1,$2,$3)
            """, sid, f.sira, f.firma_adi)
        rows = await conn.fetch("SELECT * FROM satin_alma_firmalar WHERE satin_alma_id=$1 ORDER BY sira", sid)
        return [dict(r) for r in rows]


# ── Komisyon ─────────────────────────────────────────────────────────────────

@router.put("/{sid}/komisyon")
async def upsert_komisyon(sid: int, komisyon: List[KomisyonCreate], token: dict = Depends(require_sa_editor)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM satin_alma_komisyon WHERE satin_alma_id=$1", sid)
        for k in komisyon:
            await conn.execute("""
                INSERT INTO satin_alma_komisyon (satin_alma_id, komisyon_turu, gorev, ad_soyad, unvan)
                VALUES ($1,$2,$3,$4,$5)
            """, sid, k.komisyon_turu, k.gorev, k.ad_soyad, k.unvan)
        rows = await conn.fetch("SELECT * FROM satin_alma_komisyon WHERE satin_alma_id=$1 ORDER BY komisyon_turu, gorev DESC", sid)
        return [dict(r) for r in rows]
