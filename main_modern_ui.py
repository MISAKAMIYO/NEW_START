"""
RAILGUN - 现代化UI入口程序
保留main.py所有核心功能，只优化UI为深色科技风格
"""

import sys
import os
import ctypes
import threading
import logging
import webbrowser
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QFrame, QGridLayout,
                             QLineEdit, QGraphicsDropShadowEffect, QMessageBox,
                             QShortcut, QTextEdit, QDialog)
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QFont, QKeySequence, QColor, QPainter, QLinearGradient, QPalette, QBrush, QPixmap
from settings_manager import ConfigManager


def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_PATH = get_base_path()

try:
    from WEBSITE.api_routes import app as api_app
    API_APP_AVAILABLE = True
except ImportError:
    API_APP_AVAILABLE = False


class RemoteControlServer:
    def __init__(self, main_window, port=5000):
        self.main_window = main_window
        self.port = port
        self.app = api_app
        self.server_thread = None
        self.running = False
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("RemoteServer")

    def start(self):
        if self.running:
            return
        if not API_APP_AVAILABLE:
            return

        def run_server():
            try:
                self.logger.info(f"启动远程控制服务器，端口: {self.port}")
                self.app.run(host='0.0.0.0', port=self.port, threaded=True)
            except Exception as e:
                self.logger.error(f"服务器启动失败: {str(e)}")

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        self.running = True
        self.logger.info("服务器已启动")


class NeonButton(QPushButton):
    """霓虹效果按钮"""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(55)
        self.setFont(QFont("Microsoft YaHei UI", 10))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(0, 153, 255, 0.3), stop:1 rgba(204, 102, 255, 0.3));
                color: #ffffff;
                border: 1px solid rgba(0, 212, 255, 0.5);
                border-radius: 14px;
                padding: 14px 20px;
                text-align: left;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(0, 180, 255, 0.5), stop:1 rgba(220, 120, 255, 0.5));
                border: 1px solid #00d4ff;
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(0, 100, 200, 0.6), stop:1 rgba(180, 80, 220, 0.6));
            }
        """)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 212, 255, 80))
        shadow.setOffset(0, 0)
        self.setGraphicsEffect(shadow)


class ModernIconButton(QPushButton):
    """现代化图标按钮"""
    def __init__(self, icon, tooltip="", parent=None):
        super().__init__(icon, parent)
        self.setFixedSize(40, 40)
        if tooltip:
            self.setToolTip(tooltip)
        self.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 20px;
                font-size: 16px;
                color: white;
            }
            QPushButton:hover {
                background: rgba(0, 212, 255, 0.2);
                border: 1px solid rgba(0, 212, 255, 0.5);
            }
        """)


