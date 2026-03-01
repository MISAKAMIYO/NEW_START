const ForumApp = {
    currentPage: 1,
    currentCategory: 'all',
    currentSort: 'latest',
    perPage: 20,
    isLoading: false,
    socket: null,
    user: null,
    token: null,

    async init() {
        this.token = localStorage.getItem('forum_token');
        if (this.token) {
            await this.checkAuth();
        }
        this.bindEvents();
        this.connectWebSocket();
        await this.loadCategories();
        await this.loadStats();
        await this.loadPosts();
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
                this.updateAuthUI();
            } else {
                this.token = null;
                localStorage.removeItem('forum_token');
            }
        } catch (error) {
            console.error('Auth check failed:', error);
            this.token = null;
            localStorage.removeItem('forum_token');
        }
    },

    updateAuthUI() {
        const loginLink = document.getElementById('loginLink');
        const userInfo = document.getElementById('userInfo');
        const usernameDisplay = document.getElementById('usernameDisplay');

        if (this.user) {
            if (loginLink) loginLink.style.display = 'none';
            if (userInfo) userInfo.style.display = 'flex';
            if (usernameDisplay) usernameDisplay.textContent = this.user.username;
        } else {
            if (loginLink) loginLink.style.display = 'block';
            if (userInfo) userInfo.style.display = 'none';
        }
    },

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}`;

        try {
            this.socket = io(wsUrl, {
                transports: ['websocket'],
                reconnection: true,
                reconnectionAttempts: 5,
                reconnectionDelay: 1000
            });

            this.socket.on('connect', () => {
                console.log('WebSocket connected');
                if (this.user) {
                    this.socket.emit('join', { username: this.user.username });
                }
            });

            this.socket.on('disconnect', () => {
                console.log('WebSocket disconnected');
            });

            this.socket.on('new_post', (data) => {
                this.showToast('有新帖子发布！', 'info');
                if (this.currentCategory === 'all' || this.currentCategory === data.post.category) {
                    this.loadPosts();
                }
                this.updateNotificationBadge();
            });

            this.socket.on('new_reply', (data) => {
                this.showToast(`${data.reply.author} 回复了帖子`, 'info');
                if (window.location.pathname.includes('post.html')) {
                    const urlParams = new URLSearchParams(window.location.search);
                    if (parseInt(urlParams.get('id')) === data.post_id) {
                        this.loadPost();
                    }
                }
            });

            this.socket.on('post_liked', (data) => {
                const likeEl = document.querySelector(`[data-post-id="${data.post_id}"] .like-count`);
                if (likeEl) {
                    likeEl.textContent = this.formatNumber(data.like_count);
                }
            });

            this.socket.on('user_joined', (data) => {
                console.log(`${data.username} joined, online: ${data.online_count}`);
            });

            this.socket.on('user_left', (data) => {
                console.log(`${data.username} left, online: ${data.online_count}`);
            });

        } catch (error) {
            console.error('WebSocket connection failed:', error);
        }
    },

    updateNotificationBadge() {
        const badge = document.getElementById('notificationBadge');
        if (badge) {
            let count = parseInt(badge.textContent || '0') + 1;
            badge.textContent = count;
            badge.style.display = 'flex';
        }
    },

    bindEvents() {
        document.querySelectorAll('.category-item').forEach(item => {
            item.addEventListener('click', () => {
                const category = item.dataset.category;
                this.changeCategory(category);
            });
        });

        const loginLink = document.getElementById('loginLink');
        if (loginLink) {
            loginLink.addEventListener('click', (e) => {
                e.preventDefault();
                window.location.href = 'login.html';
            });
        }

        const userInfo = document.getElementById('userInfo');
        if (userInfo) {
            userInfo.addEventListener('click', () => {
                window.location.href = 'profile.html';
            });
        }

        window.addEventListener('online', () => this.handleOnline());
        window.addEventListener('offline', () => this.handleOffline());
    },

    handleOnline() {
        this.showToast('网络已连接', 'success');
        this.loadPosts();
    },

    handleOffline() {
        this.showToast('网络连接已断开', 'error');
    },

    async loadCategories() {
        try {
            const response = await this.fetchWithTimeout('/api/categories', {
                headers: { 'Accept': 'application/json' }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();

            if (result.success) {
                result.data.categories.forEach(cat => {
                    const countEl = document.getElementById(`count-${cat.id}`);
                    if (countEl) {
                        this.animateCount(countEl, 0, cat.count, 500);
                    }
                });
            }
        } catch (error) {
            console.error('Failed to load categories:', error);
            this.showToast('加载分类失败', 'error');
        }
    },

    async loadStats() {
        try {
            const response = await this.fetchWithTimeout('/api/stats', {
                headers: { 'Accept': 'application/json' }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();

            if (result.success) {
                const data = result.data;
                this.animateCount(document.getElementById('total-posts'), 0, data.total_posts, 800);
                this.animateCount(document.getElementById('total-replies'), 0, data.total_replies, 800);
                this.animateCount(document.getElementById('today-posts'), 0, data.today_posts, 600);
                this.animateCount(document.getElementById('online-count'), 0, data.online_count || 0, 600);
            }
        } catch (error) {
            console.error('Failed to load stats:', error);
            this.showToast('加载统计信息失败', 'error');
        }
    },

    animateCount(element, start, end, duration) {
        const startTime = performance.now();

        const updateCount = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);

            const easeOutQuart = 1 - Math.pow(1 - progress, 4);
            const current = Math.floor(start + (end - start) * easeOutQuart);

            element.textContent = this.formatNumber(current);

            if (progress < 1) {
                requestAnimationFrame(updateCount);
            } else {
                element.textContent = this.formatNumber(end);
            }
        };

        requestAnimationFrame(updateCount);
    },

    async loadPosts() {
        if (this.isLoading) return;
        this.isLoading = true;

        const postsList = document.getElementById('postsList');
        postsList.innerHTML = `
            <div class="loading">
                <div class="spinner"></div>
                <div class="loading-text">正在加载帖子${'.'.repeat(Math.floor(Math.random() * 3) + 1)}</div>
            </div>
        `;

        try {
            const params = new URLSearchParams({
                page: this.currentPage,
                per_page: this.perPage,
                category: this.currentCategory,
                sort: this.currentSort
            });

            const response = await this.fetchWithTimeout(`/api/posts?${params}`, {
                headers: { 'Accept': 'application/json' }
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();

            if (result.success) {
                const posts = result.data.posts;
                const pagination = result.data.pagination;

                if (posts.length === 0) {
                    postsList.innerHTML = `
                        <div class="empty-state">
                            <div class="empty-icon">📭</div>
                            <div class="empty-title">暂无帖子</div>
                            <div class="empty-desc">成为第一个发帖的人吧！</div>
                            <a href="new.html" class="btn btn-primary">🚀 发布帖子</a>
                        </div>
                    `;
                    document.getElementById('emptyState').style.display = 'block';
                    document.getElementById('pagination').style.display = 'none';
                } else {
                    document.getElementById('emptyState').style.display = 'none';
                    postsList.innerHTML = posts.map((post, index) => this.renderPostCard(post, index)).join('');
                    this.updatePagination(pagination);
                    this.animateElements();
                }
            } else {
                throw new Error(result.error || '加载帖子失败');
            }
        } catch (error) {
            console.error('Failed to load posts:', error);
            postsList.innerHTML = this.renderErrorState(error.message);
        } finally {
            this.isLoading = false;
        }
    },

    renderErrorState(message) {
        return `
            <div class="error-container">
                <div class="error-icon">⚠️</div>
                <div class="error-title">加载失败</div>
                <div class="error-message">${this.escapeHtml(message || '请检查网络连接后重试')}</div>
                <button class="retry-btn" onclick="ForumApp.loadPosts()">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="23 4 23 10 17 10"/>
                        <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
                    </svg>
                    重新加载
                </button>
            </div>
        `;
    },

    renderPostCard(post, index = 0) {
        const categoryNames = {
            'general': '综合',
            'suggestion': '建议',
            'bug': 'Bug',
            'discussion': '技术',
            'chat': '闲聊'
        };

        const categoryIcons = {
            'general': '💬',
            'suggestion': '💡',
            'bug': '🐛',
            'discussion': '💻',
            'chat': '☕'
        };

        const timeAgo = this.formatTime(post.created_at);
        const avatar = post.author.charAt(0).toUpperCase();

        return `
            <a href="post.html?id=${post.id}" class="post-card" style="animation-delay: ${index * 0.05}s" data-post-id="${post.id}">
                <div class="post-header">
                    <div class="post-avatar">${avatar}</div>
                    <div class="post-info">
                        <h3 class="post-title">${this.escapeHtml(post.title)}</h3>
                        <div class="post-meta">
                            <span class="post-badge">${categoryIcons[post.category] || '📝'} ${categoryNames[post.category] || '综合'}</span>
                            <span>👤 ${this.escapeHtml(post.author)}</span>
                            <span>🕐 ${timeAgo}</span>
                        </div>
                    </div>
                </div>
                <p class="post-content">${this.escapeHtml(post.content)}</p>
                <div class="post-footer">
                    <div class="post-stats">
                        <span class="post-stat" title="浏览次数">👁️ ${this.formatNumber(post.view_count || 0)}</span>
                        <span class="post-stat" title="回复数量">💬 ${this.formatNumber(post.reply_count || 0)}</span>
                        <span class="post-stat like-count" title="点赞数量">❤️ ${this.formatNumber(post.like_count || 0)}</span>
                    </div>
                    <span class="post-author">${this.escapeHtml(post.author)}</span>
                </div>
            </a>
        `;
    },

    updatePagination(pagination) {
        const paginationEl = document.getElementById('pagination');
        const prevBtn = document.getElementById('prevBtn');
        const nextBtn = document.getElementById('nextBtn');
        const pageInfo = document.getElementById('pageInfo');

        if (pagination.total_pages <= 1) {
            paginationEl.style.display = 'none';
            return;
        }

        paginationEl.style.display = 'flex';
        prevBtn.disabled = pagination.page <= 1;
        nextBtn.disabled = pagination.page >= pagination.total_pages;

        prevBtn.style.opacity = pagination.page <= 1 ? '0.5' : '1';
        nextBtn.style.opacity = pagination.page >= pagination.total_pages ? '0.5' : '1';

        pageInfo.textContent = `第 ${pagination.page} / ${pagination.total_pages} 页`;
    },

    changeCategory(category) {
        this.currentCategory = category;
        this.currentPage = 1;

        document.querySelectorAll('.category-item').forEach(item => {
            item.classList.toggle('active', item.dataset.category === category);
        });

        const titles = {
            'all': '全部帖子',
            'general': '综合讨论',
            'suggestion': '建议反馈',
            'bug': 'Bug反馈',
            'discussion': '技术讨论',
            'chat': '闲聊灌水'
        };
        document.getElementById('forumTitle').textContent = titles[category] || '全部帖子';

        this.loadPosts();
    },

    changeSort(sort) {
        this.currentSort = sort;

        document.querySelectorAll('.sort-tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.sort === sort);
        });

        this.loadPosts();
    },

    changePage(delta) {
        this.currentPage += delta;
        this.loadPosts();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    },

    animateElements() {
        const cards = document.querySelectorAll('.post-card');
        cards.forEach((card, index) => {
            card.style.animationDelay = `${index * 0.08}s`;
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';

            setTimeout(() => {
                card.style.transition = 'all 0.5s cubic-bezier(0.4, 0, 0.2, 1)';
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, index * 80);
        });
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

    async fetchWithTimeout(url, options = {}) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 15000);

        try {
            const response = await fetch(url, {
                ...options,
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            return response;
        } catch (error) {
            clearTimeout(timeoutId);
            if (error.name === 'AbortError') {
                throw new Error('请求超时，请检查网络连接');
            }
            throw error;
        }
    },

    showToast(message, type = 'info', duration = 3000) {
        const toast = document.getElementById('toast');
        if (!toast) {
            console.warn('Toast element not found');
            return;
        }

        const icons = {
            'success': '✅',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️'
        };

        toast.innerHTML = `<span class="toast-icon">${icons[type] || icons.info}</span><span class="toast-message">${message}</span>`;
        toast.className = `toast ${type} show`;

        setTimeout(() => {
            toast.classList.remove('show');
        }, duration);
    }
};

const PostDetail = {
    postId: null,
    isLoading: false,
    post: null,
    currentReplyPage: 1,
    replySort: 'time',
    replyPerPage: 10,
    replyTo: null,

    async init() {
        this.postId = POST_ID;
        this.token = localStorage.getItem('forum_token');
        if (this.token) {
            await this.checkAuth();
        }
        this.bindReplyEditorEvents();
        await this.loadPost();
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
                this.updateAuthUI();
            } else {
                this.token = null;
                localStorage.removeItem('forum_token');
            }
        } catch (error) {
            console.error('Auth check failed:', error);
            this.token = null;
            localStorage.removeItem('forum_token');
        }
    },

    updateAuthUI() {
        const loginLink = document.getElementById('loginLink');
        const userInfo = document.getElementById('userInfo');
        const usernameDisplay = document.getElementById('usernameDisplay');
        const authorInput = document.getElementById('replyAuthor');

        if (this.user) {
            if (loginLink) loginLink.style.display = 'none';
            if (userInfo) userInfo.style.display = 'flex';
            if (usernameDisplay) usernameDisplay.textContent = this.user.username;
            if (authorInput) {
                authorInput.value = this.user.username;
                authorInput.parentElement.style.display = 'none';
            }
        } else {
            if (loginLink) loginLink.style.display = 'block';
            if (userInfo) userInfo.style.display = 'none';
            if (authorInput) authorInput.parentElement.style.display = 'block';
        }
    },

    bindReplyEditorEvents() {
        const toolbar = document.getElementById('replyToolbar');
        const textarea = document.getElementById('replyContent');

        if (toolbar) {
            toolbar.addEventListener('click', (e) => {
                const btn = e.target.closest('button');
                if (!btn) return;
                const action = btn.dataset.action;
                this.handleEditorAction(action, textarea);
            });
        }

        if (textarea) {
            textarea.addEventListener('input', () => {
                this.updateReplyPreview();
            });
        }
    },

    handleEditorAction(action, textarea) {
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const text = textarea.value;
        const selectedText = text.substring(start, end);

        let insertion = '';
        let cursorOffset = 0;

        switch (action) {
            case 'bold':
                insertion = `**${selectedText || '粗体文本'}**`;
                cursorOffset = selectedText ? 0 : 2;
                break;
            case 'italic':
                insertion = `*${selectedText || '斜体文本'}*`;
                cursorOffset = selectedText ? 0 : 1;
                break;
            case 'heading':
                insertion = `\n### ${selectedText || '标题'}\n`;
                cursorOffset = 4;
                break;
            case 'code':
                insertion = `\`${selectedText || '代码'}\``;
                cursorOffset = selectedText ? 0 : 1;
                break;
            case 'quote':
                insertion = `\n> ${selectedText || '引用文本'}\n`;
                cursorOffset = 3;
                break;
            case 'link':
                insertion = `[${selectedText || '链接文本'}](https://)`;
                cursorOffset = selectedText ? 0 : 1;
                break;
        }

        if (insertion) {
            const newText = text.substring(0, start) + insertion + text.substring(end);
            textarea.value = newText;
            textarea.focus();

            const newCursorPos = start + insertion.length - cursorOffset;
            textarea.setSelectionRange(newCursorPos, newCursorPos);

            this.updateReplyPreview();
        }
    },

    updateReplyPreview() {
        const textarea = document.getElementById('replyContent');
        const preview = document.getElementById('replyPreview');
        if (!textarea || !preview) return;

        const text = textarea.value;
        const html = this.markdownToHtml(text);
        preview.innerHTML = html || '<p style="color: var(--text-muted);">预览区域...</p>';
    },

    markdownToHtml(text) {
        let html = ForumApp.escapeHtml(text);

        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
        html = html.replace(/`(.*?)`/g, '<code>$1</code>');
        html = html.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');

        html = html.replace(/### (.*?)/g, '<h3>$1</h3>');
        html = html.replace(/## (.*?)/g, '<h2>$1</h2>');
        html = html.replace(/!\[(.*?)\]\((.*?)\)/g, '<img src="$2" alt="$1" style="max-width:100%;border-radius:8px;margin:8px 0;">');
        html = html.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank" style="color:var(--primary);">$1</a>');
        html = html.replace(/^> (.*?)/gm, '<blockquote>$1</blockquote>');

        html = html.replace(/\n/g, '<br>');
        return html;
    },

    async loadPost() {
        if (this.isLoading) return;
        this.isLoading = true;

        const container = document.getElementById('postDetail');
        container.innerHTML = `
            <div class="loading">
                <div class="spinner"></div>
                <div class="loading-text">正在加载帖子内容${'.'.repeat(Math.floor(Math.random() * 3) + 1)}</div>
            </div>
        `;

        try {
            const params = new URLSearchParams({
                sort: this.replySort,
                page: this.currentReplyPage,
                per_page: this.replyPerPage
            });

            const response = await ForumApp.fetchWithTimeout(`/api/posts/${this.postId}?${params}`, {
                headers: { 'Accept': 'application/json' }
            });

            if (!response.ok) {
                if (response.status === 404) {
                    throw new Error('帖子不存在');
                }
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();

            if (result.success) {
                const post = result.data.post;
                const replies = result.data.replies;
                const pagination = result.data.pagination;
                this.post = post;

                container.innerHTML = this.renderPostDetail(post);
                document.title = `${post.title} - RAILGUN 论坛`;

                document.getElementById('repliesSection').style.display = 'block';
                document.getElementById('replyCount').textContent = pagination.total;
                this.renderReplies(replies);
                this.updateReplyPagination(pagination);
                this.updateSortButtons();
                this.animateElements();

                this.bindPostActions(post);

                if (ForumApp.socket) {
                    ForumApp.socket.emit('join', { username: post.author });

                    ForumApp.socket.on('new_reply', async (data) => {
                        if (data.post_id === parseInt(this.postId) && !data.reply.parent_id) {
                            ForumApp.showToast(`${data.reply.author} 发布新回复`, 'info');
                            if (this.currentReplyPage === 1) {
                                await this.loadPost();
                            }
                        }
                    });

                    ForumApp.socket.on('new_child_reply', async (data) => {
                        if (data.post_id === parseInt(this.postId)) {
                            ForumApp.showToast(`${data.reply.author} 回复了你的评论`, 'info');
                        }
                    });
                }
            } else {
                throw new Error(result.error || '加载失败');
            }
        } catch (error) {
            console.error('Failed to load post:', error);
            container.innerHTML = this.renderErrorState(error.message);
        } finally {
            this.isLoading = false;
        }
    },

    renderErrorState(message) {
        return `
            <div class="error-container">
                <div class="error-icon">😕</div>
                <div class="error-title">帖子不存在</div>
                <div class="error-message">${ForumApp.escapeHtml(message || '该帖子可能已被删除或链接有误')}</div>
                <a href="index.html" class="btn btn-primary">🏠 返回首页</a>
            </div>
        `;
    },

    renderPostDetail(post) {
        const categoryNames = {
            'general': '综合讨论',
            'suggestion': '建议反馈',
            'bug': 'Bug反馈',
            'discussion': '技术讨论',
            'chat': '闲聊灌水'
        };

        const categoryIcons = {
            'general': '💬',
            'suggestion': '💡',
            'bug': '🐛',
            'discussion': '💻',
            'chat': '☕'
        };

        const timeAgo = ForumApp.formatTime(post.created_at);
        const avatar = post.author.charAt(0).toUpperCase();
        const formattedDate = new Date(post.created_at).toLocaleString('zh-CN');

        const isAuthor = this.user && this.user.username === post.author;

        return `
            <article class="post-detail">
                <div class="post-detail-header">
                    <h1 class="post-detail-title">${ForumApp.escapeHtml(post.title)}</h1>
                    <div class="post-detail-meta">
                        <span class="post-badge">${categoryIcons[post.category] || '📝'} ${categoryNames[post.category] || '综合'}</span>
                        <span>👤 ${ForumApp.escapeHtml(post.author)}</span>
                        <span>🕐 ${timeAgo}</span>
                        <span>👁️ ${ForumApp.formatNumber(post.view_count || 0)} 次浏览</span>
                    </div>
                </div>
                <div class="post-detail-content">${ForumApp.escapeHtml(post.content)}</div>
                <div style="margin-top: 16px; font-size: 12px; color: var(--text-muted);">
                    发布于 ${formattedDate}
                </div>
                <div class="post-actions">
                    <button class="action-btn" onclick="PostDetail.likePost()" id="likeBtn">
                        ❤️ 点赞 (${ForumApp.formatNumber(post.like_count || 0)})
                    </button>
                    <button class="action-btn" onclick="sharePost()">
                        📤 分享链接
                    </button>
                    ${isAuthor ? `
                        <button class="action-btn" onclick="PostDetail.deletePost()" id="deleteBtn" style="color: #ef4444;">
                            🗑️ 删除
                        </button>
                    ` : ''}
                </div>
            </article>
        `;
    },

    renderReplies(replies) {
        const container = document.getElementById('repliesList');

        if (!replies || replies.length === 0) {
            container.innerHTML = '<div class="empty-state" style="padding: 40px;"><div class="empty-icon">💭</div><div class="empty-desc">暂无回复，快来抢沙发~</div></div>';
            return;
        }

        container.innerHTML = replies.map((reply, index) => this.renderReplyCard(reply, index)).join('');
    },

    renderReplyCard(reply, index = 0) {
        const timeAgo = ForumApp.formatTime(reply.created_at);
        const avatar = reply.author.charAt(0).toUpperCase();
        const formattedDate = new Date(reply.created_at).toLocaleString('zh-CN');

        const isAuthor = this.user && this.user.username === reply.author;
        const content = reply.is_deleted ? '<span style="color: var(--text-muted); font-style: italic;">此评论已删除</span>' : ForumApp.escapeHtml(reply.content);
        const editedBadge = reply.is_edited ? '<span style="font-size: 11px; color: var(--text-muted); margin-left: 8px;">(已编辑)</span>' : '';

        let childRepliesHtml = '';
        if (reply.replies && reply.replies.length > 0) {
            childRepliesHtml = `
                <div class="child-replies">
                    ${reply.replies.map((child, childIndex) => this.renderChildReplyCard(child, childIndex)).join('')}
                </div>
            `;
        }

        return `
            <div class="reply-card" id="reply-${reply.id}" style="animation-delay: ${index * 0.1}s">
                <div class="reply-header">
                    <div class="reply-avatar">${avatar}</div>
                    <span class="reply-author">${ForumApp.escapeHtml(reply.author)}</span>
                    <span class="reply-time" title="${formattedDate}">${timeAgo}</span>
                    ${reply.is_edited ? '<span class="edited-badge">(已编辑)</span>' : ''}
                </div>
                <div class="reply-content">${content}</div>
                <div class="reply-actions">
                    <span class="reply-action" onclick="PostDetail.likeReply(${reply.id})">
                        ❤️ ${ForumApp.formatNumber(reply.like_count || 0)}
                    </span>
                    <span class="reply-action" onclick="PostDetail.replyTo(${reply.id}, '${ForumApp.escapeHtml(reply.author)}')">
                        💬 回复
                    </span>
                    ${isAuthor ? `
                        <span class="reply-action" onclick="PostDetail.editReply(${reply.id})">
                            ✏️ 编辑
                        </span>
                        <span class="reply-action" onclick="PostDetail.deleteReply(${reply.id})" style="color: #ef4444;">
                            🗑️ 删除
                        </span>
                    ` : ''}
                </div>
                ${childRepliesHtml}
            </div>
        `;
    },

    renderChildReplyCard(child, index = 0) {
        const timeAgo = ForumApp.formatTime(child.created_at);
        const avatar = child.author.charAt(0).toUpperCase();
        const formattedDate = new Date(child.created_at).toLocaleString('zh-CN');

        const isAuthor = this.user && this.user.username === child.author;
        const content = child.is_deleted ? '<span style="color: var(--text-muted); font-style: italic;">此评论已删除</span>' : ForumApp.escapeHtml(child.content);

        return `
            <div class="child-reply-card" id="reply-${child.id}" style="animation-delay: ${index * 0.05}s">
                <div class="child-reply-header">
                    <div class="reply-avatar small">${avatar}</div>
                    <span class="reply-author">${ForumApp.escapeHtml(child.author)}</span>
                    <span class="reply-time" title="${formattedDate}">${timeAgo}</span>
                    ${child.is_edited ? '<span class="edited-badge">(已编辑)</span>' : ''}
                </div>
                <div class="reply-content">${content}</div>
                <div class="reply-actions">
                    <span class="reply-action" onclick="PostDetail.likeReply(${child.id})">
                        ❤️ ${ForumApp.formatNumber(child.like_count || 0)}
                    </span>
                    <span class="reply-action" onclick="PostDetail.replyTo(${child.id}, '${ForumApp.escapeHtml(child.author)}')">
                        💬 回复
                    </span>
                    ${isAuthor ? `
                        <span class="reply-action" onclick="PostDetail.editReply(${child.id})">
                            ✏️ 编辑
                        </span>
                        <span class="reply-action" onclick="PostDetail.deleteReply(${child.id})" style="color: #ef4444;">
                            🗑️ 删除
                        </span>
                    ` : ''}
                </div>
            </div>
        `;
    },

    updateReplyPagination(pagination) {
        const paginationEl = document.getElementById('repliesPagination');
        const prevBtn = document.getElementById('repliesPrevBtn');
        const nextBtn = document.getElementById('repliesNextBtn');
        const pageInfo = document.getElementById('repliesPageInfo');

        if (pagination.total_pages <= 1) {
            paginationEl.style.display = 'none';
            return;
        }

        paginationEl.style.display = 'flex';
        prevBtn.disabled = pagination.page <= 1;
        nextBtn.disabled = pagination.page >= pagination.total_pages;

        prevBtn.style.opacity = pagination.page <= 1 ? '0.5' : '1';
        nextBtn.style.opacity = pagination.page >= pagination.total_pages ? '0.5' : '1';

        pageInfo.textContent = `第 ${pagination.page} / ${pagination.total_pages} 页`;
    },

    updateSortButtons() {
        document.querySelectorAll('.reply-sort .sort-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.sort === this.replySort);
        });
    },

    changeSort(sort) {
        this.replySort = sort;
        this.currentReplyPage = 1;
        this.loadPost();
    },

    changeReplyPage(delta) {
        this.currentReplyPage += delta;
        this.loadPost();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    },

    replyTo(replyId, author) {
        this.replyTo = replyId;
        const infoEl = document.getElementById('replyToInfo');
        const authorEl = document.getElementById('replyToAuthor');

        if (infoEl && authorEl) {
            infoEl.style.display = 'block';
            authorEl.textContent = author;
        }

        const textarea = document.getElementById('replyContent');
        if (textarea) {
            textarea.focus();
            textarea.placeholder = `回复 @${author}：`;
        }

        window.scrollTo({
            top: document.getElementById('replyForm').offsetTop - 100,
            behavior: 'smooth'
        });
    },

    cancelReply() {
        this.replyTo = null;
        const infoEl = document.getElementById('replyToInfo');
        const textarea = document.getElementById('replyContent');

        if (infoEl) infoEl.style.display = 'none';
        if (textarea) {
            textarea.placeholder = '支持Markdown语法：\n**粗体** *斜体* \n### 标题\n> 引用\n`代码`';
        }
    },

    bindPostActions(post) {
        window.currentPost = post;
    },

    animateElements() {
        const detail = document.querySelector('.post-detail');
        if (detail) {
            detail.style.opacity = '0';
            detail.style.transform = 'translateY(20px)';
            setTimeout(() => {
                detail.style.transition = 'all 0.6s cubic-bezier(0.4, 0, 0.2, 1)';
                detail.style.opacity = '1';
                detail.style.transform = 'translateY(0)';
            }, 100);
        }

        const replies = document.querySelectorAll('.reply-card');
        replies.forEach((reply, index) => {
            reply.style.opacity = '0';
            reply.style.transform = 'translateX(-20px)';
            setTimeout(() => {
                reply.style.transition = 'all 0.5s cubic-bezier(0.4, 0, 0.2, 1)';
                reply.style.opacity = '1';
                reply.style.transform = 'translateX(0)';
            }, 300 + index * 100);
        });
    },

    async likePost() {
        try {
            const headers = { 'Content-Type': 'application/json' };
            if (this.token) {
                headers['Authorization'] = `Bearer ${this.token}`;
            }

            const response = await ForumApp.fetchWithTimeout(`/api/posts/${this.postId}/like`, {
                method: 'POST',
                headers
            });

            const result = await response.json();

            if (result.success) {
                const btn = document.getElementById('likeBtn');
                btn.innerHTML = `❤️ 已点赞 (${ForumApp.formatNumber(result.data.like_count)})`;
                btn.classList.add('liked');
                ForumApp.showToast('点赞成功！', 'success');
            }
        } catch (error) {
            console.error('Failed to like post:', error);
            ForumApp.showToast('点赞失败，请重试', 'error');
        }
    },

    async likeReply(replyId) {
        try {
            const headers = { 'Content-Type': 'application/json' };
            if (this.token) {
                headers['Authorization'] = `Bearer ${this.token}`;
            }

            const response = await ForumApp.fetchWithTimeout(`/api/posts/${this.postId}/replies/${replyId}/like`, {
                method: 'POST',
                headers
            });

            const result = await response.json();

            if (result.success) {
                const replyEl = document.querySelector(`#reply-${replyId} .reply-action:first-child`);
                if (replyEl) {
                    replyEl.innerHTML = `❤️ ${ForumApp.formatNumber(result.data.like_count)}`;
                }
                ForumApp.showToast('点赞成功！', 'success');
            }
        } catch (error) {
            console.error('Failed to like reply:', error);
            ForumApp.showToast('点赞失败，请重试', 'error');
        }
    },

    async deletePost() {
        if (!confirm('确定要删除这篇帖子吗？此操作不可恢复。')) {
            return;
        }

        if (!this.token) {
            ForumApp.showToast('请先登录', 'error');
            window.location.href = 'login.html';
            return;
        }

        try {
            const response = await ForumApp.fetchWithTimeout(`/api/posts/${this.postId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${this.token}`
                }
            });

            const result = await response.json();

            if (result.success) {
                ForumApp.showToast('帖子已删除', 'success');
                setTimeout(() => {
                    window.location.href = 'index.html';
                }, 1500);
            } else {
                throw new Error(result.error || '删除失败');
            }
        } catch (error) {
            console.error('Failed to delete post:', error);
            ForumApp.showToast(error.message || '删除失败，请重试', 'error');
        }
    },

    async submitReply(event) {
        event.preventDefault();

        const content = document.getElementById('replyContent').value.trim();

        if (!content) {
            ForumApp.showToast('请填写回复内容', 'error');
            return;
        }

        if (content.length < 2) {
            ForumApp.showToast('回复内容至少2个字符', 'error');
            return;
        }

        const author = this.user ? this.user.username : document.getElementById('replyAuthor').value.trim();

        if (!author && !this.user) {
            ForumApp.showToast('请填写昵称', 'error');
            return;
        }

        const submitBtn = event.target.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        const originalContent = submitBtn.innerHTML;
        submitBtn.innerHTML = '<span class="spinner" style="width:16px;height:16px;border-width:2px;"></span> 发布中...';

        try {
            const headers = { 'Content-Type': 'application/json' };
            if (this.token) {
                headers['Authorization'] = `Bearer ${this.token}`;
            }

            const body = { author, content };
            if (this.replyTo) {
                body.parent_id = this.replyTo;
            }

            const response = await ForumApp.fetchWithTimeout(`/api/posts/${this.postId}/replies`, {
                method: 'POST',
                headers,
                body: JSON.stringify(body)
            });

            const result = await response.json();

            if (result.success) {
                ForumApp.showToast(this.replyTo ? '回复发布成功！' : '评论发布成功！', 'success');
                document.getElementById('replyContent').value = '';
                this.cancelReply();
                await this.loadPost();
            } else {
                throw new Error(result.error || '发布失败');
            }
        } catch (error) {
            console.error('Failed to submit reply:', error);
            ForumApp.showToast(error.message || '网络错误，请重试', 'error');
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalContent;
        }
    },

    async editReply(replyId) {
        const replyEl = document.querySelector(`#reply-${replyId}`);
        if (!replyEl) return;

        const contentEl = replyEl.querySelector('.reply-content');
        if (!contentEl || replyEl.dataset.isDeleted === 'true') return;

        const originalContent = contentEl.innerHTML;
        const currentText = contentEl.textContent;

        contentEl.innerHTML = `
            <div class="edit-form">
                <textarea class="edit-textarea" id="editReplyContent-${replyId}">${currentText}</textarea>
                <div class="edit-actions">
                    <button class="btn btn-primary btn-sm" onclick="PostDetail.saveReplyEdit(${replyId})">保存</button>
                    <button class="btn btn-secondary btn-sm" onclick="PostDetail.cancelReplyEdit(${replyId}, '${originalContent.replace(/'/g, "\\'")}')">取消</button>
                </div>
            </div>
        `;

        const textarea = document.getElementById(`editReplyContent-${replyId}`);
        if (textarea) {
            textarea.focus();
            textarea.setSelectionRange(textarea.value.length, textarea.value.length);
        }
    },

    async saveReplyEdit(replyId) {
        const textarea = document.getElementById(`editReplyContent-${replyId}`);
        if (!textarea) return;

        const newContent = textarea.value.trim();

        if (!newContent) {
            ForumApp.showToast('回复内容不能为空', 'error');
            return;
        }

        if (newContent.length < 2) {
            ForumApp.showToast('回复内容至少2个字符', 'error');
            return;
        }

        if (!this.token) {
            ForumApp.showToast('请先登录', 'error');
            return;
        }

        try {
            const response = await ForumApp.fetchWithTimeout(`/api/posts/${this.postId}/replies/${replyId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.token}`
                },
                body: JSON.stringify({ content: newContent })
            });

            const result = await response.json();

            if (result.success) {
                ForumApp.showToast('编辑成功', 'success');
                await this.loadPost();
            } else {
                throw new Error(result.error || '编辑失败');
            }
        } catch (error) {
            console.error('Failed to edit reply:', error);
            ForumApp.showToast(error.message || '编辑失败，请重试', 'error');
        }
    },

    cancelReplyEdit(replyId, originalContent) {
        const replyEl = document.querySelector(`#reply-${replyId}`);
        if (replyEl) {
            const contentEl = replyEl.querySelector('.reply-content');
            if (contentEl) {
                contentEl.innerHTML = originalContent;
            }
        }
    },

    async deleteReply(replyId) {
        if (!confirm('确定要删除这条回复吗？此操作不可恢复。')) {
            return;
        }

        if (!this.token) {
            ForumApp.showToast('请先登录', 'error');
            window.location.href = 'login.html';
            return;
        }

        try {
            const response = await ForumApp.fetchWithTimeout(`/api/posts/${this.postId}/replies/${replyId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${this.token}`
                }
            });

            const result = await response.json();

            if (result.success) {
                ForumApp.showToast('删除成功', 'success');
                await this.loadPost();
            } else {
                throw new Error(result.error || '删除失败');
            }
        } catch (error) {
            console.error('Failed to delete reply:', error);
            ForumApp.showToast(error.message || '删除失败，请重试', 'error');
        }
    }
};

