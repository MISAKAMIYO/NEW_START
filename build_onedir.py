import os
import sys
import shutil
from pathlib import Path
import PyInstaller.__main__

os.environ['QTWEBENGINE_DISABLE_SANDBOX'] = '1'

project_root = Path("e:/Python/NEW_start/RAILGUN")
dist_dir = project_root / "dist_nuit"
build_dir = project_root / "build_nuit"

if dist_dir.exists():
    shutil.rmtree(dist_dir)
if build_dir.exists():
    shutil.rmtree(build_dir)

data_files = [
    (str(project_root / "Data"), "Data"),
    (str(project_root / "WEBSITE"), "WEBSITE"),
    (str(project_root / "Music_Player" / "settings.json"), "Music_Player/settings.json"),
]

data_args = []
for src, dst in data_files:
    if os.path.exists(src):
        if os.path.isdir(src):
            data_args.extend(['--add-data', f'{src};{dst}'])
        else:
            data_args.extend(['--add-data', f'{src};{dst}'])

hidden_imports = [
    'PyQt5',
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets',
    'PyQt5.QtMultimedia',
    'PyQt5.QtNetwork',
    'flask',
    'flask_cors',
    'flask_socketio',
    'requests',
    'openai',
    'pyautogui',
    'httpx',
    'python_vlc',
    'pygame',
    'werkzeug',
    'jinja2',
    'click',
    'itsdangerous',
    'markupsafe',
    'certifi',
    'charset_normalizer',
    'idna',
    'urllib3',
    'numpy',
    'PIL',
    'PIL._imaging',
    'xmltodict',
    'dnspython',
    'email_validator',
    'aiohttp',
    'yarl',
    'multidict',
    'async_timeout',
    'asyncio',
]

hidden_imports_args = []
for imp in hidden_imports:
    hidden_imports_args.extend(['--hidden-import', imp])

PyInstaller.__main__.run([
    str(project_root / "main.py"),
    '--name=RAILGUN',
    '--onedir',
    '--windowed',
    '--icon=NONE',
    '--clean',
    '--noconfirm',
] + data_args + hidden_imports_args)

print("\n" + "="*50)
print("打包完成！")
print(f"输出目录: {dist_dir}")
print("="*50)
