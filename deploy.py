import paramiko
import os
import sys
import json
import time

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
    except Exception:
        pass

def print_banner():
    print("=" * 70)
    print(" 🚀 KLIPPERGRAM - EVRENSEL 3D YAZICI TELEGRAM PANELİ OTOMATİK KURULUM")
    print("=" * 70)
    print(" Bu betik, KlipperGram Telegram botunu ve görsel web panelini")
    print(" doğrudan 3D yazıcınızın içine (Linux arka plan servisi) kuracaktır.")
    print("=" * 70)
    print()

def setup_config():
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    example_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.example.json")
    
    # Mevcut config kontrolü
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            token = cfg.get("telegram", {}).get("bot_token", "")
            if token and token != "YOUR_TELEGRAM_BOT_TOKEN_HERE":
                print(f"[i] Mevcut yapılandırma dosyası (config.json) bulundu.")
                print(f"    -> Bot Token: {token[:8]}...{token[-4:]}")
                print(f"    -> Yetkili ID: {cfg.get('telegram', {}).get('allowed_users', [])}")
                print(f"    -> Moonraker URL: {cfg.get('moonraker', {}).get('url', 'http://127.0.0.1')}")
                ans = input("\n👉 Mevcut ayarlar ile kuruluma devam edilsin mi? [E/h]: ").strip().lower()
                if ans in ["", "e", "evet", "y", "yes"]:
                    return cfg
        except Exception as e:
            print(f"[UYARI] config.json okunamadı ({e}), yeniden oluşturulacak.")

    print("--- ⚙️ YAPILANDIRMA BİLGİLERİ GİRİŞİ ---")
    print("Lütfen Telegram botunuzu yazıcınıza bağlamak için bilgileri girin.\n")
    
    bot_token = ""
    while not bot_token or bot_token == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        bot_token = input("1) Telegram Bot Token (@BotFather'dan aldığınız): ").strip()
        if not bot_token:
            print("   [HATA] Bot Token boş olamaz! Lütfen tekrar girin.")

    user_id_str = ""
    while not user_id_str.isdigit():
        user_id_str = input("2) Telegram Kullanıcı ID'niz (@userinfobot'tan aldığınız sayısal ID): ").strip()
        if not user_id_str.isdigit():
            print("   [HATA] Kullanıcı ID sadece rakamlardan oluşmalıdır (Örn: 7557861007).")
    user_id = int(user_id_str)

    # Örnek config üzerinden oluştur
    if os.path.exists(example_path):
        with open(example_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    else:
        cfg = {
            "telegram": {"bot_token": "", "allowed_users": [], "enable_notifications": True, "notify_on_layer_change": False, "notify_interval_minutes": 15},
            "moonraker": {"url": "http://127.0.0.1", "api_key": ""},
            "webcam": {"enabled": True, "snapshot_url": "http://127.0.0.1/webcam/?action=snapshot", "flip_horizontal": False, "flip_vertical": False},
            "webapp": {"enabled": True, "host": "0.0.0.0", "port": 8085, "public_url": ""}
        }

    cfg["telegram"]["bot_token"] = bot_token
    cfg["telegram"]["allowed_users"] = [user_id]
    cfg["moonraker"]["url"] = "http://127.0.0.1"
    
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    
    print("\n✅ Yapılandırma başarıyla 'config.json' dosyasına kaydettirildi!\n")
    return cfg

def main():
    print_banner()
    cfg = setup_config()
    
    print("--- 🌐 3D YAZICI BAĞLANTI AYARLARI ---")
    host = input("👉 3D Yazıcınızın IP Adresi [Varsayılan: 192.168.1.130]: ").strip()
    if not host:
        host = "192.168.1.130"
    
    user = input("👉 SSH Kullanıcı Adı [Varsayılan: mks]: ").strip()
    if not user:
        user = "mks"

    passwords = ["makerbase", "elegoo", "mks", "makerbase.123", "admin", "123456", ""]
    
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    connected_pass = None
    print(f"\n[1/4] {host} adresine SSH bağlantısı deneniyor...")
    
    for pw in passwords:
        try:
            client.connect(hostname=host, username=user, password=pw, timeout=5)
            connected_pass = pw
            print(f"[OK] Bağlantı başarılı! (Varsayılan şifre kabul edildi)")
            break
        except paramiko.AuthenticationException:
            continue
        except Exception:
            break

    if connected_pass is None and connected_pass != "":
        # Varsayılanlar olmadıysa kullanıcıdan iste
        custom_pw = input(f"👉 '{user}@{host}' için SSH şifresini girin: ").strip()
        try:
            client.connect(hostname=host, username=user, password=custom_pw, timeout=5)
            connected_pass = custom_pw
            print("[OK] Bağlantı başarılı!")
        except Exception as e:
            print(f"\n[HATA] Yazıcıya bağlanılamadı! Lütfen ağ bağlantınızı ve şifrenizi kontrol edin.\nDetay: {e}")
            sys.exit(1)

    # SFTP ile dosyaları aktar
    print("\n[2/4] Proje dosyaları yazıcıya yükleniyor (SFTP)...")
    sftp = client.open_sftp()
    
    remote_dir = f"/home/{user}/klippergram"
    try:
        sftp.mkdir(remote_dir)
    except Exception:
        pass

    local_dir = os.path.dirname(os.path.abspath(__file__))
    files_to_send = [
        "config.json", "config.example.json", "bot.py", "webapp.py",
        "moonraker_client.py", "notifications.py", "config.py",
        "requirements.txt", "install.sh", "README.md", "LICENSE"
    ]
    
    for fname in files_to_send:
        local_path = os.path.join(local_dir, fname)
        remote_path = f"{remote_dir}/{fname}"
        if os.path.exists(local_path):
            sftp.put(local_path, remote_path)
            print(f"  -> Yüklendi: {fname}")
            
    # static klasörünü aktar
    try:
        sftp.mkdir(f"{remote_dir}/static")
    except Exception:
        pass

    static_dir = os.path.join(local_dir, "static")
    if os.path.exists(static_dir):
        for fname in os.listdir(static_dir):
            local_path = os.path.join(static_dir, fname)
            remote_path = f"{remote_dir}/static/{fname}"
            if os.path.isfile(local_path):
                sftp.put(local_path, remote_path)
                print(f"  -> Yüklendi: static/{fname}")
                
    sftp.close()

    # Yazıcıda kurulumu başlat
    print("\n[3/4] Yazıcıda kurulum betiği çalıştırılıyor (Python sanal ortamı ve klippergram servisi)...")
    print("⚠️  Bu işlem ilk kurulumda bağımlılıklar yüklenirken 1-2 dakika sürebilir, lütfen bekleyin...\n")
    
    commands = [
        f"chmod +x {remote_dir}/install.sh",
        f"cd {remote_dir} && echo '{connected_pass}' | sudo -S -v && ./install.sh"
    ]
    
    for cmd in commands:
        stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)
        if connected_pass:
            stdin.write(connected_pass + "\n")
            stdin.flush()
        
        for line in iter(stdout.readline, ""):
            print(line, end="")
            
        status = stdout.channel.recv_exit_status()
        if status != 0:
            err = stderr.read().decode()
            print(f"\n[HATA] Kurulum sırasında hata oluştu (Kod {status}): {err}")
            client.close()
            sys.exit(1)

    print("\n[4/4] Servisin canlı çalışma durumu doğrulanıyor...")
    time.sleep(2)
    stdin, stdout, stderr = client.exec_command(f"systemctl status klippergram.service --no-pager", get_pty=True)
    for line in iter(stdout.readline, ""):
        print("  " + line.strip())

    client.close()
    
    print("\n" + "=" * 70)
    print(" KLIPPERGRAM KURULUMU TAMAMLANDI")
    print("=" * 70)
    print(" Telegram üzerinden botunuza /start komutunu göndererek")
    print(" yönetim panelini kullanmaya başlayabilirsiniz.")
    print("=" * 70)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[i] Kurulum kullanıcı tarafından iptal edildi.")
        sys.exit(0)
