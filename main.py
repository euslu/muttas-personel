import time
from collections import defaultdict
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from db import get_pool, close_pool
from permissions import require_admin
from auth import router as auth_router
from gunluk import router as gunluk_router
from basvurular import router as basvurular_router
from dashboard import router as dashboard_router
from tekneler import router as tekneler_router
from faturalar import router as faturalar_router
from self_servis import router as self_servis_router
from personel import router as personel_router
from izinler import router as izinler_router
from vekalet import router as vekalet_router
from pdks import router as pdks_router
from ayarlar import router as ayarlar_router
from satin_alma import router as satin_alma_router
from ihtiyac_talebi import router as ihtiyac_talebi_router


class CSPMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self' 'unsafe-inline' 'unsafe-eval' "
            "https://fonts.googleapis.com https://fonts.gstatic.com; "
            "img-src 'self' data:"
        )
        if request.url.path.endswith(".html"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-worker rate limit. Limitler worker sayısına bölünmüş halde (4 worker)."""
    WORKER_COUNT = int(os.environ.get("WORKER_COUNT", "4"))

    def __init__(self, app):
        super().__init__(app)
        self.requests = defaultdict(list)
        # Limitler worker başına bölünüyor: 10/4 ≈ 3, 120/4 = 30
        pw = max(self.WORKER_COUNT, 1)
        self.public_limits = {
            "/public/": {"max": max(10 // pw, 2), "window": 60},
            "/auth/login": {"max": max(10 // pw, 2), "window": 60},
        }
        self.global_limit = {"max": max(120 // pw, 10), "window": 60}

    TRUSTED_PROXIES = {"127.0.0.1", "::1"}

    def _get_client_ip(self, request):
        client_ip = request.client.host if request.client else "unknown"
        if client_ip in self.TRUSTED_PROXIES:
            forwarded = request.headers.get("x-forwarded-for")
            if forwarded:
                return forwarded.split(",")[0].strip()
        return client_ip

    def _clean_old(self, key, window):
        now = time.time()
        self.requests[key] = [t for t in self.requests[key] if now - t < window]

    async def dispatch(self, request, call_next):
        ip = self._get_client_ip(request)
        path = request.url.path
        now = time.time()

        for prefix, limits in self.public_limits.items():
            if path.startswith(prefix):
                key = f"rl:{ip}:{prefix}"
                self._clean_old(key, limits["window"])
                if len(self.requests[key]) >= limits["max"]:
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "Çok fazla istek. Lütfen biraz bekleyin."},
                        headers={"Retry-After": str(limits["window"])}
                    )
                self.requests[key].append(now)
                break

        global_key = f"rl:{ip}:global"
        self._clean_old(global_key, self.global_limit["window"])
        if len(self.requests[global_key]) >= self.global_limit["max"]:
            return JSONResponse(
                status_code=429,
                content={"detail": "Çok fazla istek. Lütfen biraz bekleyin."},
                headers={"Retry-After": str(self.global_limit["window"])}
            )
        self.requests[global_key].append(now)

        # Bellek temizliği — 5000 key üzerinde çalışır
        if len(self.requests) > 5000:
            cutoff = now - 120
            self.requests = defaultdict(list, {
                k: [t for t in v if t > cutoff]
                for k, v in self.requests.items()
                if any(t > cutoff for t in v)
            })

        response = await call_next(request)
        return response


CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS limanlar (
    id          SERIAL PRIMARY KEY,
    ad          VARCHAR(255) NOT NULL,
    sehir       VARCHAR(255),
    ulke        VARCHAR(100) DEFAULT 'TR',
    kapasite    INT,
    aktif       BOOLEAN DEFAULT TRUE,
    olusturuldu TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS kullanicilar (
    id          SERIAL PRIMARY KEY,
    ad          VARCHAR(100) NOT NULL,
    soyad       VARCHAR(100) NOT NULL,
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    telefon       VARCHAR(30),
    rol           VARCHAR(50) DEFAULT 'kullanici',
    aktif       BOOLEAN DEFAULT TRUE,
    olusturuldu TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tekneler (
    id              SERIAL PRIMARY KEY,
    sahip_id        INT REFERENCES kullanicilar(id) ON DELETE SET NULL,
    ad              VARCHAR(255) NOT NULL,
    tip             VARCHAR(100),
    uzunluk_m       NUMERIC(6, 2),
    genislik_m      NUMERIC(6, 2),
    sicil_no        VARCHAR(100) UNIQUE,
    bayrak_ulke     VARCHAR(100) DEFAULT 'TR',
    aktif           BOOLEAN DEFAULT TRUE,
    olusturuldu     TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS baglamalar (
    id              SERIAL PRIMARY KEY,
    liman_id        INT REFERENCES limanlar(id) ON DELETE CASCADE,
    tekne_id        INT REFERENCES tekneler(id) ON DELETE CASCADE,
    kullanici_id    INT REFERENCES kullanicilar(id) ON DELETE SET NULL,
    giris_tarihi    TIMESTAMPTZ NOT NULL,
    cikis_tarihi    TIMESTAMPTZ,
    iskele_no       VARCHAR(50),
    durum           VARCHAR(50) DEFAULT 'aktif',
    notlar          TEXT,
    olusturuldu     TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tekne_evraklari (
    id              SERIAL PRIMARY KEY,
    tekne_id        INT REFERENCES tekneler(id) ON DELETE CASCADE,
    evrak_turu      VARCHAR(100) NOT NULL,
    evrak_no        VARCHAR(100),
    duzenleme_tarihi DATE,
    gecerlilik_tarihi DATE,
    dosya_yolu      TEXT,
    notlar          TEXT,
    olusturuldu     TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS liman_gunlugu (
    id              SERIAL PRIMARY KEY,
    liman_id        INT REFERENCES limanlar(id) ON DELETE CASCADE,
    baglama_id      INT REFERENCES baglamalar(id) ON DELETE SET NULL,
    tarih           TIMESTAMPTZ DEFAULT NOW(),
    olay_turu       VARCHAR(100) NOT NULL,
    aciklama        TEXT,
    kullanici_id    INT REFERENCES kullanicilar(id) ON DELETE SET NULL,
    olusturuldu     TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS gunluk_ozet (
    id              SERIAL PRIMARY KEY,
    liman_id        INT REFERENCES limanlar(id) ON DELETE CASCADE,
    tarih           DATE NOT NULL,
    toplam_tekne    INT DEFAULT 0,
    giris_sayisi    INT DEFAULT 0,
    cikis_sayisi    INT DEFAULT 0,
    toplam_gelir    NUMERIC(12, 2) DEFAULT 0,
    notlar          TEXT,
    olusturuldu     TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (liman_id, tarih)
);

CREATE TABLE IF NOT EXISTS faturalar (
    id              SERIAL PRIMARY KEY,
    baglama_id      INT REFERENCES baglamalar(id) ON DELETE SET NULL,
    kullanici_id    INT REFERENCES kullanicilar(id) ON DELETE SET NULL,
    fatura_no       VARCHAR(100) UNIQUE NOT NULL,
    tutar           NUMERIC(12, 2) NOT NULL,
    kdv_orani       NUMERIC(5, 2) DEFAULT 20,
    toplam_tutar    NUMERIC(12, 2) NOT NULL,
    durum           VARCHAR(50) DEFAULT 'beklemede',
    odeme_tarihi    TIMESTAMPTZ,
    son_odeme_tarihi DATE,
    notlar          TEXT,
    olusturuldu     TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS belgeler (
    id          SERIAL PRIMARY KEY,
    basvuru_id  INT REFERENCES baglamalar(id) ON DELETE CASCADE NOT NULL,
    dosya_tipi  VARCHAR(50) NOT NULL,
    dosya_adi   VARCHAR(255),
    dosya_yolu  TEXT,
    yuklendi_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS personel (
    id                   SERIAL PRIMARY KEY,
    tc_kimlik            VARCHAR(11),
    sgk_sicil            VARCHAR(50),
    maliyet_merkezi      VARCHAR(100),
    ilce                 VARCHAR(100),
    hizmet_noktasi       VARCHAR(200),
    ad_soyad             VARCHAR(200) NOT NULL,
    cinsiyet             VARCHAR(10),
    bolum                VARCHAR(100),
    unvan                VARCHAR(150),
    ise_giris            DATE,
    isten_cikis          DATE,
    cikis_kodu           VARCHAR(200),
    guvenlik_belge_tarih DATE,
    sigortalilik_baslama DATE,
    hizmet_gun           INTEGER,
    ogrenim              VARCHAR(50),
    mezun_bolum          VARCHAR(150),
    brut_ucret           NUMERIC(12,2),
    dogum_yeri           VARCHAR(100),
    dogum_tarihi         DATE,
    sendika_uyesi        VARCHAR(50),
    kan_grubu            VARCHAR(10),
    medeni_hal           VARCHAR(20),
    cocuk_sayisi         INTEGER DEFAULT 0,
    engelli              BOOLEAN DEFAULT FALSE,
    adres                TEXT,
    telefon              VARCHAR(30),
    meslek_kodu          VARCHAR(20),
    meslek_adi           VARCHAR(150),
    notlar               TEXT,
    aktif                BOOLEAN DEFAULT TRUE,
    olusturuldu          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS izinler (
    id                 SERIAL PRIMARY KEY,
    personel_id        INT REFERENCES personel(id) ON DELETE CASCADE NOT NULL,
    talep_tarihi       DATE NOT NULL DEFAULT CURRENT_DATE,
    izin_turu          VARCHAR(50) NOT NULL,
    baslangic          DATE NOT NULL,
    bitis              DATE NOT NULL,
    gun_sayisi         INTEGER NOT NULL,
    kullanilabilir_gun INTEGER,
    vekil_ad_soyad     VARCHAR(200),
    izin_adresi        TEXT,
    durum              VARCHAR(30) DEFAULT 'beklemede',
    ik_onay_tarihi     DATE,
    ik_onaylayan       VARCHAR(200),
    mudur_onay_tarihi  DATE,
    yk_onay_tarihi     DATE,
    gorev_baslama      DATE,
    notlar             TEXT,
    olusturuldu        TIMESTAMPTZ DEFAULT NOW()
);
"""

MIGRATE_SQL = """
ALTER TABLE baglamalar ADD COLUMN IF NOT EXISTS basvuru_token VARCHAR(36) UNIQUE;
ALTER TABLE baglamalar ADD COLUMN IF NOT EXISTS eposta        VARCHAR(255);
ALTER TABLE baglamalar ADD COLUMN IF NOT EXISTS tc_kimlik     VARCHAR(20);

ALTER TABLE izinler ADD COLUMN IF NOT EXISTS imza TEXT;
ALTER TABLE izinler ADD COLUMN IF NOT EXISTS ik_imza TEXT;
ALTER TABLE izinler ADD COLUMN IF NOT EXISTS mudur_imza TEXT;
ALTER TABLE izinler ADD COLUMN IF NOT EXISTS yk_imza TEXT;
ALTER TABLE izinler ADD COLUMN IF NOT EXISTS rapor_url TEXT;
ALTER TABLE izinler ADD COLUMN IF NOT EXISTS bakiye_dusuldu BOOLEAN DEFAULT FALSE;
ALTER TABLE sms_kodlari ADD COLUMN IF NOT EXISTS verified_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS satin_alma (
    id           SERIAL PRIMARY KEY,
    sayi         VARCHAR(100),
    konu         TEXT NOT NULL,
    tur          VARCHAR(50) DEFAULT 'dogrudan_temin',
    durum        VARCHAR(50) DEFAULT 'hazirlaniyor',
    tarih        DATE DEFAULT CURRENT_DATE,
    aciklama     TEXT,
    olusturan_ad VARCHAR(200),
    created_at   TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS satin_alma_kalemler (
    id             SERIAL PRIMARY KEY,
    satin_alma_id  INT REFERENCES satin_alma(id) ON DELETE CASCADE,
    sira           INT DEFAULT 1,
    ad             TEXT NOT NULL,
    miktar         NUMERIC DEFAULT 1,
    birim          VARCHAR(50) DEFAULT 'Adet',
    fiyat1         NUMERIC,
    fiyat2         NUMERIC,
    fiyat3         NUMERIC,
    fiyat4         NUMERIC
);

CREATE TABLE IF NOT EXISTS satin_alma_firmalar (
    id             SERIAL PRIMARY KEY,
    satin_alma_id  INT REFERENCES satin_alma(id) ON DELETE CASCADE,
    sira           INT DEFAULT 1,
    firma_adi      VARCHAR(300)
);

CREATE TABLE IF NOT EXISTS satin_alma_komisyon (
    id             SERIAL PRIMARY KEY,
    satin_alma_id  INT REFERENCES satin_alma(id) ON DELETE CASCADE,
    komisyon_turu  VARCHAR(100),
    gorev          VARCHAR(50) DEFAULT 'uye',
    ad_soyad       VARCHAR(200),
    unvan          VARCHAR(200)
);

CREATE TABLE IF NOT EXISTS ihtiyac_talebi (
    id                    SERIAL PRIMARY KEY,
    konu                  TEXT NOT NULL,
    talep_eden            TEXT NOT NULL,
    talep_eden_id         INT REFERENCES personel(id) ON DELETE SET NULL,
    lokasyonlar           TEXT DEFAULT '[]',
    diger_lokasyon        TEXT,
    aciklama              TEXT,
    durum                 VARCHAR(50) DEFAULT 'beklemede',
    gm_onay_ad            VARCHAR(200),
    gm_onay_tarih         TIMESTAMP,
    yk_onay_ad            VARCHAR(200),
    yk_onay_tarih         TIMESTAMP,
    satin_alma_id         INT REFERENCES satin_alma(id) ON DELETE SET NULL,
    olusturan_id          INT,
    olusturan_ad          VARCHAR(200),
    created_at            TIMESTAMP DEFAULT NOW(),
    updated_at            TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ihtiyac_talebi_kalemler (
    id         SERIAL PRIMARY KEY,
    talep_id   INT REFERENCES ihtiyac_talebi(id) ON DELETE CASCADE,
    sira       INT DEFAULT 1,
    ad         TEXT NOT NULL,
    miktar     NUMERIC DEFAULT 1,
    birim      VARCHAR(50) DEFAULT 'Adet',
    aciklama   TEXT
);

ALTER TABLE satin_alma ADD COLUMN IF NOT EXISTS ihtiyac_talep_id INT REFERENCES ihtiyac_talebi(id) ON DELETE SET NULL;

CREATE TABLE IF NOT EXISTS ihtiyac_talebi_dosyalar (
    id           SERIAL PRIMARY KEY,
    talep_id     INT REFERENCES ihtiyac_talebi(id) ON DELETE CASCADE,
    dosya_adi    VARCHAR(255) NOT NULL,
    dosya_yolu   TEXT NOT NULL,
    dosya_boyut  BIGINT,
    mime_type    VARCHAR(100),
    yukleyen_ad  VARCHAR(200),
    created_at   TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sms_kodlari (
    id SERIAL PRIMARY KEY,
    tc_kimlik VARCHAR(11) NOT NULL,
    kod VARCHAR(10) NOT NULL,
    personel_id INT NOT NULL,
    ad_soyad VARCHAR(200),
    bolum VARCHAR(200),
    unvan VARCHAR(200),
    ilce VARCHAR(200),
    attempts INT DEFAULT 0,
    verified BOOLEAN DEFAULT FALSE,
    sms_token VARCHAR(36),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    verified_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_sms_kodlari_tc ON sms_kodlari(tc_kimlik);

CREATE TABLE IF NOT EXISTS personel_evraklari (
    id           SERIAL PRIMARY KEY,
    personel_id  INT REFERENCES personel(id) ON DELETE CASCADE NOT NULL,
    evrak_adi    VARCHAR(255) NOT NULL,
    dosya_adi    VARCHAR(255) NOT NULL,
    dosya_yolu   TEXT NOT NULL,
    dosya_boyut  BIGINT,
    mime_type    VARCHAR(100),
    yuklendi_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ozgecmis_isyeri (
    id           SERIAL PRIMARY KEY,
    personel_id  INT REFERENCES personel(id) ON DELETE CASCADE NOT NULL,
    isyeri_adi   VARCHAR(255) NOT NULL,
    pozisyon     VARCHAR(255),
    baslangic    DATE,
    bitis        DATE,
    aciklama     TEXT,
    olusturuldu  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ozgecmis_okul (
    id           SERIAL PRIMARY KEY,
    personel_id  INT REFERENCES personel(id) ON DELETE CASCADE NOT NULL,
    okul_adi     VARCHAR(255) NOT NULL,
    bolum        VARCHAR(255),
    derece       VARCHAR(100),
    mezuniyet_yili INT,
    aciklama     TEXT,
    olusturuldu  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ozgecmis_sertifika (
    id           SERIAL PRIMARY KEY,
    personel_id  INT REFERENCES personel(id) ON DELETE CASCADE NOT NULL,
    sertifika_adi VARCHAR(255) NOT NULL,
    kurum        VARCHAR(255),
    tarih        DATE,
    gecerlilik   DATE,
    aciklama     TEXT,
    olusturuldu  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS yk_baskan_vekili (
    id           SERIAL PRIMARY KEY,
    personel_id  INT REFERENCES personel(id) ON DELETE CASCADE NOT NULL UNIQUE,
    olusturuldu  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS genel_mudur_vekili (
    id           SERIAL PRIMARY KEY,
    personel_id  INT REFERENCES personel(id) ON DELETE CASCADE NOT NULL UNIQUE,
    olusturuldu  TIMESTAMPTZ DEFAULT NOW()
);
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(CREATE_TABLES_SQL)
        await conn.execute(MIGRATE_SQL)
    yield
    await close_pool()


app = FastAPI(title="muttas-ik-api", lifespan=lifespan)

app.add_middleware(CSPMiddleware)
app.add_middleware(RateLimitMiddleware)

ALLOWED_ORIGINS = [
    "https://ik.muttas.com.tr",
    "http://ik.muttas.com.tr",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth_router)
app.include_router(gunluk_router)
app.include_router(basvurular_router)
app.include_router(dashboard_router)
app.include_router(tekneler_router)
app.include_router(faturalar_router)
app.include_router(self_servis_router)
app.include_router(personel_router)
app.include_router(izinler_router)
app.include_router(vekalet_router)
app.include_router(pdks_router)
app.include_router(ayarlar_router)
app.include_router(satin_alma_router)
app.include_router(ihtiyac_talebi_router)


@app.get("/")
def root():
    return FileResponse("static/index.html")


@app.get("/basvuru")
def basvuru_sayfasi():
    return FileResponse("static/basvuru.html")


@app.get("/izin-basvuru")
def izin_basvuru_sayfasi():
    return FileResponse(
        "static/izin-basvuru.html",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        }
    )


@app.get("/basvuru/{token}")
def basvuru_takip(token: str):
    return FileResponse("static/basvuru.html")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.api_route("/setup-db", methods=["GET", "POST"])
async def setup_db(token: dict = Depends(require_admin)):
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(CREATE_TABLES_SQL)
        return {
            "status": "ok",
            "message": "Tüm tablolar başarıyla oluşturuldu.",
            "tables": [
                "limanlar",
                "kullanicilar",
                "tekneler",
                "baglamalar",
                "tekne_evraklari",
                "liman_gunlugu",
                "gunluk_ozet",
                "faturalar",
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/public/resmi-tatiller")
async def public_resmi_tatiller():
    """Auth gerektirmeyen resmi tatil listesi — izin başvuru formu için."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT tarih::text, gun::float FROM resmi_tatiller ORDER BY tarih"
            )
            return [{"tarih": r["tarih"][:10], "gun": r["gun"]} for r in rows]
    except Exception as e:
        return []


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5000,
        reload=True,
        reload_excludes=["mobile/*", "mobile/node_modules/*"],
    )
