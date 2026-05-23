# Muttaş İK & Liman Yönetim Sistemi — Proje Bağlamı

## Genel Bakış

FastAPI tabanlı bir insan kaynakları ve liman yönetim sistemi.
Canlı: **https://ik.muttas.com.tr** (sunucu: 185.123.103.61)

---

## Teknoloji Yığını

| Katman | Teknoloji |
|--------|-----------|
| Backend | Python 3.11, FastAPI, asyncpg |
| Veritabanı | PostgreSQL (production: localhost:5432/muttas_db) |
| Auth | JWT (python-jose), bcrypt şifre hash |
| Frontend | Vanilla HTML/CSS/JS (tek sayfa uygulama — dashboard.html) |
| Sunucu | Gunicorn + UvicornWorker, 4 worker, port 8000 |
| Ters Proxy | Nginx + Let's Encrypt SSL |
| Mobil | Expo + React Native (mobile/ klasörü) |

---

## Dosya Yapısı

```
main.py                  — FastAPI app, tüm router'lar, CREATE/MIGRATE SQL, middleware
personel_app.py          — Eski app dosyası (hâlâ bazı tablolar burada)
db.py                    — asyncpg bağlantı havuzu (DATABASE_URL veya DB_* env vars)
permissions.py           — JWT decode, rol guard'ları
auth.py                  — /auth/ endpointleri, JWT üretimi (48 saat), şifre işlemleri
personel.py              — /personel CRUD, evrak yükleme, fotoğraf, özgeçmiş
izinler.py               — /izinler CRUD, onay akışı, log, SMS entegrasyonu
ayarlar.py               — /ayarlar/* (çalışma günleri, unvanlar, KS atama, tatiller...)
self_servis.py           — /public/* endpointleri (SMS doğrulama, izin başvurusu)
satin_alma.py            — /satin-alma CRUD + kalemler/firmalar/komisyon
ihtiyac_talebi.py        — /ihtiyac-talebi CRUD + onay akışı + dosya yükleme
dashboard.py             — /dashboard/ik-ozet özet istatistikleri
vekalet.py               — /vekaletler yönetimi
pdks.py / pdks_agent.py  — PDKS (giriş/çıkış) hareketleri
gunluk.py                — /gunluk liman log kayıtları
basvurular.py            — /public/basvuru tekne bağlama başvuruları
tekneler.py              — /tekneler CRUD
faturalar.py             — /faturalar CRUD

static/
  dashboard.html         — Ana panel (~11.300 satır, tüm modüller tek dosyada)
  login.html             — JWT login formu (TC kimlik ile giriş)
  izin-basvuru.html      — Self-servis izin başvurusu (5 adımlı: TC→SMS→Form→İmza→Onay)
  personel_detay.html    — Personel detay (artık dashboard içinde inline açılıyor)
  logo.png               — Muttaş logosu

uploads/
  personel/              — Personel evrakları
  foto/                  — Personel profil fotoğrafları

mobile/                  — Expo React Native mobil uygulama
```

---

## Veritabanı Tabloları (38 adet)

### Kullanıcı & Auth
| Tablo | Açıklama |
|-------|----------|
| `kullanicilar` | Sistem kullanıcıları — `email`=TC kimlik, `password_hash`=bcrypt, `rol`, `sifre_degistir_gerekli` BOOLEAN |

