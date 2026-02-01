// Global değişkenler
let currentPath = '/opt';
let currentFile = null;
let currentServiceProto = 'tcp';
let allPackages = [];
let allProcesses = [];
let contextMenuItem = null;
let selectedFiles = new Set();
let clipboardHasItems = false;

// Tab yönetimi
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        const tabName = tab.dataset.tab;
        
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
        
        tab.classList.add('active');
        document.getElementById(tabName).classList.add('active');
        
        // Tab değişince ilgili veriyi yükle
        if (tabName === 'dashboard') {
            loadDashboard();
        } else if (tabName === 'network') {
            loadNetworkInterfaces();
        } else if (tabName === 'storage') {
            loadStorage();
        } else if (tabName === 'processes') {
            console.log('Loading processes tab...');
            loadProcesses();
        } else if (tabName === 'services') {
            loadServices();
        } else if (tabName === 'packages' && allPackages.length === 0) {
            loadPackages();
        } else if (tabName === 'files') {
            loadFiles(currentPath);
        }
    });
});

// Bildirim göster
function showNotification(message, type = 'success') {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.className = `notification ${type} show`;
    
    setTimeout(() => {
        notification.classList.remove('show');
    }, 3000);
}

// Stats güncelleme
async function updateStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('cpuValue').textContent = `${data.cpu}%`;
            document.getElementById('ramValue').textContent = 
                `${data.memory.used} / ${data.memory.total} MB`;
        }
    } catch (error) {
        console.error('Stats hatası:', error);
    }
    
    // Sistem bilgisi
    try {
        const response = await fetch('/api/system/info');
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('uptimeValue').textContent = data.info.uptime || '--';
            document.getElementById('loadValue').textContent = 
                data.info.load ? data.info.load.slice(0,2).join(', ') : '--';
        }
    } catch (error) {
        console.error('System info hatası:', error);
    }
}

// Dashboard yükle
async function loadDashboard() {
    // Sistem bilgisi
    try {
        const response = await fetch('/api/system/info');
        const data = await response.json();
        
        if (data.success) {
            const info = data.info;
            document.getElementById('systemInfo').innerHTML = `
                <div class="info-item">
                    <span class="info-label">Hostname</span>
                    <span class="info-value">${info.hostname}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Kernel</span>
                    <span class="info-value">${info.kernel}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Uptime</span>
                    <span class="info-value">${info.uptime}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Load Avg</span>
                    <span class="info-value">${info.load.join(' / ')}</span>
                </div>
            `;
        }
    } catch (error) {
        document.getElementById('systemInfo').innerHTML = '<div>Yüklenemedi</div>';
    }
    
    // Bellek bilgisi
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        
        if (data.success) {
            const mem = data.memory;
            document.getElementById('memoryInfo').innerHTML = `
                <div class="info-item">
                    <span class="info-label">Toplam</span>
                    <span class="info-value">${mem.total} MB</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Kullanılan</span>
                    <span class="info-value">${mem.used} MB</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Boş</span>
                    <span class="info-value">${(mem.total - mem.used).toFixed(1)} MB</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Kullanım</span>
                    <span class="info-value">${mem.percent}%</span>
                </div>
            `;
        }
    } catch (error) {
        document.getElementById('memoryInfo').innerHTML = '<div>Yüklenemedi</div>';
    }
    
    // Ağ durumu
    try {
        const response = await fetch('/api/network/interfaces');
        const data = await response.json();
        
        if (data.success) {
            const upInterfaces = data.interfaces.filter(i => i.state === 'UP');
            document.getElementById('networkStatus').innerHTML = `
                <div class="info-item">
                    <span class="info-label">Aktif Arayüz</span>
                    <span class="info-value">${upInterfaces.length}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Toplam Arayüz</span>
                    <span class="info-value">${data.interfaces.length}</span>
                </div>
                ${upInterfaces.slice(0, 2).map(i => `
                    <div class="info-item">
                        <span class="info-label">${i.name}</span>
                        <span class="info-value">${i.ipv4[0] || 'IP yok'}</span>
                    </div>
                `).join('')}
            `;
        }
    } catch (error) {
        document.getElementById('networkStatus').innerHTML = '<div>Yüklenemedi</div>';
    }
    
    // WiFi durumu
    try {
        const response = await fetch('/api/network/wireless');
        const data = await response.json();
        
        if (data.success && data.wireless.length > 0) {
            const wlan = data.wireless[0];
            document.getElementById('wifiStatus').innerHTML = `
                <div class="info-item">
                    <span class="info-label">Arayüz</span>
                    <span class="info-value">${wlan.interface}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">SSID</span>
                    <span class="info-value">${wlan.ssid || 'Bağlı değil'}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Frekans</span>
                    <span class="info-value">${wlan.frequency || '--'}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Sinyal</span>
                    <span class="info-value">${wlan.signal || '--'}</span>
                </div>
            `;
        } else {
            document.getElementById('wifiStatus').innerHTML = '<div class="info-item"><span>WiFi arayüzü bulunamadı</span></div>';
        }
    } catch (error) {
        document.getElementById('wifiStatus').innerHTML = '<div>Yüklenemedi</div>';
    }
}

