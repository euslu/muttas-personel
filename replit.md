# muttas-liman-api

Marina ve İnsan Kaynakları yönetim sistemi — Python FastAPI + PostgreSQL.

## Stack
- **Backend:** Python 3.11, FastAPI, asyncpg, python-jose, bcrypt
- **Frontend:** Vanilla HTML/CSS/JS (static/dashboard.html, static/login.html)
- **Database:** PostgreSQL (Replit managed)
- **Auth:** JWT token (localStorage), Bearer header
- **Port:** 5000 (Replit), 8000 (DO production)

## Dosya Yapısı
```
personel_app.py   - FastAPI app, CORS, CSP middleware, tablo oluşturma
main.py           - uvicorn runner (personel_app import)
db.py             - asyncpg connection pool
auth.py           - /auth/login, /auth/me, kullanıcı yönetimi
personel.py       - /personel CRUD + evraklar + foto upload
izinler.py        - /izinler CRUD + onay akışı
permissions.py    - JWT decode, role guards (require_ik_editor vb.)
static/
  login.html      - JWT login formu (TC kimlik ile giriş)
  dashboard.html  - Ana panel (sidebar + tüm sayfalar)
  personel_detay.html - Personel detay sayfası (standalone, artık dashboard içinde inline açılır)
  logo.png        - Muttaş logosu
  izin-basvuru.html - Self-servis izin başvuru formu (5 adımlı: Kimlik → SMS Doğrulama → İzin Formu → İmza → Onay)
uploads/
  personel/       - Personel evrakları
  foto/           - Personel profil fotoğrafları
```

## Veritabanı Tabloları
- `limanlar` — Marina/liman kayıtları
- `kullanicilar` — Kullanıcılar (admin/ik_admin/liman_admin), password_hash
- `personel` — Personel kayıtları (~964 kişi, Google Sheets'ten aktarıldı)
  - foto_url alanı: profil fotoğrafı yolu
- `personel_evraklari` — Personel belge/evrakları
- `izinler` — İzin talepleri (onay akışı: beklemede → ik_onayladi → mudur_onayladi → onaylandi → tamamlandi)
- `tekneler` — Tekne kayıtları
- `baglamalar` — Bağlama başvuruları
- `gunluk` — Liman günlük log girişleri

## Rol Yapısı
- `admin` — Tüm modüllere erişim (liman + İK)
- `ik_admin` — Sadece İK modülleri (personel + izin)
- `liman_admin` / `liman_viewer` — Sadece liman modülleri

## Kullanıcılar
- UĞUR YAKA: TC 66292029624, rol: ik_admin
- SEDAT BAYRAK: TC 50668716706, rol: admin
- Şifre: Muttas2026!

## Personel Detay Sayfası
- Drawer yerine ayrı pencerede açılır (personel_detay.html)
- Profil fotoğrafı: yuvarlak avatar, yüklenebilir (/personel/{id}/foto)
- Sekmeler: Kişisel Bilgiler, Görev Bilgileri, İletişim, Evraklar
- Yerinde düzenleme: "Düzenle" butonu ile form moduna geçiş
- Yazdırma desteği
- Combobox alanları (bölüm, ünvan, maliyet merkezi, hizmet noktası, ilçe, meslek, çıkış kodu)

## Production (DigitalOcean)
- IP: 209.38.219.210
- Gunicorn port 8000, 4 workers, systemd service "muttas"
- PostgreSQL local (sudo -u postgres psql -d muttas_db)
- SSH: sshpass -p '5Ec9f39fd0*-E' ssh root@209.38.219.210

## SMS Doğrulama Sistemi
- İzin başvuru formunda TC girişi sonrası SMS doğrulama adımı eklendi
- Backend: `/public/sms-gonder` (kod gönderir), `/public/sms-dogrula` (kodu doğrular, sms_token döner)
- sms_token izin başvurusu yapılırken `/public/izin` endpoint'ine gönderilir
- SMS API henüz yapılandırılmadı (SMS_API_URL, SMS_API_KEY, SMS_API_SECRET env vars); API yokken kodlar sunucu loguna yazılır
- Kod süresi: 5 dakika, max 5 deneme hakkı, 60 sn tekrar gönderim bekleme

## Notlar
- Login TC kimlik numarası ile yapılır (email alanı TC olarak kullanılır)
- Bcrypt hash'leri SSH ile aktarırken $ karakteri sorun çıkarır — heredoc SQL dosyaları kullan
- `baglamalar.notlar` formatı: "Referans: REFNO | Sahip: AD"
