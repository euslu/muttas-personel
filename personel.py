import os
import shutil
import uuid
from pathlib import Path
from typing import Optional
from datetime import date

from fastapi import APIRouter, HTTPException, Query, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from db import get_pool
from permissions import decode_token, require_ik_editor

UPLOAD_DIR = Path("uploads/personel")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/personel", tags=["personel"])


class PersonelCreate(BaseModel):
    tc_kimlik:          Optional[str] = None
    sgk_sicil:          Optional[str] = None
    maliyet_merkezi:    Optional[str] = None
    ilce:               Optional[str] = None
    hizmet_noktasi:     Optional[str] = None
    ad_soyad:           str
    cinsiyet:           Optional[str] = None
    bolum:              Optional[str] = None
    unvan:              Optional[str] = None
    ise_giris:          Optional[date] = None
    isten_cikis:        Optional[date] = None
    cikis_kodu:         Optional[str] = None
    guvenlik_belge_tarih: Optional[date] = None
    sigortalilik_baslama: Optional[date] = None
    hizmet_gun:         Optional[int] = None
    ogrenim:            Optional[str] = None
    mezun_bolum:        Optional[str] = None
    brut_ucret:         Optional[float] = None
    dogum_yeri:         Optional[str] = None
    dogum_tarihi:       Optional[date] = None
    sendika_uyesi:      Optional[str] = None
    kan_grubu:          Optional[str] = None
    medeni_hal:         Optional[str] = None
    cocuk_sayisi:       Optional[int] = 0
    engelli:            Optional[bool] = False
    adres:              Optional[str] = None
    telefon:            Optional[str] = None
    meslek_kodu:        Optional[str] = None
    meslek_adi:         Optional[str] = None
    notlar:             Optional[str] = None


class PersonelUpdate(PersonelCreate):
    ad_soyad: Optional[str] = None
    aktif:    Optional[bool] = None


SORT_COLS = {
    "ad_soyad":             "p.ad_soyad",
    "bolum":                "p.bolum",
    "unvan":                "p.unvan",
    "ilce":                 "p.ilce",
    "ise_giris":            "p.ise_giris",
    "guvenlik_belge_tarih": "p.guvenlik_belge_tarih",
    "telefon":              "p.telefon",
}

