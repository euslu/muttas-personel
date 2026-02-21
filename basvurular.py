import os, csv, io, random, string
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Depends, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, JWTError

from db import get_pool

router = APIRouter(prefix="/basvurular", tags=["basvurular"])

JWT_SECRET    = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
security      = HTTPBearer()

VALID_DURUMS = {
    "beklemede", "islem_bekliyor", "odeme_islemde",
    "manuel_odeme", "onaylandi", "reddedildi", "dosya_yuklenenler"
}


def decode_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        return jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Geçersiz token.")


def gen_ref_no(length: int = 8) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


# ── Pydantic Models ─────────────────────────────────
class BasvuruCreate(BaseModel):
    tekne_id:       Optional[int]   = None
    tekne_adi:      str
    liman_id:       int
    iskele_no:      Optional[str]   = None
    basvuru_sahibi: Optional[str]   = None
    telefon:        Optional[str]   = None
    giris_tarihi:   date
    cikis_tarihi:   Optional[date]  = None
    durum:          str             = "beklemede"
    sigorta_bitis:  Optional[date]  = None
    notlar:         Optional[str]   = None
    uzunluk_m:      Optional[float] = None
    genislik_m:     Optional[float] = None
    tip:            Optional[str]   = None
    tutar:          Optional[float] = None
    odeme_durumu:   Optional[str]   = None


class BasvuruUpdate(BaseModel):
    tekne_adi:      Optional[str]   = None
    liman_id:       Optional[int]   = None
    iskele_no:      Optional[str]   = None
    basvuru_sahibi: Optional[str]   = None
    telefon:        Optional[str]   = None
    giris_tarihi:   Optional[date]  = None
    cikis_tarihi:   Optional[date]  = None
    durum:          Optional[str]   = None
    sigorta_bitis:  Optional[date]  = None
    notlar:         Optional[str]   = None
    uzunluk_m:      Optional[float] = None
    genislik_m:     Optional[float] = None
    tutar:          Optional[float] = None
    odeme_durumu:   Optional[str]   = None


class DurumUpdate(BaseModel):
    durum: str


class OdemeLinkiCreate(BaseModel):
    link: str


# ── Helpers ─────────────────────────────────────────
LIST_SQL = """
    SELECT
        b.id, b.ref_no, b.liman_id, b.tekne_id,
        b.iskele_no, b.basvuru_sahibi, b.telefon,
        b.giris_tarihi, b.cikis_tarihi, b.durum,
        b.sigorta_bitis, b.notlar, b.odeme_linki, b.odeme_linki_tarihi,
        b.olusturuldu,
        t.ad  AS tekne_adi,
        t.uzunluk_m, t.genislik_m, t.tip AS tekne_tipi,
        l.ad  AS liman_adi,
        f.tutar, f.toplam_tutar, f.fatura_no,
        f.durum AS odeme_durumu
    FROM baglamalar b
    LEFT JOIN tekneler t ON t.id = b.tekne_id
    LEFT JOIN limanlar l ON l.id = b.liman_id
    LEFT JOIN LATERAL (
        SELECT tutar, toplam_tutar, fatura_no, durum
        FROM   faturalar
        WHERE  baglama_id = b.id
        ORDER  BY id DESC LIMIT 1
    ) f ON TRUE
"""


def row_to_dict(r) -> dict:
    def fmt(v):
        if isinstance(v, (date, datetime)):
            return v.isoformat()
        return v

    return {k: fmt(v) for k, v in dict(r).items()}


def build_where(
    durum, odeme_durumu, tarih_baslangic, tarih_bitis, liman_id, search, params
):
    conds, idx = [], len(params) + 1

    if durum:
        conds.append(f"b.durum = ${idx}"); params.append(durum); idx += 1
    if odeme_durumu:
        conds.append(f"f.durum = ${idx}"); params.append(odeme_durumu); idx += 1
    if tarih_baslangic:
        conds.append(f"b.giris_tarihi >= ${idx}"); params.append(tarih_baslangic); idx += 1
    if tarih_bitis:
        conds.append(f"b.giris_tarihi <= ${idx}"); params.append(tarih_bitis); idx += 1
    if liman_id:
        conds.append(f"b.liman_id = ${idx}"); params.append(liman_id); idx += 1
    if search:
        like = f"%{search}%"
        conds.append(
            f"(t.ad ILIKE ${idx} OR b.ref_no ILIKE ${idx} OR b.basvuru_sahibi ILIKE ${idx})"
        )
        params.append(like); idx += 1

    where = ("WHERE " + " AND ".join(conds)) if conds else ""
    return where, idx