// Ağ arayüzleri yükle
async function loadNetworkInterfaces() {
    try {
        const response = await fetch('/api/network/interfaces');
        const data = await response.json();
        
        if (data.success) {
            const container = document.getElementById('networkInterfaces');
            
            if (data.interfaces.length === 0) {
                container.innerHTML = '<div class="loading">Arayüz bulunamadı</div>';
                return;
            }
            
            container.innerHTML = data.interfaces.map(iface => `
                <div class="interface-card">
                    <div class="interface-header">
                        <span class="interface-name">${iface.name}</span>
                        <span class="interface-status ${iface.state === 'UP' ? 'status-up' : 'status-down'}">
                            ${iface.state}
                        </span>
                    </div>
                    <div class="info-grid">
                        ${iface.mac ? `
                        <div class="info-item">
                            <span class="info-label">MAC Address</span>
                            <span class="info-value">${iface.mac}</span>
                        </div>
                        ` : ''}
                        ${iface.ipv4.length > 0 ? `
                        <div class="info-item">
                            <span class="info-label">IPv4</span>
                            <span class="info-value">${iface.ipv4.join(', ')}</span>
                        </div>
                        ` : ''}
                        ${iface.ipv6.length > 0 ? `
                        <div class="info-item">
                            <span class="info-label">IPv6</span>
                            <span class="info-value">${iface.ipv6.join(', ')}</span>
                        </div>
                        ` : ''}
                    </div>
                </div>
            `).join('');
        }
    } catch (error) {
        document.getElementById('networkInterfaces').innerHTML = 
            '<div class="loading">Yüklenemedi</div>';
    }
}

