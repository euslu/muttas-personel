from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from datetime import date
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


class IzinTuruBody(BaseModel):
    kod: str
    ad:  str


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


class YkUyeUnvanBody(BaseModel):
    unvan: str


@router.get("/yk-uye-unvanlar")
async def get_yk_uye_unvanlar(token: dict = Depends(decode_token)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT unvan FROM yk_uye_unvanlar ORDER BY unvan"
        )
    return [r["unvan"] for r in rows]


@router.post("/yk-uye-unvanlar", status_code=201)
async def add_yk_uye_unvan(
    body: YkUyeUnvanBody,
    token: dict = Depends(require_ayar_editor),
):
    unvan = body.unvan.strip().upper()
    if not unvan:
        raise HTTPException(status_code=400, detail="Unvan boş olamaz.")
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO yk_uye_unvanlar (unvan) VALUES ($1) ON CONFLICT DO NOTHING",
            unvan,
        )
        await conn.execute(
            """
            UPDATE kullanicilar k
            SET rol = 'genel_mudur'
            FROM personel p
            WHERE LOWER(REPLACE(p.tc_kimlik,' ','')) = k.email
              AND p.unvan = $1
              AND k.aktif = TRUE
            """,
            unvan,
        )
    return {"ok": True}


@router.delete("/yk-uye-unvanlar")
async def remove_yk_uye_unvan(
    body: YkUyeUnvanBody,
    token: dict = Depends(require_ayar_editor),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM yk_uye_unvanlar WHERE unvan = $1", body.unvan
        )
    return {"ok": True}


@router.get("/ks-listesi")
async def get_ks_listesi(token: dict = Depends(require_ayar_editor)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT p.id AS personel_id, p.ad_soyad, k.rol
            FROM kullanicilar k
            JOIN personel p ON LOWER(REPLACE(p.tc_kimlik,' ','')) = k.email
            WHERE k.rol IN ('koordinasyon_sorumlusu', 'mudur') AND k.aktif = TRUE AND p.aktif = TRUE
            ORDER BY p.ad_soyad
        """)
        return [{"personel_id": r["personel_id"], "ad_soyad": r["ad_soyad"], "rol": r["rol"]} for r in rows]


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


# ── Resmi Tatiller ─────────────────────────────────────────────────────────────

class ResmiTatilEkle(BaseModel):
    ad: str
    tarih: date
    gun: float


class ResmiTatilGuncelle(BaseModel):
    ad: str
    gun: float


@router.get("/resmi-tatiller")
async def get_resmi_tatiller(token: dict = Depends(decode_token)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, ad, tarih::text, gun::float FROM resmi_tatiller ORDER BY tarih"
        )
        return [dict(r) for r in rows]


@router.post("/resmi-tatiller", status_code=201)
async def add_resmi_tatil(body: ResmiTatilEkle, token: dict = Depends(require_ayar_editor)):
    if not body.ad.strip():
        raise HTTPException(status_code=400, detail="Ad boş olamaz.")
    if body.gun <= 0:
        raise HTTPException(status_code=400, detail="Gün sayısı 0'dan büyük olmalıdır.")
    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            row = await conn.fetchrow(
                "INSERT INTO resmi_tatiller (ad, tarih, gun) VALUES ($1, $2, $3) RETURNING id",
                body.ad.strip(), body.tarih, body.gun
            )
        except Exception:
            raise HTTPException(status_code=409, detail="Bu tarihte zaten bir tatil kayıtlı.")
    return {"id": row["id"]}


@router.put("/resmi-tatiller/{tid}")
async def update_resmi_tatil(tid: int, body: ResmiTatilGuncelle, token: dict = Depends(require_ayar_editor)):
    if not body.ad.strip():
        raise HTTPException(status_code=400, detail="Ad boş olamaz.")
    pool = await get_pool()
    async with pool.acquire() as conn:
        exists = await conn.fetchval("SELECT id FROM resmi_tatiller WHERE id = $1", tid)
        if not exists:
            raise HTTPException(status_code=404, detail="Tatil bulunamadı.")
        await conn.execute(
            "UPDATE resmi_tatiller SET ad=$1, gun=$2 WHERE id=$3",
            body.ad.strip(), body.gun, tid
        )
    return {"ok": True}


@router.delete("/resmi-tatiller/{tid}")
async def delete_resmi_tatil(tid: int, token: dict = Depends(require_ayar_editor)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        exists = await conn.fetchval("SELECT id FROM resmi_tatiller WHERE id = $1", tid)
        if not exists:
            raise HTTPException(status_code=404, detail="Tatil bulunamadı.")
        await conn.execute("DELETE FROM resmi_tatiller WHERE id=$1", tid)
    return {"ok": True}


# ── YK Başkan Vekili ───────────────────────────────────────────────────────────

class YkBvEkle(BaseModel):
    personel_id: int


@router.get("/yk-baskan-vekili")
async def get_yk_baskan_vekili(token: dict = Depends(require_ayar_editor)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT b.id, b.personel_id, p.ad_soyad, p.unvan, p.bolum
            FROM yk_baskan_vekili b
            JOIN personel p ON p.id = b.personel_id
            ORDER BY p.ad_soyad
        """)
        return [dict(r) for r in rows]


