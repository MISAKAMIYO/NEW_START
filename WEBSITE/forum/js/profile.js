const Profile = {
    user: null,
    token: null,

    async init() {
        this.token = localStorage.getItem('forum_token');
        if (!this.token) {
            window.location.href = 'login.html';
            return;
        }

        await this.loadProfile();
        this.bindEvents();
    },

    async loadProfile() {
        try {
            const response = await fetch('/api/auth/me', {
                headers: {
                    'Authorization': `Bearer ${this.token}`
                }
            });

            const result = await response.json();

            if (result.success) {
                this.user = result.data;
                this.renderProfile();
                await this.loadMyPosts();
                await this.loadNotifications();
            } else {
                this.showToast('请先登录', 'error');
                setTimeout(() => {
                    window.location.href = 'login.html';
                }, 1500);
            }
        } catch (error) {
            console.error('Failed to load profile:', error);
            this.showToast('加载失败，请刷新重试', 'error');
        }
    },

    renderProfile() {
        const avatarEl = document.getElementById('profileAvatar');
        if (avatarEl) {
            avatarEl.textContent = this.user.username.charAt(0).toUpperCase();
            if (this.user.avatar) {
                avatarEl.innerHTML = `<img src="${this.escapeHtml(this.user.avatar)}" alt="头像">`;
            }
        }

        const usernameEl = document.getElementById('profileUsername');
        if (usernameEl) {
            usernameEl.textContent = this.user.username;
        }

        const bioEl = document.getElementById('profileBio');
        if (bioEl) {
            bioEl.textContent = this.user.bio || '暂无个人简介';
        }

        document.getElementById('statPosts').textContent = this.formatNumber(this.user.post_count || 0);
        document.getElementById('statLikes').textContent = this.formatNumber(this.user.like_count || 0);

        const joinDateEl = document.getElementById('joinDate');
        if (joinDateEl && this.user.created_at) {
            const date = new Date(this.user.created_at);
            joinDateEl.textContent = date.toLocaleDateString('zh-CN');
            document.getElementById('statCreated').textContent = this.calcDays(date);
        }

        document.getElementById('editUsername').value = this.user.username;
        document.getElementById('editBio').value = this.user.bio || '';
    },

    calcDays(date) {
        const now = new Date();
        const diff = Math.floor((now - date) / (1000 * 60 * 60 * 24));
        if (diff < 1) return '今天';
        if (diff < 30) return `${diff}天`;
        if (diff < 365) return `${Math.floor(diff / 30)}月`;
        return `${Math.floor(diff / 365)}年`;
    },

    async loadMyPosts() {
        try {
            const response = await fetch('/api/posts?per_page=50', {
                headers: {
                    'Authorization': `Bearer ${this.token}`
                }
            });

            const result = await response.json();

            if (result.success) {
                const myPosts = result.data.posts.filter(p => p.author === this.user.username);
                this.renderMyPosts(myPosts);
            }
        } catch (error) {
            console.error('Failed to load posts:', error);
        }
    },

    renderMyPosts(posts) {
        const container = document.getElementById('myPostsList');

        if (posts.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📭</div>
                    <p>还没有发布过帖子</p>
                    <a href="new.html" class="btn btn-primary" style="margin-top: 16px;">发布第一个帖子</a>
                </div>
            `;
            return;
        }

        container.innerHTML = posts.slice(0, 10).map(post => `
            <a href="post.html?id=${post.id}" class="activity-item">
                <div class="activity-title">${this.escapeHtml(post.title)}</div>
                <div class="activity-meta">
                    <span class="activity-badge">${this.getCategoryIcon(post.category)} ${this.getCategoryName(post.category)}</span>
                    <span>👁️ ${this.formatNumber(post.view_count || 0)}</span>
                    <span>💬 ${this.formatNumber(post.reply_count || 0)}</span>
                    <span>🕐 ${this.formatTime(post.created_at)}</span>
                </div>
            </a>
        `).join('');
    },

    async loadNotifications() {
        try {
            const response = await fetch('/api/notifications', {
                headers: {
                    'Authorization': `Bearer ${this.token}`
                }
            });

            const result = await response.json();

            if (result.success) {
                this.renderNotifications(result.data);
            }
        } catch (error) {
            console.error('Failed to load notifications:', error);
        }
    },

    renderNotifications(notifications) {
        const container = document.getElementById('notificationsList');

        if (notifications.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🔔</div>
                    <p>暂无通知</p>
                </div>
            `;
            return;
        }

        container.innerHTML = notifications.slice(0, 10).map(n => `
            <div class="notification-item ${n.read ? '' : 'unread'}" onclick="window.location.href='post.html?id=${n.post_id}'">
                <div class="notification-icon">${n.type === 'reply' ? '💬' : '❤️'}</div>
                <div class="notification-content">
                    <div class="notification-message">${this.escapeHtml(n.message)}</div>
                    <div class="notification-time">${this.formatTime(n.created_at)}</div>
                </div>
            </div>
        `).join('');
    },

    bindEvents() {
        const editBtn = document.getElementById('editProfileBtn');
        if (editBtn) {
            editBtn.addEventListener('click', () => this.showEditForm());
        }

        const cancelBtn = document.getElementById('cancelEditBtn');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this.hideEditForm());
        }

        const saveBtn = document.getElementById('saveProfileBtn');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveProfile());
        }

        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => this.logout());
        }

        const avatarInput = document.getElementById('avatarInput');
        if (avatarInput) {
            avatarInput.addEventListener('change', (e) => this.uploadAvatar(e));
        }
    },

    showEditForm() {
        document.getElementById('profileHeader').style.display = 'none';
        document.getElementById('profileContent').style.display = 'none';
        document.getElementById('editProfileForm').classList.add('active');
    },

    hideEditForm() {
        document.getElementById('editProfileForm').classList.remove('active');
        document.getElementById('profileHeader').style.display = 'flex';
        document.getElementById('profileContent').style.display = 'grid';
    },

    async saveProfile() {
        const bio = document.getElementById('editBio').value.trim();

        try {
            const response = await fetch('/api/auth/update_profile', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.token}`
                },
                body: JSON.stringify({ bio })
            });

            const result = await response.json();

            if (result.success) {
                this.user.bio = result.data.bio;
                this.renderProfile();
                this.hideEditForm();
                this.showToast('资料更新成功', 'success');
            } else {
                this.showToast(result.error || '更新失败', 'error');
            }
        } catch (error) {
            console.error('Save profile error:', error);
            this.showToast('网络错误，请重试', 'error');
        }
    },

    async uploadAvatar(event) {
        const file = event.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('avatar', file);

        try {
            const response = await fetch('/api/upload/avatar', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.token}`
                },
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                this.user.avatar = result.data.url;
                this.renderProfile();
                this.showToast('头像上传成功', 'success');
            } else {
                this.showToast(result.error || '上传失败', 'error');
            }
        } catch (error) {
            console.error('Upload avatar error:', error);
            this.showToast('网络错误，请重试', 'error');
        }
    },

    async logout() {
        try {
            await fetch('/api/auth/logout', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.token}`
                }
            });
        } catch (error) {
            console.error('Logout error:', error);
        }

        localStorage.removeItem('forum_token');
        this.showToast('已退出登录', 'success');

        setTimeout(() => {
            window.location.href = 'index.html';
        }, 1000);
    },

    formatNumber(num) {
        if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
        if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
        return num.toString();
    },

    formatTime(dateStr) {
        const date = new Date(dateStr);
        const now = new Date();
        const diff = Math.floor((now - date) / 1000);

        if (isNaN(diff)) return '未知时间';
        if (diff < 0) return '刚刚';
        if (diff < 60) return '刚刚';
        if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`;
        if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`;
        if (diff < 604800) return `${Math.floor(diff / 86400)} 天前`;

        return date.toLocaleDateString('zh-CN');
    },

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    getCategoryName(category) {
        const names = {
            'general': '综合',
            'suggestion': '建议',
            'bug': 'Bug',
            'discussion': '技术',
            'chat': '闲聊'
        };
        return names[category] || '综合';
    },

    getCategoryIcon(category) {
        const icons = {
            'general': '💬',
            'suggestion': '💡',
            'bug': '🐛',
            'discussion': '💻',
            'chat': '☕'
        };
        return icons[category] || '📝';
    },

    showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;

        const icons = {
            'success': '✅',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️'
        };

        toast.innerHTML = `
            <span class="toast-icon">${icons[type] || icons.info}</span>
            <span class="toast-message">${this.escapeHtml(message)}</span>
        `;

        container.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'slideIn 0.3s ease reverse';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
};

document.addEventListener('DOMContentLoaded', () => {
    Profile.init();
});