# ── Endpoints ────────────────────────────────────────

@router.get("/sigorta-uyarilari")
async def sigorta_uyarilari(token: dict = Depends(decode_token)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            LIST_SQL + """
            WHERE b.sigorta_bitis IS NOT NULL
              AND b.sigorta_bitis <= CURRENT_DATE + INTERVAL '30 days'
              AND b.sigorta_bitis >= CURRENT_DATE
            ORDER BY b.sigorta_bitis ASC
            LIMIT 100
            """
        )
    return [row_to_dict(r) for r in rows]


@router.get("/export/muhasebe")
async def export_muhasebe(
    durum:          Optional[str]  = Query(None),
    odeme_durumu:   Optional[str]  = Query(None),
    tarih_baslangic:Optional[date] = Query(None),
    tarih_bitis:    Optional[date] = Query(None),
    liman_id:       Optional[int]  = Query(None),
    token:          dict           = Depends(decode_token),
):
    pool   = await get_pool()
    params = []
    where, _ = build_where(durum, odeme_durumu, tarih_baslangic, tarih_bitis, liman_id, None, params)
    async with pool.acquire() as conn:
        rows = await conn.fetch(LIST_SQL + f" {where} ORDER BY b.olusturuldu DESC", *params)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Ref No", "Tekne Adı", "Liman", "Başvuru Sahibi", "Giriş Tarihi",
                     "Çıkış Tarihi", "Tutar", "KDV'li Tutar", "Ödeme Durumu", "Durum", "Fatura No"])
    for r in rows:
        d = row_to_dict(r)
        writer.writerow([
            d["ref_no"], d["tekne_adi"], d["liman_adi"], d["basvuru_sahibi"],
            d["giris_tarihi"], d["cikis_tarihi"],
            d["tutar"], d["toplam_tutar"], d["odeme_durumu"], d["durum"], d["fatura_no"]
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.read()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=muhasebe.csv"}
    )


@router.get("/export/kayitlar")
async def export_kayitlar(
    durum:          Optional[str]  = Query(None),
    odeme_durumu:   Optional[str]  = Query(None),
    tarih_baslangic:Optional[date] = Query(None),
    tarih_bitis:    Optional[date] = Query(None),
    liman_id:       Optional[int]  = Query(None),
    token:          dict           = Depends(decode_token),
):
    pool   = await get_pool()
    params = []
    where, _ = build_where(durum, odeme_durumu, tarih_baslangic, tarih_bitis, liman_id, None, params)
    async with pool.acquire() as conn:
        rows = await conn.fetch(LIST_SQL + f" {where} ORDER BY b.olusturuldu DESC", *params)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Ref No", "Tekne Adı", "Tekne Tipi", "Liman", "Bağlama Yeri",
                     "Başvuru Sahibi", "Telefon", "Giriş Tarihi", "Çıkış Tarihi",
                     "Boy (m)", "En (m)", "Durum", "Sigorta Bitiş", "Notlar"])
    for r in rows:
        d = row_to_dict(r)
        writer.writerow([
            d["ref_no"], d["tekne_adi"], d["tekne_tipi"], d["liman_adi"], d["iskele_no"],
            d["basvuru_sahibi"], d["telefon"], d["giris_tarihi"], d["cikis_tarihi"],
            d["uzunluk_m"], d["genislik_m"], d["durum"], d["sigorta_bitis"], d["notlar"]
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.read()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=kayitlar.csv"}
    )


@router.get("")
async def list_basvurular(
    durum:           Optional[str]  = Query(None),
    odeme_durumu:    Optional[str]  = Query(None),
    tarih_baslangic: Optional[date] = Query(None),
    tarih_bitis:     Optional[date] = Query(None),
    liman_id:        Optional[int]  = Query(None),
    search:          Optional[str]  = Query(None),
    page:            int            = Query(1, ge=1),
    per_page:        int            = Query(25, ge=1, le=100),
    token:           dict           = Depends(decode_token),
):
    pool   = await get_pool()
    params = []
    where, idx = build_where(durum, odeme_durumu, tarih_baslangic, tarih_bitis, liman_id, search, params)
    offset = (page - 1) * per_page

    count_sql = f"""
        SELECT COUNT(*) FROM baglamalar b
        LEFT JOIN tekneler t ON t.id = b.tekne_id
        LEFT JOIN LATERAL (
            SELECT durum FROM faturalar WHERE baglama_id = b.id ORDER BY id DESC LIMIT 1
        ) f ON TRUE
        {where}
    """

    async with pool.acquire() as conn:
        total = await conn.fetchval(count_sql, *params)
        rows  = await conn.fetch(
            LIST_SQL + f" {where} ORDER BY b.olusturuldu DESC LIMIT ${idx} OFFSET ${idx+1}",
            *params, per_page, offset
        )

    return {
        "toplam":   total,
        "sayfa":    page,
        "per_page": per_page,
        "kayitlar": [row_to_dict(r) for r in rows],
    }


@router.get("/{basvuru_id}")
async def get_basvuru(basvuru_id: int, token: dict = Depends(decode_token)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(LIST_SQL + " WHERE b.id = $1", basvuru_id)
    if not row:
        raise HTTPException(status_code=404, detail="Başvuru bulunamadı.")
    return row_to_dict(row)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_basvuru(body: BasvuruCreate, token: dict = Depends(decode_token)):
    user_id = int(token.get("sub"))
    pool    = await get_pool()

    async with pool.acquire() as conn:
        # Ref no üret (unique olmalı)
        for _ in range(10):
            ref_no = gen_ref_no()
            exists = await conn.fetchval("SELECT id FROM baglamalar WHERE ref_no = $1", ref_no)
            if not exists:
                break

        # Tekne bul veya oluştur
        tekne_id = body.tekne_id
        if not tekne_id:
            t = await conn.fetchrow("SELECT id FROM tekneler WHERE LOWER(ad) = LOWER($1) LIMIT 1", body.tekne_adi)
            if t:
                tekne_id = t["id"]
            else:
                tekne_id = await conn.fetchval(
                    "INSERT INTO tekneler (ad, tip, uzunluk_m, genislik_m) VALUES ($1,$2,$3,$4) RETURNING id",
                    body.tekne_adi, body.tip, body.uzunluk_m, body.genislik_m
                )
        else:
            if body.uzunluk_m or body.genislik_m or body.tip:
                await conn.execute(
                    "UPDATE tekneler SET uzunluk_m=COALESCE($1,uzunluk_m), genislik_m=COALESCE($2,genislik_m), tip=COALESCE($3,tip) WHERE id=$4",
                    body.uzunluk_m, body.genislik_m, body.tip, tekne_id
                )

        giris = datetime(body.giris_tarihi.year, body.giris_tarihi.month, body.giris_tarihi.day)
        cikis = datetime(body.cikis_tarihi.year, body.cikis_tarihi.month, body.cikis_tarihi.day) if body.cikis_tarihi else None

        row = await conn.fetchrow(
            """
            INSERT INTO baglamalar
                (liman_id, tekne_id, kullanici_id, giris_tarihi, cikis_tarihi,
                 iskele_no, durum, notlar, ref_no, basvuru_sahibi, telefon, sigorta_bitis)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
            RETURNING id
            """,
            body.liman_id, tekne_id, user_id, giris, cikis,
            body.iskele_no, body.durum, body.notlar,
            ref_no, body.basvuru_sahibi, body.telefon, body.sigorta_bitis
        )
        baglama_id = row["id"]

        if body.tutar and body.tutar > 0:
            kdv      = 20.0
            toplam   = round(body.tutar * 1.20, 2)
            fatura_no = f"FAT-{ref_no}"
            odeme_dur = body.odeme_durumu or "beklemede"
            await conn.execute(
                """
                INSERT INTO faturalar (baglama_id, kullanici_id, fatura_no, tutar, kdv_orani, toplam_tutar, durum)
                VALUES ($1,$2,$3,$4,$5,$6,$7)
                ON CONFLICT (fatura_no) DO NOTHING
                """,
                baglama_id, user_id, fatura_no, body.tutar, kdv, toplam, odeme_dur
            )

        result = await conn.fetchrow(LIST_SQL + " WHERE b.id = $1", baglama_id)
    return row_to_dict(result)


@router.put("/{basvuru_id}")
async def update_basvuru(basvuru_id: int, body: BasvuruUpdate, token: dict = Depends(decode_token)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow("SELECT * FROM baglamalar WHERE id = $1", basvuru_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Başvuru bulunamadı.")

        giris = datetime(body.giris_tarihi.year, body.giris_tarihi.month, body.giris_tarihi.day) if body.giris_tarihi else None
        cikis = datetime(body.cikis_tarihi.year, body.cikis_tarihi.month, body.cikis_tarihi.day) if body.cikis_tarihi else None

        if body.tekne_adi:
            t = await conn.fetchrow("SELECT id FROM tekneler WHERE LOWER(ad) = LOWER($1) LIMIT 1", body.tekne_adi)
            if t:
                tekne_id = t["id"]
            else:
                tekne_id = await conn.fetchval(
                    "INSERT INTO tekneler (ad, tip, uzunluk_m, genislik_m) VALUES ($1,$2,$3,$4) RETURNING id",
                    body.tekne_adi, body.tip, body.uzunluk_m, body.genislik_m
                )
            await conn.execute("UPDATE baglamalar SET tekne_id=$1 WHERE id=$2", tekne_id, basvuru_id)

        await conn.execute(
            """
            UPDATE baglamalar SET
                liman_id       = COALESCE($1, liman_id),
                iskele_no      = COALESCE($2, iskele_no),
                basvuru_sahibi = COALESCE($3, basvuru_sahibi),
                telefon        = COALESCE($4, telefon),
                giris_tarihi   = COALESCE($5, giris_tarihi),
                cikis_tarihi   = COALESCE($6, cikis_tarihi),
                durum          = COALESCE($7, durum),
                sigorta_bitis  = COALESCE($8, sigorta_bitis),
                notlar         = COALESCE($9, notlar)
            WHERE id = $10
            """,
            body.liman_id, body.iskele_no, body.basvuru_sahibi, body.telefon,
            giris, cikis, body.durum, body.sigorta_bitis, body.notlar, basvuru_id
        )

        if body.tutar is not None:
            fatura = await conn.fetchrow("SELECT id FROM faturalar WHERE baglama_id=$1 ORDER BY id DESC LIMIT 1", basvuru_id)
            kdv    = 20.0
            toplam = round(body.tutar * 1.20, 2)
            if fatura:
                await conn.execute(
                    "UPDATE faturalar SET tutar=$1, toplam_tutar=$2, durum=COALESCE($3,durum) WHERE id=$4",
                    body.tutar, toplam, body.odeme_durumu, fatura["id"]
                )
            else:
                ref_no    = existing["ref_no"] or gen_ref_no()
                fatura_no = f"FAT-{ref_no}-UPD"
                await conn.execute(
                    """
                    INSERT INTO faturalar (baglama_id, kullanici_id, fatura_no, tutar, kdv_orani, toplam_tutar, durum)
                    VALUES ($1,1,$2,$3,$4,$5,$6) ON CONFLICT DO NOTHING
                    """,
                    basvuru_id, fatura_no, body.tutar, kdv, toplam, body.odeme_durumu or "beklemede"
                )

        result = await conn.fetchrow(LIST_SQL + " WHERE b.id = $1", basvuru_id)
    return row_to_dict(result)


@router.put("/{basvuru_id}/durum")
async def update_durum(basvuru_id: int, body: DurumUpdate, token: dict = Depends(decode_token)):
    if body.durum not in VALID_DURUMS:
        raise HTTPException(status_code=422, detail=f"Geçersiz durum: {body.durum}")
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE baglamalar SET durum=$1 WHERE id=$2", body.durum, basvuru_id
        )
        if result == "UPDATE 0":
            raise HTTPException(status_code=404, detail="Başvuru bulunamadı.")
        row = await conn.fetchrow(LIST_SQL + " WHERE b.id = $1", basvuru_id)
    return row_to_dict(row)


@router.post("/{basvuru_id}/odeme-linki")
async def set_odeme_linki(basvuru_id: int, body: OdemeLinkiCreate, token: dict = Depends(decode_token)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE baglamalar SET odeme_linki=$1, odeme_linki_tarihi=NOW() WHERE id=$2",
            body.link, basvuru_id
        )
        if result == "UPDATE 0":
            raise HTTPException(status_code=404, detail="Başvuru bulunamadı.")
        row = await conn.fetchrow("SELECT odeme_linki, odeme_linki_tarihi FROM baglamalar WHERE id=$1", basvuru_id)
    return {"odeme_linki": row["odeme_linki"], "odeme_linki_tarihi": row["odeme_linki_tarihi"].isoformat() if row["odeme_linki_tarihi"] else None}


@router.delete("/{basvuru_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_basvuru(basvuru_id: int, token: dict = Depends(decode_token)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM baglamalar WHERE id=$1", basvuru_id)
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Başvuru bulunamadı.")
