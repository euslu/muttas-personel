import asyncio
import csv
import os
import bcrypt

DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    env = {}
    if os.path.exists(".env"):
        with open(".env") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    DATABASE_URL = env.get("DATABASE_URL", "")

if not DATABASE_URL:
    print("HATA: DATABASE_URL bulunamadı. .env dosyasını kontrol edin.")
    exit(1)

import asyncpg

SCHEMA = """
CREATE TABLE IF NOT EXISTS personel (
    id SERIAL PRIMARY KEY,
    tc_kimlik VARCHAR(11),
    sgk_sicil VARCHAR(50),
    maliyet_merkezi VARCHAR(100),
    ilce VARCHAR(100),
    hizmet_noktasi VARCHAR(200),
    ad_soyad VARCHAR(200) NOT NULL,
    cinsiyet VARCHAR(10),
    bolum VARCHAR(100),
    unvan VARCHAR(100),
    ise_giris DATE,
    isten_cikis DATE,
    cikis_kodu VARCHAR(50),
    guvenlik_belge_tarih DATE,
    sigortalilik_baslama DATE,
    hizmet_gun INTEGER,
    ogrenim VARCHAR(50),
    mezun_bolum VARCHAR(100),
    brut_ucret NUMERIC(12,2),
    dogum_yeri VARCHAR(100),
    dogum_tarihi DATE,
    sendika_uyesi VARCHAR(50),
    kan_grubu VARCHAR(10),
    medeni_hal VARCHAR(20),
    cocuk_sayisi INTEGER DEFAULT 0,
    engelli BOOLEAN DEFAULT FALSE,
    adres TEXT,
    telefon VARCHAR(30),
    meslek_kodu VARCHAR(50),
    meslek_adi VARCHAR(100),
    notlar TEXT,
    aktif BOOLEAN DEFAULT TRUE,
    olusturuldu TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS kullanicilar (
    id SERIAL PRIMARY KEY,
    ad VARCHAR(100) NOT NULL,
    soyad VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    telefon VARCHAR(30),
    rol VARCHAR(50) DEFAULT 'kullanici',
    aktif BOOLEAN DEFAULT TRUE,
    olusturuldu TIMESTAMPTZ DEFAULT NOW(),
    password_hash VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS izinler (
    id SERIAL PRIMARY KEY,
    personel_id INTEGER NOT NULL REFERENCES personel(id) ON DELETE CASCADE,
    talep_tarihi DATE DEFAULT CURRENT_DATE NOT NULL,
    izin_turu VARCHAR(50) NOT NULL,
    baslangic DATE NOT NULL,
    bitis DATE NOT NULL,
    gun_sayisi INTEGER NOT NULL,
    kullanilabilir_gun INTEGER,
    vekil_ad_soyad VARCHAR(200),
    izin_adresi TEXT,
    durum VARCHAR(30) DEFAULT 'beklemede',
    ik_onay_tarihi DATE,
    ik_onaylayan VARCHAR(200),
    mudur_onay_tarihi DATE,
    yk_onay_tarihi DATE,
    gorev_baslama DATE,
    notlar TEXT,
    olusturuldu TIMESTAMPTZ DEFAULT NOW(),
    imza TEXT
);

CREATE TABLE IF NOT EXISTS personel_evraklari (
    id SERIAL PRIMARY KEY,
    personel_id INTEGER NOT NULL REFERENCES personel(id) ON DELETE CASCADE,
    belge_turu VARCHAR(100),
    dosya_adi VARCHAR(255),
    dosya_yolu TEXT,
    notlar TEXT,
    yuklendi_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pdks_cihazlar (
    id SERIAL PRIMARY KEY,
    cihaz_no INTEGER UNIQUE NOT NULL,
    cihaz_adi VARCHAR(100) NOT NULL,
    konum VARCHAR(200),
    aktif BOOLEAN DEFAULT TRUE,
    olusturuldu TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pdks_hareketler (
    id SERIAL PRIMARY KEY,
    cihaz_no INTEGER NOT NULL,
    personel_no VARCHAR(20) NOT NULL,
    giris_cikis SMALLINT NOT NULL,
    zaman TIMESTAMPTZ NOT NULL,
    ham_veri TEXT,
    yukleme_zamani TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (cihaz_no, personel_no, zaman)
);
CREATE INDEX IF NOT EXISTS idx_pdks_zaman ON pdks_hareketler (zaman DESC);
CREATE INDEX IF NOT EXISTS idx_pdks_personel ON pdks_hareketler (personel_no);
"""

async def main():
    print(f"Veritabanına bağlanılıyor...")
    conn = await asyncpg.connect(DATABASE_URL)

    print("Tablolar oluşturuluyor...")
    await conn.execute(SCHEMA)
    print("Tablolar OK.")

    count = await conn.fetchval("SELECT COUNT(*) FROM personel")
    if count > 0:
        print(f"Personel tablosu zaten dolu ({count} kayıt). Veri aktarımı atlandı.")
    else:
        csv_path = "personel_export.csv"
        if not os.path.exists(csv_path):
            print("HATA: personel_export.csv bulunamadı.")
        else:
            print("Personel verisi aktarılıyor...")
            with open(csv_path, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))

            def v(row, key):
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
                    v(row,"tc_kimlik"), v(row,"sgk_sicil"), v(row,"maliyet_merkezi"),
                    v(row,"ilce"), v(row,"hizmet_noktasi"), row["ad_soyad"],
                    v(row,"cinsiyet"), v(row,"bolum"), v(row,"unvan"),
                    v(row,"ise_giris"), v(row,"isten_cikis"), v(row,"cikis_kodu"),
                    v(row,"guvenlik_belge_tarih"), v(row,"sigortalilik_baslama"),
                    int(row["hizmet_gun"]) if v(row,"hizmet_gun") else None,
                    v(row,"ogrenim"), v(row,"mezun_bolum"),
                    float(row["brut_ucret"]) if v(row,"brut_ucret") else None,
                    v(row,"dogum_yeri"), v(row,"dogum_tarihi"),
                    v(row,"sendika_uyesi"), v(row,"kan_grubu"), v(row,"medeni_hal"),
                    int(row["cocuk_sayisi"]) if v(row,"cocuk_sayisi") else 0,
                    row["engelli"].lower() == "t",
                    v(row,"adres"), v(row,"telefon"),
                    v(row,"meslek_kodu"), v(row,"meslek_adi"), v(row,"notlar"),
                    row["aktif"].lower() == "t",
                )
                kayit += 1

            await conn.execute("SELECT setval('personel_id_seq', (SELECT MAX(id) FROM personel))")
            print(f"{kayit} personel kaydı aktarıldı.")

    admin = await conn.fetchval("SELECT COUNT(*) FROM kullanicilar WHERE email = 'admin@liman.com'")
    if admin == 0:
        pw = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
        await conn.execute("""
            INSERT INTO kullanicilar (ad, soyad, email, rol, password_hash)
            VALUES ('Admin', 'Kullanici', 'admin@liman.com', 'admin', $1)
        """, pw)
        print("Admin kullanıcı oluşturuldu: admin@liman.com / admin123")
    else:
        print("Admin kullanıcı zaten var.")

    await conn.close()
    print("\nKurulum tamamlandı.")

asyncio.run(main())
