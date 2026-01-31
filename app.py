from flask import Flask, render_template, request, jsonify
import subprocess

app = Flask(__name__)

def get_packages_status():
    """Tüm paketleri ve yüklü olup olmadıklarını opkg üzerinden canlı çeker."""
    all_packages = {}
    
    try:
        # 1. Tüm paket listesini al (opkg list)
        full_list = subprocess.check_output(["opkg", "list"], text=True)
        for line in full_list.splitlines():
            if ' - ' in line:
                parts = line.split(' - ', 2)
                name = parts[0].strip()
                all_packages[name] = {
                    'name': name,
                    'version': parts[1].strip(),
                    'desc': parts[2].strip() if len(parts) > 2 else "Açıklama yok.",
                    'installed': False
                }
        
        # 2. Yüklü paketleri işaretle (opkg list-installed)
        installed_list = subprocess.check_output(["opkg", "list-installed"], text=True)
        for line in installed_list.splitlines():
            name = line.split(' - ')[0].strip()
            if name in all_packages:
                all_packages[name]['installed'] = True
                
    except Exception as e:
        print(f"Hata oluştu: {e}")
        
    return sorted(all_packages.values(), key=lambda x: x['name'])

@app.route('/')
def index():
    pkgs = get_packages_status()
    return render_template('index.html', packages=pkgs)

@app.route('/action', methods=['POST'])
def action():
    pkg_name = request.json.get('name')
    action_type = request.json.get('action') # 'install' veya 'remove'
    
    command = ["opkg", action_type, pkg_name]
    try:
        # Komutu çalıştır ve çıktıları yakala
        process = subprocess.run(command, capture_output=True, text=True, timeout=120)
        output = process.stdout + process.stderr
    except Exception as e:
        output = str(e)
    
    return jsonify({"status": "success", "output": output})

if __name__ == '__main__':
    print("Keenetic Paket Merkezi Başlatılıyor...")
    print("Erişim adresi: http://192.168.1.1:5000")
    # Debug=False: Keenetic /dev/shm hatasını önlemek ve performans için
    app.run(host='0.0.0.0', port=5000, debug=False)
