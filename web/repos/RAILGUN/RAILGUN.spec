# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['e:\\Python\\NEW_start\\RAILGUN\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('e:\\Python\\NEW_start\\RAILGUN\\Data', 'Data'), ('e:\\Python\\NEW_start\\RAILGUN\\WEBSITE', 'WEBSITE'), ('e:\\Python\\NEW_start\\RAILGUN\\Music_Player\\settings.json', 'Music_Player/settings.json')],
    hiddenimports=['PyQt5', 'PyQt5.QtCore', 'PyQt5.QtGui', 'PyQt5.QtWidgets', 'PyQt5.QtMultimedia', 'PyQt5.QtNetwork', 'flask', 'flask_cors', 'flask_socketio', 'flask_sqlalchemy', 'flask_migrate', 'sqlalchemy', 'requests', 'beautifulsoup4', 'bs4', 'openai', 'pyautogui', 'httpx', 'python_vlc', 'pygame', 'werkzeug', 'jinja2', 'click', 'itsdangerous', 'markupsafe', 'certifi', 'charset_normalizer', 'idna', 'urllib3', 'numpy', 'PIL', 'PIL._imaging', 'xmltodict', 'dnspython', 'email_validator', 'aiohttp', 'yarl', 'multidict', 'async_timeout', 'asyncio', 'socketio', 'python_socketio', 'engineio', 'greenlet', 'gevent', 'gevent.websocket', 'websockets', 'zope.interface'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='RAILGUN',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='NONE',
)
