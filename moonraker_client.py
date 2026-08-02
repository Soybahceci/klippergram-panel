import aiohttp
import asyncio
import urllib.parse
from config import config

class MoonrakerClient:
    def __init__(self):
        self.base_url = config.moonraker_url
        self.headers = {}
        if config.moonraker_api_key:
            self.headers["X-Api-Key"] = config.moonraker_api_key

    async def _get(self, endpoint: str, params: dict = None) -> dict:
        url = f"{self.base_url}{endpoint}"
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        text = await response.text()
                        return {"error": True, "status": response.status, "message": text}
        except Exception as e:
            return {"error": True, "message": str(e)}

    async def _post(self, endpoint: str, json_data: dict = None, params: dict = None) -> dict:
        url = f"{self.base_url}{endpoint}"
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.post(url, json=json_data, params=params, timeout=10) as response:
                    if response.status in [200, 201]:
                        return await response.json()
                    else:
                        text = await response.text()
                        return {"error": True, "status": response.status, "message": text}
        except Exception as e:
            return {"error": True, "message": str(e)}

    async def get_printer_status(self) -> dict:
        """Yazıcının anlık durumunu (sıcaklıklar, ilerleme, dosya adı vb.) sorgular."""
        objects = "webhooks&display_status&heater_bed&extruder&print_stats&toolhead&fan"
        res = await self._get(f"/printer/objects/query?{objects}")
        if res.get("error"):
            return res
        
        status = res.get("result", {}).get("status", {})
        print_stats = status.get("print_stats", {})
        extruder = status.get("extruder", {})
        heater_bed = status.get("heater_bed", {})
        display_status = status.get("display_status", {})
        toolhead = status.get("toolhead", {})
        fan = status.get("fan", {})
        webhooks = status.get("webhooks", {})

        state = print_stats.get("state", webhooks.get("state", "unknown"))
        filename = print_stats.get("filename", "Yok")
        progress = display_status.get("progress", 0.0) * 100
        print_duration = print_stats.get("print_duration", 0)
        
        return {
            "error": False,
            "state": state,
            "filename": filename,
            "progress": round(progress, 1),
            "duration_seconds": int(print_duration),
            "extruder_temp": round(extruder.get("temperature", 0.0), 1),
            "extruder_target": round(extruder.get("target", 0.0), 1),
            "bed_temp": round(heater_bed.get("temperature", 0.0), 1),
            "bed_target": round(heater_bed.get("target", 0.0), 1),
            "fan_speed": round(fan.get("speed", 0.0) * 100),
            "max_velocity": round(toolhead.get("max_velocity", 0.0)),
            "position_z": round(toolhead.get("position", [0,0,0])[2], 2) if "position" in toolhead else 0.0
        }

    async def send_gcode(self, script: str) -> dict:
        """Klipper üzerine G-code komutu gönderir."""
        return await self._post("/printer/gcode/script", params={"script": script})

    async def send_and_read_console(self, script: str) -> str:
        """G-code komutu gönderir ve Klipper konsol çıktısını (yanıtını) okur."""
        res = await self.send_gcode(script)
        if res.get("error"):
            return f"❌ Hata: {res.get('message')}"
        
        # Klipper'ın komutu işleyip konsola basması için kısa süre bekle
        await asyncio.sleep(0.5)
        
        # Moonraker gcode_store'dan son yanıtları çek
        store_res = await self._get("/server/gcode_store", params={"count": 15})
        if store_res.get("error"):
            return "✅ Komut gönderildi (Konsol okunamadı)."
            
        store = store_res.get("result", {}).get("gcode_store", [])
        responses = []
        
        # Sondan başa doğru (en yeni) kendi komutumuzu bulana kadar gelen 'response' tipindeki mesajları topla
        for item in reversed(store):
            if item.get("type") == "command" and item.get("message") == script:
                break
            if item.get("type") == "response":
                responses.insert(0, item.get("message"))
                
        if not responses:
            return "✅ Komut gönderildi (Konsol yanıtı yok)."
            
        return "\n".join(responses)

    async def pause_print(self) -> dict:
        return await self._post("/printer/print/pause")

    async def clear_bed(self, strike_z: float) -> dict:
        """Tablayı otomatik süpürme (Ataletle obje düşürme) otomasyonu."""
        script = f"""
G90
G1 Z{strike_z + 10} F1200
G1 X115 Y220 F3000
G1 Z{strike_z} F1200
G1 Y0 F6000
G1 X0 Y220 F3000
G1 Z50 F1200
"""
        return await self.send_gcode(script)

    async def shake_bed(self) -> dict:
        """Tablayı hızlıca ileri geri sallayarak objeyi düşürme (Atalet Modu)."""
        script = "G90\nG1 Z50 F1200\n" # Güvenli yükseklik
        for _ in range(10):
            script += "G1 Y220 F15000\n" # 250mm/s hızla geri
            script += "G1 Y0 F15000\n"   # 250mm/s hızla ileri
        return await self.send_gcode(script)

    async def resume_print(self) -> dict:
        return await self._post("/printer/print/resume")

    async def cancel_print(self) -> dict:
        return await self._post("/printer/print/cancel")

    async def set_temperature(self, extruder: int = None, bed: int = None) -> dict:
        """Nozzle ve/veya tabla sıcaklığını ayarlar."""
        commands = []
        if extruder is not None:
            commands.append(f"M104 S{extruder}")
        if bed is not None:
            commands.append(f"M140 S{bed}")
        
        if not commands:
            return {"error": True, "message": "Sıcaklık belirtilmedi"}
        
        return await self.send_gcode(" \n ".join(commands))

    async def toggle_led(self, state: bool) -> dict:
        """Klipper LED ışığını açar veya kapatır (Neptune 4, Voron, Creality K1 vb. makrolarını dener)."""
        # Klipper yazıcılarda FLASHLIGHT_ON / OFF veya SET_LED gibi standart makrolar kullanılır.
        # En yaygın komutları sırasıyla deneriz veya FLASHLIGHT makrosunu tetikleriz:
        cmd = "FLASHLIGHT_ON" if state else "FLASHLIGHT_OFF"
        res = await self.send_gcode(cmd)
        if res.get("error"):
            # Alternatif LED komutu: SET_LED LED=led RED=1 GREEN=1 BLUE=1 veya W=1
            cmd2 = "SET_LED LED=led RED=1 GREEN=1 BLUE=1" if state else "SET_LED LED=led RED=0 GREEN=0 BLUE=0"
            return await self.send_gcode(cmd2)
        return res

    async def get_gcode_files(self) -> list:
        """G-code dosyalarını listeler."""
        res = await self._get("/server/files/list?root=gcodes")
        if res.get("error"):
            return []
        files = res.get("result", [])
        # En son değiştirilenleri en başa al
        files.sort(key=lambda x: x.get("modified", 0), reverse=True)
        return files[:15] # Son 15 dosya

    async def start_print(self, filename: str) -> dict:
        """Belirtilen G-code dosyasının baskısını başlatır."""
        return await self._post("/printer/print/start", json_data={"filename": filename})

    async def get_webcam_snapshot(self) -> bytes:
        """Webcam'den anlık fotoğraf çeker ve byte olarak döndürür."""
        if not config.webcam_enabled:
            return None
        try:
            url = config.webcam_snapshot_url
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        return await response.read()
        except Exception as e:
            print(f"[HATA] Webcam fotoğrafı alınamadı: {e}")
        return None

moonraker_client = MoonrakerClient()
