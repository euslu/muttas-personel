import csv
import io
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware

import bcrypt

from db import get_pool, close_pool
from auth import router as auth_router
from personel import router as personel_router
from izinler import router as izinler_router
from self_servis import router as self_servis_router


class CSPMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self' 'unsafe-inline' 'unsafe-eval' "
            "https://fonts.googleapis.com https://fonts.gstatic.com; "
            "img-src 'self' data:"
        )
        return response


CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS kullanicilar (
    id            SERIAL PRIMARY KEY,
    ad            VARCHAR(100) NOT NULL,
    soyad         VARCHAR(100) NOT NULL,
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    telefon       VARCHAR(30),
    rol           VARCHAR(50) DEFAULT 'kullanici',
    aktif         BOOLEAN DEFAULT TRUE,
    olusturuldu   TIMESTAMPTZ DEFAULT NOW()
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
    imza               TEXT,
    olusturuldu        TIMESTAMPTZ DEFAULT NOW()
);

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
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(CREATE_TABLES_SQL)
            exists = await conn.fetchval("SELECT id FROM kullanicilar LIMIT 1")
            if not exists:
                pw_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
                await conn.execute(
                    """INSERT INTO kullanicilar (ad, soyad, email, password_hash, rol)
                       VALUES ('Admin', 'Kullanıcı', 'admin@liman.com', $1, 'admin')
                       ON CONFLICT (email) DO NOTHING""",
                    pw_hash,
                )
                print("[INFO] Varsayılan admin kullanıcısı oluşturuldu.")
    except Exception as e:
        print(f"[WARN] Startup DB init skipped: {e}")
    yield
    await close_pool()


app = FastAPI(title="muttas-personel-api", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CSPMiddleware)

app.mount("/static",  StaticFiles(directory="static"),  name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(auth_router)
app.include_router(personel_router)
app.include_router(izinler_router)
app.include_router(self_servis_router)


@app.post("/admin/seed-personel")
async def seed_personel(anahtar: str = ""):
    if anahtar != os.environ.get("JWT_SECRET", ""):
        raise HTTPException(status_code=403, detail="Yetkisiz.")

    csv_path = "personel_export.csv"
    if not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail="personel_export.csv bulunamadı.")

    pool = await get_pool()
    async with pool.acquire() as conn:
        mevcut = await conn.fetchval("SELECT COUNT(*) FROM personel")
        if mevcut > 0:
            return {"mesaj": f"Personel tablosu zaten dolu ({mevcut} kayıt). İşlem yapılmadı."}

        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        def _v(row, key):
            val = row.get(key, "")
            return val if val not in ("", "None", "\\N") else None

        kayit = 0
        for row in rows:
            await conn.execute("""
                INSERT INTO personel
                    (id, tc_kimlik, sgk_sicil, maliyet_merkezi, ilce, hizmet_noktasi,
                     ad_soyad, cinsiyet, bolum, unvan, ise_giris, isten_cikis,
                     cikis_kodu, guvenlik_belge_tarih, sigortalilik_baslama, hizmet_gun,
                     ogrenim, mezun_bolum, brut_ucret, dogum_yeri, dogum_tarihi,
                     sendika_uyesi, kan_grubu, medeni_hal, cocuk_sayisi, engelli,
                     adres, telefon, meslek_kodu, meslek_adi, notlar, aktif)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,
                        $17,$18,$19,$20,$21,$22,$23,$24,$25,$26,$27,$28,$29,$30,$31,$32)
                ON CONFLICT (id) DO NOTHING
            """,
                int(row["id"]),
                _v(row,"tc_kimlik"), _v(row,"sgk_sicil"), _v(row,"maliyet_merkezi"),
                _v(row,"ilce"), _v(row,"hizmet_noktasi"), row["ad_soyad"],
                _v(row,"cinsiyet"), _v(row,"bolum"), _v(row,"unvan"),
                _v(row,"ise_giris"), _v(row,"isten_cikis"), _v(row,"cikis_kodu"),
                _v(row,"guvenlik_belge_tarih"), _v(row,"sigortalilik_baslama"),
                int(row["hizmet_gun"]) if _v(row,"hizmet_gun") else None,
                _v(row,"ogrenim"), _v(row,"mezun_bolum"),
                float(row["brut_ucret"]) if _v(row,"brut_ucret") else None,
                _v(row,"dogum_yeri"), _v(row,"dogum_tarihi"),
                _v(row,"sendika_uyesi"), _v(row,"kan_grubu"), _v(row,"medeni_hal"),
                int(row["cocuk_sayisi"]) if _v(row,"cocuk_sayisi") else 0,
                row["engelli"].lower() == "t",
                _v(row,"adres"), _v(row,"telefon"),
                _v(row,"meslek_kodu"), _v(row,"meslek_adi"), _v(row,"notlar"),
                row["aktif"].lower() == "t",
            )
            kayit += 1

        await conn.execute("SELECT setval('personel_id_seq', (SELECT MAX(id) FROM personel))")

    return {"mesaj": f"{kayit} personel kaydı başarıyla aktarıldı."}


@app.get("/")
@app.get("/login.html")
def root():
    return FileResponse("static/login.html")

@app.get("/dashboard")
@app.get("/dashboard.html")
def dashboard():
    return FileResponse("static/dashboard.html")

@app.get("/izin-basvuru")
def izin_basvuru():
    return FileResponse("static/izin-basvuru.html")

@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("personel_app:app", host="0.0.0.0", port=8000, reload=True)
