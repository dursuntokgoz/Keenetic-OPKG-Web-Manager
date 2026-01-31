# Keenetic OPKG Web Manager 🚀

[TR] Keenetic yönlendiriciler için hafif, Python tabanlı bir OPKG paket yönetim arayüzü.
[EN] A lightweight, Python-based OPKG package management interface for Keenetic routers.

---

## 🇹🇷 Türkçe Açıklama

Bu proje, Keenetic cihazlar üzerindeki Entware (OPKG) paketlerini bir web arayüzü üzerinden yönetmenizi sağlar. SSH terminaline girmeden paketleri arayabilir, yükleyebilir ve kaldırabilirsiniz.

### ✨ Özellikler
* **Canlı Liste:** Doğrudan `opkg list` komutuyla güncel repo listesini çeker.
* **Durum Kontrolü:** Hangi paketlerin yüklü olduğunu otomatik tespit eder.
* **Tek Tıkla İşlem:** Kolayca paket yükleme ve silme.
* **Entegre Terminal:** İşlem çıktılarını anlık olarak arayüzden takip edin.
* **Hafif:** Keenetic Titan ve benzeri cihazlar için optimize edilmiştir.

### 🛠 Kurulum
1.  **Gereksinimler:**
    ```bash
    opkg update
    opkg install python3 python3-pip
    pip install flask
    ```
2.  **Dosyaları Kopyalayın:** Proje dosyalarını `/opt/etc/my_manager` klasörüne yerleştirin.
3.  **Çalıştırın:**
    ```bash
    python3 app.py
    ```
4.  **Erişim:** Tarayıcıdan `http://ROUTER_IP:5000` adresine gidin.

---

## 🇺🇸 English Description

This project allows you to manage Entware (OPKG) packages on Keenetic devices via a web interface. You can search, install, and uninstall packages without using the SSH terminal.

### ✨ Features
* **Live Listing:** Fetches the current repository list directly with the `opkg list` command.
* **Status Check:** Automatically detects which packages are currently installed.
* **One-Click Actions:** Easily install or remove packages.
* **Integrated Terminal:** Monitor process outputs in real-time from the dashboard.
* **Lightweight:** Optimized for Keenetic Titan and similar embedded devices.

### 🛠 Installation
1.  **Requirements:**
    ```bash
    opkg update
    opkg install python3 python3-pip
    pip install flask
    ```
2.  **Copy Files:** Place the project files into the `/opt/etc/my_manager` directory.
3.  **Run:**
    ```bash
    python3 app.py
    ```
4.  **Access:** Open your browser and go to `http://ROUTER_IP:5000`.

---

## 📂 Project Structure / Proje Yapısı
```text
/opt/etc/my_manager/
├── app.py              # Backend logic (Python/Flask)
├── templates/
│   └── index.html      # Modern UI (Tailwind CSS)
├── init.d/
│   └── S99package_manager # Autostart script
└── README.md           # Documentation
