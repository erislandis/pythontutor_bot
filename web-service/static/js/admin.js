/**
 * Python Tutor Bot - Admin Panel JavaScript
 * Common functionality for the admin panel
 */

// Global variables
let currentUserId = null;
let notificationTimeout;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeAdminPanel();
    setupEventListeners();
    initializeTooltips();
    initializeModals();
});

/**
 * Initialize the admin panel
 */
function initializeAdminPanel() {
    console.log('Admin panel initialized');
    
    // Set current user from session
    setCurrentUser();
    
    // Initialize sidebar
    initializeSidebar();
    
    // Auto-hide alerts after 5 seconds
    setupAutoHideAlerts();
    
    // Initialize date/time displays
    updateDateTime();
    setInterval(updateDateTime, 1000);
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Logout confirmation
    const logoutLinks = document.querySelectorAll('a[href*="logout"]');
    logoutLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            if (!confirm('¿Estás seguro de que quieres cerrar sesión?')) {
                e.preventDefault();
            }
        });
    });
    
    // Form validation
    const forms = document.querySelectorAll('form[data-validate]');
    forms.forEach(form => {
        form.addEventListener('submit', validateForm);
    });
    
    // Dynamic content loading
    const dynamicLinks = document.querySelectorAll('a[data-load]');
    dynamicLinks.forEach(link => {
        link.addEventListener('click', loadDynamicContent);
    });
}

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Initialize Bootstrap modals
 */
function initializeModals() {
    // Auto-focus first input in modals
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('shown.bs.modal', function () {
            const firstInput = this.querySelector('input, textarea, select');
            if (firstInput) {
                firstInput.focus();
            }
        });
    });
}

/**
 * Set current user information
 */
function setCurrentUser() {
    // This would typically come from server-side rendering
    const userElement = document.getElementById('current-user');
    if (userElement) {
        currentUserId = userElement.dataset.userId;
    }
}

/**
 * Initialize sidebar functionality
 */
function initializeSidebar() {
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.querySelector('.sidebar');
    
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('show');
        });
    }
    
    // Active state management
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.sidebar .nav-link');
    
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
}

/**
 * Setup auto-hide for alerts
 */
function setupAutoHideAlerts() {
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        setTimeout(() => {
            if (alert.parentNode) {
                alert.style.transition = 'opacity 0.5s';
                alert.style.opacity = '0';
                setTimeout(() => alert.remove(), 500);
            }
        }, 5000);
    });
}

/**
 * Update date and time displays
 */
function updateDateTime() {
    const now = new Date();
    const timeElements = document.querySelectorAll('.current-time');
    const dateElements = document.querySelectorAll('.current-date');
    
    timeElements.forEach(el => {
        el.textContent = now.toLocaleTimeString('es-ES');
    });
    
    dateElements.forEach(el => {
        el.textContent = now.toLocaleDateString('es-ES');
    });
}

/**
 * Show loading state on button
 */
function showLoading(button, text = 'Procesando...') {
    if (!button) return;
    
    button.disabled = true;
    button.dataset.originalText = button.innerHTML;
    button.innerHTML = `<i class="bi bi-arrow-repeat me-2"></i>${text}`;
    button.classList.add('loading');
}

/**
 * Hide loading state on button
 */
function hideLoading(button) {
    if (!button || !button.dataset.originalText) return;
    
    button.disabled = false;
    button.innerHTML = button.dataset.originalText;
    delete button.dataset.originalText;
    button.classList.remove('loading');
}

/**
 * Show notification
 */
function showNotification(message, type = 'info', duration = 5000) {
    // Clear existing timeout
    if (notificationTimeout) {
        clearTimeout(notificationTimeout);
    }
    
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Add to page
    document.body.appendChild(notification);
    
    // Auto-hide
    notificationTimeout = setTimeout(() => {
        notification.style.transition = 'opacity 0.5s';
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 500);
    }, duration);
}

/**
 * Validate form
 */
function validateForm(e) {
    const form = e.target;
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            isValid = false;
            showFieldError(field, 'Este campo es obligatorio');
        } else {
            clearFieldError(field);
        }
    });
    
    if (!isValid) {
        e.preventDefault();
        showNotification('Por favor completa todos los campos obligatorios', 'warning');
    }
    
    return isValid;
}

/**
 * Show field error
 */
function showFieldError(field, message) {
    clearFieldError(field);
    
    field.classList.add('is-invalid');
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'invalid-feedback';
    errorDiv.textContent = message;
    
    field.parentNode.appendChild(errorDiv);
}

/**
 * Clear field error
 */
function clearFieldError(field) {
    field.classList.remove('is-invalid');
    const errorDiv = field.parentNode.querySelector('.invalid-feedback');
    if (errorDiv) {
        errorDiv.remove();
    }
}

/**
 * Load dynamic content
 */
