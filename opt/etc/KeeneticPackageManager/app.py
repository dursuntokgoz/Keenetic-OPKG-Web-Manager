#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, jsonify, request, send_from_directory, send_file
import subprocess
import os
import json
import time
import shutil
import re
import zipfile
import io
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max upload

# CPU kullanımını hesaplamak için önceki değerleri sakla
last_cpu_stats = None
last_cpu_time = None

# Clipboard için geçici depolama (copy/paste işlemleri için)
clipboard = {'items': [], 'operation': None}  # operation: 'copy' veya 'cut'

def get_cpu_usage():
    """Diferansiyel CPU kullanımı hesaplama"""
    global last_cpu_stats, last_cpu_time
    
    try:
        with open('/proc/stat', 'r') as f:
            line = f.readline()
            
        # cpu  user nice system idle iowait irq softirq
        parts = line.split()
        if parts[0] != 'cpu':
            return 0.0
            
        # İlk 4 değeri al (user, nice, system, idle)
        user = int(parts[1])
        nice = int(parts[2])
        system = int(parts[3])
        idle = int(parts[4])
        
        total = user + nice + system + idle
        active = user + nice + system
        
        current_time = time.time()
        
        if last_cpu_stats is None:
            last_cpu_stats = {'total': total, 'active': active}
            last_cpu_time = current_time
            time.sleep(0.1)  # İlk okuma için kısa bekleme
            return get_cpu_usage()
        
        # Diferansiyel hesaplama
        total_delta = total - last_cpu_stats['total']
        active_delta = active - last_cpu_stats['active']
        
        if total_delta == 0:
            cpu_percent = 0.0
        else:
            cpu_percent = (active_delta / total_delta) * 100.0
        
        # Güncelle
        last_cpu_stats = {'total': total, 'active': active}
        last_cpu_time = current_time
        
        return round(cpu_percent, 1)
    except Exception as e:
        print(f"CPU hesaplama hatası: {e}")
        return 0.0

def get_memory_usage():
    """RAM kullanımı hesaplama"""
    try:
        with open('/proc/meminfo', 'r') as f:
            lines = f.readlines()
        
        mem_info = {}
        for line in lines:
            parts = line.split(':')
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip().split()[0]
                mem_info[key] = int(value)
        
        total = mem_info.get('MemTotal', 0)
        free = mem_info.get('MemFree', 0)
        buffers = mem_info.get('Buffers', 0)
        cached = mem_info.get('Cached', 0)
        
        # Kullanılan = Toplam - (Boş + Buffers + Cached)
        used = total - (free + buffers + cached)
        
        return {
            'used': round(used / 1024, 1),  # MB
            'total': round(total / 1024, 1),  # MB
            'percent': round((used / total) * 100, 1) if total > 0 else 0
        }
    except Exception as e:
        print(f"RAM hesaplama hatası: {e}")
        return {'used': 0, 'total': 0, 'percent': 0}

def get_system_info():
    """Sistem bilgilerini al (OpenWRT tarzı)"""
    info = {}
    
    try:
        # Hostname
        with open('/proc/sys/kernel/hostname', 'r') as f:
            info['hostname'] = f.read().strip()
    except:
        info['hostname'] = 'Unknown'
    
    try:
        # Uptime
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.read().split()[0])
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            info['uptime'] = f"{days}d {hours}h {minutes}m"
            info['uptime_seconds'] = int(uptime_seconds)
    except:
        info['uptime'] = 'Unknown'
        info['uptime_seconds'] = 0
    
    try:
        # Load average
        with open('/proc/loadavg', 'r') as f:
            loads = f.read().split()[:3]
            info['load'] = [float(x) for x in loads]
    except:
        info['load'] = [0, 0, 0]
    
    try:
        # Kernel version
        with open('/proc/version', 'r') as f:
            version = f.read().strip()
            info['kernel'] = version.split()[2]
    except:
        info['kernel'] = 'Unknown'
    
    return info

