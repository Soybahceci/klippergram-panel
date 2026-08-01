import json
import os
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"
EXAMPLE_CONFIG_FILE = BASE_DIR / "config.example.json"

class Config:
    def __init__(self):
        self.data = self._load_config()

    def _load_config(self) -> dict:
        if not CONFIG_FILE.exists():
            if EXAMPLE_CONFIG_FILE.exists():
                shutil.copy(EXAMPLE_CONFIG_FILE, CONFIG_FILE)
                print(f"[BİLGİ] config.json bulunamadı. Örnek yapılandırma dosyası kopyalandı: {CONFIG_FILE}")
            else:
                return {}
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[HATA] Yapılandırma dosyası okunamadı: {e}")
            return {}

    @property
    def bot_token(self) -> str:
        return self.data.get("telegram", {}).get("bot_token", "")

    @property
    def allowed_users(self) -> list:
        return self.data.get("telegram", {}).get("allowed_users", [])

    @property
    def enable_notifications(self) -> bool:
        return self.data.get("telegram", {}).get("enable_notifications", True)

    @property
    def notify_on_layer_change(self) -> bool:
        return self.data.get("telegram", {}).get("notify_on_layer_change", False)

    @property
    def moonraker_url(self) -> str:
        return self.data.get("moonraker", {}).get("url", "http://127.0.0.1:7125").rstrip("/")

    @property
    def moonraker_api_key(self) -> str:
        return self.data.get("moonraker", {}).get("api_key", "")

    @property
    def webcam_enabled(self) -> bool:
        return self.data.get("webcam", {}).get("enabled", True)

    @property
    def webcam_snapshot_url(self) -> str:
        return self.data.get("webcam", {}).get("snapshot_url", "http://127.0.0.1/webcam/?action=snapshot")

    @property
    def webapp_enabled(self) -> bool:
        return self.data.get("webapp", {}).get("enabled", True)

    @property
    def webapp_host(self) -> str:
        return self.data.get("webapp", {}).get("host", "0.0.0.0")

    @property
    def webapp_port(self) -> int:
        return self.data.get("webapp", {}).get("port", 8085)

    @property
    def webapp_public_url(self) -> str:
        return self.data.get("webapp", {}).get("public_url", "")

    def is_user_allowed(self, user_id: int) -> bool:
        # Eğer liste boşsa veya 123456789 örneği varsa, tüm kullanıcılara veya ilk gelene uyarı verebiliriz.
        # Güvenlik için listeye kontrol ekleyelim:
        if not self.allowed_users:
            return True # Liste boşsa herkese izin ver (veya test modu)
        return user_id in self.allowed_users

config = Config()
