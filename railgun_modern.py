"""
RAILGUN - 现代化入口程序
保留main.py原有功能，使用现代深色科技风格UI
"""

import sys
import os
import ctypes
import json
import traceback
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QFrame, QStackedWidget,
                             QGraphicsDropShadowEffect, QMessageBox, QListWidget, 
                             QSlider, QProgressBar, QTextEdit, QDialog, QScrollArea,
                             QListWidgetItem, QLineEdit)
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QFont


class ConfigManager:
    """配置文件管理类"""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = os.path.join(self.get_base_path(), "settings.json")
        self.config_path = config_path
        self.default_config = {
            "window": {"width": 1400, "height": 900, "x": 100, "y": 100},
            "paths": {"data": "./Data", "download": "./Data/Downloads"},
            "features": {"ai_chat": True, "auto_update": False},
            "ui": {"theme": {"frame_bg": "#1A1A1A", "accent": "#0099FF", "text": "#FFFFFF"}}
        }
        self.config = self.load_config()
    
    def get_base_path(self):
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        return os.path.dirname(os.path.abspath(__file__))
    
    def load_config(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                self.save_config(self.default_config)
                return self.default_config.copy()
        except:
            return self.default_config.copy()
    
    def save_config(self, config=None):
        if config is None:
            config = self.config
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def get(self, key, default=None):
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def set(self, key, value):
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config or not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        self.save_config()


class NeonButton(QPushButton):
    """霓虹效果按钮"""
    
    def __init__(self, text="", gradient_start="#0099FF", gradient_end="#CC66FF", parent=None):
        super().__init__(text, parent)
        self.gradient_start = gradient_start
        self.gradient_end = gradient_end
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(40)
        self.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {gradient_start}, stop:1 {gradient_end});
                border: none;
                border-radius: 20px;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 8px 24px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {gradient_start}, stop:1 {gradient_end});
                border: 2px solid white;
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {gradient_end}, stop:1 {gradient_start});
            }}
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(gradient_end))
        shadow.setOffset(0, 0)
        self.setGraphicsEffect(shadow)


class FunctionCard(QFrame):
    """功能卡片组件"""
    clicked = pyqtSignal(str)
    
    def __init__(self, title="", icon="", func_name="", desc="", 
                 gradient_start="#0099FF", gradient_end="#CC66FF", parent=None):
        super().__init__(parent)
        self.func_name = func_name
        self.setFixedHeight(100)
        self.setCursor(Qt.PointingHandCursor)
        
        self.setStyleSheet(f"""
            QFrame {{
                background: rgba(30, 30, 30, 0.95);
                border: 2px solid {gradient_end};
                border-radius: 12px;
            }}
            QFrame:hover {{
                background: rgba(40, 40, 40, 0.95);
                border: 2px solid {gradient_start};
            }}
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(gradient_end))
        shadow.setOffset(0, 0)
        self.setGraphicsEffect(shadow)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(20, 15, 20, 15)
        
        icon_label = QLabel(icon)
        icon_label.setFixedSize(60, 60)
        icon_label.setStyleSheet(f"""
            QLabel {{
                font-size: 32px;
                background: rgba(0, 0, 0, 0.3);
                border-radius: 12px;
                border: 2px solid {gradient_end};
            }}
        """)
        icon_label.setAlignment(Qt.AlignCenter)
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(5)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 18px;
                font-weight: bold;
                background: transparent;
            }
        """)
        
        desc_label = QLabel(desc)
        desc_label.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 12px;
                background: transparent;
            }
        """)
        
        text_layout.addWidget(title_label)
        text_layout.addWidget(desc_label)
        text_layout.addStretch()
        
        arrow_label = QLabel("→")
        arrow_label.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 24px;
                background: transparent;
            }
        """)
        
        layout.addWidget(icon_label)
        layout.addLayout(text_layout)
        layout.addStretch()
        layout.addWidget(arrow_label)
        
        self.setLayout(layout)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            print(f"[功能卡片] 点击: {self.func_name}")
            self.clicked.emit(self.func_name)
        super().mousePressEvent(event)
    
    def enterEvent(self, event):
        self.animate_scale(1.02)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self.animate_scale(1.0)
        super().leaveEvent(event)
    
    def animate_scale(self, scale):
        animation = QPropertyAnimation(self, b"geometry")
        animation.setDuration(150)
        animation.setEasingCurve(QEasingCurve.OutCubic)
        current = self.geometry()
        new_w = int(current.width() * scale)
        new_h = int(current.height() * scale)
        new_rect = current
        new_rect.setWidth(new_w)
        new_rect.setHeight(new_h)
        new_rect.moveCenter(current.center())
        animation.setStartValue(current)
        animation.setEndValue(new_rect)
        animation.start()


