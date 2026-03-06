"""
PDKS Veri Aktarma Ajanı - Menteşe Belediyesi
=============================================
Perkotek Bilgi Aktar tr500.txt verisini sunucuya gönderir.

Kullanım:
  python pdks_agent.py              → Tek seferlik gönderim
  python pdks_agent.py --zamanlayici → Arka planda çalışır, belirlenen saatlerde gönderir
  python pdks_agent.py --servis-kur  → Windows başlangıcına ekler (otomatik çalışır)
  python pdks_agent.py --servis-sil  → Windows başlangıcından kaldırır
"""

import os
import sys
import time
import shutil
import ctypes
import winreg
import argparse
import threading
from datetime import datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import json
import logging
import io
import uuid

# =============================================================================
# AYARLAR
# =============================================================================
TR500_DOSYA   = r"C:\Program Files (x86)\Perkotek\Bilgi Aktar v8.2.2\tr500.txt"
SUNUCU_URL    = "http://209.38.219.210:8002/pdks/yukle"
API_ANAHTAR   = "MentesePDKS2026!"
LOG_KLASOR    = r"C:\Perkotek\pdks_logs"
ARSIV_KLASOR  = r"C:\Perkotek\pdks_arsiv"
GONDERIM_SAATLERI = ["02:00", "06:00", "08:30", "12:00", "13:30", "17:30", "22:00"]
UYGULAMA_ADI  = "MentesePDKS_Agent"
# =============================================================================

os.makedirs(LOG_KLASOR, exist_ok=True)
os.makedirs(ARSIV_KLASOR, exist_ok=True)

log_dosya = os.path.join(LOG_KLASOR, f"pdks_{datetime.now().strftime('%Y%m')}.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_dosya, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("pdks")


def multipart_encode(dosya_yolu):
    boundary = uuid.uuid4().hex
    dosya_adi = os.path.basename(dosya_yolu)
    with open(dosya_yolu, "rb") as f:
        icerik = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="dosya"; filename="{dosya_adi}"\r\n'
        f"Content-Type: text/plain\r\n\r\n"
    ).encode("utf-8") + icerik + f"\r\n--{boundary}--\r\n".encode("utf-8")

    content_type = f"multipart/form-data; boundary={boundary}"
    return body, content_type


def dosya_gonder(dosya_yolu):
    if not os.path.exists(dosya_yolu):
        log.warning(f"Dosya bulunamadi: {dosya_yolu}")
        return False

    boyut = os.path.getsize(dosya_yolu)
    if boyut == 0:
        log.warning("Dosya bos, gonderim atlanıyor.")
        return False

    log.info(f"Dosya okunuyor: {dosya_yolu} ({boyut:,} byte)")

    try:
        body, content_type = multipart_encode(dosya_yolu)

        req = Request(SUNUCU_URL, data=body, method="POST")
        req.add_header("x-api-key", API_ANAHTAR)
        req.add_header("Content-Type", content_type)

        with urlopen(req, timeout=120) as resp:
            veri = json.loads(resp.read().decode("utf-8"))
            log.info(
                f"Basarili! Toplam: {veri.get('toplam', 0)}, "
                f"Eklenen: {veri.get('eklenen', 0)}, "
                f"Atlanan: {veri.get('atlanan', 0)}"
            )
            return True

    except HTTPError as e:
        log.error(f"Sunucu hatasi: HTTP {e.code} - {e.read().decode('utf-8', errors='replace')[:200]}")
    except URLError as e:
        log.error(f"Baglanti hatasi: {e.reason}")
    except Exception as e:
        log.error(f"Beklenmeyen hata: {e}")

    return False


def arsivle(dosya_yolu):
    try:
        tarih = datetime.now().strftime("%Y%m%d_%H%M%S")
        arsiv_adi = os.path.join(ARSIV_KLASOR, f"tr500_{tarih}.txt")
        shutil.copy2(dosya_yolu, arsiv_adi)
        log.info(f"Arsivlendi: {arsiv_adi}")

        arsiv_dosyalar = sorted(Path(ARSIV_KLASOR).glob("tr500_*.txt"))
        if len(arsiv_dosyalar) > 90:
            for eski in arsiv_dosyalar[:-90]:
                eski.unlink()
                log.info(f"Eski arsiv silindi: {eski}")
    except Exception as e:
        log.warning(f"Arsivleme hatasi: {e}")


