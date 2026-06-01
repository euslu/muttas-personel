import os, uuid, shutil, random, time, logging, re, httpx
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, File, UploadFile, Form, Depends
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, JWTError

from db import get_pool

logger = logging.getLogger("sms")

router = APIRouter(tags=["self-servis"])

JWT_SECRET    = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
security      = HTTPBearer()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

DOSYA_TURLERI = {"ruhsat", "sigorta", "kimlik", "diger"}
ALLOWED_EXT   = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
MAX_BOYUT     = 10 * 1024 * 1024  # 10 MB


def decode_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        return jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Geçersiz token.")


# ── Modeller ──────────────────────────────────────────────────────────────────

class PublicBasvuruCreate(BaseModel):
    tekne_adi:      str
    tekne_tipi:     Optional[str]   = None
    uzunluk_m:      Optional[float] = None
    genislik_m:     Optional[float] = None
    sicil_no:       Optional[str]   = None
    bayrak_ulke:    str             = "TR"
    basvuru_sahibi: str
    tc_kimlik:      Optional[str]   = None
    telefon:        str
    eposta:         Optional[str]   = None
    liman_id:       int
    giris_tarihi:   date
    cikis_tarihi:   Optional[date]  = None
    sigorta_bitis:  Optional[date]  = None
    notlar:         Optional[str]   = None


# ── Yardımcı ──────────────────────────────────────────────────────────────────

def _dosya_adi_guveli(basvuru_id: int, dosya_tipi: str, orijinal: str) -> str:
    ext = os.path.splitext(orijinal)[1].lower() if orijinal else ".bin"
    return f"{basvuru_id}_{dosya_tipi}_{uuid.uuid4().hex[:8]}{ext}"


# ── Herkese Açık Endpoint'ler ─────────────────────────────────────────────────

@router.get("/public/limanlar")
async def public_limanlar():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, ad, sehir FROM limanlar WHERE aktif=TRUE ORDER BY ad")
        return [{"id": r["id"], "ad": r["ad"], "sehir": r["sehir"]} for r in rows]


