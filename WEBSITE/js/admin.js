const Admin = {
    currentUser: null,
    currentRole: 'user',
    isLoggedIn: false,

    init() {
        this.loadUserFromStorage();
        this.setupEventListeners();
        this.setupCharts();
        if (this.isLoggedIn) {
            this.showAdminLayout();
        }
    },

    loadUserFromStorage() {
        const savedUser = localStorage.getItem('admin_user');
        if (savedUser) {
            try {
                this.currentUser = JSON.parse(savedUser);
                this.currentRole = this.currentUser.role || 'user';
                this.isLoggedIn = true;
            } catch (e) {
                this.logout();
            }
        }
    },

    saveUserToStorage() {
        if (this.currentUser) {
            localStorage.setItem('admin_user', JSON.stringify(this.currentUser));
        }
    },

    logout() {
        this.currentUser = null;
        this.currentRole = 'user';
        this.isLoggedIn = false;
        localStorage.removeItem('admin_user');
    },

    setupEventListeners() {
        document.getElementById('loginForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleLogin();
        });

        document.querySelectorAll('.admin-nav-item').forEach(item => {
            item.addEventListener('click', () => {
                document.querySelectorAll('.admin-nav-item').forEach(i => i.classList.remove('active'));
                item.classList.add('active');
            });
        });
    },

    selectRole(role) {
        this.currentRole = role;
        document.querySelectorAll('.admin-login-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.role === role);
        });
    },

    async handleLogin() {
        const username = document.getElementById('loginUsername').value;
        const password = document.getElementById('loginPassword').value;

        if (!username || !password) {
            this.showNotification('请填写完整信息', 'error');
            return;
        }

        const submitBtn = document.querySelector('#loginForm button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<span class="loading"></span> 登录中...';
        submitBtn.disabled = true;

        try {
            const response = await apiCall('/api/auth/login', {
                method: 'POST',
                body: JSON.stringify({ username, password, role: this.currentRole })
            });

            if (response.success) {
                this.currentUser = response.user;
                this.currentRole = response.user.role || 'user';
                this.isLoggedIn = true;
                this.saveUserToStorage();
                this.showAdminLayout();
                this.showNotification('登录成功！', 'success');
            } else {
                this.showNotification(response.error || '登录失败', 'error');
            }
        } catch (error) {
            this.showNotification('登录失败，请重试', 'error');
        } finally {
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
        }
    },

    showAdminLayout() {
        document.getElementById('loginPage').style.display = 'none';
        document.getElementById('adminLayout').style.display = 'flex';

        this.updateUserInfo();
        this.updateNavForRole();
        this.loadDashboardData();
    },

    showLoginPage() {
        document.getElementById('loginPage').style.display = 'flex';
        document.getElementById('adminLayout').style.display = 'none';
    },

    updateUserInfo() {
        if (this.currentUser) {
            const name = this.currentUser.name || this.currentUser.username || '用户';
            document.getElementById('userName').textContent = name;
            document.getElementById('userAvatar').textContent = name.charAt(0).toUpperCase();
            document.getElementById('userRole').textContent = this.currentRole === 'admin' ? '管理员' : '普通用户';
        }
    },

    updateNavForRole() {
        const adminSections = document.querySelectorAll('.admin-only-section');
        const userSections = document.querySelectorAll('.user-only-section');

        if (this.currentRole === 'admin') {
            adminSections.forEach(el => el.style.display = 'block');
            userSections.forEach(el => el.style.display = 'block');
        } else {
            adminSections.forEach(el => el.style.display = 'none');
            userSections.forEach(el => el.style.display = 'block');
        }
    },

    showAdminPage(pageName) {
        document.querySelectorAll('.admin-page').forEach(page => {
            page.style.display = 'none';
        });

        const page = document.getElementById('page' + pageName.charAt(0).toUpperCase() + pageName.slice(1));
        if (page) {
            page.style.display = 'block';
        }

        const pageTitles = {
            dashboard: '仪表盘',
            users: '用户管理',
            profile: '个人资料',
            settings: '偏好设置',
            analytics: '数据分析',
            logs: '操作日志',
            system: '系统状态',
            config: '系统配置',
            history: '使用记录'
        };

        document.getElementById('breadcrumbCurrent').textContent = pageTitles[pageName] || pageName;

        document.querySelectorAll('.admin-nav-item').forEach(item => {
            item.classList.toggle('active', item.dataset.page === pageName);
        });

        if (pageName === 'dashboard') {
            this.loadDashboardData();
        }
    },

    async loadDashboardData() {
        try {
            const stats = await apiCall('/api/admin/stats');
            if (stats.success) {
                document.getElementById('totalUsers').textContent = this.formatNumber(stats.users || 1234);
                document.getElementById('totalDownloads').textContent = this.formatNumber(stats.downloads || 56700);
                document.getElementById('aiConversations').textContent = this.formatNumber(stats.aiConversations || 89200);
                document.getElementById('videoDownloads').textContent = this.formatNumber(stats.videoDownloads || 12300);
            }
        } catch (error) {
            console.log('Using demo data');
        }
    },

    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'k';
        }
        return num.toString();
    },

    setupCharts() {
        this.renderActivityChart();
    },

    renderActivityChart() {
        const chart = document.getElementById('activityChart');
        if (!chart) return;

        const data = [65, 78, 90, 81, 95, 88, 92];
        const labels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
        const maxValue = Math.max(...data);

        chart.innerHTML = data.map((value, index) => `
            <div class="admin-chart-bar" style="height: ${(value / maxValue) * 100}%" data-value="${value}">
                <span class="admin-chart-label">${labels[index]}</span>
            </div>
        `).join('');
    },

    toggleSidebar() {
        const sidebar = document.getElementById('adminSidebar');
        sidebar.classList.toggle('collapsed');
    },

    showUserMenu() {
        const menu = document.createElement('div');
        menu.className = 'dropdown-menu';
        menu.innerHTML = `
            <a href="#" onclick="Admin.showAdminPage('profile'); return false;">个人资料</a>
            <a href="#" onclick="Admin.showAdminPage('settings'); return false;">设置</a>
            <hr style="border: none; border-top: 1px solid var(--border); margin: 8px 0;">
            <a href="#" onclick="Admin.handleLogout(); return false;">退出登录</a>
        `;
        menu.style.cssText = `
            position: absolute;
            top: 100%;
            right: 0;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 8px 0;
            min-width: 160px;
            z-index: 100;
            box-shadow: var(--shadow-lg);
        `;

        const userDiv = document.querySelector('.admin-user');
        userDiv.appendChild(menu);

        document.addEventListener('click', function handler(e) {
            if (!menu.contains(e.target)) {
                menu.remove();
                document.removeEventListener('click', handler);
            }
        });
    },

    async handleLogout() {
        try {
            await apiCall('/api/auth/logout', { method: 'POST' });
        } catch (e) {
            console.log('Logout API call skipped');
        }
        this.logout();
        this.showLoginPage();
        this.showNotification('已退出登录', 'success');
    },

    showAddUserModal() {
        document.getElementById('addUserModal').classList.add('active');
    },

    async addUser() {
        const username = document.querySelector('#addUserModal input[type="text"]').value;
        const email = document.querySelector('#addUserModal input[type="email"]').value;
        const password = document.querySelector('#addUserModal input[type="password"]').value;
        const role = document.querySelector('#addUserModal select').value;

        if (!username || !email || !password) {
            this.showNotification('请填写完整信息', 'error');
            return;
        }

        try {
            const response = await apiCall('/api/admin/users', {
                method: 'POST',
                body: JSON.stringify({ username, email, password, role })
            });

            if (response.success) {
                this.closeModal('addUserModal');
                this.showNotification('用户添加成功', 'success');
                this.loadUsers();
            } else {
                this.showNotification(response.error || '添加失败', 'error');
            }
        } catch (error) {
            this.showNotification('添加失败，请重试', 'error');
        }
    },

    closeModal(modalId) {
        document.getElementById(modalId).classList.remove('active');
    },

    async loadUsers() {
        try {
            const response = await apiCall('/api/admin/users');
            if (response.success) {
                this.renderUsersTable(response.users);
            }
        } catch (error) {
            console.log('Using demo users');
        }
    },

    renderUsersTable(users) {
        const tbody = document.getElementById('usersTableBody');
        if (!tbody) return;

        tbody.innerHTML = users.map(user => `
            <tr>
                <td>
                    <div class="admin-user-cell">
                        <div class="avatar">${(user.name || user.username).charAt(0).toUpperCase()}</div>
                        <span>${user.name || user.username}</span>
                    </div>
                </td>
                <td>${user.email}</td>
                <td><span class="badge ${user.role === 'admin' ? 'badge-primary' : ''}" style="background: var(--bg-elevated); color: var(--text-secondary);">${user.role === 'admin' ? '管理员' : '用户'}</span></td>
                <td><span class="admin-status ${user.status === 'active' ? 'active' : 'inactive'}">●</span> ${user.status === 'active' ? '正常' : '禁用'}</td>
                <td>${new Date(user.createdAt).toLocaleDateString()}</td>
                <td>
                    <div class="admin-actions">
                        <button class="admin-action-btn edit" title="编辑" onclick="Admin.editUser('${user.id}')">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                            </svg>
                        </button>
                        <button class="admin-action-btn delete" title="删除" onclick="Admin.deleteUser('${user.id}')">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <polyline points="3 6 5 6 21 6"/>
                                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                            </svg>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
    },

    async editUser(userId) {
        this.showNotification('编辑用户功能开发中', 'info');
    },

    async deleteUser(userId) {
        if (!confirm('确定要删除此用户吗？')) return;

        try {
            const response = await apiCall(`/api/admin/users/${userId}`, { method: 'DELETE' });
            if (response.success) {
                this.showNotification('用户已删除', 'success');
                this.loadUsers();
            } else {
                this.showNotification(response.error || '删除失败', 'error');
            }
        } catch (error) {
            this.showNotification('删除失败，请重试', 'error');
        }
    },

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <span>${message}</span>
            <button onclick="this.parentElement.remove()">×</button>
        `;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 16px 24px;
            background: ${type === 'success' ? 'var(--success)' : type === 'error' ? 'var(--error)' : 'var(--info)'};
            color: white;
            border-radius: var(--radius);
            display: flex;
            align-items: center;
            gap: 12px;
            z-index: 9999;
            animation: slideIn 0.3s ease;
            box-shadow: var(--shadow-lg);
        `;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
};

const Auth = {
    async login(username, password, role = 'user') {
        return apiCall('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify({ username, password, role })
        });
    },

    async register(data) {
        return apiCall('/api/auth/register', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async logout() {
        return apiCall('/api/auth/logout', { method: 'POST' });
    },

    async getProfile() {
        return apiCall('/api/auth/profile');
    },

    async updateProfile(data) {
        return apiCall('/api/auth/profile', {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    async changePassword(oldPassword, newPassword) {
        return apiCall('/api/auth/password', {
            method: 'POST',
            body: JSON.stringify({ oldPassword, newPassword })
        });
    }
};

const AdminAPI = {
    async getStats() {
        return apiCall('/api/admin/stats');
    },

    async getUsers(params = {}) {
        return apiCall('/api/admin/users?' + new URLSearchParams(params));
    },

    async createUser(data) {
        return apiCall('/api/admin/users', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    async updateUser(userId, data) {
        return apiCall(`/api/admin/users/${userId}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    async deleteUser(userId) {
        return apiCall(`/api/admin/users/${userId}`, { method: 'DELETE' });
    },

    async getLogs(params = {}) {
        return apiCall('/api/admin/logs?' + new URLSearchParams(params));
    },

    async getAnalytics(days = 7) {
        return apiCall(`/api/admin/analytics?days=${days}`);
    },

    async getSystemInfo() {
        return apiCall('/api/admin/system');
    },

    async updateConfig(config) {
        return apiCall('/api/admin/config', {
            method: 'POST',
            body: JSON.stringify(config)
        });
    }
};

document.addEventListener('DOMContentLoaded', () => {
    Admin.init();
});

window.Admin = Admin;
window.Auth = Auth;
window.AdminAPI = AdminAPI;