// Network restart
async function restartNetwork() {
    if (!confirm('Network yeniden başlatılacak. Emin misiniz?')) return;
    
    try {
        const response = await fetch('/api/network/restart', {
            method: 'POST'
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Network yeniden başlatılıyor...', 'success');
        } else {
            showNotification('Hata: ' + data.error, 'error');
        }
    } catch (error) {
        showNotification('Hata: ' + error.message, 'error');
    }
}

// Depolama yükle
async function loadStorage() {
    try {
        const response = await fetch('/api/storage');
        const data = await response.json();
        
        if (data.success) {
            const tbody = document.querySelector('#storageTable tbody');
            
            if (data.storage.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6">Depolama bilgisi bulunamadı</td></tr>';
                return;
            }
            
            tbody.innerHTML = data.storage.map(s => `
                <tr>
                    <td>${s.filesystem}</td>
                    <td>${s.size}</td>
                    <td>${s.used}</td>
                    <td>${s.available}</td>
                    <td>
                        <div>${s.use_percent}</div>
                        <div class="storage-bar">
                            <div class="storage-bar-fill" style="width: ${s.use_percent}"></div>
                        </div>
                    </td>
                    <td>${s.mounted_on}</td>
                </tr>
            `).join('');
        }
    } catch (error) {
        document.querySelector('#storageTable tbody').innerHTML = 
            '<tr><td colspan="6">Yüklenemedi</td></tr>';
    }
}

// İşlemleri yükle
async function loadProcesses() {
    try {
        const response = await fetch('/api/processes');
        const data = await response.json();
        
        console.log('Processes API response:', data);
        
        if (data.success) {
            allProcesses = data.processes;
            console.log('Total processes:', allProcesses.length);
            renderProcesses(allProcesses);
        } else {
            console.error('Processes API error:', data.error);
            document.getElementById('processTableBody').innerHTML = 
                '<tr><td colspan="6">API Hatası: ' + (data.error || 'Bilinmeyen hata') + '</td></tr>';
        }
    } catch (error) {
        console.error('Processes fetch error:', error);
        document.getElementById('processTableBody').innerHTML = 
            '<tr><td colspan="6">Yüklenemedi: ' + error.message + '</td></tr>';
    }
}

function renderProcesses(processes) {
    const tbody = document.getElementById('processTableBody');
    
    console.log('Rendering processes:', processes.length);
    
    if (!tbody) {
        console.error('processTableBody element not found!');
        return;
    }
    
    if (!processes || processes.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:40px;color:#6b7280;">İşlem bulunamadı</td></tr>';
        return;
    }
    
    tbody.innerHTML = processes.map(p => {
        // HTML escape for command
        const escapedCommand = (p.command || '').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        
        return `
            <tr>
                <td>${p.pid || '-'}</td>
                <td>${p.user || '-'}</td>
                <td>${p.cpu || '0.0'}%</td>
                <td>${p.mem || '0.0'}%</td>
                <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${escapedCommand}">${escapedCommand}</td>
                <td><button class="btn btn-sm btn-remove" onclick="killProcess('${p.pid}')">Kill</button></td>
            </tr>
        `;
    }).join('');
    
    console.log('Processes rendered successfully');
}

// Process ara
document.getElementById('processSearch').addEventListener('input', (e) => {
    const search = e.target.value.toLowerCase();
    const filtered = allProcesses.filter(p => 
        p.command.toLowerCase().includes(search) || 
        p.pid.includes(search) ||
        p.user.toLowerCase().includes(search)
    );
    renderProcesses(filtered);
});

// Process kill
async function killProcess(pid) {
    if (!confirm(`PID ${pid} sonlandırılacak. Emin misiniz?`)) return;
    
    try {
        const response = await fetch('/api/processes/kill', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({pid: pid})
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('İşlem sonlandırıldı', 'success');
            loadProcesses();
        } else {
            showNotification('Hata: ' + data.error, 'error');
        }
    } catch (error) {
        showNotification('Hata: ' + error.message, 'error');
    }
}

// Servisleri yükle
async function loadServices() {
    try {
        const response = await fetch('/api/services');
        const data = await response.json();
        
        if (data.success) {
            renderServices(data[currentServiceProto] || []);
        }
    } catch (error) {
        document.getElementById('serviceList').innerHTML = 
            '<div class="loading">Servisler yüklenemedi</div>';
    }
}

function renderServices(services) {
    const list = document.getElementById('serviceList');
    
    if (services.length === 0) {
        list.innerHTML = '<div class="loading">Servis bulunamadı</div>';
        return;
    }
    
    list.innerHTML = services.map(svc => `
        <div class="service-item">
            <div class="service-proto">${svc.proto}</div>
            <div class="service-port">${svc.port}</div>
            <div class="service-address">${svc.address}</div>
            <div class="service-program">${svc.program}</div>
        </div>
    `).join('');
}

// Servis filtre
document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        currentServiceProto = btn.dataset.proto;
        
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        
        loadServices();
    });
});

// Paketleri yükle
async function loadPackages() {
    try {
        const response = await fetch('/api/packages');
        const data = await response.json();
        
        if (data.success) {
            allPackages = data.packages;
            renderPackages(allPackages);
        }
    } catch (error) {
        document.getElementById('packageList').innerHTML = 
            '<div class="loading">Paketler yüklenemedi</div>';
    }
}

function renderPackages(packages) {
    const list = document.getElementById('packageList');
    
    if (packages.length === 0) {
        list.innerHTML = '<div class="loading">Paket bulunamadı</div>';
        return;
    }
    
    list.innerHTML = packages.map(pkg => `
        <div class="package-item">
            <div class="package-info">
                <div class="package-name">${pkg.name}</div>
                <div class="package-version">${pkg.version}</div>
                ${pkg.description ? `<div class="package-desc">${pkg.description}</div>` : ''}
            </div>
            ${pkg.installed 
                ? `<button class="btn btn-remove" onclick="removePackage('${pkg.name}')">Kaldır</button>`
                : `<button class="btn btn-install" onclick="installPackage('${pkg.name}')">Yükle</button>`
            }
        </div>
    `).join('');
}

// Paket ara
document.getElementById('packageSearch').addEventListener('input', (e) => {
    const search = e.target.value.toLowerCase();
    const filtered = allPackages.filter(pkg => 
        pkg.name.toLowerCase().includes(search) || 
        (pkg.description && pkg.description.toLowerCase().includes(search))
    );
    renderPackages(filtered);
});

