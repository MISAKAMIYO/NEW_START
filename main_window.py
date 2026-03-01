import sys
import os
import threading
import logging
from pathlib import Path
from PyQt5.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel, QFrame, QGridLayout, QMessageBox, QLineEdit, QHBoxLayout
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPainter, QColor, QLinearGradient
from PyQt5.QtCore import Qt, QSize
from settings_manager import ConfigManager
import webbrowser
import time

sys.path.insert(0, os.path.dirname(__file__))

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_PATH = get_base_path()

from WEBSITE.api_routes import app as api_app


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


class ForumServer:
    def __init__(self, port=5001):
        self.port = port
        self.app = None
        self.socketio = None
        self.server_thread = None
        self.running = False
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("ForumServer")

    def start(self):
        if self.running:
            return

        try:
            from WEBSITE.forum.forum_backend import app as forum_app, socketio as forum_socketio
            self.app = forum_app
            self.socketio = forum_socketio
            
            def run_server():
                try:
                    self.logger.info(f"启动论坛服务器，端口: {self.port}")
                    self.socketio.run(self.app, host='0.0.0.0', port=self.port, debug=False, allow_unsafe_werkzeug=True)
                except Exception as e:
                    self.logger.error(f"论坛服务器启动失败: {str(e)}")

            self.server_thread = threading.Thread(target=run_server, daemon=True)
            self.server_thread.start()
            self.running = True
            self.logger.info("论坛服务器已启动")
            return True
        except Exception as e:
            self.logger.error(f"加载论坛模块失败: {str(e)}")
            return False

    def open_forum(self):
        if self.running:
            url = f"http://localhost:{self.port}"
            webbrowser.open(url)
            self.logger.info(f"已在浏览器中打开论坛: {url}")

class CodeHostServer:
    def __init__(self, port=8088):
        self.port = port
        self.app = None
        self.server_thread = None
        self.running = False
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("CodeHostServer")

    def start(self):
        if self.running:
            return

        try:
            from web.backend import app as web_app
            self.app = web_app
            
            def run_server():
                try:
                    self.logger.info(f"启动代码托管服务器，端口: {self.port}")
                    self.app.run(host='0.0.0.0', port=self.port, debug=False, use_reloader=False)
                except Exception as e:
                    self.logger.error(f"代码托管服务器启动失败: {str(e)}")

            self.server_thread = threading.Thread(target=run_server, daemon=True)
            self.server_thread.start()
            self.running = True
            self.logger.info("代码托管服务器已启动")
            return True
        except Exception as e:
            self.logger.error(f"加载代码托管模块失败: {str(e)}")
            return False

    def open_web(self):
        if self.running:
            url = f"http://localhost:{self.port}"
            webbrowser.open(url)
            self.logger.info(f"已在浏览器中打开代码托管: {url}")

class ModernButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(55)
        self.setFont(QFont("Microsoft YaHei UI", 10))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background: rgba(0, 0, 0, 0.5);
                color: #ffffff;
                border: 1px solid rgba(0, 212, 255, 0.4);
                border-radius: 14px;
                padding: 14px 20px;
                text-align: left;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(0, 50, 80, 0.6);
                border: 1px solid #00d4ff;
            }
            QPushButton:pressed {
                background: rgba(0, 80, 120, 0.7);
            }
        """)


class GradientHeader(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFont(QFont("Microsoft YaHei UI", 18, QFont.Bold))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                color: #2C3E50;
                padding: 20px;
            }
        """)
        self.setFixedHeight(80)

    def paintEvent(self, event):
        painter = QPainter(self)
        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0, QColor("#4A90D9"))
        gradient.setColorAt(1, QColor("#67B8F7"))
        painter.fillRect(self.rect(), gradient)
        
        painter.setPen(QColor("#FFFFFF"))
        painter.setFont(self.font())
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text())


