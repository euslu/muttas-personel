from typing import Optional
from datetime import date

from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel

from db import get_pool
from permissions import decode_token, require_ik_editor

router = APIRouter(prefix="/izinler", tags=["izinler"])

IZIN_TURLERI = ["yillik", "ucretsiz", "mazeret", "hastalik", "dogum", "olum", "diger"]
DURUMLAR     = ["beklemede", "ik_onayladi", "mudur_onayladi", "onaylandi", "reddedildi", "tamamlandi"]


class IzinCreate(BaseModel):
    personel_id:      int
    talep_tarihi:     Optional[date] = None
    izin_turu:        str
    baslangic:        date
    bitis:            date
    gun_sayisi:       int
    kullanilabilir_gun: Optional[int] = None
    vekil_ad_soyad:   Optional[str] = None
    izin_adresi:      Optional[str] = None
    notlar:           Optional[str] = None
    imza:             Optional[str] = None


class IzinOnay(BaseModel):
    durum:     str
    onaylayan: Optional[str] = None
    notlar:    Optional[str] = None
    imza:      Optional[str] = None


def fmt(d):
    return d.isoformat() if d else None


def row_to_dict(r):
    return {k: (fmt(v) if isinstance(v, date) else v) for k, v in dict(r).items()}


@router.get("")
async def list_izinler(
    personel_id: Optional[int]  = Query(None),
    izin_turu:   Optional[str]  = Query(None),
    durum:       Optional[str]  = Query(None),
    yil:         Optional[int]  = Query(None),
    q:           Optional[str]  = Query(None),
    page:        int = Query(1, ge=1),
    per_page:    int = Query(25, ge=1, le=100),
    token:       dict = Depends(decode_token),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        wheres = []
        params = []

        if personel_id:
            params.append(personel_id)
            wheres.append(f"i.personel_id = ${len(params)}")

        if izin_turu:
            params.append(izin_turu)
            wheres.append(f"i.izin_turu = ${len(params)}")

        if durum:
            params.append(durum)
            wheres.append(f"i.durum = ${len(params)}")

        if yil:
            params.append(yil)
            wheres.append(f"EXTRACT(YEAR FROM i.baslangic) = ${len(params)}")

        if q:
            params.append(f"%{q}%")
            wheres.append(f"p.ad_soyad ILIKE ${len(params)}")

        where_sql = "WHERE " + " AND ".join(wheres) if wheres else ""

        toplam = await conn.fetchval(f"""
            SELECT COUNT(*) FROM izinler i
            JOIN personel p ON p.id = i.personel_id
            {where_sql}
        """, *params)

        offset = (page - 1) * per_page
        rows = await conn.fetch(f"""
            SELECT i.*, p.ad_soyad, p.bolum, p.unvan, p.ilce
            FROM izinler i
            JOIN personel p ON p.id = i.personel_id
            {where_sql}
            ORDER BY i.olusturuldu DESC
            LIMIT ${len(params)+1} OFFSET ${len(params)+2}
        """, *params, per_page, offset)

        return {
            "toplam":   toplam,
            "sayfa":    page,
            "per_page": per_page,
            "veri": [row_to_dict(r) for r in rows],
        }


@router.get("/ozet")
async def get_ozet(
    yil:   int = Query(None),
    token: dict = Depends(decode_token),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        if not yil:
            from datetime import datetime
            yil = datetime.now().year

        rows = await conn.fetch("""
            SELECT
                izin_turu,
                durum,
                COUNT(*)         AS adet,
                SUM(gun_sayisi)  AS toplam_gun
            FROM izinler
            WHERE EXTRACT(YEAR FROM baslangic) = $1
            GROUP BY izin_turu, durum
            ORDER BY izin_turu, durum
        """, yil)

        bekleyen = await conn.fetchval(
            "SELECT COUNT(*) FROM izinler WHERE durum NOT IN ('onaylandi','reddedildi','tamamlandi')"
        )

        return {
            "yil":      yil,
            "bekleyen": int(bekleyen),
            "turlere_gore": [dict(r) for r in rows],
        }


@router.get("/{iid}")
async def get_izin(iid: int, token: dict = Depends(decode_token)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        r = await conn.fetchrow("""
            SELECT i.*, p.ad_soyad, p.tc_kimlik, p.bolum, p.unvan, p.ilce, p.hizmet_noktasi, p.telefon
            FROM izinler i
            JOIN personel p ON p.id = i.personel_id
            WHERE i.id = $1
        """, iid)
        if not r:
            raise HTTPException(status_code=404, detail="İzin kaydı bulunamadı.")
        return row_to_dict(r)


@router.post("", status_code=201)
async def create_izin(body: IzinCreate, token: dict = Depends(require_ik_editor)):
    if body.izin_turu not in IZIN_TURLERI:
        raise HTTPException(status_code=400, detail=f"Geçersiz izin türü. Kabul edilenler: {IZIN_TURLERI}")

    pool = await get_pool()
    async with pool.acquire() as conn:
        exists = await conn.fetchval("SELECT id FROM personel WHERE id = $1 AND aktif = TRUE", body.personel_id)
        if not exists:
            raise HTTPException(status_code=404, detail="Personel bulunamadı.")

        talep = body.talep_tarihi or date.today()
        row = await conn.fetchrow("""
            INSERT INTO izinler (
                personel_id, talep_tarihi, izin_turu, baslangic, bitis,
                gun_sayisi, kullanilabilir_gun, vekil_ad_soyad, izin_adresi, notlar, imza
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
            RETURNING id
        """,
            body.personel_id, talep, body.izin_turu, body.baslangic, body.bitis,
            body.gun_sayisi, body.kullanilabilir_gun, body.vekil_ad_soyad,
            body.izin_adresi, body.notlar, body.imza,
        )
        return {"id": row["id"]}


@router.put("/{iid}")
async def update_izin(iid: int, body: IzinCreate, token: dict = Depends(require_ik_editor)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        exists = await conn.fetchval(
            "SELECT id FROM izinler WHERE id = $1 AND durum = 'beklemede'", iid
        )
        if not exists:
            raise HTTPException(status_code=400, detail="Sadece beklemede olan izinler düzenlenebilir.")

        await conn.execute("""
            UPDATE izinler SET
                izin_turu = $2, baslangic = $3, bitis = $4, gun_sayisi = $5,
                kullanilabilir_gun = $6, vekil_ad_soyad = $7, izin_adresi = $8,
                notlar = $9, talep_tarihi = $10, imza = COALESCE($11, imza)
            WHERE id = $1
        """,
            iid, body.izin_turu, body.baslangic, body.bitis, body.gun_sayisi,
            body.kullanilabilir_gun, body.vekil_ad_soyad, body.izin_adresi,
            body.notlar, body.talep_tarihi or date.today(), body.imza,
        )
        return {"ok": True}


@router.put("/{iid}/onay")
async def onay_izin(iid: int, body: IzinOnay, token: dict = Depends(require_ik_editor)):
    if body.durum not in DURUMLAR:
        raise HTTPException(status_code=400, detail=f"Geçersiz durum. Kabul edilenler: {DURUMLAR}")

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT durum FROM izinler WHERE id = $1", iid)
        if not row:
            raise HTTPException(status_code=404, detail="İzin kaydı bulunamadı.")

        today = date.today()
        extra_sets = ""
        extra_vals = []

        if body.durum == "ik_onayladi":
            extra_sets = ", ik_onay_tarihi = $4, ik_onaylayan = $5, ik_imza = $6"
            extra_vals = [today, body.onaylayan, body.imza]
        elif body.durum == "mudur_onayladi":
            extra_sets = ", mudur_onay_tarihi = $4, mudur_imza = $5"
            extra_vals = [today, body.imza]
        elif body.durum == "onaylandi":
            extra_sets = ", yk_onay_tarihi = $4, yk_imza = $5"
            extra_vals = [today, body.imza]
        elif body.durum == "tamamlandi":
            extra_sets = ", gorev_baslama = $4"
            extra_vals = [today]

        base_params = [iid, body.durum, body.notlar]
        await conn.execute(
            f"UPDATE izinler SET durum = $2, notlar = COALESCE($3, notlar){extra_sets} WHERE id = $1",
            *base_params, *extra_vals,
        )
        return {"ok": True}


@router.delete("/{iid}")
async def delete_izin(iid: int, token: dict = Depends(require_ik_editor)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        exists = await conn.fetchval(
            "SELECT id FROM izinler WHERE id = $1 AND durum = 'beklemede'", iid
        )
        if not exists:
            raise HTTPException(status_code=400, detail="Sadece beklemede olan izinler silinebilir.")
        await conn.execute("DELETE FROM izinler WHERE id = $1", iid)
        return {"ok": True}


@router.get("/personel-izin-gecmisi/{pid}")
async def personel_izin_gecmisi(pid: int, token: dict = Depends(decode_token)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        exists = await conn.fetchval("SELECT id FROM personel WHERE id = $1", pid)
        if not exists:
            raise HTTPException(status_code=404, detail="Personel bulunamadı.")

        gecmis = await conn.fetch("""
            SELECT id, baslangic, bitis, gun_sayisi, kalan_izin, toplam_hak, 'gecmis' as tip
            FROM izin_gecmisi
            WHERE personel_id = $1
            ORDER BY baslangic DESC
        """, pid)

        aktif = await conn.fetch("""
            SELECT id, baslangic, bitis, gun_sayisi, izin_turu, durum,
                   kullanilabilir_gun, vekil_ad_soyad, izin_adresi, notlar, 'sistem' as tip
            FROM izinler
            WHERE personel_id = $1
            ORDER BY baslangic DESC
        """, pid)

        def fmt(d):
            return d.isoformat() if d else None

        return {
            "gecmis": [
                {
                    "id": r["id"],
                    "baslangic": fmt(r["baslangic"]),
                    "bitis": fmt(r["bitis"]),
                    "gun_sayisi": r["gun_sayisi"],
                    "kalan_izin": r["kalan_izin"],
                    "toplam_hak": r["toplam_hak"],
                    "tip": "gecmis",
                }
                for r in gecmis
            ],
            "aktif": [
                {
                    "id": r["id"],
                    "baslangic": fmt(r["baslangic"]),
                    "bitis": fmt(r["bitis"]),
                    "gun_sayisi": r["gun_sayisi"],
                    "izin_turu": r["izin_turu"],
                    "durum": r["durum"],
                    "kullanilabilir_gun": r["kullanilabilir_gun"],
                    "vekil_ad_soyad": r["vekil_ad_soyad"],
                    "izin_adresi": r["izin_adresi"],
                    "notlar": r["notlar"],
                    "tip": "sistem",
                }
                for r in aktif
            ],
        }
