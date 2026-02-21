from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware
from db import get_pool, close_pool
from auth import router as auth_router
from gunluk import router as gunluk_router


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
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
    yield
    await close_pool()


app = FastAPI(title="muttas-liman-api", lifespan=lifespan)

app.add_middleware(CSPMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth_router)
app.include_router(gunluk_router)


@app.get("/")
def root():
    return FileResponse("static/index.html")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.api_route("/setup-db", methods=["GET", "POST"])
async def setup_db():
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
