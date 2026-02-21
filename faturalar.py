import os, csv, io, random, string, json
from datetime import date, datetime
from typing import Optional
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Query, Depends, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, JWTError

from db import get_pool

router = APIRouter(prefix="/faturalar", tags=["faturalar"])

JWT_SECRET    = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
security      = HTTPBearer()

DAMGA_ORANI = Decimal("0.00948")   # %0,948


def decode_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        return jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Geçersiz token.")


def gen_fatura_no() -> str:
    return "FAT-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=9))


# ── Pydantic Models ────────────────────────────────────────────────────────────

class Hizmetler(BaseModel):
    baglama: float = 0
    atik_su: float = 0
    sintine: float = 0
    atik_yag: float = 0
    yakit_ikmal: float = 0
    palamar: float = 0
    diger: float = 0


class FaturaCreate(BaseModel):
    baglama_id: Optional[int] = None
    hizmetler: Optional[Hizmetler] = None
    tutar: Optional[float] = None          # manuel tutar (hizmetler yoksa)
    kdv_orani: float = 20.0
    odeme_turu: Optional[str] = None       # Sanal POS / Havale-EFT / Nakit / Cari
    banka: Optional[str] = None
    tahsil_eden: Optional[str] = None
    son_odeme_tarihi: Optional[date] = None
    notlar: Optional[str] = None


class FaturaUpdate(BaseModel):
    hizmetler: Optional[Hizmetler] = None
    tutar: Optional[float] = None
    kdv_orani: Optional[float] = None
    odeme_turu: Optional[str] = None
    banka: Optional[str] = None
    tahsil_eden: Optional[str] = None
    son_odeme_tarihi: Optional[date] = None
    notlar: Optional[str] = None
    durum: Optional[str] = None


class DurumUpdate(BaseModel):
    durum: str


def hesapla(hizmetler_dict: dict, tutar_raw: float, kdv_orani: float):
    """Tutar, KDV, Damga Vergisi ve Genel Toplam hesapla."""
    if hizmetler_dict:
        net = Decimal(str(sum(float(v) for v in hizmetler_dict.values())))
    else:
        net = Decimal(str(tutar_raw or 0))
    kdv = (net * Decimal(str(kdv_orani)) / 100).quantize(Decimal("0.01"))
    damga = ((net + kdv) * DAMGA_ORANI).quantize(Decimal("0.01"))
    toplam = (net + kdv + damga).quantize(Decimal("0.01"))
    return float(net), float(kdv), float(damga), float(toplam)


def _parse_jsonb(val) -> dict:
    if val is None:
        return {}
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            return {}
    try:
        return dict(val)
    except Exception:
        return {}


def row_to_dict(r) -> dict:
    return {
        "id": r["id"],
        "fatura_no": r["fatura_no"],
        "baglama_id": r["baglama_id"],
        "tekne_adi": r["tekne_adi"],
        "liman_adi": r["liman_adi"],
        "iskele_no": r["iskele_no"],
        "tutar": float(r["tutar"]) if r["tutar"] else 0,
        "kdv_orani": float(r["kdv_orani"]) if r["kdv_orani"] else 20,
        "kdv_tutari": float(r["kdv_tutari"]) if r["kdv_tutari"] else 0,
        "damga_vergisi": float(r["damga_vergisi"]) if r["damga_vergisi"] else 0,
        "toplam_tutar": float(r["toplam_tutar"]) if r["toplam_tutar"] else 0,
        "durum": r["durum"],
        "odeme_turu": r["odeme_turu"],
        "banka": r["banka"],
        "tahsil_eden": r["tahsil_eden"],
        "hizmetler": _parse_jsonb(r["hizmetler"]),
        "notlar": r["notlar"],
        "son_odeme_tarihi": r["son_odeme_tarihi"].isoformat() if r["son_odeme_tarihi"] else None,
        "olusturuldu": r["olusturuldu"].strftime("%Y-%m-%d") if r["olusturuldu"] else None,
    }


