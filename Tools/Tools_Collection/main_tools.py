from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QLineEdit, QTextEdit, QFileDialog, 
                             QMessageBox, QScrollArea, QFrame, QGridLayout,
                             QComboBox, QSlider, QProgressBar, QListWidget,
                             QListWidgetItem, QTreeWidget, QTreeWidgetItem,
                             QHeaderView, QInputDialog, QColorDialog, QFontDialog,
                             QTabWidget, QApplication)
from PyQt5.QtCore import Qt, QTimer, QPoint, QUrl, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QPixmap, QScreen, QImage, QColor, QFont, QIcon, QDesktopServices
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
import hashlib
import os
import time
import requests
import json
import subprocess
import threading
import datetime
from datetime import datetime as dt

class ScreenshotWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("截图工具")
        self.setGeometry(100, 100, 400, 300)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        info = QLabel("点击开始截图按钮，然后选择屏幕区域进行截图")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        self.result_label = QLabel("截图将显示在这里")
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_label.setStyleSheet("""
            QLabel {
                background: rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                padding: 50px;
                min-height: 150px;
            }
        """)
        layout.addWidget(self.result_label)
        
        btn_layout = QHBoxLayout()
        
        self.screenshot_btn = QPushButton("📸 开始截图")
        self.screenshot_btn.clicked.connect(self.take_screenshot)
        btn_layout.addWidget(self.screenshot_btn)
        
        self.save_btn = QPushButton("💾 保存图片")
        self.save_btn.clicked.connect(self.save_screenshot)
        self.save_btn.setEnabled(False)
        btn_layout.addWidget(self.save_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        
        self.screenshot_pixmap = None
        
    def take_screenshot(self):
        self.hide()
        QTimer.singleShot(200, self.capture_screen)
        
    def capture_screen(self):
        screen = self.screen()
        if screen:
            self.screenshot_pixmap = screen.grabWindow(0)
            self.result_label.setPixmap(self.screenshot_pixmap.scaled(
                self.result_label.size(), Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
            self.save_btn.setEnabled(True)
        self.show()
        
    def save_screenshot(self):
        if self.screenshot_pixmap:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存截图", "", "PNG图片 (*.png);;JPEG图片 (*.jpg)"
            )
            if file_path:
                self.screenshot_pixmap.save(file_path)
                QMessageBox.information(self, "成功", "截图已保存!")


class ColorPickerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("取色器")
        self.setGeometry(100, 100, 350, 250)
        self.current_color = "#000000"
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        self.color_preview = QFrame()
        self.color_preview.setFixedHeight(80)
        self.color_preview.setStyleSheet(f"background-color: {self.current_color}; border-radius: 8px;")
        layout.addWidget(self.color_preview)
        
        self.hex_label = QLabel(f"HEX: {self.current_color}")
        self.hex_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.hex_label)
        
        self.rgb_label = QLabel("RGB: 0, 0, 0")
        self.rgb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.rgb_label)
        
        self.pick_btn = QPushButton("🎯 从屏幕取色")
        self.pick_btn.clicked.connect(self.pick_color)
        layout.addWidget(self.pick_btn)
        
        self.copy_btn = QPushButton("📋 复制颜色代码")
        self.copy_btn.clicked.connect(self.copy_color)
        layout.addWidget(self.copy_btn)
        
        self.setLayout(layout)
        
    def pick_color(self):
        self.hide()
        QTimer.singleShot(300, self.capture_color)
        
    def capture_color(self):
        screen = self.screen()
        if screen:
            pixmap = screen.grabWindow(0)
            img = pixmap.toImage()
            center = QPoint(img.width() // 2, img.height() // 2)
            color = QColor(img.pixel(center))
            
            self.current_color = color.name()
            self.color_preview.setStyleSheet(f"background-color: {self.current_color}; border-radius: 8px;")
            self.hex_label.setText(f"HEX: {self.current_color}")
            self.rgb_label.setText(f"RGB: {color.red()}, {color.green()}, {color.blue()}")
        self.show()
        
    def copy_color(self):
        clipboard = self.app.clipboard()
        clipboard.setText(self.current_color)
        QMessageBox.information(self, "已复制", f"颜色代码 {self.current_color} 已复制到剪贴板")


class HashCalculatorWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("文件哈希计算器")
        self.setGeometry(100, 100, 500, 400)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        file_layout = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("选择文件...")
        file_layout.addWidget(self.file_path_edit)
        
        self.browse_btn = QPushButton("📁 浏览")
        self.browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(self.browse_btn)
        layout.addLayout(file_layout)
        
        self.calc_btn = QPushButton("🔢 计算哈希值")
        self.calc_btn.clicked.connect(self.calculate_hash)
        layout.addWidget(self.calc_btn)
        
        results_label = QLabel("哈希结果:")
        layout.addWidget(results_label)
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet("""
            QTextEdit {
                background: rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                padding: 10px;
            }
        """)
        layout.addWidget(self.result_text)
        
        self.setLayout(layout)
        
    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择文件")
        if file_path:
            self.file_path_edit.setText(file_path)
            
    def calculate_hash(self):
        file_path = self.file_path_edit.text()
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "错误", "请选择有效的文件")
            return
            
        self.result_text.append("正在计算...")
        
        try:
            results = []
            
            md5 = hashlib.md5()
            sha1 = hashlib.sha1()
            sha256 = hashlib.sha256()
            
            with open(file_path, 'rb') as f:
                while chunk := f.read(8192):
                    md5.update(chunk)
                    sha1.update(chunk)
                    sha256.update(chunk)
            
            results.append(f"MD5:    {md5.hexdigest()}")
            results.append(f"SHA1:   {sha1.hexdigest()}")
            results.append(f"SHA256: {sha256.hexdigest()}")
            
            self.result_text.setText("\n".join(results))
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"计算失败: {str(e)}")


class ToolsCollectionWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("工具集")
        self.setGeometry(100, 100, 600, 450)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        title = QLabel("常用工具集")
        title.setFont(QFont("Microsoft YaHei UI", 18, QFont.Bold))
        title.setStyleSheet("color: white; padding: 10px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
        """)
        
        scroll_content = QWidget()
        grid = QGridLayout()
        grid.setSpacing(15)
        
        tools = [
            ("📸 截图工具", "快速截取屏幕区域", self.open_screenshot),
            ("🎯 取色器", "从屏幕获取颜色代码", self.open_color_picker),
            ("🔢 哈希计算器", "计算文件MD5/SHA1/SHA256", self.open_hash_calculator),
            ("📹 屏幕录制", "录制屏幕为视频文件", self.open_screen_recorder),
            ("📁 文件管理器", "浏览和管理本地文件", self.open_file_manager),
            ("⏱️ 计时器", "倒计时和秒表功能", self.open_timer),
            ("🔳 二维码", "生成和扫描二维码", self.open_qrcode),
            ("🌐 翻译工具", "多语言翻译功能", self.open_translator),
        ]
        
        for i, (name, desc, func) in enumerate(tools):
            card = self.create_tool_card(name, desc, func)
            row = i // 2
            col = i % 2
            grid.addWidget(card, row, col)
        
        scroll_content.setLayout(grid)
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        self.setLayout(layout)
        
    def create_tool_card(self, name, desc, func):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: rgba(0, 0, 0, 0.5);
                border: 1px solid rgba(0, 212, 255, 0.3);
                border-radius: 12px;
                padding: 20px;
            }
            QFrame:hover {
                background: rgba(0, 50, 80, 0.6);
                border: 1px solid rgba(0, 212, 255, 0.6);
            }
        """)
        
        layout = QVBoxLayout()
        
        title = QLabel(name)
        title.setFont(QFont("Microsoft YaHei UI", 14, QFont.Bold))
        title.setStyleSheet("color: white;")
        layout.addWidget(title)
        
        description = QLabel(desc)
        description.setStyleSheet("color: rgba(255, 255, 255, 0.6);")
        layout.addWidget(description)
        
        btn = QPushButton("打开")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(func)
        btn.setStyleSheet("""
            QPushButton {
                background: rgba(0, 212, 255, 0.3);
                border: 1px solid rgba(0, 212, 255, 0.5);
                border-radius: 8px;
                padding: 8px;
                color: white;
            }
            QPushButton:hover {
                background: rgba(0, 212, 255, 0.5);
            }
        """)
        layout.addWidget(btn)
        
        card.setLayout(layout)
        return card
        
    def open_screenshot(self):
        self.screenshot_win = ScreenshotWindow()
        self.screenshot_win.show()
        
    def open_color_picker(self):
        self.color_picker = ColorPickerWindow()
        self.color_picker.app = self.window().app if hasattr(self.window(), 'app') else None
        self.color_picker.show()
        
    def open_hash_calculator(self):
        self.hash_win = HashCalculatorWindow()
        self.hash_win.show()
        
    def open_screen_recorder(self):
        self.recorder = ScreenRecorderWindow()
        self.recorder.show()
        
    def open_file_manager(self):
        self.file_mgr = FileManagerWindow()
        self.file_mgr.show()
        
    def open_timer(self):
        self.timer = TimerWindow()
        self.timer.show()
        
    def open_qrcode(self):
        self.qrcode = QRCodeWindow()
        self.qrcode.show()
        
    def open_translator(self):
        self.translator = TranslatorWindow()
        self.translator.show()


class ScreenRecorderWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("屏幕录制")
        self.setGeometry(100, 100, 450, 350)
        self.recording = False
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        info = QLabel("📹 屏幕录制工具\n支持录制全屏或指定区域")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setStyleSheet("color: white; font-size: 14px; padding: 20px;")
        layout.addWidget(info)
        
        self.status_label = QLabel("状态: 就绪")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #00d4ff; font-size: 16px; padding: 10px;")
        layout.addWidget(self.status_label)
        
        options_group = QFrame()
        options_layout = QVBoxLayout()
        
        self.fullscreen_cb = True
        btn_layout = QHBoxLayout()
        self.record_btn = QPushButton("🔴 开始录制")
        self.record_btn.setStyleSheet("""
            QPushButton {
                background: #ff4757;
                color: white;
                border: none;
                padding: 15px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background: #ff6b7a; }
        """)
        self.record_btn.clicked.connect(self.toggle_recording)
        btn_layout.addWidget(self.record_btn)
        
        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background: #57606f;
                color: white;
                border: none;
                padding: 15px;
                border-radius: 8px;
                font-size: 14px;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_recording)
        btn_layout.addWidget(self.stop_btn)
        
        options_layout.addLayout(btn_layout)
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        self.result_label = QLabel("")
        self.result_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_label.setWordWrap(True)
        layout.addWidget(self.result_label)
        
        self.setLayout(layout)
        
    def toggle_recording(self):
        if not self.recording:
            self.start_recording()
        else:
            self.stop_recording()
            
    def start_recording(self):
        try:
            output_file = os.path.join(os.path.expanduser("~"), "Videos", f"screen_record_{int(time.time())}.mp4")
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            cmd = [
                "ffmpeg", "-f", "gdigrab", "-framerate", "30", 
                "-i", "desktop", "-c:v", "libx264", "-preset", "fast",
                "-y", output_file
            ]
            
            self.record_thread = threading.Thread(target=self.run_recording, args=(cmd, output_file))
            self.record_thread.daemon = True
            self.record_thread.start()
            
            self.recording = True
            self.record_btn.setText("⏹ 录制中...")
            self.record_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.status_label.setText("状态: 录制中...")
            self.status_label.setStyleSheet("color: #ff4757; font-size: 16px;")
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法开始录制: {str(e)}\n\n请确保已安装ffmpeg")
            
    def run_recording(self, cmd, output_file):
        try:
            self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.process.wait()
        except Exception as e:
            print(f"录制出错: {e}")
            
    def stop_recording(self):
        if hasattr(self, 'process') and self.process:
            self.process.terminate()
            self.process.wait()
            
        self.recording = False
        self.record_btn.setText("🔴 开始录制")
        self.record_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("状态: 已完成")
        self.status_label.setStyleSheet("color: #2ed573; font-size: 16px;")
        
        output_file = os.path.join(os.path.expanduser("~"), "Videos", f"screen_record_{int(time.time())-10}.mp4")
        self.result_label.setText(f"✅ 录制完成！\n保存位置: {output_file}")


class FileManagerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("文件管理器")
        self.setGeometry(100, 100, 800, 500)
        self.current_path = os.path.expanduser("~")
        self.init_ui()
        self.refresh_tree()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        toolbar = QHBoxLayout()
        
        self.path_label = QLabel(self.current_path)
        self.path_label.setStyleSheet("color: white; padding: 5px;")
        toolbar.addWidget(self.path_label)
        
        self.back_btn = QPushButton("⬆️ 返回")
        self.back_btn.clicked.connect(self.go_back)
        toolbar.addWidget(self.back_btn)
        
        self.home_btn = QPushButton("🏠 主目录")
        self.home_btn.clicked.connect(self.go_home)
        toolbar.addWidget(self.home_btn)
        
        self.refresh_btn = QPushButton("🔄 刷新")
        self.refresh_btn.clicked.connect(self.refresh_tree)
        toolbar.addWidget(self.refresh_btn)
        
        layout.addLayout(toolbar)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["名称", "大小", "修改时间"])
        self.tree.setColumnWidth(0, 300)
        self.tree.setStyleSheet("""
            QTreeWidget {
                background: rgba(0, 0, 0, 0.3);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
            }
            QTreeWidget::item:hover { background: rgba(0, 212, 255, 0.2); }
        """)
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.tree)
        
        self.setLayout(layout)
        
    def refresh_tree(self):
        self.tree.clear()
        self.path_label.setText(self.current_path)
        
        try:
            items = []
            for entry in os.scandir(self.current_path):
                try:
                    item = QTreeWidgetItem()
                    item.setText(0, entry.name)
                    
                    if entry.is_dir():
                        item.setText(0, "📁 " + entry.name)
                        item.setData(0, 1, "dir")
                    else:
                        size = entry.stat().st_size
                        size_str = self.format_size(size)
                        item.setText(1, size_str)
                        item.setData(0, 1, "file")
                    
                    mtime = dt.fromtimestamp(entry.stat().st_mtime)
                    item.setText(2, mtime.strftime("%Y-%m-%d %H:%M"))
                    
                    items.append(item)
                except:
                    pass
                    
            items.sort(key=lambda x: (x.text(0).startswith("📁"), x.text(0).lower()))
            for item in items:
                self.tree.addTopLevelItem(item)
                
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法读取目录: {str(e)}")
            
    def format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
        
    def on_item_double_clicked(self, item, column):
        path = os.path.join(self.current_path, item.text(0).replace("📁 ", ""))
        if os.path.isdir(path):
            self.current_path = path
            self.refresh_tree()
            
    def go_back(self):
        parent = os.path.dirname(self.current_path)
        if parent and parent != self.current_path:
            self.current_path = parent
            self.refresh_tree()
            
    def go_home(self):
        self.current_path = os.path.expanduser("~")
        self.refresh_tree()


class TimerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("计时器")
        self.setGeometry(100, 100, 400, 450)
        self.mode = "timer"
        self.seconds = 0
        self.running = False
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        mode_layout = QHBoxLayout()
        self.timer_btn = QPushButton("⏱ 倒计时")
        self.timer_btn.setCheckable(True)
        self.timer_btn.setChecked(True)
        self.timer_btn.clicked.connect(lambda: self.set_mode("timer"))
        mode_layout.addWidget(self.timer_btn)
        
        self.stopwatch_btn = QPushButton("⏱️ 秒表")
        self.stopwatch_btn.setCheckable(True)
        self.stopwatch_btn.clicked.connect(lambda: self.set_mode("stopwatch"))
        mode_layout.addWidget(self.stopwatch_btn)
        
        layout.addLayout(mode_layout)
        
        self.time_display = QLabel("00:00:00")
        self.time_display.setFont(QFont("Consolas", 48, QFont.Bold))
        self.time_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_display.setStyleSheet("""
            color: #00d4ff;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 15px;
            padding: 30px;
        """)
        layout.addWidget(self.time_display)
        
        if self.mode == "timer":
            self.input_layout = QHBoxLayout()
            self.hour_input = QLineEdit("0")
            self.hour_input.setPlaceholderText("时")
            self.min_input = QLineEdit("0")
            self.min_input.setPlaceholderText("分")
            self.sec_input = QLineEdit("0")
            self.sec_input.setPlaceholderText("秒")
            
            for inp in [self.hour_input, self.min_input, self.sec_input]:
                inp.setStyleSheet("""
                    QLineEdit {
                        background: rgba(0, 0, 0, 0.5);
                        color: white;
                        border: 1px solid rgba(0, 212, 255, 0.3);
                        border-radius: 5px;
                        padding: 8px;
                        font-size: 16px;
                    }
                """)
                self.input_layout.addWidget(inp)
            layout.addLayout(self.input_layout)
        
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶️ 开始")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: #2ed573;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        self.start_btn.clicked.connect(self.start_timer)
        btn_layout.addWidget(self.start_btn)
        
        self.pause_btn = QPushButton("⏸ 暂停")
        self.pause_btn.setEnabled(False)
        self.pause_btn.setStyleSheet("""
            QPushButton {
                background: #ffa502;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-size: 16px;
            }
        """)
        self.pause_btn.clicked.connect(self.pause_timer)
        btn_layout.addWidget(self.pause_btn)
        
        self.reset_btn = QPushButton("🔄 重置")
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background: #57606f;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-size: 16px;
            }
        """)
        self.reset_btn.clicked.connect(self.reset_timer)
        btn_layout.addWidget(self.reset_btn)
        
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        
    def set_mode(self, mode):
        self.mode = mode
        self.timer.stop()
        self.running = False
        
        if mode == "timer":
            self.timer_btn.setChecked(True)
            self.stopwatch_btn.setChecked(False)
        else:
            self.timer_btn.setChecked(False)
            self.stopwatch_btn.setChecked(True)
            
        self.seconds = 0
        self.update_display()
        
    def start_timer(self):
        if not self.running:
            if self.mode == "timer" and self.seconds == 0:
                h = int(self.hour_input.text() or 0)
                m = int(self.min_input.text() or 0)
                s = int(self.sec_input.text() or 0)
                self.seconds = h * 3600 + m * 60 + s
                
            self.running = True
            self.timer.start(1000)
            self.start_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
            
    def pause_timer(self):
        if self.running:
            self.timer.stop()
            self.running = False
            self.start_btn.setEnabled(True)
            self.pause_btn.setEnabled(False)
            
    def reset_timer(self):
        self.timer.stop()
        self.running = False
        self.seconds = 0
        self.update_display()
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        
    def update_timer(self):
        if self.mode == "timer":
            if self.seconds > 0:
                self.seconds -= 1
            else:
                self.timer.stop()
                self.running = False
                QMessageBox.information(self, "时间到!", "倒计时结束！")
                self.start_btn.setEnabled(True)
                self.pause_btn.setEnabled(False)
        else:
            self.seconds += 1
            
        self.update_display()
        
    def update_display(self):
        h = self.seconds // 3600
        m = (self.seconds % 3600) // 60
        s = self.seconds % 60
        self.time_display.setText(f"{h:02d}:{m:02d}:{s:02d}")


class QRCodeWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("二维码工具")
        self.setGeometry(100, 100, 500, 550)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        title = QLabel("🔢 二维码工具")
        title.setFont(QFont("Microsoft YaHei UI", 16, QFont.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: white; padding: 10px;")
        layout.addWidget(title)
        
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                background: rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(0, 212, 255, 0.3);
                border-radius: 8px;
            }
        """)
        
        self.tab_widget.addTab(self.init_generate_tab(), "生成")
        self.tab_widget.addTab(self.init_scan_tab(), "扫描")
        
        layout.addWidget(self.tab_widget)
        
    def init_generate_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        self.content_input = QTextEdit()
        self.content_input.setPlaceholderText("输入文本、网址或内容...")
        self.content_input.setStyleSheet("""
            QTextEdit {
                background: rgba(0, 0, 0, 0.5);
                color: white;
                border: 1px solid rgba(0, 212, 255, 0.3);
                border-radius: 8px;
                padding: 10px;
                min-height: 100px;
            }
        """)
        layout.addWidget(self.content_input)
        
        btn_layout = QHBoxLayout()
        
        gen_btn = QPushButton("🔳 生成二维码")
        gen_btn.clicked.connect(self.generate_qr)
        gen_btn.setStyleSheet("""
            QPushButton {
                background: #00d4ff;
                color: black;
                border: none;
                padding: 12px;
                border-radius: 8px;
                font-weight: bold;
            }
        """)
        btn_layout.addWidget(gen_btn)
        
        copy_btn = QPushButton("📋 复制")
        copy_btn.clicked.connect(self.copy_qr)
        btn_layout.addWidget(copy_btn)
        
        layout.addLayout(btn_layout)
        
        self.qr_label = QLabel()
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_label.setStyleSheet("""
            background: white;
            border-radius: 10px;
            padding: 10px;
        """)
        layout.addWidget(self.qr_label)
        
        widget.setLayout(layout)
        return widget
        
    def init_scan_tab(self):
        widget = QWidget()
        layout = QVBoxLayout()
        
        info = QLabel("📷 扫描二维码\n\n请选择图片文件进行解析")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setStyleSheet("color: white; padding: 20px;")
        layout.addWidget(info)
        
        select_btn = QPushButton("📁 选择图片")
        select_btn.clicked.connect(self.scan_qr)
        select_btn.setStyleSheet("""
            QPushButton {
                background: #00d4ff;
                color: black;
                border: none;
                padding: 12px;
                border-radius: 8px;
                font-weight: bold;
            }
        """)
        layout.addWidget(select_btn)
        
        self.scan_result = QTextEdit()
        self.scan_result.setReadOnly(True)
        self.scan_result.setPlaceholderText("扫描结果将显示在这里...")
        self.scan_result.setStyleSheet("""
            QTextEdit {
                background: rgba(0, 0, 0, 0.5);
                color: white;
                border: 1px solid rgba(0, 212, 255, 0.3);
                border-radius: 8px;
                padding: 10px;
                min-height: 150px;
            }
        """)
        layout.addWidget(self.scan_result)
        
        widget.setLayout(layout)
        return widget
        
    def generate_qr(self):
        content = self.content_input.toPlainText()
        if not content:
            QMessageBox.warning(self, "警告", "请输入内容")
            return
            
        try:
            import qrcode
            from PIL import Image
            from io import BytesIO
            
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(content)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            
            pixmap = QPixmap()
            pixmap.loadFromData(buffer.getvalue())
            
            scaled_pixmap = pixmap.scaled(250, 250, Qt.AspectRatioMode.KeepAspectRatio)
            self.qr_label.setPixmap(scaled_pixmap)
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"生成失败: {str(e)}")
            
    def copy_qr(self):
        if self.qr_label.pixmap():
            clipboard = QApplication.clipboard()
            clipboard.setPixmap(self.qr_label.pixmap())
            QMessageBox.information(self, "成功", "二维码已复制到剪贴板")
            
    def scan_qr(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择二维码图片", "", "图片文件 (*.png *.jpg *.jpeg *.bmp)"
        )
        
        if not file_path:
            return
            
        try:
            from PIL import Image
            import pyzbar
            from pyzbar.pyzbar import decode
            
            img = Image.open(file_path)
            decoded = decode(img)
            
            if decoded:
                result = decoded[0].data.decode("utf-8")
                self.scan_result.setPlainText(result)
            else:
                QMessageBox.warning(self, "未找到", "图片中未识别到二维码")
                
        except ImportError:
            QMessageBox.warning(self, "依赖缺失", "请安装 pyzbar: pip install pyzbar")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"扫描失败: {str(e)}")


class TranslatorWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("翻译工具")
        self.setGeometry(100, 100, 600, 500)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        title = QLabel("🌐 翻译工具")
        title.setFont(QFont("Microsoft YaHei UI", 16, QFont.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: white; padding: 10px;")
        layout.addWidget(title)
        
        lang_layout = QHBoxLayout()
        
        self.source_lang = QComboBox()
        self.source_lang.addItems(["自动检测", "中文", "英文", "日语", "韩语", "法语", "德语", "俄语", "西班牙语"])
        self.source_lang.setCurrentText("自动检测")
        lang_layout.addWidget(QLabel("源语言:"))
        lang_layout.addWidget(self.source_lang)
        
        self.target_lang = QComboBox()
        self.target_lang.addItems(["中文", "英文", "日语", "韩语", "法语", "德语", "俄语", "西班牙语"])
        self.target_lang.setCurrentText("中文")
        lang_layout.addWidget(QLabel("目标语言:"))
        lang_layout.addWidget(self.target_lang)
        
        layout.addLayout(lang_layout)
        
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("输入要翻译的文本...")
        self.input_text.setStyleSheet("""
            QTextEdit {
                background: rgba(0, 0, 0, 0.5);
                color: white;
                border: 1px solid rgba(0, 212, 255, 0.3);
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
            }
        """)
        layout.addWidget(self.input_text)
        
        btn_layout = QHBoxLayout()
        
        self.translate_btn = QPushButton("🔄 翻译")
        self.translate_btn.clicked.connect(self.translate)
        self.translate_btn.setStyleSheet("""
            QPushButton {
                background: #00d4ff;
                color: black;
                border: none;
                padding: 12px 30px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
            }
        """)
        btn_layout.addWidget(self.translate_btn)
        
        clear_btn = QPushButton("🗑️ 清空")
        clear_btn.clicked.connect(lambda: (self.input_text.clear(), self.output_text.clear()))
        clear_btn.setStyleSheet("""
            QPushButton {
                background: #57606f;
                color: white;
                border: none;
                padding: 12px;
                border-radius: 8px;
            }
        """)
        btn_layout.addWidget(clear_btn)
        
        layout.addLayout(btn_layout)
        
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setPlaceholderText("翻译结果...")
        self.output_text.setStyleSheet("""
            QTextEdit {
                background: rgba(0, 0, 0, 0.5);
                color: white;
                border: 1px solid rgba(0, 212, 255, 0.3);
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
            }
        """)
        layout.addWidget(self.output_text)
        
        self.setLayout(layout)
        
    def translate(self):
        text = self.input_text.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "警告", "请输入要翻译的文本")
            return
            
        source = self.source_lang.currentText()
        target = self.target_lang.currentText()
        
        lang_map = {
            "中文": "zh", "英文": "en", "日语": "ja", "韩语": "ko",
            "法语": "fr", "德语": "de", "俄语": "ru", "西班牙语": "es",
            "自动检测": "auto"
        }
        
        from_lang = lang_map.get(source, "auto")
        to_lang = lang_map.get(target, "zh")
        
        try:
            url = "https://translate.googleapis.com/translate_a/single"
            params = {
                "client": "gtx",
                "sl": from_lang,
                "tl": to_lang,
                "dt": "t",
                "q": text
            }
            
            response = requests.get(url, params=params, timeout=10)
            result = response.json()
            
            translated = "".join([item[0] for item in result[0] if item[0]])
            self.output_text.setPlainText(translated)
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"翻译失败: {str(e)}")
