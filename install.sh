#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "  KlipperGram - Telegram Yönetim Paneli Kurulumu"
echo "=========================================================="

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

# 1. Python3 ve venv kontrolü
if ! command -v python3 &> /dev/null; then
    echo "[HATA] python3 sistemde bulunamadı!"
    exit 1
fi

echo "[1/4] Sanal ortam (virtualenv) kontrol ediliyor..."
if ! python3 -m venv --help &> /dev/null; then
    echo "[UYARI] python3-venv paketi eksik! Eski Debian / Buster depoları üzerinden otomatik yükleniyor..."
    # Elegoo Neptune 4 Pro (Debian Buster) gibi eski sistemler için arşiv depoları ve geçerlilik süresi koruması
    echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf > /dev/null || true
    sudo apt-get update -o Acquire::Check-Valid-Until=false || true
    sudo apt-get install -y -o Acquire::Check-Valid-Until=false python3-venv python3-pip
fi

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "[BİLGİ] Sanal ortam (venv) başarıyla oluşturuldu."
else
    echo "[BİLGİ] Mevcut sanal ortam kullanılıyor."
fi

echo "[2/4] Gerekli bağımlılıklar yükleniyor (aiogram, aiohttp, Pillow)..."
./venv/bin/pip install --upgrade pip --quiet || true
./venv/bin/pip install -r requirements.txt

echo "[3/4] Yapılandırma dosyası (config.json) kontrol ediliyor..."
if [ ! -f "config.json" ]; then
    if [ -f "config.example.json" ]; then
        cp config.example.json config.json
        echo "------------------------------------------------------------------"
        echo "[UYARI] config.json örnek dosyadan oluşturuldu!"
        echo "Lütfen 'nano config.json' komutuyla dosya içine girip Telegram"
        echo "Bot Token ve Kullanıcı ID bilgilerinizi yazmayı unutmayın!"
        echo "------------------------------------------------------------------"
    fi
fi

echo "[4/4] Systemd arka plan servisi (klippergram.service) oluşturuluyor..."
SERVICE_PATH="/etc/systemd/system/klippergram.service"
USER_NAME="$(whoami)"

# Eski servis varsa durdur ve çakışmayı önle
sudo systemctl stop neptune4-telegram.service 2>/dev/null || true
sudo systemctl disable neptune4-telegram.service 2>/dev/null || true

cat << EOF | sudo tee "$SERVICE_PATH" > /dev/null
[Unit]
Description=KlipperGram Universal Klipper Telegram Management Bot and Mini App
After=network-online.target moonraker.service
Wants=network-online.target

[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$DIR
ExecStart=$DIR/venv/bin/python $DIR/bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "Systemd yapılandırması yenileniyor ve servis başlatılıyor..."
sudo systemctl daemon-reload
sudo systemctl enable klippergram.service
sudo systemctl restart klippergram.service

echo "=========================================================="
echo "  KURULUM TAMAMLANDI"
echo "=========================================================="
echo "Servis Durumunu Kontrol Etmek İçin:"
echo "  sudo systemctl status klippergram.service"
echo ""
echo "Canlı Logları (Hataları veya Durumu) İzlemek İçin:"
echo "  journalctl -u klippergram.service -f"
echo "=========================================================="
