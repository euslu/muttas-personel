from typing import Optional
from datetime import date, datetime

from fastapi import APIRouter, HTTPException, Query, Depends, Request
from pydantic import BaseModel

from db import get_pool
from permissions import decode_token, require_ik_editor, require_izin_editor, IK_EDITORS, IZIN_EDITORS, GM_EDITORS, YK_EDITORS
from vekalet import get_vekalet_rolleri

router = APIRouter(prefix="/izinler", tags=["izinler"])

async def get_izin_turleri_db() -> list:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT kod FROM izin_turleri WHERE aktif = TRUE ORDER BY sira, ad")
        return [r["kod"] for r in rows]

DURUMLAR = ["beklemede", "ik_onayladi", "mudur_onayladi", "onaylandi", "reddedildi", "tamamlandi"]

DURUM_ACIKLAMA = {
    "beklemede":        "İzin talebi oluşturuldu",
    "ik_onayladi":      "İK/İdari İşler onayı verildi",
    "mudur_onayladi":   "Genel Müdür onayı verildi",
    "onaylandi":        "YK onayı verildi (UYGUNDUR)",
    "reddedildi":       "İzin talebi reddedildi",
    "tamamlandi":       "İzin tamamlandı, göreve başlandı",
}


async def izin_log_yaz(conn, izin_id, personel_id, personel_ad, onceki_durum, yeni_durum, token, ip=None, aciklama=None, ek_bilgi=None):
    import json
    islem_yapan_id  = int(token.get("sub", 0)) if token else None
    islem_yapan_ad  = ((token.get("ad", "") + " " + token.get("soyad", "")).strip()) if token else None
    islem_yapan_rol = token.get("rol", "") if token else None
    if not aciklama:
        aciklama = DURUM_ACIKLAMA.get(yeni_durum, f"Durum değişikliği: {yeni_durum}")
    try:
        await conn.execute("""
            INSERT INTO izin_log (izin_id, personel_id, personel_ad, onceki_durum, yeni_durum,
                islem_yapan_id, islem_yapan_ad, islem_yapan_rol, ip_adresi, aciklama, ek_bilgi)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
        """, izin_id, personel_id, personel_ad, onceki_durum, yeni_durum,
             islem_yapan_id, islem_yapan_ad, islem_yapan_rol, ip,
             aciklama, json.dumps(ek_bilgi) if ek_bilgi else None)
    except Exception:
        pass


class IzinCreate(BaseModel):
    personel_id:      int
    talep_tarihi:     Optional[date] = None
    izin_turu:        str
    baslangic:        date
    bitis:            date
    gun_sayisi:       int
    saat_sayisi:      Optional[int] = None
    kullanilabilir_gun: Optional[int] = None
    vekil_ad_soyad:   Optional[str] = None
    izin_adresi:      Optional[str] = None
    aciklama:         Optional[str] = None
    notlar:           Optional[str] = None
    imza:             Optional[str] = None
    ks_onaylayan:     Optional[str] = None


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

        # KS kullanıcısı veya Müdür: kendi atandığı VEYA henüz birim sorumlusu atanmamış izinleri görebilir
        if token.get("rol") in {"koordinasyon_sorumlusu", "mudur"}:
            ks_row = await conn.fetchrow(
                "SELECT p.ad_soyad FROM personel p JOIN kullanicilar k ON LOWER(REPLACE(p.tc_kimlik,' ','')) = k.email WHERE k.email = $1",
                token.get("email", "")
            )
            ks_adi = ks_row["ad_soyad"] if ks_row else (token.get("ad", "") + " " + token.get("soyad", "")).strip()
            params.append(ks_adi)
            wheres.append(f"(UPPER(i.ks_onaylayan) = UPPER(${len(params)}) OR i.ks_onaylayan IS NULL OR i.ks_onaylayan = '')")

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


