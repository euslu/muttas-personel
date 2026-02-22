from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware

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
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(CREATE_TABLES_SQL)
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


@app.get("/")
def root():
    return FileResponse("static/login.html")

@app.get("/dashboard")
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
    uvicorn.run("personel_app:app", host="0.0.0.0", port=5000, reload=True)
