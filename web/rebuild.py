import os
import shutil
import json
from pathlib import Path

web_dir = Path(r"e:\Python\NEW_start\RAILGUN\web")
web_dir.mkdir(parents=True, exist_ok=True)

(web_dir / "templates").mkdir(exist_ok=True)
(web_dir / "static").mkdir(exist_ok=True)
(web_dir / "repos").mkdir(exist_ok=True)

print("=" * 50)
print("重建代码托管网站")
print("=" * 50)

print("\n[1/5] 复制源代码到仓库...")
source_dir = Path(r"e:\Python\NEW_start\RAILGUN")
repo_dir = web_dir / "repos" / "RAILGUN"
repo_dir.mkdir(parents=True, exist_ok=True)

include_dirs = ['AI_Chat', 'Bilibili_Music_Download', 'GAMES', 'Macro', 'Music_Download', 'Music_Player', 'Tools', 'WEBSITE']
include_files = ['main.py', 'main_window.py', 'modern_window.py', 'settings_manager.py', 
                'build.py', 'make_installer.py', 'test_ai_modules.py', 'requirements.txt',
                'Just Start.bat', 'RAILGUN.spec']

for dirname in include_dirs:
    src = source_dir / dirname
    if src.exists() and src.is_dir():
        dst = repo_dir / dirname
        try:
            shutil.copytree(src, dst, dirs_exist_ok=True, ignore=lambda d, files: [f for f in files if f == '__pycache__' or f.endswith('.pyc')])
            print(f"  复制: {dirname}/")
        except Exception as e:
            print(f"  复制失败 {dirname}: {e}")

for filename in include_files:
    src = source_dir / filename
    if src.exists() and src.is_file():
        dst = repo_dir / filename
        try:
            shutil.copy2(src, dst)
            print(f"  复制: {filename}")
        except Exception as e:
            print(f"  复制失败 {filename}: {e}")

print("\n[2/5] 生成data.json...")
files_list = []
for f in repo_dir.rglob('*'):
    if f.is_file() and '__pycache__' not in str(f) and not f.name.endswith('.pyc'):
        rel = str(f.relative_to(repo_dir)).replace('\\', '/')
        files_list.append(rel)

files_list.sort()

data = {
    "repos": [{
        "name": "RAILGUN",
        "description": "RAILGUN - 多功能工具集合软件",
        "created": "2026-02-17T00:00:00",
        "updated": "2026-02-19T00:00:00",
        "files": files_list,
        "commits": 1
    }],
    "users": {
        "admin": {"password": "admin", "name": "Administrator"}
    }
}

with open(web_dir / "data.json", 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"  已保存 {len(files_list)} 个文件")

print("\n[3/5] 创建backend.py...")
backend_code = '''import os
import json
from pathlib import Path
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

DATA_FILE = Path(__file__).parent / 'data.json'
REPOS_DIR = Path(__file__).parent / 'repos'

def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"repos": [], "users": {}}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/repo/<name>')
def repo(name):
    return render_template('repo.html', repo_name=name)

@app.route('/api/repos')
def get_repos():
    data = load_data()
    return jsonify(data.get('repos', []))

@app.route('/api/repo/<name>')
def get_repo(name):
    data = load_data()
    for repo in data.get('repos', []):
        if repo['name'] == name:
            return jsonify(repo)
    return jsonify({"error": "Repository not found"}), 404

@app.route('/api/repo/<name>/files')
def get_repo_files(name):
    repo_path = REPOS_DIR / name
    if not repo_path.exists():
        return jsonify({"error": "Repository not found"}), 404
    
    path = request.args.get('path', '')
    full_path = repo_path / path
    
    if not full_path.exists():
        return jsonify({"error": "Path not found"}), 404
    
    if full_path.is_file():
        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return jsonify({"type": "file", "content": content, "path": path})
    
    items = []
    for item in sorted(full_path.iterdir()):
        if item.name.startswith('.'):
            continue
        items.append({
            "name": item.name,
            "type": "dir" if item.is_dir() else "file"
        })
    return jsonify({"type": "dir", "items": items, "path": path})

@app.route('/api/repo/<name>/file', methods=['GET', 'POST'])
def manage_file(name):
    repo_path = REPOS_DIR / name
    file_path = request.args.get('path', '')
    full_path = repo_path / file_path
    
    if request.method == 'GET':
        if not full_path.exists():
            return jsonify({"error": "File not found"}), 404
        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return jsonify({"content": content, "path": file_path})
    
    if request.method == 'POST':
        content = request.json.get('content', '')
        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route('/api/repo/<name>/delete', methods=['POST'])
def delete_file(name):
    repo_path = REPOS_DIR / name
    file_path = request.json.get('path', '')
    full_path = repo_path / file_path
    
    try:
        if full_path.is_file():
            full_path.unlink()
        elif full_path.is_dir():
            shutil.rmtree(full_path)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8088, debug=True)
'''

