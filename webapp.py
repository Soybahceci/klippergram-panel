import asyncio
import os
from pathlib import Path
from aiohttp import web
from config import config
from moonraker_client import moonraker_client

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

async def handle_index(request):
    return web.FileResponse(STATIC_DIR / "index.html")

async def api_status(request):
    status = await moonraker_client.get_printer_status()
    return web.json_response(status)

async def api_files(request):
    files = await moonraker_client.get_gcode_files()
    return web.json_response({"files": files})

async def api_control(request):
    try:
        data = await request.json()
        action = data.get("action")
        
        if action == "pause":
            res = await moonraker_client.pause_print()
        elif action == "resume":
            res = await moonraker_client.resume_print()
        elif action == "cancel":
            res = await moonraker_client.cancel_print()
        elif action == "toggle_led":
            res = await moonraker_client.toggle_led(True)
        elif action == "start_print":
            filename = data.get("filename")
            res = await moonraker_client.start_print(filename)
        elif action == "set_temp":
            extruder = data.get("extruder")
            bed = data.get("bed")
            res = await moonraker_client.set_temperature(extruder, bed)
        elif action == "gcode":
            script = data.get("script")
            res = await moonraker_client.send_gcode(script)
        else:
            return web.json_response({"error": True, "message": "Geçersiz işlem!"}, status=400)
            
        return web.json_response(res)
    except Exception as e:
        return web.json_response({"error": True, "message": str(e)}, status=500)

async def api_snapshot(request):
    cam_bytes = await moonraker_client.get_webcam_snapshot()
    if cam_bytes:
        return web.Response(body=cam_bytes, content_type="image/jpeg")
    else:
        return web.Response(text="Webcam görüntüsü yok", status=404)

async def start_webapp_server():
    if not STATIC_DIR.exists():
        STATIC_DIR.mkdir(parents=True, exist_ok=True)
        
    app = web.Application()
    
    # Rotalar
    app.router.add_get("/", handle_index)
    app.router.add_get("/api/status", api_status)
    app.router.add_get("/api/files", api_files)
    app.router.add_post("/api/control", api_control)
    app.router.add_get("/api/snapshot", api_snapshot)
    
    # Statik klasör (CSS, JS, resimler)
    app.router.add_static("/static/", path=STATIC_DIR, name="static")
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, config.webapp_host, config.webapp_port)
    await site.start()
    print(f"[START] Telegram Mini App Web Sunucusu calisiyor: http://{config.webapp_host}:{config.webapp_port}")

if __name__ == "__main__":
    asyncio.run(start_webapp_server())
    asyncio.get_event_loop().run_forever()