class MusicPlayerWidget(QWidget):
    """音乐播放器组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_song = None
        self.is_playing = False
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        title = QLabel("🎵 音乐播放器")
        title.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 24px;
                font-weight: bold;
            }
        """)
        
        control_layout = QHBoxLayout()
        
        self.play_btn = NeonButton("▶ 播放", "#0099FF", "#CC66FF")
        self.play_btn.clicked.connect(self.play_clicked)
        
        self.pause_btn = NeonButton("⏸ 暂停", "#FF9900", "#FF6600")
        self.pause_btn.clicked.connect(self.pause_clicked)
        
        self.stop_btn = NeonButton("⏹ 停止", "#666666", "#444444")
        self.stop_btn.clicked.connect(self.stop_clicked)
        
        control_layout.addStretch()
        control_layout.addWidget(self.play_btn)
        control_layout.addWidget(self.pause_btn)
        control_layout.addWidget(self.stop_btn)
        control_layout.addStretch()
        
        self.song_list = QListWidget()
        self.song_list.setStyleSheet("""
            QListWidget {
                background: rgba(20, 20, 20, 0.9);
                border: 1px solid #333333;
                border-radius: 8px;
                color: white;
                padding: 10px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #333333;
            }
            QListWidget::item:selected {
                background: rgba(0, 153, 255, 0.3);
            }
        """)
        
        songs = ["Only My Railgun - fripSide", "Moon Halo - 茶理理", 
                 "TruE - 茶理理", "Umbrella - 茶理理"]
        self.song_list.addItems(songs)
        
        volume_layout = QHBoxLayout()
        volume_label = QLabel("🔊 音量:")
        volume_label.setStyleSheet("color: white;")
        
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 8px;
                background: #333333;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                width: 16px;
                margin: -4px 0;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0099FF, stop:1 #CC66FF);
                border-radius: 8px;
            }
        """)
        
        volume_layout.addWidget(volume_label)
        volume_layout.addWidget(self.volume_slider)
        
        layout.addWidget(title)
        layout.addLayout(control_layout)
        layout.addWidget(self.song_list)
        layout.addLayout(volume_layout)
        
        self.setLayout(layout)
    
    def play_clicked(self):
        item = self.song_list.currentItem()
        if item:
            print(f"[音乐] 播放: {item.text()}")
            QMessageBox.information(self, "播放", f"正在播放: {item.text()}")
            self.is_playing = True
        else:
            print("[音乐] 请先选择歌曲")
            QMessageBox.warning(self, "提示", "请先选择一首歌曲")
    
    def pause_clicked(self):
        print("[音乐] 暂停")
        QMessageBox.information(self, "暂停", "音乐已暂停")
    
    def stop_clicked(self):
        print("[音乐] 停止")
        QMessageBox.information(self, "停止", "音乐已停止")


class MusicDownloadWidget(QWidget):
    """音乐下载组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        title = QLabel("📥 音乐下载")
        title.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 24px;
                font-weight: bold;
            }
        """)
        
        search_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入歌曲名称搜索...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background: rgba(30, 30, 30, 0.9);
                border: 2px solid #333333;
                border-radius: 8px;
                color: white;
                padding: 10px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #0099FF;
            }
        """)
        
        self.search_btn = NeonButton("🔍 搜索", "#0099FF", "#CC66FF")
        self.search_btn.clicked.connect(self.search_clicked)
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_btn)
        
        self.result_list = QListWidget()
        self.result_list.setStyleSheet("""
            QListWidget {
                background: rgba(20, 20, 20, 0.9);
                border: 1px solid #333333;
                border-radius: 8px;
                color: white;
                padding: 10px;
            }
            QListWidget::item {
                padding: 12px;
                border-bottom: 1px solid #333333;
            }
        """)
        
        download_layout = QHBoxLayout()
        
        self.download_btn = NeonButton("⬇ 下载", "#00CC66", "#00FF88")
        self.download_btn.clicked.connect(self.download_clicked)
        
        download_layout.addStretch()
        download_layout.addWidget(self.download_btn)
        
        layout.addWidget(title)
        layout.addLayout(search_layout)
        layout.addWidget(self.result_list)
        layout.addLayout(download_layout)
        
        self.setLayout(layout)
    
    def search_clicked(self):
        keyword = self.search_input.text().strip()
        if keyword:
            print(f"[下载] 搜索: {keyword}")
            self.result_list.clear()
            results = [
                f"{keyword} - 歌曲1",
                f"{keyword} - 歌曲2",
                f"{keyword} - 歌曲3"
            ]
            self.result_list.addItems(results)
            QMessageBox.information(self, "搜索", f"找到 {len(results)} 个结果")
        else:
            QMessageBox.warning(self, "提示", "请输入搜索关键词")
    
    def download_clicked(self):
        item = self.result_list.currentItem()
        if item:
            print(f"[下载] 下载: {item.text()}")
            QMessageBox.information(self, "下载", f"开始下载: {item.text()}")
        else:
            QMessageBox.warning(self, "提示", "请先选择要下载的歌曲")


