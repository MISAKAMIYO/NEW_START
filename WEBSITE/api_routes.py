import sys
import os
import json
import time
import uuid
import random
import string
import hashlib
import threading
import re
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, jsonify, request, send_from_directory, Response
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY'] = 'RAILGUN_PRO_SECRET_KEY_V2'
app.config['JSON_SORT_KEYS'] = False

VERSION = "2.5.0"
START_TIME = datetime.now()

def get_uptime():
    uptime = datetime.now() - START_TIME
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Data')
os.makedirs(DATA_DIR, exist_ok=True)

USERS_FILE = os.path.join(DATA_DIR, 'users.json')
LOGS_FILE = os.path.join(DATA_DIR, 'admin_logs.json')

def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def load_logs():
    if os.path.exists(LOGS_FILE):
        try:
            with open(LOGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_logs(logs):
    with open(LOGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(logs[-1000:], f, ensure_ascii=False, indent=2)

def add_log(user, action, details, log_type='info'):
    logs = load_logs()
    logs.append({
        'timestamp': datetime.now().isoformat(),
        'user': user,
        'action': action,
        'details': details,
        'type': log_type,
        'ip': request.remote_addr if request else 'unknown'
    })
    save_logs(logs)

DEFAULT_ADMIN = {
    'admin': {
        'id': 'admin',
        'username': 'admin',
        'password': hashlib.sha256('admin123'.encode()).hexdigest(),
        'email': 'admin@railgun.local',
        'name': '系统管理员',
        'role': 'admin',
        'status': 'active',
        'createdAt': '2026-01-01T00:00:00',
        'lastLogin': None
    }
}

def init_default_users():
    users = load_users()
    if not users:
        users = DEFAULT_ADMIN.copy()
        save_users(users)
        print("Created default admin user: admin / admin123")

init_default_users()

API_ROUTES = {}

def api_route(path):
    def decorator(f):
        API_ROUTES[path] = f.__name__
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                response = f(*args, **kwargs)
                if isinstance(response, dict):
                    return jsonify({
                        "success": True,
                        "data": response,
                        "timestamp": datetime.now().isoformat()
                    })
                return response
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "timestamp": datetime.now().isoformat()
                }), 500
        return wrapper
    return decorator

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({"success": False, "error": "未授权访问"}), 401
        
        token = auth_header[7:]
        users = load_users()
        
        for user_id, user in users.items():
            if user.get('token') == token:
                request.current_user = user
                return f(*args, **kwargs)
        
        return jsonify({"success": False, "error": "无效的令牌"}), 401
    return decorated

def require_admin(f):
    @wraps(f)
    @require_auth
    def decorated(*args, **kwargs):
        if request.current_user.get('role') != 'admin':
            return jsonify({"success": False, "error": "需要管理员权限"}), 403
        return f(*args, **kwargs)
    return decorated

def generate_token():
    return hashlib.sha256(f"{uuid.uuid4()}{time.time()}".encode()).hexdigest()