BASE_QUERY = """
    SELECT f.*,
           t.ad  AS tekne_adi,
           l.ad  AS liman_adi,
           b.iskele_no
    FROM faturalar f
    LEFT JOIN baglamalar b ON f.baglama_id = b.id
    LEFT JOIN tekneler   t ON b.tekne_id   = t.id
    LEFT JOIN limanlar   l ON b.liman_id   = l.id
"""


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("")
async def list_faturalar(
    durum: Optional[str]  = Query(None),
    liman_id: Optional[int] = Query(None),
    baslangic: Optional[date] = Query(None),
    bitis: Optional[date] = Query(None),
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    token: dict = Depends(decode_token),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        conditions = []
        params = []

        if durum:
            params.append(durum)
            conditions.append(f"f.durum = ${len(params)}")

        if liman_id:
            params.append(liman_id)
            conditions.append(f"b.liman_id = ${len(params)}")

        if baslangic:
            params.append(baslangic)
            conditions.append(f"f.olusturuldu::date >= ${len(params)}")

        if bitis:
            params.append(bitis)
            conditions.append(f"f.olusturuldu::date <= ${len(params)}")

        if q:
            params.append(f"%{q}%")
            conditions.append(f"(f.fatura_no ILIKE ${len(params)} OR t.ad ILIKE ${len(params)})")

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        # Totals for stats strip
        stats = await conn.fetchrow(f"""
            SELECT
              COUNT(*) as toplam_adet,
              COALESCE(SUM(f.toplam_tutar), 0) AS toplam,
              COALESCE(SUM(CASE WHEN f.durum='odendi'    THEN f.toplam_tutar ELSE 0 END), 0) AS odenen,
              COALESCE(SUM(CASE WHEN f.durum='beklemede' THEN f.toplam_tutar ELSE 0 END), 0) AS bekleyen,
              COALESCE(SUM(CASE WHEN f.durum='iptal'     THEN f.toplam_tutar ELSE 0 END), 0) AS iptal
            FROM faturalar f
            LEFT JOIN baglamalar b ON f.baglama_id = b.id
            LEFT JOIN tekneler   t ON b.tekne_id   = t.id
            LEFT JOIN limanlar   l ON b.liman_id   = l.id
            {where}
        """, *params)

        total = stats["toplam_adet"]
        offset = (page - 1) * per_page
        rows = await conn.fetch(
            f"{BASE_QUERY} {where} ORDER BY f.olusturuldu DESC LIMIT ${len(params)+1} OFFSET ${len(params)+2}",
            *params, per_page, offset,
        )

        return {
            "faturalar": [row_to_dict(r) for r in rows],
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
            "stats": {
                "toplam": float(stats["toplam"]),
                "odenen": float(stats["odenen"]),
                "bekleyen": float(stats["bekleyen"]),
                "iptal": float(stats["iptal"]),
            },
        }


@router.get("/export")
async def export_faturalar(
    durum: Optional[str] = Query(None),
    liman_id: Optional[int] = Query(None),
    baslangic: Optional[date] = Query(None),
    bitis: Optional[date] = Query(None),
    token: dict = Depends(decode_token),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        conditions = []
        params = []
        if durum:
            params.append(durum); conditions.append(f"f.durum = ${len(params)}")
        if liman_id:
            params.append(liman_id); conditions.append(f"b.liman_id = ${len(params)}")
        if baslangic:
            params.append(baslangic); conditions.append(f"f.olusturuldu::date >= ${len(params)}")
        if bitis:
            params.append(bitis); conditions.append(f"f.olusturuldu::date <= ${len(params)}")
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        rows = await conn.fetch(
            f"{BASE_QUERY} {where} ORDER BY f.olusturuldu DESC", *params
        )

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Fatura No", "Tekne", "Liman", "İskele", "Net Tutar", "KDV Oranı",
                "KDV Tutarı", "Damga Vergisi", "Genel Toplam",
                "Ödeme Türü", "Banka", "Tahsil Eden", "Durum", "Tarih", "Notlar"])
    for r in rows:
        d = row_to_dict(r)
        w.writerow([
            d["fatura_no"], d["tekne_adi"] or "", d["liman_adi"] or "", d["iskele_no"] or "",
            d["tutar"], f'%{d["kdv_orani"]}', d["kdv_tutari"], d["damga_vergisi"],
            d["toplam_tutar"], d["odeme_turu"] or "", d["banka"] or "",
            d["tahsil_eden"] or "", d["durum"], d["olusturuldu"] or "", d["notlar"] or "",
        ])

    buf.seek(0)
    filename = f"faturalar_{date.today()}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{fatura_id}")