class AIChatWidget(QWidget):
    """AI聊天组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        
        title = QLabel("🤖 AI 助手")
        title.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 24px;
                font-weight: bold;
            }
        """)
        
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background: rgba(20, 20, 20, 0.9);
                border: 1px solid #333333;
                border-radius: 8px;
                color: white;
                padding: 10px;
                font-size: 14px;
            }
        """)
        
        self.chat_display.setHtml("""
            <div style="color: #00CC66; margin: 10px;">
                <b>🤖 AI助手:</b> 您好！我是RAILGUN AI助手，可以帮您解答问题、聊天互动。<br><br>
                请在下方输入您的问题...
            </div>
        """)
        
        input_layout = QHBoxLayout()
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("输入消息...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                background: rgba(30, 30, 30, 0.9);
                border: 2px solid #333333;
                border-radius: 8px;
                color: white;
                padding: 10px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #CC66FF;
            }
        """)
        self.input_field.returnPressed.connect(self.send_message)
        
        self.send_btn = NeonButton("发送", "#CC66FF", "#0099FF")
        self.send_btn.clicked.connect(self.send_message)
        
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_btn)
        
        layout.addWidget(title)
        layout.addWidget(self.chat_display)
        layout.addLayout(input_layout)
        
        self.setLayout(layout)
    
    def send_message(self):
        message = self.input_field.text().strip()
        if message:
            print(f"[AI聊天] 用户: {message}")
            
            self.chat_display.append(f"""
                <div style="color: #0099FF; margin: 10px;">
                    <b>👤 您:</b> {message}
                </div>
            """)
            
            response = self.get_ai_response(message)
            
            self.chat_display.append(f"""
                <div style="color: #00CC66; margin: 10px;">
                    <b>🤖 AI助手:</b> {response}
                </div>
            """)
            
            self.input_field.clear()
    
    def get_ai_response(self, message):
        responses = {
            "你好": "您好！很高兴为您服务！有什么可以帮助您的吗？",
            "你是谁": "我是RAILGUN AI助手，可以帮您解答问题、聊天互动。",
            "帮助": "我可以帮您：1.回答问题 2.聊天互动 3.提供信息查询",
            "天气": "抱歉，我暂时无法获取实时天气信息。",
            "谢谢": "不客气！随时为您服务！"
        }
        
        message_lower = message.lower()
        for key, value in responses.items():
            if key in message_lower:
                return value
        
        return f"我收到您的消息了：'{message}'。请问还有什么可以帮助您的？"