### İK Modülü
| Tablo | Açıklama |
|-------|----------|
| `personel` | ~964 personel kaydı (Google Sheets'ten aktarıldı) |
| `personel_evraklari` | `evrak_adi`, `dosya_adi`, `dosya_yolu`, `dosya_boyut`, `mime_type` |
| `izinler` | İzin talepleri — `durum`: beklemede→ik_onayladi→mudur_onayladi→onaylandi→tamamlandi |
| `izin_gecmisi` | Excel'den aktarılan 7824 geçmiş izin kaydı |
| `izin_log` | İzin durum değişiklik logları |
| `izin_turleri` | İzin türleri (yıllık, ücretsiz vb.) |
| `sms_kodlari` | SMS doğrulama kodları (Gunicorn multi-worker için DB'de) |
| `ozgecmis_isyeri` | Personel iş geçmişi |
| `ozgecmis_okul` | Personel eğitim geçmişi |
| `ozgecmis_sertifika` | Personel sertifikaları |

### Ayarlar
| Tablo | Açıklama |
|-------|----------|
| `unvan_calisma_gunu` | Unvana göre çalışma günü (5 veya 6) — owner: postgres |
| `yonetici_unvanlar` | Yönetici unvan listesi — owner: postgres |
| `ks_personel_atama` | Koordinasyon Sorumlusu atamaları — owner: postgres |
| `resmi_tatiller` | Resmi tatil takvimi |
| `yk_baskan_vekili` | YK Başkan Vekili listesi |
| `genel_mudur_vekili` | Genel Müdür Vekili listesi |
| `yk_uye_unvanlar` | YK üye unvanları |
| `yk_uye_personel` | YK üye personel listesi |
| `vekaletler` | Vekalet tanımlamaları |

### Satın Alma & İhtiyaç
| Tablo | Açıklama |
|-------|----------|
| `satin_alma` | Satın alma süreçleri |
| `satin_alma_kalemler` | Satın alma kalemleri (4 fiyat sütunu) |
| `satin_alma_firmalar` | Teklif veren firmalar |
| `satin_alma_komisyon` | Komisyon üyeleri |
| `ihtiyac_talebi` | İhtiyaç talepleri — onay akışı: beklemede→gm_onayladi→yk_onayladi |
| `ihtiyac_talebi_kalemler` | Talep kalemleri |
| `ihtiyac_talebi_dosyalar` | Talep ekleri |

### PDKS
| Tablo | Açıklama |
|-------|----------|
| `pdks_cihazlar` | PDKS okuyucu cihazlar |
| `pdks_hareketler` | Giriş/çıkış kayıtları |

### Liman Modülü
| Tablo | Açıklama |
|-------|----------|
| `limanlar` | Marina/liman kayıtları |
| `tekneler` | Tekne kayıtları |
| `baglamalar` | Tekne bağlama başvuruları |
| `belgeler` | Bağlama belgeleri |
| `tekne_evraklari` | Tekne evrakları |
| `gunluk_kayitlar` | Liman günlük log girişleri |
| `gunluk_ozet` | Liman günlük özet istatistikleri |
| `liman_gunlugu` | Eski liman log tablosu |
| `faturalar` | Liman faturaları |

---

## Auth & Roller

### Giriş
- `email` alanı TC kimlik numarası olarak kullanılır
- JWT token: 48 saat geçerli
- `Authorization: Bearer <token>` header'ı

### Rol Yapısı
| Rol | Erişim |
|-----|--------|
| `admin` | Her şey (liman + İK + ayarlar + kullanıcı yönetimi) |
| `ik_admin` | Personel + İzin + Ayarlar |
| `genel_mudur` | İK modülleri + özel onay yetkisi |
| `mudur` | İzin onay (kendi ekibi) |
| `koordinasyon_sorumlusu` | İzin onay (KS katmanı) |
| `yk_uyesi` / `yk_baskani` | YK onay |
| `liman_admin` | Sadece liman modülleri |
| `liman_viewer` | Liman okuma |

### Güvenlik Grupları (permissions.py)
```python
IK_EDITORS     = {"admin", "ik_admin", "genel_mudur"}
IZIN_EDITORS   = IK_EDITORS | {"koordinasyon_sorumlusu", "mudur"}
LIMAN_EDITORS  = {"admin", "liman_admin"}
```

### Özel Şifre Kuralları
- `SIFRE_SIFIRLAMA_ROLLER = {"koordinasyon_sorumlusu", "mudur", "genel_mudur"}`
- Bu rollere atanan kullanıcının şifresi `Muttas2026!` olur, `sifre_degistir_gerekli = TRUE` set edilir
- İlk girişte yeni şifre zorunlu — eski şifre tekrar kullanılamaz, min 8 karakter
- kullanicilar tablosunda `sifre_degistir_gerekli BOOLEAN` kolonu var

---

## API Endpoint Özeti

### /auth/
| Method | Path | Açıklama |
|--------|------|----------|
| POST | /auth/login | TC + şifre ile giriş → token |
| POST | /auth/register | Yeni kullanıcı (require_admin) |
| GET | /auth/kullanicilar | Kullanıcı listesi (require_admin) |
| PUT | /auth/kullanicilar/{id}/rol | Rol güncelle (require_admin) |
| DELETE | /auth/kullanicilar/{id} | Kullanıcı sil (require_admin) |
| PUT | /auth/sifre-degistir | Şifre değiştir |

### /personel/
| Method | Path | Açıklama |
|--------|------|----------|
| GET | /personel | Liste (filtreli, sayfalı) |
| GET | /personel/meta | Combobox verileri (bölüm, unvan vb.) |
| GET | /personel/{id} | Tek personel |
| POST | /personel | Yeni personel (require_ik_editor) |
| PUT | /personel/{id} | Güncelle (require_ik_editor) |
| DELETE | /personel/{id} | Sil (require_ik_editor) |
| GET | /personel/{id}/evraklar | Evrak listesi |
| POST | /personel/{id}/evraklar | Evrak yükle |
| GET | /personel/evrak/{id}/indir | Evrak indir |
| DELETE | /personel/evrak/{id} | Evrak sil |
| POST | /personel/{id}/foto | Profil fotoğrafı yükle |
| GET/POST/DELETE | /personel/{id}/isyeri,okul,sertifika | Özgeçmiş CRUD |

### /izinler/
| Method | Path | Açıklama |
|--------|------|----------|
| GET | /izinler | Liste (filtreli, sayfalı) |
| GET | /izinler/ozet | İzin özet istatistikleri |
| GET | /izinler/{id} | Tek izin |
| POST | /izinler | Yeni izin (require_izin_editor) |
| PUT | /izinler/{id} | Güncelle |
| PUT | /izinler/{id}/onay | Onay/red işlemi (çok adımlı akış) |
| PUT | /izinler/{id}/ks-onayla | KS onayı |
| POST | /izinler/{id}/rapor | İzin raporu yükle |
| DELETE | /izinler/{id} | Sil |
| GET | /izinler/log/listele | Onay log kayıtları |
| GET | /izinler/personel-izin-gecmisi/{id} | Geçmiş izinler |

### /public/ (Auth gerektirmez)
| Method | Path | Açıklama |
|--------|------|----------|
| GET | /public/limanlar | Liman listesi |
| POST | /public/basvuru | Bağlama başvurusu oluştur |
| GET | /public/basvuru/{token} | Başvuru sorgula |
| POST | /public/sms-gonder | SMS kodu gönder |
| POST | /public/sms-dogrula | SMS kodu doğrula → sms_token |
| GET | /public/personel/ara | TC ile personel ara (sms_token gerekli) |
| POST | /public/izin | Self-servis izin başvurusu |

### /ayarlar/
`GET /calisma-gunleri`, `PUT /calisma-gunleri`, `GET/POST/DELETE /yonetici-unvanlar`,
`GET /ks-listesi`, `GET/POST/DELETE /ks-atama`, `GET /personel-havuzu`,
`GET/POST/PUT/DELETE /resmi-tatiller`, `GET/POST/DELETE /yk-baskan-vekili`,
`GET/POST/DELETE /genel-mudur-vekili`, `GET/POST/DELETE /izin-turleri`

### /satin-alma/
`GET/POST /`, `GET/PUT/DELETE /{id}`,
`PUT /{id}/kalemler`, `PUT /{id}/firmalar`, `PUT /{id}/komisyon`

### /ihtiyac-talebi/
`GET/POST /`, `GET/PUT/DELETE /{id}`, `PUT /{id}/kalemler`,
`POST /{id}/gm-onayla`, `POST /{id}/yk-onayla`, `POST /{id}/reddet`,
`POST /{id}/satin-almaya-don`, `GET/POST /{id}/dosyalar`

---

## Frontend: dashboard.html

Tek büyük HTML dosyası (~11.300 satır). Tüm sayfalar `<div class="page" id="page-*">` ile bölümlenmiş, JavaScript ile gösterip gizleniyor.

### Kritik JS Değişkenleri
```javascript
currentUser          // { id, email, rol, ad, soyad, unvan }
UNVAN_CALISMA_GUNU   // { "BAKIM ONARIM SORUMLUSU": 6, ... }  (dict)
YONETICI_UNVANLAR    // ["FİNANS SORUMLUSU", ...]  (array)
IZIN_TURLERI_LISTE   // [{ kod, ad, ... }]
```

### Kritik JS Fonksiyonlar
```javascript
navigate(page, el)      // Sayfa geçişi — loadAyarlar(), loadPersonel() vb. tetikler
getToken()              // localStorage.getItem('token')
authHeaders()           // { Content-Type, Authorization: Bearer ... }
api(url, opts)          // fetch wrapper
showToast(msg, type)    // Bildirim ('success' | 'error' | 'info')
loadAyarlar()           // Ayarlar sayfasını yükler (Promise.all ile paralel)
ayarTabSec(tabId, btn)  // Ayarlar sekme geçişi — her sekme için ayrı load fonksiyonu
```

### Global 401 Interceptor
`window.fetch` override edilmiş — herhangi bir API çağrısı 401 dönerse:
- localStorage temizlenir
- "Oturumunuz sona erdi" toast gösterilir
- 1.8 saniye sonra login.html'e yönlendirilir
- `/auth/` endpoint'leri bu kuraldan muaf

### CSS Değişkenleri
```css
--accent: #4361ee
--bg-soft: #f4f6fa
--border-dark: #d1d5db
--text-2: #6b7280
--text-3: #9ca3af
/* DİKKAT: --bg-2 ve --primary TANIMLI DEĞİL — fallback kullanın */
```

### Ayarlar Sekmesi Yükleme Akışı
```
navigate('ayarlar') → loadAyarlar()
  ├── dashWidgetAyarPanelDoldur()
  ├── Promise.all([loadCalismaGunleri(), loadYoneticiUnvanlar()])   ← cache:'no-store'
  ├── renderIzinKurallariUnvanlar()   ← UNVAN_CALISMA_GUNU'dan tablo çizer
  └── loadIzinTurleri()

ayarTabSec('rol-unvan')    → loadRolUnvanTab()
ayarTabSec('ks-atama')     → ksAtamaYukleKsList()
ayarTabSec('resmi-tatiller') → loadTatiller()
ayarTabSec('yk-bv')        → loadYkBv()
ayarTabSec('gm-vekil')     → loadGmVekil()
ayarTabSec('dashboard')    → dashWidgetAyarPanelDoldur()
```

---

## İzin Onay Akışı

```
Oluşturuldu (beklemede)
  → KS Onayı (ks_onayladi) — koordinasyon_sorumlusu
  → İK Onayı (ik_onayladi) — ik_admin / admin
  → Müdür Onayı (mudur_onayladi) — mudur
  → YK Onayı (yk_onayladi) — yk_uyesi / yk_baskani
  → Onaylandı (onaylandi)
  → Tamamlandı (tamamlandi)
  → Reddedildi (reddedildi) — herhangi bir aşamada
```

İzin onayında imza (base64 PNG) kaydedilir: `imza`, `ik_imza`, `mudur_imza`, `yk_imza`

---

## SMS Doğrulama Sistemi

- Self-servis izin başvurusunda TC girişi sonrası aktif
- DB'de `sms_kodlari` tablosunda saklanır (Gunicorn multi-worker uyumlu)
- Env vars: `SMS_API_URL`, `SMS_API_KEY`, `SMS_API_SECRET`
- API tanımlı değilse kod sunucu loguna yazılır (geliştirme modu)
- Kod süresi: 5 dk, max 5 deneme, 60 sn yeniden gönderim bekleme
- Başarılı doğrulama → `sms_token` (UUID) döner → izin başvurusunda kullanılır

---

## Production Sunucu

| Bilgi | Değer |
|-------|-------|
| IP | 185.123.103.61 |
| Domain | ik.muttas.com.tr |
| Servis | `systemctl status muttas` |
| Proje dizini | /opt/muttas/ |
| DB | postgresql://muttas:***@127.0.0.1:5432/muttas_db |
| Nginx config | /etc/nginx/sites-enabled/ik-muttas |
| SSL | Let's Encrypt (Certbot), otomatik yenileme |
| Workers | Gunicorn, 4 UvicornWorker |

### Deploy Yöntemi
```bash
# Statik dosyalar
sshpass -p 'SIFRE' scp static/dashboard.html srv@185.123.103.61:/opt/muttas/static/

# Python dosyaları
sshpass -p 'SIFRE' scp auth.py srv@185.123.103.61:/opt/muttas/

# Servisi yeniden başlat
sshpass -p 'SIFRE' ssh srv@185.123.103.61 "sudo systemctl restart muttas"
```

---

## Bilinen Önemli Notlar

1. **TC Kimlik = Email**: `kullanicilar.email` alanı TC kimlik numarasıdır
2. **Bcrypt ve `**: SSH ile hash aktarırken ` karakteri sorun yaratır — heredoc SQL dosyası kullan
3. **`--bg-2` tanımsız**: CSS değişkeni yok, fallback ekle: `var(--bg-2, #f0f2f5)`
4. **`--primary` tanımsız**: `var(--accent)` kullan
5. **dashboard.html büyük**: 11.300+ satır, tüm modüller tek dosyada
6. **`unvan_calisma_gunu` owner=postgres**: Bu tabloyu migrate SQL ile değil, doğrudan psql ile oluşturulmuş
7. **`ks_personel_atama` owner=postgres**: Aynı durum
8. **izin_turleri tablosu**: `ayarlar.py` değil, `izinler.py`'deki `get_izin_turleri_db()` fonksiyonu kullanır
9. **Mobil uygulama**: `mobile/` klasörü, Expo Go ile test, production API'ye bağlı
10. **Rate limiting**: `/public/` ve `/auth/login`: 10 req/60sn; global: 120 req/60sn (in-memory, Gunicorn restart'ta sıfırlanır)
11. **`sifre_degistir_gerekli`**: `kullanicilar` tablosunda — login endpoint bu bayrağı döndürür, frontend modal gösterir

---

## Test Kullanıcıları

| Kullanıcı | TC | Rol | Şifre |
|-----------|-----|-----|-------|
| SEDAT BAYRAK | 50668716706 | admin | Muttas2026! (veya değiştirilmiş) |
| UĞUR YAKA | 66292029624 | ik_admin | Muttas2026! (veya değiştirilmiş) |

---

## Mobil Uygulama (mobile/)

- Framework: Expo SDK + React Native
- API: https://ik.muttas.com.tr (production)
- Ekranlar: Login, Ana Sayfa (izin bakiyesi), İzin Talebi (3 adım), İzinlerim, Onaylar, Profil
- Çalıştırma: `cd mobile && npx expo start --port 8081`
- QR kod ile Expo Go uygulamasından test edilir