with open(web_dir / 'backend.py', 'w', encoding='utf-8') as f:
    f.write(backend_code)

print("\n[4/5] 创建HTML模板...")

index_html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>代码托管</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>📦 代码托管</h1>
            <p>本地GitHub风格代码仓库</p>
        </header>
        
        <div class="repo-list" id="repoList">
            <div class="loading">加载中...</div>
        </div>
    </div>
    
    <script>
        async function loadRepos() {
            try {
                const response = await fetch('/api/repos');
                const repos = await response.json();
                
                const container = document.getElementById('repoList');
                
                if (repos.length === 0) {
                    container.innerHTML = '<div class="empty">暂无仓库</div>';
                    return;
                }
                
                container.innerHTML = repos.map(repo => `
                    <div class="repo-card" onclick="window.location.href='/repo/${repo.name}'">
                        <h3>${repo.name}</h3>
                        <p>${repo.description || '暂无描述'}</p>
                        <div class="repo-meta">
                            <span>📁 ${repo.files?.length || 0} 文件</span>
                            <span>📅 ${new Date(repo.updated).toLocaleDateString()}</span>
                        </div>
                    </div>
                `).join('');
            } catch (error) {
                console.error('加载仓库失败:', error);
            }
        }
        
        loadRepos();
    </script>
</body>
</html>
'''

with open(web_dir / 'templates' / 'index.html', 'w', encoding='utf-8') as f:
    f.write(index_html)

repo_html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ repo_name }} - 代码托管</title>
    <link rel="stylesheet" href="/static/style.css">
    <style>
        .file-list { list-style: none; padding: 0; }
        .file-item { padding: 8px 12px; border-bottom: 1px solid #eee; display: flex; align-items: center; gap: 8px; }
        .file-item:hover { background: #f5f5f5; }
        .file-item.folder { font-weight: 500; }
        .file-icon { width: 20px; text-align: center; }
        .file-content { background: #f6f8fa; padding: 20px; border-radius: 6px; overflow-x: auto; }
        .file-content pre { margin: 0; font-family: 'Consolas', monospace; font-size: 14px; }
        .breadcrumb { padding: 10px 0; color: #666; }
        .breadcrumb a { color: #0366d6; text-decoration: none; }
        .breadcrumb a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1><a href="/" style="color: inherit; text-decoration: none;">📦 代码托管</a></h1>
            <a href="/" class="btn">← 返回</a>
        </header>
        
        <div class="repo-view">
            <h2>{{ repo_name }}</h2>
            <div class="breadcrumb" id="breadcrumb">
                <a href="/repo/{{ repo_name }}">根目录</a>
            </div>
            
            <div id="content">
                <div class="loading">加载中...</div>
            </div>
        </div>
    </div>
    
    <script>
        const repoName = '{{ repo_name }}';
        let currentPath = '';
        
        async function loadPath(path = '') {
            currentPath = path;
            
            const breadcrumb = document.getElementById('breadcrumb');
            const parts = path.split('/').filter(p => p);
            let breadcrumbHtml = '<a href="/repo/' + repoName + '">根目录</a>';
            let prefix = '';
            for (const part of parts) {
                prefix += prefix ? '/' + part : part;
                breadcrumbHtml += ' / <a href="/repo/' + repoName + '?path=' + prefix + '">' + part + '</a>';
            }
            breadcrumb.innerHTML = breadcrumbHtml;
            
            try {
                const url = '/api/repo/' + repoName + '/files' + (path ? '?path=' + encodeURIComponent(path) : '');
                const response = await fetch(url);
                const data = await response.json();
                
                const container = document.getElementById('content');
                
                if (data.type === 'file') {
                    const escaped = data.content.replace(/</g, '&lt;').replace(/>/g, '&gt;');
                    container.innerHTML = '<div class="file-content"><pre>' + escaped + '</pre></div>';
                } else {
                    container.innerHTML = '<ul class="file-list">' + 
                        data.items.map(item => {
                            const icon = item.type === 'dir' ? '📁' : '📄';
                            const link = item.type === 'dir' 
                                ? 'href="javascript:loadPath(\\'' + (path ? path + '/' : '') + item.name + '\\')"'
                                : 'href="javascript:loadPath(\\'' + (path ? path + '/' : '') + item.name + '\\')"';
                            return '<li class="file-item ' + item.type + '"><span class="file-icon">' + icon + '</span><a ' + link + '>' + item.name + '</a></li>';
                        }).join('') + 
                        '</ul>';
                }
            } catch (error) {
                console.error('加载失败:', error);
                document.getElementById('content').innerHTML = '<div class="error">加载失败</div>';
            }
        }
        
        const urlParams = new URLSearchParams(window.location.search);
        loadPath(urlParams.get('path') || '');
    </script>
</body>
</html>
'''