class ToolsWidget(QWidget):
    """工具集合组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        title = QLabel("🛠️ 实用工具")
        title.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 24px;
                font-weight: bold;
            }
        """)
        
        tools_grid_layout = QHBoxLayout()
        tools_grid_layout.setSpacing(20)
        
        tools = [
            ("📷", "截图工具", self.screenshot_tool),
            ("🎨", "取色器", self.color_picker),
            ("🔄", "文件转换", self.file_convert),
            ("🎲", "随机生成", self.random_generate)
        ]
        
        for icon, name, func in tools:
            tool_btn = NeonButton(f"{icon} {name}", "#0099FF", "#CC66FF")
            tool_btn.clicked.connect(func)
            tools_grid_layout.addWidget(tool_btn)
        
        result_label = QLabel("👆 点击上方按钮使用工具")
        result_label.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 14px;
            }
        """)
        result_label.setAlignment(Qt.AlignCenter)
        self.result_label = result_label
        
        layout.addWidget(title)
        layout.addLayout(tools_grid_layout)
        layout.addWidget(self.result_label)
        layout.addStretch()
        
        self.setLayout(layout)
    
    def screenshot_tool(self):
        print("[工具] 截图工具")
        QMessageBox.information(self, "截图工具", "截图功能开发中...")
        self.result_label.setText("📷 截图工具已启动")
    
    def color_picker(self):
        print("[工具] 取色器")
        QMessageBox.information(self, "取色器", "取色功能开发中...")
        self.result_label.setText("🎨 取色器已启动")
    
    def file_convert(self):
        print("[工具] 文件转换")
        QMessageBox.information(self, "文件转换", "文件转换功能开发中...")
        self.result_label.setText("🔄 文件转换已启动")
    
    def random_generate(self):
        import random
        names = ["张三", "李四", "王五", "赵六", "钱七", "孙八", "周九", "吴十"]
        random_name = random.choice(names)
        print(f"[工具] 随机生成: {random_name}")
        QMessageBox.information(self, "随机生成", f"随机姓名: {random_name}")
        self.result_label.setText(f"🎲 随机生成: {random_name}")


class ModernEntryWindow(QMainWindow):
    """现代化入口程序主窗口"""
    
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.current_page = "welcome"
        
        self.setWindowTitle("RAILGUN - 多功能桌面应用")
        self.setGeometry(100, 100, 1400, 900)
        
        self.setStyleSheet("""
            QMainWindow {
                background: #1A1A1A;
            }
        """)
        
        self.setup_ui()
        
    def setup_ui(self):
        central_widget = QWidget()
        central_widget.setStyleSheet("""
            QWidget {
                background: #1A1A1A;
            }
        """)
        
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        left_panel = self.create_left_panel()
        main_layout.addWidget(left_panel)
        
        self.right_panel = self.create_right_panel()
        main_layout.addWidget(self.right_panel)
        
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        self.setWindowFlag(Qt.FramelessWindowHint)
    
    def create_left_panel(self):
        panel = QFrame()
        panel.setFixedWidth(320)
        panel.setStyleSheet("""
            QFrame {
                background: #151515;
                border-right: 2px solid #333333;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 30, 20, 30)
        layout.setSpacing(15)
        
        logo_label = QLabel("RAILGUN")
        logo_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 28px;
                font-weight: bold;
                padding: 20px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0099FF, stop:1 #CC66FF);
                border-radius: 12px;
            }
        """)
        logo_label.setAlignment(Qt.AlignCenter)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor("#CC66FF"))
        shadow.setOffset(0, 0)
        logo_label.setGraphicsEffect(shadow)
        
        cards = [
            ("🎵", "音乐模块", "music", "播放与下载音乐"),
            ("📥", "音乐下载", "download", "搜索下载高品质音乐"),
            ("🤖", "AI 助手", "ai", "智能对话与问答"),
            ("🛠️", "工具集合", "tools", "实用工具集合")
        ]
        
        for icon, title, func, desc in cards:
            card = FunctionCard(title, icon, func, desc, "#0099FF", "#CC66FF")
            card.clicked.connect(self.on_function_clicked)
            layout.addWidget(card)
        
        layout.addStretch()
        
        version_label = QLabel("v1.0.0 | 现代UI版本")
        version_label.setStyleSheet("""
            QLabel {
                color: #555555;
                font-size: 12px;
            }
        """)
        version_label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(version_label)
        
        panel.setLayout(layout)
        return panel
    
    def create_right_panel(self):
        panel = QWidget()
        panel.setStyleSheet("""
            QWidget {
                background: #1A1A1A;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.stacked_widget = QStackedWidget()
        
        welcome_page = self.create_welcome_page()
        self.stacked_widget.addWidget(welcome_page)
        
        music_page = MusicPlayerWidget()
        self.stacked_widget.addWidget(music_page)
        
        download_page = MusicDownloadWidget()
        self.stacked_widget.addWidget(download_page)
        
        ai_page = AIChatWidget()
        self.stacked_widget.addWidget(ai_page)
        
        tools_page = ToolsWidget()
        self.stacked_widget.addWidget(tools_page)
        
        layout.addWidget(self.stacked_widget)
        
        panel.setLayout(layout)
        return panel
    
    def create_welcome_page(self):
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(50, 50, 50, 50)
        
        welcome_label = QLabel("欢迎使用 RAILGUN")
        welcome_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 36px;
                font-weight: bold;
            }
        """)
        welcome_label.setAlignment(Qt.AlignCenter)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor("#CC66FF"))
        shadow.setOffset(0, 0)
        welcome_label.setGraphicsEffect(shadow)
        
        subtitle = QLabel("多功能桌面应用平台")
        subtitle.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 18px;
            }
        """)
        subtitle.setAlignment(Qt.AlignCenter)
        
        desc = QLabel("""
            <div style="color: #AAAAAA; font-size: 14px; line-height: 2;">
            • 🎵 音乐播放与下载<br>
            • 🤖 AI智能助手<br>
            • 🛠️ 实用工具集合<br>
            • 🎮 娱乐游戏功能<br>
            </div>
        """)
        desc.setAlignment(Qt.AlignCenter)
        
        layout.addStretch()
        layout.addWidget(welcome_label)
        layout.addWidget(subtitle)
        layout.addSpacing(30)
        layout.addWidget(desc)
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
    
    def on_function_clicked(self, func_name):
        print(f"[主窗口] 切换到: {func_name}")
        
        page_map = {
            "welcome": 0,
            "music": 1,
            "download": 2,
            "ai": 3,
            "tools": 4
        }
        
        page_index = page_map.get(func_name, 0)
        self.stacked_widget.setCurrentIndex(page_index)
        self.current_page = func_name
        
        print(f"[主窗口] 页面切换完成: {page_index}")


class RAILGUNApp:
    """RAILGUN 应用入口类"""
    
    def __init__(self):
        os.environ['QT_MULTIMEDIA_PREFERRED_PLUGINS'] = 'windowsmediafoundation,directshow'
        self.app = QApplication(sys.argv)
        self.app.setStyle("Fusion")
        self.main_window = ModernEntryWindow()
    
    def run(self):
        self.main_window.show()
        return self.app.exec_()


def main():
    """程序入口"""
    print("=" * 50)
    print("启动 RAILGUN 现代化入口程序...")
    print("=" * 50)
    
    try:
        railgun_app = RAILGUNApp()
        sys.exit(railgun_app.run())
    except Exception as e:
        print(f"[错误] {e}")
        traceback.print_exc()
        QMessageBox.critical(None, "错误", f"应用启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()