// Paket yükle
async function installPackage(packageName) {
    if (!confirm(`${packageName} paketini yüklemek istediğinizden emin misiniz?`)) return;
    
    const btn = event.target;
    btn.disabled = true;
    btn.textContent = 'Yükleniyor...';
    
    try {
        const response = await fetch('/api/packages/install', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({package: packageName})
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Paket başarıyla yüklendi', 'success');
            loadPackages();
        } else {
            showNotification('Yükleme başarısız: ' + (data.error || data.output), 'error');
            btn.disabled = false;
            btn.textContent = 'Yükle';
        }
    } catch (error) {
        showNotification('Hata: ' + error.message, 'error');
        btn.disabled = false;
        btn.textContent = 'Yükle';
    }
}

// Paket kaldır
async function removePackage(packageName) {
    if (!confirm(`${packageName} paketini kaldırmak istediğinizden emin misiniz?`)) return;
    
    const btn = event.target;
    btn.disabled = true;
    btn.textContent = 'Kaldırılıyor...';
    
    try {
        const response = await fetch('/api/packages/remove', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({package: packageName})
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Paket başarıyla kaldırıldı', 'success');
            loadPackages();
        } else {
            showNotification('Kaldırma başarısız: ' + (data.error || data.output), 'error');
            btn.disabled = false;
            btn.textContent = 'Kaldır';
        }
    } catch (error) {
        showNotification('Hata: ' + error.message, 'error');
        btn.disabled = false;
        btn.textContent = 'Kaldır';
    }
}

// Logları yükle
async function loadKernelLog() {
    try {
        const response = await fetch('/api/logs/kernel');
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('logContainer').innerHTML = 
                data.logs.map(line => `<div class="log-line">${line}</div>`).join('');
        }
    } catch (error) {
        document.getElementById('logContainer').innerHTML = 'Yüklenemedi';
    }
}

async function loadSystemLog() {
    try {
        const response = await fetch('/api/logs/system');
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('logContainer').innerHTML = 
                data.logs.map(line => `<div class="log-line">${line}</div>`).join('');
        }
    } catch (error) {
        document.getElementById('logContainer').innerHTML = 'Yüklenemedi';
    }
}

function clearLogDisplay() {
    document.getElementById('logContainer').innerHTML = 'Bir log türü seçin...';
}

// Network Tools
async function runPing() {
    const host = document.getElementById('pingHost').value;
    document.getElementById('pingOutput').textContent = 'Çalıştırılıyor...';
    
    try {
        const response = await fetch('/api/ping', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({host: host, count: 4})
        });
        
        const data = await response.json();
        document.getElementById('pingOutput').textContent = data.output || data.error;
    } catch (error) {
        document.getElementById('pingOutput').textContent = 'Hata: ' + error.message;
    }
}

async function runDNS() {
    const host = document.getElementById('dnsHost').value;
    document.getElementById('dnsOutput').textContent = 'Çalıştırılıyor...';
    
    try {
        const response = await fetch('/api/dns/check', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({host: host})
        });
        
        const data = await response.json();
        document.getElementById('dnsOutput').textContent = data.output || data.error;
    } catch (error) {
        document.getElementById('dnsOutput').textContent = 'Hata: ' + error.message;
    }
}

async function runTraceroute() {
    const host = document.getElementById('traceHost').value;
    document.getElementById('traceOutput').textContent = 'Çalıştırılıyor...';
    
    try {
        const response = await fetch('/api/traceroute', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({host: host})
        });
        
        const data = await response.json();
        document.getElementById('traceOutput').textContent = data.output || data.error;
    } catch (error) {
        document.getElementById('traceOutput').textContent = 'Hata: ' + error.message;
    }
}

// Terminal
function handleTerminalKey(e) {
    if (e.key === 'Enter') {
        executeTerminalCommand();
    }
}

async function executeTerminalCommand() {
    const input = document.getElementById('terminalInput');
    const command = input.value.trim();
    
    if (!command) return;
    
    const output = document.getElementById('terminalOutput');
    output.textContent += `\n$ ${command}\n`;
    
    try {
        const response = await fetch('/api/terminal', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({command: command})
        });
        
        const data = await response.json();
        
        if (data.success) {
            output.textContent += data.stdout || '';
            if (data.stderr) {
                output.textContent += 'STDERR:\n' + data.stderr;
            }
        } else {
            output.textContent += 'HATA: ' + data.error + '\n';
        }
    } catch (error) {
        output.textContent += 'HATA: ' + error.message + '\n';
    }
    
    input.value = '';
    output.scrollTop = output.scrollHeight;
}

