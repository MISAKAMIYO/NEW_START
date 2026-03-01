import sys
import os
import json
import time
import uuid
import hashlib
import re
import logging
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, jsonify, request, send_from_directory, Response
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

app.config['SECRET_KEY'] = 'FORUM_SECRET_KEY_V1'
app.config['JSON_SORT_KEYS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

VERSION = "1.2.0"
START_TIME = datetime.now()

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
BACKUP_DIR = os.path.join(os.path.dirname(__file__), 'backup')
STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')
UPLOAD_DIR = os.path.join(STATIC_DIR, 'uploads')

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

POSTS_FILE = os.path.join(DATA_DIR, 'posts.json')
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
REPLIES_FILE = os.path.join(DATA_DIR, 'replies.json')
SESSIONS_FILE = os.path.join(DATA_DIR, 'sessions.json')
NOTIFICATIONS_FILE = os.path.join(DATA_DIR, 'notifications.json')
BACKUP_INTERVAL = 3600
MAX_BACKUPS = 5

def hash_password(password):
    return hashlib.sha256((password + 'RAILGUN_SALT').encode()).hexdigest()

def generate_token():
    return secrets.token_urlsafe(32)

def validate_input(data, field, min_len=0, max_len=None, required=True):
    value = data.get(field, '').strip() if data else ''
    
    if required and not value:
        return None, f"{field}不能为空"
    
    if value and len(value) < min_len:
        return None, f"{field}不能少于{min_len}个字符"
    
    if max_len and len(value) > max_len:
        return None, f"{field}不能超过{max_len}个字符"
    
    return value, None

def create_backup():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    for src_file, name in [(POSTS_FILE, 'posts'), (REPLIES_FILE, 'replies'), (USERS_FILE, 'users'), (SESSIONS_FILE, 'sessions')]:
        if os.path.exists(src_file):
            try:
                backup_file = os.path.join(BACKUP_DIR, f'{name}_{timestamp}.json')
                with open(src_file, 'r', encoding='utf-8') as sf:
                    with open(backup_file, 'w', encoding='utf-8') as bf:
                        bf.write(sf.read())
                
                backups = sorted([
                    f for f in os.listdir(BACKUP_DIR) 
                    if f.startswith(name) and f.endswith('.json')
                ])
                while len(backups) > MAX_BACKUPS:
                    oldest = backups.pop(0)
                    try:
                        os.remove(os.path.join(BACKUP_DIR, oldest))
                    except:
                        pass
            except Exception as e:
                logger.error(f"Backup failed for {name}: {e}")

def load_json(file_path, default):
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in {file_path}: {e}")
            for i in range(3, 0, -1):
                backup_file = os.path.join(BACKUP_DIR, f'posts_{datetime.now().strftime("%Y%m%d")}_{i}.json')
                if os.path.exists(backup_file):
                    try:
                        with open(backup_file, 'r', encoding='utf-8') as bf:
                            return json.load(bf)
                    except:
                        continue
            return default
        except Exception as e:
            logger.error(f"Failed to load {file_path}: {e}")
            return default
    return default

def save_json(file_path, data):
    try:
        temp_file = f"{file_path}.tmp.{os.getpid()}"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        if os.path.exists(file_path):
            old_file = f"{file_path}.old.{os.getpid()}"
            os.rename(file_path, old_file)
            os.rename(temp_file, file_path)
            try:
                os.remove(old_file)
            except:
                pass
        else:
            os.rename(temp_file, file_path)
        
        return True
    except Exception as e:
        logger.error(f"Failed to save {file_path}: {e}")
        return False

def get_uptime():
    uptime = datetime.now() - START_TIME
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"

posts_data = {
    "posts": [],
    "last_id": 0
}

users_data = {
    "users": {},
    "last_id": 0
}

sessions_data = {
    "sessions": {}
}

replies_data = {
    "replies": [],
    "last_id": 0
}

notifications_data = {
    "notifications": []
}

posts_data = load_json(POSTS_FILE, posts_data)
users_data = load_json(USERS_FILE, users_data)
sessions_data = load_json(SESSIONS_FILE, sessions_data)
replies_data = load_json(REPLIES_FILE, replies_data)
notifications_data = load_json(NOTIFICATIONS_FILE, notifications_data)

last_backup_time = time.time()

online_users = {}

def init_routes():
    @app.route('/')
    def index():
        return send_from_directory(os.path.dirname(__file__), 'index.html')

    @app.route('/index.html')
    def index_html():
        return send_from_directory(os.path.dirname(__file__), 'index.html')

    @app.route('/post.html')
    def post_html():
        return send_from_directory(os.path.dirname(__file__), 'post.html')

    @app.route('/new.html')
    def new_html():
        return send_from_directory(os.path.dirname(__file__), 'new.html')

    @app.route('/login.html')
    def login_html():
        return send_from_directory(os.path.dirname(__file__), 'login.html')

    @app.route('/profile.html')
    def profile_html():
        return send_from_directory(os.path.dirname(__file__), 'profile.html')

    @app.route('/css/<path:path>')
    def css_files(path):
        return send_from_directory(os.path.join(os.path.dirname(__file__), 'css'), path)

    @app.route('/js/<path:path>')
    def js_files(path):
        return send_from_directory(os.path.join(os.path.dirname(__file__), 'js'), path)

    @app.route('/static/<path:path>')
    def static_files(path):
        return send_from_directory(os.path.join(os.path.dirname(__file__), 'static'), path)

    @socketio.on('connect')
    def handle_connect():
        emit('status', {'message': 'Connected to server'})

    @socketio.on('join')
    def handle_join(data):
        username = data.get('username', 'anonymous')
        sid = request.sid
        online_users[sid] = {'username': username, 'connected_at': datetime.now().isoformat()}
        join_room('main_room')
        emit('user_joined', {'username': username, 'online_count': len(online_users)}, room='main_room')
        logger.info(f"User joined: {username}")

    @socketio.on('disconnect')
    def handle_disconnect():
        sid = request.sid
        if sid in online_users:
            username = online_users[sid]['username']
            del online_users[sid]
            emit('user_left', {'username': username, 'online_count': len(online_users)}, room='main_room')
            logger.info(f"User left: {username}")

    @socketio.on('typing')
    def handle_typing(data):
        emit('user_typing', data, room='main_room')

    @socketio.on('stop_typing')
    def handle_stop_typing(data):
        emit('user_stop_typing', data, room='main_room')

    @app.route('/api/status', methods=['GET'])
    def api_status():
        return jsonify({
            "success": True,
            "data": {
                "version": VERSION,
                "uptime": get_uptime(),
                "status": "running",
                "total_posts": len(posts_data["posts"]),
                "total_users": len(users_data["users"]),
                "total_replies": len(replies_data["replies"]),
                "online_count": len(online_users)
            },
            "timestamp": datetime.now().isoformat()
        })

    @app.route('/api/auth/register', methods=['POST'])
    def register():
        try:
            data = request.json or {}

            username, error = validate_input(data, 'username', 2, 20)
            if error:
                return jsonify({"success": False, "error": error}), 400

            password, error = validate_input(data, 'password', 6, 50)
            if error:
                return jsonify({"success": False, "error": error}), 400

            email = data.get('email', '').strip()
            if email and not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
                return jsonify({"success": False, "error": "邮箱格式不正确"}), 400

            if username in users_data["users"]:
                return jsonify({"success": False, "error": "用户名已被注册"}), 400

            for user in users_data["users"].values():
                if email and user.get('email') == email:
                    return jsonify({"success": False, "error": "邮箱已被注册"}), 400

            users_data["last_id"] += 1
            user_id = users_data["last_id"]

            users_data["users"][username] = {
                "id": user_id,
                "username": username,
                "password": hash_password(password),
                "email": email,
                "avatar": f"https://api.dicebear.com/7.x/avataaars/svg?seed={username}",
                "bio": "",
                "created_at": datetime.now().isoformat(),
                "last_login": datetime.now().isoformat(),
                "post_count": 0,
                "like_count": 0
            }

            if not save_json(USERS_FILE, users_data):
                del users_data["users"][username]
                return jsonify({"success": False, "error": "注册失败，请重试"}), 500

            return jsonify({
                "success": True,
                "data": {"user_id": user_id, "username": username},
                "message": "注册成功",
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Register error: {e}")
            return jsonify({"success": False, "error": "服务器内部错误"}), 500

    @app.route('/api/auth/login', methods=['POST'])
    def login():
        try:
            data = request.json or {}

            username, error = validate_input(data, 'username', 2, 20)
            if error:
                return jsonify({"success": False, "error": error}), 400

            password, error = validate_input(data, 'password', 6, 50)
            if error:
                return jsonify({"success": False, "error": error}), 400

            if username not in users_data["users"]:
                return jsonify({"success": False, "error": "用户名或密码错误"}), 401

            user = users_data["users"][username]
            if user['password'] != hash_password(password):
                return jsonify({"success": False, "error": "用户名或密码错误"}), 401

            user['last_login'] = datetime.now().isoformat()
            save_json(USERS_FILE, users_data)

            token = generate_token()
            sessions_data["sessions"][token] = {
                "username": username,
                "created_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(days=7)).isoformat()
            }
            save_json(SESSIONS_FILE, sessions_data)

            return jsonify({
                "success": True,
                "data": {
                    "token": token,
                    "username": username,
                    "user": {
                        "id": user['id'],
                        "username": user['username'],
                        "avatar": user['avatar'],
                        "email": user.get('email', ''),
                        "bio": user.get('bio', ''),
                        "post_count": user.get('post_count', 0),
                        "like_count": user.get('like_count', 0)
                    }
                },
                "message": "登录成功",
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Login error: {e}")
            return jsonify({"success": False, "error": "服务器内部错误"}), 500

    @app.route('/api/auth/logout', methods=['POST'])
    def logout():
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            if token in sessions_data["sessions"]:
                del sessions_data["sessions"][token]
                save_json(SESSIONS_FILE, sessions_data)
        return jsonify({
            "success": True,
            "message": "已退出登录",
            "timestamp": datetime.now().isoformat()
        })

    @app.route('/api/auth/me', methods=['GET'])
    def get_me():
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({"success": False, "error": "未登录"}), 401

        token = auth_header[7:]
        if token not in sessions_data["sessions"]:
            return jsonify({"success": False, "error": "登录已过期"}), 401

        session = sessions_data["sessions"][token]
        username = session['username']

        if username not in users_data["users"]:
            return jsonify({"success": False, "error": "用户不存在"}), 404

        user = users_data["users"][username]
        return jsonify({
            "success": True,
            "data": {
                "id": user['id'],
                "username": user['username'],
                "avatar": user['avatar'],
                "email": user.get('email', ''),
                "bio": user.get('bio', ''),
                "post_count": user.get('post_count', 0),
                "like_count": user.get('like_count', 0),
                "created_at": user.get('created_at', '')
            },
            "timestamp": datetime.now().isoformat()
        })

    @app.route('/api/auth/update_profile', methods=['POST'])
    def update_profile():
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({"success": False, "error": "未登录"}), 401

        token = auth_header[7:]
        if token not in sessions_data["sessions"]:
            return jsonify({"success": False, "error": "登录已过期"}), 401

        username = sessions_data["sessions"][token]['username']
        if username not in users_data["users"]:
            return jsonify({"success": False, "error": "用户不存在"}), 404

        data = request.json or {}
        user = users_data["users"][username]

        if 'bio' in data:
            bio = data['bio'][:200]
            user['bio'] = bio

        if 'avatar' in data:
            avatar = data['avatar']
            if avatar.startswith('http') or avatar.startswith('data:'):
                user['avatar'] = avatar

        save_json(USERS_FILE, users_data)

        return jsonify({
            "success": True,
            "data": {
                "bio": user.get('bio', ''),
                "avatar": user['avatar']
            },
            "message": "资料更新成功",
            "timestamp": datetime.now().isoformat()
        })

    def require_auth(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return jsonify({"success": False, "error": "未登录"}), 401
            
            token = auth_header[7:]
            if token not in sessions_data["sessions"]:
                return jsonify({"success": False, "error": "登录已过期"}), 401
            
            session = sessions_data["sessions"][token]
            kwargs['current_user'] = session['username']
            return f(*args, **kwargs)
        return decorated

    @app.route('/api/upload/image', methods=['POST'])
    @require_auth
    def upload_image(current_user):
        if 'image' not in request.files:
            return jsonify({"success": False, "error": "没有上传文件"}), 400

        file = request.files['image']
        if file.filename == '':
            return jsonify({"success": False, "error": "没有选择文件"}), 400

        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        if ext not in allowed_extensions:
            return jsonify({"success": False, "error": "不支持的文件格式"}), 400

        filename = f"{current_user}_{int(time.time())}_{secrets.token_hex(8)}.{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        file.save(filepath)

        image_url = f"/static/uploads/{filename}"

        return jsonify({
            "success": True,
            "data": {"url": image_url},
            "message": "上传成功",
            "timestamp": datetime.now().isoformat()
        })

    @app.route('/api/upload/avatar', methods=['POST'])
    @require_auth
    def upload_avatar(current_user):
        if 'avatar' not in request.files:
            return jsonify({"success": False, "error": "没有上传文件"}), 400

        file = request.files['avatar']
        if file.filename == '':
            return jsonify({"success": False, "error": "没有选择文件"}), 400

        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        if ext not in allowed_extensions:
            return jsonify({"success": False, "error": "不支持的文件格式"}), 400

        filename = f"avatar_{current_user}_{secrets.token_hex(8)}.{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        file.save(filepath)

        users_data["users"][current_user]['avatar'] = f"/static/uploads/{filename}"
        save_json(USERS_FILE, users_data)

        return jsonify({
            "success": True,
            "data": {"url": f"/static/uploads/{filename}"},
            "message": "头像上传成功",
            "timestamp": datetime.now().isoformat()
        })

    @app.route('/api/notifications', methods=['GET'])
    @require_auth
    def get_notifications(current_user):
        user_notifications = [n for n in notifications_data["notifications"] if n.get('user') == current_user]
        user_notifications.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return jsonify({
            "success": True,
            "data": user_notifications[:50],
            "timestamp": datetime.now().isoformat()
        })

    @app.route('/api/posts', methods=['GET'])
    def get_posts():
        global last_backup_time
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        category = request.args.get('category', '')
        sort = request.args.get('sort', 'latest')

        if page < 1:
            page = 1
        if per_page < 1 or per_page > 100:
            per_page = 20

        posts = posts_data["posts"].copy()

        if category and category != 'all':
            posts = [p for p in posts if p.get('category') == category]

        if sort == 'latest':
            posts.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        elif sort == 'popular':
            posts.sort(key=lambda x: x.get('view_count', 0), reverse=True)
        elif sort == 'replies':
            posts.sort(key=lambda x: x.get('reply_count', 0), reverse=True)

        total = len(posts)
        start = (page - 1) * per_page
        end = start + per_page
        posts_slice = posts[start:end]

        if time.time() - last_backup_time > BACKUP_INTERVAL:
            create_backup()
            last_backup_time = time.time()

        return jsonify({
            "success": True,
            "data": {
                "posts": posts_slice,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "total_pages": (total + per_page - 1) // per_page
                }
            },
            "timestamp": datetime.now().isoformat()
        })

    @app.route('/api/posts/<post_id>', methods=['GET'])
    def get_post(post_id):
        if not post_id or not post_id.strip():
            return jsonify({
                "success": False,
                "error": "帖子ID无效",
                "error_type": "invalid_id"
            }), 400

        for post in posts_data["posts"]:
            if str(post.get('id')) == str(post_id):
                post['view_count'] = post.get('view_count', 0) + 1
                if not save_json(POSTS_FILE, posts_data):
                    post['view_count'] -= 1
                    return jsonify({
                        "success": False,
                        "error": "更新浏览计数失败",
                        "error_type": "save_error"
                    }), 500

                sort = request.args.get('sort', 'time')
                page = request.args.get('page', 1, type=int)
                per_page = request.args.get('per_page', 20, type=int)
                
                post_replies = [r for r in replies_data["replies"] if str(r.get('post_id')) == str(post_id) and not r.get('is_deleted') and not r.get('parent_id')]
                
                if sort == 'hot':
                    post_replies.sort(key=lambda x: (x.get('like_count', 0), x.get('created_at', '')), reverse=True)
                else:
                    post_replies.sort(key=lambda x: x.get('created_at', ''), reverse=True)
                
                total = len(post_replies)
                start_idx = (page - 1) * per_page
                end_idx = start_idx + per_page
                paginated_replies = post_replies[start_idx:end_idx]
                
                for reply in paginated_replies:
                    reply['replies'] = []
                    child_replies = [r for r in replies_data["replies"] if str(r.get('post_id')) == str(post_id) and r.get('parent_id') == reply['id'] and not r.get('is_deleted')]
                    child_replies.sort(key=lambda x: x.get('created_at', ''), reverse=True)
                    reply['replies'] = child_replies
                    reply['reply_count'] = len(child_replies)

                return jsonify({
                    "success": True,
                    "data": {
                        "post": post,
                        "replies": paginated_replies,
                        "pagination": {
                            "page": page,
                            "per_page": per_page,
                            "total": total,
                            "total_pages": (total + per_page - 1) // per_page
                        }
                    },
                    "timestamp": datetime.now().isoformat()
                })

        return jsonify({
            "success": False,
            "error": "帖子不存在",
            "error_type": "not_found"
        }), 404

    @app.route('/api/posts', methods=['POST'])
    def create_post():
        try:
            data = request.json or {}

            title, error = validate_input(data, 'title', 2, 100)
            if error:
                return jsonify({"success": False, "error": error}), 400

            content, error = validate_input(data, 'content', 10, 10000)
            if error:
                return jsonify({"success": False, "error": error}), 400

            category = data.get('category', 'general')
            if category not in ['general', 'suggestion', 'bug', 'discussion', 'chat']:
                category = 'general'

            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
                if token in sessions_data["sessions"]:
                    author = sessions_data["sessions"][token]['username']
                    if author in users_data["users"]:
                        users_data["users"][author]['post_count'] += 1
                        save_json(USERS_FILE, users_data)
                else:
                    author = data.get('author', '匿名').strip() or '匿名'
            else:
                author = data.get('author', '匿名').strip() or '匿名'

            posts_data["last_id"] += 1
            post_id = posts_data["last_id"]

            now = datetime.now().isoformat()
            post = {
                "id": post_id,
                "title": title,
                "content": content,
                "category": category,
                "author": author,
                "created_at": now,
                "updated_at": now,
                "view_count": 0,
                "reply_count": 0,
                "like_count": 0,
                "is_top": False,
                "is_locked": False,
                "is_deleted": False
            }

            posts_data["posts"].insert(0, post)

            if not save_json(POSTS_FILE, posts_data):
                posts_data["posts"].pop(0)
                return jsonify({
                    "success": False,
                    "error": "保存帖子失败，请重试",
                    "error_type": "save_error"
                }), 500

            socketio.emit('new_post', {'post': post}, room='main_room')

            return jsonify({
                "success": True,
                "data": {"post_id": post_id},
                "message": "帖子发布成功",
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Create post error: {e}")
            return jsonify({
                "success": False,
                "error": "服务器内部错误",
                "error_type": "server_error"
            }), 500

    @app.route('/api/posts/<post_id>/replies', methods=['POST'])
    def create_reply(post_id):
        try:
            if not post_id or not post_id.strip():
                return jsonify({
                    "success": False,
                    "error": "帖子ID无效",
                    "error_type": "invalid_id"
                }), 400

            data = request.json or {}

            content, error = validate_input(data, 'content', 2, 2000)
            if error:
                return jsonify({"success": False, "error": error}), 400

            parent_id = data.get('parent_id')
            if parent_id and not isinstance(parent_id, int):
                parent_id = None

            auth_header = request.headers.get('Authorization', '')
            author = None
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]
                if token in sessions_data["sessions"]:
                    author = sessions_data["sessions"][token]['username']
            
            if not author:
                author = data.get('author', '匿名').strip() or '匿名'

            post_exists = False
            post_index = -1
            post_author = None
            for i, post in enumerate(posts_data["posts"]):
                if str(post.get('id')) == str(post_id):
                    post_exists = True
                    if post.get('is_locked'):
                        return jsonify({
                            "success": False,
                            "error": "帖子已锁定，无法回复",
                            "error_type": "locked"
                        }), 403
                    post_index = i
                    post_author = post.get('author')
                    break

            if not post_exists:
                return jsonify({
                    "success": False,
                    "error": "帖子不存在",
                    "error_type": "not_found"
                }), 404

            if parent_id:
                parent_reply = None
                for r in replies_data["replies"]:
                    if r.get('id') == parent_id and str(r.get('post_id')) == str(post_id):
                        parent_reply = r
                        break
                
                if not parent_reply:
                    return jsonify({
                        "success": False,
                        "error": "父评论不存在",
                        "error_type": "not_found"
                    }), 404
                
                if parent_reply.get('is_deleted'):
                    return jsonify({
                        "success": False,
                        "error": "父评论已被删除",
                        "error_type": "deleted"
                    }), 400

            replies_data["last_id"] += 1
            reply_id = replies_data["last_id"]

            now = datetime.now().isoformat()
            reply = {
                "id": reply_id,
                "post_id": int(post_id),
                "parent_id": parent_id,
                "content": content,
                "author": author,
                "created_at": now,
                "like_count": 0,
                "is_deleted": False,
                "is_edited": False,
                "edited_at": None
            }

            replies_data["replies"].append(reply)

            if not save_json(REPLIES_FILE, replies_data):
                replies_data["replies"].pop()
                return jsonify({
                    "success": False,
                    "error": "保存回复失败，请重试",
                    "error_type": "save_error"
                }), 500

            posts_data["posts"][post_index]['reply_count'] = posts_data["posts"][post_index].get('reply_count', 0) + 1
            if not save_json(POSTS_FILE, posts_data):
                posts_data["posts"][post_index]['reply_count'] -= 1
                logger.warning("Reply saved but post update failed")

            if parent_id:
                socketio.emit('new_child_reply', {
                    'post_id': int(post_id), 
                    'reply': reply,
                    'parent_id': parent_id
                }, room=f'reply_{parent_id}')
                
                if parent_reply.get('author') != author:
                    notification = {
                        "id": len(notifications_data["notifications"]) + 1,
                        "user": parent_reply.get('author'),
                        "type": "reply",
                        "message": f"{author} 回复了你的评论",
                        "post_id": int(post_id),
                        "reply_id": reply_id,
                        "parent_id": parent_id,
                        "read": False,
                        "created_at": now
                    }
                    notifications_data["notifications"].append(notification)
                    save_json(NOTIFICATIONS_FILE, notifications_data)
            else:
                socketio.emit('new_reply', {'post_id': int(post_id), 'reply': reply}, room='main_room')
                
                if post_author and post_author != author:
                    notification = {
                        "id": len(notifications_data["notifications"]) + 1,
                        "user": post_author,
                        "type": "reply",
                        "message": f"{author} 回复了你的帖子",
                        "post_id": int(post_id),
                        "reply_id": reply_id,
                        "read": False,
                        "created_at": now
                    }
                    notifications_data["notifications"].append(notification)
                    save_json(NOTIFICATIONS_FILE, notifications_data)

            return jsonify({
                "success": True,
                "data": {"reply_id": reply_id},
                "message": "回复发布成功",
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Create reply error: {e}")
            return jsonify({
                "success": False,
                "error": "服务器内部错误，请稍后重试",
                "error_type": "server_error"
            }), 500

    @app.route('/api/posts/<post_id>/replies/<reply_id>', methods=['PUT'])
    def update_reply(post_id, reply_id):
        try:
            if not post_id or not post_id.strip():
                return jsonify({
                    "success": False,
                    "error": "帖子ID无效",
                    "error_type": "invalid_id"
                }), 400
            
            if not reply_id or not reply_id.strip():
                return jsonify({
                    "success": False,
                    "error": "回复ID无效",
                    "error_type": "invalid_id"
                }), 400

            data = request.json or {}
            new_content = data.get('content', '').strip()

            if len(new_content) < 2:
                return jsonify({
                    "success": False,
                    "error": "回复内容至少2个字符",
                    "error_type": "validation_error"
                }), 400

            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return jsonify({
                    "success": False,
                    "error": "请先登录后操作",
                    "error_type": "auth_required"
                }), 401

            token = auth_header[7:]
            if token not in sessions_data["sessions"]:
                return jsonify({
                    "success": False,
                    "error": "登录已过期，请重新登录",
                    "error_type": "auth_expired"
                }), 401

            current_user = sessions_data["sessions"][token]['username']

            reply = None
            reply_index = -1
            for i, r in enumerate(replies_data["replies"]):
                if str(r.get('id')) == str(reply_id) and str(r.get('post_id')) == str(post_id):
                    reply = r
                    reply_index = i
                    break

            if not reply:
                return jsonify({
                    "success": False,
                    "error": "回复不存在",
                    "error_type": "not_found"
                }), 404

            if reply.get('is_deleted'):
                return jsonify({
                    "success": False,
                    "error": "回复已被删除",
                    "error_type": "deleted"
                }), 400

            if reply.get('author') != current_user:
                return jsonify({
                    "success": False,
                    "error": "只能编辑自己的回复",
                    "error_type": "permission_denied"
                }), 403

            replies_data["replies"][reply_index]['content'] = new_content
            replies_data["replies"][reply_index]['is_edited'] = True
            replies_data["replies"][reply_index]['edited_at'] = datetime.now().isoformat()

            if not save_json(REPLIES_FILE, replies_data):
                return jsonify({
                    "success": False,
                    "error": "保存失败，请重试",
                    "error_type": "save_error"
                }), 500

            return jsonify({
                "success": True,
                "data": {
                    "reply_id": int(reply_id),
                    "content": new_content,
                    "is_edited": True,
                    "edited_at": replies_data["replies"][reply_index]['edited_at']
                },
                "message": "编辑成功",
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Update reply error: {e}")
            return jsonify({
                "success": False,
                "error": "服务器内部错误，请稍后重试",
                "error_type": "server_error"
            }), 500

    @app.route('/api/posts/<post_id>/replies/<reply_id>', methods=['DELETE'])
    def delete_reply(post_id, reply_id):
        try:
            if not post_id or not post_id.strip():
                return jsonify({
                    "success": False,
                    "error": "帖子ID无效",
                    "error_type": "invalid_id"
                }), 400
            
            if not reply_id or not reply_id.strip():
                return jsonify({
                    "success": False,
                    "error": "回复ID无效",
                    "error_type": "invalid_id"
                }), 400

            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return jsonify({
                    "success": False,
                    "error": "请先登录后操作",
                    "error_type": "auth_required"
                }), 401

            token = auth_header[7:]
            if token not in sessions_data["sessions"]:
                return jsonify({
                    "success": False,
                    "error": "登录已过期，请重新登录",
                    "error_type": "auth_expired"
                }), 401

            current_user = sessions_data["sessions"][token]['username']

            reply = None
            reply_index = -1
            post_index = -1
            for i, r in enumerate(replies_data["replies"]):
                if str(r.get('id')) == str(reply_id) and str(r.get('post_id')) == str(post_id):
                    reply = r
                    reply_index = i
                    break

            if not reply:
                return jsonify({
                    "success": False,
                    "error": "回复不存在",
                    "error_type": "not_found"
                }), 404

            if reply.get('is_deleted'):
                return jsonify({
                    "success": False,
                    "error": "回复已被删除",
                    "error_type": "deleted"
                }), 400

            if reply.get('author') != current_user:
                return jsonify({
                    "success": False,
                    "error": "只能删除自己的回复",
                    "error_type": "permission_denied"
                }), 403

            replies_data["replies"][reply_index]['is_deleted'] = True
            replies_data["replies"][reply_index]['content'] = '[已删除]'

            if not save_json(REPLIES_FILE, replies_data):
                return jsonify({
                    "success": False,
                    "error": "删除失败，请重试",
                    "error_type": "save_error"
                }), 500

            for i, post in enumerate(posts_data["posts"]):
                if str(post.get('id')) == str(post_id):
                    post_index = i
                    break
            
            if post_index >= 0:
                posts_data["posts"][post_index]['reply_count'] = max(0, posts_data["posts"][post_index].get('reply_count', 1) - 1)
                save_json(POSTS_FILE, posts_data)

            return jsonify({
                "success": True,
                "data": {"reply_id": int(reply_id)},
                "message": "删除成功",
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.error(f"Delete reply error: {e}")
            return jsonify({
                "success": False,
                "error": "服务器内部错误，请稍后重试",
                "error_type": "server_error"
            }), 500

    @app.route('/api/posts/<post_id>/replies/<reply_id>', methods=['GET'])
    def get_reply(post_id, reply_id):
        try:
            if not post_id or not post_id.strip():
                return jsonify({
                    "success": False,
                    "error": "帖子ID无效",
                    "error_type": "invalid_id"
                }), 400
            
            if not reply_id or not reply_id.strip():
                return jsonify({
                    "success": False,
                    "error": "回复ID无效",
                    "error_type": "invalid_id"
                }), 400

            for r in replies_data["replies"]:
                if str(r.get('id')) == str(reply_id) and str(r.get('post_id')) == str(post_id):
                    if r.get('is_deleted'):
                        return jsonify({
                            "success": False,
                            "error": "回复已被删除",
                            "error_type": "deleted"
                        }), 404
                    
                    return jsonify({
                        "success": True,
                        "data": {"reply": r},
                        "timestamp": datetime.now().isoformat()
                    })

            return jsonify({
                "success": False,
                "error": "回复不存在",
                "error_type": "not_found"
            }), 404
        except Exception as e:
            logger.error(f"Get reply error: {e}")
            return jsonify({
                "success": False,
                "error": "服务器内部错误",
                "error_type": "server_error"
            }), 500

    @app.route('/api/posts/<post_id>/like', methods=['POST'])
    def like_post(post_id):
        if not post_id or not post_id.strip():
            return jsonify({
                "success": False,
                "error": "帖子ID无效",
                "error_type": "invalid_id"
            }), 400

        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            if token in sessions_data["sessions"]:
                username = sessions_data["sessions"][token]['username']
            else:
                username = 'anonymous'
        else:
            username = 'anonymous'

        for i, post in enumerate(posts_data["posts"]):
            if str(post.get('id')) == str(post_id):
                post['like_count'] = post.get('like_count', 0) + 1
                if not save_json(POSTS_FILE, posts_data):
                    post['like_count'] -= 1
                    return jsonify({
                        "success": False,
                        "error": "点赞失败，请重试",
                        "error_type": "save_error"
                    }), 500

                socketio.emit('post_liked', {'post_id': int(post_id), 'like_count': post['like_count']}, room='main_room')

                if username != 'anonymous' and username != post.get('author'):
                    now = datetime.now().isoformat()
                    notification = {
                        "id": len(notifications_data["notifications"]) + 1,
                        "user": post.get('author'),
                        "type": "like",
                        "message": f"{username} 点赞了你的帖子",
                        "post_id": int(post_id),
                        "read": False,
                        "created_at": now
                    }
                    notifications_data["notifications"].append(notification)
                    save_json(NOTIFICATIONS_FILE, notifications_data)

                return jsonify({
                    "success": True,
                    "data": {"like_count": post['like_count']},
                    "timestamp": datetime.now().isoformat()
                })

        return jsonify({
            "success": False,
            "error": "帖子不存在",
            "error_type": "not_found"
        }), 404

    @app.route('/api/posts/<post_id>/replies/<reply_id>/like', methods=['POST'])
    def like_reply(post_id, reply_id):
        if not post_id or not post_id.strip():
            return jsonify({
                "success": False,
                "error": "帖子ID无效",
                "error_type": "invalid_id"
            }), 400

        if not reply_id or not reply_id.strip():
            return jsonify({
                "success": False,
                "error": "回复ID无效",
                "error_type": "invalid_id"
            }), 400

        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            if token in sessions_data["sessions"]:
                username = sessions_data["sessions"][token]['username']
            else:
                username = 'anonymous'
        else:
            username = 'anonymous'

        for i, reply in enumerate(replies_data["replies"]):
            if str(reply.get('id')) == str(reply_id) and str(reply.get('post_id')) == str(post_id):
                reply['like_count'] = reply.get('like_count', 0) + 1
                if not save_json(REPLIES_FILE, replies_data):
                    reply['like_count'] -= 1
                    return jsonify({
                        "success": False,
                        "error": "点赞失败，请重试",
                        "error_type": "save_error"
                    }), 500

                socketio.emit('reply_liked', {'post_id': int(post_id), 'reply_id': int(reply_id), 'like_count': reply['like_count']}, room='main_room')

                return jsonify({
                    "success": True,
                    "data": {"like_count": reply['like_count']},
                    "timestamp": datetime.now().isoformat()
                })

        return jsonify({
            "success": False,
            "error": "回复不存在",
            "error_type": "not_found"
        }), 404

    @app.route('/api/categories', methods=['GET'])
    def get_categories():
        categories = [
            {"id": "all", "name": "全部", "icon": "📋", "count": len(posts_data["posts"])},
            {"id": "general", "name": "综合", "icon": "💬", "count": len([p for p in posts_data["posts"] if p.get('category') == 'general'])},
            {"id": "suggestion", "name": "建议反馈", "icon": "💡", "count": len([p for p in posts_data["posts"] if p.get('category') == 'suggestion'])},
            {"id": "bug", "name": "Bug反馈", "icon": "🐛", "count": len([p for p in posts_data["posts"] if p.get('category') == 'bug'])},
            {"id": "discussion", "name": "技术讨论", "icon": "💻", "count": len([p for p in posts_data["posts"] if p.get('category') == 'discussion'])},
            {"id": "chat", "name": "闲聊灌水", "icon": "☕", "count": len([p for p in posts_data["posts"] if p.get('category') == 'chat'])}
        ]
        return jsonify({
            "success": True,
            "data": {"categories": categories},
            "timestamp": datetime.now().isoformat()
        })

    @app.route('/api/stats', methods=['GET'])
    def get_stats():
        today = datetime.now().strftime('%Y-%m-%d')
        today_posts = len([p for p in posts_data["posts"] if p.get('created_at', '').startswith(today)])
        today_replies = len([r for r in replies_data["replies"] if r.get('created_at', '').startswith(today)])
        online_count = len(online_users)

        return jsonify({
            "success": True,
            "data": {
                "total_posts": len(posts_data["posts"]),
                "total_replies": len(replies_data["replies"]),
                "total_users": len(users_data["users"]),
                "today_posts": today_posts,
                "today_replies": today_replies,
                "online_count": online_count
            },
            "timestamp": datetime.now().isoformat()
        })

    @app.route('/api/search', methods=['GET'])
    def search_posts():
        keyword = request.args.get('keyword', '').strip().lower()
        if not keyword or len(keyword) < 2:
            return jsonify({
                "success": False,
                "error": "搜索关键词至少2个字符",
                "error_type": "invalid_keyword"
            }), 400

        if len(keyword) > 100:
            return jsonify({
                "success": False,
                "error": "搜索关键词过长",
                "error_type": "keyword_too_long"
            }), 400

        results = []
        for post in posts_data["posts"]:
            if keyword in post.get('title', '').lower() or keyword in post.get('content', '').lower():
                results.append({
                    "id": post.get('id'),
                    "title": post.get('title'),
                    "author": post.get('author'),
                    "created_at": post.get('created_at'),
                    "reply_count": post.get('reply_count', 0),
                    "category": post.get('category')
                })

        return jsonify({
            "success": True,
            "data": {
                "keyword": keyword,
                "results": results,
                "count": len(results)
            },
            "timestamp": datetime.now().isoformat()
        })

    @app.route('/api/users/<username>', methods=['GET'])
    def get_user_profile(username):
        if username not in users_data["users"]:
            return jsonify({
                "success": False,
                "error": "用户不存在"
            }), 404

        user = users_data["users"][username]
        return jsonify({
            "success": True,
            "data": {
                "id": user['id'],
                "username": user['username'],
                "avatar": user['avatar'],
                "bio": user.get('bio', ''),
                "post_count": user.get('post_count', 0),
                "like_count": user.get('like_count', 0),
                "created_at": user.get('created_at', ''),
                "last_login": user.get('last_login', '')
            },
            "timestamp": datetime.now().isoformat()
        })

    @app.route('/api/posts/<post_id>', methods=['DELETE'])
    def delete_post(post_id):
        if not post_id or not post_id.strip():
            return jsonify({
                "success": False,
                "error": "帖子ID无效",
                "error_type": "invalid_id"
            }), 400

        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({
                "success": False,
                "error": "需要登录才能删除"
            }), 401

        token = auth_header[7:]
        if token not in sessions_data["sessions"]:
            return jsonify({
                "success": False,
                "error": "登录已过期"
            }), 401

        username = sessions_data["sessions"][token]['username']

        for i, post in enumerate(posts_data["posts"]):
            if str(post.get('id')) == str(post_id):
                if post.get('author') != username:
                    return jsonify({
                        "success": False,
                        "error": "无权删除此帖子"
                    }), 403

                posts_data["posts"][i]['is_deleted'] = True
                if not save_json(POSTS_FILE, posts_data):
                    posts_data["posts"][i]['is_deleted'] = False
                    return jsonify({
                        "success": False,
                        "error": "删除失败，请重试",
                        "error_type": "save_error"
                    }), 500

                original_count = len(replies_data["replies"])
                replies_data["replies"] = [r for r in replies_data["replies"] if str(r.get('post_id')) != str(post_id)]
                if len(replies_data["replies"]) != original_count:
                    save_json(REPLIES_FILE, replies_data)

                return jsonify({
                    "success": True,
                    "message": "帖子已删除",
                    "timestamp": datetime.now().isoformat()
                })

        return jsonify({
            "success": False,
            "error": "帖子不存在",
            "error_type": "not_found"
        }), 404

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({
            "success": False,
            "error": "请求的资源不存在",
            "error_type": "not_found",
            "timestamp": datetime.now().isoformat()
        }), 404

    @app.errorhandler(500)
    def server_error(e):
        logger.error(f"Server error: {e}")
        return jsonify({
            "success": False,
            "error": "服务器内部错误",
            "error_type": "server_error",
            "timestamp": datetime.now().isoformat()
        }), 500

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({
            "success": False,
            "error": "请求参数错误",
            "error_type": "bad_request",
            "timestamp": datetime.now().isoformat()
        }), 400

if __name__ == '__main__':
    init_routes()
    print("=" * 50)
    print("  🚀 RAILGUN Forum Server v1.2.0")
    print("  📍 Address: http://127.0.0.1:5001")
    print("  🔐 Auth: Enabled")
    print("  📤 Upload: Enabled")
    print("  🔔 WebSocket: Enabled")
    print("=" * 50)
    socketio.run(app, host='0.0.0.0', port=5001, debug=False)
