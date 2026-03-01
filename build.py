import argparse
import os
import shutil
import sys
from pathlib import Path

import PyInstaller.__main__

# Disable QtWebEngine sandbox to avoid runtime errors when frozen
os.environ['QTWEBENGINE_DISABLE_SANDBOX'] = '1'

# Disable polars CPU check to avoid compilation crashes
os.environ['POLARS_SKIP_CPU_CHECK'] = '1'


def parse_args():
    """Parse command line options for the build script."""
    parser = argparse.ArgumentParser(
        description="Build the RAILGUN application using PyInstaller."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--onefile",
        action="store_true",
        help="Produce a single-file executable (default mode).",
    )
    group.add_argument(
        "--onedir",
        action="store_true",
        help="Produce a directory containing the executable and dependencies.",
    )
    parser.add_argument(
        "--name",
        default="RAILGUN",
        help="Name of the generated executable/bundle.",
    )
    parser.add_argument(
        "--icon",
        default="NONE",
        help="Path to the icon file, or NONE to skip.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove existing build/dist folders before starting.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="PyInstaller log level.",
    )
    return parser.parse_args()


def collect_data_args(project_root: Path):
    """Return a list of --add-data arguments for PyInstaller."""
    data_files = [
        (project_root / "Data", "Data"),
        (project_root / "WEBSITE", "WEBSITE"),
        (project_root / "Music_Player" / "settings.json", "Music_Player/settings.json"),
    ]
    args = []
    for src_path, dst in data_files:
        src_str = str(src_path)
        if os.path.exists(src_str):
            args.extend(["--add-data", f"{src_str}{os.pathsep}{dst}"])
    return args


def collect_hidden_imports() -> list[str]:
    """Return a list of modules that PyInstaller should include explicitly."""
    modules = [
        "PyQt5",
        "PyQt5.QtCore",
        "PyQt5.QtGui",
        "PyQt5.QtWidgets",
        "PyQt5.QtMultimedia",
        "PyQt5.QtNetwork",
        "flask",
        "flask_cors",
        "flask_socketio",
        "flask_sqlalchemy",
        "flask_migrate",
        "sqlalchemy",
        "requests",
        "beautifulsoup4",
        "bs4",
        "openai",
        "pyautogui",
        "httpx",
        "python_vlc",
        "pygame",
        "werkzeug",
        "jinja2",
        "click",
        "itsdangerous",
        "markupsafe",
        "certifi",
        "charset_normalizer",
        "idna",
        "urllib3",
        "numpy",
        "PIL",
        "PIL._imaging",
        "xmltodict",
        "dnspython",
        "email_validator",
        "aiohttp",
        "yarl",
        "multidict",
        "async_timeout",
        "asyncio",
        "socketio",
        "python_socketio",
        "engineio",
        "greenlet",
        "gevent",
        "gevent.websocket",
        "websockets",
        "zope.interface",
        "Music_Player.lyrics_search",
        "Music_Player.lyrics_search_dialog",
        "Music_Player.lyrics_widget",
    ]
    return modules


def main():
    args = parse_args()

    project_root = Path(__file__).resolve().parent
    dist_dir = project_root / ("dist" if args.onefile or not args.onedir else "dist_nuit")
    build_dir = project_root / ("build" if args.onefile or not args.onedir else "build_nuit")

    if args.clean:
        for d in (dist_dir, build_dir):
            if d.exists():
                shutil.rmtree(d)

    data_args = collect_data_args(project_root)
    hidden_imports_args = []
    for module in collect_hidden_imports():
        hidden_imports_args.extend(["--hidden-import", module])

    base_args = [str(project_root / "main.py"), f"--name={args.name}", "--windowed"]
    if args.onefile or not args.onedir:
        base_args.append("--onefile")
    if args.onedir:
        base_args.append("--onedir")
    if args.icon and args.icon.upper() != "NONE":
        base_args.append(f"--icon={args.icon}")
    else:
        base_args.append("--icon=NONE")
    base_args.append(f"--log-level={args.log_level}")
    base_args.append("--noconfirm")

    # exclude unnecessary modules to reduce size
    exclude_modules = [
        "onnx", "onnx.reference", "onnxruntime",
        "polars", "polars._utils",
    ]
    for mod in exclude_modules:
        base_args.append(f"--exclude-module={mod}")

    final_args = [a for a in base_args if a] + data_args + hidden_imports_args
    PyInstaller.__main__.run(final_args)

    print("\n" + "=" * 50)
    print("打包完成！")
    print(f"输出目录: {dist_dir}")
    print("=" * 50)


if __name__ == "__main__":
    main()