// ===== DOSYA YÖNETİCİSİ =====

async function loadFiles(path) {
    currentPath = path;
    document.getElementById('currentPath').textContent = path;
    selectedFiles.clear();
    updateToolbarButtons();
    
    try {
        const response = await fetch(`/api/files?path=${encodeURIComponent(path)}`);
        const data = await response.json();
        
        if (data.success) {
            renderFiles(data.items);
        }
    } catch (error) {
        document.getElementById('fileList').innerHTML = 
            '<div class="loading">Dosyalar yüklenemedi</div>';
    }
}

function renderFiles(items) {
    const list = document.getElementById('fileList');
    
    let html = '';
    
    if (currentPath !== '/opt') {
        html += `
            <div class="file-item" onclick="navigateUp()" data-path="..">
                <span class="file-icon">⬆️</span>
                <span class="file-name">..</span>
            </div>
        `;
    }
    
    html += items.map(item => `
        <div class="file-item" 
             data-path="${item.path}"
             data-is-dir="${item.is_dir}"
             onclick="handleFileClick(event, '${item.path}', ${item.is_dir})"
             ondblclick="handleFileDblClick('${item.path}', ${item.is_dir})"
             oncontextmenu="showContextMenu(event, '${item.path}', ${item.is_dir})"
             draggable="true"
             ondragstart="handleDragStart(event)"
             ondragover="handleDragOver(event)"
             ondrop="handleDrop(event, '${item.path}', ${item.is_dir})">
            <input type="checkbox" class="file-checkbox" onclick="toggleFileSelection(event, '${item.path}')">
            <span class="file-icon">${getFileIcon(item.name, item.is_dir)}</span>
            <span class="file-name">${item.name}</span>
            ${!item.is_dir ? `<span class="file-size">${formatSize(item.size)}</span>` : '<span class="file-size">--</span>'}
        </div>
    `).join('');
    
    list.innerHTML = html;
}

function getFileIcon(name, isDir) {
    if (isDir) return '📁';
    
    const ext = name.split('.').pop().toLowerCase();
    const iconMap = {
        'zip': '🗜️', 'gz': '🗜️', 'tar': '🗜️', 'rar': '🗜️', '7z': '🗜️',
        'txt': '📄', 'md': '📝', 'pdf': '📕',
        'doc': '📘', 'docx': '📘', 'xls': '📗', 'xlsx': '📗',
        'jpg': '🖼️', 'jpeg': '🖼️', 'png': '🖼️', 'gif': '🖼️', 'svg': '🖼️',
        'mp3': '🎵', 'wav': '🎵', 'mp4': '🎬', 'avi': '🎬',
        'sh': '⚙️', 'py': '🐍', 'js': '📜', 'json': '📋', 'xml': '📋',
        'html': '🌐', 'css': '🎨', 'c': '⚙️', 'cpp': '⚙️', 'h': '⚙️'
    };
    
    return iconMap[ext] || '📄';
}

function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function navigateUp() {
    const parts = currentPath.split('/').filter(p => p);
    parts.pop();
    const newPath = '/' + parts.join('/');
    loadFiles(newPath || '/opt');
}

function toggleFileSelection(e, path) {
    e.stopPropagation();
    
    if (e.target.checked) {
        selectedFiles.add(path);
    } else {
        selectedFiles.delete(path);
    }
    
    updateToolbarButtons();
}

function handleFileClick(e, path, isDir) {
    if (e.target.type === 'checkbox') return;
    
    if (e.ctrlKey || e.metaKey) {
        const checkbox = e.currentTarget.querySelector('.file-checkbox');
        checkbox.checked = !checkbox.checked;
        toggleFileSelection({target: checkbox, stopPropagation: () => {}}, path);
    }
}

async function handleFileDblClick(path, isDir) {
    if (isDir) {
        loadFiles(path);
    } else {
        await selectFile(path);
    }
}

async function selectFile(path) {
    currentFile = path;
    document.getElementById('editorFilename').textContent = path.split('/').pop();
    document.getElementById('saveBtn').disabled = false;
    
    const textarea = document.getElementById('fileContent');
    textarea.disabled = true;
    textarea.value = 'Yükleniyor...';
    
    try {
        const response = await fetch('/api/files/read', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({path: path})
        });
        
        const data = await response.json();
        
        if (data.success) {
            textarea.value = data.content;
            textarea.disabled = false;
        } else {
            textarea.value = 'Hata: ' + data.error;
        }
    } catch (error) {
        textarea.value = 'Hata: ' + error.message;
    }
}