def get_network_interfaces():
    """Ağ arayüzlerini al"""
    interfaces = []
    
    try:
        result = subprocess.run(['ip', 'addr', 'show'], capture_output=True, text=True, timeout=5)
        current_iface = None
        
        for line in result.stdout.split('\n'):
            line = line.strip()
            
            # Yeni interface başlangıcı
            if line and line[0].isdigit():
                parts = line.split(':')
                if len(parts) >= 2:
                    iface_name = parts[1].strip()
                    
                    # State kontrolü
                    state = 'DOWN'
                    if 'state UP' in line:
                        state = 'UP'
                    elif 'state UNKNOWN' in line:
                        state = 'UNKNOWN'
                    
                    current_iface = {
                        'name': iface_name,
                        'state': state,
                        'ipv4': [],
                        'ipv6': [],
                        'mac': ''
                    }
                    interfaces.append(current_iface)
            
            elif current_iface:
                # MAC adresi
                if 'link/ether' in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        current_iface['mac'] = parts[1]
                
                # IPv4 adresi
                elif 'inet ' in line and 'inet6' not in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        current_iface['ipv4'].append(parts[1])
                
                # IPv6 adresi
                elif 'inet6' in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        current_iface['ipv6'].append(parts[1])
    
    except Exception as e:
        print(f"Network interfaces hatası: {e}")
    
    return interfaces

def get_storage_info():
    """Disk kullanımı (OpenWRT tarzı)"""
    storage = []
    
    try:
        result = subprocess.run(['df', '-h'], capture_output=True, text=True, timeout=5)
        
        for line in result.stdout.split('\n')[1:]:  # İlk satırı atla (header)
            if line.strip():
                parts = line.split()
                if len(parts) >= 6:
                    storage.append({
                        'filesystem': parts[0],
                        'size': parts[1],
                        'used': parts[2],
                        'available': parts[3],
                        'use_percent': parts[4],
                        'mounted_on': parts[5]
                    })
    except Exception as e:
        print(f"Storage info hatası: {e}")
    
    return storage

def get_wireless_info():
    """WiFi bilgileri (OpenWRT/Keenetic tarzı)"""
    wireless = []
    
    try:
        # iwconfig ile wireless interface bilgisi
        result = subprocess.run(['iwconfig'], capture_output=True, text=True, timeout=5)
        
        current_iface = None
        for line in result.stdout.split('\n'):
            if line and not line.startswith(' '):
                # Yeni interface
                parts = line.split()
                if len(parts) > 0 and 'no wireless' not in line.lower():
                    current_iface = {
                        'interface': parts[0],
                        'ssid': '',
                        'frequency': '',
                        'signal': '',
                        'bitrate': ''
                    }
                    wireless.append(current_iface)
            
            elif current_iface:
                # SSID
                if 'ESSID:' in line:
                    match = re.search(r'ESSID:"([^"]*)"', line)
                    if match:
                        current_iface['ssid'] = match.group(1)
                
                # Frequency
                if 'Frequency:' in line:
                    match = re.search(r'Frequency:([\d.]+\s*GHz)', line)
                    if match:
                        current_iface['frequency'] = match.group(1).strip()
                
                # Bit Rate
                if 'Bit Rate' in line:
                    match = re.search(r'Bit Rate[=:]([^\s]+\s*[^\s]*)', line)
                    if match:
                        current_iface['bitrate'] = match.group(1).strip()
                
                # Signal level
                if 'Signal level' in line:
                    match = re.search(r'Signal level[=:]([^\s]+)', line)
                    if match:
                        current_iface['signal'] = match.group(1).strip()
    
    except Exception as e:
        print(f"Wireless info hatası: {e}")
    
    return wireless

def get_processes():
    """Çalışan process listesi"""
    processes = []
    
    try:
        # Önce ps aux dene
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=5)
        
        # Eğer boşsa veya hata varsa, alternatif ps komutunu dene
        if not result.stdout or result.returncode != 0:
            result = subprocess.run(['ps', '-w'], capture_output=True, text=True, timeout=5)
        
        lines = result.stdout.split('\n')
        
        # Header'ı bul ve atla
        start_idx = 0
        for i, line in enumerate(lines):
            if 'PID' in line or 'USER' in line:
                start_idx = i + 1
                break
        
        for line in lines[start_idx:]:
            if not line.strip():
                continue
            
            # Farklı ps formatlarını destekle
            parts = line.split(None, 10)
            
            if len(parts) >= 11:
                # Standard ps aux format
                processes.append({
                    'user': parts[0],
                    'pid': parts[1],
                    'cpu': parts[2],
                    'mem': parts[3],
                    'vsz': parts[4],
                    'rss': parts[5],
                    'command': parts[10]
                })
            elif len(parts) >= 5:
                # BusyBox ps format (PID USER VSZ STAT COMMAND)
                processes.append({
                    'user': parts[1] if len(parts) > 1 else 'root',
                    'pid': parts[0],
                    'cpu': '0.0',
                    'mem': '0.0',
                    'vsz': parts[2] if len(parts) > 2 else '0',
                    'rss': '0',
                    'command': ' '.join(parts[4:]) if len(parts) > 4 else parts[-1]
                })
    except subprocess.TimeoutExpired:
        print(f"Process list zaman aşımı")
    except Exception as e:
        print(f"Process list hatası: {e}")
    
    return processes

