from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from db import get_pool
from permissions import decode_token
import json

router = APIRouter(prefix="/ihtiyac-talebi", tags=["ihtiyac-talebi"])

IT_ONAY_ROLLERI = {"admin", "genel_mudur"}
YK_ONAY_ROLLERI = {"admin", "yk_baskani"}


class KalemModel(BaseModel):
    sira: int = 1
    ad: str
    miktar: float = 1
    birim: str = "Adet"
    aciklama: Optional[str] = None


class IhtiyacCreate(BaseModel):
    konu: str
    talep_eden: str
    talep_eden_id: Optional[int] = None
    lokasyonlar: List[str] = []
    diger_lokasyon: Optional[str] = None
    aciklama: Optional[str] = None


class KalemlerUpdate(BaseModel):
    kalemler: List[KalemModel]


def _fmt(d):
    return d.isoformat() if d else None


def _row(r):
    row = {k: (_fmt(v) if isinstance(v, date) else v) for k, v in dict(r).items()}
    if row.get("lokasyonlar") and isinstance(row["lokasyonlar"], str):
        try:
            row["lokasyonlar"] = json.loads(row["lokasyonlar"])
        except Exception:
            row["lokasyonlar"] = []
    elif row.get("lokasyonlar") is None:
        row["lokasyonlar"] = []
    return row