@router.get("/hesapla-kalan/{personel_id}")
async def hesapla_kalan_izin(personel_id: int, token: dict = Depends(decode_token)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        p = await conn.fetchrow(
            "SELECT kalan_izin, toplam_izin_hak FROM personel WHERE id = $1 AND aktif = TRUE",
            personel_id
        )
        if not p:
            raise HTTPException(status_code=404, detail="Personel bulunamadı.")

        toplam_hak  = p["toplam_izin_hak"] or 0
        kalan_pdks  = p["kalan_izin"] or 0

        # Reddedilmeyenler arasından yıllık izin kullanımı
        yillik_kullanilan = await conn.fetchval("""
            SELECT COALESCE(SUM(gun_sayisi), 0)
            FROM izinler
            WHERE personel_id = $1
              AND izin_turu = 'yillik'
              AND durum NOT IN ('reddedildi')
        """, personel_id) or 0

        # Saatlik izin toplamı (saat cinsinden); eski kayıtlarda 8 saat varsay
        saatlik_toplam_saat = await conn.fetchval("""
            SELECT COALESCE(SUM(COALESCE(saat_sayisi, 8)), 0)
            FROM izinler
            WHERE personel_id = $1
              AND izin_turu = 'saatlik'
              AND durum NOT IN ('reddedildi')
        """, personel_id) or 0

        import math
        saatlik_gun_karsiligi = math.ceil(saatlik_toplam_saat / 8)
        efektif_kalan = max(0, kalan_pdks - saatlik_gun_karsiligi)

        return {
            "toplam_hak":            toplam_hak,
            "kalan_pdks":            kalan_pdks,
            "yillik_kullanilan":     int(yillik_kullanilan),
            "saatlik_toplam_saat":   int(saatlik_toplam_saat),
            "saatlik_gun_karsiligi": saatlik_gun_karsiligi,
            "efektif_kalan":         efektif_kalan,
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
        if token.get("rol") in {"koordinasyon_sorumlusu", "mudur"}:
            ks_row2 = await conn.fetchrow(
                "SELECT p.ad_soyad FROM personel p JOIN kullanicilar k ON LOWER(REPLACE(p.tc_kimlik,' ','')) = k.email WHERE k.email = $1",
                token.get("email", "")
            )
            ks_adi = ks_row2["ad_soyad"] if ks_row2 else (token.get("ad", "") + " " + token.get("soyad", "")).strip()
            existing_ks = (r["ks_onaylayan"] or "").strip()
            if existing_ks and existing_ks.upper() != ks_adi.upper():
                raise HTTPException(status_code=403, detail="Bu izin kaydına erişim yetkiniz yok.")
        return row_to_dict(r)


@router.post("", status_code=201)
async def create_izin(body: IzinCreate, request: Request, token: dict = Depends(require_izin_editor)):
    izin_turleri = await get_izin_turleri_db()
    if body.izin_turu not in izin_turleri:
        raise HTTPException(status_code=400, detail=f"Geçersiz izin türü. Kabul edilenler: {izin_turleri}")

    pool = await get_pool()
    async with pool.acquire() as conn:
        prs = await conn.fetchrow("SELECT id, ad_soyad FROM personel WHERE id = $1 AND aktif = TRUE", body.personel_id)
        if not prs:
            raise HTTPException(status_code=404, detail="Personel bulunamadı.")

        talep = body.talep_tarihi or date.today()
        row = await conn.fetchrow("""
            INSERT INTO izinler (
                personel_id, talep_tarihi, izin_turu, baslangic, bitis,
                gun_sayisi, saat_sayisi, kullanilabilir_gun, vekil_ad_soyad, izin_adresi, aciklama, notlar, imza, ks_onaylayan
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
            RETURNING id
        """,
            body.personel_id, talep, body.izin_turu, body.baslangic, body.bitis,
            body.gun_sayisi, body.saat_sayisi, body.kullanilabilir_gun, body.vekil_ad_soyad,
            body.izin_adresi, body.aciklama, body.notlar, body.imza, body.ks_onaylayan,
        )
        ip = request.headers.get("x-forwarded-for", request.client.host if request.client else None)
        await izin_log_yaz(conn, row["id"], body.personel_id, prs["ad_soyad"],
            None, "beklemede", token, ip,
            f"İzin talebi oluşturuldu: {body.izin_turu}, {body.baslangic} - {body.bitis}, {body.gun_sayisi} gün")
        return {"id": row["id"]}


@router.put("/{iid}")
async def update_izin(iid: int, body: IzinCreate, token: dict = Depends(require_izin_editor)):
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
                saat_sayisi = $6, kullanilabilir_gun = $7, vekil_ad_soyad = $8, izin_adresi = $9,
                aciklama = $10, notlar = $11, talep_tarihi = $12, imza = COALESCE($13, imza),
                ks_onaylayan = $14
            WHERE id = $1
        """,
            iid, body.izin_turu, body.baslangic, body.bitis, body.gun_sayisi,
            body.saat_sayisi, body.kullanilabilir_gun, body.vekil_ad_soyad, body.izin_adresi,
            body.aciklama, body.notlar, body.talep_tarihi or date.today(), body.imza,
            body.ks_onaylayan,
        )
        return {"ok": True}


ONAY_YETKI = {
    "ik_onayladi":     IK_EDITORS,
    "mudur_onayladi":  GM_EDITORS,
    "onaylandi":       YK_EDITORS,
    "reddedildi":      IK_EDITORS | GM_EDITORS | YK_EDITORS,
    "tamamlandi":      GM_EDITORS,
}


@router.put("/{iid}/onay")
async def onay_izin(iid: int, body: IzinOnay, request: Request, token: dict = Depends(decode_token)):
    if body.durum not in DURUMLAR:
        raise HTTPException(status_code=400, detail=f"Geçersiz durum. Kabul edilenler: {DURUMLAR}")

    rol = token.get("rol", "")
    kullanici_id = int(token.get("sub", 0))
    yetkili_roller = ONAY_YETKI.get(body.durum, set())

    yetki_var = rol in yetkili_roller
    vekalet_rolleri = set()
    if not yetki_var and kullanici_id:
        vekalet_rolleri = await get_vekalet_rolleri(kullanici_id)
        yetki_var = bool(vekalet_rolleri & yetkili_roller)

    if not yetki_var:
        durum_label = {
            "ik_onayladi": "İK onayını sadece İK yöneticisi verebilir.",
            "mudur_onayladi": "Genel Müdür onayını sadece Genel Müdür verebilir.",
            "onaylandi": "YK onayını sadece Yönetim Kurulu üyesi verebilir.",
            "tamamlandi": "Dönüş imzasını sadece Genel Müdür atabilir.",
        }
        raise HTTPException(status_code=403, detail=durum_label.get(body.durum, "Bu onay için yetkiniz yok."))

    ONAY_SIRASI = {
        "ik_onayladi":     {"beklemede"},
        "mudur_onayladi":  {"ik_onayladi"},
        "onaylandi":       {"mudur_onayladi"},
        "tamamlandi":      {"onaylandi", "mudur_onayladi"},
        "reddedildi":      {"beklemede", "ik_onayladi", "mudur_onayladi"},
    }

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT i.durum, i.personel_id, i.ks_onaylayan, i.ks_onay_tarihi, i.ik_onay_tarihi, p.ad_soyad
            FROM izinler i JOIN personel p ON p.id = i.personel_id
            WHERE i.id = $1
        """, iid)
        if not row:
            raise HTTPException(status_code=404, detail="İzin kaydı bulunamadı.")

        mevcut_durum = row["durum"]
        gereken = ONAY_SIRASI.get(body.durum)
        if gereken and mevcut_durum not in gereken:
            sira_mesaj = {
                "ik_onayladi":    "İK onayı yalnızca 'Beklemede' durumundaki izinlere verilebilir.",
                "mudur_onayladi": "Genel Müdür onayı için önce İK onayı gereklidir.",
                "onaylandi":      "YK onayı için önce Genel Müdür onayı gereklidir.",
                "tamamlandi":     "Tamamlama için önce en az Genel Müdür onayı gereklidir.",
                "reddedildi":     "Bu durumdaki izin reddedilemez.",
            }
            raise HTTPException(status_code=400, detail=sira_mesaj.get(body.durum, "Onay sırası uygun değil."))

        # KS onayı zorunluluğu: ks_onaylayan atanmışsa İK imzalamadan önce KS onayı gerekli
        if body.durum == "ik_onayladi" and row["ks_onaylayan"] and not row["ks_onay_tarihi"]:
            raise HTTPException(status_code=400, detail="İK onayı için önce Koordinasyon Sorumlusu onayı gereklidir.")

        # İK onayı zorunluluğu: Genel Müdür imzalamadan önce İK onayı gerekli
        if body.durum == "mudur_onayladi" and not row["ik_onay_tarihi"]:
            raise HTTPException(status_code=400, detail="Genel Müdür onayı için önce İK onayı gereklidir.")

        today = date.today()
        extra_sets = ""
        extra_vals = []

        now_str = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

        ad_soyad = (token.get("ad", "") + " " + token.get("soyad", "")).strip() or body.onaylayan or ""
        onaylayan_ad = ad_soyad + " (V)" if vekalet_rolleri & yetkili_roller and rol not in yetkili_roller else ad_soyad

        if body.durum == "ik_onayladi":
            extra_sets = ", ik_onay_tarihi = $4, ik_onaylayan = $5, ik_imza = $6"
            extra_vals = [today, onaylayan_ad, now_str]
        elif body.durum == "mudur_onayladi":
            extra_sets = ", mudur_onay_tarihi = $4, mudur_imza = $5, mudur_onaylayan = $6"
            extra_vals = [today, now_str, onaylayan_ad]
        elif body.durum == "onaylandi":
            extra_sets = ", yk_onay_tarihi = $4, yk_imza = $5, yk_onaylayan = $6"
            extra_vals = [today, now_str, onaylayan_ad]
        elif body.durum == "tamamlandi":
            extra_sets = ", gorev_baslama = $4"
            extra_vals = [today]

        base_params = [iid, body.durum, body.notlar]
        await conn.execute(
            f"UPDATE izinler SET durum = $2, notlar = COALESCE($3, notlar){extra_sets} WHERE id = $1",
            *base_params, *extra_vals,
        )

        ip = request.headers.get("x-forwarded-for", request.client.host if request.client else None)
        personel_id = row["personel_id"]
        personel_ad = row["ad_soyad"]
        await izin_log_yaz(conn, iid, personel_id, personel_ad, mevcut_durum, body.durum, token, ip)

        if body.durum == "tamamlandi":
            kullanici = await conn.fetchrow(
                "SELECT id FROM kullanicilar WHERE TRIM(CONCAT(ad, ' ', soyad)) = $1 AND aktif = true",
                personel_ad.strip()
            )
            if kullanici:
                await conn.execute(
                    "UPDATE vekaletler SET aktif = false WHERE veren_kullanici_id = $1 AND aktif = true",
                    kullanici["id"]
                )

        return {"ok": True}


@router.put("/{iid}/ks-onayla")
async def ks_onayla_izin(iid: int, token: dict = Depends(decode_token)):
    if token.get("rol") not in {"koordinasyon_sorumlusu", "mudur"}:
        raise HTTPException(status_code=403, detail="Bu işlem sadece Koordinasyon Sorumlusu veya Müdür tarafından yapılabilir.")

    pool = await get_pool()
    async with pool.acquire() as conn:
        ks_row = await conn.fetchrow(
            "SELECT p.ad_soyad FROM personel p JOIN kullanicilar k ON LOWER(REPLACE(p.tc_kimlik,' ','')) = k.email WHERE k.email = $1",
            token.get("email", "")
        )
        ks_adi = ks_row["ad_soyad"] if ks_row else (token.get("ad", "") + " " + token.get("soyad", "")).strip()

        row = await conn.fetchrow("SELECT id, ks_onaylayan FROM izinler WHERE id = $1", iid)
        if not row:
            raise HTTPException(status_code=404, detail="İzin kaydı bulunamadı.")
        existing_ks = (row["ks_onaylayan"] or "").strip()
        if existing_ks and existing_ks.upper() != ks_adi.upper():
            raise HTTPException(status_code=403, detail="Bu izin size atanmamış.")

        now_str = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        today = date.today()
        await conn.execute(
            "UPDATE izinler SET ks_onay_tarihi = $2, ks_imza = $3, ks_onaylayan = $4 WHERE id = $1",
            iid, today, now_str, ks_adi
        )
    return {"ok": True}


@router.delete("/{iid}")
async def delete_izin(iid: int, token: dict = Depends(require_ik_editor)):
    pool = await get_pool()
    rol = token.get("rol", "")
    async with pool.acquire() as conn:
        if rol == "admin":
            exists = await conn.fetchval("SELECT id FROM izinler WHERE id = $1", iid)
            if not exists:
                raise HTTPException(status_code=404, detail="İzin kaydı bulunamadı.")
        else:
            exists = await conn.fetchval(
                "SELECT id FROM izinler WHERE id = $1 AND durum = 'beklemede'", iid
            )
            if not exists:
                raise HTTPException(status_code=400, detail="Sadece beklemede olan izinler silinebilir.")
        await conn.execute("DELETE FROM izinler WHERE id = $1", iid)
        return {"ok": True}


@router.get("/log/listele")
async def izin_log_listele(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    izin_id: Optional[int] = None,
    personel_ad: Optional[str] = None,
    durum: Optional[str] = None,
    baslangic: Optional[str] = None,
    bitis: Optional[str] = None,
    token: dict = Depends(decode_token),
):
    rol = token.get("rol", "")
    if rol not in ("admin", "ik_admin", "genel_mudur"):
        raise HTTPException(status_code=403, detail="Log görüntüleme yetkiniz yok.")

    pool = await get_pool()
    async with pool.acquire() as conn:
        where = []
        vals = []
        idx = 1
        if izin_id:
            where.append(f"l.izin_id = ${idx}")
            vals.append(izin_id)
            idx += 1
        if personel_ad:
            where.append(f"l.personel_ad ILIKE ${idx}")
            vals.append(f"%{personel_ad}%")
            idx += 1
        if durum:
            where.append(f"l.yeni_durum = ${idx}")
            vals.append(durum)
            idx += 1
        if baslangic:
            where.append(f"l.islem_zamani >= ${idx}::timestamp")
            vals.append(baslangic)
            idx += 1
        if bitis:
            where.append(f"l.islem_zamani <= ${idx}::timestamp + interval '1 day'")
            vals.append(bitis)
            idx += 1
        w = ("WHERE " + " AND ".join(where)) if where else ""

        total = await conn.fetchval(f"SELECT COUNT(*) FROM izin_log l {w}", *vals)
        offset = (page - 1) * per_page
        rows = await conn.fetch(f"""
            SELECT l.* FROM izin_log l {w}
            ORDER BY l.islem_zamani DESC
            LIMIT {per_page} OFFSET {offset}
        """, *vals)

        def fmt_ts(ts):
            return ts.strftime("%d.%m.%Y %H:%M:%S") if ts else None

        return {
            "total": total,
            "page": page,
            "per_page": per_page,
            "data": [
                {
                    "id": r["id"],
                    "izin_id": r["izin_id"],
                    "personel_id": r["personel_id"],
                    "personel_ad": r["personel_ad"],
                    "islem_zamani": fmt_ts(r["islem_zamani"]),
                    "onceki_durum": r["onceki_durum"],
                    "yeni_durum": r["yeni_durum"],
                    "islem_yapan_id": r["islem_yapan_id"],
                    "islem_yapan_ad": r["islem_yapan_ad"],
                    "islem_yapan_rol": r["islem_yapan_rol"],
                    "ip_adresi": r["ip_adresi"],
                    "aciklama": r["aciklama"],
                }
                for r in rows
            ],
        }


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
