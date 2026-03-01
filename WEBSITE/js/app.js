const UserMenu = {
    currentUser: null,

    init() {
        this.loadUserFromStorage();
        this.updateUI();
    },

    loadUserFromStorage() {
        const savedUser = localStorage.getItem('admin_user');
        if (savedUser) {
            try {
                this.currentUser = JSON.parse(savedUser);
            } catch (e) {
                this.currentUser = null;
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
        localStorage.removeItem('admin_user');
        this.updateUI();
        if (typeof Admin !== 'undefined' && Admin.handleLogout) {
            Admin.handleLogout();
        }
    },

    updateUI() {
        const loginBtn = document.getElementById('loginBtn');
        const adminLink = document.getElementById('adminLink');
        const userMenu = document.getElementById('userMenu');
        const userName = document.getElementById('userName');
        const userAvatar = document.getElementById('userAvatar');

        if (this.currentUser) {
            loginBtn.style.display = 'none';
            adminLink.style.display = 'flex';
            userMenu.style.display = 'block';
            userName.textContent = this.currentUser.name || this.currentUser.username || '用户';
            if (userAvatar) {
                userAvatar.textContent = (this.currentUser.name || this.currentUser.username || 'U').charAt(0).toUpperCase();
            }
        } else {
            loginBtn.style.display = 'flex';
            adminLink.style.display = 'none';
            userMenu.style.display = 'none';
        }
    }
};

function toggleUserDropdown() {
    const dropdown = document.getElementById('userDropdown');
    if (dropdown) {
        dropdown.classList.toggle('show');
    }
}

document.addEventListener('click', function(e) {
    const dropdown = document.getElementById('userDropdown');
    const trigger = document.querySelector('.user-menu-trigger');
    if (dropdown && trigger && !trigger.contains(e.target) && !dropdown.contains(e.target)) {
        dropdown.classList.remove('show');
    }
});

const App = {
    init() {
        this.setupNavigation();
        this.setupAnimations();
        this.setupMobileMenu();
        this.setupConnectionStatus();
        UserMenu.init();
    },

    setupNavigation() {
        const currentPage = window.location.pathname.split('/').pop() || 'index.html';
        document.querySelectorAll('.nav-links a').forEach(link => {
            const href = link.getAttribute('href');
            if (href === currentPage) {
                link.classList.add('active');
            } else {
                link.classList.remove('active');
            }
        });
    },

    setupAnimations() {
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('fade-in');
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);

        document.querySelectorAll('.card, .tool-card, .section-header').forEach(el => {
            observer.observe(el);
        });
    },

    setupMobileMenu() {
        const menuBtn = document.querySelector('.mobile-menu-btn');
        const navLinks = document.querySelector('.nav-links');

        if (menuBtn && navLinks) {
            menuBtn.addEventListener('click', () => {
                navLinks.classList.toggle('mobile-open');
                menuBtn.classList.toggle('active');
            });
        }
    },

    setupConnectionStatus() {
        const statusElement = document.querySelector('.connection-status');
        if (!statusElement) return;

        const checkConnection = async () => {
            try {
                const response = await fetch('/api/status');
                if (response.ok) {
                    statusElement.classList.remove('disconnected');
                    statusElement.classList.add('connected');
                    statusElement.innerHTML = '<span class="status-dot"></span>已连接';
                } else {
                    throw new Error('Connection failed');
                }
            } catch (error) {
                statusElement.classList.remove('connected');
                statusElement.classList.add('disconnected');
                statusElement.innerHTML = '<span class="status-dot"></span>未连接';
            }
        };

        checkConnection();
        setInterval(checkConnection, 30000);
    }
};

const API = {
    baseUrl: '',

    async call(endpoint, options = {}) {
        try {
            const response = await fetch(this.baseUrl + endpoint, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            return { success: false, error: error.message };
        }
    },

    async status() {
        return this.call('/api/status');
    },

    async routes() {
        return this.call('/api/routes');
    }
};

const MusicPlayer = {
    state: {
        playing: false,
        current: null,
        progress: 0,
        volume: 80,
        playlist: []
    },

    init() {
        this.syncState();
        setInterval(() => this.syncState(), 2000);
    },

    async syncState() {
        const result = await API.call('/api/music/status');
        if (result.success && result.data) {
            this.state = { ...this.state, ...result.data };
            this.updateUI();
        }
    },

    updateUI() {
        const playBtn = document.getElementById('playPauseBtn');
        const progressBar = document.getElementById('musicProgress');
        const currentTrack = document.getElementById('currentTrack');

        if (playBtn) {
            playBtn.textContent = this.state.playing ? '⏸' : '▶';
        }

        if (progressBar) {
            progressBar.style.width = `${this.state.progress}%`;
        }

        if (currentTrack && this.state.current) {
            currentTrack.textContent = this.state.current.title || '未播放';
        }
    },

    async play() {
        await API.call('/api/music/play', { method: 'POST' });
        this.state.playing = true;
        this.updateUI();
    },

    async pause() {
        await API.call('/api/music/pause', { method: 'POST' });
        this.state.playing = false;
        this.updateUI();
    },

    async toggle() {
        if (this.state.playing) {
            await this.pause();
        } else {
            await this.play();
        }
    },

    async next() {
        await API.call('/api/music/next', { method: 'POST' });
        this.state.progress = 0;
        this.syncState();
    },

    async prev() {
        await API.call('/api/music/previous', { method: 'POST' });
        this.state.progress = 0;
        this.syncState();
    },

    async setVolume(value) {
        await API.call('/api/music/volume', {
            method: 'POST',
            body: JSON.stringify({ volume: parseInt(value) })
        });
    },

    async addToPlaylist(url) {
        await API.call('/api/music/playlist/add', {
            method: 'POST',
            body: JSON.stringify({ url })
        });
    }
};

const AIChat = {
    history: [],

    init() {
        this.loadHistory();
        this.setupInput();
    },

    loadHistory() {
        const saved = localStorage.getItem('ai_chat_history');
        if (saved) {
            this.history = JSON.parse(saved);
        }
    },

    saveHistory() {
        localStorage.setItem('ai_chat_history', JSON.stringify(this.history));
    },

    setupInput() {
        const input = document.getElementById('aiInput');
        const sendBtn = document.getElementById('aiSendBtn');

        if (input && sendBtn) {
            const send = async () => {
                const message = input.value.trim();
                if (!message) return;

                this.addMessage(message, 'user');
                input.value = '';

                await this.sendToAI(message);
            };

            sendBtn.addEventListener('click', send);
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') send();
            });
        }
    },

    addMessage(content, role) {
        const container = document.getElementById('chatMessages');
        if (!container) return;

        const msgDiv = document.createElement('div');
        msgDiv.className = `chat-message ${role}`;
        msgDiv.innerHTML = content;
        container.appendChild(msgDiv);
        container.scrollTop = container.scrollHeight;

        this.history.push({ role, content, timestamp: Date.now() });
        this.saveHistory();
    },

    async sendToAI(message) {
        const container = document.getElementById('chatMessages');
        if (!container) return;

        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'chat-message assistant';
        loadingDiv.innerHTML = '<span class="loading"></span> AI 思考中...';
        container.appendChild(loadingDiv);
        container.scrollTop = container.scrollHeight;

        try {
            const result = await API.call('/api/ai/chat', {
                method: 'POST',
                body: JSON.stringify({ message })
            });

            loadingDiv.remove();

            if (result.success) {
                this.addMessage(result.response || result.message, 'assistant');
            } else {
                loadingDiv.innerHTML = '❌ ' + (result.error || '请求失败');
            }
        } catch (error) {
            loadingDiv.innerHTML = '❌ 网络错误，请重试';
        }
    }
};