async function saveFile() {
    if (!currentFile) return;
    
    const content = document.getElementById('fileContent').value;
    const btn = document.getElementById('saveBtn');
    
    btn.disabled = true;
    btn.textContent = '💾 Kaydediliyor...';
    
    try {
        const response = await fetch('/api/files/write', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({path: currentFile, content: content})
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Dosya kaydedildi', 'success');
        } else {
            showNotification('Kaydetme hatası: ' + data.error, 'error');
        }
    } catch (error) {
        showNotification('Hata: ' + error.message, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '💾 Kaydet';
    }
}

async function createNewFolder() {
    const name = prompt('Klasör adı:');
    if (!name) return;
    
    try {
        const response = await fetch('/api/files/create', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({path: currentPath, name: name, is_dir: true})
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Klasör oluşturuldu', 'success');
            loadFiles(currentPath);
        } else {
            showNotification('Hata: ' + data.error, 'error');
        }
    } catch (error) {
        showNotification('Hata: ' + error.message, 'error');
    }
}

async function createNewFile() {
    const name = prompt('Dosya adı:');
    if (!name) return;
    
    try {
        const response = await fetch('/api/files/create', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({path: currentPath, name: name, is_dir: false})
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Dosya oluşturuldu', 'success');
            loadFiles(currentPath);
        } else {
            showNotification('Hata: ' + data.error, 'error');
        }
    } catch (error) {
        showNotification('Hata: ' + error.message, 'error');
    }
}

function showContextMenu(e, path, isDir) {
    e.preventDefault();
    
    contextMenuItem = {path: path, isDir: isDir};
    
    const menu = document.getElementById('contextMenu');
    menu.style.left = e.pageX + 'px';
    menu.style.top = e.pageY + 'px';
    menu.classList.add('show');
    
    return false;
}

document.addEventListener('click', () => {
    document.getElementById('contextMenu').classList.remove('show');
});

function openFile() {
    if (!contextMenuItem) return;
    if (contextMenuItem.isDir) {
        loadFiles(contextMenuItem.path);
    } else {
        selectFile(contextMenuItem.path);
    }
}

function renameItem() {
    if (!contextMenuItem) return;
    
    const currentName = contextMenuItem.path.split('/').pop();
    document.getElementById('renameInput').value = currentName;
    document.getElementById('renameModal').classList.add('show');
}

async function performRename() {
    const newName = document.getElementById('renameInput').value.trim();
    if (!newName || !contextMenuItem) return;
    
    try {
        const response = await fetch('/api/files/rename', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                old_path: contextMenuItem.path,
                new_name: newName
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Yeniden adlandırıldı', 'success');
            closeModal('renameModal');
            loadFiles(currentPath);
        } else {
            showNotification('Hata: ' + data.error, 'error');
        }
    } catch (error) {
        showNotification('Hata: ' + error.message, 'error');
    }
}

async function duplicateItem() {
    if (!contextMenuItem) return;
    
    try {
        const response = await fetch('/api/files/duplicate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({path: contextMenuItem.path})
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Klonlandı', 'success');
            loadFiles(currentPath);
        } else {
            showNotification('Hata: ' + data.error, 'error');
        }
    } catch (error) {
        showNotification('Hata: ' + error.message, 'error');
    }
}

async function downloadItem() {
    if (!contextMenuItem) return;
    window.open(`/api/files/download?path=${encodeURIComponent(contextMenuItem.path)}`, '_blank');
}

async function compressItem() {
    if (!contextMenuItem) return;
    
    try {
        const response = await fetch('/api/files/compress', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({path: contextMenuItem.path})
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('ZIP oluşturuldu', 'success');
            loadFiles(currentPath);
        } else {
            showNotification('Hata: ' + data.error, 'error');
        }
    } catch (error) {
        showNotification('Hata: ' + error.message, 'error');
    }
}

async function extractItem() {
    if (!contextMenuItem) return;
    
    try {
        const response = await fetch('/api/files/extract', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                zip_path: contextMenuItem.path,
                extract_to: currentPath
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('ZIP çıkartıldı', 'success');
            loadFiles(currentPath);
        } else {
            showNotification('Hata: ' + data.error, 'error');
        }
    } catch (error) {
        showNotification('Hata: ' + error.message, 'error');
    }
}

async function showFileInfo() {
    if (!contextMenuItem) return;
    
    try {
        const response = await fetch(`/api/files/info?path=${encodeURIComponent(contextMenuItem.path)}`);
        const data = await response.json();
        
        if (data.success) {
            const info = data.info;
            const html = `
                <div class="info-row">
                    <div class="info-label">Ad:</div>
                    <div class="info-value">${info.name}</div>
                </div>
                <div class="info-row">
                    <div class="info-label">Yol:</div>
                    <div class="info-value">${info.path}</div>
                </div>
                <div class="info-row">
                    <div class="info-label">Tür:</div>
                    <div class="info-value">${info.is_dir ? 'Klasör' : 'Dosya'}</div>
                </div>
                ${!info.is_dir ? `
                <div class="info-row">
                    <div class="info-label">Boyut:</div>
                    <div class="info-value">${formatSize(info.size)}</div>
                </div>
                ` : `
                <div class="info-row">
                    <div class="info-label">İçerik:</div>
                    <div class="info-value">${info.file_count || 0} dosya, ${info.dir_count || 0} klasör</div>
                </div>
                `}
                <div class="info-row">
                    <div class="info-label">Oluşturulma:</div>
                    <div class="info-value">${info.created}</div>
                </div>
                <div class="info-row">
                    <div class="info-label">Değiştirilme:</div>
                    <div class="info-value">${info.modified}</div>
                </div>
                <div class="info-row">
                    <div class="info-label">İzinler:</div>
                    <div class="info-value">${info.permissions}</div>
                </div>
            `;
            
            document.getElementById('infoContent').innerHTML = html;
            document.getElementById('infoModal').classList.add('show');
        } else {
            showNotification('Hata: ' + data.error, 'error');
        }
    } catch (error) {
        showNotification('Hata: ' + error.message, 'error');
    }
}

async function deleteItem() {
    if (!contextMenuItem) return;
    
    if (!confirm(`"${contextMenuItem.path}" silinecek. Emin misiniz?`)) {
        return;
    }
    
    try {
        const response = await fetch('/api/files/delete', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({path: contextMenuItem.path})
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Silindi', 'success');
            loadFiles(currentPath);
            
            if (currentFile === contextMenuItem.path) {
                currentFile = null;
                document.getElementById('editorFilename').textContent = 'Dosya seçilmedi';
                document.getElementById('fileContent').value = '';
                document.getElementById('fileContent').disabled = true;
                document.getElementById('saveBtn').disabled = true;
            }
        } else {
            showNotification('Silme hatası: ' + data.error, 'error');
        }
    } catch (error) {
        showNotification('Hata: ' + error.message, 'error');
    }
}

function updateToolbarButtons() {
    const hasSelection = selectedFiles.size > 0;
    
    document.getElementById('copyBtn').disabled = !hasSelection;
    document.getElementById('cutBtn').disabled = !hasSelection;
    document.getElementById('deleteBtn').disabled = !hasSelection;
    document.getElementById('downloadBtn').disabled = selectedFiles.size !== 1;
    document.getElementById('pasteBtn').disabled = !clipboardHasItems;
}

async function copySelected() {
    if (selectedFiles.size === 0) return;
    
    try {
        const response = await fetch('/api/files/copy', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({paths: Array.from(selectedFiles)})
        });
        
        const data = await response.json();
        
        if (data.success) {
            clipboardHasItems = true;
            updateToolbarButtons();
            showNotification(`${data.count} öğe kopyalandı`, 'success');
        } else {
            showNotification('Hata: ' + data.error, 'error');
        }
    } catch (error) {
        showNotification('Hata: ' + error.message, 'error');
    }
}