def get_kernel_log(lines=50):
    """Kernel log mesajları (dmesg)"""
    try:
        result = subprocess.run(['dmesg', '-T'], capture_output=True, text=True, timeout=5)
        log_lines = result.stdout.split('\n')
        return log_lines[-lines:] if len(log_lines) > lines else log_lines
    except:
        return []

def get_system_log(lines=50):
    """System log (logread or syslog)"""
    try:
        # OpenWRT logread
        result = subprocess.run(['logread'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            log_lines = result.stdout.split('\n')
            return log_lines[-lines:] if len(log_lines) > lines else log_lines
    except:
        pass
    
    # Alternatif: /var/log/messages
    try:
        with open('/var/log/messages', 'r') as f:
            log_lines = f.readlines()
            return [l.strip() for l in log_lines[-lines:]]
    except:
        return []

@app.route('/')
def index():
    """Ana sayfa"""
    return send_from_directory('.', 'index.html')

@app.route('/app.js')
def serve_js():
    """JavaScript dosyası"""
    return send_from_directory('.', 'app.js', mimetype='application/javascript')

@app.route('/api-docs.html')
def api_docs_page():
    """API dokümantasyon sayfası"""
    return send_from_directory('.', 'api-docs.html')

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Sistem istatistikleri (CPU, RAM)"""
    try:
        cpu = get_cpu_usage()
        memory = get_memory_usage()
        
        return jsonify({
            'success': True,
            'cpu': cpu,
            'memory': memory
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/services', methods=['GET'])
def get_services():
    """Çalışan servisleri listele (netstat)"""
    try:
        result = subprocess.run(
            ['netstat', '-tulpn'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        tcp_services = []
        udp_services = []
        
        lines = result.stdout.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('Active') or line.startswith('Proto'):
                continue
            
            parts = line.split()
            if len(parts) < 4:
                continue
            
            proto = parts[0].lower()
            local_address = parts[3] if len(parts) > 3 else ''
            program = parts[-1] if len(parts) > 6 else '-'
            
            # Port numarasını çıkar
            port = ''
            if ':' in local_address:
                port = local_address.split(':')[-1]
            
            # Program adını temizle (PID/Program formatı)
            if '/' in program:
                program = program.split('/')[-1]
            
            service_info = {
                'proto': proto,
                'port': port,
                'address': local_address,
                'program': program
            }
            
            if proto in ['tcp', 'tcp6']:
                tcp_services.append(service_info)
            elif proto in ['udp', 'udp6']:
                udp_services.append(service_info)
        
        return jsonify({
            'success': True,
            'tcp': tcp_services,
            'udp': udp_services
        })
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': 'Zaman aşımı'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/packages', methods=['GET'])
def get_packages():
    """Tüm paketleri ve yüklü olanları listele"""
    try:
        # Yüklü paketler
        installed_result = subprocess.run(
            ['opkg', 'list-installed'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        installed = set()
        for line in installed_result.stdout.split('\n'):
            if line.strip():
                pkg_name = line.split()[0] if line.split() else ''
                if pkg_name:
                    installed.add(pkg_name)
        
        # Tüm paketler
        all_result = subprocess.run(
            ['opkg', 'list'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        packages = []
        for line in all_result.stdout.split('\n'):
            if line.strip():
                parts = line.split(' - ')
                if len(parts) >= 2:
                    pkg_name = parts[0].strip()
                    version = parts[1].strip() if len(parts) > 1 else ''
                    description = parts[2].strip() if len(parts) > 2 else ''
                    
                    packages.append({
                        'name': pkg_name,
                        'version': version,
                        'description': description,
                        'installed': pkg_name in installed
                    })
        
        return jsonify({
            'success': True,
            'packages': packages
        })
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': 'Zaman aşımı'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/packages/install', methods=['POST'])
def install_package():
    """Paket yükle"""
    try:
        data = request.get_json()
        package_name = data.get('package', '')
        
        if not package_name:
            return jsonify({'success': False, 'error': 'Paket adı gerekli'}), 400
        
        result = subprocess.run(
            ['opkg', 'install', package_name],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        return jsonify({
            'success': result.returncode == 0,
            'output': result.stdout + result.stderr
        })
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': 'Zaman aşımı'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/packages/remove', methods=['POST'])
def remove_package():
    """Paket kaldır"""
    try:
        data = request.get_json()
        package_name = data.get('package', '')
        
        if not package_name:
            return jsonify({'success': False, 'error': 'Paket adı gerekli'}), 400
        
        result = subprocess.run(
            ['opkg', 'remove', package_name],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        return jsonify({
            'success': result.returncode == 0,
            'output': result.stdout + result.stderr
        })
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': 'Zaman aşımı'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/files', methods=['GET'])
def list_files():
    """Dosya ve klasörleri listele"""
    try:
        path = request.args.get('path', '/opt')
        
        # Güvenlik: sadece /opt altına izin ver
        if not path.startswith('/opt'):
            path = '/opt'
        
        if not os.path.exists(path):
            return jsonify({'success': False, 'error': 'Yol bulunamadı'}), 404
        
        items = []
        
        try:
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                is_dir = os.path.isdir(item_path)
                size = 0
                modified = ''
                permissions = ''
                
                try:
                    stat_info = os.stat(item_path)
                    size = stat_info.st_size if not is_dir else 0
                    modified = datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                    permissions = oct(stat_info.st_mode)[-3:]
                except:
                    pass
                
                items.append({
                    'name': item,
                    'path': item_path,
                    'is_dir': is_dir,
                    'size': size,
                    'modified': modified,
                    'permissions': permissions
                })
        except PermissionError:
            return jsonify({'success': False, 'error': 'Erişim reddedildi'}), 403
        
        return jsonify({
            'success': True,
            'path': path,
            'items': sorted(items, key=lambda x: (not x['is_dir'], x['name'].lower()))
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/files/read', methods=['POST'])
def read_file():
    """Dosya içeriğini oku"""
    try:
        data = request.get_json()
        file_path = data.get('path', '')
        
        if not file_path.startswith('/opt'):
            return jsonify({'success': False, 'error': 'Erişim reddedildi'}), 403
        
        if not os.path.isfile(file_path):
            return jsonify({'success': False, 'error': 'Dosya değil'}), 400
        
        # Binary kontrolü
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return jsonify({
                'success': True,
                'content': content
            })
        except UnicodeDecodeError:
            return jsonify({'success': False, 'error': 'Binary dosya, düzenlenemez'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/files/write', methods=['POST'])
def write_file():
    """Dosyaya yaz/kaydet"""
    try:
        data = request.get_json()
        file_path = data.get('path', '')
        content = data.get('content', '')
        
        if not file_path.startswith('/opt'):
            return jsonify({'success': False, 'error': 'Erişim reddedildi'}), 403
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/files/create', methods=['POST'])
def create_file_or_folder():
    """Dosya veya klasör oluştur"""
    try:
        data = request.get_json()
        path = data.get('path', '')
        name = data.get('name', '')
        is_dir = data.get('is_dir', False)
        
        if not path.startswith('/opt'):
            return jsonify({'success': False, 'error': 'Erişim reddedildi'}), 403
        
        full_path = os.path.join(path, name)
        
        if is_dir:
            os.makedirs(full_path, exist_ok=True)
        else:
            # Boş dosya oluştur
            open(full_path, 'a').close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/files/delete', methods=['POST'])
def delete_file_or_folder():
    """Dosya veya klasör sil"""
    try:
        data = request.get_json()
        path = data.get('path', '')
        
        if not path.startswith('/opt'):
            return jsonify({'success': False, 'error': 'Erişim reddedildi'}), 403
        
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/files/rename', methods=['POST'])
def rename_file_or_folder():
    """Dosya veya klasör yeniden adlandır"""
    try:
        data = request.get_json()
        old_path = data.get('old_path', '')
        new_name = data.get('new_name', '')
        
        if not old_path.startswith('/opt'):
            return jsonify({'success': False, 'error': 'Erişim reddedildi'}), 403
        
        parent_dir = os.path.dirname(old_path)
        new_path = os.path.join(parent_dir, new_name)
        
        if os.path.exists(new_path):
            return jsonify({'success': False, 'error': 'Bu isimde bir dosya/klasör zaten var'}), 400
        
        os.rename(old_path, new_path)
        
        return jsonify({'success': True, 'new_path': new_path})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/files/copy', methods=['POST'])
def copy_to_clipboard():
    """Dosyaları clipboard'a kopyala"""
    try:
        data = request.get_json()
        paths = data.get('paths', [])
        
        for path in paths:
            if not path.startswith('/opt'):
                return jsonify({'success': False, 'error': 'Erişim reddedildi'}), 403
        
        clipboard['items'] = paths
        clipboard['operation'] = 'copy'
        
        return jsonify({'success': True, 'count': len(paths)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/files/cut', methods=['POST'])
def cut_to_clipboard():
    """Dosyaları clipboard'a kes"""
    try:
        data = request.get_json()
        paths = data.get('paths', [])
        
        for path in paths:
            if not path.startswith('/opt'):
                return jsonify({'success': False, 'error': 'Erişim reddedildi'}), 403
        
        clipboard['items'] = paths
        clipboard['operation'] = 'cut'
        
        return jsonify({'success': True, 'count': len(paths)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/files/paste', methods=['POST'])
def paste_from_clipboard():
    """Clipboard'dan yapıştır"""
    try:
        data = request.get_json()
        dest_path = data.get('dest_path', '')
        
        if not dest_path.startswith('/opt'):
            return jsonify({'success': False, 'error': 'Erişim reddedildi'}), 403
        
        if not clipboard['items']:
            return jsonify({'success': False, 'error': 'Clipboard boş'}), 400
        
        operation = clipboard['operation']
        pasted_count = 0
        
        for item_path in clipboard['items']:
            if not os.path.exists(item_path):
                continue
            
            item_name = os.path.basename(item_path)
            dest_item_path = os.path.join(dest_path, item_name)
            
            # Aynı isimde dosya varsa _copy ekle
            if os.path.exists(dest_item_path):
                base, ext = os.path.splitext(item_name)
                counter = 1
                while os.path.exists(dest_item_path):
                    if ext:
                        dest_item_path = os.path.join(dest_path, f"{base}_copy{counter}{ext}")
                    else:
                        dest_item_path = os.path.join(dest_path, f"{item_name}_copy{counter}")
                    counter += 1
            
            try:
                if operation == 'copy':
                    if os.path.isdir(item_path):
                        shutil.copytree(item_path, dest_item_path)
                    else:
                        shutil.copy2(item_path, dest_item_path)
                elif operation == 'cut':
                    shutil.move(item_path, dest_item_path)
                
                pasted_count += 1
            except Exception as e:
                print(f"Yapıştırma hatası ({item_path}): {e}")
        
        # Cut işleminden sonra clipboard'ı temizle
        if operation == 'cut':
            clipboard['items'] = []
            clipboard['operation'] = None
        
        return jsonify({'success': True, 'count': pasted_count})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/files/duplicate', methods=['POST'])
def duplicate_file():
    """Dosya veya klasörü klonla"""
    try:
        data = request.get_json()
        path = data.get('path', '')
        
        if not path.startswith('/opt'):
            return jsonify({'success': False, 'error': 'Erişim reddedildi'}), 403
        
        if not os.path.exists(path):
            return jsonify({'success': False, 'error': 'Dosya bulunamadı'}), 404
        
        # Yeni isim oluştur
        parent_dir = os.path.dirname(path)
        item_name = os.path.basename(path)
        base, ext = os.path.splitext(item_name)
        
        counter = 1
        new_path = os.path.join(parent_dir, f"{base}_copy{ext}")
        
        while os.path.exists(new_path):
            counter += 1
            if ext:
                new_path = os.path.join(parent_dir, f"{base}_copy{counter}{ext}")
            else:
                new_path = os.path.join(parent_dir, f"{item_name}_copy{counter}")
        
        # Kopyala
        if os.path.isdir(path):
            shutil.copytree(path, new_path)
        else:
            shutil.copy2(path, new_path)
        
        return jsonify({'success': True, 'new_path': new_path})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/files/move', methods=['POST'])
def move_file():
    """Dosya veya klasörü taşı"""
    try:
        data = request.get_json()
        source_path = data.get('source_path', '')
        dest_path = data.get('dest_path', '')
        
        if not source_path.startswith('/opt') or not dest_path.startswith('/opt'):
            return jsonify({'success': False, 'error': 'Erişim reddedildi'}), 403
        
        if not os.path.exists(source_path):
            return jsonify({'success': False, 'error': 'Kaynak bulunamadı'}), 404
        
        if not os.path.isdir(dest_path):
            return jsonify({'success': False, 'error': 'Hedef klasör değil'}), 400
        
        item_name = os.path.basename(source_path)
        final_dest = os.path.join(dest_path, item_name)
        
        if os.path.exists(final_dest):
            return jsonify({'success': False, 'error': 'Hedefte aynı isimde dosya var'}), 400
        
        shutil.move(source_path, final_dest)
        
        return jsonify({'success': True, 'new_path': final_dest})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/files/compress', methods=['POST'])
def compress_folder():
    """Klasörü ZIP olarak sıkıştır"""
    try:
        data = request.get_json()
        path = data.get('path', '')
        
        if not path.startswith('/opt'):
            return jsonify({'success': False, 'error': 'Erişim reddedildi'}), 403
        
        if not os.path.exists(path):
            return jsonify({'success': False, 'error': 'Dosya/klasör bulunamadı'}), 404
        
        # ZIP dosya adı oluştur
        base_name = os.path.basename(path)
        parent_dir = os.path.dirname(path)
        zip_name = f"{base_name}.zip"
        zip_path = os.path.join(parent_dir, zip_name)
        
        # Aynı isimde zip varsa _1, _2 ekle
        counter = 1
        while os.path.exists(zip_path):
            zip_name = f"{base_name}_{counter}.zip"
            zip_path = os.path.join(parent_dir, zip_name)
            counter += 1
        
        # ZIP oluştur
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            if os.path.isfile(path):
                zipf.write(path, os.path.basename(path))
            else:
                for root, dirs, files in os.walk(path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, os.path.dirname(path))
                        zipf.write(file_path, arcname)
        
        return jsonify({'success': True, 'zip_path': zip_path})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/files/extract', methods=['POST'])
def extract_zip():
    """ZIP dosyasını çıkart"""
    try:
        data = request.get_json()
        zip_path = data.get('zip_path', '')
        extract_to = data.get('extract_to', '')
        
        if not zip_path.startswith('/opt'):
            return jsonify({'success': False, 'error': 'Erişim reddedildi'}), 403
        
        if not extract_to:
            # Eğer hedef belirtilmemişse ZIP'in bulunduğu klasöre çıkart
            extract_to = os.path.dirname(zip_path)
        
        if not extract_to.startswith('/opt'):
            return jsonify({'success': False, 'error': 'Erişim reddedildi'}), 403
        
        if not os.path.exists(zip_path):
            return jsonify({'success': False, 'error': 'ZIP dosyası bulunamadı'}), 404
        
        if not zipfile.is_zipfile(zip_path):
            return jsonify({'success': False, 'error': 'Geçerli bir ZIP dosyası değil'}), 400
        
        # ZIP içeriğini çıkart
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            zipf.extractall(extract_to)
        
        return jsonify({'success': True, 'extracted_to': extract_to})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/files/upload', methods=['POST'])
def upload_file():
    """Dosya yükle"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'Dosya bulunamadı'}), 400
        
        file = request.files['file']
        dest_path = request.form.get('dest_path', '/opt')
        
        if not dest_path.startswith('/opt'):
            return jsonify({'success': False, 'error': 'Erişim reddedildi'}), 403
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'Dosya adı boş'}), 400
        
        filename = secure_filename(file.filename)
        save_path = os.path.join(dest_path, filename)
        
        # Aynı isimde dosya varsa _1, _2 ekle
        if os.path.exists(save_path):
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(save_path):
                save_path = os.path.join(dest_path, f"{base}_{counter}{ext}")
                counter += 1
        
        file.save(save_path)
        
        return jsonify({'success': True, 'path': save_path})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/files/download', methods=['GET'])
def download_file():
    """Dosya indir"""
    try:
        file_path = request.args.get('path', '')
        
        if not file_path.startswith('/opt'):
            return jsonify({'success': False, 'error': 'Erişim reddedildi'}), 403
        
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'error': 'Dosya bulunamadı'}), 404
        
        if os.path.isdir(file_path):
            # Klasörü ZIP olarak indir
            memory_file = io.BytesIO()
            
            with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(file_path):
                    for file in files:
                        file_full_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_full_path, os.path.dirname(file_path))
                        zipf.write(file_full_path, arcname)
            
            memory_file.seek(0)
            folder_name = os.path.basename(file_path)
            
            return send_file(
                memory_file,
                mimetype='application/zip',
                as_attachment=True,
                download_name=f'{folder_name}.zip'
            )
        else:
            # Tekil dosyayı indir
            return send_file(
                file_path,
                as_attachment=True,
                download_name=os.path.basename(file_path)
            )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/files/search', methods=['GET'])
def search_files():
    """Dosya ara"""
    try:
        query = request.args.get('query', '').lower()
        search_path = request.args.get('path', '/opt')
        
        if not search_path.startswith('/opt'):
            search_path = '/opt'
        
        if not query:
            return jsonify({'success': False, 'error': 'Arama sorgusu gerekli'}), 400
        
        results = []
        
        for root, dirs, files in os.walk(search_path):
            # Klasörleri kontrol et
            for dir_name in dirs:
                if query in dir_name.lower():
                    full_path = os.path.join(root, dir_name)
                    results.append({
                        'name': dir_name,
                        'path': full_path,
                        'is_dir': True,
                        'parent': root
                    })
            
            # Dosyaları kontrol et
            for file_name in files:
                if query in file_name.lower():
                    full_path = os.path.join(root, file_name)
                    try:
                        size = os.path.getsize(full_path)
                    except:
                        size = 0
                    
                    results.append({
                        'name': file_name,
                        'path': full_path,
                        'is_dir': False,
                        'size': size,
                        'parent': root
                    })
            
            # Çok fazla sonuç varsa kes
            if len(results) > 500:
                break
        
        return jsonify({
            'success': True,
            'results': results[:500],  # Max 500 sonuç
            'count': len(results)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/files/info', methods=['GET'])
def get_file_info():
    """Dosya/klasör detaylı bilgi"""
    try:
        path = request.args.get('path', '')
        
        if not path.startswith('/opt'):
            return jsonify({'success': False, 'error': 'Erişim reddedildi'}), 403
        
        if not os.path.exists(path):
            return jsonify({'success': False, 'error': 'Dosya bulunamadı'}), 404
        
        stat_info = os.stat(path)
        is_dir = os.path.isdir(path)
        
        info = {
            'name': os.path.basename(path),
            'path': path,
            'is_dir': is_dir,
            'size': stat_info.st_size,
            'created': datetime.fromtimestamp(stat_info.st_ctime).strftime('%Y-%m-%d %H:%M:%S'),
            'modified': datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            'accessed': datetime.fromtimestamp(stat_info.st_atime).strftime('%Y-%m-%d %H:%M:%S'),
            'permissions': oct(stat_info.st_mode)[-3:],
            'owner_uid': stat_info.st_uid,
            'owner_gid': stat_info.st_gid
        }
        
        # Klasörse içindeki öğe sayısını ekle
        if is_dir:
            try:
                items = os.listdir(path)
                info['item_count'] = len(items)
                info['file_count'] = sum(1 for i in items if os.path.isfile(os.path.join(path, i)))
                info['dir_count'] = sum(1 for i in items if os.path.isdir(os.path.join(path, i)))
            except:
                info['item_count'] = 0
        
        return jsonify({'success': True, 'info': info})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/system/info', methods=['GET'])
def get_system_info_api():
    """Sistem bilgileri (OpenWRT LuCI tarzı)"""
    try:
        return jsonify({
            'success': True,
            'info': get_system_info()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/network/interfaces', methods=['GET'])
def get_network_interfaces_api():
    """Ağ arayüzleri"""
    try:
        return jsonify({
            'success': True,
            'interfaces': get_network_interfaces()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/network/wireless', methods=['GET'])
def get_wireless_info_api():
    """WiFi bilgileri"""
    try:
        return jsonify({
            'success': True,
            'wireless': get_wireless_info()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/storage', methods=['GET'])
def get_storage_api():
    """Disk kullanımı"""
    try:
        return jsonify({
            'success': True,
            'storage': get_storage_info()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/processes', methods=['GET'])
def get_processes_api():
    """Çalışan process listesi"""
    try:
        processes = get_processes()
        return jsonify({
            'success': True,
            'processes': processes,
            'count': len(processes)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/debug/ps', methods=['GET'])
def debug_ps():
    """PS komutunu debug et"""
    try:
        # ps aux dene
        result1 = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=5)
        
        # ps -w dene
        result2 = subprocess.run(['ps', '-w'], capture_output=True, text=True, timeout=5)
        
        # ps (sadece) dene
        result3 = subprocess.run(['ps'], capture_output=True, text=True, timeout=5)
        
        return jsonify({
            'success': True,
            'ps_aux': {
                'returncode': result1.returncode,
                'stdout': result1.stdout[:500],  # İlk 500 karakter
                'stderr': result1.stderr
            },
            'ps_w': {
                'returncode': result2.returncode,
                'stdout': result2.stdout[:500],
                'stderr': result2.stderr
            },
            'ps': {
                'returncode': result3.returncode,
                'stdout': result3.stdout[:500],
                'stderr': result3.stderr
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/processes/kill', methods=['POST'])
def kill_process():
    """Process'i sonlandır"""
    try:
        data = request.get_json()
        pid = data.get('pid', '')
        
        if not pid:
            return jsonify({'success': False, 'error': 'PID gerekli'}), 400
        
        result = subprocess.run(['kill', '-9', str(pid)], capture_output=True, text=True, timeout=5)
        
        return jsonify({
            'success': result.returncode == 0,
            'output': result.stdout + result.stderr
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/logs/kernel', methods=['GET'])
def get_kernel_log_api():
    """Kernel log"""
    try:
        lines = int(request.args.get('lines', 50))
        return jsonify({
            'success': True,
            'logs': get_kernel_log(lines)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/logs/system', methods=['GET'])
def get_system_log_api():
    """System log"""
    try:
        lines = int(request.args.get('lines', 50))
        return jsonify({
            'success': True,
            'logs': get_system_log(lines)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/network/restart', methods=['POST'])
def restart_network():
    """Network'ü yeniden başlat"""
    try:
        # OpenWRT için: /etc/init.d/network restart
        result = subprocess.run(['/etc/init.d/network', 'restart'], 
                              capture_output=True, text=True, timeout=30)
        
        return jsonify({
            'success': result.returncode == 0,
            'output': result.stdout + result.stderr
        })
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': 'Zaman aşımı'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/system/reboot', methods=['POST'])
def reboot_system():
    """Sistemi yeniden başlat"""
    try:
        # 5 saniye sonra reboot
        subprocess.Popen(['sleep', '5', '&&', 'reboot'], 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.DEVNULL)
        
        return jsonify({
            'success': True,
            'message': 'Sistem 5 saniye içinde yeniden başlatılacak'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/firewall/rules', methods=['GET'])
def get_firewall_rules():
    """Firewall kuralları (iptables)"""
    try:
        result = subprocess.run(['iptables', '-L', '-n', '-v'], 
                              capture_output=True, text=True, timeout=10)
        
        return jsonify({
            'success': True,
            'rules': result.stdout
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bandwidth', methods=['GET'])
def get_bandwidth():
    """Bandwidth kullanımı (interface bazlı)"""
    try:
        interfaces = {}
        
        with open('/proc/net/dev', 'r') as f:
            lines = f.readlines()[2:]  # İlk 2 satırı atla
        
        for line in lines:
            if ':' in line:
                parts = line.split(':')
                iface = parts[0].strip()
                stats = parts[1].split()
                
                if len(stats) >= 9:
                    interfaces[iface] = {
                        'rx_bytes': int(stats[0]),
                        'rx_packets': int(stats[1]),
                        'tx_bytes': int(stats[8]),
                        'tx_packets': int(stats[9])
                    }
        
        return jsonify({
            'success': True,
            'interfaces': interfaces
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dns/check', methods=['POST'])
def check_dns():
    """DNS kontrolü"""
    try:
        data = request.get_json()
        host = data.get('host', 'google.com')
        
        result = subprocess.run(['nslookup', host], 
                              capture_output=True, text=True, timeout=10)
        
        return jsonify({
            'success': result.returncode == 0,
            'output': result.stdout
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ping', methods=['POST'])
def ping_host():
    """Ping testi"""
    try:
        data = request.get_json()
        host = data.get('host', '8.8.8.8')
        count = data.get('count', 4)
        
        result = subprocess.run(['ping', '-c', str(count), host], 
                              capture_output=True, text=True, timeout=30)
        
        return jsonify({
            'success': result.returncode == 0,
            'output': result.stdout
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/traceroute', methods=['POST'])
def traceroute_host():
    """Traceroute"""
    try:
        data = request.get_json()
        host = data.get('host', '8.8.8.8')
        
        result = subprocess.run(['traceroute', '-m', '15', host], 
                              capture_output=True, text=True, timeout=60)
        
        return jsonify({
            'success': True,
            'output': result.stdout
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/terminal', methods=['POST'])
def execute_command():
    """Terminal komutu çalıştır (DİKKATLİ KULLAN!)"""
    try:
        data = request.get_json()
        command = data.get('command', '')
        
        if not command:
            return jsonify({'success': False, 'error': 'Komut gerekli'}), 400
        
        # Tehlikeli komutları engelle
        dangerous = ['rm -rf /', 'mkfs', 'dd if=', ':(){:|:&};:']
        for danger in dangerous:
            if danger in command:
                return jsonify({'success': False, 'error': 'Tehlikeli komut engellendi'}), 403
        
        result = subprocess.run(command, shell=True, capture_output=True, 
                              text=True, timeout=30)
        
        return jsonify({
            'success': True,
            'returncode': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr
        })
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': 'Komut zaman aşımına uğradı'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("🔧 Keenetic Sistem Yönetim Paneli Başlatılıyor...")
    print("=" * 60)
    print("\n✓ Panel hazır!")
    print("📍 Adres: http://0.0.0.0:5000")
    print("🌐 Tarayıcıda açın ve kullanmaya başlayın!")
    print("\n" + "=" * 60 + "\n")
    
    app.run(host='0.0.0.0', port=5000)