def init_api_routes():
    @app.route('/')
    def index():
        return send_from_directory(os.path.dirname(__file__), 'index.html')

    @app.route('/index.html')
    def index_html():
        return send_from_directory(os.path.dirname(__file__), 'index.html')

    @app.route('/tools.html')
    def tools_html():
        return send_from_directory(os.path.dirname(__file__), 'tools.html')

    @app.route('/admin.html')
    def admin_html():
        return send_from_directory(os.path.dirname(__file__), 'admin.html')

    @app.route('/css/<path:path>')
    def css_files(path):
        return send_from_directory(os.path.join(os.path.dirname(__file__), 'css'), path)

    @app.route('/js/<path:path>')
    def js_files(path):
        return send_from_directory(os.path.join(os.path.dirname(__file__), 'js'), path)

    @app.route('/api/status', methods=['GET'])
    @api_route('/api/status')
    def api_status():
        return {
            "version": VERSION,
            "uptime": get_uptime(),
            "status": "running",
            "services": {
                "music_player": "ready",
                "ai_chat": "ready",
                "downloader": "ready",
                "macro": "disabled",
                "screen_pen": "disabled"
            },
            "platform": "windows",
            "architecture": "x64"
        }

    @app.route('/api/routes', methods=['GET'])
    @api_route('/api/routes')
    def list_routes():
        routes = []
        for rule in app.url_map.iter_rules():
            if rule.endpoint != 'static' and not rule.rule.startswith('/api/') and rule.rule != '/':
                methods = ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'})) if rule.methods else ''
                routes.append({
                    "path": rule.rule,
                    "methods": methods,
                    "endpoint": rule.endpoint
                })
        return {"routes": routes}

    @app.route('/api/auth/register', methods=['POST'])
    @api_route('/api/auth/register')
    def auth_register():
        data = request.json or {}
        
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        name = data.get('name', username)
        
        if not username or not email or not password:
            raise Exception("请填写完整信息")
        
        if len(password) < 6:
            raise Exception("密码长度至少6位")
        
        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            raise Exception("用户名只能包含字母、数字和下划线")
        
        users = load_users()
        
        for user in users.values():
            if user.get('username') == username:
                raise Exception("用户名已存在")
            if user.get('email') == email:
                raise Exception("邮箱已被注册")
        
        user_id = f"u{uid.uuid4().hex[:8]}"
        
        users[user_id] = {
            'id': user_id,
            'username': username,
            'password': hashlib.sha256(password.encode()).hexdigest(),
            'email': email,
            'name': name,
            'role': 'user',
            'status': 'active',
            'createdAt': datetime.now().isoformat(),
            'lastLogin': None,
            'token': None
        }
        
        save_users(users)
        add_log(username, 'register', f'新用户注册: {username}', 'success')
        
        return {
            "success": True,
            "message": "注册成功",
            "user": {
                "id": user_id,
                "username": username,
                "email": email,
                "name": name,
                "role": "user"
            }
        }

    @app.route('/api/auth/login', methods=['POST'])
    @api_route('/api/auth/login')
    def auth_login():
        data = request.json or {}
        
        username = data.get('username', '').strip()
        password = data.get('password', '')
        role = data.get('role', 'user')
        
        if not username or not password:
            raise Exception("请填写用户名和密码")
        
        users = load_users()
        
        user = None
        for u in users.values():
            if u.get('username') == username or u.get('email') == username:
                user = u
                break
        
        if not user:
            raise Exception("用户不存在")
        
        if user.get('password') != hashlib.sha256(password.encode()).hexdigest():
            add_log(username, 'login_failed', '密码错误', 'error')
            raise Exception("密码错误")
        
        if user.get('status') != 'active':
            add_log(username, 'login_failed', '账户已被禁用', 'error')
            raise Exception("账户已被禁用")
        
        if role == 'admin' and user.get('role') != 'admin':
            raise Exception("您不是管理员")
        
        token = generate_token()
        user['token'] = token
        user['lastLogin'] = datetime.now().isoformat()
        
        for i, u in users.items():
            if u['id'] == user['id']:
                users[i] = user
                break
        save_users(users)
        
        add_log(username, 'login', '用户登录成功', 'success')
        
        return {
            "success": True,
            "message": "登录成功",
            "user": {
                "id": user['id'],
                "username": user['username'],
                "email": user['email'],
                "name": user['name'],
                "role": user['role'],
                "token": token
            }
        }

    @app.route('/api/auth/logout', methods=['POST'])
    @api_route('/api/auth/logout')
    @require_auth
    def auth_logout():
        user = request.current_user
        
        users = load_users()
        for i, u in users.items():
            if u['id'] == user['id']:
                u['token'] = None
                users[i] = u
                break
        save_users(users)
        
        add_log(user.get('username', 'unknown'), 'logout', '用户退出登录', 'info')
        
        return {"success": True, "message": "退出成功"}

    @app.route('/api/auth/profile', methods=['GET'])
    @api_route('/api/auth/profile')
    @require_auth
    def auth_profile():
        user = request.current_user
        return {
            "user": {
                "id": user['id'],
                "username": user['username'],
                "email": user['email'],
                "name": user['name'],
                "role": user['role'],
                "status": user['status'],
                "createdAt": user['createdAt'],
                "lastLogin": user['lastLogin']
            }
        }

    @app.route('/api/auth/profile', methods=['PUT'])
    @api_route('/api/auth/profile')
    @require_auth
    def auth_update_profile():
        data = request.json or {}
        user = request.current_user
        
        name = data.get('name', user.get('name'))
        email = data.get('email', user.get('email'))
        
        users = load_users()
        
        for u in users.values():
            if u.get('email') == email and u['id'] != user['id']:
                raise Exception("邮箱已被使用")
        
        for i, u in users.items():
            if u['id'] == user['id']:
                u['name'] = name
                u['email'] = email
                users[i] = u
                break
        save_users(users)
        
        add_log(user.get('username'), 'update_profile', '更新个人资料', 'info')
        
        return {
            "success": True,
            "message": "资料已更新",
            "user": {
                "id": user['id'],
                "username": user['username'],
                "email": email,
                "name": name,
                "role": user['role']
            }
        }

    @app.route('/api/auth/password', methods=['POST'])
    @api_route('/api/auth/password')
    @require_auth
    def auth_change_password():
        data = request.json or {}
        old_password = data.get('oldPassword', '')
        new_password = data.get('newPassword', '')
        
        if not old_password or not new_password:
            raise Exception("请填写新旧密码")
        
        if len(new_password) < 6:
            raise Exception("新密码长度至少6位")
        
        user = request.current_user
        
        if user.get('password') != hashlib.sha256(old_password.encode()).hexdigest():
            add_log(user.get('username'), 'password_change_failed', '原密码错误', 'error')
            raise Exception("原密码错误")
        
        users = load_users()
        for i, u in users.items():
            if u['id'] == user['id']:
                u['password'] = hashlib.sha256(new_password.encode()).hexdigest()
                users[i] = u
                break
        save_users(users)
        
        add_log(user.get('username'), 'password_changed', '修改密码成功', 'success')
        
        return {"success": True, "message": "密码已修改"}

    @app.route('/api/admin/stats', methods=['GET'])
    @api_route('/api/admin/stats')
    @require_admin
    def admin_stats():
        users = load_users()
        
        active_users = sum(1 for u in users.values() if u.get('status') == 'active')
        
        return {
            "users": len(users),
            "active_users": active_users,
            "downloads": 56700 + random.randint(-1000, 1000),
            "aiConversations": 89200 + random.randint(-1000, 1000),
            "videoDownloads": 12300 + random.randint(-500, 500)
        }

    @app.route('/api/admin/users', methods=['GET'])
    @api_route('/api/admin/users')
    @require_admin
    def admin_users():
        users = load_users()
        
        user_list = []
        for u in users.values():
            user_list.append({
                "id": u['id'],
                "username": u['username'],
                "email": u['email'],
                "name": u['name'],
                "role": u['role'],
                "status": u['status'],
                "createdAt": u['createdAt'],
                "lastLogin": u['lastLogin']
            })
        
        return {"users": user_list, "count": len(user_list)}

    @app.route('/api/admin/users', methods=['POST'])
    @api_route('/api/admin/users')
    @require_admin
    def admin_create_user():
        data = request.json or {}
        
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        role = data.get('role', 'user')
        name = data.get('name', username)
        
        if not username or not email or not password:
            raise Exception("请填写完整信息")
        
        users = load_users()
        
        for u in users.values():
            if u.get('username') == username:
                raise Exception("用户名已存在")
        
        user_id = f"u{uuid.uuid4().hex[:8]}"
        
        users[user_id] = {
            'id': user_id,
            'username': username,
            'password': hashlib.sha256(password.encode()).hexdigest(),
            'email': email,
            'name': name,
            'role': role,
            'status': 'active',
            'createdAt': datetime.now().isoformat(),
            'lastLogin': None,
            'token': None
        }
        
        save_users(users)
        
        add_log(request.current_user.get('username'), 'create_user', f'创建用户: {username}', 'success')
        
        return {
            "success": True,
            "message": "用户已创建",
            "user": {
                "id": user_id,
                "username": username,
                "email": email,
                "name": name,
                "role": role
            }
        }

    @app.route('/api/admin/users/<user_id>', methods=['PUT'])
    @api_route('/api/admin/users/<user_id>')
    @require_admin
    def admin_update_user(user_id):
        data = request.json or {}
        users = load_users()
        
        if user_id not in users:
            raise Exception("用户不存在")
        
        if user_id == request.current_user['id']:
            raise Exception("不能修改自己的账户")
        
        users[user_id]['role'] = data.get('role', users[user_id]['role'])
        users[user_id]['status'] = data.get('status', users[user_id]['status'])
        users[user_id]['email'] = data.get('email', users[user_id]['email'])
        users[user_id]['name'] = data.get('name', users[user_id]['name'])
        
        if data.get('password'):
            users[user_id]['password'] = hashlib.sha256(data['password'].encode()).hexdigest()
        
        save_users(users)
        
        add_log(request.current_user.get('username'), 'update_user', f'更新用户: {users[user_id]["username"]}', 'success')
        
        return {"success": True, "message": "用户已更新"}

    @app.route('/api/admin/users/<user_id>', methods=['DELETE'])
    @api_route('/api/admin/users/<user_id>')
    @require_admin
    def admin_delete_user(user_id):
        users = load_users()
        
        if user_id not in users:
            raise Exception("用户不存在")
        
        if user_id == request.current_user['id']:
            raise Exception("不能删除自己的账户")
        
        username = users[user_id]['username']
        del users[user_id]
        
        save_users(users)
        
        add_log(request.current_user.get('username'), 'delete_user', f'删除用户: {username}', 'warning')
        
        return {"success": True, "message": "用户已删除"}

    @app.route('/api/admin/logs', methods=['GET'])
    @api_route('/api/admin/logs')
    @require_admin
    def admin_logs():
        logs = load_logs()
        
        log_type = request.args.get('type')
        if log_type:
            logs = [l for l in logs if l.get('type') == log_type]
        
        return {"logs": logs[-100:], "count": len(logs[-100:])}

    @app.route('/api/admin/analytics', methods=['GET'])
    @api_route('/api/admin/analytics')
    @require_admin
    def admin_analytics():
        days = int(request.args.get('days', 7))
        
        data = []
        for i in range(days):
            date = datetime.now() - timedelta(days=days - i - 1)
            data.append({
                "date": date.strftime('%Y-%m-%d'),
                "users": random.randint(50, 200),
                "downloads": random.randint(100, 500),
                "conversations": random.randint(200, 800)
            })
        
        return {"data": data, "days": days}

    @app.route('/api/admin/system', methods=['GET'])
    @api_route('/api/admin/system')
    @require_admin
    def admin_system():
        import platform
        return {
            "platform": platform.system(),
            "python_version": platform.python_version(),
            "version": VERSION,
            "uptime": get_uptime(),
            "memory": f"{random.randint(30, 60)}%",
            "cpu": f"{random.randint(20, 50)}%"
        }

    @app.route('/api/admin/config', methods=['GET'])
    @api_route('/api/admin/config')
    @require_admin
    def admin_get_config():
        return {
            "config": {
                "site_name": "RAILGUN",
                "allow_registration": True,
                "ai_enabled": True,
                "download_enabled": True,
                "macro_enabled": False
            }
        }

    @app.route('/api/admin/config', methods=['POST'])
    @api_route('/api/admin/config')
    @require_admin
    def admin_update_config():
        data = request.json or {}
        
        add_log(request.current_user.get('username'), 'update_config', '更新系统配置', 'success')
        
        return {"success": True, "message": "配置已更新"}

    @app.route('/api/music/status', methods=['GET'])
    @api_route('/api/music/status')
    def music_status():
        return {
            "playing": False,
            "current": None,
            "progress": 0,
            "volume": 80,
            "mode": "list",
            "playlist": []
        }

    @app.route('/api/music/play', methods=['POST'])
    @api_route('/api/music/play')
    def music_play():
        return {"playing": True, "message": "播放命令已发送"}

    @app.route('/api/music/pause', methods=['POST'])
    @api_route('/api/music/pause')
    def music_pause():
        return {"playing": False, "message": "暂停命令已发送"}

    @app.route('/api/music/stop', methods=['POST'])
    @api_route('/api/music/stop')
    def music_stop():
        return {"playing": False, "message": "停止命令已发送"}

    @app.route('/api/music/next', methods=['POST'])
    @api_route('/api/music/next')
    def music_next():
        return {"message": "下一首命令已发送"}

    @app.route('/api/music/previous', methods=['POST'])
    @api_route('/api/music/previous')
    def music_previous():
        return {"message": "上一首命令已发送"}

    @app.route('/api/music/volume', methods=['POST'])
    @api_route('/api/music/volume')
    def music_volume():
        data = request.json or {}
        volume = data.get('volume', 80)
        return {"volume": volume, "message": f"音量设置为 {volume}"}

    @app.route('/api/music/seek', methods=['POST'])
    @api_route('/api/music/seek')
    def music_seek():
        data = request.json or {}
        position = data.get('position', 0)
        return {"Position": position, "message": f"跳转至 {position}秒"}

    @app.route('/api/music/mode', methods=['GET', 'POST'])
    @api_route('/api/music/mode')
    def music_mode():
        if request.method == 'POST':
            data = request.json or {}
            mode = data.get('mode', 'list')
            return {"mode": mode}
        return {"mode": "list"}

    @app.route('/api/music/playlist', methods=['GET'])
    @api_route('/api/music/playlist')
    def music_playlist():
        return {"playlist": [], "count": 0}

    @app.route('/api/music/playlist/add', methods=['POST'])
    @api_route('/api/music/playlist/add')
    def music_add_to_playlist():
        data = request.json or {}
        url = data.get('url', '')
        return {"message": "已添加到播放列表", "url": url}

    @app.route('/api/music/lyrics', methods=['GET'])
    @api_route('/api/music/lyrics')
    def music_lyrics():
        return {"lyrics": [], "current": None}

    @app.route('/api/ai/chat', methods=['POST'])
    @api_route('/api/ai/chat')
    def ai_chat():
        data = request.json or {}
        message = data.get('message', '')
        return {
            "response": f"AI 服务已准备就绪。\n\n您发送的消息: {message}\n\n(请在软件中配置 AI 密钥以使用完整功能)",
            "message": message
        }

    @app.route('/api/ai/history', methods=['GET'])
    @api_route('/api/ai/history')
    def ai_history():
        return {"history": []}

    @app.route('/api/download/platforms', methods=['GET'])
    @api_route('/api/download/platforms')
    def download_platforms():
        platforms = [
            {"name": "网易云音乐", "domains": ["music.163.com"], "icon": "🎵"},
            {"name": "QQ音乐", "domains": ["y.qq.com"], "icon": "🎶"},
            {"name": "酷狗音乐", "domains": ["kugou.com"], "icon": "🐕"},
            {"name": "Bilibili", "domains": ["bilibili.com"], "icon": "📺"},
            {"name": "抖音", "domains": ["douyin.com"], "icon": "🎵"}
        ]
        return {"platforms": platforms}

    @app.route('/api/download', methods=['POST'])
    @api_route('/api/download')
    def download_submit():
        data = request.json or {}
        url = data.get('url', '')
        format_type = data.get('format', 'default')
        if not url:
            raise Exception("请提供下载链接")
        return {
            "id": f"D{random.randint(1000,9999)}",
            "url": url,
            "format": format_type,
            "status": "pending",
            "message": "下载任务已添加"
        }

    @app.route('/api/download/queue', methods=['GET'])
    @api_route('/api/download/queue')
    def download_queue():
        return {"queue": [], "count": 0}

    @app.route('/api/random/number', methods=['POST'])
    @api_route('/api/random/number')
    def random_number():
        data = request.json or {}
        min_val = data.get('min', 1)
        max_val = data.get('max', 100)
        count = data.get('count', 1)
        
        try:
            min_val = int(min_val)
            max_val = int(max_val)
            count = min(int(count), 100)
            if min_val > max_val:
                min_val, max_val = max_val, min_val
        except ValueError:
            raise Exception("参数必须为有效数字")
        
        numbers = [random.randint(min_val, max_val) for _ in range(count)]
        
        return {"numbers": numbers, "count": len(numbers)}

    @app.route('/api/random/password', methods=['POST'])
    @api_route('/api/random/password')
    def random_password():
        data = request.json or {}
        length = min(max(data.get('length', 16), 8), 128)
        use_upper = data.get('uppercase', True)
        use_lower = data.get('lowercase', True)
        use_numbers = data.get('numbers', True)
        use_symbols = data.get('symbols', True)
        
        chars = ''
        if use_upper: chars += string.ascii_uppercase
        if use_lower: chars += string.ascii_lowercase
        if use_numbers: chars += string.digits
        if use_symbols: chars += '!@#$%^&*()_+-=[]{}|;:,.<>?'
        if not chars: chars = string.ascii_letters + string.digits
        
        password = ''.join(random.choice(chars) for _ in range(length))
        
        return {
            "password": password,
            "length": length,
            "strength": "strong" if length >= 12 and use_symbols else "medium" if length >= 8 else "weak"
        }

    @app.route('/api/random/color', methods=['GET'])
    @api_route('/api/random/color')
    def random_color():
        def random_hex():
            return ''.join(random.choices('0123456789ABCDEF', k=6))
        
        colors = []
        for _ in range(5):
            hex_color = random_hex()
            colors.append({
                "hex": f"#{hex_color}",
                "rgb": tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            })
        
        return {"colors": colors, "count": 5}

    @app.route('/api/random/uuid', methods=['POST'])
    @api_route('/api/random/uuid')
    def random_uuid():
        count = min(max(request.json.get('count', 1), 1), 100)
        uuids = [str(uuid.uuid4()) for _ in range(count)]
        return {"uuids": uuids, "count": count}

    @app.route('/api/text/convert', methods=['POST'])
    @api_route('/api/text/convert')
    def text_convert():
        data = request.json or {}
        text = data.get('text', '')
        conversion = data.get('conversion', 'uppercase')
        
        if conversion == 'uppercase': result = text.upper()
        elif conversion == 'lowercase': result = text.lower()
        elif conversion == 'capitalize': result = text.title()
        elif conversion == 'reverse': result = text[::-1]
        elif conversion == 'trim': result = text.strip()
        else: result = text
        
        return {"result": result, "conversion": conversion}

    @app.route('/api/system/info', methods=['GET'])
    @api_route('/api/system/info')
    def system_info():
        import platform
        return {
            "platform": platform.system(),
            "version": platform.version(),
            "architecture": platform.machine(),
            "python_version": platform.python_version()
        }

init_api_routes()
