import sys
import os
import json
import time
import uuid
import random
import string
import hashlib
import re
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, jsonify, request, send_from_directory, Response
from flask_cors import CORS
import base64
from urllib.parse import quote, unquote

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__)
CORS(app)

app.config['SECRET_KEY'] = 'RAILGUN_PRO_SECRET_KEY_V2'
app.config['JSON_SORT_KEYS'] = False

VERSION = "2.6.0"
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
PLAYLIST_FILE = os.path.join(DATA_DIR, 'playlist.json')

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

music_state = {
    "playing": False,
    "current_song": None,
    "volume": 70,
    "position": 0,
    "duration": 0,
    "mode": "顺序播放",
    "playlist": []
}

AI_CHAT_HISTORY = []
DOWNLOAD_QUEUE = []
download_id_counter = 0

def load_playlist():
    try:
        if os.path.exists(PLAYLIST_FILE):
            with open(PLAYLIST_FILE, 'r', encoding='utf-8') as f:
                return json.load(f).get('playlist', [])
    except:
        pass
    return []

def save_playlist(playlist):
    try:
        with open(PLAYLIST_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                "version": "1.0",
                "playlist": playlist,
                "updated": datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False

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

    @app.route('/about.html')
    def about_html():
        return send_from_directory(os.path.dirname(__file__), 'about.html')

    @app.route('/contact.html')
    def contact_html():
        return send_from_directory(os.path.dirname(__file__), 'contact.html')

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
                "macro": "disabled"
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
            'id': user_id, 'username': username,
            'password': hashlib.sha256(password.encode()).hexdigest(),
            'email': email, 'name': name,
            'role': 'user', 'status': 'active',
            'createdAt': datetime.now().isoformat(),
            'lastLogin': None, 'token': None
        }
        save_users(users)
        add_log(username, 'register', f'新用户注册: {username}', 'success')
        
        return {"success": True, "message": "注册成功", "user": {
            "id": user_id, "username": username,
            "email": email, "name": name, "role": "user"
        }}

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
        
        return {"success": True, "message": "登录成功", "user": {
            "id": user['id'], "username": user['username'],
            "email": user['email'], "name": user['name'],
            "role": user['role'], "token": token
        }}

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
        return {"user": {
            "id": user['id'], "username": user['username'],
            "email": user['email'], "name": user['name'],
            "role": user['role'], "status": user['status'],
            "createdAt": user['createdAt'], "lastLogin": user['lastLogin']
        }}

    @app.route('/api/admin/stats', methods=['GET'])
    @api_route('/api/admin/stats')
    @require_admin
    def admin_stats():
        users = load_users()
        return {
            "users": len(users),
            "active_users": sum(1 for u in users.values() if u.get('status') == 'active'),
            "downloads": 56700 + random.randint(-1000, 1000),
            "aiConversations": 89200 + random.randint(-1000, 1000)
        }

    @app.route('/api/admin/users', methods=['GET'])
    @api_route('/api/admin/users')
    @require_admin
    def admin_users():
        users = load_users()
        user_list = []
        for u in users.values():
            user_list.append({
                "id": u['id'], "username": u['username'],
                "email": u['email'], "name": u['name'],
                "role": u['role'], "status": u['status'],
                "createdAt": u['createdAt'], "lastLogin": u['lastLogin']
            })
        return {"users": user_list, "count": len(user_list)}

    @app.route('/api/music/status', methods=['GET'])
    @api_route('/api/music/status')
    def music_status():
        return {
            "playing": music_state["playing"],
            "current_song": music_state["current_song"],
            "volume": music_state["volume"],
            "position": music_state["position"],
            "duration": music_state["duration"],
            "mode": music_state["mode"],
            "playlist_count": len(music_state["playlist"])
        }

    @app.route('/api/music/play', methods=['POST'])
    @api_route('/api/music/play')
    def music_play():
        music_state["playing"] = True
        return {"status": "playing", "current_song": music_state["current_song"]}

    @app.route('/api/music/pause', methods=['POST'])
    @api_route('/api/music/pause')
    def music_pause():
        music_state["playing"] = False
        return {"status": "paused", "current_song": music_state["current_song"]}

    @app.route('/api/music/stop', methods=['POST'])
    @api_route('/api/music/stop')
    def music_stop():
        music_state["playing"] = False
        music_state["current_song"] = None
        music_state["position"] = 0
        return {"status": "stopped"}

    @app.route('/api/music/next', methods=['POST'])
    @api_route('/api/music/next')
    def music_next():
        if not music_state["playlist"]:
            return {"status": "no_playlist"}
        if music_state["current_song"]:
            current_idx = -1
            for i, song in enumerate(music_state["playlist"]):
                if song.get('id') == music_state["current_song"].get('id'):
                    current_idx = i
                    break
            if music_state["mode"] == "随机播放":
                next_idx = random.randint(0, len(music_state["playlist"]) - 1)
            else:
                next_idx = (current_idx + 1) % len(music_state["playlist"])
            music_state["current_song"] = music_state["playlist"][next_idx]
        else:
            music_state["current_song"] = music_state["playlist"][0] if music_state["playlist"] else None
        music_state["position"] = 0
        music_state["playing"] = True
        return {"status": "playing", "current_song": music_state["current_song"]}

    @app.route('/api/music/volume', methods=['POST'])
    @api_route('/api/music/volume')
    def music_volume():
        data = request.json or {}
        volume = data.get('volume', 70)
        music_state["volume"] = max(0, min(100, volume))
        return {"volume": music_state["volume"]}

    @app.route('/api/music/mode', methods=['GET', 'POST'])
    @api_route('/api/music/mode')
    def music_mode():
        if request.method == 'POST':
            data = request.json or {}
            mode = data.get('mode', '顺序播放')
            valid_modes = ['顺序播放', '随机播放', '单曲循环', '列表循环']
            music_state["mode"] = mode if mode in valid_modes else '顺序播放'
        return {"mode": music_state["mode"]}

    @app.route('/api/music/playlist', methods=['GET'])
    @api_route('/api/music/playlist')
    def get_playlist():
        playlist = load_playlist()
        music_state["playlist"] = playlist
        return {"playlist": playlist, "count": len(playlist), "current_song": music_state["current_song"]}

    @app.route('/api/music/lyrics', methods=['GET'])
    @api_route('/api/music/lyrics')
    def get_lyrics():
        return {"lyrics": music_state["current_song"].get('lyrics', []) if music_state["current_song"] else [], "song": music_state["current_song"]}

    @app.route('/api/ai/chat', methods=['POST'])
    @api_route('/api/ai/chat')
    def ai_chat():
        global AI_CHAT_HISTORY
        data = request.json or {}
        message = data.get('message', '').strip()
        
        if not message:
            raise Exception("消息内容不能为空")
        
        if len(AI_CHAT_HISTORY) > 10:
            AI_CHAT_HISTORY = AI_CHAT_HISTORY[-10:]
        
        AI_CHAT_HISTORY.append({"role": "user", "content": message})
        
        responses = [
            f"收到你的问题：「{message}」。这是一个很好的话题！",
            f"关于「{message}」，我认为最重要的是明确目标，然后逐步实现。",
            f"很有趣的话题！这让我想到了几个要点。",
            f"针对「{message}」，让我从多个角度来分析。"
        ]
        
        response_text = random.choice(responses)
        AI_CHAT_HISTORY.append({"role": "assistant", "content": response_text})
        
        return {"response": response_text, "message": message}

    @app.route('/api/download/platforms', methods=['GET'])
    @api_route('/api/download/platforms')
    def get_platforms():
        return {"platforms": [
            {"name": "Bilibili", "domains": ["bilibili.com"], "icon": "📺"},
            {"name": "YouTube", "domains": ["youtube.com"], "icon": "▶️"},
            {"name": "抖音", "domains": ["douyin.com"], "icon": "🎵"},
            {"name": "小红书", "domains": ["xiaohongshu.com"], "icon": "📕"}
        ]}

    @app.route('/api/download', methods=['POST'])
    @api_route('/api/download')
    def submit_download():
        global download_id_counter, DOWNLOAD_QUEUE
        data = request.json or {}
        url = data.get('url', '').strip()
        
        if not url:
            raise Exception("请提供下载链接")
        
        download_id_counter += 1
        task = {
            "id": f"D{download_id_counter:04d}",
            "url": url,
            "status": "pending",
            "progress": 0,
            "created_at": datetime.now().isoformat()
        }
        DOWNLOAD_QUEUE.insert(0, task)
        DOWNLOAD_QUEUE[:50] = DOWNLOAD_QUEUE[:50]
        return {"status": "queued", "task_id": task["id"], "queue_position": DOWNLOAD_QUEUE.index(task) + 1}

    @app.route('/api/download/queue', methods=['GET'])
    @api_route('/api/download/queue')
    def get_download_queue():
        return {"queue": DOWNLOAD_QUEUE[:20], "total": len(DOWNLOAD_QUEUE)}

    @app.route('/api/random/number', methods=['POST'])
    @api_route('/api/random/number')
    def random_number():
        data = request.json or {}
        min_val = data.get('min', 1)
        max_val = data.get('max', 100)
        count = min(max(data.get('count', 1), 1), 1000)
        numbers = [random.randint(min_val, max_val) for _ in range(count)]
        return {"numbers": numbers, "count": len(numbers)}

    @app.route('/api/random/password', methods=['POST'])
    @api_route('/api/random/password')
    def random_password():
        data = request.json or {}
        length = min(max(data.get('length', 16), 8, 128)
        chars = ''
        if data.get('uppercase', True): chars += string.ascii_uppercase
        if data.get('lowercase', True): chars += string.ascii_lowercase
        if data.get('numbers', True): chars += string.digits
        if data.get('symbols', True): chars += '!@#$%^&*()_+-=[]{}|;:,.<>?'
        if not chars: chars = string.ascii_letters + string.digits
        password = ''.join(random.choice(chars) for _ in range(length))
        return {"password": password, "length": length, "strength": "strong" if length >= 12 else "medium"}

    @app.route('/api/random/color', methods=['GET'])
    @api_route('/api/random/color')
    def random_color():
        colors = []
        for _ in range(5):
            hex_color = '#{:06x}'.format(random.randint(0, 0xFFFFFF))
            rgb = tuple(int(hex_color[i:i+2], 16) for i in (1, 3, 5))
            colors.append({"hex": hex_color, "rgb": f"rgb{rgb}"})
        return {"colors": colors, "count": 5}

    @app.route('/api/random/uuid', methods=['POST'])
    @api_route('/api/random/uuid')
    def random_uuid():
        count = min(max(request.json.get('count', 1), 1), 100)
        return {"uuids": [str(uuid.uuid4()) for _ in range(count)], "count": count}

    @app.route('/api/text/convert', methods=['POST'])
    @api_route('/api/text/convert')
    def text_convert():
        data = request.json or {}
        text = data.get('text', '')
        conversion = data.get('conversion', 'uppercase')
        
        conversions = {
            'uppercase': lambda t: t.upper(),
            'lowercase': lambda t: t.lower(),
            'titlecase': lambda t: t.title(),
            'capitalize': lambda t: t.capitalize(),
            'reverse': lambda t: t[::-1],
            'strip': lambda t: t.strip(),
            'base64_encode': lambda t: base64.b64encode(t.encode()).decode(),
            'base64_decode': lambda t: base64.b64decode(t.encode()).decode(),
            'url_encode': lambda t: quote(t),
            'url_decode': lambda t: unquote(t),
            'md5': lambda t: hashlib.md5(t.encode()).hexdigest(),
            'sha256': lambda t: hashlib.sha256(t.encode()).hexdigest()
        }
        
        try:
            result = conversions.get(conversion, lambda t: t)(text)
        except Exception as e:
            raise Exception(f"转换失败: {e}")
        
        return {"result": result, "conversion": conversion}

    @app.route('/api/calculator/calculate', methods=['POST'])
    @api_route('/api/calculator/calculate')
    def calculator():
        data = request.json or {}
        expression = data.get('expression', '').strip()
        
        try:
            sanitized = re.sub(r'[^0-9+\-*/().\s]', '', expression)
            result = eval(sanitized) if sanitized else 0
            return {"result": str(result), "expression": expression}
        except:
            return {"error": "无效的表达式", "expression": expression}

    @app.route('/api/qrcode/generate', methods=['POST'])
    @api_route('/api/qrcode/generate')
    def generate_qrcode():
        data = request.json or {}
        text = data.get('text', '')
        size = min(max(data.get('size', 200), 100, 500)
        
        try:
            import qrcode
            qr = qrcode.QRCode(box_size=10, border=2)
            qr.add_data(text)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            import io
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            return {"image": f"data:image/png;base64,{img_str}", "size": size}
        except ImportError:
            return {"error": "二维码生成需要 qrcode 库", "text": text}

    @app.route('/api/timestamp/now', methods=['GET'])
    @api_route('/api/timestamp/now')
    def timestamp_now():
        now = datetime.now()
        return {
            "timestamp": int(now.timestamp()),
            "datetime": now.strftime('%Y-%m-%d %H:%M:%S'),
            "iso": now.isoformat(),
            "unix": int(now.timestamp())
        }

    @app.route('/api/timestamp/convert', methods=['POST'])
    @api_route('/api/timestamp/convert')
    def timestamp_convert():
        data = request.json or {}
        timestamp = data.get('timestamp')
        datetime_str = data.get('datetime')
        
        if timestamp:
            try:
                dt = datetime.fromtimestamp(int(timestamp))
                return {
                    "timestamp": int(timestamp),
                    "datetime": dt.strftime('%Y-%m-%d %H:%M:%S'),
                    "date": dt.strftime('%Y-%m-%d'),
                    "time": dt.strftime('%H:%M:%S'),
                    "iso": dt.isoformat()
                }
            except:
                raise Exception("无效的时间戳")
        
        if datetime_str:
            try:
                dt = datetime.fromisoformat(datetime_str.replace(' ', 'T'))
                return {
                    "timestamp": int(dt.timestamp()),
                    "datetime": dt.strftime('%Y-%m-%d %H:%M:%S'),
                    "date": dt.strftime('%Y-%m-%d'),
                    "time": dt.strftime('%H:%M:%S'),
                    "iso": dt.isoformat()
                }
            except:
                try:
                    dt = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
                    return {
                        "timestamp": int(dt.timestamp()),
                        "datetime": dt.strftime('%Y-%m-%d %H:%M:%S'),
                        "date": dt.strftime('%Y-%m-%d'),
                        "time": dt.strftime('%H:%M:%S'),
                        "iso": dt.isoformat()
                    }
                except:
                    raise Exception("无效的日期时间格式")
        
        raise Exception("请提供时间戳或日期时间")

    @app.route('/api/password/strength', methods=['POST'])
    @api_route('/api/password/strength')
    def password_strength():
        data = request.json or {}
        password = data.get('password', '')
        
        if not password:
            raise Exception("请输入密码")
        
        score = 0
        feedback = []
        
        if len(password) >= 8:
            score += 1
        else:
            feedback.append("密码长度至少8位")
        
        if len(password) >= 12:
            score += 1
        
        if any(c.isupper() for c in password):
            score += 1
        else:
            feedback.append("建议添加大写字母")
        
        if any(c.islower() for c in password):
            score += 1
        else:
            feedback.append("建议添加小写字母")
        
        if any(c.isdigit() for c in password):
            score += 1
        else:
            feedback.append("建议添加数字")
        
        special_chars = '!@#$%^&*()_+-=[]{}|;:,.<>?'
        if any(c in special_chars for c in password):
            score += 1
        else:
            feedback.append("建议添加特殊字符")
        
        if password.lower() in ['password', '123456', 'qwerty', 'admin']:
            score = 0
            feedback = ["密码太常见，请使用更复杂的密码"]
        
        strength = "weak" if score <= 2 else "medium" if score <= 4 else "strong"
        
        return {
            "score": score,
            "max_score": 6,
            "strength": strength,
            "length": len(password),
            "feedback": feedback if feedback else ["密码强度良好"]
        }

    @app.route('/api/json/format', methods=['POST'])
    @api_route('/api/json/format')
    def json_format():
        data = request.json or {}
        json_str = data.get('json', '')
        minify = data.get('minify', False)
        
        if not json_str:
            raise Exception("请输入JSON字符串")
        
        try:
            parsed = json.loads(json_str)
            if minify:
                result = json.dumps(parsed, separators=(',', ':'))
            else:
                result = json.dumps(parsed, ensure_ascii=False, indent=2)
            return {
                "result": result,
                "valid": True,
                "size": len(result),
                "keys_count": len(parsed) if isinstance(parsed, dict) else 0
            }
        except json.JSONDecodeError as e:
            raise Exception(f"JSON格式错误: {e}")

    @app.route('/api/json/validate', methods=['POST'])
    @api_route('/api/json/validate')
    def json_validate():
        data = request.json or {}
        json_str = data.get('json', '')
        
        if not json_str:
            raise Exception("请输入JSON字符串")
        
        try:
            parsed = json.loads(json_str)
            return {
                "valid": True,
                "type": type(parsed).__name__,
                "keys_count": len(parsed) if isinstance(parsed, dict) else len(parsed) if isinstance(parsed, list) else 0
            }
        except json.JSONDecodeError as e:
            return {
                "valid": False,
                "error": str(e),
                "position": e.pos if hasattr(e, 'pos') else 0
            }

    @app.route('/api/unit/convert', methods=['POST'])
    @api_route('/api/unit/convert')
    def unit_convert():
        data = request.json or {}
        value = float(data.get('value', 0))
        from_unit = data.get('from', '').lower()
        to_unit = data.get('to', '').lower()
        
        conversions = {
            ('m', 'km'): 0.001,
            ('km', 'm'): 1000,
            ('m', 'cm'): 100,
            ('cm', 'm'): 0.01,
            ('km', 'cm'): 100000,
            ('cm', 'km'): 0.00001,
            ('kg', 'g'): 1000,
            ('g', 'kg'): 0.001,
            ('kg', 'lb'): 2.20462,
            ('lb', 'kg'): 0.453592,
            ('g', 'mg'): 1000,
            ('mg', 'g'): 0.001,
            ('s', 'ms'): 1000,
            ('ms', 's'): 0.001,
            ('s', 'min'): 1/60,
            ('min', 's'): 60,
            ('min', 'h'): 1/60,
            ('h', 'min'): 60,
            ('C', 'F'): lambda c: c * 9/5 + 32,
            ('F', 'C'): lambda f: (f - 32) * 5/9,
            ('C', 'K'): lambda c: c + 273.15,
            ('K', 'C'): lambda k: k - 273.15,
            ('px', 'pt'): 0.75,
            ('pt', 'px'): 1.33333,
            ('px', 'em'): 0.0625,
            ('em', 'px'): 16,
            ('inch', 'cm'): 2.54,
            ('cm', 'inch'): 0.393701
        }
        
        key = (from_unit, to_unit)
        if key in conversions:
            if callable(conversions[key]):
                result = conversions[key](value)
            else:
                result = value * conversions[key]
            return {"result": round(result, 6), "from": from_unit, "to": to_unit, "original": value}
        else:
            raise Exception(f"不支持的单位转换: {from_unit} -> {to_unit}")

    @app.route('/api/base64/encode', methods=['POST'])
    @api_route('/api/base64/encode')
    def base64_encode():
        data = request.json or {}
        text = data.get('text', '')
        
        result = base64.b64encode(text.encode()).decode()
        return {"result": result, "encoded": True}

    @app.route('/api/base64/decode', methods=['POST'])
    @api_route('/api/base64/decode')
    def base64_decode():
        data = request.json or {}
        encoded = data.get('text', '')
        
        try:
            result = base64.b64decode(encoded.encode()).decode()
            return {"result": result, "encoded": False}
        except:
            try:
                result = base64.urlsafe_b64decode(encoded.encode()).decode()
                return {"result": result, "encoded": False}
            except Exception as e:
                raise Exception(f"Base64解码失败: {e}")

    @app.route('/api/ip/info', methods=['GET'])
    @api_route('/api/ip/info')
    def ip_info():
        return {
            "ip": request.remote_addr or 'unknown',
            "user_agent": request.headers.get('User-Agent', 'unknown')[:100]
        }

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

    @app.route('/api/timezones', methods=['GET'])
    @api_route('/api/timezones')
    def get_timezones():
        return {
            "timezones": [
                {"name": "UTC", "offset": "+00:00"},
                {"name": "CST (China)", "offset": "+08:00"},
                {"name": "JST (Japan)", "offset": "+09:00"},
                {"name": "KST (Korea)", "offset": "+09:00"},
                {"name": "EST (New York)", "offset": "-05:00"},
                {"name": "PST (Los Angeles)", "offset": "-08:00"},
                {"name": "GMT (London)", "offset": "+00:00"},
                {"name": "CET (Paris)", "offset": "+01:00"},
                {"name": "AEST (Sydney)", "offset": "+11:00"}
            ]
        }

    @app.route('/api/currency/rates', methods=['GET'])
    @api_route('/api/currency/rates')
    def currency_rates():
        return {
            "rates": {
                "USD": 1.0,
                "CNY": 7.24,
                "EUR": 0.92,
                "GBP": 0.79,
                "JPY": 149.50,
                "KRW": 1320.0,
                "HKD": 7.82,
                "TWD": 31.5
            },
            "base": "USD",
            "timestamp": datetime.now().isoformat()
        }

    @app.route('/api/image/info', methods=['POST'])
    @api_route('/api/image/info')
    def image_info():
        data = request.json or {}
        encoded_image = data.get('image', '')
        if not encoded_image:
            return {"error": "请提供图片数据"}

        try:
            from PIL import Image
            import io
            import base64

            if encoded_image.startswith('data:image'):
                encoded_image = encoded_image.split(',', 1)[1]

            image_data = base64.b64decode(encoded_image)
            img = Image.open(io.BytesIO(image_data))

            return {
                "width": img.size[0],
                "height": img.size[1],
                "format": img.format,
                "mode": img.mode,
                "size_bytes": len(image_data),
                "size_readable": f"{len(image_data) / 1024:.1f} KB"
            }
        except ImportError:
            return {"error": "图片处理需要 Pillow 库 (pip install Pillow)"}
        except Exception as e:
            return {"error": f"无法读取图片: {e}"}

    @app.route('/api/image/resize', methods=['POST'])
    @api_route('/api/image/resize')
    def image_resize():
        data = request.json or {}
        encoded_image = data.get('image', '')
        width = data.get('width', 800)
        height = data.get('height', None)
        maintain_ratio = data.get('maintain_ratio', True)

        if not encoded_image:
            return {"error": "请提供图片数据"}

        try:
            from PIL import Image
            import io
            import base64

            if encoded_image.startswith('data:image'):
                encoded_image = encoded_image.split(',', 1)[1]

            image_data = base64.b64decode(encoded_image)
            img = Image.open(io.BytesIO(image_data))

            if maintain_ratio:
                if height is None:
                    ratio = width / float(img.size[0])
                    height = int(float(img.size[1]) * ratio)
                else:
                    ratio = min(width / float(img.size[0]), height / float(img.size[1]))
                    new_width = int(float(img.size[0]) * ratio)
                    new_height = int(float(img.size[1]) * ratio)
                    width, height = new_width, new_height

            resized_img = img.resize((width, height), Image.LANCZOS)

            output = io.BytesIO()
            resized_img.save(output, format='PNG', quality=95)
            result_base64 = base64.b64encode(output.getvalue()).decode()

            return {
                "image": f"data:image/png;base64,{result_base64}",
                "width": width,
                "height": height,
                "original_width": img.size[0],
                "original_height": img.size[1],
                "format": "PNG"
            }
        except ImportError:
            return {"error": "图片处理需要 Pillow 库 (pip install Pillow)"}
        except Exception as e:
            return {"error": f"调整图片大小时出错: {e}"}

    @app.route('/api/image/compress', methods=['POST'])
    @api_route('/api/image/compress')
    def image_compress():
        data = request.json or {}
        encoded_image = data.get('image', '')
        quality = data.get('quality', 80)
        max_size = data.get('max_size', 1920)

        if not encoded_image:
            return {"error": "请提供图片数据"}

        try:
            from PIL import Image
            import io
            import base64

            if encoded_image.startswith('data:image'):
                encoded_image = encoded_image.split(',', 1)[1]

            image_data = base64.b64decode(encoded_image)
            img = Image.open(io.BytesIO(image_data))

            original_size = len(image_data)

            if img.size[0] > max_size or img.size[1] > max_size:
                ratio = min(max_size / float(img.size[0]), max_size / float(img.size[1]))
                new_width = int(float(img.size[0]) * ratio)
                new_height = int(float(img.size[1]) * ratio)
                img = img.resize((new_width, new_height), Image.LANCZOS)

            output = io.BytesIO()
            img.save(output, format='JPEG', quality=quality, optimize=True)
            compressed_data = output.getvalue()
            result_base64 = base64.b64encode(compressed_data).decode()

            compression_ratio = (1 - len(compressed_data) / original_size) * 100 if original_size > 0 else 0

            return {
                "image": f"data:image/jpeg;base64,{result_base64}",
                "original_size": original_size,
                "compressed_size": len(compressed_data),
                "compression_ratio": f"{compression_ratio:.1f}%",
                "quality": quality
            }
        except ImportError:
            return {"error": "图片处理需要 Pillow 库 (pip install Pillow)"}
        except Exception as e:
            return {"error": f"压缩图片时出错: {e}"}

    @app.route('/api/image/convert', methods=['POST'])
    @api_route('/api/image/convert')
    def image_convert():
        data = request.json or {}
        encoded_image = data.get('image', '')
        target_format = data.get('format', 'PNG').upper()

        if not encoded_image:
            return {"error": "请提供图片数据"}

        if target_format not in ['PNG', 'JPEG', 'WEBP', 'BMP', 'GIF']:
            return {"error": "不支持的目标格式，仅支持 PNG、JPEG、WEBP、BMP、GIF"}

        try:
            from PIL import Image
            import io
            import base64

            if encoded_image.startswith('data:image'):
                encoded_image = encoded_image.split(',', 1)[1]

            image_data = base64.b64decode(encoded_image)
            img = Image.open(io.BytesIO(image_data))

            output = io.BytesIO()
            save_format = target_format if target_format != 'JPG' else 'JPEG'

            if save_format == 'JPEG':
                img = img.convert('RGB')

            img.save(output, format=save_format, quality=95)
            result_base64 = base64.b64encode(output.getvalue()).decode()
            mime_type = f"image/{save_format.lower()}"

            return {
                "image": f"{mime_type};base64,{result_base64}",
                "original_format": img.format or 'Unknown',
                "target_format": target_format
            }
        except ImportError:
            return {"error": "图片处理需要 Pillow 库 (pip install Pillow)"}
        except Exception as e:
            return {"error": f"转换图片格式时出错: {e}"}

    @app.route('/api/image/watermark', methods=['POST'])
    @api_route('/api/image/watermark')
    def image_watermark():
        data = request.json or {}
        encoded_image = data.get('image', '')
        text = data.get('text', 'RAILGUN')
        position = data.get('position', 'bottom-right')

        if not encoded_image:
            return {"error": "请提供图片数据"}

        try:
            from PIL import Image, ImageDraw, ImageFont
            import io
            import base64

            if encoded_image.startswith('data:image'):
                encoded_image = encoded_image.split(',', 1)[1]

            image_data = base64.b64decode(encoded_image)
            img = Image.open(io.BytesIO(image_data)).convert('RGBA')

            txt_layer = Image.new('RGBA', img.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(txt_layer)

            try:
                font = ImageFont.truetype("arial.ttf", max(20, int(img.size[1] * 0.05)))
            except:
                font = ImageFont.load_default()

            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            padding = 20
            positions = {
                'top-left': (padding, padding),
                'top-right': (img.size[0] - text_width - padding, padding),
                'bottom-left': (padding, img.size[1] - text_height - padding),
                'bottom-right': (img.size[0] - text_width - padding, img.size[1] - text_height - padding),
                'center': ((img.size[0] - text_width) // 2, (img.size[1] - text_height) // 2)
            }

            pos = positions.get(position, positions['bottom-right'])

            draw.text(pos, text, font=font, fill=(255, 255, 255, 180))

            watermarked = Image.alpha_composite(img, txt_layer)

            output = io.BytesIO()
            watermarked.convert('RGB').save(output, format='PNG')
            result_base64 = base64.b64encode(output.getvalue()).decode()

            return {
                "image": f"data:image/png;base64,{result_base64}",
                "watermark_text": text,
                "position": position
            }
        except ImportError:
            return {"error": "图片处理需要 Pillow 库 (pip install Pillow)"}
        except Exception as e:
            return {"error": f"添加水印时出错: {e}"}

    @app.route('/api/color/picker', methods=['POST'])
    @api_route('/api/color/picker')
    def color_picker():
        data = request.json or {}
        action = data.get('action', 'generate')

        if action == 'generate':
            color = {
                'hex': '#{:06x}'.format(random.randint(0, 0xFFFFFF)),
                'rgb': f'rgb({random.randint(0,255)}, {random.randint(0,255)}, {random.randint(0,255)})',
                'hsl': f'hsl({random.randint(0,360)}, {random.randint(50,100)}%, {random.randint(40,60)}%)'
            }
            return color
        elif action == 'hex_to_rgb':
            hex_color = data.get('color', '#000000').replace('#', '')
            if len(hex_color) == 6:
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                return {
                    'hex': f'#{hex_color.upper()}',
                    'rgb': f'rgb({r}, {g}, {b})',
                    'rgb_values': [r, g, b]
                }
            return {"error": "无效的 HEX 颜色格式"}
        elif action == 'rgb_to_hex':
            rgb = data.get('color', '0, 0, 0')
            try:
                parts = [int(x.strip()) for x in rgb.split(',')]
                if len(parts) == 3:
                    hex_color = '#{:02x}{:02x}{:02x}'.format(parts[0] % 256, parts[1] % 256, parts[2] % 256)
                    return {'hex': hex_color.upper(), 'rgb': f'rgb({parts[0]}, {parts[1]}, {parts[2]})'}
            except:
                pass
            return {"error": "无效的 RGB 颜色格式"}
        return {"error": "不支持的操作"}

    @app.route('/api/converter/bytes', methods=['POST'])
    @api_route('/api/converter/bytes')
    def bytes_converter():
        data = request.json or {}
        value = float(data.get('value', 0))
        from_unit = data.get('from', 'bytes')
        to_unit = data.get('to', 'KB')

        units = {
            'bytes': 1,
            'KB': 1024,
            'MB': 1024**2,
            'GB': 1024**3,
            'TB': 1024**4
        }

        if from_unit not in units or to_unit not in units:
            return {"error": "不支持的单位"}

        result = value * units[from_unit] / units[to_unit]

        if result >= 1:
            result = round(result, 4)
        else:
            result = round(result, 6)

        return {
            "result": result,
            "from": from_unit,
            "to": to_unit,
            "formatted": f"{result} {to_unit}"
        }

    @app.route('/api/idcard/info', methods=['POST'])
    @api_route('/api/idcard/info')
    def idcard_info():
        data = request.json or {}
        idcard = data.get('idcard', '').strip()

        if not idcard or len(idcard) != 18:
            return {"error": "请输入正确的18位身份证号码"}

        try:
            address_codes = {
                '11': '北京', '12': '天津', '13': '河北', '14': '山西', '15': '内蒙古',
                '21': '辽宁', '22': '吉林', '23': '黑龙江', '31': '上海', '32': '江苏',
                '33': '浙江', '34': '安徽', '35': '福建', '36': '江西', '37': '山东',
                '41': '河南', '42': '湖北', '43': '湖南', '44': '广东', '45': '广西',
                '46': '海南', '50': '重庆', '51': '四川', '52': '贵州', '53': '云南',
                '54': '西藏', '61': '陕西', '62': '甘肃', '63': '青海', '64': '宁夏',
                '65': '新疆', '71': '台湾', '81': '香港', '82': '澳门', '91': '国外'
            }

            year = int(idcard[6:10])
            month = int(idcard[10:12])
            day = int(idcard[12:14])
            gender = int(idcard[16]) % 2

            province = address_codes.get(idcard[0:2], '未知')

            zodiac_signs = [
                (1, 20, '摩羯座'), (2, 19, '水瓶座'), (3, 21, '双鱼座'), (4, 20, '白羊座'),
                (5, 21, '金牛座'), (6, 22, '双子座'), (7, 23, '巨蟹座'), (8, 23, '狮子座'),
                (9, 23, '处女座'), (10, 23, '天秤座'), (11, 22, '天蝎座'), (12, 22, '射手座')
            ]

            date = month * 100 + day
            zodiac = '摩羯座'
            for m, d, z in zodiac_signs:
                if date < m * 100 + d:
                    zodiac = z
                    break

            zodiac_years = ['鼠', '牛', '虎', '兔', '龙', '蛇', '马', '羊', '猴', '鸡', '狗', '猪']
            zodiac_year = zodiac_years[(year - 1900) % 12]

            return {
                "province": province,
                "city": "",
                "birthday": f"{year}年{month:02d}月{day:02d}日",
                "age": 2026 - year,
                "gender": "男" if gender == 1 else "女",
                "zodiac": zodiac,
                "chinese_zodiac": zodiac_year,
                "valid": True
            }
        except Exception as e:
            return {"error": f"解析失败: {e}"}

init_api_routes()

if __name__ == '__main__':
    print(f"Starting RAILGUN API Server v{VERSION}")
    print(f"Go to http://localhost:5000 to view the website")
    app.run(host='0.0.0.0', port=5000, debug=False)
