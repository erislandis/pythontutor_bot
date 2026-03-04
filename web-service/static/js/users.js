/**
 * Users Management JavaScript
 * Handles all interactive functionality for the users management page
 */

class UsersManager {
    constructor() {
        this.currentPage = 1;
        this.totalPages = 1;
        this.selectedUsers = new Set();
        this.deleteUserId = null;
        this.searchTimeout = null;
        this.isLoading = false;
        
        this.init();
    }

    init() {
        this.bindElements();
        this.bindEvents();
        this.loadInitialData();
    }

    bindElements() {
        // Search and filters
        this.searchInput = document.getElementById('search-input');
        this.statusFilter = document.getElementById('status-filter');
        this.perPageSelect = document.getElementById('per-page');
        this.refreshBtn = document.getElementById('refresh-btn');
        this.exportBtn = document.getElementById('export-btn');
        
        // Table and pagination
        this.loadingState = document.getElementById('loading-state');
        this.emptyState = document.getElementById('empty-state');
        this.usersTableContainer = document.getElementById('users-table-container');
        this.paginationContainer = document.getElementById('pagination-container');
        this.usersTbody = document.getElementById('users-tbody');
        
        // Bulk actions
        this.bulkActions = document.getElementById('bulk-actions');
        this.selectAllCheckbox = document.getElementById('select-all');
        this.selectedCount = document.getElementById('selected-count');
        this.bulkActivateBtn = document.getElementById('bulk-activate');
        this.bulkDeactivateBtn = document.getElementById('bulk-deactivate');
        this.bulkDeleteBtn = document.getElementById('bulk-delete');
        
        // Modal
        this.deleteModal = new bootstrap.Modal(document.getElementById('deleteModal'));
        this.confirmDeleteBtn = document.getElementById('confirm-delete');
        
        // Stats
        this.totalUsersEl = document.getElementById('total-users');
        this.activeUsersEl = document.getElementById('active-users');
        this.inactiveUsersEl = document.getElementById('inactive-users');
        this.recentUsersEl = document.getElementById('recent-users');
        
        // Toast
        this.toastEl = document.getElementById('liveToast');
        this.toastMessage = document.getElementById('toast-message');
        this.toast = new bootstrap.Toast(this.toastEl);
    }

