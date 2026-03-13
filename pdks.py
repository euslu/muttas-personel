import re
from datetime import datetime, date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Header
from db import get_pool
from auth import decode_token

router = APIRouter(prefix="/pdks", tags=["pdks"])

PDKS_API_KEY = "MuttasPDKS2026!"

TR500_PATTERN = re.compile(
    r"(\d+),(\d+),(\d+)\s+(\d{4}/\d{2}/\d{2})\s+(\d{2}:\d{2}:\d{2})"
)

def parse_tr500(content: str):
    kayitlar = []
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        m = TR500_PATTERN.match(line)
        if m:
            cihaz_no = int(m.group(1))
            personel_no = m.group(2).lstrip("0") or "0"
            giris_cikis = int(m.group(3))
            tarih_str = m.group(4).replace("/", "-")
            saat_str = m.group(5)
            zaman = datetime.fromisoformat(f"{tarih_str} {saat_str}")
            kayitlar.append({
                "cihaz_no": cihaz_no,
                "personel_no": personel_no,
                "giris_cikis": giris_cikis,
                "zaman": zaman,
                "ham_veri": line,
            })
    return kayitlar


@router.post("/yukle")
async def pdks_dosya_yukle(
    dosya: UploadFile = File(...),
    x_api_key: Optional[str] = Header(None),
):
    if x_api_key != PDKS_API_KEY:
        raise HTTPException(status_code=403, detail="Geçersiz API anahtarı")

    icerik = await dosya.read()
    try:
        metin = icerik.decode("utf-8")
    except UnicodeDecodeError:
        metin = icerik.decode("windows-1254", errors="replace")

    kayitlar = parse_tr500(metin)
    if not kayitlar:
        return {"durum": "uyari", "mesaj": "Dosyada geçerli kayıt bulunamadı", "toplam": 0}

    pool = await get_pool()
    eklenen = 0
    atlanan = 0
    async with pool.acquire() as conn:
        for k in kayitlar:
            try:
                await conn.execute(
                    """
                    INSERT INTO pdks_hareketler (cihaz_no, personel_no, giris_cikis, zaman, ham_veri)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (cihaz_no, personel_no, zaman) DO NOTHING
                    """,
                    k["cihaz_no"], k["personel_no"], k["giris_cikis"], k["zaman"], k["ham_veri"]
                )
                eklenen += 1
            except Exception:
                atlanan += 1

    return {
        "durum": "ok",
        "toplam": len(kayitlar),
        "eklenen": eklenen,
        "atlanan": atlanan,
    }


@router.get("/hareketler")
async def pdks_hareketler(
    tarih: Optional[str] = None,
    personel_no: Optional[str] = None,
    cihaz_no: Optional[int] = None,
    limit: int = 200,
    current_user=Depends(decode_token),
):
    pool = await get_pool()
    kosullar = []
    params = []

    if tarih:
        params.append(tarih)
        kosullar.append(f"DATE(h.zaman) = ${len(params)}")
    if personel_no:
        params.append(personel_no)
        kosullar.append(f"h.personel_no = ${len(params)}")
    if cihaz_no:
        params.append(cihaz_no)
        kosullar.append(f"h.cihaz_no = ${len(params)}")

    where = ("WHERE " + " AND ".join(kosullar)) if kosullar else ""
    params.append(limit)

    query = f"""
        SELECT h.id, h.cihaz_no, c.cihaz_adi, h.personel_no,
               p.ad_soyad,
               h.giris_cikis, h.zaman
        FROM pdks_hareketler h
        LEFT JOIN pdks_cihazlar c ON c.cihaz_no = h.cihaz_no
        LEFT JOIN personel p ON p.sicil_no::text = h.personel_no
        {where}
        ORDER BY h.zaman DESC
        LIMIT ${len(params)}
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)

    return [dict(r) for r in rows]


@router.get("/ozet")
async def pdks_ozet(
    tarih: Optional[str] = None,
    current_user=Depends(decode_token),
):
    pool = await get_pool()
    if not tarih:
        tarih = datetime.now().strftime("%Y-%m-%d")
    tarih_dt = date.fromisoformat(tarih)

    async with pool.acquire() as conn:
        toplam = await conn.fetchval(
            "SELECT COUNT(*) FROM pdks_hareketler WHERE DATE(zaman) = $1", tarih_dt
        )
        giris = await conn.fetchval(
            "SELECT COUNT(*) FROM pdks_hareketler WHERE DATE(zaman) = $1 AND giris_cikis = 0", tarih_dt
        )
        cikis = await conn.fetchval(
            "SELECT COUNT(*) FROM pdks_hareketler WHERE DATE(zaman) = $1 AND giris_cikis = 1", tarih_dt
        )
        cihaz_rows = await conn.fetch(
            """
            SELECT c.cihaz_adi, COUNT(*) as hareket
            FROM pdks_hareketler h
            JOIN pdks_cihazlar c ON c.cihaz_no = h.cihaz_no
            WHERE DATE(h.zaman) = $1
            GROUP BY c.cihaz_adi ORDER BY hareket DESC
            """, tarih_dt
        )
        son_yukleme = await conn.fetchval(
            "SELECT MAX(yukleme_zamani) FROM pdks_hareketler"
        )

    return {
        "tarih": tarih,
        "toplam": toplam,
        "giris": giris,
        "cikis": cikis,
        "son_yukleme": son_yukleme.isoformat() if son_yukleme else None,
        "cihaz_dagilim": [dict(r) for r in cihaz_rows],
    }


@router.get("/cihazlar")
async def pdks_cihazlar(current_user=Depends(decode_token)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM pdks_cihazlar ORDER BY cihaz_no")
    return [dict(r) for r in rows]


@router.get("/personel/{personel_no}")
async def pdks_personel_detay(
    personel_no: str,
    tarih_baslangic: Optional[str] = None,
    tarih_bitis: Optional[str] = None,
    current_user=Depends(decode_token),
):
    pool = await get_pool()
    params = [personel_no]
    ek = ""
    if tarih_baslangic:
        params.append(tarih_baslangic)
        ek += f" AND DATE(h.zaman) >= ${len(params)}"
    if tarih_bitis:
        params.append(tarih_bitis)
        ek += f" AND DATE(h.zaman) <= ${len(params)}"

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"""
            SELECT h.id, h.cihaz_no, c.cihaz_adi, h.giris_cikis, h.zaman
            FROM pdks_hareketler h
            LEFT JOIN pdks_cihazlar c ON c.cihaz_no = h.cihaz_no
            WHERE h.personel_no = $1 {ek}
            ORDER BY h.zaman DESC LIMIT 500
            """,
            *params
        )
    return [dict(r) for r in rows]
