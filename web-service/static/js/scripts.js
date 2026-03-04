// Centralized Admin Panel JavaScript
// Consolidated from all admin templates

// ============= UTILITY FUNCTIONS =============

// Debounce function for search inputs
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Show notification
function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    
    const iconClass = type === 'success' ? 'check-circle' : 
                    type === 'danger' ? 'exclamation-triangle' : 
                    type === 'warning' ? 'exclamation-triangle' : 'info-circle';
    
    notification.innerHTML = `
        <i class="fas fa-${iconClass} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        const bsAlert = new bootstrap.Alert(notification);
        bsAlert.close();
    }, 5000);
}

// Show/hide loading
function showLoading(show) {
    const loadingElement = document.getElementById('loadingIndicator');
    if (loadingElement) {
        loadingElement.style.display = show ? 'block' : 'none';
    }
}

// ============= USERS PAGE FUNCTIONS =============

function filterUsers() {
    const searchValue = document.getElementById('searchInput').value.toLowerCase();
    const statusValue = document.getElementById('statusFilter').value;
    const rows = document.querySelectorAll('#usersTable tbody tr');
    
    rows.forEach(row => {
        const userText = row.textContent.toLowerCase();
        const matchesSearch = !searchValue || userText.includes(searchValue);
        const matchesStatus = statusValue === 'all' || row.textContent.includes(statusValue);
        
        row.style.display = matchesSearch && matchesStatus ? '' : 'none';
    });
}

function exportUsers() {
    // Implementation for user export
    showNotification('Función de exportación de usuarios en desarrollo', 'info');
}

function refreshUsers() {
    // Implementation for user refresh
    showNotification('Actualizando lista de usuarios...', 'info');
    setTimeout(() => {
        window.location.reload();
    }, 1000);
}

function viewUser(userId) {
    // Implementation for viewing user details
    showNotification(`Viendo detalles del usuario ${userId}`, 'info');
}

function editUser(userId) {
    // Implementation for editing user
    showNotification(`Editando usuario ${userId}`, 'info');
}

// ============= SETTINGS PAGE FUNCTIONS =============

function selectTheme(theme) {
    // Remove selected class from all themes
    document.querySelectorAll('.theme-option').forEach(option => {
        option.classList.remove('selected');
    });
    
    // Add selected class to chosen theme
    document.querySelector(`.theme-option[data-theme="${theme}"]`).classList.add('selected');
    
    // Apply theme (implementation depends on your theme system)
    document.body.setAttribute('data-theme', theme);
    
    showNotification(`Tema ${theme} aplicado`, 'success');
}

function saveSettings() {
    // Implementation for saving settings
    showNotification('Configuración guardada exitosamente', 'success');
}

// ============= PROFILE PAGE FUNCTIONS =============

document.addEventListener('DOMContentLoaded', function() {
    const profileForm = document.getElementById('profileForm');
    if (profileForm) {
        profileForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Show loading state
            const submitBtn = profileForm.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Actualizando...';
            submitBtn.disabled = true;
            
            // Simulate save
            setTimeout(() => {
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
                showNotification('Perfil actualizado exitosamente', 'success');
            }, 2000);
        });
    }
    
    // Clear validation on input
    document.querySelectorAll('.form-control').forEach(input => {
        input.addEventListener('input', function() {
            this.classList.remove('is-invalid', 'is-valid');
        });
    });
});

// ============= NOTIFICATIONS PAGE FUNCTIONS =============

function updateStats() {
    const notifications = document.querySelectorAll('.notification-item');
    const total = notifications.length;
    const unread = document.querySelectorAll('.notification-item.unread').length;
    const sent = document.querySelectorAll('.notification-item.sent').length;
    const pending = document.querySelectorAll('.notification-item.pending').length;
    
    // Update stat cards
    const totalElement = document.getElementById('totalNotifications');
    const unreadElement = document.getElementById('totalUnread');
    const sentElement = document.getElementById('totalSent');
    const pendingElement = document.getElementById('totalPending');
    
    if (totalElement) totalElement.textContent = total;
    if (unreadElement) unreadElement.textContent = unread;
    if (sentElement) sentElement.textContent = sent;
    if (pendingElement) pendingElement.textContent = pending;
}

function sendNotification() {
    const title = document.getElementById('notificationTitle').value;
    const message = document.getElementById('notificationMessage').value;
    const type = document.getElementById('notificationType').value;
    const target = document.getElementById('notificationTarget').value;
    
    if (!title || !message) {
        showNotification('Por favor completa todos los campos', 'warning');
        return;
    }
    
    // Show loading
    const sendBtn = document.querySelector('#composeForm button[type="submit"]');
    const originalText = sendBtn.innerHTML;
    sendBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Enviando...';
    sendBtn.disabled = true;
    
    // Simulate send
    setTimeout(() => {
        sendBtn.innerHTML = originalText;
        sendBtn.disabled = false;
        showNotification('Notificación enviada exitosamente', 'success');
        
        // Reset form
        document.getElementById('composeForm').reset();
        updateStats();
    }, 2000);
}

// ============= LOGS PAGE FUNCTIONS =============

let isLive = false;
let liveInterval;

function toggleLiveConsole() {
    isLive = !isLive;
    const toggleBtn = document.getElementById('liveToggle');
    const consoleElement = document.getElementById('liveConsole');
    
    if (isLive) {
        toggleBtn.innerHTML = '<i class="fas fa-pause me-2"></i> Pausar';
        toggleBtn.className = 'btn btn-warning';
        
        // Start live updates
        liveInterval = setInterval(() => {
            const timestamp = new Date().toLocaleTimeString();
            const logEntry = `[${timestamp}] INFO: Sistema funcionando normalmente`;
            consoleElement.innerHTML += logEntry + '\n';
            consoleElement.scrollTop = consoleElement.scrollHeight;
        }, 2000);
        
        showNotification('Consola en vivo activada', 'success');
    } else {
        toggleBtn.innerHTML = '<i class="fas fa-play me-2"></i> Iniciar';
        toggleBtn.className = 'btn btn-primary';
        
        // Stop live updates
        if (liveInterval) {
            clearInterval(liveInterval);
        }
        
        showNotification('Consola en vivo pausada', 'info');
    }
}

function clearLogs() {
    if (confirm('¿Estás seguro de que quieres limpiar todos los logs?')) {
        document.getElementById('logsTableBody').innerHTML = '';
        showNotification('Logs limpiados exitosamente', 'success');
    }
}

function filterLogs() {
    const levelValue = document.getElementById('logLevelFilter').value;
    const searchValue = document.getElementById('logSearch').value.toLowerCase();
    const rows = document.querySelectorAll('#logsTable tbody tr');
    
    rows.forEach(row => {
        const level = row.querySelector('.level-badge').textContent.toLowerCase();
        const message = row.querySelector('td:nth-child(3)').textContent.toLowerCase();
        
        const matchesLevel = levelValue === 'all' || level.includes(levelValue);
        const matchesSearch = !searchValue || message.includes(searchValue);
        
        row.style.display = matchesLevel && matchesSearch ? '' : 'none';
    });
}

// ============= HELP PAGE FUNCTIONS =============

function searchHelp() {
    const searchValue = document.getElementById('helpSearch').value.toLowerCase();
    const categories = document.querySelectorAll('.help-category');
    
    categories.forEach(category => {
        const title = category.querySelector('h5').textContent.toLowerCase();
        const content = category.textContent.toLowerCase();
        
        if (title.includes(searchValue) || content.includes(searchValue)) {
            category.style.display = 'block';
        } else {
            category.style.display = 'none';
        }
    });
}

// ============= DATABASE PAGE FUNCTIONS =============

function updateStats() {
    // Simulated database statistics
    document.getElementById('usersCount').textContent = Math.floor(Math.random() * 1000) + 100;
    document.getElementById('exercisesCount').textContent = Math.floor(Math.random() * 500) + 50;
    document.getElementById('logsCount').textContent = Math.floor(Math.random() * 10000) + 1000;
    document.getElementById('adminsCount').textContent = Math.floor(Math.random() * 10) + 1;
}

function testConnection() {
    const statusCard = document.querySelector('.status-card');
    const testBtn = document.querySelector('button[onclick="testConnection()"]');
    
    // Show testing state
    statusCard.classList.remove('connected', 'disconnected');
    statusCard.classList.add('testing');
    testBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Probando...';
    testBtn.disabled = true;
    
    // Simulate connection test
    setTimeout(() => {
        const success = Math.random() > 0.2; // 80% success rate
        
        statusCard.classList.remove('testing');
        if (success) {
            statusCard.classList.add('connected');
            showNotification('Conexión a base de datos exitosa', 'success');
        } else {
            statusCard.classList.add('disconnected');
            showNotification('Error de conexión a base de datos', 'danger');
        }
        
        testBtn.innerHTML = '<i class="fas fa-plug me-2"></i> Probar Conexión';
        testBtn.disabled = false;
        
        updateLastCheck();
    }, 2000);
}

function updateLastCheck() {
    const lastCheckElement = document.getElementById('lastCheck');
    if (lastCheckElement) {
        lastCheckElement.textContent = 'Hace un momento';
    }
}

function executeQuery() {
    const query = document.getElementById('sqlQuery').value;
    const resultElement = document.getElementById('queryResult');
    
    if (!query.trim()) {
        showNotification('Por favor ingresa una consulta SQL', 'warning');
        return;
    }
    
    // Show executing state
    const executeBtn = document.querySelector('button[onclick="executeQuery()"]');
    const originalText = executeBtn.innerHTML;
    executeBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Ejecutando...';
    executeBtn.disabled = true;
    
    // Simulate query execution
    setTimeout(() => {
        executeBtn.innerHTML = originalText;
        executeBtn.disabled = false;
        
        // Show mock results
        const timestamp = new Date().toLocaleTimeString();
        resultElement.innerHTML = `
            <div class="console-line success">[${timestamp}] Query ejecutada exitosamente</div>
            <div class="console-line info">Consulta: ${query}</div>
            <div class="console-line normal">----------------</div>
            <div class="console-line normal">| total_users |</div>
            <div class="console-line normal">|-------------|</div>
            <div class="console-line normal">|     156     |</div>
            <div class="console-line normal">----------------</div>
            <div class="console-line success">(1 fila afectada)</div>
        `;
        
        showNotification('Consulta ejecutada exitosamente', 'success');
    }, 1500);
}

function clearConsole() {
    document.getElementById('queryResult').innerHTML = '<div class="console-line success">-- Consola limpiada</div>';
}

function addQueryResult(message, type) {
    const console = document.getElementById('queryResult');
    const colors = {
        info: '#2196f3',
        success: '#4caf50',
        warning: '#ff9800',
        error: '#f44336',
        normal: '#6c757d'
    };
    
    const color = colors[type] || colors.normal;
    const timestamp = new Date().toLocaleTimeString();
    
    const resultLine = document.createElement('div');
    resultLine.className = 'console-line';
    resultLine.style.color = color;
    resultLine.textContent = `[${timestamp}] ${message}`;
    
    console.appendChild(resultLine);
    console.scrollTop = console.scrollHeight;
}

// ============= DASHBOARD PAGE FUNCTIONS =============

// Auto-refresh dashboard
setTimeout(() => {
    window.location.reload();
}, 30000);

// ============= BOT CONTROL PAGE FUNCTIONS =============

function updateMetrics() {
    // Simulated metrics
    document.getElementById('activeUsers').textContent = Math.floor(Math.random() * 50) + 10;
    document.getElementById('totalMessages').textContent = Math.floor(Math.random() * 1000) + 500;
    document.getElementById('responseTime').textContent = (Math.random() * 100 + 50).toFixed(0) + 'ms';
    document.getElementById('uptime').textContent = Math.floor(Math.random() * 30) + 1 + ' días';
}

function startBot() {
    const statusElement = document.getElementById('botStatus');
    const startBtn = document.querySelector('button[onclick="startBot()"]');
    
    startBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Iniciando...';
    startBtn.disabled = true;
    
    setTimeout(() => {
        statusElement.innerHTML = '<span class="status-badge status-online"><i class="fas fa-circle"></i> En línea</span>';
        startBtn.innerHTML = '<i class="fas fa-stop me-2"></i> Detener Bot';
        startBtn.setAttribute('onclick', 'stopBot()');
        startBtn.disabled = false;
        
        showNotification('Bot iniciado exitosamente', 'success');
        updateMetrics();
    }, 2000);
}

function stopBot() {
    const statusElement = document.getElementById('botStatus');
    const stopBtn = document.querySelector('button[onclick="stopBot()"]');
    
    stopBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Deteniendo...';
    stopBtn.disabled = true;
    
    setTimeout(() => {
        statusElement.innerHTML = '<span class="status-badge status-offline"><i class="fas fa-circle"></i> Desconectado</span>';
        stopBtn.innerHTML = '<i class="fas fa-play me-2"></i> Iniciar Bot';
        stopBtn.setAttribute('onclick', 'startBot()');
        stopBtn.disabled = false;
        
        showNotification('Bot detenido exitosamente', 'info');
        updateMetrics();
    }, 1500);
}

function restartBot() {
    if (confirm('¿Estás seguro de que quieres reiniciar el bot?')) {
        showNotification('Reiniciando bot...', 'info');
        setTimeout(() => {
            showNotification('Bot reiniciado exitosamente', 'success');
            updateMetrics();
        }, 2000);
    }
}

// ============= BACKUP PAGE FUNCTIONS =============

let backupInterval;
let currentProgress = 0;

function createBackup(type) {
    if (confirm(`¿Crear respaldo ${type === 'full' ? 'completo' : type === 'database' ? 'de base de datos' : 'de archivos'} ahora?`)) {
        // Show progress panel
        const progressPanel = document.getElementById('backupProgress');
        if (progressPanel) {
            progressPanel.style.display = 'block';
        }
        
        // Reset progress
        currentProgress = 0;
        updateProgress(0);
        
        // Start backup simulation
        backupInterval = setInterval(() => {
            currentProgress += Math.random() * 10;
            if (currentProgress >= 100) {
                currentProgress = 100;
                clearInterval(backupInterval);
                completeBackup();
            }
            updateProgress(currentProgress);
        }, 500);
    }
}

function updateProgress(percent) {
    const circle = document.getElementById('progressCircle');
    const percentText = document.getElementById('progressPercent');
    const filesProcessed = document.getElementById('filesProcessed');
    const dataSize = document.getElementById('dataSize');
    const timeElapsed = document.getElementById('timeElapsed');
    
    if (circle && percentText && filesProcessed && dataSize && timeElapsed) {
        const circumference = 2 * Math.PI * 52;
        const offset = circumference - (percent / 100) * circumference;
        
        circle.style.strokeDashoffset = offset;
        percentText.textContent = Math.round(percent) + '%';
        filesProcessed.textContent = Math.round(percent * 2.5);
        dataSize.textContent = Math.round(percent * 2.45) + ' MB';
        timeElapsed.textContent = Math.round(percent * 0.6) + 's';
    }
}

function completeBackup() {
    setTimeout(() => {
        const progressPanel = document.getElementById('backupProgress');
        if (progressPanel) {
            progressPanel.style.display = 'none';
        }
        showNotification('Respaldo completado exitosamente', 'success');
        refreshHistory();
    }, 2000);
}

function restoreBackup() {
    if (confirm('¿Restaurar desde un respaldo existente? Esta acción sobreescribirá los datos actuales.')) {
        showNotification('Función de restauración en desarrollo', 'info');
    }
}

function restoreFromBackup(backupId) {
    if (confirm(`¿Restaurar desde el respaldo #${backupId}? Esta acción no se puede deshacer.`)) {
        showNotification(`Restaurando desde respaldo #${backupId}...`, 'info');
    }
}

