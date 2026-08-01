# KlipperGram - Klipper & Moonraker Telegram Bot and Web Panel

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/Python-3.7%2B-blue.svg)](https://www.python.org/)
[![Klipper Compatible](https://img.shields.io/badge/Klipper%20%2F%20Moonraker-Compatible-0088cc.svg)](https://www.klipper3d.org/)

KlipperGram, Klipper ve Moonraker koşan 3D yazıcıları telefondan yönetmek ve uzaktan izlemek için geliştirilmiş açık kaynaklı bir Telegram yönetim botu ve yerel ağ web panelidir. Yazıcının kendi kartı üzerinde (ARM64/AMD64, Raspberry Pi, Debian, Armbian) arka plan servisi (systemd) olarak çalışır.

Evinizde değilken bile modeminizde herhangi bir port açmadan (port forwarding) veya üçüncü parti tünel servisleri (Cloudflare, Ngrok vb.) kurmadan; doğrudan cep telefonunuz üzerinden Telegram aracılığıyla 3D yazıcınızın durumunu canlı izleyebilir, baskı süreçlerini kontrol edebilir ve kamera akışını takip edebilirsiniz.

---

## Desteklenen Donanımlar ve Uyumluluk

KlipperGram, doğrudan Moonraker REST API ve WebSocket protokollerini kullandığı için Klipper kurulu tüm 3D yazıcılar ve kontrol kartları ile uyumludur:

* **Voron Design:** Voron 2.4, Trident, Switchwire, 0.2, Legacy
* **Creality:** Creality K1, K1 Max, K1C, Ender-3 V3 KE, Ender-3 V3 SE (Klipper modlu), Sonic Pad, Nebula Pad
* **Elegoo:** Neptune 4 Pro, Neptune 4 Plus, Neptune 4 Max, Neptune 4 Standart
* **Sovol & Qidi Tech:** Sovol SV06 Plus, SV07 Plus, Qidi Tech X-Max 3, X-Plus 3, X-Smart 3
* **RatRig & Anycubic:** RatRig V-Core 3, V-Minion, Anycubic Kobra 2/3 serisi (Klipper modlu), FLSUN
* **Tek Kartlı Bilgisayarlar (SBC) & Anakartlar:** Raspberry Pi 3/4/5, Orange Pi, Makerbase (MKS PI, SKIPR), BigTreeTech (BTT CB1, Pi, Manta, Octopus), Mainsail, Fluidd ve Crowsnest sistemleri

---

## Özellikler

- **Anlık Kare Güncelleme (Canlı İzleme):** Telegram'ın `edit_message_media` özelliği sayesinde tek bir bildirim mesajı üzerinden fotoğrafı her ~3 saniyede bir yerinde yenileyerek canlı takip imkanı sunar. Sohbet geçmişinde mesaj kirliliği oluşturmaz.
- **5 Saniyelik GIF / Video Kaydı:** Kameradan 5 saniye boyunca kare toplayarak akıcı bir animasyona dönüştürür ve sohbete video olarak iletir.
- **Güvenli Ağ Mimarisi:** Yazıcı dış dünyaya hiçbir inbound (içeri yönlü) port açmaz. Yalnızca yapılandırma dosyasında belirtilen Telegram ID'lerine (whitelist) yanıt verir.
- **Yerel Ağ Web Paneli:** Aynı Wi-Fi ağındayken mobil veya masaüstü tarayıcılardan erişilebilen, karanlık temalı ve hafif bir kontrol arayüzü sunar (Telegram Mini App destekli).
- **Durum ve Katman Bildirimleri:** Baskı başlangıcı, bitişi, duraklatılması, hata durumları ve isteğe bağlı olarak katman değişimlerinde fotoğraflı bildirim gönderir.
- **Sıcaklık ve Görev Kontrolü:** PLA, PETG, ABS, TPU için ön ısıtma profilleri; baskı duraklatma, devam ettirme, iptal etme, LED kontrolü ve acil durdurma (E-Stop) komutları.

---

## Mimari

```
[ Telegram Uygulaması (Mobil / Masaüstü) ]
                   │
                   ▼ (SSL/TLS Şifreli Bağlantı)
       [ Telegram API Sunucuları ]
                   ▲
                   │ (Outbound İstekler)
 ┌─────────────────┴──────────────────────────────────────┐
 │  KlipperGram Bot Servisi (klippergram.service)         │
 │  ├── Yetkilendirme Kontrolü (Allowed Users Whitelist)  │
 │  ├── Medya Motoru (aiogram & Pillow GIF/Webcam İşleme) │
 │  └── Moonraker İstemcisi (127.0.0.1:7125 REST & WS)    │
 │                                                        │
 │  3D Yazıcı Sistemi (Linux / Klipper / Moonraker)       │
 └────────────────────────────────────────────────────────┘
```

---

## Kurulum

Kurulumu gerçekleştirmek için aşağıdaki otomatik dağıtım betiğini kullanabilir veya doğrudan yazıcı üzerinde manuel kurulum yapabilirsiniz.

### Ön Hazırlık
1. **Bot Token:** Telegram'da [@BotFather](https://t.me/BotFather) üzerinden `/newbot` komutu ile bir bot oluşturup API anahtarını alın.
2. **Kullanıcı ID:** Telegram'da [@userinfobot](https://t.me/userinfobot) botuna `/start` yazarak sayısal kullanıcı ID'nizi öğrenin.

---

### Yöntem 1: Otomatik Kurulum (Önerilen)

Bu yöntem bilgisayarınız üzerinden SSH ile yazıcıya bağlanarak gerekli dosyaları ve servis yapılandırmasını tự động oluşturur.

1. Depoyu indirin veya klonlayın:
   ```bash
   git clone https://github.com/Soybahceci/klippergram-panel.git
   cd klippergram-panel
   ```
2. Kurulumu başlatın:
   - **Windows:** Klasör içindeki `Kurulumu_Baslat.bat` dosyasını çalıştırın.
   - **Linux / macOS:** Terminalde `python3 deploy.py` komutunu çalıştırın.
3. Ekrana gelen promptlarda Bot Token, Kullanıcı ID, Yazıcı IP adresi ve SSH şifrenizi girin.
4. Kurulum betiği bağımlılıkları (python3-venv, Pillow, aiogram) yükleyecek ve `klippergram.service` systemd servisini başlatacaktır.

---

### Yöntem 2: Yazıcı Üzerinde Manuel Kurulum

SSH terminali üzerinden doğrudan kurulum yapmak için:

1. Yazıcıya SSH ile bağlanın:
   ```bash
   ssh mks@192.168.1.130
   ```
2. Depoyu klonlayın ve dizine girin:
   ```bash
   git clone https://github.com/Soybahceci/klippergram-panel.git ~/klippergram
   cd ~/klippergram
   ```
3. Yapılandırma dosyasını oluşturun ve düzenleyin:
   ```bash
   cp config.example.json config.json
   nano config.json
   ```
   *`bot_token` ve `allowed_users` alanlarını doldurup kaydedin.*
4. Kurulum betiğini çalıştırın:
   ```bash
   chmod +x install.sh
   ./install.sh
   ```

---

## Yapılandırma (`config.json`)

| Parametre | Varsayılan | Açıklama |
| :--- | :--- | :--- |
| `telegram.bot_token` | `""` | @BotFather tarafından sağlanan bot API anahtarı. |
| `telegram.allowed_users` | `[]` | Yetkili Telegram sayısal ID listesi (Örn: `[7557861007]`). |
| `telegram.enable_notifications` | `true` | Otomatik baskı durumu ve hata bildirimleri. |
| `telegram.notify_on_layer_change` | `false` | Katman değişimlerinde bildirim gönderimi. |
| `moonraker.url` | `"http://127.0.0.1"` | Yerel Moonraker API adresi. |
| `webcam.enabled` | `true` | Kamera anlık görüntü desteği. |
| `webcam.snapshot_url` | `"http://127.0.0.1/webcam/?action=snapshot"` | Klippy/Crowsnest anlık görüntü URL'si. |
| `webapp.port` | `8085` | Yerel ağ web panelinin port adresi. |

---

## Telegram Bot Komutları ve Butonlar

Bot ile sohbete başlayıp `/start` veya `/menu` yazdığınızda kontrol paneli açılır:

- **Görsel Web Paneli:** Aynı Wi-Fi ağındayken tarayıcı üzerinden açılabilen arayüz.
- **Durum Raporu:** Sıcaklık, baskı yüzdesi, geçen süre, Z yüksekliği ve anlık kamera karesi.
- **Tek Kare Foto:** Kameradan anlık fotoğraf çeker.
- **Canlı İzle (Anlık Yenileme):** 60 saniye boyunca mevcut mesajı her 3 saniyede bir güncelleyerek canlı akış sağlar.
- **5sn Video/GIF Kaydı:** Kameradan 5 saniyelik hareketli video oluşturup gönderir.
- **Isıtma Menüsü:** PLA (200/60°C), PETG (230/70°C), ABS (250/90°C), TPU (220/50°C) ve soğutma komutları.
- **G-code Dosyaları:** Yazıcıdaki G-code dosyalarını listeler ve onay ile baskı başlatır.
- **Duraklat / Devam Et / İptal:** Aktif baskı yönetimi.
- **LED Işık / Acil Durdur (E-Stop):** Kasa aydınlatması kontrolü ve acil durdurma tetikleyicisi.

---

## Sorun Giderme

Servisin durumunu kontrol etmek için:
```bash
sudo systemctl status klippergram.service
```

Canlı sistem loglarını izlemek için:
```bash
journalctl -u klippergram.service -f
```

Yapılandırmayı değiştirdikten sonra servisi yeniden başlatmak için:
```bash
sudo systemctl restart klippergram.service
```

Debian Buster veya eski tabanlı dağıtımlarda `apt-get update` sırasında depo süresi dolmuş (InRelease is expired) hatası alınırsa, `install.sh` betiği otomatik olarak `Acquire::Check-Valid-Until=false` parametresini uygulayarak kurulumu tamamlar.

---

## Lisans

Bu proje MIT Lisansı altında dağıtılmaktadır. Daha fazla bilgi için `LICENSE` dosyasına bakabilirsiniz.
