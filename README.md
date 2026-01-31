# Keenetic OPKG Web Manager 🚀

[TR] Keenetic yönlendiriciler için hafif, Python tabanlı bir OPKG paket yönetim arayüzü.
[EN] A lightweight, Python-based OPKG package management interface for Keenetic routers.

---

## 🇹🇷 Türkçe Açıklama

Bu proje, Keenetic cihazlar üzerindeki Entware (OPKG) paketlerini bir web arayüzü üzerinden yönetmenizi sağlar.

### ✨ Özellikler
* **Canlı Liste:** `opkg list` ile güncel repo verileri.
* **Durum Kontrolü:** Yüklü paketleri otomatik tespit eder (YÜKLÜ/DEPO).
* **Tek Tıkla İşlem:** Paket yükleme ve kaldırma.
* **Entegre Terminal:** İşlem çıktılarını anlık izleme.

### 🛠 Kurulum ve Otomatik Başlatma
1.  **Gereksinimler:**
    ```bash
    opkg update
    opkg install python3 python3-pip
    pip install flask
    ```
2.  **Dosya Yapısı:**
    Dosyaları `/opt/etc/my_manager/` altına kopyalayın. `templates/index.html` dosyasının doğru yerde olduğundan emin olun.
3.  **Otomatik Başlatma Ayarı (Servis):**
    Cihaz her açıldığında uygulamanın başlaması için şu komutları çalıştırın:
    ```bash
    # Servis dosyasını oluşturun
    nano /opt/etc/init.d/S99package_manager
    ```
    İçine servis betiğini yapıştırın ve kaydedin. Ardından izinleri verin:
    ```bash
    chmod +x /opt/etc/init.d/S99package_manager
    # Servisi hemen başlatın
    /opt/etc/init.d/S99package_manager start
    ```

---

## 🇺🇸 English Description

Manage your Entware (OPKG) packages on Keenetic devices via a modern web interface.

### ✨ Features
* **Live Listing:** Real-time data from `opkg list`.
* **Status Check:** Automatically detects installed packages (INSTALLED/REPO).
* **One-Click Actions:** Fast install and uninstall buttons.
* **Integrated Terminal:** Real-time process logs on the dashboard.

### 🛠 Installation & Autostart
1.  **Requirements:**
    ```bash
    opkg update
    opkg install python3 python3-pip
    pip install flask
    ```
2.  **File Structure:**
    Place files into `/opt/etc/my_manager/`. Ensure `templates/index.html` is in the correct sub-directory.
3.  **Autostart Configuration (Service):**
    To start the app automatically on boot, run the following commands:
    ```bash
    # Create the service file
    nano /opt/etc/init.d/S99package_manager
    ```
    Paste the service script, save it, and set permissions:
    ```bash
    chmod +x /opt/etc/init.d/S99package_manager
    # Start the service immediately
    /opt/etc/init.d/S99package_manager start
    ```

---

## 📂 Project Structure / Proje Yapısı
```text
/opt/etc/my_manager/
├── app.py              # Backend (Python/Flask)
├── templates/
│   └── index.html      # UI (Tailwind CSS)
└── README.md           # Documentation
/opt/etc/init.d/
└── S99package_manager  # Service Script (Autostart)