with open(web_dir / 'templates' / 'repo.html', 'w', encoding='utf-8') as f:
    f.write(repo_html)

print("\n[5/5] 创建静态样式...")

css_code = '''* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #f6f8fa;
    color: #24292e;
    min-height: 100vh;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px 0;
    border-bottom: 1px solid #e1e4e8;
    margin-bottom: 30px;
}

header h1 {
    font-size: 28px;
    color: #0366d6;
}

.repo-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 20px;
}

.repo-card {
    background: white;
    border: 1px solid #e1e4e8;
    border-radius: 6px;
    padding: 20px;
    cursor: pointer;
    transition: all 0.2s;
}

.repo-card:hover {
    border-color: #0366d6;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    transform: translateY(-2px);
}

.repo-card h3 {
    color: #0366d6;
    margin-bottom: 8px;
}

.repo-card p {
    color: #586069;
    font-size: 14px;
    margin-bottom: 12px;
}

.repo-meta {
    display: flex;
    gap: 15px;
    font-size: 12px;
    color: #586069;
}

.repo-view {
    background: white;
    border: 1px solid #e1e4e8;
    border-radius: 6px;
    padding: 30px;
}

.repo-view h2 {
    margin-bottom: 20px;
    padding-bottom: 15px;
    border-bottom: 1px solid #e1e4e8;
}

.btn {
    display: inline-block;
    padding: 8px 16px;
    background: #0366d6;
    color: white;
    text-decoration: none;
    border-radius: 6px;
    font-size: 14px;
}

.btn:hover {
    background: #0256bf;
}

.loading, .empty, .error {
    text-align: center;
    padding: 40px;
    color: #586069;
}

.file-list {
    list-style: none;
    border: 1px solid #e1e4e8;
    border-radius: 6px;
    overflow: hidden;
}

.file-item {
    padding: 10px 15px;
    border-bottom: 1px solid #e1e4e8;
    display: flex;
    align-items: center;
    gap: 10px;
}

.file-item:last-child {
    border-bottom: none;
}

.file-item a {
    color: #0366d6;
    text-decoration: none;
}

.file-item a:hover {
    text-decoration: underline;
}

.file-item.folder a {
    color: #24292e;
    font-weight: 500;
}

.file-content {
    background: #f6f8fa;
    padding: 20px;
    border-radius: 6px;
    overflow-x: auto;
}

.file-content pre {
    margin: 0;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 14px;
    line-height: 1.5;
}

.breadcrumb {
    padding: 10px 0;
    margin-bottom: 20px;
    color: #586069;
}

.breadcrumb a {
    color: #0366d6;
    text-decoration: none;
}

.breadcrumb a:hover {
    text-decoration: underline;
}
'''

with open(web_dir / 'static' / 'style.css', 'w', encoding='utf-8') as f:
    f.write(css_code)

print("\n" + "=" * 50)
print("完成! 网站已重建")
print("=" * 50)
print(f"\n仓库包含 {len(files_list)} 个文件")
print("运行 'python backend.py' 启动网站")
