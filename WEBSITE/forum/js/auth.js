const Auth = {
    token: null,
    user: null,

    async init() {
        this.token = localStorage.getItem('forum_token');
        if (this.token) {
            await this.checkAuth();
        }
        this.bindEvents();
    },

    async checkAuth() {
        try {
            const response = await fetch('/api/auth/me', {
                headers: {
                    'Authorization': `Bearer ${this.token}`
                }
            });

            const result = await response.json();
            if (result.success) {
                this.user = result.data;
                this.updateUI();
            } else {
                this.logout(false);
            }
        } catch (error) {
            console.error('Auth check failed:', error);
            this.logout(false);
        }
    },

    updateUI() {
        const userElements = document.querySelectorAll('.auth-user');
        userElements.forEach(el => {
            el.style.display = this.user ? 'flex' : 'none';
        });

        const guestElements = document.querySelectorAll('.auth-guest');
        guestElements.forEach(el => {
            el.style.display = this.user ? 'none' : 'flex';
        });

        const usernameElements = document.querySelectorAll('.auth-username');
        usernameElements.forEach(el => {
            if (this.user) {
                el.textContent = this.user.username;
                if (el.tagName === 'DIV' || el.tagName === 'SPAN') {
                    el.style.backgroundImage = `url(${this.user.avatar})`;
                }
            }
        });
    },

    bindEvents() {
        const tabs = document.querySelectorAll('.auth-tab');
        tabs.forEach(tab => {
            tab.addEventListener('click', () => this.switchTab(tab.dataset.tab));
        });

        const loginForm = document.getElementById('loginForm');
        if (loginForm) {
            loginForm.addEventListener('submit', (e) => this.handleLogin(e));
        }

        const registerForm = document.getElementById('registerForm');
        if (registerForm) {
            registerForm.addEventListener('submit', (e) => this.handleRegister(e));

            const passwordInput = document.getElementById('regPassword');
            if (passwordInput) {
                passwordInput.addEventListener('input', (e) => this.checkPasswordStrength(e.target.value));
            }
        }

        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => this.logout());
        }
    },

    switchTab(tab) {
        document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.auth-form').forEach(f => f.classList.remove('active'));

        document.querySelector(`.auth-tab[data-tab="${tab}"]`).classList.add('active');
        document.getElementById(`${tab}Form`).classList.add('active');

        this.hideMessages();
    },

    async handleLogin(event) {
        event.preventDefault();

        const username = document.getElementById('loginUsername').value.trim();
        const password = document.getElementById('loginPassword').value;
        const btn = document.getElementById('loginBtn');

        if (!username || !password) {
            this.showError('请填写完整的登录信息');
            return;
        }

        btn.disabled = true;
        btn.innerHTML = '<span class="loading-spinner"></span> 登录中...';

        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password })
            });

            const result = await response.json();

            if (result.success) {
                this.token = result.data.token;
                this.user = result.data.user;
                localStorage.setItem('forum_token', this.token);
                this.updateUI();
                this.showSuccess('登录成功！');

                setTimeout(() => {
                    window.location.href = 'index.html';
                }, 1000);
            } else {
                this.showError(result.error || '登录失败，请检查用户名和密码');
            }
        } catch (error) {
            console.error('Login error:', error);
            this.showError('网络错误，请检查网络连接后重试');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '🚀 立即登录';
        }
    },

    async handleRegister(event) {
        event.preventDefault();

        const username = document.getElementById('regUsername').value.trim();
        const email = document.getElementById('regEmail').value.trim();
        const password = document.getElementById('regPassword').value;
        const passwordConfirm = document.getElementById('regPasswordConfirm').value;
        const btn = document.getElementById('registerBtn');

        if (!username || !password || !passwordConfirm) {
            this.showError('请填写完整的注册信息');
            return;
        }

        if (password !== passwordConfirm) {
            this.showError('两次输入的密码不一致');
            return;
        }

        btn.disabled = true;
        btn.innerHTML = '<span class="loading-spinner"></span> 注册中...';

        try {
            const response = await fetch('/api/auth/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, email, password })
            });

            const result = await response.json();

            if (result.success) {
                this.showSuccess('注册成功！请登录');

                setTimeout(() => {
                    this.switchTab('login');
                    document.getElementById('loginUsername').value = username;
                }, 1500);
            } else {
                this.showError(result.error || '注册失败，请重试');
            }
        } catch (error) {
            console.error('Register error:', error);
            this.showError('网络错误，请检查网络连接后重试');
        } finally {
            btn.disabled = false;
            btn.innerHTML = '✨ 创建账户';
        }
    },

    checkPasswordStrength(password) {
        const bar = document.getElementById('strengthBar');
        if (!bar) return;

        let strength = 0;
        if (password.length >= 6) strength++;
        if (password.length >= 10) strength++;
        if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++;
        if (/[0-9]/.test(password)) strength++;
        if (/[^a-zA-Z0-9]/.test(password)) strength++;

        bar.className = 'password-strength-bar';
        if (strength < 3) {
            bar.classList.add('strength-weak');
        } else if (strength < 5) {
            bar.classList.add('strength-medium');
        } else {
            bar.classList.add('strength-strong');
        }
    },

    async logout(showMessage = true) {
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

        this.token = null;
        this.user = null;
        localStorage.removeItem('forum_token');
        this.updateUI();

        if (showMessage) {
            this.showSuccess('已退出登录');
        }

        setTimeout(() => {
            window.location.href = 'index.html';
        }, 1000);
    },

    showError(message) {
        const errorEl = document.getElementById('errorMessage');
        const successEl = document.getElementById('successMessage');

        if (errorEl) {
            errorEl.textContent = message;
            errorEl.style.display = 'block';
        }
        if (successEl) {
            successEl.style.display = 'none';
        }

        setTimeout(() => {
            if (errorEl) errorEl.style.display = 'none';
        }, 5000);
    },

    showSuccess(message) {
        const errorEl = document.getElementById('errorMessage');
        const successEl = document.getElementById('successMessage');

        if (successEl) {
            successEl.textContent = message;
            successEl.style.display = 'block';
        }
        if (errorEl) {
            errorEl.style.display = 'none';
        }

        setTimeout(() => {
            if (successEl) successEl.style.display = 'none';
        }, 5000);
    },

    hideMessages() {
        const errorEl = document.getElementById('errorMessage');
        const successEl = document.getElementById('successMessage');

        if (errorEl) errorEl.style.display = 'none';
        if (successEl) successEl.style.display = 'none';
    },

    getToken() {
        return this.token;
    },

    isLoggedIn() {
        return !!this.token && !!this.user;
    }
};

document.addEventListener('DOMContentLoaded', () => {
    Auth.init();
});