function downloadBackup(backupId) {
    showNotification(`Descargando respaldo #${backupId}...`, 'info');
}

function viewDetails(backupId) {
    showNotification(`Ver detalles del respaldo #${backupId}`, 'info');
}

function deleteBackup(backupId) {
    if (confirm(`¿Eliminar el respaldo #${backupId}?`)) {
        showNotification(`Respaldo #${backupId} eliminado`, 'success');
        refreshHistory();
    }
}

function saveSchedule() {
    showNotification('Configuración de respaldo guardada', 'success');
}

function testSchedule() {
    showNotification('Programación de respaldo probada exitosamente', 'info');
}

function refreshHistory() {
    location.reload();
}

function cleanupBackups() {
    if (confirm('¿Limpiar respaldos antiguos? Se eliminarán los respaldos mayores a 30 días.')) {
        showNotification('Respaldos antiguos eliminados', 'success');
        refreshHistory();
    }
}

function loadMoreBackups() {
    showNotification('Cargando más respaldos...', 'info');
}

// ============= BOT CONTROL PAGE FUNCTIONS =============

function startBackup() {
    const startBtn = document.querySelector('button[onclick="startBackup()"]');
    const progressBar = document.getElementById('backupProgress');
    const progressText = document.getElementById('progressText');
    
    startBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Respaldo en progreso...';
    startBtn.disabled = true;
    
    currentProgress = 0;
}