const NewPost = {
    markdownEditor: null,

    async init() {
        if (!ForumApp.user) {
            const token = localStorage.getItem('forum_token');
            if (!token) {
                window.location.href = 'login.html?redirect=new.html';
                return;
            }
        }
        this.initEditor();
        this.bindEvents();
    },

    initEditor() {
        const textarea = document.getElementById('postContent');
        if (!textarea) return;

        textarea.addEventListener('input', () => {
            this.updatePreview();
        });

        const toolbar = document.getElementById('editorToolbar');
        if (toolbar) {
            toolbar.addEventListener('click', (e) => {
                const btn = e.target.closest('button');
                if (!btn) return;

                const action = btn.dataset.action;
                this.handleEditorAction(action, textarea);
            });
        }

        this.updatePreview();
    },

    handleEditorAction(action, textarea) {
        const start = textarea.selectionStart;
        const end = textarea.selectionEnd;
        const text = textarea.value;
        const selectedText = text.substring(start, end);

        let insertion = '';
        let cursorOffset = 0;

        switch (action) {
            case 'bold':
                insertion = `**${selectedText || '粗体文本'}**`;
                cursorOffset = selectedText ? 0 : 2;
                break;
            case 'italic':
                insertion = `*${selectedText || '斜体文本'}*`;
                cursorOffset = selectedText ? 0 : 1;
                break;
            case 'heading':
                insertion = `\n### ${selectedText || '标题'}\n`;
                cursorOffset = 4;
                break;
            case 'link':
                insertion = `[${selectedText || '链接文本'}](https://)`;
                cursorOffset = selectedText ? 0 : 1;
                break;
            case 'image':
                insertion = `![${selectedText || '图片描述'}](图片URL)`;
                cursorOffset = 0;
                break;
            case 'code':
                insertion = `\`${selectedText || '代码'}\``;
                cursorOffset = selectedText ? 0 : 1;
                break;
            case 'quote':
                insertion = `\n> ${selectedText || '引用文本'}\n`;
                cursorOffset = 3;
                break;
            case 'list':
                insertion = `\n- ${selectedText || '列表项'}\n`;
                cursorOffset = 3;
                break;
            case 'upload':
                document.getElementById('imageUpload').click();
                return;
        }

        const newText = text.substring(0, start) + insertion + text.substring(end);
        textarea.value = newText;
        textarea.focus();

        const newCursorPos = start + insertion.length - cursorOffset;
        textarea.setSelectionRange(newCursorPos, newCursorPos);

        this.updatePreview();
    },

    async handleImageUpload(event) {
        const file = event.target.files[0];
        if (!file) return;

        if (!ForumApp.token) {
            ForumApp.showToast('请先登录以上传图片', 'error');
            window.location.href = 'login.html?redirect=new.html';
            return;
        }

        const formData = new FormData();
        formData.append('image', file);

        try {
            const response = await ForumApp.fetchWithTimeout('/api/upload/image', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${ForumApp.token}`
                },
                body: formData
            });

            const result = await response.json();

            if (result.success) {
                const textarea = document.getElementById('postContent');
                const cursorPos = textarea.selectionStart;
                const text = textarea.value;
                const insertion = `\n![图片](${result.data.url})\n`;
                textarea.value = text.substring(0, cursorPos) + insertion + text.substring(cursorPos);
                this.updatePreview();
                ForumApp.showToast('图片上传成功', 'success');
            } else {
                throw new Error(result.error || '上传失败');
            }
        } catch (error) {
            console.error('Upload failed:', error);
            ForumApp.showToast(error.message || '图片上传失败', 'error');
        }

        event.target.value = '';
    },

    updatePreview() {
        const textarea = document.getElementById('postContent');
        const preview = document.getElementById('contentPreview');
        if (!textarea || !preview) return;

        const text = textarea.value;
        const html = this.markdownToHtml(text);
        preview.innerHTML = html;
    },

    markdownToHtml(text) {
        let html = ForumApp.escapeHtml(text);

        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
        html = html.replace(/`(.*?)`/g, '<code>$1</code>');
        html = html.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');

        html = html.replace(/### (.*?)/g, '<h3>$1</h3>');
        html = html.replace(/## (.*?)/g, '<h2>$1</h2>');
        html = html.replace(/# (.*?)/g, '<h1>$1</h1>');

        html = html.replace(/!\[(.*?)\]\((.*?)\)/g, '<img src="$2" alt="$1" style="max-width:100%;border-radius:8px;margin:8px 0;">');
        html = html.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank" style="color:var(--primary);">$1</a>');

        html = html.replace(/^> (.*?)/gm, '<blockquote>$1</blockquote>');
        html = html.replace(/^- (.*?)/gm, '<li>$1</li>');

        html = html.replace(/\n/g, '<br>');

        return html || '<p style="color:var(--text-muted);">预览区域...</p>';
    },

    bindEvents() {
        const form = document.getElementById('newPostForm');
        if (form) {
            form.addEventListener('submit', (e) => this.submitPost(e));
        }

        const imageUpload = document.getElementById('imageUpload');
        if (imageUpload) {
            imageUpload.addEventListener('change', (e) => this.handleImageUpload(e));
        }
    },

    async submitPost(event) {
        event.preventDefault();

        const title = document.getElementById('postTitle').value.trim();
        const content = document.getElementById('postContent').value.trim();
        const category = document.getElementById('postCategory').value;

        if (!title || title.length < 2) {
            ForumApp.showToast('标题不能少于2个字符', 'error');
            return;
        }

        if (!content || content.length < 10) {
            ForumApp.showToast('内容不能少于10个字符', 'error');
            return;
        }

        const submitBtn = document.getElementById('submitBtn');
        submitBtn.disabled = true;
        const originalContent = submitBtn.innerHTML;
        submitBtn.innerHTML = '<span class="spinner" style="width:16px;height:16px;border-width:2px;"></span> 发布中...';

        try {
            const headers = { 'Content-Type': 'application/json' };
            if (ForumApp.token) {
                headers['Authorization'] = `Bearer ${ForumApp.token}`;
            }

            const response = await ForumApp.fetchWithTimeout('/api/posts', {
                method: 'POST',
                headers,
                body: JSON.stringify({ title, content, category })
            });

            const result = await response.json();

            if (result.success) {
                ForumApp.showToast('帖子发布成功！', 'success');
                setTimeout(() => {
                    window.location.href = `post.html?id=${result.data.post_id}`;
                }, 1500);
            } else {
                throw new Error(result.error || '发布失败');
            }
        } catch (error) {
            console.error('Failed to create post:', error);
            ForumApp.showToast(error.message || '网络错误，请重试', 'error');
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalContent;
        }
    }
};

function handleSearch(event) {
    if (event.key === 'Enter') {
        const keyword = event.target.value.trim();
        if (keyword.length >= 2) {
            window.location.href = `index.html?search=${encodeURIComponent(keyword)}`;
        } else if (keyword.length > 0) {
            ForumApp.showToast('搜索关键词至少2个字符', 'error');
        }
    }
}

function sharePost() {
    const url = window.location.href;
    if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(url).then(() => {
            ForumApp.showToast('链接已复制到剪贴板', 'success');
        }).catch(err => {
            console.error('Failed to copy:', err);
            fallbackCopy(url);
        });
    } else {
        fallbackCopy(url);
    }
}

function fallbackCopy(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.left = '-9999px';
    document.body.appendChild(textArea);
    textArea.select();
    try {
        document.execCommand('copy');
        ForumApp.showToast('链接已复制到剪贴板', 'success');
    } catch (err) {
        console.error('Fallback copy failed:', err);
        ForumApp.showToast('请手动复制链接', 'error');
    }
    document.body.removeChild(textArea);
}

function showToast(message, type = 'info') {
    ForumApp.showToast(message, type);
}

const App = {
    init() {
        console.log('Forum App initialized');

        if (ForumApp.socket) {
            ForumApp.socket.on('new_post', (data) => {
                ForumApp.showToast(`新帖子: ${data.post.title.substring(0, 20)}...`, 'info');
            });
        }

        document.addEventListener('visibilitychange', () => {
            if (!document.hidden && navigator.onLine) {
                if (window.ForumApp && ForumApp.currentPage) {
                    ForumApp.loadPosts();
                }
            }
        });
    }
};