@router.post("/public/basvuru")
async def public_basvuru_olustur(data: PublicBasvuruCreate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        liman = await conn.fetchrow(
            "SELECT id, ad FROM limanlar WHERE id=$1 AND aktif=TRUE", data.liman_id
        )
        if not liman:
            raise HTTPException(status_code=404, detail="Liman bulunamadı.")

        # Tekne bul veya oluştur
        tekne_id = None
        if data.sicil_no:
            t = await conn.fetchrow(
                "SELECT id FROM tekneler WHERE sicil_no=$1 LIMIT 1", data.sicil_no
            )
            if t:
                tekne_id = t["id"]

        if not tekne_id:
            t = await conn.fetchrow(
                "SELECT id FROM tekneler WHERE LOWER(ad)=LOWER($1) LIMIT 1", data.tekne_adi
            )
            if t:
                tekne_id = t["id"]

        if not tekne_id:
            tekne_id = await conn.fetchval(
                """INSERT INTO tekneler (ad, tip, uzunluk_m, genislik_m, sicil_no, bayrak_ulke)
                   VALUES ($1,$2,$3,$4,$5,$6) RETURNING id""",
                data.tekne_adi, data.tekne_tipi, data.uzunluk_m,
                data.genislik_m, data.sicil_no, data.bayrak_ulke
            )

        # Ref no (unique)
        for _ in range(10):
            ref_no = "REF-" + uuid.uuid4().hex[:8].upper()
            exists = await conn.fetchval(
                "SELECT id FROM baglamalar WHERE ref_no=$1", ref_no
            )
            if not exists:
                break

        token = str(uuid.uuid4())

        giris = datetime(data.giris_tarihi.year, data.giris_tarihi.month, data.giris_tarihi.day)
        cikis = (
            datetime(data.cikis_tarihi.year, data.cikis_tarihi.month, data.cikis_tarihi.day)
            if data.cikis_tarihi else None
        )

        row = await conn.fetchrow(
            """
            INSERT INTO baglamalar
                (liman_id, tekne_id, giris_tarihi, cikis_tarihi,
                 durum, notlar, ref_no, basvuru_sahibi, telefon,
                 sigorta_bitis, basvuru_token, eposta, tc_kimlik)
            VALUES ($1,$2,$3,$4,'dosya_yuklenenler',$5,$6,$7,$8,$9,$10,$11,$12)
            RETURNING id, ref_no, basvuru_token
            """,
            data.liman_id, tekne_id, giris, cikis,
            data.notlar, ref_no, data.basvuru_sahibi, data.telefon,
            data.sigorta_bitis, token, data.eposta, data.tc_kimlik
        )

        return {
            "mesaj": "Başvurunuz alındı. Lütfen belgelerinizi yükleyin.",
            "basvuru_id": row["id"],
            "ref_no":     row["ref_no"],
            "token":      row["basvuru_token"],
        }


@router.get("/public/basvuru/{token}")
async def public_basvuru_getir(token: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT b.id, b.ref_no, b.basvuru_sahibi, b.telefon, b.eposta, b.tc_kimlik,
                   b.durum, b.giris_tarihi, b.cikis_tarihi, b.sigorta_bitis, b.notlar,
                   t.ad AS tekne_adi, t.tip, t.uzunluk_m, t.genislik_m, t.sicil_no, t.bayrak_ulke,
                   l.ad AS liman_adi, l.sehir AS liman_sehir
            FROM baglamalar b
            LEFT JOIN tekneler t ON t.id = b.tekne_id
            LEFT JOIN limanlar l ON l.id = b.liman_id
            WHERE b.basvuru_token = $1
            """,
            token,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Başvuru bulunamadı veya geçersiz link.")

        belgeler = await conn.fetch(
            "SELECT id, dosya_tipi, dosya_adi, yuklendi_at FROM belgeler WHERE basvuru_id=$1 ORDER BY yuklendi_at",
            row["id"],
        )

        return {
            "id":             row["id"],
            "ref_no":         row["ref_no"],
            "basvuru_sahibi": row["basvuru_sahibi"],
            "telefon":        row["telefon"],
            "eposta":         row["eposta"],
            "tc_kimlik":      row["tc_kimlik"],
            "durum":          row["durum"],
            "giris_tarihi":   row["giris_tarihi"].strftime("%Y-%m-%d") if row["giris_tarihi"] else None,
            "cikis_tarihi":   row["cikis_tarihi"].strftime("%Y-%m-%d") if row["cikis_tarihi"] else None,
            "sigorta_bitis":  row["sigorta_bitis"].isoformat() if row["sigorta_bitis"] else None,
            "liman_adi":      row["liman_adi"],
            "liman_sehir":    row["liman_sehir"],
            "tekne_adi":      row["tekne_adi"],
            "tip":            row["tip"],
            "uzunluk_m":      float(row["uzunluk_m"]) if row["uzunluk_m"] else None,
            "genislik_m":     float(row["genislik_m"]) if row["genislik_m"] else None,
            "sicil_no":       row["sicil_no"],
            "bayrak_ulke":    row["bayrak_ulke"],
            "notlar":         row["notlar"],
            "belgeler": [
                {
                    "id":          b["id"],
                    "dosya_tipi":  b["dosya_tipi"],
                    "dosya_adi":   b["dosya_adi"],
                    "yuklendi_at": b["yuklendi_at"].strftime("%d.%m.%Y %H:%M") if b["yuklendi_at"] else None,
                }
                for b in belgeler
            ],
        }


@router.post("/public/basvuru/{token}/belge")
async def public_belge_yukle(
    token: str,
    dosya_tipi: str = Form(...),
    dosya: UploadFile = File(...),
):
    if dosya_tipi not in DOSYA_TURLERI:
        raise HTTPException(
            status_code=400,
            detail=f"Geçersiz dosya tipi. Seçenekler: {', '.join(sorted(DOSYA_TURLERI))}"
        )

    ext = os.path.splitext(dosya.filename or "")[1].lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail="Sadece PDF, JPG, PNG, WEBP dosyaları kabul edilir.")

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id FROM baglamalar WHERE basvuru_token=$1", token
        )
        if not row:
            raise HTTPException(status_code=404, detail="Başvuru bulunamadı.")

        basvuru_id = row["id"]

        # Aynı tipten mevcut belge varsa sil
        old = await conn.fetchrow(
            "SELECT dosya_yolu FROM belgeler WHERE basvuru_id=$1 AND dosya_tipi=$2",
            basvuru_id, dosya_tipi,
        )
        if old and old["dosya_yolu"] and os.path.exists(old["dosya_yolu"]):
            os.remove(old["dosya_yolu"])
        await conn.execute(
            "DELETE FROM belgeler WHERE basvuru_id=$1 AND dosya_tipi=$2",
            basvuru_id, dosya_tipi,
        )

        icerik = await dosya.read()
        if len(icerik) > MAX_BOYUT:
            raise HTTPException(status_code=400, detail="Dosya 10 MB'ı geçemez.")

        dosya_adi_guveli = _dosya_adi_guveli(basvuru_id, dosya_tipi, dosya.filename or "dosya")
        dosya_yolu = os.path.join(UPLOAD_DIR, dosya_adi_guveli)
        with open(dosya_yolu, "wb") as f:
            f.write(icerik)

        belge = await conn.fetchrow(
            """INSERT INTO belgeler (basvuru_id, dosya_tipi, dosya_adi, dosya_yolu)
               VALUES ($1,$2,$3,$4) RETURNING id""",
            basvuru_id, dosya_tipi, dosya.filename, dosya_yolu,
        )

        return {"mesaj": "Belge yüklendi.", "belge_id": belge["id"]}


# ── SMS Doğrulama ──────────────────────────────────────────────────────────

SMS_CODE_EXPIRY = 300
SMS_CODE_LENGTH = 6

SMS_API_URL = os.environ.get("SMS_API_URL", "https://api.netgsm.com.tr/sms/send/xml")
NETGSM_USERCODE = os.environ.get("NETGSM_USERCODE", "")
NETGSM_PASSWORD = os.environ.get("NETGSM_PASSWORD", "")
NETGSM_MSGHEADER = os.environ.get("NETGSM_MSGHEADER", "MUTTAS")


def _mask_phone(phone: str) -> str:
    digits = re.sub(r'\D', '', phone)
    if len(digits) >= 7:
        return digits[:3] + '***' + digits[-2:]
    return '***'


def _format_phone_netgsm(phone: str) -> str:
    digits = re.sub(r'\D', '', phone)
    if digits.startswith('0') and len(digits) == 11:
        digits = '9' + digits
    elif len(digits) == 10:
        digits = '90' + digits
    return digits


async def _send_sms(phone: str, message: str) -> bool:
    if not NETGSM_USERCODE or not NETGSM_PASSWORD:
        logger.warning(f"NetGSM yapılandırılmamış — mesaj gönderilmedi ({_mask_phone(phone)})")
        return True

    formatted_phone = _format_phone_netgsm(phone)

    params = {
        "usercode": NETGSM_USERCODE,
        "password": NETGSM_PASSWORD,
        "gsmno": formatted_phone,
        "message": message,
        "msgheader": NETGSM_MSGHEADER,
        "dil": "TR",
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://api.netgsm.com.tr/sms/send/get/",
                params=params,
            )
            resp_text = resp.text.strip()
            logger.info(f"NetGSM yanıt: {resp_text} (telefon: {_mask_phone(phone)})")

            if resp_text.startswith("00") or resp_text.startswith("01") or resp_text.startswith("02"):
                logger.info(f"SMS başarıyla gönderildi: {_mask_phone(phone)}")
                return True
            else:
                logger.error(f"NetGSM SMS hata kodu: {resp_text}")
                return False
    except Exception as e:
        logger.error(f"SMS gönderim hatası: {e}")
        return False


class SmsKodGonder(BaseModel):
    tc_kimlik: str


class SmsKodDogrula(BaseModel):
    tc_kimlik: str
    kod: str


@router.post("/public/sms-gonder")
async def sms_kod_gonder(data: SmsKodGonder):
    tc = data.tc_kimlik.strip()
    if not tc or len(tc) != 11 or not tc.isdigit():
        raise HTTPException(status_code=400, detail="Geçerli bir TC kimlik numarası giriniz.")

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            existing = await conn.fetchrow(
                "SELECT created_at FROM sms_kodlari WHERE tc_kimlik=$1 ORDER BY created_at DESC LIMIT 1 FOR UPDATE", tc
            )
            if existing and (datetime.now(existing["created_at"].tzinfo) - existing["created_at"]).total_seconds() < 60:
                raise HTTPException(status_code=429, detail="Lütfen 1 dakika bekleyip tekrar deneyin.")

            row = await conn.fetchrow(
                "SELECT id, ad_soyad, telefon, bolum, unvan, ilce FROM personel WHERE tc_kimlik=$1 AND aktif=TRUE",
                tc
            )
            if not row:
                raise HTTPException(status_code=404, detail="Bu TC kimlik numarasıyla kayıtlı aktif personel bulunamadı.")

            telefon = row["telefon"]
            if not telefon:
                raise HTTPException(status_code=400, detail="Personelin kayıtlı telefon numarası bulunamadı.")

            kod = ''.join([str(random.randint(0, 9)) for _ in range(SMS_CODE_LENGTH)])

            await conn.execute("DELETE FROM sms_kodlari WHERE tc_kimlik=$1", tc)
            await conn.execute("""
                INSERT INTO sms_kodlari (tc_kimlik, kod, personel_id, ad_soyad, bolum, unvan, ilce)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, tc, kod, row["id"], row["ad_soyad"], row["bolum"], row["unvan"], row["ilce"])

        sms_mesaj = f"MUTTAS IK izin basvuru dogrulama kodunuz: {kod}"
        sent = await _send_sms(telefon, sms_mesaj)
        if not sent:
            await conn.execute("DELETE FROM sms_kodlari WHERE tc_kimlik=$1", tc)
            raise HTTPException(status_code=500, detail="SMS gönderilemedi. Lütfen daha sonra tekrar deneyin.")

        await conn.execute(
            "DELETE FROM sms_kodlari WHERE created_at < NOW() - INTERVAL '10 minutes' AND tc_kimlik != $1", tc
        )

    return {
        "mesaj": "Doğrulama kodu gönderildi.",
        "telefon": _mask_phone(telefon),
        "ad_soyad": row["ad_soyad"],
    }


@router.post("/public/sms-dogrula")
async def sms_kod_dogrula(data: SmsKodDogrula):
    tc = data.tc_kimlik.strip()
    kod = data.kod.strip()

    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            entry = await conn.fetchrow(
                "SELECT * FROM sms_kodlari WHERE tc_kimlik=$1 ORDER BY created_at DESC LIMIT 1 FOR UPDATE", tc
            )
            if not entry:
                raise HTTPException(status_code=400, detail="Önce doğrulama kodu talep edin.")

            elapsed = (datetime.now(entry["created_at"].tzinfo) - entry["created_at"]).total_seconds()
            if elapsed > SMS_CODE_EXPIRY:
                await conn.execute("DELETE FROM sms_kodlari WHERE tc_kimlik=$1", tc)
                raise HTTPException(status_code=400, detail="Kodun süresi doldu. Lütfen yeni kod talep edin.")

            updated = await conn.fetchrow(
                "UPDATE sms_kodlari SET attempts=attempts+1 WHERE id=$1 RETURNING attempts", entry["id"]
            )
            new_attempts = updated["attempts"]

            if new_attempts > 5:
                await conn.execute("DELETE FROM sms_kodlari WHERE tc_kimlik=$1", tc)
                raise HTTPException(status_code=429, detail="Çok fazla hatalı deneme. Lütfen yeni kod talep edin.")

            if kod != entry["kod"]:
                kalan = 5 - new_attempts
                raise HTTPException(status_code=400, detail=f"Kod hatalı. {kalan} deneme hakkınız kaldı.")

            sms_token = str(uuid.uuid4())
            await conn.execute(
                "UPDATE sms_kodlari SET verified=TRUE, sms_token=$1 WHERE id=$2",
                sms_token, entry["id"]
            )
            is_yonetici_row = await conn.fetchval(
                "SELECT 1 FROM yonetici_unvanlar WHERE unvan = $1", entry["unvan"] or ""
            )

    return {
        "mesaj": "Doğrulama başarılı.",
        "sms_token": sms_token,
        "personel": {
            "id": entry["personel_id"],
            "ad_soyad": entry["ad_soyad"],
            "bolum": entry["bolum"],
            "unvan": entry["unvan"],
            "ilce": entry["ilce"],
            "is_yonetici": bool(is_yonetici_row),
        }
    }


# ── Public İzin Başvuru Endpoint'leri ────────────────────────────────────────

@router.get("/public/personel/ara")
async def public_personel_ara(tc: Optional[str] = None, sms_token: Optional[str] = None):
    if not tc:
        raise HTTPException(status_code=400, detail="TC kimlik numarası gereklidir.")
    if not sms_token:
        raise HTTPException(status_code=403, detail="SMS doğrulaması gereklidir.")

    tc = tc.strip()
    if not tc or len(tc) != 11 or not tc.isdigit():
        raise HTTPException(status_code=400, detail="Geçerli bir TC kimlik numarası giriniz.")

    pool = await get_pool()
    async with pool.acquire() as conn:
        entry = await conn.fetchrow(
            "SELECT personel_id FROM sms_kodlari WHERE tc_kimlik=$1 AND verified=TRUE AND sms_token=$2",
            tc, sms_token
        )
        if not entry:
            raise HTTPException(status_code=403, detail="SMS doğrulaması gereklidir.")

        row = await conn.fetchrow(
            "SELECT id, ad_soyad, bolum, unvan, ilce FROM personel WHERE tc_kimlik=$1 AND aktif=TRUE",
            tc
        )
        if not row:
            raise HTTPException(status_code=404, detail="Personel bulunamadı.")
        return {
            "id":       row["id"],
            "ad_soyad": row["ad_soyad"],
            "bolum":    row["bolum"],
            "unvan":    row["unvan"],
            "ilce":     row["ilce"],
        }


class PublicIzinCreate(BaseModel):
    personel_id:        int
    tc_kimlik:          str
    sms_token:          Optional[str] = None
    izin_turu:          str
    baslangic:          date
    bitis:              date
    gun_sayisi:         int
    kullanilabilir_gun: Optional[int] = None
    vekil_ad_soyad:     Optional[str] = None
    izin_adresi:        Optional[str] = None
    aciklama:           Optional[str] = None
    notlar:             Optional[str] = None
    imza:               Optional[str] = None
    ks_onaylayan:       Optional[str] = None


@router.get("/public/ks-listesi")
async def public_ks_listesi():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT DISTINCT p.ad_soyad
            FROM personel p
            JOIN kullanicilar k ON LOWER(REPLACE(p.tc_kimlik,' ','')) = k.email
            WHERE k.rol IN ('koordinasyon_sorumlusu', 'mudur')
              AND k.aktif = TRUE AND p.aktif = TRUE
            ORDER BY p.ad_soyad
        """)
    return [r["ad_soyad"] for r in rows]


@router.get("/public/yonetici-unvanlar")
async def public_yonetici_unvanlar():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT unvan FROM yonetici_unvanlar ORDER BY unvan"
        )
    return [r["unvan"] for r in rows]


@router.get("/public/yk-uye-unvanlar")
async def public_yk_uye_unvanlar():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT unvan FROM yk_uye_unvanlar ORDER BY unvan"
        )
    return [r["unvan"] for r in rows]


@router.get("/public/izin-turleri")
async def public_izin_turleri():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT kod, ad FROM izin_turleri WHERE aktif = TRUE ORDER BY sira, ad")
    return [{"kod": r["kod"], "ad": r["ad"]} for r in rows]


@router.get("/public/calisma-gunleri")
async def public_calisma_gunleri():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT unvan, gun_sayisi FROM unvan_calisma_gunu ORDER BY unvan")
    return {r["unvan"]: r["gun_sayisi"] for r in rows}


@router.post("/public/izin", status_code=201)
async def public_izin_olustur(data: PublicIzinCreate):
    pool_check = await get_pool()
    async with pool_check.acquire() as conn_check:
        gecerli = [r["kod"] for r in await conn_check.fetch("SELECT kod FROM izin_turleri WHERE aktif=TRUE")]
    if data.izin_turu not in gecerli:
        raise HTTPException(status_code=400, detail="Geçersiz izin türü.")

    if data.gun_sayisi < 1 or data.gun_sayisi > 365:
        raise HTTPException(status_code=400, detail="Gün sayısı 1-365 arasında olmalıdır.")

    if data.bitis < data.baslangic:
        raise HTTPException(status_code=400, detail="Bitiş tarihi başlangıçtan önce olamaz.")

    tc = data.tc_kimlik.strip()

    pool = await get_pool()
    async with pool.acquire() as conn:
        entry = await conn.fetchrow(
            "SELECT * FROM sms_kodlari WHERE tc_kimlik=$1 AND verified=TRUE AND sms_token=$2 ORDER BY created_at DESC LIMIT 1",
            tc, data.sms_token
        )
        if not entry:
            raise HTTPException(status_code=403, detail="SMS doğrulaması yapılmamış veya geçersiz.")

        elapsed = (datetime.now(entry["created_at"].tzinfo) - entry["created_at"]).total_seconds()
        if elapsed > SMS_CODE_EXPIRY * 2:
            await conn.execute("DELETE FROM sms_kodlari WHERE tc_kimlik=$1", tc)
            raise HTTPException(status_code=403, detail="SMS doğrulama süresi doldu. Lütfen yeniden başvurun.")

        if entry["personel_id"] != data.personel_id:
            raise HTTPException(status_code=403, detail="Personel kimlik doğrulaması başarısız.")

        prs = await conn.fetchrow(
            "SELECT id FROM personel WHERE id=$1 AND tc_kimlik=$2 AND aktif=TRUE",
            data.personel_id, data.tc_kimlik
        )
        if not prs:
            raise HTTPException(status_code=403, detail="TC kimlik doğrulaması başarısız.")

        duplicate = await conn.fetchval(
            "SELECT id FROM izinler WHERE personel_id=$1 AND baslangic=$2 AND bitis=$3 AND izin_turu=$4",
            data.personel_id, data.baslangic, data.bitis, data.izin_turu
        )
        if duplicate:
            raise HTTPException(status_code=409, detail="Bu tarih aralığında aynı türde izin talebi zaten mevcut.")

        row = await conn.fetchrow("""
            INSERT INTO izinler
                (personel_id, talep_tarihi, izin_turu, baslangic, bitis,
                 gun_sayisi, kullanilabilir_gun, vekil_ad_soyad, izin_adresi,
                 aciklama, notlar, imza, ks_onaylayan)
            VALUES ($1, CURRENT_DATE, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            RETURNING id
        """,
            data.personel_id, data.izin_turu, data.baslangic, data.bitis,
            data.gun_sayisi, data.kullanilabilir_gun, data.vekil_ad_soyad,
            data.izin_adresi, data.aciklama, data.notlar, data.imza,
            data.ks_onaylayan,
        )
        await conn.execute("DELETE FROM sms_kodlari WHERE tc_kimlik=$1", tc)

        return {"id": row["id"], "mesaj": "İzin başvurunuz alındı."}


# ── Personel Endpoint'leri (JWT Gerekli) ──────────────────────────────────────

@router.post("/baglamalar/{basvuru_id}/link-olustur")
async def link_olustur(basvuru_id: int, token: dict = Depends(decode_token)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, basvuru_token FROM baglamalar WHERE id=$1", basvuru_id
        )
        if not row:
            raise HTTPException(status_code=404, detail="Başvuru bulunamadı.")

        mevcut_token = row["basvuru_token"]
        if not mevcut_token:
            mevcut_token = str(uuid.uuid4())
            await conn.execute(
                "UPDATE baglamalar SET basvuru_token=$1 WHERE id=$2",
                mevcut_token, basvuru_id,
            )

        return {"token": mevcut_token}


@router.get("/baglamalar/{basvuru_id}/belgeler")
async def basvuru_belgeleri(basvuru_id: int, token: dict = Depends(decode_token)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        exists = await conn.fetchval(
            "SELECT id FROM baglamalar WHERE id=$1", basvuru_id
        )
        if not exists:
            raise HTTPException(status_code=404, detail="Başvuru bulunamadı.")

        rows = await conn.fetch(
            """SELECT id, dosya_tipi, dosya_adi, dosya_yolu, yuklendi_at
               FROM belgeler WHERE basvuru_id=$1 ORDER BY yuklendi_at""",
            basvuru_id,
        )
        return [
            {
                "id":          r["id"],
                "dosya_tipi":  r["dosya_tipi"],
                "dosya_adi":   r["dosya_adi"],
                "dosya_yolu":  r["dosya_yolu"],
                "yuklendi_at": r["yuklendi_at"].strftime("%d.%m.%Y %H:%M") if r["yuklendi_at"] else None,
            }
            for r in rows
        ]


@router.get("/belgeler/{belge_id}/indir")
async def belge_indir(belge_id: int, auth: dict = Depends(decode_token)):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT dosya_adi, dosya_yolu FROM belgeler WHERE id=$1", belge_id
        )
        if not row or not row["dosya_yolu"] or not os.path.exists(row["dosya_yolu"]):
            raise HTTPException(status_code=404, detail="Dosya bulunamadı.")

        return FileResponse(
            row["dosya_yolu"],
            filename=row["dosya_adi"],
            media_type="application/octet-stream",
        )
