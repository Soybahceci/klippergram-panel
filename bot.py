import asyncio
import logging
import sys
import io
import time
from PIL import Image

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
    except Exception:
        pass

from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputFile, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
from config import config
from moonraker_client import moonraker_client
from notifications import NotificationManager

# Logging ayarları
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=config.bot_token)
dp = Dispatcher(bot)

# Canlı izleme oturumlarını takip eden sözlük
active_live_views = {}

def check_auth(user_id: int) -> bool:
    allowed = config.is_user_allowed(user_id)
    if not allowed:
        logger.warning(f"Yetkisiz kullanıcı denemesi: ID={user_id}")
    return allowed

def get_main_keyboard() -> InlineKeyboardMarkup:
    # WebApp URL kontrolü
    webapp_url = config.webapp_public_url
    if not webapp_url:
        webapp_url = f"http://{config.moonraker_url.replace('http://', '').replace('https://', '').split(':')[0]}:{config.webapp_port}"
        if not webapp_url.startswith("http"):
            webapp_url = f"http://{webapp_url}"
    
    if webapp_url.startswith("https://"):
        web_btn = InlineKeyboardButton(text="🌐 Görsel Web Paneli (Mini App)", web_app=WebAppInfo(url=webapp_url))
    else:
        web_btn = InlineKeyboardButton(text="🌐 Görsel Web Paneli (Tarayıcıda Aç)", url=webapp_url)
    
    buttons = [
        [
            web_btn
        ],
        [
            InlineKeyboardButton(text="📊 Durum Raporu", callback_data="status"),
            InlineKeyboardButton(text="📷 Tek Kare Foto", callback_data="cam")
        ],
        [
            InlineKeyboardButton(text="🔴 Canlı İzle (Anlık Yenileme)", callback_data="live_view"),
            InlineKeyboardButton(text="🎬 5sn Video/GIF Kaydı", callback_data="cam_video")
        ],
        [
            InlineKeyboardButton(text="🌡 Isıtma Menüsü", callback_data="temp_menu"),
            InlineKeyboardButton(text="📁 G-code Dosyaları", callback_data="files")
        ],
        [
            InlineKeyboardButton(text="⏸ Duraklat", callback_data="pause"),
            InlineKeyboardButton(text="▶️ Devam Et", callback_data="resume"),
            InlineKeyboardButton(text="⏹ İptal", callback_data="cancel")
        ],
        [
            InlineKeyboardButton(text="💡 LED Işık", callback_data="toggle_led"),
            InlineKeyboardButton(text="🚨 Acil Durdur (E-Stop)", callback_data="estop")
        ],
        [
            InlineKeyboardButton(text="🧹 Tablayı Temizle", callback_data="clear_bed_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_clear_bed_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="🧹 Z=3mm (Küçük Parça)", callback_data="clear_bed_3")
        ],
        [
            InlineKeyboardButton(text="🧹 Z=5mm (Orta Parça)", callback_data="clear_bed_5")
        ],
        [
            InlineKeyboardButton(text="🧹 Z=10mm (Büyük Parça)", callback_data="clear_bed_10")
        ],
        [
            InlineKeyboardButton(text="🔙 Ana Menü", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_live_view_keyboard(msg_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="⏹ Durdur", callback_data=f"live_stop_{msg_id}"),
            InlineKeyboardButton(text="🔄 60sn Yenile", callback_data=f"live_restart_{msg_id}")
        ],
        [
            InlineKeyboardButton(text="🔙 Ana Menü", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_temp_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="🟢 PLA (200°C / 60°C)", callback_data="set_temp_pla"),
            InlineKeyboardButton(text="🟡 PETG (230°C / 70°C)", callback_data="set_temp_petg")
        ],
        [
            InlineKeyboardButton(text="🔴 ABS (250°C / 90°C)", callback_data="set_temp_abs"),
            InlineKeyboardButton(text="🔥 TPU (220°C / 50°C)", callback_data="set_temp_tpu")
        ],
        [
            InlineKeyboardButton(text="❄️ Soğut (0°C)", callback_data="set_temp_cool")
        ],
        [
            InlineKeyboardButton(text="🔙 Ana Menü", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_persistent_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.row(KeyboardButton("🤖 Ana Menü"), KeyboardButton("🧹 Tablayı Temizle"))
    kb.row(KeyboardButton("🚨 Acil Durdur!"))
    return kb

@dp.message_handler(commands=["start", "help", "menu"])
async def cmd_start(message: types.Message):
    if not check_auth(message.from_user.id):
        return await message.reply("⛔ **Yetkisiz Erişim!** Bu yazıcıyı kontrol etme yetkiniz yok.", parse_mode="Markdown")
    
    text = (
        "🤖 **KlipperGram - Evrensel 3D Yazıcı Yönetim Paneline Hoş Geldiniz!**\n\n"
        "Klipper tabanlı yazıcınızı aşağıdaki butonlar ile kolayca yönetebilir, anlık durumunu inceleyebilir veya canlı kamera takibi yapabilirsiniz.\n\n"
        "💡 *İpucu:* Konsol komutu göndermek için `/gcode <komut>` yazabilirsiniz. (Örn: `/gcode STATUS`)"
    )
    await message.answer("Klavye butonları aktifleştirildi! 👇", reply_markup=get_persistent_keyboard())
    await message.answer(text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

@dp.message_handler(commands=["gcode", "c", "console"])
async def cmd_gcode(message: types.Message):
    if not check_auth(message.from_user.id):
        return
    
    command = message.get_args().strip()
    if not command:
        return await message.reply("⚠️ **Kullanım:** `/gcode <komut>`\nÖrnek: `/gcode STATUS` veya `/c G28`", parse_mode="Markdown")
        
    wait_msg = await message.reply(f"⏳ Komut gönderiliyor: `{command}`...", parse_mode="Markdown")
    response = await moonraker_client.send_and_read_console(command)
    
    # Çok uzun yanıtları Telegram limitine takılmaması için sınırla
    if len(response) > 3500:
        response = response[:3500] + "\n... (Çıktı çok uzun, kırpıldı)"
        
    await bot.edit_message_text(f"🖥 **Konsol Çıktısı:**\n```text\n{response}\n```", chat_id=message.chat.id, message_id=wait_msg.message_id, parse_mode="Markdown")

@dp.message_handler(commands=["status"])
async def cmd_status(message: types.Message):
    if not check_auth(message.from_user.id):
        return
    await send_status_report(message.chat.id)

async def send_status_report(chat_id: int):
    status = await moonraker_client.get_printer_status()
    if status.get("error"):
        await bot.send_message(chat_id, f"❌ **Moonraker Bağlantı Hatası:**\n`{status.get('message')}`", parse_mode="Markdown")
        return

    state_emojis = {
        "printing": "🟢 Çalışıyor (Baskıda)",
        "standby": "🟡 Hazır (Beklemede)",
        "complete": "🏁 Tamamlandı",
        "error": "🔴 HATA!",
        "paused": "⏸ Duraklatıldı"
    }
    state_str = state_emojis.get(status.get("state"), status.get("state", "Bilinmiyor"))

    text = (
        f"📊 **YAZICI DURUM RAPORU**\n\n"
        f"🖥 **Durum:** {state_str}\n"
        f"📄 **Dosya:** `{status.get('filename')}`\n"
        f"⏳ **İlerleme:** %{status.get('progress')}\n"
        f"⏱ **Geçen Süre:** {status.get('duration_seconds') // 60} dakika\n\n"
        f"🔥 **Nozzle:** {status.get('extruder_temp')}°C / {status.get('extruder_target')}°C\n"
        f"🛏 **Tabla:** {status.get('bed_temp')}°C / {status.get('bed_target')}°C\n"
        f"💨 **Fan Hızı:** %{status.get('fan_speed')}\n"
        f"📐 **Z Konumu:** {status.get('position_z')} mm"
    )

    cam_bytes = await moonraker_client.get_webcam_snapshot() if config.webcam_enabled else None
    if cam_bytes:
        photo = InputFile(io.BytesIO(cam_bytes), filename="status.jpg")
        await bot.send_photo(chat_id, photo=photo, caption=text, reply_markup=get_main_keyboard(), parse_mode="Markdown")
    else:
        await bot.send_message(chat_id, text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

@dp.message_handler(commands=["cam"])
async def cmd_cam(message: types.Message):
    if not check_auth(message.from_user.id):
        return
    await send_cam_snapshot(message.chat.id)

async def send_cam_snapshot(chat_id: int):
    cam_bytes = await moonraker_client.get_webcam_snapshot()
    if cam_bytes:
        photo = InputFile(io.BytesIO(cam_bytes), filename="cam.jpg")
        await bot.send_photo(chat_id, photo=photo, caption="📷 **Anlık Kamera Görüntüsü**", reply_markup=get_main_keyboard(), parse_mode="Markdown")
    else:
        await bot.send_message(chat_id, "⚠️ Kamera görüntüsü alınamadı veya ayar kapalı.", reply_markup=get_main_keyboard())

async def send_live_view_start(chat_id: int):
    cam_bytes = await moonraker_client.get_webcam_snapshot()
    if not cam_bytes:
        await bot.send_message(chat_id, "⚠️ Kamera görüntüsü alınamadı veya ayar kapalı.", reply_markup=get_main_keyboard())
        return

    photo = InputFile(io.BytesIO(cam_bytes), filename="live.jpg")
    caption = f"🔴 **Canlı İzleme Aktif (60s)**\n⏱ Başlangıç: `{time.strftime('%H:%M:%S')}`\n*Her ~3 saniyede bir fotoğraf yerinde güncellenir.*"
    msg = await bot.send_photo(chat_id, photo=photo, caption=caption, parse_mode="Markdown")
    
    try:
        await bot.edit_message_reply_markup(chat_id=chat_id, message_id=msg.message_id, reply_markup=get_live_view_keyboard(msg.message_id))
    except Exception:
        pass
    
    active_live_views[(chat_id, msg.message_id)] = True
    asyncio.create_task(_live_view_loop(chat_id, msg.message_id))

async def _live_view_loop(chat_id: int, message_id: int):
    for i in range(20): # 20 kare ~ 60 saniye
        await asyncio.sleep(3)
        if not active_live_views.get((chat_id, message_id), False):
            break
        
        cam_bytes = await moonraker_client.get_webcam_snapshot()
        if cam_bytes and active_live_views.get((chat_id, message_id), False):
            try:
                media = types.InputMediaPhoto(
                    media=InputFile(io.BytesIO(cam_bytes), filename="live.jpg"),
                    caption=f"🔴 **Canlı İzleme Aktif**\n⏱ Güncellendi: `{time.strftime('%H:%M:%S')}`\n⏳ Kalan: {(20 - i - 1) * 3}s",
                    parse_mode="Markdown"
                )
                await bot.edit_message_media(chat_id=chat_id, message_id=message_id, media=media, reply_markup=get_live_view_keyboard(message_id))
            except Exception:
                pass

    active_live_views[(chat_id, message_id)] = False
    try:
        await bot.edit_message_caption(chat_id=chat_id, message_id=message_id, caption="⏹ *Canlı İzleme Süresi Bitti veya Durduruldu.*", reply_markup=get_main_keyboard(), parse_mode="Markdown")
    except Exception:
        pass

async def send_video_gif(chat_id: int):
    status_msg = await bot.send_message(chat_id, "⏳ **Kameradan 5 saniyelik hareketli video yakalanıyor...** Lütfen bekleyin 🎥", parse_mode="Markdown")
    
    frames = []
    for _ in range(12): # ~4-5 saniye
        cam_bytes = await moonraker_client.get_webcam_snapshot()
        if cam_bytes:
            try:
                img = Image.open(io.BytesIO(cam_bytes))
                img.thumbnail((480, 360)) # Hızlı işleme
                frames.append(img)
            except Exception as e:
                logger.error(f"Frame hatası: {e}")
        await asyncio.sleep(0.35)

    try:
        await bot.delete_message(chat_id, status_msg.message_id)
    except Exception:
        pass

    if frames:
        gif_bytes = io.BytesIO()
        frames[0].save(
            gif_bytes,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            duration=350,
            loop=0
        )
        gif_bytes.seek(0)
        video_file = InputFile(gif_bytes, filename="live_stream.gif")
        await bot.send_animation(chat_id, animation=video_file, caption="🎬 **5 Saniyelik Hareketli Kamera Kaydı**", reply_markup=get_main_keyboard(), parse_mode="Markdown")
    else:
        await bot.send_message(chat_id, "⚠️ Hareketli görüntü oluşturulamadı.", reply_markup=get_main_keyboard())

@dp.message_handler(commands=["files"])
async def cmd_files(message: types.Message):
    if not check_auth(message.from_user.id):
        return
    await send_file_list(message.chat.id)

async def send_file_list(chat_id: int):
    files = await moonraker_client.get_gcode_files()
    if not files:
        await bot.send_message(chat_id, "📁 Kayıtlı G-code dosyası bulunamadı.", reply_markup=get_main_keyboard())
        return

    buttons = []
    for f in files[:8]: # İlk 8 dosya
        fname = f.get("filename", "")
        buttons.append([InlineKeyboardButton(text=f"🖨️ {fname}", callback_data=f"print_confirm_{fname}")])
    
    buttons.append([InlineKeyboardButton(text="🔙 Ana Menü", callback_data="main_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await bot.send_message(chat_id, "📁 **Yazıcıdaki G-code Dosyaları:**\nBaskıyı başlatmak için bir dosyaya tıklayın:", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query_handler(lambda c: c.data == "clear_bed_menu")
async def process_clear_bed_menu(callback_query: types.CallbackQuery):
    if not check_auth(callback_query.from_user.id): return
    await bot.edit_message_text(
        "🧹 **Tablayı Temizleme (Otomatik Sıyırma)**\n\n"
        "Nozzle'ın parçaya hangi yükseklikten (Z ekseni) çarpmasını istediğinizi seçin.\n\n"
        "⚠️ *Yazıcı 'Homed' durumunu kaybettiyse güvenlik gereği hareket etmeyi reddeder.*",
        chat_id=callback_query.message.chat.id,
        message_id=callback_query.message.message_id,
        reply_markup=get_clear_bed_keyboard(),
        parse_mode="Markdown"
    )

@dp.callback_query_handler(lambda c: c.data.startswith("clear_bed_") and c.data != "clear_bed_menu")
async def process_clear_bed_action(callback_query: types.CallbackQuery):
    if not check_auth(callback_query.from_user.id): return
    try:
        strike_z = float(callback_query.data.split("_")[2])
    except:
        return
        
    await bot.answer_callback_query(callback_query.id, text=f"🚀 Tablayı temizleme başlatıldı (Z={strike_z}mm)", show_alert=True)
    await moonraker_client.clear_bed(strike_z)

@dp.callback_query_handler(lambda c: True)
async def callback_handler(callback: types.CallbackQuery):
    if not check_auth(callback.from_user.id):
        await callback.answer("⛔ Yetkisiz işlem!", show_alert=True)
        return

    data = callback.data
    chat_id = callback.message.chat.id

    if data == "status":
        await send_status_report(chat_id)
        await callback.answer()
    elif data == "cam":
        await send_cam_snapshot(chat_id)
        await callback.answer()
    elif data == "live_view":
        await callback.answer("🔴 Canlı izleme başlatılıyor...")
        asyncio.create_task(send_live_view_start(chat_id))
    elif data == "cam_video":
        await callback.answer("🎬 Hareketli kayıt başlatılıyor...")
        asyncio.create_task(send_video_gif(chat_id))
    elif data and data.startswith("live_stop_"):
        msg_id = int(data.replace("live_stop_", ""))
        active_live_views[(chat_id, msg_id)] = False
        await callback.answer("⏹ Canlı izleme durduruldu.")
    elif data and data.startswith("live_restart_"):
        msg_id = int(data.replace("live_restart_", ""))
        active_live_views[(chat_id, msg_id)] = False # Eskisini durdur
        await callback.answer("🔄 Yeniden başlatılıyor...")
        asyncio.create_task(send_live_view_start(chat_id))
    elif data == "temp_menu":
        await callback.message.edit_text("🌡 **Hazır Sıcaklık Profilleri**\nLütfen bir profil seçin:", reply_markup=get_temp_keyboard(), parse_mode="Markdown")
        await callback.answer()
    elif data == "main_menu":
        await callback.message.edit_text("🤖 **KlipperGram - Ana Menü**", reply_markup=get_main_keyboard(), parse_mode="Markdown")
        await callback.answer()
    elif data == "files":
        await send_file_list(chat_id)
        await callback.answer()
    elif data in ["pause", "resume", "cancel"]:
        res = await moonraker_client.control_job(data)
        if not res.get("error"):
            await callback.answer(f"✅ İşlem başarılı: {data.upper()}", show_alert=True)
            await send_status_report(chat_id)
        else:
            await callback.answer(f"❌ Hata: {res.get('message')}", show_alert=True)
    elif data == "estop":
        res = await moonraker_client.emergency_stop()
        if not res.get("error"):
            await callback.answer("🚨 ACİL DURDURMA KOMUTU GÖNDERİLDİ!", show_alert=True)
        else:
            await callback.answer(f"❌ Hata: {res.get('message')}", show_alert=True)
    elif data == "toggle_led":
        res = await moonraker_client.toggle_led("caselight")
        await callback.answer("💡 LED ışık komutu iletildi.")
    elif data and data.startswith("set_temp_"):
        profile = data.replace("set_temp_", "")
        temps = {
            "pla": (200, 60),
            "petg": (230, 70),
            "abs": (250, 90),
            "tpu": (220, 50),
            "cool": (0, 0)
        }
        if profile in temps:
            ext, bed = temps[profile]
            res1 = await moonraker_client.set_temperature("extruder", ext)
            res2 = await moonraker_client.set_temperature("heater_bed", bed)
            if not res1.get("error") and not res2.get("error"):
                await callback.message.edit_text(f"✅ **Sıcaklıklar Ayarlandı!**\n🔥 Nozzle: {ext}°C\n🛏 Tabla: {bed}°C", reply_markup=get_main_keyboard(), parse_mode="Markdown")
            else:
                await callback.answer("❌ Sıcaklık ayarlanırken hata oluştu!", show_alert=True)
        await callback.answer()
    elif data and data.startswith("print_confirm_"):
        fname = data.replace("print_confirm_", "")
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🟢 Evet, Başlat!", callback_data=f"print_start_{fname}"),
                InlineKeyboardButton(text="❌ Vazgeç", callback_data="files")
            ]
        ])
        await callback.message.edit_text(f"🖨️ `{fname}` dosyasının baskısı başlatılsın mı?\n**Lütfen tablanın boş olduğundan emin olun!**", reply_markup=kb, parse_mode="Markdown")
        await callback.answer()
    elif data and data.startswith("print_start_"):
        fname = data.replace("print_start_", "")
        res = await moonraker_client.start_print(fname)
        if not res.get("error"):
            await callback.message.edit_text(f"🟢 **Baskı Başlatıldı!**\n📄 Dosya: `{fname}`", reply_markup=get_main_keyboard(), parse_mode="Markdown")
        else:
            await callback.message.edit_text(f"❌ **Baskı Başlatılamadı:** `{res.get('message')}`", reply_markup=get_main_keyboard(), parse_mode="Markdown")
        await callback.answer()

@dp.message_handler()
async def cmd_fallback(message: types.Message):
    logger.info(f"Mesaj alındı: ID={message.from_user.id} Text={message.text}")
    if not check_auth(message.from_user.id):
        return await message.reply(f"⛔ **Yetkisiz Erişim!** (Sizin ID'niz: `{message.from_user.id}`)\nBu yazıcıyı kontrol etme yetkiniz yok.", parse_mode="Markdown")
    
    text = message.text.strip()
    if text == "🤖 Ana Menü":
        await cmd_start(message)
        return
    elif text == "🧹 Tablayı Temizle":
        await message.answer(
            "🧹 **Tablayı Temizleme (Otomatik Sıyırma)**\n\n"
            "Nozzle'ın parçaya hangi yükseklikten çarpmasını istediğinizi seçin.\n\n"
            "⚠️ *Yazıcı 'Homed' durumunu kaybettiyse güvenlik gereği hareket etmeyi reddeder.*",
            reply_markup=get_clear_bed_keyboard(),
            parse_mode="Markdown"
        )
        return
    elif text == "🚨 Acil Durdur!":
        res = await moonraker_client.emergency_stop()
        if not res.get("error"):
            await message.answer("🚨 ACİL DURDURMA KOMUTU GÖNDERİLDİ!")
        else:
            await message.answer(f"❌ Hata: {res.get('message')}")
        return

    await message.answer(
        "🤖 **KlipperGram - Evrensel Yönetim Paneli**\n\nİşlem yapmak için aşağıdaki butonları kullanabilir veya klavye menüsünü açabilirsiniz:",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

async def on_startup(dispatcher):
    notif_manager = NotificationManager(bot)
    asyncio.create_task(notif_manager.start_monitoring())
    if config.webapp_enabled:
        from webapp import start_webapp_server
        asyncio.create_task(start_webapp_server())
    print("[START] KlipperGram - Evrensel Klipper Telegram Botu calisiyor (aiogram v2 / Python 3.7+ uyumlu)...")

if __name__ == "__main__":
    if not config.bot_token or config.bot_token == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("[HATA] Lütfen config.json içinde 'bot_token' alanını doldurun!")
        sys.exit(1)
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)