    bindEvents() {
        // Search and filter events
        this.searchInput.addEventListener('input', () => this.debounceSearch());
        this.statusFilter.addEventListener('change', () => this.loadUsers());
        this.perPageSelect.addEventListener('change', () => this.loadUsers());
        this.refreshBtn.addEventListener('click', () => this.loadUsers());
        this.exportBtn.addEventListener('click', () => this.exportUsers());
        
        // Select all checkbox
        this.selectAllCheckbox.addEventListener('change', () => this.toggleSelectAll());
        
        // Bulk actions
        this.bulkActivateBtn.addEventListener('click', () => this.bulkUpdateStatus(true));
        this.bulkDeactivateBtn.addEventListener('click', () => this.bulkUpdateStatus(false));
        this.bulkDeleteBtn.addEventListener('click', () => this.bulkDelete());
        
        // Delete modal
        this.confirmDeleteBtn.addEventListener('click', () => this.confirmDeleteUser());
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyboardShortcuts(e));
    }

    async loadInitialData() {
        await Promise.all([
            this.loadUsers(),
            this.loadStats()
        ]);
    }

    async loadUsers() {
        if (this.isLoading) return;
        
        this.showLoading();
        this.isLoading = true;
        
        try {
            const params = new URLSearchParams({
                search: this.searchInput.value,
                status: this.statusFilter.value,
                page: this.currentPage,
                per_page: this.perPageSelect.value
            });
            
            const response = await fetch(`/api/admin/users?${params}`);
            const data = await response.json();
            
            if (response.ok) {
                this.renderUsers(data.users);
                this.renderPagination(data.pagination);
                this.updateCounts(data.pagination);
            } else {
                this.showToast('Error al cargar usuarios: ' + data.error, 'danger');
                this.showEmpty();
            }
        } catch (error) {
            console.error('Error loading users:', error);
            this.showToast('Error de conexión al cargar usuarios', 'danger');
            this.showEmpty();
        } finally {
            this.isLoading = false;
        }
    }

    async loadStats() {
        try {
            const response = await fetch('/api/admin/users/stats');
            const stats = await response.json();
            
            if (response.ok) {
                this.animateNumber(this.totalUsersEl, stats.total);
                this.animateNumber(this.activeUsersEl, stats.active);
                this.animateNumber(this.inactiveUsersEl, stats.inactive);
                this.animateNumber(this.recentUsersEl, stats.recent);
            }
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }

    renderUsers(users) {
        if (users.length === 0) {
            this.showEmpty();
            return;
        }
        
        this.usersTbody.innerHTML = users.map(user => this.createUserRow(user)).join('');
        this.hideLoading();
        this.usersTableContainer.style.display = 'block';
        this.paginationContainer.style.display = 'flex';
    }

    createUserRow(user) {
        const initials = user.first_name ? user.first_name[0].toUpperCase() : 'U';
        const displayName = `${user.first_name || 'N/A'} ${user.last_name || ''}`.trim();
        const username = user.username || 'N/A';
        const telegramId = user.telegram_id || 'N/A';
        const level = user.current_level || 1;
        const exercises = user.total_exercises_completed || 0;
        const createdAt = this.formatDate(user.created_at);
        const lastInteraction = this.formatDate(user.last_interaction) || 'Nunca';
        const statusClass = user.is_active ? 'success' : 'warning';
        const statusText = user.is_active ? 'Activo' : 'Inactivo';
        
        return `
            <tr data-user-id="${user.id}">
                <td>
                    <input type="checkbox" class="form-check-input user-checkbox" 
                           value="${user.id}" onchange="usersManager.toggleUserSelection(${user.id})">
                </td>
                <td>
                    <div class="d-flex align-items-center">
                        <div class="user-avatar-sm me-3">${initials}</div>
                        <div>
                            <div class="fw-semibold">${displayName}</div>
                            <small class="text-muted">@${username}</small>
                        </div>
                    </div>
                </td>
                <td>
                    <code class="code-telegram">${telegramId}</code>
                </td>
                <td>
                    <div class="user-progress-mini">
                        <span class="user-level-badge">Nivel ${level}</span>
                        <small class="text-muted">${exercises} ejercicios</small>
                    </div>
                </td>
                <td>
                    <small class="text-muted">${createdAt}</small>
                </td>
                <td>
                    <small class="text-muted">${lastInteraction}</small>
                </td>
                <td>
                    <div class="form-check form-switch">
                        <input class="form-check-input" type="checkbox" 
                               ${user.is_active ? 'checked' : ''}
                               onchange="usersManager.toggleUserStatus(${user.id}, this.checked)">
                        <label class="form-check-label">
                            <span class="badge bg-${statusClass}">${statusText}</span>
                        </label>
                    </div>
                </td>
                <td>
                    <div class="action-buttons btn-group btn-group-sm">
                        <button class="btn btn-outline-primary" onclick="usersManager.viewUserDetails(${user.id})" 
                                title="Ver detalles">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-outline-danger" onclick="usersManager.deleteUser(${user.id}, '${username}')" 
                                title="Eliminar usuario">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }

    renderPagination(pagination) {
        this.currentPage = pagination.page;
        this.totalPages = pagination.pages;
        
        document.getElementById('current-page').textContent = this.currentPage;
        document.getElementById('total-pages').textContent = this.totalPages;
        
        const paginationEl = document.getElementById('pagination');
        paginationEl.innerHTML = this.generatePaginationHTML();
    }

    generatePaginationHTML() {
        let html = '';
        
        // Previous button
        html += `
            <li class="page-item ${this.currentPage === 1 ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="usersManager.changePage(${this.currentPage - 1})">
                    <i class="fas fa-chevron-left"></i>
                </a>
            </li>
        `;
        
        // Page numbers
        for (let i = 1; i <= this.totalPages; i++) {
            if (i === 1 || i === this.totalPages || (i >= this.currentPage - 2 && i <= this.currentPage + 2)) {
                html += `
                    <li class="page-item ${i === this.currentPage ? 'active' : ''}">
                        <a class="page-link" href="#" onclick="usersManager.changePage(${i})">${i}</a>
                    </li>
                `;
            } else if (i === this.currentPage - 3 || i === this.currentPage + 3) {
                html += '<li class="page-item disabled"><a class="page-link">...</a></li>';
            }
        }
        
        // Next button
        html += `
            <li class="page-item ${this.currentPage === this.totalPages ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="usersManager.changePage(${this.currentPage + 1})">
                    <i class="fas fa-chevron-right"></i>
                </a>
            </li>
        `;
        
        return html;
    }

    async toggleUserStatus(userId, isActive) {
        try {
            const response = await fetch(`/api/admin/users/${userId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ is_active: isActive })
            });
            
            if (response.ok) {
                this.showToast(`Usuario ${isActive ? 'activado' : 'desactivado'} exitosamente`, 'success');
                await this.loadStats();
            } else {
                const data = await response.json();
                this.showToast('Error: ' + data.error, 'danger');
                // Revert checkbox
                event.target.checked = !isActive;
            }
        } catch (error) {
            console.error('Error updating user:', error);
            this.showToast('Error de conexión', 'danger');
            event.target.checked = !isActive;
        }
    }

    deleteUser(userId, username) {
        this.deleteUserId = userId;
        document.getElementById('delete-user-info').innerHTML = `
            <strong>Usuario:</strong> ${username}<br>
            <strong>ID:</strong> ${userId}
        `;
        this.deleteModal.show();
    }

    async confirmDeleteUser() {
        if (!this.deleteUserId) return;
        
        try {
            const response = await fetch(`/api/admin/users/${this.deleteUserId}`, {
                method: 'DELETE'
            });
            
            if (response.ok) {
                this.showToast('Usuario eliminado exitosamente', 'success');
                this.deleteModal.hide();
                await this.loadUsers();
                await this.loadStats();
            } else {
                const data = await response.json();
                this.showToast('Error: ' + data.error, 'danger');
            }
        } catch (error) {
            console.error('Error deleting user:', error);
            this.showToast('Error de conexión', 'danger');
        } finally {
            this.deleteUserId = null;
        }
    }

    toggleUserSelection(userId) {
        if (this.selectedUsers.has(userId)) {
            this.selectedUsers.delete(userId);
        } else {
            this.selectedUsers.add(userId);
        }
        this.updateBulkActions();
    }

    toggleSelectAll() {
        const checkboxes = document.querySelectorAll('.user-checkbox');
        checkboxes.forEach(cb => {
            cb.checked = this.selectAllCheckbox.checked;
            const userId = parseInt(cb.value);
            if (this.selectAllCheckbox.checked) {
                this.selectedUsers.add(userId);
            } else {
                this.selectedUsers.delete(userId);
            }
        });
        this.updateBulkActions();
    }

    updateBulkActions() {
        const count = this.selectedUsers.size;
        this.selectedCount.textContent = count;
        this.bulkActions.style.display = count > 0 ? 'block' : 'none';
    }

    async bulkUpdateStatus(isActive) {
        if (this.selectedUsers.size === 0) return;
        
        const action = isActive ? 'activar' : 'desactivar';
        if (!confirm(`¿Estás seguro de ${action} ${this.selectedUsers.size} usuarios?`)) {
            return;
        }
        
        try {
            const promises = Array.from(this.selectedUsers).map(userId => 
                fetch(`/api/admin/users/${userId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ is_active: isActive })
                })
            );
            
            await Promise.all(promises);
            
            this.showToast(`${this.selectedUsers.size} usuarios ${isActive ? 'activados' : 'desactivados'} exitosamente`, 'success');
            this.selectedUsers.clear();
            this.updateBulkActions();
            this.selectAllCheckbox.checked = false;
            await this.loadUsers();
            await this.loadStats();
        } catch (error) {
            console.error('Error in bulk update:', error);
            this.showToast('Error en la actualización masiva', 'danger');
        }
    }

    async bulkDelete() {
        if (this.selectedUsers.size === 0) return;
        
        if (!confirm(`¿Estás seguro de eliminar ${this.selectedUsers.size} usuarios? Esta acción no se puede deshacer.`)) {
            return;
        }
        
        try {
            const promises = Array.from(this.selectedUsers).map(userId => 
                fetch(`/api/admin/users/${userId}`, { method: 'DELETE' })
            );
            
            await Promise.all(promises);
            
            this.showToast(`${this.selectedUsers.size} usuarios eliminados exitosamente`, 'success');
            this.selectedUsers.clear();
            this.updateBulkActions();
            this.selectAllCheckbox.checked = false;
            await this.loadUsers();
            await this.loadStats();
        } catch (error) {
            console.error('Error in bulk delete:', error);
            this.showToast('Error en la eliminación masiva', 'danger');
        }
    }

    changePage(page) {
        if (page < 1 || page > this.totalPages) return;
        this.currentPage = page;
        this.loadUsers();
    }

    debounceSearch() {
        clearTimeout(this.searchTimeout);
        this.searchTimeout = setTimeout(() => {
            this.currentPage = 1;
            this.loadUsers();
        }, 300);
    }

    exportUsers() {
        // Placeholder for export functionality
        this.showToast('Función de exportación próximamente', 'info');
    }

    viewUserDetails(userId) {
        // Placeholder for user details view
        this.showToast(`Ver detalles del usuario ${userId}`, 'info');
    }

    handleKeyboardShortcuts(e) {
        // Ctrl/Cmd + F: Focus search
        if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
            e.preventDefault();
            this.searchInput.focus();
        }
        
        // Ctrl/Cmd + R: Refresh
        if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
            e.preventDefault();
            this.loadUsers();
        }
        
        // Escape: Clear selection
        if (e.key === 'Escape') {
            this.selectedUsers.clear();
            this.updateBulkActions();
            this.selectAllCheckbox.checked = false;
        }
    }

    // Utility methods
    showLoading() {
        this.loadingState.style.display = 'block';
        this.emptyState.style.display = 'none';
        this.usersTableContainer.style.display = 'none';
        this.paginationContainer.style.display = 'none';
    }

    showEmpty() {
        this.loadingState.style.display = 'none';
        this.emptyState.style.display = 'block';
        this.usersTableContainer.style.display = 'none';
        this.paginationContainer.style.display = 'none';
    }

    hideLoading() {
        this.loadingState.style.display = 'none';
        this.emptyState.style.display = 'none';
    }

    updateCounts(pagination) {
        document.getElementById('showing-count').textContent = 
            Math.min(pagination.page * pagination.per_page, pagination.total);
        document.getElementById('total-count').textContent = pagination.total;
    }

    formatDate(dateString) {
        if (!dateString) return null;
        const date = new Date(dateString);
        return date.toLocaleDateString('es-ES', { 
            day: '2-digit', 
            month: '2-digit', 
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    animateNumber(element, target) {
        const duration = 1000;
        const start = parseInt(element.textContent) || 0;
        const increment = (target - start) / (duration / 16);
        let current = start;
        
        const timer = setInterval(() => {
            current += increment;
            if ((increment > 0 && current >= target) || (increment < 0 && current <= target)) {
                element.textContent = target;
                clearInterval(timer);
            } else {
                element.textContent = Math.round(current);
            }
        }, 16);
    }

    showToast(message, type = 'info') {
        const toastHeader = this.toastEl.querySelector('.toast-header i');
        
        this.toastMessage.textContent = message;
        toastHeader.className = `fas me-2 text-${type === 'danger' ? 'danger' : type === 'success' ? 'success' : 'primary'}`;
        
        this.toast.show();
    }
}

// Initialize the users manager when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.usersManager = new UsersManager();
});

// Export for global access
window.UsersManager = UsersManager;
