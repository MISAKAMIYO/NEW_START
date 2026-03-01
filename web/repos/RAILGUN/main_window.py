import sys
import os
import threading
import logging
from PyQt5.QtWidgets import QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel, QFrame, QGridLayout, QMessageBox
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPainter, QColor, QLinearGradient
from PyQt5.QtCore import Qt, QSize
from settings_manager import ConfigManager
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO
import webbrowser
import time

sys.path.insert(0, os.path.dirname(__file__))
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
        self.setMinimumHeight(50)
        self.setFont(QFont("Microsoft YaHei UI", 10))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background-color: #4A90D9;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
                text-align: left;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5BA0E9;
            }
            QPushButton:pressed {
                background-color: #3A80C9;
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
        # 改为横向长方形入口窗口
        self.setGeometry(100, 100, 1000, 520)
        
        # 应用主题样式（从配置读取）
        ui_theme = self.config.get_config("ui.theme") or {}
        frame_bg = ui_theme.get("frame_bg", "#2B0B3A")
        accent = ui_theme.get("accent", "#8A2BE2")
        text_color = ui_theme.get("text", "#ECEAF6")

        entry_bg = self.config.get_config("ui.entry_background") or ""

        # 应用全局样式（不包含背景图片，背景图片应用到 central_widget）
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {frame_bg};
            }}
            QWidget {{
                font-family: "Microsoft YaHei UI", "微软雅黑", sans-serif;
                font-size: 14px;
                color: {text_color};
            }}
            QLabel {{ color: {text_color}; }}
            QGroupBox {{ border: 1px solid {accent}; border-radius: 8px; }}
            QFrame {{ background-color: rgba(255,255,255,0.02); border-radius:8px; }}
            QPushButton {{ background-color: {accent}; color: white; border-radius: 8px; padding: 8px; }}
        """)

        # 如果指定了入口背景图片，则应用到 central_widget（使用 file:/// 前缀保证加载）
        if entry_bg:
            file_url = entry_bg.replace('\\', '/')
            if not file_url.startswith('file:///') and not file_url.startswith('http'):
                # windows 路径转换为 file:///C:/path
                if file_url.startswith('/'):
                    file_url = 'file://' + file_url
                else:
                    file_url = 'file:///' + file_url
            # 应用到 central widget 的样式
            # central widget 背景会覆盖 QMainWindow 的背景区域
            bg_css = f"background-image: url('{file_url}'); background-repeat: no-repeat; background-position: center; background-size: cover;"
        else:
            bg_css = ""

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        # 保留 central widget 引用以便在运行时更新背景
        self.central_widget = central_widget

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        header = QLabel("RAILGUN")
        header.setFont(QFont("Microsoft YaHei UI", 24, QFont.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("""
            QLabel {
                color: #2C3E50;
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                    stop:0 #4A90D9, stop:1 #67B8F7);
                color: white;
                border-radius: 12px;
                padding: 25px;
                font-size: 28px;
            }
        """)
        header.setFixedHeight(90)
        # 在标题右上角添加背景设置按钮
        header_bar = QFrame()
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(0,0,0,0)
        header_layout.addWidget(header)
        settings_btn = QPushButton("设置背景")
        settings_btn.setFixedWidth(100)
        settings_btn.clicked.connect(self.change_entry_background)
        header_layout.addWidget(settings_btn, 0, Qt.AlignmentFlag.AlignRight)
        header_bar.setLayout(header_layout)
        layout.addWidget(header_bar)

        subtitle = QLabel("选择要使用的功能")
        subtitle.setFont(QFont("Microsoft YaHei UI", 11))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #7F8C8D;")
        layout.addWidget(subtitle)

        layout.addSpacing(10)

        # 使用网格布局，使按钮两列并列
        btn_configs = [
            ("🎵 音乐下载", self.open_music_download, "music_download_btn"),
            ("📺 B站音乐下载", self.open_bilibili_music_download, "bilibili_music_download_btn"),
            ("🤖 AI 智能对话", self.open_ai_chat, "ai_chat_btn"),
            ("🎶 本地音乐播放器", self.open_music_player, "music_player_btn"),
            ("🔄 格式转换工具", self.open_convert_tools, "convert_tools_btn"),
            ("🎲 随机数工具", self.open_random_name, "random_name_btn"),
            ("🎮 宏控制工具", self.open_macro, "macro_btn"),
            ("✏️ 屏幕画笔", self.open_screen_pen, "screen_pen_btn"),
            ("🐍 贪吃蛇游戏", self.open_snakes, "snakes_btn"),
            ("💬 社区论坛", self.open_forum, "forum_btn"),
            ("📦 代码托管", self.open_code_host, "code_host_btn"),
        ]

        grid = QGridLayout()
        grid.setSpacing(12)
        # 按钮大小策略：每行两列
        for idx, (btn_text, btn_handler, btn_name) in enumerate(btn_configs):
            btn = ModernButton(btn_text)
            btn.clicked.connect(btn_handler)
            row = idx // 2
            col = idx % 2
            grid.addWidget(btn, row, col)

        layout.addLayout(grid)

        footer = QLabel("© 2025 RAILGUN Team")
        footer.setFont(QFont("Microsoft YaHei UI", 9))
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: #BDC3C7;")
        layout.addWidget(footer)

        try:
            self.remote_server = RemoteControlServer(self, 5000)
            self.remote_server.start()
            
            self.forum_server = ForumServer(5001)
            if self.forum_server.start():
                print("[主窗口] 论坛服务器已启动: http://localhost:5001")
            else:
                print("[主窗口] 论坛服务器启动失败")
            
            self.code_host_server = CodeHostServer(8088)
            if self.code_host_server.start():
                print("[主窗口] 代码托管服务器已启动: http://localhost:8088")
            else:
                print("[主窗口] 代码托管服务器启动失败")
            
            print("[主窗口] 远程控制服务器已启动: http://localhost:5000")
        except Exception as e:
            print(f"[主窗口] 启动服务器失败: {e}")

        central_widget.setLayout(layout)
        # 确保 central widget 能够呈现背景图（使用 QPalette + QPixmap，更稳健）
        central_widget.setAutoFillBackground(True)
        # 如果配置了背景图片，尝试加载并应用（支持包含中文路径）
        if entry_bg:
            try:
                self.apply_entry_background(entry_bg)
            except Exception:
                pass

    def open_music_download(self):
        """打开音乐下载模块"""
        from Music_Download.main_music_download import MusicDownloadWindow
        self.md_window = MusicDownloadWindow()
        self.md_window.show()

    def open_bilibili_music_download(self):
        """打开B站音乐下载模块"""
        from Bilibili_Music_Download.main_bilibili_download import BilibiliMusicDownloadWindow  # type: ignore
        self.bmd_window = BilibiliMusicDownloadWindow()
        self.bmd_window.show()

    def open_ai_chat(self):
        """打开AI聊天模块"""
        from AI_Chat.main_ai_chat import AIChatWindow
        self.ac_window = AIChatWindow(self.config)
        self.ac_window.show()

    def open_convert_tools(self):
        """打开格式转换工具窗口"""
        from Tools.Convert_Tools.main_convert import ConvertToolsWindow
        # 传入配置管理器以便工具读取 paths.data 等设置
        self.convert_window = ConvertToolsWindow(self.config)
        self.convert_window.show()


    def open_music_player(self):
        """打开本地音乐播放器"""
        from Music_Player.main_music_player import MusicPlayerWindow
        self.mp_window = MusicPlayerWindow()
        self.mp_window.show()

    def open_random_name(self):
        """打开随机数工具"""
        from Tools.RandomName.main_randomname import RandomNameWindow
        self.rn_window = RandomNameWindow()
        self.rn_window.show()

    def open_macro(self):
        """打开宏控制工具"""
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
        from Tools.Screen_Pen.main_screen_pen import WhiteboardWindow
        self.sp_window = WhiteboardWindow()
        self.sp_window.show()

    def open_snakes(self):
        """打开贪吃蛇游戏"""
        from GAMES.SNAKES.main_snakes import SnakesWindow
        self.snakes_window = SnakesWindow()
        self.snakes_window.show()

    def open_forum(self):
        """打开社区论坛"""
        if hasattr(self, 'forum_server') and self.forum_server.running:
            self.forum_server.open_forum()
        else:
            webbrowser.open("http://localhost:5001")
            QMessageBox.information(self, "提示", "正在启动论坛服务器...\n请稍候片刻后刷新页面")

    def open_code_host(self):
        """打开代码托管"""
        if hasattr(self, 'code_host_server') and self.code_host_server.running:
            self.code_host_server.open_web()
        else:
            webbrowser.open("http://localhost:8088")
            QMessageBox.information(self, "提示", "正在启动代码托管服务器...\n请稍候片刻后刷新页面")

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

    def apply_entry_background(self, file_path: str) -> None:
        """使用 QPixmap 加载图片并通过 QPalette 在 central_widget 上设置缩放背景。

        直接使用文件路径加载 QPixmap，避免 QSS 在处理包含非 ASCII 路径时失败。
        """
        from PyQt5.QtGui import QPalette, QBrush
        pixmap = QPixmap(file_path)
        if pixmap.isNull():
            # 如果加载失败，尝试用替代的路径分隔符重试
            alt = file_path.replace('\\', '/')
            pixmap = QPixmap(alt)
        if pixmap.isNull():
            return
        # 按当前 central_widget 大小进行缩放并填充
        size = self.central_widget.size()
        if size.width() <= 0 or size.height() <= 0:
            scaled = pixmap
        else:
            scaled = pixmap.scaled(size, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        palette = QPalette()
        palette.setBrush(QPalette.ColorRole.Window, QBrush(scaled))
        self.central_widget.setPalette(palette)

    def resizeEvent(self, event):
        # 窗口大小改变时，重新缩放背景以适配 central_widget
        try:
            entry_bg = self.config.get_config("ui.entry_background") or ""
            if entry_bg:
                self.apply_entry_background(entry_bg)
        except Exception:
            pass