function clearCache() {
    if (confirm('¿Estás seguro de que deseas limpiar el caché?')) {
        addLog('Limpiando caché...', 'info');
        setTimeout(() => {
            addLog('Caché limpiado correctamente', 'success');
        }, 1500);
    }
}

function refreshLogs() {
    addLog('Logs actualizados', 'info');
}

function clearLogs() {
    if (confirm('¿Estás seguro de que deseas limpiar los logs?')) {
        const logsContainer = document.getElementById('botLogs');
        if (logsContainer) {
            logsContainer.innerHTML = '<div style="color: #ff9800;">[LOGS LIMPIADOS]</div>';
        }
    }
}

function sendBroadcast() {
    const message = prompt('Escribe el mensaje para broadcast:');
    if (message) {
        addLog(`Enviando broadcast: "${message}"`, 'info');
        setTimeout(() => {
            addLog('Broadcast enviado a todos los usuarios', 'success');
        }, 2000);
    }
}

function backupData() {
    addLog('Iniciando respaldo de datos...', 'info');
    setTimeout(() => {
        addLog('Respaldo completado exitosamente', 'success');
    }, 3000);
}

function updateBot() {
    addLog('Verificando actualizaciones...', 'info');
    setTimeout(() => {
        addLog('Bot está actualizado', 'success');
    }, 2000);
}