@router.get("")
async def list_personel(
    q:        Optional[str] = Query(None),
    bolum:    Optional[str] = Query(None),
    unvan:    Optional[str] = Query(None),
    ilce:     Optional[str] = Query(None),
    aktif:    Optional[bool] = Query(None),
    sort_by:  Optional[str] = Query("ad_soyad"),
    sort_dir: Optional[str] = Query("asc"),
    page:     int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    token:    dict = Depends(decode_token),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        wheres = []
        params = []

        if q:
            params.append(f"%{q}%")
            wheres.append(f"(p.ad_soyad ILIKE ${len(params)} OR p.tc_kimlik ILIKE ${len(params)} OR p.telefon ILIKE ${len(params)})")

        if bolum:
            params.append(bolum)
            wheres.append(f"p.bolum = ${len(params)}")

        if unvan:
            params.append(unvan)
            wheres.append(f"p.unvan = ${len(params)}")

        if ilce:
            params.append(ilce)
            wheres.append(f"p.ilce = ${len(params)}")

        if aktif is not None:
            params.append(aktif)
            wheres.append(f"p.aktif = ${len(params)}")
        else:
            wheres.append("p.aktif = TRUE")

        where_sql = "WHERE " + " AND ".join(wheres) if wheres else ""

        toplam = await conn.fetchval(f"SELECT COUNT(*) FROM personel p {where_sql}", *params)

        order_col = SORT_COLS.get(sort_by or "ad_soyad", "p.ad_soyad")
        order_dir = "DESC" if (sort_dir or "asc").upper() == "DESC" else "ASC"
        order_sql = f"ORDER BY {order_col} {order_dir} NULLS LAST"

        offset = (page - 1) * per_page
        params_page = params + [per_page, offset]
        rows = await conn.fetch(f"""
            SELECT p.id, p.ad_soyad, p.tc_kimlik, p.bolum, p.unvan,
                   p.ilce, p.hizmet_noktasi, p.ise_giris, p.isten_cikis,
                   p.telefon, p.cinsiyet, p.aktif, p.brut_ucret,
                   p.guvenlik_belge_tarih, p.medeni_hal, p.cocuk_sayisi,
                   p.sendika_uyesi, p.maliyet_merkezi, p.olusturuldu
            FROM personel p
            {where_sql}
            {order_sql}
            LIMIT ${len(params_page)-1} OFFSET ${len(params_page)}
        """, *params_page)

        def fmt(d):
            return d.isoformat() if d else None

        return {
            "toplam": toplam,
            "sayfa": page,
            "per_page": per_page,
            "veri": [
                {
                    "id":                   r["id"],
                    "ad_soyad":             r["ad_soyad"],
                    "tc_kimlik":            r["tc_kimlik"],
                    "bolum":                r["bolum"],
                    "unvan":                r["unvan"],
                    "ilce":                 r["ilce"],
                    "hizmet_noktasi":       r["hizmet_noktasi"],
                    "ise_giris":            fmt(r["ise_giris"]),
                    "isten_cikis":          fmt(r["isten_cikis"]),
                    "telefon":              r["telefon"],
                    "cinsiyet":             r["cinsiyet"],
                    "aktif":                r["aktif"],
                    "brut_ucret":           float(r["brut_ucret"]) if r["brut_ucret"] else None,
                    "guvenlik_belge_tarih": fmt(r["guvenlik_belge_tarih"]),
                    "medeni_hal":           r["medeni_hal"],
                    "cocuk_sayisi":         r["cocuk_sayisi"],
                    "sendika_uyesi":        r["sendika_uyesi"],
                    "maliyet_merkezi":      r["maliyet_merkezi"],
                }
                for r in rows
            ],
        }


@router.get("/meta")
async def get_meta(token: dict = Depends(decode_token)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        bolumler = await conn.fetch("SELECT DISTINCT bolum FROM personel WHERE bolum IS NOT NULL ORDER BY bolum")
        unvanlar = await conn.fetch("SELECT DISTINCT unvan FROM personel WHERE unvan IS NOT NULL ORDER BY unvan")
        ilceler  = await conn.fetch("SELECT DISTINCT ilce  FROM personel WHERE ilce  IS NOT NULL ORDER BY ilce")
        return {
            "bolumler": [r["bolum"] for r in bolumler],
            "unvanlar": [r["unvan"] for r in unvanlar],
            "ilceler":  [r["ilce"]  for r in ilceler],
        }


@router.get("/{pid}")
async def get_personel(pid: int, token: dict = Depends(decode_token)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        r = await conn.fetchrow("SELECT * FROM personel WHERE id = $1", pid)
        if not r:
            raise HTTPException(status_code=404, detail="Personel bulunamadı.")

        def fmt(d):
            return d.isoformat() if d else None

        return {k: (fmt(v) if isinstance(v, date) else v) for k, v in dict(r).items()}


@router.post("", status_code=201)
async def create_personel(body: PersonelCreate, token: dict = Depends(require_ik_editor)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO personel (
                tc_kimlik, sgk_sicil, maliyet_merkezi, ilce, hizmet_noktasi,
                ad_soyad, cinsiyet, bolum, unvan, ise_giris, isten_cikis,
                cikis_kodu, guvenlik_belge_tarih, sigortalilik_baslama,
                hizmet_gun, ogrenim, mezun_bolum, brut_ucret,
                dogum_yeri, dogum_tarihi, sendika_uyesi, kan_grubu,
                medeni_hal, cocuk_sayisi, engelli, adres, telefon,
                meslek_kodu, meslek_adi, notlar
            ) VALUES (
                $1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,
                $15,$16,$17,$18,$19,$20,$21,$22,$23,$24,$25,$26,
                $27,$28,$29,$30
            ) RETURNING id
        """,
            body.tc_kimlik, body.sgk_sicil, body.maliyet_merkezi, body.ilce,
            body.hizmet_noktasi, body.ad_soyad, body.cinsiyet, body.bolum,
            body.unvan, body.ise_giris, body.isten_cikis, body.cikis_kodu,
            body.guvenlik_belge_tarih, body.sigortalilik_baslama, body.hizmet_gun,
            body.ogrenim, body.mezun_bolum, body.brut_ucret, body.dogum_yeri,
            body.dogum_tarihi, body.sendika_uyesi, body.kan_grubu, body.medeni_hal,
            body.cocuk_sayisi, body.engelli, body.adres, body.telefon,
            body.meslek_kodu, body.meslek_adi, body.notlar,
        )
        return {"id": row["id"]}


@router.put("/{pid}")
async def update_personel(pid: int, body: PersonelUpdate, token: dict = Depends(require_ik_editor)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        exists = await conn.fetchval("SELECT id FROM personel WHERE id = $1", pid)
        if not exists:
            raise HTTPException(status_code=404, detail="Personel bulunamadı.")

        fields = body.model_dump(exclude_none=True)
        if not fields:
            raise HTTPException(status_code=400, detail="Güncellenecek alan yok.")

        sets = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(fields))
        vals = list(fields.values())
        await conn.execute(f"UPDATE personel SET {sets} WHERE id = $1", pid, *vals)
        return {"ok": True}


@router.delete("/{pid}")
async def delete_personel(pid: int, token: dict = Depends(require_ik_editor)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE personel SET aktif = FALSE WHERE id = $1", pid)
        return {"ok": True}


# ── EVRAK ENDPOINTS ──────────────────────────────────────────

@router.get("/{pid}/evraklar")
async def list_evraklar(pid: int, token: dict = Depends(decode_token)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, evrak_adi, dosya_adi, dosya_boyut, mime_type, yuklendi_at "
            "FROM personel_evraklari WHERE personel_id = $1 ORDER BY yuklendi_at DESC",
            pid
        )
        return [
            {
                "id":          r["id"],
                "evrak_adi":   r["evrak_adi"],
                "dosya_adi":   r["dosya_adi"],
                "dosya_boyut": r["dosya_boyut"],
                "mime_type":   r["mime_type"],
                "yuklendi_at": r["yuklendi_at"].isoformat() if r["yuklendi_at"] else None,
            }
            for r in rows
        ]


@router.post("/{pid}/evraklar", status_code=201)
async def upload_evrak(
    pid:       int,
    evrak_adi: str = Form(...),
    dosya:     UploadFile = File(...),
    token:     dict = Depends(require_ik_editor),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        exists = await conn.fetchval("SELECT id FROM personel WHERE id = $1", pid)
        if not exists:
            raise HTTPException(status_code=404, detail="Personel bulunamadı.")

    dest_dir = UPLOAD_DIR / str(pid)
    dest_dir.mkdir(parents=True, exist_ok=True)

    ext      = Path(dosya.filename).suffix
    unique   = f"{uuid.uuid4().hex}{ext}"
    dest     = dest_dir / unique

    with dest.open("wb") as f:
        shutil.copyfileobj(dosya.file, f)

    boyut = dest.stat().st_size

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO personel_evraklari
               (personel_id, evrak_adi, dosya_adi, dosya_yolu, dosya_boyut, mime_type)
               VALUES ($1, $2, $3, $4, $5, $6) RETURNING id""",
            pid, evrak_adi, dosya.filename, str(dest), boyut, dosya.content_type,
        )
    return {"id": row["id"]}


@router.get("/evrak/{eid}/indir")
async def indir_evrak(eid: int, token: Optional[str] = Query(None),
                      credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))):
    t = token or (credentials.credentials if credentials else None)
    if not t:
        raise HTTPException(status_code=401, detail="Token gerekli.")
    try:
        jwt.decode(t, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Geçersiz token.")

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT dosya_yolu, dosya_adi, mime_type FROM personel_evraklari WHERE id = $1", eid
        )
    if not row:
        raise HTTPException(status_code=404, detail="Evrak bulunamadı.")
    path = Path(row["dosya_yolu"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="Dosya bulunamadı.")
    return FileResponse(path, media_type=row["mime_type"] or "application/octet-stream",
                        filename=row["dosya_adi"])


@router.delete("/evrak/{eid}")
async def delete_evrak(eid: int, token: dict = Depends(require_ik_editor)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT dosya_yolu FROM personel_evraklari WHERE id = $1", eid
        )
        if not row:
            raise HTTPException(status_code=404, detail="Evrak bulunamadı.")
        await conn.execute("DELETE FROM personel_evraklari WHERE id = $1", eid)

    path = Path(row["dosya_yolu"])
    if path.exists():
        path.unlink()
    return {"ok": True}