def tek_gonderim():
    log.info("=" * 50)
    log.info("PDKS gonderimi baslatildi")
    log.info(f"Tarih: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    basari = dosya_gonder(TR500_DOSYA)

    if basari:
        arsivle(TR500_DOSYA)
        log.info("Islem tamamlandi.")
    else:
        log.error("Gonderim basarisiz.")

    return basari


def zamanlayici_calistir():
    log.info("=" * 50)
    log.info("PDKS Zamanlayici baslatildi")
    log.info(f"Gonderim saatleri: {', '.join(GONDERIM_SAATLERI)}")
    log.info(f"tr500 dosyasi: {TR500_DOSYA}")
    log.info(f"Sunucu: {SUNUCU_URL}")

    son_gonderim = {}

    while True:
        simdi = datetime.now()
        saat_str = simdi.strftime("%H:%M")
        tarih_str = simdi.strftime("%Y-%m-%d")

        for hedef_saat in GONDERIM_SAATLERI:
            if saat_str == hedef_saat and son_gonderim.get(hedef_saat) != tarih_str:
                log.info(f"Zamanlanmis gonderim: {hedef_saat}")
                tek_gonderim()
                son_gonderim[hedef_saat] = tarih_str

        time.sleep(30)


def windows_baslanigca_ekle():
    try:
        if getattr(sys, 'frozen', False):
            exe_yol = sys.executable
        else:
            exe_yol = f'"{sys.executable}" "{os.path.abspath(__file__)}" --zamanlayici'

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, UYGULAMA_ADI, 0, winreg.REG_SZ, exe_yol)
        winreg.CloseKey(key)
        log.info(f"Windows baslangicinsa eklendi: {UYGULAMA_ADI}")
        print("\n[OK] Windows baslangicina eklendi.")
        print(f"     Her bilgisayar acildiginda PDKS ajani otomatik calisacak.")
        print(f"     Gonderim saatleri: {', '.join(GONDERIM_SAATLERI)}")
    except Exception as e:
        log.error(f"Baslangicinsa eklenemedi: {e}")
        print(f"\n[HATA] Baslangicinsa eklenemedi: {e}")
        print("       Yonetici olarak calistirmayi deneyin.")


def windows_baslangictan_sil():
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        )
        winreg.DeleteValue(key, UYGULAMA_ADI)
        winreg.CloseKey(key)
        log.info("Windows baslangicasindan kaldirildi.")
        print("\n[OK] Windows baslangicasindan kaldirildi.")
    except FileNotFoundError:
        print("\n[BILGI] Zaten baslangica eklenmemis.")
    except Exception as e:
        log.error(f"Kaldirilaamadi: {e}")
        print(f"\n[HATA] Kaldirilaamadi: {e}")


def durum_goster():
    print("\n" + "=" * 55)
    print("  PDKS Veri Aktarma Ajani - Mentese Belediyesi")
    print("=" * 55)
    print(f"  tr500 dosyasi : {TR500_DOSYA}")
    print(f"  Sunucu        : {SUNUCU_URL}")
    print(f"  Log klasoru   : {LOG_KLASOR}")
    print(f"  Arsiv klasoru : {ARSIV_KLASOR}")
    print(f"  Saatler       : {', '.join(GONDERIM_SAATLERI)}")

    if os.path.exists(TR500_DOSYA):
        boyut = os.path.getsize(TR500_DOSYA)
        degistirme = datetime.fromtimestamp(os.path.getmtime(TR500_DOSYA))
        print(f"\n  Dosya durumu  : MEVCUT ({boyut:,} byte)")
        print(f"  Son degisiklik: {degistirme.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print(f"\n  Dosya durumu  : BULUNAMADI")

    arsiv_sayisi = len(list(Path(ARSIV_KLASOR).glob("tr500_*.txt"))) if os.path.exists(ARSIV_KLASOR) else 0
    print(f"  Arsiv sayisi  : {arsiv_sayisi}")
    print("=" * 55)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PDKS Veri Aktarma Ajani")
    parser.add_argument("--zamanlayici", action="store_true", help="Arka planda zamanlayici olarak calistir")
    parser.add_argument("--servis-kur", action="store_true", help="Windows baslangicina ekle")
    parser.add_argument("--servis-sil", action="store_true", help="Windows baslangicaindan kaldir")
    parser.add_argument("--durum", action="store_true", help="Mevcut durumu goster")
    args = parser.parse_args()

    if args.durum:
        durum_goster()
    elif args.servis_kur:
        durum_goster()
        windows_baslanigca_ekle()
    elif args.servis_sil:
        windows_baslangictan_sil()
    elif args.zamanlayici:
        durum_goster()
        zamanlayici_calistir()
    else:
        durum_goster()
        print("\nTek seferlik gonderim baslatiliyor...\n")
        basari = tek_gonderim()
        sys.exit(0 if basari else 1)