function viewStats() {
    addLog('Abriendo estadísticas detalladas...', 'info');
}

function addLog(message, type) {
    const logsContainer = document.getElementById('botLogs');
    if (!logsContainer) return;
    
    const timestamp = new Date().toLocaleString();
    const colors = {
        info: '#2196f3',
        success: '#4caf50',
        warning: '#ff9800',
        error: '#f44336'
    };
    
    const logEntry = document.createElement('div');
    logEntry.style.color = colors[type] || '#d4d4d4';
    logEntry.textContent = `[${timestamp}] ${type.toUpperCase()}: ${message}`;
    
    logsContainer.appendChild(logEntry);
    logsContainer.scrollTop = logsContainer.scrollHeight;
}

// ============= PASSWORD CHANGE FUNCTIONS =============

function checkPasswordStrength(password) {
    let strength = 0;
    const requirements = {
        length: password.length >= 8,
        uppercase: /[A-Z]/.test(password),
        lowercase: /[a-z]/.test(password),
        number: /[0-9]/.test(password)
    };

    // Update requirement indicators
    Object.keys(requirements).forEach(req => {
        const element = document.getElementById(req);
        if (element) {
            if (requirements[req]) {
                element.classList.add('valid');
                element.classList.remove('invalid');
                element.innerHTML = `<i class="fas fa-check-circle"></i> ${getRequirementText(req)}`;
                strength++;
            } else {
                element.classList.add('invalid');
                element.classList.remove('valid');
                element.innerHTML = `<i class="fas fa-times-circle"></i> ${getRequirementText(req)}`;
            }
        }
    });

    return strength;
}