class GradientTitleLabel(QLabel):
    """渐变标题标签"""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFont(QFont("Microsoft YaHei UI", 18, QFont.Bold))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                color: #ffffff;
                padding: 15px;
                background: transparent;
            }
        """)
        self.setFixedHeight(60)
        
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 212, 255, 150))
        shadow.setOffset(0, 0)
        self.setGraphicsEffect(shadow)

    def paintEvent(self, event):
        painter = QPainter(self)
        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0, QColor("#0099FF"))
        gradient.setColorAt(1, QColor("#CC66FF"))
        
        painter.setPen(QColor("#FFFFFF"))
        painter.setFont(self.font())
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text())


class ModernMainWindow(QMainWindow):
    """RAILGUN 现代风格主窗口 - 保留所有原有功能"""
    
    def __init__(self, config: ConfigManager):
        super().__init__()
        self.config = config
        self.setWindowTitle("RAILGUN 多功能桌面应用")
        self.setWindowFlags(Qt.FramelessWindowHint)
        
        self.load_window_state()
        self.setup_ui()
        
        # 加载保存的背景图片
        self.load_background_image()
        
        self.remote_server = RemoteControlServer(self, 5000)
        try:
            self.remote_server.start()
            print("[主窗口] 远程控制服务器已启动: http://localhost:5000")
        except Exception as e:
            print(f"[主窗口] 启动远程控制服务器失败: {e}")
        
        self.forum_server = None
        self.code_host_server = None
        

        
        self.setup_shortcuts()

    def load_window_state(self):
        """加载窗口状态"""
        width = self.config.get_config('window.width') or 1200
        height = self.config.get_config('window.height') or 800
        x = self.config.get_config('window.x') or 100
        y = self.config.get_config('window.y') or 100
        self.setGeometry(x, y, width, height)

    def save_window_state(self):
        """保存窗口状态"""
        geometry = self.geometry()
        self.config.set_config('window.width', geometry.width())
        self.config.set_config('window.height', geometry.height())
        self.config.set_config('window.x', geometry.x())
        self.config.set_config('window.y', geometry.y())

    def setup_ui(self):
        """设置UI"""
        self.setStyleSheet("""
            QMainWindow {
                background: transparent;
            }
        """)
        
        central_widget = QWidget()
        central_widget.setStyleSheet("""
            QWidget {
                background: transparent;
            }
        """)
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.content_widget = QWidget()
        self.content_widget.setObjectName("contentWidget")
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(30, 25, 30, 25)
        content_layout.setSpacing(20)

        top_bar = self.create_top_bar()
        content_layout.addWidget(top_bar)

        recent_frame = self.create_recent_frame()
        content_layout.addWidget(recent_frame)

        content_label = QLabel("选择功能")
        content_label.setFont(QFont("Microsoft YaHei UI", 13))
        content_label.setStyleSheet("color: rgba(255, 255, 255, 0.6); padding-left: 5px;")
        content_layout.addWidget(content_label)

        grid_layout = self.create_function_buttons()
        content_layout.addLayout(grid_layout)

        content_layout.addStretch()

        footer = self.create_footer()
        content_layout.addWidget(footer)

        self.content_widget.setLayout(content_layout)
        main_layout.addWidget(self.content_widget)

        central_widget.setLayout(main_layout)

    def create_top_bar(self):
        """创建顶部导航栏"""
        top_bar = QFrame()
        top_bar.setStyleSheet("""
            QFrame {
                background: transparent;
            }
        """)
        top_bar_layout = QHBoxLayout()
        top_bar_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("RAILGUN")
        title_label.setFont(QFont("Microsoft YaHei UI", 26, QFont.Bold))
        title_label.setStyleSheet("""
            color: #ffffff;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #0099FF, stop:1 #CC66FF);
            padding: 8px 25px;
            border-radius: 12px;
        """)
        
        title_shadow = QGraphicsDropShadowEffect()
        title_shadow.setBlurRadius(15)
        title_shadow.setColor(QColor(204, 102, 255))
        title_shadow.setOffset(0, 0)
        title_label.setGraphicsEffect(title_shadow)
        
        top_bar_layout.addWidget(title_label)
        top_bar_layout.addStretch()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 搜索功能...")
        self.search_box.setFixedWidth(220)
        self.search_box.setStyleSheet("""
            QLineEdit {
                background: rgba(30, 30, 30, 0.9);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 20px;
                padding: 8px 16px;
                color: white;
                font-size: 13px;
            }
            QLineEdit::placeholder {
                color: rgba(255, 255, 255, 0.5);
            }
            QLineEdit:focus {
                border: 1px solid rgba(0, 212, 255, 0.8);
                background: rgba(0, 212, 255, 0.1);
            }
        """)
        self.search_box.textChanged.connect(self.on_search_changed)
        top_bar_layout.addWidget(self.search_box)

        theme_btn = ModernIconButton("🌙", "切换主题")
        theme_btn.clicked.connect(self.toggle_theme)

        settings_btn = ModernIconButton("🖼️", "设置背景")
        settings_btn.clicked.connect(self.change_entry_background)

        backup_btn = ModernIconButton("💾", "备份数据")
        backup_btn.clicked.connect(self.backup_data)

        top_bar_layout.addWidget(theme_btn)
        top_bar_layout.addWidget(settings_btn)
        top_bar_layout.addWidget(backup_btn)
        
        top_bar_layout.addSpacing(10)
        
        min_btn = QPushButton("─")
        min_btn.setFixedSize(40, 32)
        min_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #fff;
                border: none;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
            }
        """)
        min_btn.clicked.connect(self.showMinimized)
        
        max_btn = QPushButton("□")
        max_btn.setFixedSize(40, 32)
        max_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #fff;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
            }
        """)
        max_btn.clicked.connect(self.toggle_maximize)
        
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(40, 32)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #fff;
                border: none;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #e81123;
                color: #fff;
            }
        """)
        close_btn.clicked.connect(self.close)
        
        top_bar_layout.addWidget(min_btn)
        top_bar_layout.addWidget(max_btn)
        top_bar_layout.addWidget(close_btn)

        top_bar.setLayout(top_bar_layout)
        return top_bar
    
    def toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragPosition = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.dragPosition)
            event.accept()

    def create_recent_frame(self):
        """创建最近使用区域"""
        recent_frame = QFrame()
        recent_frame.setStyleSheet("""
            QFrame {
                background: rgba(30, 30, 30, 0.6);
                border: 1px solid rgba(0, 212, 255, 0.2);
                border-radius: 16px;
                padding: 10px;
            }
        """)
        recent_layout = QHBoxLayout()
        recent_layout.setContentsMargins(15, 10, 15, 10)

        recent_title = QLabel("最近使用")
        recent_title.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
        recent_title.setStyleSheet("color: rgba(255, 255, 255, 0.7);")
        recent_layout.addWidget(recent_title)

        self.recent_label = QLabel("")
        recent_layout.addWidget(self.recent_label)
        recent_layout.addStretch()

        recent_frame.setLayout(recent_layout)
        self.update_recent_functions()
        return recent_frame

    def create_function_buttons(self):
        """创建功能按钮网格"""
        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)

        btn_configs = [
            ("🎵 音乐下载", self.open_music_download, "Ctrl+1"),
            ("📺 B站音乐下载", self.open_bilibili_music_download, "Ctrl+2"),
            ("🌐 多平台音乐", self.open_multi_platform_music, "Ctrl+M"),
            ("🤖 AI 智能对话", self.open_ai_chat, "Ctrl+3"),
            ("🎶 本地音乐播放器", self.open_music_player, "Ctrl+5"),
            ("🔄 格式转换工具", self.open_convert_tools, "Ctrl+4"),
            ("🎲 随机数工具", self.open_random_name, "Ctrl+6"),
            ("🔧 工具集", self.open_tools_collection, "Ctrl+T"),
            ("🎮 宏控制工具", self.open_macro, "Ctrl+7"),
            ("✏️ 屏幕画笔", self.open_screen_pen, "Ctrl+8"),
            ("🐍 贪吃蛇游戏", self.open_snakes, "Ctrl+9"),
            ("📱 扫码登录", self.open_qrcode_scanner, "Ctrl+Shift+S"),
            ("🔔 自动更新检测", self.open_auto_update, "Ctrl+Shift+U"),
        ]

        for idx, (btn_text, btn_handler, shortcut) in enumerate(btn_configs):
            btn = NeonButton(btn_text)
            btn.setToolTip(f"快捷键: {shortcut}")
            btn.clicked.connect(btn_handler)
            row = idx // 3
            col = idx % 3
            grid_layout.addWidget(btn, row, col)

        return grid_layout

    def create_footer(self):
        """创建底部栏"""
        footer = QLabel("💡 快捷键: Ctrl+数字键 | Ctrl+M 多平台音乐 | Ctrl+F 论坛 | Ctrl+G 代码托管 | Ctrl+Q 退出  ⚡ RAILGUN ⚡")
        footer.setFont(QFont("Microsoft YaHei UI", 9))
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("""
            color: rgba(255, 255, 255, 0.4); 
            padding: 12px;
            border-top: 1px solid rgba(0, 212, 255, 0.2);
            background: rgba(20, 20, 20, 0.5);
        """)
        return footer

    def setup_shortcuts(self):
        """设置快捷键"""
        shortcuts = [
            ("Ctrl+1", self.open_music_download),
            ("Ctrl+2", self.open_bilibili_music_download),
            ("Ctrl+3", self.open_ai_chat),
            ("Ctrl+4", self.open_convert_tools),
            ("Ctrl+5", self.open_music_player),
            ("Ctrl+6", self.open_random_name),
            ("Ctrl+7", self.open_macro),
            ("Ctrl+8", self.open_screen_pen),
            ("Ctrl+9", self.open_snakes),
            ("Ctrl+F", self.open_forum),
            ("Ctrl+G", self.open_code_host),
            ("Ctrl+,", self.change_entry_background),
            ("Ctrl+Q", self.close),
        ]
        
        for key, func in shortcuts:
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(func)

    def record_recent_function(self, func_name):
        """记录最近使用的功能"""
        print(f"[主窗口] 打开功能: {func_name}")
        
    def update_recent_functions(self):
        """更新最近使用显示"""
        self.recent_label.setText("🎵 音乐下载")
        self.recent_label.setStyleSheet("color: rgba(255, 255, 255, 0.5);")

    def on_search_changed(self, text):
        """搜索框内容变化"""
        print(f"[搜索] {text}")

    def toggle_theme(self):
        """切换主题"""
        print("[主窗口] 切换主题")

    def change_entry_background(self):
        """允许用户选择主入口背景图片并保存到配置"""
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择背景图片", 
            self.config.get_config("paths.data") or "", 
            "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            self.config.set_config("ui.entry_background", file_path)
            try:
                self.apply_entry_background(file_path)
            except Exception as e:
                print(f"[错误] 应用背景失败: {e}")
            QMessageBox.information(self, "已保存", "主入口背景已更新。")

    def load_background_image(self):
        """加载背景图片"""
        entry_bg = self.config.get_config("ui.entry_background") or ""
        if entry_bg:
            self.apply_background_image(entry_bg)
    
    def apply_background_image(self, file_path: str):
        """使用QLabel显示背景图片"""
        try:
            if not hasattr(self, 'bg_label'):
                self.bg_label = QLabel(self)
                self.bg_label.setObjectName("bgLabel")
                self.bg_label.lower()
            
            pixmap = QPixmap(file_path)
            if pixmap.isNull():
                pixmap = QPixmap(os.path.normpath(file_path))
            
            if not pixmap.isNull():
                size = self.size()
                scaled = pixmap.scaled(
                    size,
                    Qt.IgnoreAspectRatio,
                    Qt.SmoothTransformation
                )
                self.bg_label.setPixmap(scaled)
                self.bg_label.setGeometry(0, 0, size.width(), size.height())
                self.bg_label.lower()
                self.bg_label.stackUnder(self.centralWidget())
                print(f"[主窗口] 背景图片已加载: {file_path}")
            else:
                print(f"[错误] 无法加载图片: {file_path}")
        except Exception as e:
            print(f"[错误] 加载背景失败: {e}")
    
    def apply_entry_background(self, file_path: str) -> None:
        """应用背景图片"""
        self.config.set_config("ui.entry_background", file_path)
        self.apply_background_image(file_path)
        QMessageBox.information(self, "已保存", "主入口背景已更新。")

    def backup_data(self):
        """备份数据"""
        print("[主窗口] 备份数据")

    def open_music_download(self):
        """打开音乐下载模块"""
        self.record_recent_function("music_download")
        try:
            from Music_Download.main_music_download import MusicDownloadWindow
            self.md_window = MusicDownloadWindow()
            self.md_window.show()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开音乐下载: {e}")

    def open_bilibili_music_download(self):
        """打开B站音乐下载模块"""
        self.record_recent_function("bilibili_music_download")
        try:
            from Bilibili_Music_Download.main_bilibili_download import BilibiliMusicDownloadWindow
            self.bmd_window = BilibiliMusicDownloadWindow()
            self.bmd_window.show()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开B站音乐下载: {e}")

    def open_multi_platform_music(self):
        """打开多平台音乐下载模块"""
        self.record_recent_function("multi_platform_music")
        try:
            from Music_Download.multi_platform import MultiPlatformMusicWindow
            self.mpm_window = MultiPlatformMusicWindow()
            self.mpm_window.show()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开多平台音乐: {e}")

    def open_ai_chat(self):
        """打开AI聊天模块"""
        self.record_recent_function("ai_chat")
        try:
            from AI_Chat.main_ai_chat import AIChatWindow
            self.ac_window = AIChatWindow(self.config)
            self.ac_window.show()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开AI聊天: {e}")

    def open_convert_tools(self):
        """打开格式转换工具窗口"""
        self.record_recent_function("convert_tools")
        try:
            from Tools.Convert_Tools.main_convert import ConvertToolsWindow
            self.convert_window = ConvertToolsWindow(self.config)
            self.convert_window.show()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开格式转换工具: {e}")

    def open_music_player(self):
        """打开本地音乐播放器"""
        self.record_recent_function("music_player")
        try:
            from Music_Player.main_music_player import MusicPlayerWindow
            self.mp_window = MusicPlayerWindow()
            self.mp_window.show()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开本地音乐播放器: {e}")

    def open_random_name(self):
        """打开随机数工具"""
        self.record_recent_function("random_name")
        try:
            from Tools.RandomName.main_randomname import RandomNameWindow
            self.rn_window = RandomNameWindow()
            self.rn_window.show()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开随机数工具: {e}")

    def open_tools_collection(self):
        """打开工具集"""
        self.record_recent_function("tools_collection")
        try:
            from Tools.Tools_Collection.main_tools import ToolsCollectionWindow
            self.tools_window = ToolsCollectionWindow()
            self.tools_window.show()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法打开工具集: {e}")

    def open_macro(self):
        """打开宏控制工具"""
        self.record_recent_function("macro")
        try:
            import subprocess
            import os
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Macro", "macro.py")
            if os.path.exists(script_path):
                subprocess.Popen(["python", script_path])
            else:
                QMessageBox.warning(self, "错误", "未找到宏控制工具")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"启动失败: {e}")

    def open_screen_pen(self):
        """打开屏幕画笔"""
        self.record_recent_function("screen_pen")
        try:
            import subprocess
            import os
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Tools", "Screen_Pen", "main_screen_pen.py")
            if os.path.exists(script_path):
                subprocess.Popen(["python", script_path])
            else:
                QMessageBox.warning(self, "错误", "未找到屏幕画笔工具")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"启动失败: {e}")

    def open_snakes(self):
        """打开贪吃蛇游戏"""
        self.record_recent_function("snakes")
        try:
            import subprocess
            import os
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "GAMES", "SNAKES", "main_snakes.py")
            print(f"[贪吃蛇] 脚本路径: {script_path}")
            print(f"[贪吃蛇] 文件存在: {os.path.exists(script_path)}")
            if os.path.exists(script_path):
                subprocess.Popen(["python", script_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                QMessageBox.warning(self, "错误", "未找到贪吃蛇游戏")
        except Exception as e:
            print(f"[贪吃蛇] 错误: {e}")
            QMessageBox.warning(self, "错误", f"启动失败: {e}")
    
    def open_qrcode_scanner(self):
        """打开扫码登录功能"""
        self.record_recent_function("扫码登录")
        try:
            import subprocess
            import os
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saoma", "bilibili_qrcode.py")
            if os.path.exists(script_path):
                subprocess.Popen(["python", script_path, "--gui"])
            else:
                QMessageBox.warning(self, "错误", "未找到扫码模块")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"启动扫码失败: {e}")
    
    def open_auto_update(self):
        """打开自动更新检测功能"""
        self.record_recent_function("自动更新检测")
        self.show_auto_update_dialog()
    
    def show_auto_update_dialog(self):
        """显示自动更新检测对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("原神自动更新检测")
        dialog.setMinimumSize(500, 400)
        dialog.setModal(True)
        
        from PyQt5.QtCore import pyqtSignal, QObject
        
        class UpdateSignals(QObject):
            log_signal = pyqtSignal(str)
            status_signal = str
            finish_signal = pyqtSignal()
        
        layout = QVBoxLayout()
        
        title = QLabel("🎮 原神自动更新检测工具")
        title.setFont(QFont("Microsoft YaHei UI", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #00d4ff; padding: 10px;")
        layout.addWidget(title)
        
        status_label = QLabel("状态: 就绪")
        status_label.setStyleSheet("color: #00ff88; font-size: 12px; padding: 5px;")
        layout.addWidget(status_label)
        
        log_text = QTextEdit()
        log_text.setReadOnly(True)
        log_text.setMaximumHeight(200)
        log_text.setStyleSheet("""
            QTextEdit {
                background: rgba(0, 0, 0, 0.5);
                color: #00ff88;
                border: 1px solid #00d4ff;
                border-radius: 5px;
                padding: 10px;
                font-family: Consolas, monospace;
            }
        """)
        layout.addWidget(log_text)
        
        button_layout = QHBoxLayout()
        
        run_btn = QPushButton("🔍 立即检测")
        run_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00d4ff, stop:1 #00ff88);
                color: #000;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00ffaa, stop:1 #55ffaa);
            }
        """)
        
        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.1);
                color: #fff;
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 8px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.2);
            }
        """)
        
        button_layout.addWidget(run_btn)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        
        signals = UpdateSignals()
        signals.log_signal.connect(lambda msg: log_text.append(msg))
        signals.finish_signal.connect(lambda: run_btn.setEnabled(True))
        
        def run_detection():
            log_text.clear()
            status_label.setText("状态: 检测中...")
            run_btn.setEnabled(False)
            
            import threading
            
            def detect_thread():
                try:
                    import subprocess
                    import os
                    
                    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "autoupdata", "main.py")
                    if os.path.exists(script_path):
                        process = subprocess.Popen(
                            ["python", script_path, "-r"],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            cwd=os.path.dirname(script_path)
                        )
                        
                        for line in iter(process.stdout.readline, ''):
                            if line:
                                signals.log_signal.emit(line.strip())
                        
                        process.wait()
                        status_label.setText("状态: 检测完成 ✓")
                    else:
                        signals.log_signal.emit("[错误] 未找到自动更新检测脚本")
                        status_label.setText("状态: 文件未找到")
                except Exception as e:
                    signals.log_signal.emit(f"[错误] {e}")
                    status_label.setText("状态: 检测失败")
                finally:
                    signals.finish_signal.emit()
            
            threading.Thread(target=detect_thread, daemon=True).start()
        
        run_btn.clicked.connect(run_detection)
        close_btn.clicked.connect(dialog.close)
        
        dialog.show()
    
    def open_forum(self):
        """打开论坛"""
        self.record_recent_function("forum")
        try:
            if self.forum_server is None:
                self.forum_server = ForumServer(5001)
                success = self.forum_server.start()
                if success:
                    QMessageBox.information(self, "提示", "论坛服务器已启动")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法启动论坛: {e}")

    def open_code_host(self):
        """打开代码托管"""
        self.record_recent_function("code_host")
        try:
            if self.code_host_server is None:
                self.code_host_server = CodeHostServer(8088)
                success = self.code_host_server.start()
                if success:
                    QMessageBox.information(self, "提示", "代码托管服务器已启动")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法启动代码托管: {e}")

    def closeEvent(self, event):
        """关闭事件"""
        self.save_window_state()
        event.accept()

    def resizeEvent(self, event):
        """窗口大小改变时更新背景"""
        super().resizeEvent(event)
        if hasattr(self, 'bg_label') and self.bg_label and self.bg_label.pixmap():
            size = self.size()
            self.bg_label.setGeometry(0, 0, size.width(), size.height())
            pixmap = self.bg_label.pixmap().scaled(
                size,
                Qt.IgnoreAspectRatio,
                Qt.SmoothTransformation
            )
            self.bg_label.setPixmap(pixmap)


class ForumServer:
    def __init__(self, port=5001):
        self.port = port
        self.app = None
        self.socketio = None
        self.server_thread = None
        self.running = False

    def start(self):
        if self.running:
            return True
        try:
            from WEBSITE.forum.forum_backend import app as forum_app, socketio as forum_socketio
            self.app = forum_app
            self.socketio = forum_socketio
            
            def run_server():
                try:
                    self.socketio.run(self.app, host='0.0.0.0', port=self.port, debug=False, allow_unsafe_werkzeug=True)
                except Exception as e:
                    print(f"论坛服务器启动失败: {str(e)}")

            self.server_thread = threading.Thread(target=run_server, daemon=True)
            self.server_thread.start()
            self.running = True
            return True
        except Exception as e:
            print(f"加载论坛模块失败: {str(e)}")
            return False


class CodeHostServer:
    def __init__(self, port=8088):
        self.port = port
        self.app = None
        self.server_thread = None
        self.running = False

    def start(self):
        if self.running:
            return True
        try:
            from web.backend import app as web_app
            self.app = web_app
            
            def run_server():
                try:
                    self.app.run(host='0.0.0.0', port=self.port, debug=False, use_reloader=False)
                except Exception as e:
                    print(f"代码托管服务器启动失败: {str(e)}")

            self.server_thread = threading.Thread(target=run_server, daemon=True)
            self.server_thread.start()
            self.running = True
            return True
        except Exception as e:
            print(f"加载代码托管模块失败: {str(e)}")
            return False


class RAILGUNApplication:
    """RAILGUN 应用主入口类"""
    
    def __init__(self):
        os.environ['QT_MULTIMEDIA_PREFERRED_PLUGINS'] = 'windowsmediafoundation,directshow'
        self.app = QApplication(sys.argv)
        self.app.setStyle("Fusion")
        self.config = ConfigManager()
        self.main_window = ModernMainWindow(self.config)

    def run(self) -> int:
        self.main_window.show()
        return self.app.exec_()


def check_admin_privileges():
    """检查管理员权限"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def main():
    """程序入口"""
    print("=" * 50)
    print("启动 RAILGUN 现代化UI入口程序...")
    print("=" * 50)
    
    if not check_admin_privileges():
        print("警告: 未获取管理员权限，某些功能可能受限")
    
    try:
        railgun_app = RAILGUNApplication()
        sys.exit(railgun_app.run())
    except ImportError as e:
        error_msg = f"导入模块失败：{e}\n\n请检查依赖是否已安装：\npip install -r requirements.txt"
        print(f"[错误] {error_msg}")
        import traceback
        traceback.print_exc()
        try:
            QMessageBox.critical(None, "导入错误", error_msg)
        except:
            pass
        sys.exit(1)
    except Exception as e:
        error_msg = f"应用启动失败：{e}"
        print(f"[错误] {error_msg}")
        import traceback
        traceback.print_exc()
        try:
            dialog = QDialog()
            dialog.setWindowTitle("错误详情")
            dialog.setMinimumSize(600, 400)
            layout = QVBoxLayout()
            text_edit = QTextEdit()
            text_edit.setPlainText(traceback.format_exc())
            text_edit.setReadOnly(True)
            layout.addWidget(text_edit)
            dialog.setLayout(layout)
            dialog.exec_()
        except:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()