@router.get("/hizmet-noktalari")
async def get_hizmet_noktalari(token: dict = Depends(decode_token)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT DISTINCT hizmet_noktasi FROM personel
            WHERE hizmet_noktasi IS NOT NULL AND hizmet_noktasi != ''
            ORDER BY hizmet_noktasi
        """)
        return [r["hizmet_noktasi"] for r in rows]


@router.get("")
async def list_ihtiyac(
    q: Optional[str] = Query(None),
    durum: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    token: dict = Depends(decode_token),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        wheres, params = [], []
        if q:
            params.append(f"%{q}%")
            wheres.append(f"(it.konu ILIKE ${len(params)} OR it.talep_eden ILIKE ${len(params)})")
        if durum:
            params.append(durum)
            wheres.append(f"it.durum = ${len(params)}")
        where = ("WHERE " + " AND ".join(wheres)) if wheres else ""
        params.append(per_page)
        params.append((page - 1) * per_page)
        rows = await conn.fetch(f"""
            SELECT it.*, COUNT(*) OVER() AS toplam,
                   (SELECT COUNT(*) FROM ihtiyac_talebi_kalemler WHERE talep_id = it.id) AS kalem_sayisi
            FROM ihtiyac_talebi it
            {where}
            ORDER BY it.created_at DESC
            LIMIT ${len(params)-1} OFFSET ${len(params)}
        """, *params)
        toplam = rows[0]["toplam"] if rows else 0
        return {"toplam": int(toplam), "kayitlar": [_row(r) for r in rows]}


@router.post("", status_code=201)
async def create_ihtiyac(body: IhtiyacCreate, token: dict = Depends(decode_token)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        lok_json = json.dumps(body.lokasyonlar, ensure_ascii=False)
        row = await conn.fetchrow("""
            INSERT INTO ihtiyac_talebi
                (konu, talep_eden, talep_eden_id, lokasyonlar, diger_lokasyon, aciklama,
                 durum, olusturan_id, olusturan_ad)
            VALUES ($1,$2,$3,$4,$5,$6,'beklemede',$7,$8)
            RETURNING *
        """, body.konu, body.talep_eden, body.talep_eden_id,
             lok_json, body.diger_lokasyon, body.aciklama,
             token.get("id"), (token.get("ad","") + " " + token.get("soyad","")).strip())
        return _row(row)


@router.get("/{tid}")
async def get_ihtiyac(tid: int, token: dict = Depends(decode_token)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM ihtiyac_talebi WHERE id=$1", tid)
        if not row:
            raise HTTPException(404, "Talep bulunamadı.")
        kalemler = await conn.fetch(
            "SELECT * FROM ihtiyac_talebi_kalemler WHERE talep_id=$1 ORDER BY sira", tid)
        result = _row(row)
        result["kalemler"] = [dict(k) for k in kalemler]
        return result


@router.put("/{tid}")
async def update_ihtiyac(tid: int, body: IhtiyacCreate, token: dict = Depends(decode_token)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow("SELECT durum FROM ihtiyac_talebi WHERE id=$1", tid)
        if not existing:
            raise HTTPException(404, "Talep bulunamadı.")
        if existing["durum"] not in ("beklemede", "reddedildi") and token.get("rol") not in ("admin", "ik_admin"):
            raise HTTPException(403, "Onaylı talepler düzenlenemez.")
        lok_json = json.dumps(body.lokasyonlar, ensure_ascii=False)
        row = await conn.fetchrow("""
            UPDATE ihtiyac_talebi
            SET konu=$1, talep_eden=$2, talep_eden_id=$3,
                lokasyonlar=$4, diger_lokasyon=$5, aciklama=$6, updated_at=NOW()
            WHERE id=$7 RETURNING *
        """, body.konu, body.talep_eden, body.talep_eden_id,
             lok_json, body.diger_lokasyon, body.aciklama, tid)
        return _row(row)


@router.put("/{tid}/kalemler")
async def update_kalemler(tid: int, body: KalemlerUpdate, token: dict = Depends(decode_token)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM ihtiyac_talebi_kalemler WHERE talep_id=$1", tid)
        for k in body.kalemler:
            await conn.execute("""
                INSERT INTO ihtiyac_talebi_kalemler (talep_id, sira, ad, miktar, birim, aciklama)
                VALUES ($1,$2,$3,$4,$5,$6)
            """, tid, k.sira, k.ad, k.miktar, k.birim, k.aciklama)
        rows = await conn.fetch(
            "SELECT * FROM ihtiyac_talebi_kalemler WHERE talep_id=$1 ORDER BY sira", tid)
        return [dict(r) for r in rows]


@router.post("/{tid}/gm-onayla")
async def gm_onayla(tid: int, token: dict = Depends(decode_token)):
    if token.get("rol") not in IT_ONAY_ROLLERI:
        raise HTTPException(403, "Genel Müdür yetkisi gereklidir.")
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT durum FROM ihtiyac_talebi WHERE id=$1", tid)
        if not row:
            raise HTTPException(404, "Talep bulunamadı.")
        if row["durum"] != "beklemede":
            raise HTTPException(400, "Talep 'Beklemede' durumunda olmalıdır.")
        ad = (token.get("ad","") + " " + token.get("soyad","")).strip()
        await conn.execute("""
            UPDATE ihtiyac_talebi
            SET durum='gm_onayladi', gm_onay_ad=$1, gm_onay_tarih=NOW(), updated_at=NOW()
            WHERE id=$2
        """, ad, tid)
        return {"ok": True}


@router.post("/{tid}/yk-onayla")
async def yk_onayla(tid: int, token: dict = Depends(decode_token)):
    if token.get("rol") not in YK_ONAY_ROLLERI:
        raise HTTPException(403, "YK Başkanı yetkisi gereklidir.")
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT durum FROM ihtiyac_talebi WHERE id=$1", tid)
        if not row:
            raise HTTPException(404, "Talep bulunamadı.")
        if row["durum"] != "gm_onayladi":
            raise HTTPException(400, "Talep 'GM Onaylı' durumunda olmalıdır.")
        ad = (token.get("ad","") + " " + token.get("soyad","")).strip()
        await conn.execute("""
            UPDATE ihtiyac_talebi
            SET durum='yk_onayladi', yk_onay_ad=$1, yk_onay_tarih=NOW(), updated_at=NOW()
            WHERE id=$2
        """, ad, tid)
        return {"ok": True}


@router.post("/{tid}/reddet")
async def reddet(tid: int, token: dict = Depends(decode_token)):
    if token.get("rol") not in (IT_ONAY_ROLLERI | YK_ONAY_ROLLERI):
        raise HTTPException(403, "Yetkiniz yok.")
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE ihtiyac_talebi SET durum='reddedildi', updated_at=NOW() WHERE id=$1", tid)
        return {"ok": True}


@router.post("/{tid}/satin-almaya-don")
async def satin_almaya_don(tid: int, token: dict = Depends(decode_token)):
    rol = token.get("rol")
    if rol not in {"admin", "ik_admin", "genel_mudur", "mudur", "yk_baskani"}:
        raise HTTPException(403, "Yetkiniz yok.")
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM ihtiyac_talebi WHERE id=$1", tid)
        if not row:
            raise HTTPException(404, "Talep bulunamadı.")
        if row["durum"] != "yk_onayladi":
            raise HTTPException(400, "Sadece YK onaylı talepler satın almaya dönüştürülebilir.")
        olusturan = (token.get("ad","") + " " + token.get("soyad","")).strip()
        sa_row = await conn.fetchrow("""
            INSERT INTO satin_alma
                (konu, tur, durum, tarih, aciklama, olusturan_ad, ihtiyac_talep_id)
            VALUES ($1,'dogrudan_temin','hazirlaniyor',CURRENT_DATE,$2,$3,$4)
            RETURNING *
        """, row["konu"], row["aciklama"], olusturan, tid)
        kalemler = await conn.fetch(
            "SELECT * FROM ihtiyac_talebi_kalemler WHERE talep_id=$1 ORDER BY sira", tid)
        for k in kalemler:
            await conn.execute("""
                INSERT INTO satin_alma_kalemler (satin_alma_id, sira, ad, miktar, birim)
                VALUES ($1,$2,$3,$4,$5)
            """, sa_row["id"], k["sira"], k["ad"], k["miktar"], k["birim"])
        await conn.execute("""
            UPDATE ihtiyac_talebi
            SET durum='satin_almaya_donusturuldu', satin_alma_id=$1, updated_at=NOW()
            WHERE id=$2
        """, sa_row["id"], tid)
        return {"sa_id": sa_row["id"]}


@router.delete("/{tid}")
async def delete_ihtiyac(tid: int, token: dict = Depends(decode_token)):
    if token.get("rol") not in {"admin", "ik_admin"}:
        raise HTTPException(403, "Yetkiniz yok.")
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM ihtiyac_talebi_kalemler WHERE talep_id=$1", tid)
        r = await conn.execute("DELETE FROM ihtiyac_talebi WHERE id=$1", tid)
        if r == "DELETE 0":
            raise HTTPException(404, "Talep bulunamadı.")
        return {"ok": True}