async function cutSelected() {
    if (selectedFiles.size === 0) return;
    
    try {
        const response = await fetch('/api/files/cut', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({paths: Array.from(selectedFiles)})
        });
        
        const data = await response.json();
        
        if (data.success) {
            clipboardHasItems = true;
            updateToolbarButtons();
            showNotification(`${data.count} öğe kesildi`, 'success');
        } else {
            showNotification('Hata: ' + data.error, 'error');
        }
    } catch (error) {
        showNotification('Hata: ' + error.message, 'error');
    }
}

async function pasteFiles() {
    try {
        const response = await fetch('/api/files/paste', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({dest_path: currentPath})
        });
        
        const data = await response.json();
        
        if (data.success) {
            clipboardHasItems = false;
            updateToolbarButtons();
            showNotification(`${data.count} öğe yapıştırıldı`, 'success');
            loadFiles(currentPath);
        } else {
            showNotification('Hata: ' + data.error, 'error');
        }
    } catch (error) {
        showNotification('Hata: ' + error.message, 'error');
    }
}

async function deleteSelected() {
    if (selectedFiles.size === 0) return;
    
    if (!confirm(`${selectedFiles.size} öğe silinecek. Emin misiniz?`)) {
        return;
    }
    
    let successCount = 0;
    
    for (const path of selectedFiles) {
        try {
            const response = await fetch('/api/files/delete', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({path: path})
            });
            
            const data = await response.json();
            if (data.success) successCount++;
        } catch (error) {
            console.error('Silme hatası:', error);
        }
    }
    
    selectedFiles.clear();
    updateToolbarButtons();
    showNotification(`${successCount} öğe silindi`, 'success');
    loadFiles(currentPath);
}

