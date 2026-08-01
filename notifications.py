import asyncio
import time
import io
from aiogram import Bot
from aiogram.types import InputFile
from config import config
from moonraker_client import moonraker_client

class NotificationManager:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.last_state = "unknown"
        self.last_notify_time = 0
        self.is_running = False

    async def start_monitoring(self):
        """Arka planda Moonraker yazıcı durumunu takip ederek önemli olaylarda bildirim atar."""
        if not config.enable_notifications or not config.allowed_users:
            print("[BİLGİ] Bildirimler kapalı veya izinli kullanıcı listesi boş.")
            return

        self.is_running = True
        print("[BİLGİ] Anlık baskı durumu bildirim servisi başlatıldı.")

        while self.is_running:
            try:
                status = await moonraker_client.get_printer_status()
                if not status.get("error"):
                    current_state = status.get("state", "unknown")
                    filename = status.get("filename", "Yok")
                    progress = status.get("progress", 0)

                    # Durum değişiklikleri
                    if current_state != self.last_state:
                        if self.last_state != "unknown": # İlk açılışta gereksiz bildirim atmayalım
                            await self._handle_state_change(current_state, filename, progress)
                        self.last_state = current_state

                    # Periyodik baskı durumu bildirimi (Örn: 15 dakikada bir)
                    if current_state == "printing":
                        interval_sec = config.data.get("telegram", {}).get("notify_interval_minutes", 15) * 60
                        if time.time() - self.last_notify_time >= interval_sec and self.last_notify_time > 0:
                            await self._send_progress_notification(status)
                            self.last_notify_time = time.time()
                        elif self.last_notify_time == 0:
                            self.last_notify_time = time.time()

            except Exception as e:
                print(f"[HATA] Bildirim döngüsünde hata: {e}")

            await asyncio.sleep(5) # 5 saniyede bir kontrol et (Klipper için en güvenli, yormayan yöntem)

    async def _handle_state_change(self, new_state: str, filename: str, progress: float):
        msg = ""
        send_cam = False

        if new_state == "printing":
            msg = f"🟢 **Baskı Başladı!**\n📄 Dosya: `{filename}`\n🔥 Yazıcı çalışıyor..."
            self.last_notify_time = time.time()
            send_cam = True
        elif new_state == "complete":
            msg = f"🏁 **Baskı Başarıyla Tamamlandı!** 🎉\n📄 Dosya: `{filename}`"
            send_cam = True
        elif new_state in ["error", "shutdown"]:
            msg = f"❌ **YAZICI HATASI / DURDU!** ⚠️\nLütfen yazıcıyı kontrol edin.\nSon Durum: `{new_state}`"
            send_cam = True
        elif new_state == "paused":
            msg = f"⏸ **Baskı Duraklatıldı!**\n📄 Dosya: `{filename}`\n📊 İlerleme: %{progress}"
            send_cam = True

        if msg:
            await self._broadcast(msg, send_cam=send_cam)

    async def _send_progress_notification(self, status: dict):
        msg = (
            f"📈 **Periyodik Baskı Raporu**\n"
            f"📄 Dosya: `{status.get('filename')}`\n"
            f"⏳ İlerleme: **%{status.get('progress')}**\n"
            f"🌡 Nozzle: **{status.get('extruder_temp')}°C** | Tabla: **{status.get('bed_temp')}°C**\n"
            f"📐 Z Yüksekliği: **{status.get('position_z')} mm**"
        )
        await self._broadcast(msg, send_cam=True)

    async def _broadcast(self, text: str, send_cam: bool = False):
        cam_bytes = None
        if send_cam and config.webcam_enabled:
            cam_bytes = await moonraker_client.get_webcam_snapshot()

        for user_id in config.allowed_users:
            try:
                if cam_bytes:
                    photo = InputFile(io.BytesIO(cam_bytes), filename="snapshot.jpg")
                    await self.bot.send_photo(chat_id=user_id, photo=photo, caption=text, parse_mode="Markdown")
                else:
                    await self.bot.send_message(chat_id=user_id, text=text, parse_mode="Markdown")
            except Exception as e:
                print(f"[HATA] Kullanıcıya ({user_id}) bildirim gönderilemedi: {e}")
