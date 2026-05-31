# Personel Senkronizasyon Migration Paketi

Oluşturulma: 2026-05-31 20:15

## Amaç
Mayıs 2026 SSK personel listesi (971 kişi) ile canlı sistemdeki personel kayıtlarını (970 kayıt) TC kimlik bazlı senkronize etmek.

## Karşılaştırma sonuçları

| Grup | Sayı | Anlamı |
|------|------|--------|
| Sağlıklı | 919 | TC eşleşiyor, DB ve Mayıs tutarlı |
| Adım 1 — TC ekleme | 6 | DB'de TC'siz, Mayıs'tan TC'leri alınacak |
| Adım 2 — İsim güncelleme | 21 | TC aynı, ad farklı (evlilik/yazım) |
| Adım 3 — Yeni personel | 46 | Mayıs'ta var, DB'de yok |
| Adım 4 — Pasifleştirme | 42 | DB'de aktif, Mayıs'ta yok |

## Çalıştırma sırası

### 🟢 1. `01_tc_ekle_isim_normalize.sql` — Düşük risk
- 6 TC'siz DB kaydına TC ekler (ATİYE DİKER, HÜSEYİN USLU vb.)
- Çift boşluklu isimleri normalize eder (MELİH  DEVECİ → MELİH DEVECİ)
- Mayıs listesindeki isim ile DB'deki birebir eşleşmeye dayanır

### 🟡 2. `02_isim_guncelleme.sql` — Orta risk, İK ONAYI GEREKLİ
- 21 kayıtta isim güncellemesi (TC aynı, ad farklı)
- **Önce `02_isim_guncelleme_KONTROL.xlsx` ile İK onayı alın**
- Bazıları soyadı değişikliği (ÖZLEM CAN → ÖZLEM ÇİFTÇİ — evlilik?)
- Bazıları yazım hatası (BUSE → BUĞSE, COŞKUN → ÇOŞKUN)

### 🟢 3. `03_yeni_personel_ekle.sql` — Düşük risk
- 46 yeni personel ekler (Adım 1'den SONRA çalıştırılmalı)
- Ünvan ve bölüm meslek kodundan otomatik atandı
- **Önce `03_yeni_personel_KONTROL.xlsx` ile ünvan atamalarını gözden geçirin**

### 🔴 4. PASİFLEŞTİRME — SQL henüz HAZIR DEĞİL, onay bekleniyor
- `04_pasif_yapma_ONAY_LISTESI.xlsx` ile İK onayı alınmalı (42 kişi)
- Her kişi için: AYRILDI / DOĞUM İZNİ / ASKERLİK / ÜCRETSİZ İZİN / RAPORLU / BİLMİYORUM
- Onaylanan listeyi geri gönderdiğinizde SQL üretilecek
- ⚠️ Yöneticileri yanlış pasifleştirirsek onay zincirinde sorun olur

## Komutlar (Mac/Claude Code'da)

```bash
# 1. SQL dosyalarını sunucuya kopyala
scp 01_tc_ekle_isim_normalize.sql 02_isim_guncelleme.sql 03_yeni_personel_ekle.sql \
    srv@185.123.103.61:/tmp/

# 2. ÖNCE YEDEK AL
ssh srv@185.123.103.61 'sudo -u postgres pg_dump muttas_db > /tmp/muttas_backup_$(date +%F).sql'

# 3. Sırayla çalıştır
ssh srv@185.123.103.61 'sudo -u postgres psql muttas_db -f /tmp/01_tc_ekle_isim_normalize.sql'
# Çıktıyı incele, BEGIN açık, ROLLBACK yaptıysa düzelt, COMMIT için tekrar çalıştır

ssh srv@185.123.103.61 'sudo -u postgres psql muttas_db -f /tmp/03_yeni_personel_ekle.sql'
```

## Önemli notlar

- Her SQL `BEGIN`/`COMMIT` arasında — transaction'lı, ROLLBACK ile geri alınabilir
- SQL dosyaları otomatik COMMIT YAPMAZ, manuel kontrol gerek
- Yedek olmadan production'da çalıştırmayın

## Sonraki adım

Personel senkronizasyonu tamamlandıktan sonra **6 izin Excel'inin import'una** geçilecek.
İzin import'u için ayrı bir paket hazırlanacak.