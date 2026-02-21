# muttas-liman-api

Marina yönetim sistemi — Python FastAPI + PostgreSQL.

## Stack
- **Backend:** Python 3.11, FastAPI, asyncpg, python-jose, bcrypt
- **Frontend:** Vanilla HTML/CSS/JS (static/dashboard.html, static/login.html)
- **Database:** PostgreSQL (Replit managed)
- **Auth:** JWT token (localStorage), Bearer header
- **Port:** 8000

## Dosya Yapısı
```
main.py          - FastAPI app, CORS, CSP middleware, tablo oluşturma
db.py            - asyncpg connection pool
auth.py          - /auth/login, /auth/me, kullanıcı yönetimi
gunluk.py        - /gunluk (liman günlüğü CRUD), /limanlar, /tekneler/ara
basvurular.py    - /basvurular (bağlama başvuruları CRUD + export)
dashboard.py     - /dashboard/ozet, /dashboard/gunluk-trafik
static/
  login.html     - JWT login formu
  dashboard.html - Ana panel (sidebar + tüm sayfalar)
```

## Veritabanı Tabloları
- `limanlar` — Marina/liman kayıtları
- `kullanicilar` — Kullanıcılar (admin / görevli), password_hash
- `tekneler` — Tekne kayıtları (ad, tip, uzunluk_m, genislik_m)
- `baglamalar` — Bağlama başvuruları (ref_no, basvuru_sahibi, telefon, sigorta_bitis, odeme_linki)
- `faturalar` — Fatura kayıtları (tutar, kdv, toplam_tutar, durum)
- `gunluk` — Liman günlük log girişleri
- `belgeler` — Belge ekleri (gelecekte)

## Özellikler

### Auth
- JWT token, 12 saat geçerli
- Admin: tüm limanlar görebilir + liman filtresi
- Görevli: sadece kendi limanı

### Liman Günlüğü (/gunluk)
- Tekne adına göre autocomplete (tekneler tablosu)
- Tarih/zaman filtresi, sayfalama
- CRUD (create/read/update/delete)

### Bağlama Başvuruları (/basvurular)
- 1025 gerçek üretim verisi aktarıldı (XLS'den)
- ref_no, basvuru_sahibi, telefon, sigorta_bitis, odeme_linki alanları eklendi
- Filtreler: durum, odeme_durumu, tarih, liman, arama (tekne/ref/sahip)
- Durum sistemi: beklemede, islem_bekliyor, odeme_islemde, manuel_odeme, onaylandi, reddedildi, dosya_yuklenenler
- CSV export: /export/muhasebe, /export/kayitlar
- Sigorta uyarıları: /sigorta-uyarilari (30 gün içinde bitenler)
- Sayfalama: 10/25/50 / sayfa
- Kolaps sidebar sub-menu (10 alt kategori)
- Yeni başvuru oluşturma + düzenleme (drawer panel)

### Dashboard UI
- Fixed 240px sidebar, scrollable main content
- Collapsible sub-menu: ⚓ Bağlama Başvuruları altında 10 filtre kısayolu
- Sütun görünürlük seçici (col picker)
- Durum badge renkleri (7 renk)
- Drawer (sağ panel) form: yeni/düzenle başvuru

## Admin Bilgileri
- Email: admin@liman.com
- Şifre: admin123

## Notlar
- `baglamalar.notlar` formatı: "Referans: REFNO | Sahip: AD"
- Mevcut veriler normalize edildi (aktif → onaylandi)
- durum normalize: 526 onaylandi, 293 beklemede, 206 reddedildi

## Yapılacaklar
- [ ] **Sanal POS entegrasyonu** — Muttaş ödeme yetkilileriyle görüşülecek, ardından faturalar modülüne banka/kart ödeme API'si bağlanacak
