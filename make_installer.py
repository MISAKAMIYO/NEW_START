import os
import sys
import zipfile
import shutil
import subprocess
from pathlib import Path

project_root = Path("e:/Python/NEW_start/RAILGUN")
dist_dir = project_root / "dist"
installer_dir = project_root / "installer"

if installer_dir.exists():
    shutil.rmtree(installer_dir)
installer_dir.mkdir(parents=True)

data_to_package = [
    ("RAILGUN.exe", dist_dir / "RAILGUN.exe"),
    ("Data", project_root / "Data"),
    ("WEBSITE", project_root / "WEBSITE"),
    ("Music_Player", project_root / "Music_Player"),
    ("Music_Download", project_root / "Music_Download"),
    ("Bilibili_Music_Download", project_root / "Bilibili_Music_Download"),
    ("AI_Chat", project_root / "AI_Chat"),
    ("GAMES", project_root / "GAMES"),
    ("Macro", project_root / "Macro"),
    ("Tools", project_root / "Tools"),
]

temp_dir = installer_dir / "temp"
temp_dir.mkdir(exist_ok=True)

print("正在复制文件到临时目录...")
for name, source in data_to_package:
    dest = temp_dir / name
    if source.exists():
        if source.is_dir():
            shutil.copytree(source, dest, dirs_exist_ok=True)
            print(f"  ✓ {name}/ (目录)")
        else:
            shutil.copy2(source, dest)
            print(f"  ✓ {name}")
    else:
        print(f"  ✗ {name} (不存在)")

zip_path = installer_dir / "RAILGUN.zip"
print(f"\n正在创建压缩包: {zip_path}")
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            file_path = Path(root) / file
            arcname = file_path.relative_to(temp_dir)
            zipf.write(file_path, arcname)
            print(f"  添加: {arcname}")

shutil.rmtree(temp_dir)

print(f"\n✓ 安装包已创建: {zip_path}")
print(f"  文件大小: {zip_path.stat().st_size / 1024 / 1024:.1f} MB")
print("\n分发 zip 文件即可，用户解压后运行 RAILGUN.exe")