function getRequirementText(req) {
    const texts = {
        length: 'Mínimo 8 caracteres',
        uppercase: 'Una mayúscula',
        lowercase: 'Una minúscula',
        number: 'Un número'
    };
    return texts[req] || req;
}

// ============= DATABASE FUNCTIONS =============

function optimizeDatabase() {
    if (confirm('¿Estás seguro de que deseas optimizar la base de datos?')) {
        showNotification('Optimizando base de datos...', 'warning');
        setTimeout(() => {
            showNotification('Base de datos optimizada exitosamente', 'success');
            updateStats();
        }, 2000);
    }
}

function viewLogs() {
    showNotification('Abriendo logs de la base de datos...', 'info');
    setTimeout(() => {
        addQueryResult('Logs disponibles:', 'info');
        addQueryResult('- 2024-03-04 15:30:00: Conexión establecida', 'normal');
        addQueryResult('- 2024-03-04 15:31:00: Query ejecutado: SELECT * FROM users', 'normal');
        addQueryResult('- 2024-03-04 15:32:00: Backup completado', 'normal');
    }, 1000);
}

function refreshStats() {
    showNotification('Actualizando estadísticas...', 'info');
    updateStats();
    setTimeout(() => {
        showNotification('Estadísticas actualizadas', 'success');
    }, 1000);
}

function viewTable(tableName) {
    addQueryResult(`Mostrando datos de la tabla: ${tableName}`, 'info');
    setTimeout(() => {
        addQueryResult(`✓ Tabla ${tableName} cargada`, 'success');
    }, 1000);
}