class MainWindow(QMainWindow):
    """RAILGUN 主窗口类，负责界面布局与模块切换"""
    
    def __init__(self, config: ConfigManager):
        """
        初始化主窗口
        Args:
            config (ConfigManager): 配置管理实例
        """
        super().__init__()
        self.config = config
        self.setWindowTitle("RAILGUN 多功能桌面应用")
        
        self.load_window_state()
        
        self.apply_theme()

        entry_bg = self.config.get_config("ui.entry_background") or ""

        if entry_bg:
            file_url = entry_bg.replace('\\', '/')
            if not file_url.startswith('file:///') and not file_url.startswith('http'):
                if file_url.startswith('/'):
                    file_url = 'file://' + file_url
                else:
                    file_url = 'file:///' + file_url
            bg_css = f"background-image: url('{file_url}'); background-repeat: no-repeat; background-position: center; background-size: cover;"
        else:
            bg_css = ""

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.central_widget = central_widget

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(30, 25, 30, 25)
        content_layout.setSpacing(20)

        top_bar = QFrame()
        top_bar_layout = QHBoxLayout()
        top_bar_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("RAILGUN")
        title_label.setFont(QFont("Microsoft YaHei UI", 26, QFont.Bold))
        title_label.setStyleSheet("""
            color: #ffffff;
            background: rgba(0, 0, 0, 0.3);
            padding: 8px 20px;
            border-radius: 10px;
        """)
        top_bar_layout.addWidget(title_label)

        top_bar_layout.addStretch()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 搜索功能...")
        self.search_box.setFixedWidth(200)
        self.search_box.setStyleSheet("""
            QLineEdit {
                background: rgba(255, 255, 255, 0.08);
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
                border: 1px solid rgba(0, 212, 255, 0.6);
                background: rgba(0, 212, 255, 0.1);
            }
        """)
        self.search_box.textChanged.connect(self.on_search_changed)
        top_bar_layout.addWidget(self.search_box)

        theme_btn = QPushButton("🌙")
        theme_btn.setFixedSize(40, 40)
        theme_btn.setToolTip("切换主题")
        theme_btn.clicked.connect(self.toggle_theme)
        theme_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 20px;
                font-size: 16px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.15);
            }
        """)

        settings_btn = QPushButton("🖼️")
        settings_btn.setFixedSize(40, 40)
        settings_btn.setToolTip("设置背景")
        settings_btn.clicked.connect(self.change_entry_background)
        settings_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 20px;
                font-size: 16px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.15);
            }
        """)

        backup_btn = QPushButton("💾")
        backup_btn.setFixedSize(40, 40)
        backup_btn.setToolTip("备份数据")
        backup_btn.clicked.connect(self.backup_data)
        backup_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 20px;
                font-size: 16px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.15);
            }
        """)

        top_bar_layout.addWidget(theme_btn)
        top_bar_layout.addWidget(settings_btn)
        top_bar_layout.addWidget(backup_btn)

        top_bar.setLayout(top_bar_layout)
        content_layout.addWidget(top_bar)

        self.recent_frame = QFrame()
        self.recent_frame.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 16px;
                padding: 15px;
            }
        """)
        recent_layout = QHBoxLayout()
        recent_layout.setContentsMargins(15, 10, 15, 10)

        recent_title = QLabel("最近使用")
        recent_title.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
        recent_title.setStyleSheet("color: rgba(255, 255, 255, 0.6);")
        recent_layout.addWidget(recent_title)

        self.recent_label = QLabel("")
        self.recent_buttons = []
        recent_layout.addWidget(self.recent_label)
        recent_layout.addStretch()

        self.recent_frame.setLayout(recent_layout)
        self.update_recent_functions()
        content_layout.addWidget(self.recent_frame)

        content_label = QLabel("选择功能")
        content_label.setFont(QFont("Microsoft YaHei UI", 13))
        content_label.setStyleSheet("color: rgba(255, 255, 255, 0.5); padding-left: 5px;")
        content_layout.addWidget(content_label)

        btn_configs = [
            ("🎵 音乐下载", self.open_music_download, "music_download_btn", "Ctrl+1"),
            ("📺 B站音乐下载", self.open_bilibili_music_download, "bilibili_music_download_btn", "Ctrl+2"),
            ("🌐 多平台音乐", self.open_multi_platform_music, "multi_platform_music_btn", "Ctrl+M"),
            ("🤖 AI 智能对话", self.open_ai_chat, "ai_chat_btn", "Ctrl+3"),
            ("🎶 本地音乐播放器", self.open_music_player, "music_player_btn", "Ctrl+5"),
            ("🔄 格式转换工具", self.open_convert_tools, "convert_tools_btn", "Ctrl+4"),
            ("🎲 随机数工具", self.open_random_name, "random_name_btn", "Ctrl+6"),
            ("🔧 工具集", self.open_tools_collection, "tools_collection_btn", "Ctrl+T"),
            ("🎮 宏控制工具", self.open_macro, "macro_btn", "Ctrl+7"),
            ("✏️ 屏幕画笔", self.open_screen_pen, "screen_pen_btn", "Ctrl+8"),
            ("🐍 贪吃蛇游戏", self.open_snakes, "snakes_btn", "Ctrl+9"),
        ]

        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(15)

        for idx, (btn_text, btn_handler, btn_name, shortcut) in enumerate(btn_configs):
            btn = ModernButton(btn_text)
            btn.setToolTip(f"快捷键: {shortcut}")
            btn.clicked.connect(btn_handler)
            row = idx // 3
            col = idx % 3
            self.grid_layout.addWidget(btn, row, col)

        content_layout.addLayout(self.grid_layout)

        content_layout.addStretch()

        footer = QLabel("💡 快捷键: Ctrl+数字键 | Ctrl+M 多平台音乐 | Ctrl+F 论坛 | Ctrl+G 代码托管 | Ctrl+Q 退出  ⚡ RAILGUN ⚡")
        footer.setFont(QFont("Microsoft YaHei UI", 9))
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("""
            color: rgba(255, 255, 255, 0.4); 
            padding: 12px;
            border-top: 1px solid rgba(255, 255, 255, 0.08);
        """)
        content_layout.addWidget(footer)

        content_widget.setLayout(content_layout)
        self.content_widget = content_widget
        main_layout.addWidget(content_widget)

        central_widget.setLayout(main_layout)

        try:
            self.remote_server = RemoteControlServer(self, 5000)
            self.remote_server.start()
            print("[主窗口] 远程控制服务器已启动: http://localhost:5000")
        except Exception as e:
            print(f"[主窗口] 启动远程控制服务器失败: {e}")
        
        self.forum_server = None
        self.code_host_server = None

        if entry_bg:
            try:
                self.apply_entry_background(entry_bg)
            except Exception:
                pass
        
        self.setup_shortcuts()

    def setup_shortcuts(self):
        """设置快捷键"""
        from PyQt5.QtWidgets import QShortcut
        from PyQt5.QtGui import QKeySequence
        from PyQt5.QtCore import Qt
        
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

    def open_music_download(self):
        """打开音乐下载模块"""
        self.record_recent_function("music_download")
        from Music_Download.main_music_download import MusicDownloadWindow
        self.md_window = MusicDownloadWindow()
        self.md_window.show()

    def open_bilibili_music_download(self):
        """打开B站音乐下载模块"""
        self.record_recent_function("bilibili_music_download")
        from Bilibili_Music_Download.main_bilibili_download import BilibiliMusicDownloadWindow  # type: ignore
        self.bmd_window = BilibiliMusicDownloadWindow()
        self.bmd_window.show()

    def open_multi_platform_music(self):
        """打开多平台音乐下载模块"""
        self.record_recent_function("multi_platform_music")
        from Music_Download.multi_platform import MultiPlatformMusicWindow
        self.mpm_window = MultiPlatformMusicWindow()
        self.mpm_window.show()

    def open_ai_chat(self):
        """打开AI聊天模块"""
        self.record_recent_function("ai_chat")
        from AI_Chat.main_ai_chat import AIChatWindow
        self.ac_window = AIChatWindow(self.config)
        self.ac_window.show()

    def open_convert_tools(self):
        """打开格式转换工具窗口"""
        self.record_recent_function("convert_tools")
        from Tools.Convert_Tools.main_convert import ConvertToolsWindow
        self.convert_window = ConvertToolsWindow(self.config)
        self.convert_window.show()


    def open_music_player(self):
        """打开本地音乐播放器"""
        self.record_recent_function("music_player")
        from Music_Player.main_music_player import MusicPlayerWindow
        self.mp_window = MusicPlayerWindow()
        self.mp_window.show()

    def open_random_name(self):
        """打开随机数工具"""
        self.record_recent_function("random_name")
        from Tools.RandomName.main_randomname import RandomNameWindow
        self.rn_window = RandomNameWindow()
        self.rn_window.show()

    def open_tools_collection(self):
        """打开工具集"""
        self.record_recent_function("tools_collection")
        from Tools.Tools_Collection.main_tools import ToolsCollectionWindow
        self.tools_window = ToolsCollectionWindow()
        self.tools_window.show()

    def open_macro(self):
        """打开宏控制工具"""
        self.record_recent_function("macro")
        try:
            from Macro.macro import MacroUI
            self.macro_window = MacroUI()
            self.macro_window.run()
        except ImportError as e:
            print(f"[宏控制] 导入错误: {e}")
            QMessageBox.critical(self, "错误", f"无法加载宏控制模块：\n{e}")
        except Exception as e:
            print(f"[宏控制] 运行错误: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "错误", f"宏控制运行出错：\n{e}")

    def open_screen_pen(self):
        """打开希沃白板工具"""
        self.record_recent_function("screen_pen")
        from Tools.Screen_Pen.main_screen_pen import WhiteboardWindow
        self.sp_window = WhiteboardWindow()
        self.sp_window.show()

    def open_snakes(self):
        """打开贪吃蛇游戏"""
        self.record_recent_function("snakes")
        from GAMES.SNAKES.main_snakes import SnakesWindow
        self.snakes_window = SnakesWindow()
        self.snakes_window.show()

    def open_forum(self):
        """打开社区论坛"""
        self.record_recent_function("forum")
        if self.forum_server is None:
            self.forum_server = ForumServer(5001)
        
        if self.forum_server.running:
            self.forum_server.open_forum()
        else:
            if self.forum_server.start():
                import time
                time.sleep(0.5)
                self.forum_server.open_forum()
            else:
                QMessageBox.warning(self, "错误", "论坛服务器启动失败")

    def open_code_host(self):
        """打开代码托管"""
        self.record_recent_function("code_host")
        if self.code_host_server is None:
            self.code_host_server = CodeHostServer(8088)
        
        if self.code_host_server.running:
            self.code_host_server.open_web()
        else:
            if self.code_host_server.start():
                import time
                time.sleep(0.5)
                self.code_host_server.open_web()
            else:
                QMessageBox.warning(self, "错误", "代码托管服务器启动失败")

    def change_entry_background(self):
        """允许用户选择主入口背景图片并保存到配置"""
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        file_path, _ = QFileDialog.getOpenFileName(self, "选择背景图片", self.config.get_config("paths.data") or "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            # 保存到配置并立即应用
            self.config.set_config("ui.entry_background", file_path)
            # 立即应用背景（使用 QPixmap + QPalette 方法）
            try:
                self.apply_entry_background(file_path)
            except Exception:
                pass
            QMessageBox.information(self, "已保存", "主入口背景已更新。")

    def closeEvent(self, event):
        """窗口关闭时停止所有服务器并保存状态"""
        try:
            self.save_window_state()
        except Exception:
            pass
        try:
            if hasattr(self, 'remote_server') and self.remote_server:
                self.remote_server.running = False
        except Exception:
            pass
        try:
            if hasattr(self, 'forum_server') and self.forum_server and self.forum_server.running:
                self.forum_server.running = False
        except Exception:
            pass
        try:
            if hasattr(self, 'code_host_server') and self.code_host_server and self.code_host_server.running:
                self.code_host_server.running = False
        except Exception:
            pass
        event.accept()

    def load_window_state(self):
        """加载窗口状态（位置和大小）"""
        window_state = self.config.get_config("ui.window_state") or {}
        x = window_state.get("x", 100)
        y = window_state.get("y", 100)
        width = window_state.get("width", 1000)
        height = window_state.get("height", 520)
        
        # 确保窗口在可见范围内
        from PyQt5.QtWidgets import QApplication, QDesktopWidget
        screen = QDesktopWidget().screenGeometry()
        if x < 0 or x > screen.width() - 100:
            x = 100
        if y < 0 or y > screen.height() - 100:
            y = 100
        
        self.setGeometry(x, y, width, height)

    def save_window_state(self):
        """保存窗口状态"""
        geo = self.geometry()
        self.config.set_config("ui.window_state", {
            "x": geo.x(),
            "y": geo.y(),
            "width": geo.width(),
            "height": geo.height()
        })

    def apply_theme(self):
        """应用主题样式 - 二次元风格"""
        theme_mode = self.config.get_config("ui.theme_mode") or "railgun"
        
        themes = {
            "railgun": {
                "name": "超电磁炮",
                "frame_bg": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1a1a2e, stop:0.5 #16213e, stop:1 #0f3460)",
                "accent": "#00d4ff",
                "accent_secondary": "#7b2cbf",
                "text": "#ffffff",
                "text_secondary": "#c0c0c0",
                "card_bg": "rgba(0, 0, 0, 0.5)",
                "header_bg": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00d4ff, stop:0.5 #7b2cbf, stop:1 #e94560)",
                "glow": "#00d4ff",
                "border": "rgba(0, 212, 255, 0.4)"
            },
            "genshin": {
                "name": "原神",
                "frame_bg": "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1c1c22, stop:0.5 #2d2d3a, stop:1 #1c1c22)",
                "accent": "#f5c542",
                "accent_secondary": "#c9a227",
                "text": "#ffffff",
                "text_secondary": "#d4c5a0",
                "card_bg": "rgba(0, 0, 0, 0.5)",
                "header_bg": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #c9a227, stop:0.5 #f5c542, stop:1 #c9a227)",
                "glow": "#f5c542",
                "border": "rgba(245, 197, 66, 0.4)"
            },
            "light": {
                "name": "简约亮色",
                "frame_bg": "#f0f2f5",
                "accent": "#4A90D9",
                "accent_secondary": "#67B8F7",
                "text": "#222222",
                "text_secondary": "#555555",
                "card_bg": "rgba(255, 255, 255, 0.9)",
                "header_bg": "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4A90D9, stop:1 #67B8F7)",
                "glow": "#4A90D9",
                "border": "rgba(74, 144, 217, 0.3)"
            }
        }
        
        if theme_mode not in themes:
            theme_mode = "railgun"
        
        t = themes[theme_mode]
        
        self.setStyleSheet(f"""
            QMainWindow {{
                background: {t['frame_bg']};
            }}
            QWidget {{
                font-family: "Microsoft YaHei UI", "微软雅黑", sans-serif;
                font-size: 14px;
                color: {t['text']};
            }}
            QLabel {{ color: {t['text']}; }}
            QGroupBox {{ 
                border: 1px solid {t['border']}; 
                border-radius: 12px;
                background: {t['card_bg']};
                padding: 10px;
            }}
            QFrame {{
                background: {t['card_bg']};
                border-radius: 12px;
                border: 1px solid {t['border']};
            }}
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {t['accent']}, stop:1 {t['accent_secondary']});
                color: {'#1a1a2e' if theme_mode == 'genshin' else 'white'};
                border: none;
                border-radius: 12px;
                padding: 12px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {t['accent_secondary']}, stop:1 {t['accent']});
                border: 1px solid {t['glow']};
            }}
            QPushButton:pressed {{
                background: {t['accent']};
            }}
            QLineEdit {{
                background: {t['card_bg']};
                border: 1px solid {t['border']};
                border-radius: 20px;
                padding: 8px 16px;
                color: {t['text']};
            }}
            QLineEdit:focus {{
                border: 1px solid {t['accent']};
            }}
        """)
        
        if hasattr(self, 'header_label'):
            self.header_label.setStyleSheet(f"""
                QLabel {{
                    color: {'#1a1a2e' if theme_mode == 'genshin' else 'white'};
                    background: {t['header_bg']};
                    border-radius: 16px;
                    padding: 25px;
                    font-size: 28px;
                    font-weight: bold;
                }}
            """)
        
        if hasattr(self, 'recent_frame'):
            self.recent_frame.setStyleSheet(f"""
                QFrame {{
                    background: transparent;
                    border: none;
                }}
            """)
        
        if hasattr(self, 'search_box'):
            self.search_box.setStyleSheet(f"""
                QLineEdit {{
                    background: {t['card_bg']};
                    border: 1px solid {t['border']};
                    border-radius: 20px;
                    padding: 8px 16px;
                    color: {t['text']};
                }}
                QLineEdit::placeholder {{
                    color: {t['text_secondary']};
                }}
            """)

    def toggle_theme(self):
        """切换主题"""
        theme_order = ["railgun", "genshin", "light"]
        current = self.config.get_config("ui.theme_mode") or "railgun"
        
        current_index = theme_order.index(current) if current in theme_order else 0
        next_index = (current_index + 1) % len(theme_order)
        new_theme = theme_order[next_index]
        
        self.config.set_config("ui.theme_mode", new_theme)
        self.apply_theme()
        
        theme_names = {"railgun": "⚡ 超电磁炮", "genshin": "✨ 原神", "light": "☀️ 简约亮色"}
        QMessageBox.information(self, "主题切换", f"已切换到: {theme_names.get(new_theme, new_theme)}")

    def on_search_changed(self, text):
        """搜索功能"""
        text = text.lower()
        for i in range(self.grid_layout.count()):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                btn_text = widget.text().lower()
                if text and text in btn_text:
                    widget.setVisible(True)
                else:
                    widget.setVisible(bool(not text))

    def update_recent_functions(self):
        """更新最近使用功能显示"""
        if not hasattr(self, 'recent_frame'):
            return
            
        recent_layout = self.recent_frame.layout()
        if not recent_layout:
            return
            
        recent = self.config.get_config("ui.recent_functions") or []
        
        while recent_layout.count() > 1:
            item = recent_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        
        recent_title = QLabel("最近使用")
        recent_title.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
        recent_title.setStyleSheet("color: rgba(255, 255, 255, 0.6);")
        recent_layout.insertWidget(0, recent_title)
        
        if not recent:
            no_recent = QLabel("暂无")
            no_recent.setStyleSheet("color: rgba(255, 255, 255, 0.3);")
            recent_layout.insertWidget(1, no_recent)
            return
        
        func_map = {
            "music_download": ("🎵 音乐下载", self.open_music_download),
            "bilibili_music_download": ("📺 B站音乐下载", self.open_bilibili_music_download),
            "multi_platform_music": ("🌐 多平台音乐", self.open_multi_platform_music),
            "ai_chat": ("🤖 AI 智能对话", self.open_ai_chat),
            "music_player": ("🎶 本地音乐播放器", self.open_music_player),
            "convert_tools": ("🔄 格式转换工具", self.open_convert_tools),
            "random_name": ("🎲 随机数工具", self.open_random_name),
            "tools_collection": ("🔧 工具集", self.open_tools_collection),
            "macro": ("🎮 宏控制工具", self.open_macro),
            "screen_pen": ("✏️ 屏幕画笔", self.open_screen_pen),
            "snakes": ("🐍 贪吃蛇游戏", self.open_snakes),
            "forum": ("💬 社区论坛", self.open_forum),
            "code_host": ("📦 代码托管", self.open_code_host),
        }
        
        for func_key in recent[:5]:
            if func_key in func_map:
                name, func = func_map[func_key]
                btn = QPushButton(f"  {name}  ")
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setStyleSheet("""
                    QPushButton {
                        background: rgba(0, 212, 255, 0.15);
                        border: 1px solid rgba(0, 212, 255, 0.3);
                        border-radius: 18px;
                        padding: 6px 14px;
                        color: #00d4ff;
                        font-size: 12px;
                    }
                    QPushButton:hover {
                        background: rgba(0, 212, 255, 0.25);
                        border: 1px solid rgba(0, 212, 255, 0.6);
                    }
                """)
                btn.clicked.connect(func)
                recent_layout.insertWidget(recent_layout.count() - 1, btn)

    def record_recent_function(self, func_key: str):
        """记录最近使用功能"""
        recent = self.config.get_config("ui.recent_functions") or []
        if func_key in recent:
            recent.remove(func_key)
        recent.insert(0, func_key)
        recent = recent[:10]
        self.config.set_config("ui.recent_functions", recent)
        self.update_recent_functions()

    def backup_data(self):
        """备份数据"""
        from PyQt5.QtWidgets import QFileDialog
        import shutil
        import datetime
        
        default_name = f"RAILGUN_backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "选择备份保存位置", default_name + ".zip", "ZIP压缩文件 (*.zip)"
        )
        
        if not file_path:
            return
        
        try:
            import zipfile
            data_dir = Path(BASE_PATH) / "Data"
            
            with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                if data_dir.exists():
                    for file in data_dir.rglob('*'):
                        if file.is_file():
                            arcname = str(file.relative_to(data_dir))
                            zipf.write(file, arcname)
            
            QMessageBox.information(self, "成功", f"数据已备份到:\n{file_path}")
        except Exception as e:
            QMessageBox.warning(self, "失败", f"备份失败:\n{str(e)}")

    def apply_entry_background(self, file_path: str) -> None:
        """使用 QPixmap 加载图片并通过 QPalette 设置背景"""
        from PyQt5.QtGui import QPalette, QBrush, QPixmap
        from PyQt5.QtCore import Qt
        
        pixmap = QPixmap(file_path)
        if pixmap.isNull():
            alt = file_path.replace('\\', '/')
            pixmap = QPixmap(alt)
        if pixmap.isNull():
            return
        
        if hasattr(self, 'content_widget') and self.content_widget:
            target = self.content_widget
        else:
            target = self.central_widget
        
        size = target.size()
        if size.width() <= 0 or size.height() <= 0:
            scaled = pixmap
        else:
            scaled = pixmap.scaled(size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        
        palette = QPalette()
        palette.setBrush(QPalette.ColorRole.Window, QBrush(scaled))
        target.setPalette(palette)
        target.setAutoFillBackground(True)

    def resizeEvent(self, event):
        try:
            entry_bg = self.config.get_config("ui.entry_background") or ""
            if entry_bg:
                self.apply_entry_background(entry_bg)
        except Exception:
            pass
        super().resizeEvent(event)