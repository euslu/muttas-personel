"""
PDKS Veri Aktarma Ajanı - Menteşe Belediyesi
=============================================
Bu script Perkotek Bilgi Aktar tarafından oluşturulan tr500.txt dosyasını
Menteşe İK sunucusuna otomatik olarak gönderir.

KURULUM (Windows):
1. Python 3.x yüklü olmalı: https://python.org
2. pip install requests (tek gereksinim)
3. Aşağıdaki AYARLAR bölümünü doldurun
4. Otomatik çalışması için Windows Görev Zamanlayıcısı'na ekleyin:
   - Program: python.exe
   - Argüman: C:\Perkotek\pdks_agent.py
   - Tetikleyici: Her gece 02:00

GÖREV ZAMANLAYICISI KURULUMU (Komut satırından):
schtasks /create /tn "PDKS_Ajan" /tr "python.exe C:\Perkotek\pdks_agent.py" /sc DAILY /st 02:00 /ru SYSTEM
"""

import os
import sys
import requests
import logging
from datetime import datetime
from pathlib import Path

# =============================================================================
# AYARLAR - Bu bölümü doldurun
# =============================================================================
TR500_DOSYA = r"C:\Program Files (x86)\Perkotek\Bilgi Aktar v8.2.2\tr500.txt"
SUNUCU_URL  = "http://209.38.219.210:8002/pdks/yukle"
API_ANAHTAR = "MentesePDKS2026!"
LOG_DOSYA   = r"C:\Perkotek\pdks_ajan.log"
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DOSYA, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("pdks_ajan")


def dosya_gonder(dosya_yolu: str) -> bool:
    if not os.path.exists(dosya_yolu):
        log.error(f"Dosya bulunamadı: {dosya_yolu}")
        return False

    boyut = os.path.getsize(dosya_yolu)
    log.info(f"Dosya okunuyor: {dosya_yolu} ({boyut} byte)")

    try:
        with open(dosya_yolu, "rb") as f:
            yanit = requests.post(
                SUNUCU_URL,
                files={"dosya": ("tr500.txt", f, "text/plain")},
                headers={"x-api-key": API_ANAHTAR},
                timeout=60,
            )

        if yanit.status_code == 200:
            veri = yanit.json()
            log.info(
                f"Başarılı! Toplam: {veri.get('toplam', 0)}, "
                f"Eklenen: {veri.get('eklenen', 0)}, "
                f"Atlanan (duplicate): {veri.get('atlanan', 0)}"
            )
            return True
        else:
            log.error(f"Sunucu hatası: HTTP {yanit.status_code} - {yanit.text[:200]}")
            return False

    except requests.ConnectionError:
        log.error(f"Sunucuya bağlanılamadı: {SUNUCU_URL}")
        return False
    except requests.Timeout:
        log.error("Zaman aşımı - sunucu yanıt vermedi")
        return False
    except Exception as e:
        log.error(f"Beklenmeyen hata: {e}")
        return False


def arsivle(dosya_yolu: str):
    try:
        p = Path(dosya_yolu)
        tarih_damga = datetime.now().strftime("%Y%m%d_%H%M%S")
        arsiv_adi = p.parent / f"arsiv_{tarih_damga}_{p.name}"
        p.rename(arsiv_adi)
        log.info(f"Dosya arşivlendi: {arsiv_adi}")
    except Exception as e:
        log.warning(f"Arşivleme başarısız: {e}")


if __name__ == "__main__":
    log.info("=" * 50)
    log.info("PDKS Veri Aktarma Ajanı başladı")
    log.info(f"Tarih/Saat: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    basari = dosya_gonder(TR500_DOSYA)

    if basari:
        arsivle(TR500_DOSYA)
        log.info("İşlem tamamlandı.")
        sys.exit(0)
    else:
        log.error("İşlem başarısız.")
        sys.exit(1)