function exportTable(tableName) {
    if (confirm(`¿Exportar tabla ${tableName}?`)) {
        addQueryResult(`Exportando tabla: ${tableName}`, 'info');
        setTimeout(() => {
            addQueryResult(`✓ Tabla ${tableName} exportada como ${tableName}.csv`, 'success');
        }, 2000);
    }
}

function optimizeTable(tableName) {
    if (confirm(`¿Optimizar tabla ${tableName}?`)) {
        addQueryResult(`Optimizando tabla: ${tableName}`, 'warning');
        setTimeout(() => {
            addQueryResult(`✓ Tabla ${tableName} optimizada`, 'success');
        }, 1500);
    }
}

// ============= HELP PAGE FUNCTIONS =============

function filterCategory() {
    const category = document.getElementById('categoryFilter').value;
    const categories = document.querySelectorAll('.help-category');
    
    categories.forEach(cat => {
        if (category === 'all' || cat.dataset.category === category) {
            cat.style.display = 'block';
        } else {
            cat.style.display = 'none';
        }
    });
}

function toggleFAQ(element) {
    const answer = element.nextElementSibling;
    const icon = element.querySelector('i');
    
    answer.classList.toggle('show');
    icon.classList.toggle('fa-chevron-down');
    icon.classList.toggle('fa-chevron-up');
}

function openGuide(topic) {
    showNotification(`Abriendo guía: ${topic}`, 'info');
}

function startTutorial(tutorial) {
    if (confirm(`¿Comenzar el tutorial "${tutorial}"?`)) {
        showNotification(`Tutorial "${tutorial}" iniciado`, 'success');
    }
}

// ============= LOGS FUNCTIONS =============

function addLiveLog() {
    const console = document.getElementById('liveConsole');
    if (!console) return;
    
    const timestamp = new Date().toLocaleString();
    
    const messages = [
        { text: 'Usuario conectado', level: 'info', source: 'Web Service' },
        { text: 'Ejercicio procesado', level: 'success', source: 'Bot' },
        { text: 'Sistema funcionando normalmente', level: 'info', source: 'Sistema' },
        { text: 'Query ejecutado exitosamente', level: 'success', source: 'Database' },
        { text: 'Memoria disponible: 45%', level: 'warning', source: 'Sistema' },
        { text: 'Backup programado completado', level: 'success', source: 'Database' }
    ];
    
    const msg = messages[Math.floor(Math.random() * messages.length)];
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry log-${msg.level}`;
    logEntry.textContent = `[${timestamp}] ${msg.level.toUpperCase()}: ${msg.text}`;
    
    console.appendChild(logEntry);
    console.scrollTop = console.scrollHeight;
    
    // Remove old logs if too many
    const logs = console.querySelectorAll('.log-entry');
    if (logs.length > 50) {
        logs[0].remove();
    }
}

function searchLogs() {
    const searchValue = document.getElementById('searchInput').value.toLowerCase();
    const rows = document.querySelectorAll('#logsTableBody tr');
    
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(searchValue) ? '' : 'none';
    });
}

function viewLogDetails(logId) {
    showNotification(`Ver detalles del log #${logId}`, 'info');
}

function shareLog(logId) {
    if (confirm(`¿Compartir log #${logId}?`)) {
        showNotification(`Log #${logId} compartido exitosamente`, 'success');
    }
}

function exportLogs() {
    if (confirm('¿Exportar todos los logs?')) {
        showNotification('Logs exportados como logs_' + new Date().toISOString().split('T')[0] + '.csv', 'success');
    }
}

function clearAllLogs() {
    if (confirm('¿Estás seguro de que deseas eliminar todos los logs? Esta acción no se puede deshacer.')) {
        const tableBody = document.getElementById('logsTableBody');
        if (tableBody) {
            tableBody.innerHTML = '<tr><td colspan="6" class="text-center text-muted py-4">Todos los logs han sido eliminados</td></tr>';
        }
        updateStats();
    }
}

// ============= NOTIFICATIONS FUNCTIONS =============

function scheduleNotification() {
    const scheduleTime = document.getElementById('scheduleTime').value;
    if (scheduleTime) {
        showNotification(`Notificación programada para ${new Date(scheduleTime).toLocaleString()}`, 'success');
    } else {
        showNotification('Por favor selecciona una fecha y hora para programar', 'warning');
    }
}

function saveDraft() {
    showNotification('Borrador guardado exitosamente', 'success');
}

