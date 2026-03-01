import os
import json
import shutil
from pathlib import Path
from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

DATA_FILE = Path(__file__).parent / 'data.json'
REPOS_DIR = Path(__file__).parent / 'repos'

try:
    from music_api import music_bp
    app.register_blueprint(music_bp)
except Exception as e:
    print(f"[Music API] 加载失败: {e}")

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

@app.route('/music')
def music():
    return render_template('music.html')

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