@router.post("/yk-baskan-vekili", status_code=201)
async def add_yk_baskan_vekili(body: YkBvEkle, token: dict = Depends(require_ayar_editor)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        p = await conn.fetchval("SELECT id FROM personel WHERE id=$1 AND aktif=TRUE", body.personel_id)
        if not p:
            raise HTTPException(status_code=404, detail="Personel bulunamadı.")
        try:
            row = await conn.fetchrow(
                "INSERT INTO yk_baskan_vekili (personel_id) VALUES($1) RETURNING id",
                body.personel_id
            )
        except Exception:
            raise HTTPException(status_code=409, detail="Bu personel zaten YK Başkan Vekili listesinde.")
    return {"id": row["id"]}


@router.delete("/yk-baskan-vekili/{bid}")
async def remove_yk_baskan_vekili(bid: int, token: dict = Depends(require_ayar_editor)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        exists = await conn.fetchval("SELECT id FROM yk_baskan_vekili WHERE id=$1", bid)
        if not exists:
            raise HTTPException(status_code=404, detail="Kayıt bulunamadı.")
        await conn.execute("DELETE FROM yk_baskan_vekili WHERE id=$1", bid)
    return {"ok": True}


@router.get("/izin-turleri")
async def get_izin_turleri(token: dict = Depends(decode_token)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT kod, ad FROM izin_turleri WHERE aktif = TRUE ORDER BY sira, ad")
        return [{"kod": r["kod"], "ad": r["ad"]} for r in rows]


@router.post("/izin-turleri", status_code=201)
async def ekle_izin_turu(body: IzinTuruBody, token: dict = Depends(require_ayar_editor)):
    import re as _re
    kod = body.kod.strip().lower().replace(" ", "_")
    ad  = body.ad.strip()
    if not kod or not ad:
        raise HTTPException(status_code=400, detail="Kod ve ad boş olamaz.")
    if not _re.match(r'^[a-z][a-z0-9_]*$', kod):
        raise HTTPException(status_code=400, detail="Kod sadece küçük harf, rakam ve alt çizgi içerebilir, harfle başlamalıdır.")
    pool = await get_pool()
    async with pool.acquire() as conn:
        exists = await conn.fetchval("SELECT id FROM izin_turleri WHERE kod=$1", kod)
        if exists:
            raise HTTPException(status_code=409, detail="Bu kod zaten mevcut.")
        max_sira = await conn.fetchval("SELECT COALESCE(MAX(sira),0) FROM izin_turleri") or 0
        await conn.execute(
            "INSERT INTO izin_turleri (kod, ad, sira) VALUES ($1, $2, $3)",
            kod, ad, max_sira + 1
        )
    return {"ok": True, "kod": kod}


@router.delete("/izin-turleri/{kod}")
async def sil_izin_turu(kod: str, token: dict = Depends(require_ayar_editor)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        kullanimda = await conn.fetchval(
            "SELECT COUNT(*) FROM izinler WHERE izin_turu = $1", kod
        )
        if kullanimda and kullanimda > 0:
            raise HTTPException(
                status_code=409,
                detail=f"Bu izin türünde {kullanimda} kayıt var. Silinemez, pasif yapılabilir."
            )
        result = await conn.execute("DELETE FROM izin_turleri WHERE kod=$1", kod)
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="İzin türü bulunamadı.")
    return {"ok": True}


@router.get("/yk-bv-personel-havuzu")
async def get_yk_bv_personel_havuzu(q: str = "", token: dict = Depends(require_ayar_editor)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        mevcut = await conn.fetch("SELECT personel_id FROM yk_baskan_vekili")
        mevcut_ids = [r["personel_id"] for r in mevcut]
        rows = await conn.fetch("""
            SELECT p.id, p.ad_soyad, p.unvan, p.bolum
            FROM personel p
            WHERE p.aktif = TRUE
              AND p.id != ALL($1::int[])
              AND ($2 = '' OR p.ad_soyad ILIKE $3)
            ORDER BY p.ad_soyad
            LIMIT 30
        """, mevcut_ids or [-1], q, f"%{q}%")
        return [dict(r) for r in rows]


# ── Genel Müdür Vekili ──────────────────────────────────────────────────────

class GmVekilEkle(BaseModel):
    personel_id: int


@router.get("/genel-mudur-vekili")
async def get_genel_mudur_vekili(token: dict = Depends(require_ayar_editor)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT b.id, b.personel_id, p.ad_soyad, p.unvan, p.bolum
            FROM genel_mudur_vekili b
            JOIN personel p ON p.id = b.personel_id
            ORDER BY p.ad_soyad
        """)
        return [dict(r) for r in rows]


@router.post("/genel-mudur-vekili", status_code=201)
async def add_genel_mudur_vekili(body: GmVekilEkle, token: dict = Depends(require_ayar_editor)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        p = await conn.fetchval("SELECT id FROM personel WHERE id=$1 AND aktif=TRUE", body.personel_id)
        if not p:
            raise HTTPException(status_code=404, detail="Personel bulunamadı.")
        try:
            row = await conn.fetchrow(
                "INSERT INTO genel_mudur_vekili (personel_id) VALUES($1) RETURNING id",
                body.personel_id
            )
        except Exception:
            raise HTTPException(status_code=409, detail="Bu personel zaten Genel Müdür Vekili listesinde.")
    return {"id": row["id"]}


@router.delete("/genel-mudur-vekili/{bid}")
async def remove_genel_mudur_vekili(bid: int, token: dict = Depends(require_ayar_editor)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        exists = await conn.fetchval("SELECT id FROM genel_mudur_vekili WHERE id=$1", bid)
        if not exists:
            raise HTTPException(status_code=404, detail="Kayıt bulunamadı.")
        await conn.execute("DELETE FROM genel_mudur_vekili WHERE id=$1", bid)
    return {"ok": True}


@router.get("/gm-personel-havuzu")
async def get_gm_personel_havuzu(q: str = "", token: dict = Depends(require_ayar_editor)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        mevcut = await conn.fetch("SELECT personel_id FROM genel_mudur_vekili")
        mevcut_ids = [r["personel_id"] for r in mevcut]
        rows = await conn.fetch("""
            SELECT p.id, p.ad_soyad, p.unvan, p.bolum
            FROM personel p
            WHERE p.aktif = TRUE
              AND p.id != ALL($1::int[])
              AND ($2 = '' OR p.ad_soyad ILIKE $3)
            ORDER BY p.ad_soyad
            LIMIT 30
        """, mevcut_ids or [-1], q, f"%{q}%")
        return [dict(r) for r in rows]