function filterNotifications() {
    const typeFilter = document.getElementById('typeFilter').value;
    const statusFilter = document.getElementById('statusFilter').value;
    const notifications = document.querySelectorAll('.notification-item');
    
    notifications.forEach(notification => {
        let show = true;
        
        if (typeFilter !== 'all' && notification.dataset.type !== typeFilter) {
            show = false;
        }
        
        if (statusFilter !== 'all' && notification.dataset.status !== statusFilter) {
            show = false;
        }
        
        notification.style.display = show ? 'block' : 'none';
    });
}

function searchNotifications() {
    const searchValue = document.getElementById('searchInput').value.toLowerCase();
    const notifications = document.querySelectorAll('.notification-item');
    
    notifications.forEach(notification => {
        const text = notification.textContent.toLowerCase();
        notification.style.display = text.includes(searchValue) ? 'block' : 'none';
    });
}

function markAsRead(button) {
    const notification = button.closest('.notification-item');
    if (notification) {
        notification.classList.remove('unread');
        notification.classList.add('read');
        notification.dataset.status = 'read';
        
        // Update badge
        const badge = notification.querySelector('.badge.bg-warning');
        if (badge) {
            badge.classList.remove('bg-warning');
            badge.classList.add('bg-success');
            badge.textContent = 'Leída';
        }
        
        updateStats();
    }
}

function markAllAsRead() {
    if (confirm('¿Marcar todas las notificaciones como leídas?')) {
        const unreadNotifications = document.querySelectorAll('.notification-item.unread');
        unreadNotifications.forEach(notification => {
            notification.classList.remove('unread');
            notification.classList.add('read');
            notification.dataset.status = 'read';
            
            const badge = notification.querySelector('.badge.bg-warning');
            if (badge) {
                badge.classList.remove('bg-warning');
                badge.classList.add('bg-success');
                badge.textContent = 'Leída';
            }
        });
        updateStats();
    }
}

function deleteNotification(id) {
    if (confirm('¿Estás seguro de que deseas eliminar esta notificación?')) {
        const notification = document.querySelector(`.notification-item:nth-child(${id})`);
        if (notification) {
            notification.remove();
            updateStats();
        }
    }
}

function deleteSelected() {
    showNotification('Función de eliminación múltiple en desarrollo', 'info');
}

function refreshNotifications() {
    location.reload();
}

function exportNotifications() {
    if (confirm('¿Exportar todas las notificaciones?')) {
        showNotification('Notificaciones exportadas como notifications_' + new Date().toISOString().split('T')[0] + '.csv', 'success');
    }
}

function loadMore() {
    showNotification('Cargando más notificaciones...', 'info');
}

// ============= PROFILE FUNCTIONS =============

function resetProfile() {
    if (confirm('¿Restablecer todos los campos a sus valores originales?')) {
        const fullNameInput = document.getElementById('fullName');
        const phoneInput = document.getElementById('phone');
        const timezoneSelect = document.getElementById('timezone');
        const languageSelect = document.getElementById('language');
        
        if (fullNameInput) fullNameInput.value = 'Administrador del Sistema';
        if (phoneInput) phoneInput.value = '';
        if (timezoneSelect) timezoneSelect.value = 'America/Mexico_City';
        if (languageSelect) languageSelect.value = 'es';
        
        showNotification('Perfil restablecido', 'info');
    }
}

function loadMoreActivity() {
    showNotification('Cargando más actividad...', 'info');
}

function revokeSessions() {
    if (confirm('¿Estás seguro de que deseas cerrar todas las sesiones activas? Tendrás que volver a iniciar sesión.')) {
        showNotification('Todas las sesiones han sido cerradas', 'warning');
    }
}

function autoSave() {
    showNotification('Cambios guardados automáticamente', 'success');
}

// ============= DASHBOARD FUNCTIONS =============

function animateCounter(element, target) {
    const duration = 2000;
    const start = 0;
    const increment = target / (duration / 16);
    let current = start;
    
    const timer = setInterval(() => {
        current += increment;
        if (current >= target) {
            current = target;
            clearInterval(timer);
        }
        element.textContent = Math.floor(current).toLocaleString();
    }, 16);
}

document.addEventListener('DOMContentLoaded', function() {
    const newPasswordInput = document.getElementById('new_password');
    if (newPasswordInput) {
        newPasswordInput.addEventListener('input', function() {
            checkPasswordStrength(this.value);
        });
    }
});

// ============= EXERCISE MODAL FUNCTION =============

