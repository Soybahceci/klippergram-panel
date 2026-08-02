document.addEventListener("DOMContentLoaded", () => {
    const tg = window.Telegram?.WebApp;
    if (tg) {
        tg.ready();
        tg.expand();
        if (tg.setHeaderColor) tg.setHeaderColor("#0b0f19");
        if (tg.setBackgroundColor) tg.setBackgroundColor("#0b0f19");
    }

    const DOM = {
        stateBadge: document.getElementById("printer-state"),
        progressCard: document.getElementById("progress-card"),
        printFilename: document.getElementById("print-filename"),
        printProgressText: document.getElementById("print-progress-text"),
        printProgressBar: document.getElementById("print-progress-bar"),
        printDuration: document.getElementById("print-duration"),
        printZ: document.getElementById("print-z"),
        btnPause: document.getElementById("btn-pause"),
        btnResume: document.getElementById("btn-resume"),
        btnCancel: document.getElementById("btn-cancel"),
        tempExtruder: document.getElementById("temp-extruder"),
        targetExtruder: document.getElementById("target-extruder"),
        tempBed: document.getElementById("temp-bed"),
        targetBed: document.getElementById("target-bed"),
        webcamImg: document.getElementById("webcam-img"),
        btnCamRefresh: document.getElementById("btn-cam-refresh"),
        btnRefresh: document.getElementById("btn-refresh"),
        btnLed: document.getElementById("btn-led"),
        filesList: document.getElementById("files-list"),
        btnFilesRefresh: document.getElementById("btn-files-refresh"),
        toast: document.getElementById("toast"),
        consoleOutput: document.getElementById("console-output"),
        consoleInput: document.getElementById("console-input"),
        btnConsoleSend: document.getElementById("btn-console-send")
    };

    function showToast(message, isError = false) {
        DOM.toast.textContent = message;
        DOM.toast.style.borderColor = isError ? "var(--danger)" : "var(--success)";
        DOM.toast.classList.add("show");
        setTimeout(() => DOM.toast.classList.remove("show"), 3000);
    }

    async function apiCall(endpoint, method = "GET", body = null) {
        try {
            const options = { method, headers: {} };
            if (body) {
                options.headers["Content-Type"] = "application/json";
                options.body = JSON.stringify(body);
            }
            const res = await fetch(endpoint, options);
            const data = await res.json();
            if (data.error) {
                showToast(data.message || "Bir hata oluştu", true);
            }
            return data;
        } catch (err) {
            console.error("API Hatası:", err);
            showToast("Sunucuya bağlanılamadı!", true);
            return null;
        }
    }

    async function updateStatus() {
        const data = await apiCall("/api/status");
        if (!data || data.error) return;

        // Durum rolu
        const stateMap = {
            "printing": { text: "Çalışıyor", class: "state-printing" },
            "standby": { text: "Beklemede", class: "state-standby" },
            "complete": { text: "Tamamlandı", class: "state-printing" },
            "error": { text: "HATA!", class: "state-error" },
            "paused": { text: "Duraklatıldı", class: "state-standby" }
        };
        const st = stateMap[data.state] || { text: data.state, class: "state-standby" };
        DOM.stateBadge.textContent = st.text;
        DOM.stateBadge.className = `status-badge ${st.class}`;

        // Sıcaklıklar
        DOM.tempExtruder.textContent = data.extruder_temp;
        DOM.targetExtruder.textContent = data.extruder_target;
        DOM.tempBed.textContent = data.bed_temp;
        DOM.targetBed.textContent = data.bed_target;

        // Baskı kartı
        if (data.state === "printing" || data.state === "paused") {
            DOM.progressCard.style.display = "block";
            DOM.printFilename.textContent = data.filename;
            DOM.printProgressText.textContent = `${data.progress}%`;
            DOM.printProgressBar.style.width = `${data.progress}%`;
            DOM.printDuration.textContent = `${Math.floor(data.duration_seconds / 60)} dk`;
            DOM.printZ.textContent = `${data.position_z} mm`;

            if (data.state === "paused") {
                DOM.btnPause.style.display = "none";
                DOM.btnResume.style.display = "inline-block";
            } else {
                DOM.btnPause.style.display = "inline-block";
                DOM.btnResume.style.display = "none";
            }
        } else {
            DOM.progressCard.style.display = "none";
        }
    }

    async function loadFiles() {
        DOM.filesList.innerHTML = `<li class="loading-item">Dosyalar yükleniyor...</li>`;
        const data = await apiCall("/api/files");
        if (!data || !data.files) {
            DOM.filesList.innerHTML = `<li class="loading-item">Dosya yüklenemedi.</li>`;
            return;
        }

        if (data.files.length === 0) {
            DOM.filesList.innerHTML = `<li class="loading-item">Kayıtlı G-code dosyası yok.</li>`;
            return;
        }

        DOM.filesList.innerHTML = "";
        data.files.forEach(f => {
            const li = document.createElement("li");
            li.className = "file-item";
            
            const span = document.createElement("span");
            span.className = "file-item-name";
            span.textContent = f.filename;
            span.title = f.filename;

            const btn = document.createElement("button");
            btn.className = "btn-print";
            btn.textContent = "🖨️ Yazdır";
            btn.onclick = () => confirmPrint(f.filename);

            li.appendChild(span);
            li.appendChild(btn);
            DOM.filesList.appendChild(li);
        });
    }

    function confirmAction(text, callback) {
        if (tg && tg.showConfirm) {
            tg.showConfirm(text, (confirmed) => {
                if (confirmed) callback();
            });
        } else {
            if (confirm(text)) callback();
        }
    }

    function confirmPrint(filename) {
        confirmAction(`"${filename}" baskısı başlatılsın mı?\n\nLÜTFEN TABLANIN BOŞ OLDUĞUNDAN EMİN OLUN!`, async () => {
            showToast("Baskı komutu gönderiliyor...");
            const res = await apiCall("/api/control", "POST", { action: "start_print", filename });
            if (res && !res.error) {
                showToast("Baskı başlatıldı!");
                updateStatus();
            }
        });
    }

    // Buton Olayları
    DOM.btnRefresh.addEventListener("click", () => {
        updateStatus();
        showToast("Durum güncellendi!");
    });

    DOM.btnCamRefresh.addEventListener("click", () => {
        DOM.webcamImg.src = `/api/snapshot?t=${new Date().getTime()}`;
        showToast("Kamera yenilendi");
    });

    DOM.btnPause.addEventListener("click", async () => {
        confirmAction("Baskıyı duraklatmak istediğinize emin misiniz?", async () => {
            await apiCall("/api/control", "POST", { action: "pause" });
            showToast("Baskı duraklatıldı");
            updateStatus();
        });
    });

    DOM.btnResume.addEventListener("click", async () => {
        await apiCall("/api/control", "POST", { action: "resume" });
        showToast("Baskıya devam ediliyor");
        updateStatus();
    });

    DOM.btnCancel.addEventListener("click", () => {
        confirmAction("⚠️ DİKKAT: Mevcut baskıyı tamamen İPTAL etmek istediğinize emin misiniz?", async () => {
            await apiCall("/api/control", "POST", { action: "cancel" });
            showToast("Baskı iptal edildi!", true);
            updateStatus();
        });
    });

    DOM.btnLed.addEventListener("click", async () => {
        await apiCall("/api/control", "POST", { action: "toggle_led" });
        showToast("LED komutu gönderildi");
    });

    document.querySelectorAll(".btn-preset").forEach(btn => {
        btn.addEventListener("click", async () => {
            const ext = parseInt(btn.dataset.ext);
            const bed = parseInt(btn.dataset.bed);
            const title = btn.textContent;
            confirmAction(`${title} profilini uygulamak istiyor musunuz?`, async () => {
                await apiCall("/api/control", "POST", { action: "set_temp", extruder: ext, bed: bed });
                showToast(`${title} komutu iletildi`);
                updateStatus();
            });
        });
    });

    DOM.btnFilesRefresh.addEventListener("click", loadFiles);

    // G-Code Console Olayları
    async function sendConsoleCommand() {
        const cmd = DOM.consoleInput.value.trim();
        if (!cmd) return;
        
        DOM.consoleInput.value = "";
        
        // Kullanıcının yazdığını ekrana bas
        const cmdLine = document.createElement("div");
        cmdLine.className = "console-line command";
        cmdLine.textContent = "> " + cmd;
        DOM.consoleOutput.appendChild(cmdLine);
        DOM.consoleOutput.scrollTop = DOM.consoleOutput.scrollHeight;
        
        const res = await apiCall("/api/control", "POST", { action: "console_command", script: cmd });
        if (res && !res.error && res.message) {
            const resLine = document.createElement("div");
            resLine.className = "console-line response";
            resLine.textContent = res.message;
            DOM.consoleOutput.appendChild(resLine);
            DOM.consoleOutput.scrollTop = DOM.consoleOutput.scrollHeight;
        }
    }

    DOM.btnConsoleSend.addEventListener("click", sendConsoleCommand);
    DOM.consoleInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") sendConsoleCommand();
    });

    // Başlangıç yüklemeleri ve periyodik güncelleme
    updateStatus();
    loadFiles();
    setInterval(updateStatus, 3000); // 3 saniyede bir canlı durum güncellemesi
});