function downloadSelected() {
    if (selectedFiles.size !== 1) return;
    
    const path = Array.from(selectedFiles)[0];
    window.open(`/api/files/download?path=${encodeURIComponent(path)}`, '_blank');
}

function showUploadModal() {
    document.getElementById('uploadModal').classList.add('show');
}

async function performUpload() {
    const input = document.getElementById('uploadInput');
    const files = input.files;
    
    if (files.length === 0) {
        showNotification('Dosya seçilmedi', 'error');
        return;
    }
    
    let uploadCount = 0;
    
    for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('dest_path', currentPath);
        
        try {
            const response = await fetch('/api/files/upload', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            if (data.success) uploadCount++;
        } catch (error) {
            console.error('Yükleme hatası:', error);
        }
    }
    
    closeModal('uploadModal');
    showNotification(`${uploadCount} dosya yüklendi`, 'success');
    loadFiles(currentPath);
}

document.getElementById('fileSearch').addEventListener('keypress', async (e) => {
    if (e.key !== 'Enter') return;
    
    const query = e.target.value.trim();
    if (!query) {
        loadFiles(currentPath);
        return;
    }
    
    try {
        const response = await fetch(`/api/files/search?query=${encodeURIComponent(query)}&path=${encodeURIComponent(currentPath)}`);
        const data = await response.json();
        
        if (data.success) {
            const list = document.getElementById('fileList');
            
            if (data.results.length === 0) {
                list.innerHTML = '<div class="loading">Sonuç bulunamadı</div>';
                return;
            }
            
            list.innerHTML = data.results.map(item => `
                <div class="file-item" 
                     data-path="${item.path}"
                     ondblclick="handleFileDblClick('${item.path}', ${item.is_dir})"
                     oncontextmenu="showContextMenu(event, '${item.path}', ${item.is_dir})">
                    <span class="file-icon">${getFileIcon(item.name, item.is_dir)}</span>
                    <span class="file-name">${item.name}</span>
                    <span class="file-size" style="font-size:10px;color:#9ca3af;">${item.parent}</span>
                </div>
            `).join('');
        } else {
            showNotification('Arama hatası: ' + data.error, 'error');
        }
    } catch (error) {
        showNotification('Hata: ' + error.message, 'error');
    }
});

function handleDragStart(e) {
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', e.target.dataset.path);
}

function handleDragOver(e) {
    if (e.preventDefault) {
        e.preventDefault();
    }
    e.dataTransfer.dropEffect = 'move';
    
    const item = e.currentTarget;
    if (item.dataset.isDir === 'true') {
        item.classList.add('drag-over');
    }
    
    return false;
}

function handleDrop(e, destPath, isDir) {
    if (e.stopPropagation) {
        e.stopPropagation();
    }
    
    e.currentTarget.classList.remove('drag-over');
    
    if (!isDir) return false;
    
    const sourcePath = e.dataTransfer.getData('text/plain');
    
    moveFile(sourcePath, destPath);
    
    return false;
}

async function moveFile(sourcePath, destPath) {
    try {
        const response = await fetch('/api/files/move', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({source_path: sourcePath, dest_path: destPath})
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Taşındı', 'success');
            loadFiles(currentPath);
        } else {
            showNotification('Hata: ' + data.error, 'error');
        }
    } catch (error) {
        showNotification('Hata: ' + error.message, 'error');
    }
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('show');
}

function refreshFiles() {
    loadFiles(currentPath);
}

// Başlangıç
updateStats();
setInterval(updateStats, 2000);
loadDashboard();