function openAddModal() {
    // Check if modal exists
    let modalElement = document.getElementById('exerciseModal');
    
    // Create modal if it doesn't exist
    if (!modalElement) {
        createExerciseModal();
        modalElement = document.getElementById('exerciseModal');
    }
    
    // Initialize Bootstrap modal
    let exerciseModal = bootstrap.Modal.getInstance(modalElement);
    if (!exerciseModal) {
        exerciseModal = new bootstrap.Modal(modalElement);
    }
    
    // Reset form
    document.getElementById('modalTitle').textContent = 'Agregar Nuevo Ejercicio';
    document.getElementById('exerciseForm').reset();
    document.getElementById('exerciseId').value = '';
    
    // Reset options
    for (let i = 1; i <= 4; i++) {
        const optionElement = document.getElementById(`option${i}`);
        if (optionElement) optionElement.value = '';
    }
    
    // Reset correct answer radio
    document.querySelector('input[name="correctAnswer"]:checked')?.setAttribute('checked', false);
    
    // Show modal
    exerciseModal.show();
}

function importExercises() {
    // Create file input dynamically
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = '.json';
    fileInput.style.display = 'none';
    
    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            if (file.name.endsWith('.json')) {
                // Handle file upload
                handleBulkUpload({ target: { files: [file] } });
            } else {
                showNotification('Por favor selecciona un archivo JSON válido', 'danger');
            }
        }
        // Remove the input element
        document.body.removeChild(fileInput);
    });
    
    // Add to body and trigger click
    document.body.appendChild(fileInput);
    fileInput.click();
}

function saveExercise() {
    // Validate form
    const question = document.getElementById('question').value.trim();
    const level = document.getElementById('level').value;
    const option1 = document.getElementById('option1').value.trim();
    const option2 = document.getElementById('option2').value.trim();
    const option3 = document.getElementById('option3').value.trim();
    const option4 = document.getElementById('option4').value.trim();
    const correctAnswer = document.querySelector('input[name="correctAnswer"]:checked');
    const explanation = document.getElementById('explanation').value.trim();
    
    // Validation
    if (!question || !level || !option1 || !option2 || !option3 || !option4) {
        showNotification('Por favor completa todos los campos obligatorios', 'warning');
        return;
    }
    
    if (!correctAnswer) {
        showNotification('Por favor selecciona la respuesta correcta', 'warning');
        return;
    }
    
    // Show loading state
    const saveBtn = document.querySelector('#exerciseModal .btn-primary');
    const originalText = saveBtn.innerHTML;
    saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Guardando...';
    saveBtn.disabled = true;
    
    // Prepare form data
    const formData = {
        question: question,
        level: level,
        options: [option1, option2, option3, option4],
        correct_answer: parseInt(correctAnswer.value),
        explanation: explanation
    };
    
    // Simulate save (replace with actual API call)
    setTimeout(() => {
        saveBtn.innerHTML = originalText;
        saveBtn.disabled = false;
        
        // Hide modal
        const exerciseModal = bootstrap.Modal.getInstance(document.getElementById('exerciseModal'));
        exerciseModal.hide();
        
        showNotification('Ejercicio agregado exitosamente', 'success');
        
        // Reset form
        document.getElementById('exerciseForm').reset();
        
        // Refresh exercises list if function exists
        if (typeof refreshExercises === 'function') {
            refreshExercises();
        }
    }, 2000);
}

// Handle bulk upload functionality
function handleBulkUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    if (!file.name.endsWith('.json')) {
        showNotification('Por favor selecciona un archivo JSON válido', 'danger');
        return;
    }
    
    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const exercises = JSON.parse(e.target.result);
            if (Array.isArray(exercises) && exercises.length > 0) {
                showLoading(true);
                
                // Simulate import (replace with actual API call)
                setTimeout(() => {
                    showLoading(false);
                    showNotification(`${exercises.length} ejercicios importados exitosamente`, 'success');
                    
                    // Refresh exercises list if function exists
                    if (typeof refreshExercises === 'function') {
                        refreshExercises();
                    }
                }, 2000);
            } else {
                showNotification('El archivo no contiene ejercicios válidos', 'danger');
            }
        } catch (error) {
            console.error('Error reading JSON file:', error);
            showNotification('Error al leer el archivo JSON: ' + error.message, 'danger');
        }
    };
    reader.readAsText(file);
}

// ============= INITIALIZATION =============

// Initialize common functionality when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    const tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    const popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
});
