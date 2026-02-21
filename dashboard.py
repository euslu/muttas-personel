import os
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from db import get_pool

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

JWT_SECRET    = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
security      = HTTPBearer()


def decode_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        return jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Geçersiz token.")


def liman_where(liman_id: Optional[int], alias: str = "b") -> tuple[str, list]:
    if liman_id:
        return f"{alias}.liman_id = $1", [liman_id]
    return "TRUE", []


@router.get("/ozet")
async def get_ozet(
    liman_id: Optional[int] = Query(None),
    token: dict = Depends(decode_token),
):
    pool = await get_pool()
    async with pool.acquire() as conn:

        liman_cond = "b.liman_id = $1" if liman_id else "TRUE"
        liman_cond_g = "g.liman_id = $1" if liman_id else "TRUE"
        liman_cond_f = "bag.liman_id = $1" if liman_id else "TRUE"
        params = [liman_id] if liman_id else []
        p1 = "$1" if liman_id else "NULL"

        aktif_baglamalar = await conn.fetchval(f"""
            SELECT COUNT(*) FROM baglamalar b
            WHERE {liman_cond}
              AND b.giris_tarihi::date <= CURRENT_DATE
              AND (b.cikis_tarihi IS NULL OR b.cikis_tarihi::date >= CURRENT_DATE)
        """, *params)

        # Import günü (2026-02-21) hariç, sadece onaylanmamış başvurular
        BEKLEYEN = "('beklemede','islem_bekliyor','odeme_islemde','manuel_odeme','dosya_yuklenenler')"
        IMPORT_CUTOFF = "'2026-02-21'"

        basvuru_bugun = await conn.fetchval(f"""
            SELECT COUNT(*) FROM baglamalar b
            WHERE {liman_cond}
              AND b.olusturuldu::date = CURRENT_DATE
              AND b.olusturuldu::date > {IMPORT_CUTOFF}
              AND b.durum IN {BEKLEYEN}
        """, *params)

        basvuru_bu_hafta = await conn.fetchval(f"""
            SELECT COUNT(*) FROM baglamalar b
            WHERE {liman_cond}
              AND b.olusturuldu >= DATE_TRUNC('week', CURRENT_DATE)
              AND b.olusturuldu::date > {IMPORT_CUTOFF}
              AND b.durum IN {BEKLEYEN}
        """, *params)

        basvuru_bu_ay = await conn.fetchval(f"""
            SELECT COUNT(*) FROM baglamalar b
            WHERE {liman_cond}
              AND b.olusturuldu >= DATE_TRUNC('month', CURRENT_DATE)
              AND b.olusturuldu::date > {IMPORT_CUTOFF}
              AND b.durum IN {BEKLEYEN}
        """, *params)

        bekleyen_basvuru = await conn.fetchval(f"""
            SELECT COUNT(*) FROM baglamalar b
            WHERE {liman_cond}
              AND b.durum IN ('beklemede','islem_bekliyor','odeme_islemde','manuel_odeme','dosya_yuklenenler')
        """, *params)

        kayitli_tekne = await conn.fetchval(
            "SELECT COUNT(*) FROM tekneler WHERE aktif = TRUE"
        )

        aylik_tahsilat = await conn.fetchval(f"""
            SELECT COALESCE(SUM(f.toplam_tutar), 0)
            FROM   faturalar f
            JOIN   baglamalar bag ON bag.id = f.baglama_id
            WHERE  {liman_cond_f}
              AND  f.durum = 'odendi'
              AND  DATE_TRUNC('month', COALESCE(f.odeme_tarihi, f.olusturuldu))
                   = DATE_TRUNC('month', CURRENT_DATE)
        """, *params)

        son_hareketler_rows = await conn.fetch(f"""
            SELECT g.tekne_adi, g.hareket_tipi, g.bolge,
                   g.tarih, g.saat
            FROM   gunluk_kayitlar g
            WHERE  {liman_cond_g}
            ORDER  BY g.tarih DESC, g.saat DESC
            LIMIT  10
        """, *params)

        sigorta_uyarilari = await conn.fetchval(f"""
            SELECT COUNT(*) FROM baglamalar b
            WHERE  {liman_cond}
              AND  b.sigorta_bitis IS NOT NULL
              AND  b.sigorta_bitis >= CURRENT_DATE
              AND  b.sigorta_bitis <= CURRENT_DATE + INTERVAL '30 days'
        """, *params)

        bekleyen_odeme = await conn.fetchval(f"""
            SELECT COUNT(DISTINCT b.id) FROM baglamalar b
            JOIN   faturalar f ON f.baglama_id = b.id
            WHERE  {liman_cond}
              AND  f.durum = 'beklemede'
        """, *params)

    def fmt_time(v):
        if isinstance(v, (date, datetime)):
            return v.isoformat()
        return str(v) if v is not None else None

    son_hareketler = [
        {
            "tekne_adi":    r["tekne_adi"],
            "hareket_tipi": r["hareket_tipi"],
            "bolge":        r["bolge"],
            "tarih":        fmt_time(r["tarih"]),
            "saat":         fmt_time(r["saat"]),
        }
        for r in son_hareketler_rows
    ]

    return {
        "aktif_baglamalar":  int(aktif_baglamalar),
        "bekleyen_basvuru":  int(bekleyen_basvuru),
        "basvuru_bugun":     int(basvuru_bugun),
        "basvuru_bu_hafta":  int(basvuru_bu_hafta),
        "basvuru_bu_ay":     int(basvuru_bu_ay),
        "kayitli_tekne":     int(kayitli_tekne),
        "aylik_tahsilat":    float(aylik_tahsilat),
        "son_hareketler":    son_hareketler,
        "sigorta_uyarilari": int(sigorta_uyarilari),
        "bekleyen_odeme":    int(bekleyen_odeme),
    }


@router.get("/gunluk-trafik")
async def get_gunluk_trafik(
    liman_id: Optional[int] = Query(None),
    gun:      int           = Query(30, ge=1, le=365),
    token:    dict          = Depends(decode_token),
):
    pool = await get_pool()
    async with pool.acquire() as conn:

        liman_cond = "liman_id = $1" if liman_id else "TRUE"
        params = [liman_id] if liman_id else []
        gun_param = f"${len(params)+1}"
        params.append(gun)

        rows = await conn.fetch(f"""
            SELECT
                tarih,
                COUNT(*) FILTER (WHERE LOWER(hareket_tipi) IN ('giris', 'giriş'))  AS giris_sayisi,
                COUNT(*) FILTER (WHERE LOWER(hareket_tipi) IN ('cikis', 'çıkış')) AS cikis_sayisi
            FROM   gunluk_kayitlar
            WHERE  {liman_cond}
              AND  tarih >= CURRENT_DATE - ({gun_param}::int - 1)
              AND  tarih <= CURRENT_DATE
            GROUP  BY tarih
            ORDER  BY tarih ASC
        """, *params)

    return {
        "gunler": [
            {
                "tarih":        r["tarih"].isoformat(),
                "giris_sayisi": int(r["giris_sayisi"]),
                "cikis_sayisi": int(r["cikis_sayisi"]),
            }
            for r in rows
        ]
    }
