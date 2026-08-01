@echo off
title KlipperGram - 3D Yazici Telegram Botu Kurulumu
color 0B
cls

echo ======================================================================
echo   KLIPPERGRAM - 3D YAZICI TELEGRAM KONTROL PANELI KURULUMU
echo ======================================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [HATA] Python bilgisayarinizda kurulu degil veya PATH eklentisi yok.
    echo Lutfen https://www.python.org/downloads/ adresinden Python 3 kurarken
    echo "Add Python to PATH" secenegini isaretleyip tekrar deneyin.
    echo.
    pause
    exit /b 1
)

echo [1/2] Gerekli SSH baglanti kutuphanesi (paramiko) kontrol ediliyor...
python -m pip install paramiko --quiet >nul 2>&1

echo [2/2] Kurulum betigi baslatiliyor...
echo.
python deploy.py

echo.
echo ======================================================================
echo Kurulum tamamlandi. Bu pencereyi kapatabilirsiniz.
echo ======================================================================
pause >nul