async function loadDynamicContent(e) {
    e.preventDefault();
    const link = e.target.closest('a');
    const url = link.dataset.load;
    const target = link.dataset.target || 'main';
    
    try {
        showLoading(link);
        
        const response = await fetch(url);
        const html = await response.text();
        
        document.querySelector(target).innerHTML = html;
        
        // Re-initialize components
        initializeTooltips();
        initializeModals();
        
        hideLoading(link);
        
    } catch (error) {
        console.error('Error loading content:', error);
        showNotification('Error al cargar el contenido', 'danger');
        hideLoading(link);
    }
}

/**
 * Confirm action
 */
function confirmAction(message, callback) {
    if (confirm(message)) {
        callback();
    }
}

/**
 * Format date
 */
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('es-ES', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

/**
 * Format number
 */
function formatNumber(num) {
    return new Intl.NumberFormat('es-ES').format(num);
}

/**
 * Copy to clipboard
 */
function copyToClipboard(text, button) {
    navigator.clipboard.writeText(text).then(() => {
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="bi bi-check"></i> Copiado';
        button.classList.add('btn-success');
        button.classList.remove('btn-outline-secondary');
        
        setTimeout(() => {
            button.innerHTML = originalText;
            button.classList.remove('btn-success');
            button.classList.add('btn-outline-secondary');
        }, 2000);
    }).catch(err => {
        console.error('Error copying to clipboard:', err);
        showNotification('Error al copiar al portapapeles', 'danger');
    });
}

/**
 * Export data to CSV
 */
function exportToCSV(data, filename) {
    const csv = convertToCSV(data);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

/**
 * Convert data to CSV
 */
function convertToCSV(data) {
    if (!data || data.length === 0) return '';
    
    const headers = Object.keys(data[0]);
    const csvHeaders = headers.join(',');
    
    const csvRows = data.map(row => {
        return headers.map(header => {
            const value = row[header];
            return typeof value === 'string' && value.includes(',') 
                ? `"${value}"` 
                : value;
        }).join(',');
    });
    
    return [csvHeaders, ...csvRows].join('\n');
}

/**
 * Debounce function
 */
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

/**
 * Throttle function
 */
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

/**
 * Check if element is in viewport
 */
function isInViewport(element) {
    const rect = element.getBoundingClientRect();
    return (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
        rect.right <= (window.innerWidth || document.documentElement.clientWidth)
    );
}

/**
 * Scroll to element
 */
function scrollToElement(element, offset = 100) {
    const elementPosition = element.getBoundingClientRect().top + window.pageYOffset;
    const offsetPosition = elementPosition - offset;
    
    window.scrollTo({
        top: offsetPosition,
        behavior: 'smooth'
    });
}

/**
 * Initialize data tables
 */
function initializeDataTable(tableId, options = {}) {
    const defaultOptions = {
        pageLength: 10,
        language: {
            search: "Buscar:",
            lengthMenu: "Mostrar _MENU_ registros",
            info: "Mostrando _START_ a _END_ de _TOTAL_ registros",
            paginate: {
                first: "Primero",
                last: "Último",
                next: "Siguiente",
                previous: "Anterior"
            }
        }
    };
    
    const finalOptions = { ...defaultOptions, ...options };
    
    if (typeof $ !== 'undefined' && $.fn.DataTable) {
        return $(`#${tableId}`).DataTable(finalOptions);
    } else {
        console.warn('jQuery DataTables not loaded');
        return null;
    }
}

/**
 * Handle API errors
 */
function handleApiError(error, customMessage = null) {
    console.error('API Error:', error);
    
    let message = customMessage || 'Error en la operación';
    
    if (error.response) {
        if (error.response.data && error.response.data.error) {
            message = error.response.data.error;
        } else if (error.response.status === 401) {
            message = 'No autorizado. Por favor inicia sesión nuevamente.';
            // Redirect to login after delay
            setTimeout(() => {
                window.location.href = '/login';
            }, 3000);
        } else if (error.response.status === 403) {
            message = 'Acceso denegado. No tienes permisos para esta acción.';
        } else if (error.response.status === 404) {
            message = 'Recurso no encontrado.';
        } else if (error.response.status >= 500) {
            message = 'Error del servidor. Por favor intenta más tarde.';
        }
    } else if (error.request) {
        message = 'Error de conexión. Verifica tu conexión a internet.';
    }
    
    showNotification(message, 'danger');
}

/**
 * Setup keyboard shortcuts
 */
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + S to save forms
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            const activeForm = document.querySelector('form:focus-within') || document.querySelector('form');
            if (activeForm) {
                activeForm.dispatchEvent(new Event('submit'));
            }
        }
        
        // Escape to close modals
        if (e.key === 'Escape') {
            const openModal = document.querySelector('.modal.show');
            if (openModal) {
                bootstrap.Modal.getInstance(openModal).hide();
            }
        }
    });
}

// Initialize keyboard shortcuts
setupKeyboardShortcuts();

// Export functions for global use
window.AdminUtils = {
    showLoading,
    hideLoading,
    showNotification,
    confirmAction,
    formatDate,
    formatNumber,
    copyToClipboard,
    exportToCSV,
    debounce,
    throttle,
    isInViewport,
    scrollToElement,
    initializeDataTable,
    handleApiError
};
