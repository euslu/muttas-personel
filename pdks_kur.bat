@echo off
chcp 65001 >nul
title PDKS Ajan Kurulumu - Mentese Belediyesi
echo.
echo =============================================
echo   PDKS Veri Aktarma Ajani - KURULUM
echo   Mentese Belediyesi
echo =============================================
echo.

REM Klasorleri olustur
if not exist "C:\Perkotek" mkdir "C:\Perkotek"
if not exist "C:\Perkotek\pdks_logs" mkdir "C:\Perkotek\pdks_logs"
if not exist "C:\Perkotek\pdks_arsiv" mkdir "C:\Perkotek\pdks_arsiv"

REM Agent dosyasini kopyala
copy /Y "%~dp0pdks_agent.py" "C:\Perkotek\pdks_agent.py" >nul
echo [OK] pdks_agent.py kopyalandi: C:\Perkotek\pdks_agent.py

REM Python kontrol
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo [HATA] Python bulunamadi!
    echo        https://python.org adresinden Python 3.x yukleyin
    echo        Yukleme sirasinda "Add to PATH" secenegini isaretleyin
    pause
    exit /b 1
)

echo [OK] Python bulundu
python --version

REM Tek seferlik test
echo.
echo Test gonderimi yapiliyor...
python "C:\Perkotek\pdks_agent.py"

echo.
echo =============================================
echo   Windows baslangicina eklemek ister misiniz?
echo   (Bilgisayar her acildiginda otomatik calisir)
echo =============================================
echo.
set /p CEVAP="Eklensin mi? (E/H): "
if /i "%CEVAP%"=="E" (
    python "C:\Perkotek\pdks_agent.py" --servis-kur
)

echo.
echo Kurulum tamamlandi!
echo.
pause