const RandomTools = {
    async generateNumber(min = 1, max = 100, count = 1) {
        return API.call('/api/random/number', {
            method: 'POST',
            body: JSON.stringify({ min, max, count })
        });
    },

    async generatePassword(length = 16, options = {}) {
        return API.call('/api/random/password', {
            method: 'POST',
            body: JSON.stringify({ length, ...options })
        });
    },

    async generateUUID() {
        return API.call('/api/random/uuid', { method: 'POST' });
    },

    async generateColor(format = 'hex') {
        return API.call('/api/random/color', {
            method: 'POST',
            body: JSON.stringify({ format })
        });
    }
};

const DownloadManager = {
    async getPlatforms() {
        return API.call('/api/download/platforms');
    },

    async startDownload(url, platform) {
        return API.call('/api/download', {
            method: 'POST',
            body: JSON.stringify({ url, platform })
        });
    },

    getQueue() {
        return API.call('/api/download/queue');
    },

    clearQueue() {
        return API.call('/api/download/clear', { method: 'POST' });
    }
};

const TextTools = {
    async convert(text, type) {
        return API.call('/api/text/convert', {
            method: 'POST',
            body: JSON.stringify({ text, type })
        });
    }
};

document.addEventListener('DOMContentLoaded', () => {
    App.init();

    if (document.getElementById('musicPlayer')) {
        MusicPlayer.init();
    }

    if (document.getElementById('aiChat')) {
        AIChat.init();
    }
});

window.apiCall = API.call;
window.musicPlayer = MusicPlayer;
window.aiChat = AIChat;
window.randomTools = RandomTools;
window.downloadManager = DownloadManager;
window.textTools = TextTools;