async def get_fatura(fatura_id: int, token: dict = Depends(decode_token)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(f"{BASE_QUERY} WHERE f.id = $1", fatura_id)
    if not row:
        raise HTTPException(status_code=404, detail="Fatura bulunamadı.")
    return row_to_dict(row)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_fatura(body: FaturaCreate, token: dict = Depends(decode_token)):
    hizm = body.hizmetler.model_dump() if body.hizmetler else {}
    net, kdv, damga, toplam = hesapla(hizm, body.tutar or 0, body.kdv_orani)

    pool = await get_pool()
    async with pool.acquire() as conn:
        fatura_no = gen_fatura_no()
        while await conn.fetchval("SELECT id FROM faturalar WHERE fatura_no=$1", fatura_no):
            fatura_no = gen_fatura_no()

        row = await conn.fetchrow(
            """INSERT INTO faturalar
               (baglama_id, kullanici_id, fatura_no, tutar, kdv_orani, kdv_tutari,
                damga_vergisi, toplam_tutar, hizmetler, odeme_turu, banka,
                tahsil_eden, son_odeme_tarihi, notlar, durum)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,'beklemede')
               RETURNING id, fatura_no""",
            body.baglama_id, int(token.get("sub", 1)), fatura_no,
            net, body.kdv_orani, kdv, damga, toplam,
            hizm or None,
            body.odeme_turu, body.banka, body.tahsil_eden,
            body.son_odeme_tarihi, body.notlar,
        )
    return {"id": row["id"], "fatura_no": row["fatura_no"], "mesaj": "Fatura oluşturuldu."}


@router.put("/{fatura_id}")
async def update_fatura(fatura_id: int, body: FaturaUpdate, token: dict = Depends(decode_token)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT tutar, kdv_orani, hizmetler FROM faturalar WHERE id=$1", fatura_id
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Fatura bulunamadı.")

        hizm = body.hizmetler.model_dump() if body.hizmetler else (dict(existing["hizmetler"]) if existing["hizmetler"] else {})
        kdv_orani = body.kdv_orani if body.kdv_orani is not None else float(existing["kdv_orani"])
        tutar_raw = body.tutar if body.tutar is not None else float(existing["tutar"])

        net, kdv, damga, toplam = hesapla(hizm, tutar_raw, kdv_orani)

        await conn.execute(
            """UPDATE faturalar SET
               tutar=$1, kdv_orani=$2, kdv_tutari=$3, damga_vergisi=$4, toplam_tutar=$5,
               hizmetler=$6, odeme_turu=COALESCE($7, odeme_turu),
               banka=COALESCE($8, banka), tahsil_eden=COALESCE($9, tahsil_eden),
               son_odeme_tarihi=COALESCE($10, son_odeme_tarihi),
               notlar=COALESCE($11, notlar),
               durum=COALESCE($12, durum)
               WHERE id=$13""",
            net, kdv_orani, kdv, damga, toplam,
            hizm or None,
            body.odeme_turu, body.banka, body.tahsil_eden,
            body.son_odeme_tarihi, body.notlar, body.durum,
            fatura_id,
        )
    return {"mesaj": "Fatura güncellendi."}


@router.patch("/{fatura_id}/durum")
async def update_durum(fatura_id: int, body: DurumUpdate, token: dict = Depends(decode_token)):
    valid = {"beklemede", "odendi", "iptal"}
    if body.durum not in valid:
        raise HTTPException(status_code=400, detail=f"Geçersiz durum. Geçerli değerler: {valid}")
    pool = await get_pool()
    async with pool.acquire() as conn:
        r = await conn.execute(
            "UPDATE faturalar SET durum=$1, odeme_tarihi=CASE WHEN $1='odendi' THEN NOW() ELSE odeme_tarihi END WHERE id=$2",
            body.durum, fatura_id,
        )
    if r == "UPDATE 0":
        raise HTTPException(status_code=404, detail="Fatura bulunamadı.")
    return {"mesaj": f"Durum '{body.durum}' olarak güncellendi."}
