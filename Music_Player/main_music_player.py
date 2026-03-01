"""
Music Player Module - 现代化暗黑主题音乐播放器
使用 AudioPlayer 核心模块
"""

import os
import sys
import re
import json
import logging

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QSlider, 
    QLabel, QFileDialog, QToolButton, QLineEdit, QCheckBox,
    QTextEdit, QFrame, QGraphicsDropShadowEffect, QInputDialog,
    QMessageBox, QApplication, QSpacerItem, QSizePolicy
)
from PyQt5.QtWidgets import QComboBox
from PyQt5.QtCore import QUrl, QTimer, Qt, QPropertyAnimation, QEasingCurve, QRect, QSize, QRectF
from PyQt5.QtGui import QFont, QColor, QPixmap, QPainter, QPainterPath, QLinearGradient, QIcon

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

from settings_manager import ConfigManager
from Music_Player.audio_player import AudioPlayer
from Music_Player.lyrics_widget import LyricsWidget
from Music_Player.external_lyrics_window import ExternalLyricsWindow
from Music_Player.lyrics_search_dialog import LyricsSearchDialog

logger = logging.getLogger(__name__)


MODERN_DARK_THEME = """
    QWidget {
        background-color: #0D0D0D;
        color: #E8E8E8;
        font-family: 'Segoe UI', 'Microsoft YaHei UI', sans-serif;
        font-size: 14px;
    }
    
    QFrame[cardStyle="true"] {
        background-color: rgba(25, 25, 35, 0.95);
        border-radius: 24px;
        border: 1px solid rgba(255, 255, 255, 0.08);
    }
    
    QFrame[glassStyle="true"] {
        background-color: rgba(30, 30, 45, 0.7);
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    QLineEdit {
        background-color: rgba(40, 40, 60, 0.6);
        border: 2px solid rgba(255, 255, 255, 0.1);
        border-radius: 30px;
        padding: 14px 24px;
        font-size: 14px;
        color: #FFFFFF;
        selection-background-color: #7C3AED;
    }
    
    QLineEdit:focus {
        border-color: #7C3AED;
        background-color: rgba(40, 40, 60, 0.8);
    }
    
    QLineEdit::placeholder {
        color: rgba(255, 255, 255, 0.4);
    }
    
    QListWidget {
        background-color: rgba(15, 15, 25, 0.6);
        border: none;
        border-radius: 16px;
        padding: 8px;
    }
    
    QListWidget::item {
        padding: 12px 16px;
        border-radius: 12px;
        margin-bottom: 4px;
    }
    
    QListWidget::item:hover {
        background-color: rgba(124, 58, 237, 0.15);
    }
    
    QListWidget::item:selected {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
            stop:0 rgba(124, 58, 237, 0.4), stop:1 rgba(139, 92, 246, 0.2));
        color: #FFFFFF;
    }
    
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #7C3AED, stop:1 #5B21B6);
        color: white;
        border: none;
        border-radius: 16px;
        padding: 14px 28px;
        font-weight: 600;
        font-size: 14px;
    }
    
    QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #8B5CF6, stop:1 #6D28D9);
    }
    
    QPushButton:pressed {
    }
    
    QPushButton[secondary="true"] {
        background: rgba(60, 60, 80, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    QPushButton[secondary="true"]:hover {
        background: rgba(80, 80, 100, 0.8);
        border-color: rgba(124, 58, 237, 0.5);
    }
    
    QSlider::groove:horizontal {
        background: rgba(255, 255, 255, 0.1);
        height: 6px;
        border-radius: 3px;
    }
    
    QSlider::handle:horizontal {
        background: qlineargradient(x1:0, y1=0, x2:1, y2=1,
            stop:0 #C4B5FD, stop:1 #7C3AED);
        width: 20px;
        height: 20px;
        border-radius: 10px;
        margin: -7px 0;
        border: 2px solid rgba(255, 255, 255, 0.3);
    }
    
    QSlider::sub-page:horizontal {
        background: qlineargradient(x1:0, y1=0, x2:1, y2:0,
            stop:0 #7C3AED, stop:1 #A78BFA);
        border-radius: 3px;
    }
    
    QToolButton {
        background: transparent;
        border: none;
        border-radius: 12px;
        padding: 12px;
    }
    
    QToolButton:hover {
        background-color: rgba(124, 58, 237, 0.2);
    }
    
    QToolButton[iconOnly="true"] {
        min-width: 48px;
        min-height: 48px;
    }
    
    QTextEdit {
        background-color: rgba(15, 15, 25, 0.6);
        border: none;
        border-radius: 16px;
        padding: 20px;
        font-size: 15px;
        line-height: 1.8;
    }
    
    QLabel#TitleLabel {
        font-size: 22px;
        font-weight: 700;
        color: #FFFFFF;
    }
    
    QLabel#SubtitleLabel {
        font-size: 14px;
        color: rgba(255, 255, 255, 0.6);
    }
    
    QLabel#TimeLabel {
        font-size: 12px;
        font-weight: 500;
        color: rgba(255, 255, 255, 0.5);
        font-family: 'Consolas', monospace;
    }
"""


class AnimatedCoverLabel(QLabel):
    """带动画效果的专辑封面标签"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(320, 320)
        # 使用大圆角并在绘制中使用椭圆裁剪以实现圆形封面
        self.setStyleSheet("""
            background-color: rgba(20, 20, 30, 0.9);
            border-radius: 160px;
        """)
        
        self.glow_effect = QGraphicsDropShadowEffect()
        self.glow_effect.setBlurRadius(50)
        self.glow_effect.setColor(QColor(124, 58, 237, 100))
        self.glow_effect.setOffset(0, 8)
        self.setGraphicsEffect(self.glow_effect)
        
        self.rotation_angle = 0
        self.rotation_timer = QTimer()
        self.rotation_timer.timeout.connect(self.update_rotation)
        self.is_rotating = False
        
        self.cover_pixmap = None
        
    def setRotating(self, rotating):
        self.is_rotating = rotating
        if rotating:
            self.rotation_timer.start(50)
        else:
            self.rotation_timer.stop()
    
    def update_rotation(self):
        if self.is_rotating:
            self.rotation_angle = (self.rotation_angle + 2) % 360
            self.update()
    
    def setCoverPixmap(self, pixmap):
        self.cover_pixmap = pixmap
        if pixmap and not pixmap.isNull():
            self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        center_x = self.width() // 2
        center_y = self.height() // 2
        
        if self.is_rotating and self.cover_pixmap:
            painter.translate(center_x, center_y)
            painter.rotate(self.rotation_angle)
            painter.translate(-center_x, -center_y)
        
        rect = self.rect()

        # 使用椭圆路径裁剪为圆形
        path = QPainterPath()
        path.addEllipse(QRectF(rect))
        painter.setClipPath(path)

        if self.cover_pixmap and not self.cover_pixmap.isNull():
            scaled = self.cover_pixmap.scaled(
                self.size(),
                Qt.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            # 居中裁剪显示
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
        else:
            gradient = QLinearGradient(0, 0, self.width(), self.height())
            gradient.setColorAt(0, QColor("#2A2A3C"))
            gradient.setColorAt(1, QColor("#1A1A2E"))
            painter.fillRect(rect, gradient)

            painter.setFont(QFont("Microsoft YaHei UI", 48, QFont.Bold))
            painter.setPen(QColor("#4D4D66"))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "♪")

        painter.setClipping(False)

        # 绘制圆形边框
        border_rect = rect.adjusted(2, 2, -2, -2)
        border_path = QPainterPath()
        border_path.addEllipse(QRectF(border_rect))
        pen = painter.pen()
        pen.setColor(QColor(255, 255, 255, 20))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(border_path)


class PlayControlButton(QPushButton):
    """播放控制按钮"""
    
    def __init__(self, icon_text="", parent=None):
        super().__init__(icon_text, parent)
        self.setProperty("iconOnly", "true")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(56, 56)


class CircleProgressBar(QFrame):
    """圆形进度条"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(80, 80)
        self.value = 0
        self.progress_color = QColor(124, 58, 237)
        self.background_color = QColor(60, 60, 80, 150)
    
    def setValue(self, value):
        self.value = max(0, min(100, value))
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        center_x = self.width() // 2
        center_y = self.height() // 2
        radius = min(center_x, center_y) - 6
        
        pen_width = 4
        
        background_pen = painter.pen()
        background_pen.setColor(self.background_color)
        background_pen.setWidth(pen_width)
        painter.setPen(background_pen)
        painter.drawEllipse(center_x - radius, center_y - radius, radius * 2, radius * 2)
        
        gradient = QLinearGradient(center_x - radius, center_y - radius, center_x + radius, center_y + radius)
        gradient.setColorAt(0, QColor("#7C3AED"))
        gradient.setColorAt(1, QColor("#A78BFA"))
        
        progress_pen = painter.pen()
        progress_pen.setColor(gradient)
        progress_pen.setWidth(pen_width)
        progress_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(progress_pen)
        
        start_angle = 90 * 16
        span_angle = int(-self.value * 3.6 * 16)
        painter.drawArc(center_x - radius, center_y - radius, radius * 2, radius * 2, start_angle, span_angle)


class GlassPanel(QFrame):
    """毛玻璃效果面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("glassStyle", "true")


class MusicPlayerWindow(QWidget):
    """音乐播放器窗口"""
    
    def __init__(self, config_manager: ConfigManager = None):
        super().__init__()
        self.config_manager = config_manager or ConfigManager()
        
        # 当前播放列表文件路径（默认使用 Data/playlist.json）
        base_dir = get_base_path()
        self.data_dir = os.path.join(base_dir, 'Data')
        os.makedirs(self.data_dir, exist_ok=True)
        self.playlists_dir = os.path.join(self.data_dir, 'Playlists')
        os.makedirs(self.playlists_dir, exist_ok=True)
        self.current_playlist_file = os.path.join(self.data_dir, 'playlist.json')

        self.audio_player = None
        self.lyrics_data = []
        self.external_lyrics_window = None
        
        # 进度条拖动状态跟踪
        self.progress_slider_dragging = False
        
        self.setup_ui()
        self.setup_player()
        # self.load_playlist()  # 由setup_player中的select_playlist处理
        
        # 初始化外置歌词窗口
        self.init_external_lyrics_window()
        
    def setup_ui(self):
        self.setWindowTitle("音乐播放器 - RAILGUN")
        self.setGeometry(100, 50, 1400, 800)
        self.setStyleSheet(MODERN_DARK_THEME)
        
        # 初始化歌词显示设置（在setup_center_panel之前）
        self.show_embedded_lyrics = True
        self._window_width_without_lyrics = None
        try:
            cfg_val = self.config_manager.get_config("features.show_embedded_lyrics")
            if cfg_val is not None:
                self.show_embedded_lyrics = bool(cfg_val)
        except Exception:
            self.show_embedded_lyrics = True
        
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(24)
        
        self.main_layout = main_layout  # 保存引用以便在其他方法中使用
        
        self.setup_left_panel(main_layout)
        self.setup_center_panel(main_layout)
        self.setup_right_panel(main_layout)
        
        self.setLayout(main_layout)
        
        # 根据歌词初始状态调整窗口宽度
        self.right_panel_width = 850  # 定义右侧面板宽度
        if not self.show_embedded_lyrics:
            self._window_width_without_lyrics = 1400 - self.right_panel_width
            self.setGeometry(100, 50, 1400 - self.right_panel_width, 800)
        else:
            self._window_width_without_lyrics = None
        
        self.lyrics_timer = QTimer()
        self.lyrics_timer.timeout.connect(self.update_lyrics)
        self.lyrics_timer.start(100)
    
    def init_external_lyrics_window(self):
        """初始化外置歌词窗口"""
        try:
            self.external_lyrics_window = ExternalLyricsWindow(self)
            # 从配置加载显示状态
            settings = self.config_manager.get_all_config()
            lyrics_settings = settings.get("external_lyrics", {})
            show_lyrics = lyrics_settings.get("show_lyrics", False)
            
            if show_lyrics:
                self.external_lyrics_window.show()
                # 更新按钮状态
                if hasattr(self, 'external_lyrics_btn'):
                    self.external_lyrics_btn.setChecked(True)
            else:
                self.external_lyrics_window.hide()
                # 更新按钮状态
                if hasattr(self, 'external_lyrics_btn'):
                    self.external_lyrics_btn.setChecked(False)
                
        except Exception as e:
            print(f"初始化外置歌词窗口失败: {e}")
            self.external_lyrics_window = None
    
    def setup_left_panel(self, main_layout):
        left_panel = QFrame()
        left_panel.setProperty("cardStyle", "true")
        # 使用可动画的最大宽度以支持平滑折叠/展开
        left_panel.setMinimumWidth(0)
        left_panel.setMaximumWidth(360)
        # 保存面板引用与初始宽度，便于折叠/展开控制
        self.left_panel = left_panel
        self.left_panel_width = 360
        self.left_panel_collapsed = False
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(20, 20, 20, 20)
        left_layout.setSpacing(16)
        
        title_container = QHBoxLayout()
        music_icon = QLabel("🎵")
        music_icon.setStyleSheet("font-size: 24px;")
        title_container.addWidget(music_icon)

        # 播放列表下拉（显示多个播放列表）
        self.playlist_selector = QComboBox()
        self.playlist_selector.setEditable(False)
        self.playlist_selector.setToolTip("选择播放列表")
        self.playlist_selector.currentIndexChanged.connect(self.on_playlist_selected)
        title_container.addWidget(self.playlist_selector)

        # 新建播放列表按钮
        new_pl_btn = QToolButton()
        new_pl_btn.setText("➕")
        new_pl_btn.setToolTip("新建播放列表")
        new_pl_btn.clicked.connect(self.create_new_playlist)
        title_container.addWidget(new_pl_btn)

        title_container.addStretch()
        left_layout.addLayout(title_container)
        
        search_container = QFrame()
        search_container.setStyleSheet("""
            QFrame {
                background-color: rgba(40, 40, 60, 0.4);
                border-radius: 30px;
            }
        """)
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(16, 8, 16, 8)
        search_layout.setSpacing(12)
        
        search_icon = QLabel("🔍")
        search_icon.setStyleSheet("font-size: 16px;")
        search_layout.addWidget(search_icon)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索歌曲...")
        self.search_input.textChanged.connect(self.filter_playlist)
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: transparent;
                border: none;
                padding: 8px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: none;
            }
        """)
        search_layout.addWidget(self.search_input)
        search_container.setLayout(search_layout)
        left_layout.addWidget(search_container)
        
        self.playlist_widget = QListWidget()
        self.playlist_widget.setSelectionMode(QListWidget.SingleSelection)
        self.playlist_widget.itemDoubleClicked.connect(self.play_playlist_item)
        self.playlist_widget.setStyleSheet("""
            QListWidget {
                background-color: transparent;
            }
        """)
        # 将按钮移到一个竖直侧边栏，避免底部空间拥挤
        content_h = QHBoxLayout()
        content_h.setSpacing(8)

        # 侧边栏：放置按钮（竖向）
        sidebar_frame = QFrame()
        # 收窄侧边栏以适配竖向文字按钮
        sidebar_frame.setFixedWidth(48)
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(4, 8, 4, 8)
        sidebar_layout.setSpacing(12)
        # 帮助函数：将中文文本转换为竖排（每字一行）
        def vertical_text(text: str) -> str:
            # 例如 '添加' -> '添\n加'
            return "\n".join(list(text))

        add_btn = QPushButton(vertical_text("添加"))
        add_btn.setToolTip("添加文件")
        add_btn.setFixedSize(QSize(40, 80))
        add_btn.setStyleSheet("""
            QPushButton {
                font-size: 12px;
                border-radius: 8px;
                color: #E8E8E8;
                background: transparent;
                padding: 2px;
            }
            QPushButton:hover { background: rgba(124,58,237,0.12); }
        """)
        add_btn.clicked.connect(self.add_files)
        add_btn.setProperty("secondary", "true")
        sidebar_layout.addWidget(add_btn)

        remove_btn = QPushButton(vertical_text("移除"))
        remove_btn.setToolTip("移除选中")
        remove_btn.setFixedSize(QSize(40, 80))
        remove_btn.setStyleSheet("""
            QPushButton { font-size: 12px; border-radius: 8px; color: #E8E8E8; background: transparent; padding: 2px; }
            QPushButton:hover { background: rgba(244,67,54,0.08); }
        """)
        remove_btn.clicked.connect(self.remove_selected)
        remove_btn.setProperty("secondary", "true")
        sidebar_layout.addWidget(remove_btn)

        bulk_btn = QPushButton(vertical_text("批量"))
        bulk_btn.setToolTip("批量选择文件并加入播放列表")
        bulk_btn.setFixedSize(QSize(40, 80))
        bulk_btn.setStyleSheet("font-size:12px; border-radius:8px; background: transparent; padding:2px;")
        bulk_btn.clicked.connect(self.bulk_add_files)
        bulk_btn.setProperty("secondary", "true")
        sidebar_layout.addWidget(bulk_btn)

        scan_btn = QPushButton(vertical_text("扫描"))
        scan_btn.setToolTip("在指定目录中识别并加入支持的音频文件")
        scan_btn.setFixedSize(QSize(40, 80))
        scan_btn.setStyleSheet("font-size:12px; border-radius:8px; background: transparent; padding:2px;")
        scan_btn.clicked.connect(self.auto_add_from_folder)
        scan_btn.setProperty("secondary", "true")
        sidebar_layout.addWidget(scan_btn)

        clear_btn = QPushButton(vertical_text("清空"))
        clear_btn.setToolTip("清空播放列表")
        clear_btn.setFixedSize(QSize(40, 80))
        clear_btn.setStyleSheet("font-size:12px; border-radius:8px; background: transparent; padding:2px;")
        clear_btn.clicked.connect(self.clear_playlist)
        clear_btn.setProperty("secondary", "true")
        sidebar_layout.addWidget(clear_btn)

        sidebar_layout.addStretch()
        sidebar_frame.setLayout(sidebar_layout)

        # 主要内容区：搜索 + 列表
        content_frame = QFrame()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)
        content_layout.addWidget(search_container)
        content_layout.addWidget(self.playlist_widget, 1)
        content_frame.setLayout(content_layout)

        content_h.addWidget(sidebar_frame)
        content_h.addWidget(content_frame, 1)

        left_layout.addLayout(content_h)
        
        left_panel.setLayout(left_layout)
        main_layout.addWidget(left_panel, 30)
    
    def setup_center_panel(self, main_layout):
        center_panel = QFrame()
        center_panel.setProperty("cardStyle", "true")
        center_layout = QVBoxLayout()
        center_layout.setContentsMargins(28, 20, 28, 28)
        center_layout.setSpacing(16)
        
        status_container = GlassPanel()
        status_container.setFixedHeight(48)
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(16, 8, 16, 8)
        
        self.status_label = QLabel("准备就绪")
        self.status_label.setObjectName("SubtitleLabel")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        
        self.play_mode_label = QLabel("顺序播放")
        self.play_mode_label.setObjectName("SubtitleLabel")
        status_layout.addWidget(self.play_mode_label)
        
        status_container.setLayout(status_layout)
        center_layout.addWidget(status_container)
        
        center_layout.addStretch()

        # 右上角：默认封面开关（用户可决定是否启用默认封面）
        top_row = QHBoxLayout()
        top_row.addStretch()
        use_default = True
        try:
            cfg_val = self.config_manager.get_config("features.use_default_cover")
            if cfg_val is not None:
                use_default = bool(cfg_val)
        except Exception:
            use_default = True

        self.default_cover_checkbox = QCheckBox("使用默认封面")
        self.default_cover_checkbox.setChecked(use_default)
        self.default_cover_checkbox.stateChanged.connect(self.on_toggle_default_cover)
        top_row.addWidget(self.default_cover_checkbox)

        # 歌词显示开关
        self.lyrics_checkbox = QCheckBox("歌词")
        self.lyrics_checkbox.setChecked(self.show_embedded_lyrics)
        self.lyrics_checkbox.setStyleSheet("""
            QCheckBox {
                color: #FFFFFF;
                font-size: 14px;
            }
        """)
        self.lyrics_checkbox.stateChanged.connect(self.on_toggle_lyrics_checkbox)
        top_row.addWidget(self.lyrics_checkbox)

        # 歌词搜索按钮
        self.lyrics_search_btn = QPushButton("🔍")
        self.lyrics_search_btn.setToolTip("搜索歌词")
        self.lyrics_search_btn.setFixedSize(36, 36)
        self.lyrics_search_btn.setStyleSheet("""
            QPushButton { font-size: 16px; border-radius:18px; background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 rgba(100,150,200,0.9), stop:1 rgba(80,130,180,0.85)); color: #FFFFFF }
            QPushButton:hover { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 rgba(120,170,220,1), stop:1 rgba(100,150,200,1)); }
        """)
        self.lyrics_search_btn.clicked.connect(self.on_search_lyrics)
        top_row.addWidget(self.lyrics_search_btn)

        # 外置歌词开关
        self.external_lyrics_btn = QPushButton("📝")
        self.external_lyrics_btn.setToolTip("外置歌词")
        self.external_lyrics_btn.setFixedSize(36, 36)
        self.external_lyrics_btn.setCheckable(True)
        self.external_lyrics_btn.setStyleSheet("""
            QPushButton { font-size: 18px; border-radius:18px; background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 rgba(180,80,100,0.9), stop:1 rgba(160,60,80,0.85)); color: #FFFFFF }
            QPushButton:hover { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 rgba(200,100,120,1), stop:1 rgba(180,80,100,1)); }
            QPushButton:checked { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 rgba(100,180,100,0.9), stop:1 rgba(80,160,80,0.85)); }
        """)
        self.external_lyrics_btn.clicked.connect(self.on_toggle_external_lyrics)
        top_row.addWidget(self.external_lyrics_btn)
        
        # 根据外置歌词窗口的当前可见状态设置按钮
        if self.external_lyrics_window:
            self.external_lyrics_btn.setChecked(self.external_lyrics_window.isVisible())
        else:
            self.external_lyrics_btn.setChecked(False)

        # 在右侧增加播放列表折叠入口按钮（位于中部面板右上角，作为折叠面板的入口）
        # 使用更明显的图标与圆形背景，并支持折叠动画时同步文本
        self.playlist_fold_btn = QPushButton("◀")
        self.playlist_fold_btn.setToolTip("收起播放列表")
        self.playlist_fold_btn.setFixedSize(36, 36)
        self.playlist_fold_btn.setStyleSheet("""
            QPushButton { font-size: 16px; border-radius:18px; background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 rgba(100,80,180,0.9), stop:1 rgba(80,60,160,0.85)); color: #FFFFFF }
            QPushButton:hover { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 rgba(120,100,200,1), stop:1 rgba(100,80,180,1)); }
        """)
        self.playlist_fold_btn.clicked.connect(self.toggle_left_panel)
        top_row.addWidget(self.playlist_fold_btn)
        center_layout.addLayout(top_row)
        
        self.cover_label = AnimatedCoverLabel()
        center_layout.addWidget(self.cover_label, 0, Qt.AlignHCenter)

        # 歌名区域：歌名 + 编辑按钮
        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title_row.addStretch()
        self.song_info_label = QLabel("等待播放")
        self.song_info_label.setObjectName("TitleLabel")
        self.song_info_label.setAlignment(Qt.AlignCenter)
        # 修复可能导致标题变透明的问题，显式设置文本颜色
        self.song_info_label.setStyleSheet("color: #FFFFFF;")
        title_row.addWidget(self.song_info_label)

        self.edit_title_btn = QToolButton()
        self.edit_title_btn.setText("🖊")
        self.edit_title_btn.setToolTip("编辑歌名")
        self.edit_title_btn.setFixedSize(28, 28)
        self.edit_title_btn.clicked.connect(self.on_edit_song_name)
        title_row.addWidget(self.edit_title_btn)
        title_row.addStretch()

        center_layout.addLayout(title_row)
        
        self.artist_label = QLabel("选择一首歌曲开始播放")
        self.artist_label.setObjectName("SubtitleLabel")
        self.artist_label.setAlignment(Qt.AlignCenter)
        self.artist_label.setStyleSheet("color: rgba(255,255,255,0.9);")
        center_layout.addWidget(self.artist_label, 0, Qt.AlignHCenter)
        
        center_layout.addStretch(1)
        
        progress_container = QFrame()
        progress_container.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 30, 45, 0.5);
                border-radius: 16px;
                padding: 16px;
            }
        """)
        progress_layout = QVBoxLayout()
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(8)
        
        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setFixedHeight(8)
        self.progress_slider.sliderPressed.connect(self.on_progress_slider_pressed)
        self.progress_slider.sliderReleased.connect(self.on_progress_slider_released)
        progress_layout.addWidget(self.progress_slider)
        
        time_row = QHBoxLayout()
        time_row.setSpacing(8)
        
        self.current_time_label = QLabel("00:00")
        self.current_time_label.setObjectName("TimeLabel")
        time_row.addWidget(self.current_time_label)
        
        time_row.addStretch(1)
        
        self.total_time_label = QLabel("00:00")
        self.total_time_label.setObjectName("TimeLabel")
        time_row.addWidget(self.total_time_label)
        
        progress_layout.addLayout(time_row)
        progress_container.setLayout(progress_layout)
        center_layout.addWidget(progress_container)
        
        control_container = GlassPanel()
        control_container.setStyleSheet("""
            GlassPanel {
                background-color: rgba(25, 25, 40, 0.6);
                border-radius: 24px;
                padding: 16px;
            }
        """)
        control_layout = QHBoxLayout()
        control_layout.setContentsMargins(20, 12, 20, 12)
        control_layout.setSpacing(16)
        
        self.mode_btn = QToolButton()
        self.mode_btn.setText("🔁")
        self.mode_btn.setToolTip("播放模式")
        self.mode_btn.setIconSize(QSize(24, 24))
        self.mode_btn.clicked.connect(self.toggle_playback_mode)
        control_layout.addWidget(self.mode_btn)
        

        
        self.vlc_btn = QToolButton()
        self.vlc_btn.setText("🎵")
        self.vlc_btn.setToolTip("播放引擎: QMediaPlayer (VLC已移除)")
        self.vlc_btn.setIconSize(QSize(24, 24))
        self.vlc_btn.clicked.connect(self.toggle_vlc_engine)
        control_layout.addWidget(self.vlc_btn)
        
        control_layout.addStretch(1)
        
        prev_btn = QToolButton()
        prev_btn.setText("⏮️")
        prev_btn.setIconSize(QSize(28, 28))
        prev_btn.clicked.connect(self.play_previous)
        control_layout.addWidget(prev_btn)
        
        self.play_pause_btn = QPushButton("▶️")
        self.play_pause_btn.setFixedSize(72, 72)
        self.play_pause_btn.setStyleSheet("""
            QPushButton {
                font-size: 28px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #8B5CF6, stop:1 #7C3AED);
                border-radius: 36px;
                padding: 0px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2=1,
                    stop:0 #A78BFA, stop:1 #8B5CF6);
            }
        """)
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        control_layout.addWidget(self.play_pause_btn)
        
        next_btn = QToolButton()
        next_btn.setText("⏭️")
        next_btn.setIconSize(QSize(28, 28))
        next_btn.clicked.connect(self.play_next)
        control_layout.addWidget(next_btn)
        
        control_layout.addStretch(1)
        
        volume_container = QHBoxLayout()
        volume_container.setSpacing(8)
        
        self.volume_btn = QToolButton()
        self.volume_btn.setText("🔊")
        self.volume_btn.setIconSize(QSize(20, 20))
        volume_container.addWidget(self.volume_btn)
        
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setFixedWidth(80)
        self.volume_slider.setFixedHeight(6)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.valueChanged.connect(self.set_volume)
        volume_container.addWidget(self.volume_slider)
        
        control_layout.addLayout(volume_container)
        control_container.setLayout(control_layout)
        center_layout.addWidget(control_container)
        
        center_panel.setLayout(center_layout)
        main_layout.addWidget(center_panel, 40)
    
    def setup_right_panel(self, main_layout):
        right_panel = QFrame()
        right_panel.setProperty("cardStyle", "true")
        # 使用可动画的最大宽度以支持歌词栏展开/折叠
        # 不设置最大宽度限制，让歌词栏可以根据空间自动扩展
        self.right_panel = right_panel
        self.right_panel_width = 850
        self.right_panel_collapsed = not self.show_embedded_lyrics
        # 根据初始状态设置面板宽度
        right_panel.setFixedWidth(0 if self.right_panel_collapsed else 850)
        
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(16, 12, 16, 12)
        right_layout.setSpacing(8)
        
        header = QHBoxLayout()
        header.setSpacing(8)
        
        lyrics_icon = QLabel("📝")
        lyrics_icon.setStyleSheet("font-size: 16px;")
        header.addWidget(lyrics_icon)
        
        lyrics_title = QLabel("歌词")
        lyrics_title.setObjectName("TitleLabel")
        lyrics_title.setStyleSheet("font-size: 14px; color: #FFFFFF;")
        header.addWidget(lyrics_title)
        header.addStretch()

        right_layout.addLayout(header)

        self.lyrics_display = LyricsWidget()
        self.lyrics_display.setStyleSheet("""
            LyricsWidget {
                background: transparent;
            }
        """)
        right_layout.addWidget(self.lyrics_display, 1)
        
        right_panel.setLayout(right_layout)
        main_layout.addWidget(right_panel, 45)
    
    def setup_player(self):
        self.audio_player = AudioPlayer()
        logger.info(f"setup_player: 设置playlist_widget, self.playlist_widget = {self.playlist_widget}")
        self.audio_player.playlist_widget = self.playlist_widget
        
        self.audio_player.state_changed.connect(self.on_state_changed)
        self.audio_player.position_changed.connect(self.on_position_changed)
        self.audio_player.duration_changed.connect(self.on_duration_changed)
        self.audio_player.media_status_changed.connect(self.on_media_status_changed)
        self.audio_player.current_song_changed.connect(self.on_current_song_changed)
        self.audio_player.status_message_changed.connect(self.on_status_message_changed)
        
        self.audio_player.set_volume(70)
        self.volume_slider.setValue(70)
        # 刷新并载入默认/当前播放列表
        self.refresh_playlists()
        self.select_playlist(self.current_playlist_file)
    
    def toggle_play_pause(self):
        self.audio_player.toggle_play_pause()
    
    def play(self):
        if self.audio_player.current_song_path:
            self.audio_player.play()
        else:
            if self.audio_player.playlist_count > 0:
                self.audio_player.play_by_index(0)

            else:
                QMessageBox.warning(self, "提示", "播放列表为空")
    
    def play_playlist_item(self, item):
        row = self.playlist_widget.row(item)
        self.audio_player.play_by_index(row)
    
    def add_files(self):
        dlg = QFileDialog()
        dlg.setFileMode(QFileDialog.ExistingFiles)
        dlg.setNameFilter("音频文件 (*.mp3 *.wav *.aac *.flac *.m4a *.ogg *.wma)")
        
        if dlg.exec() == QFileDialog.DialogCode.Accepted:
            for file_path in dlg.selectedFiles():
                self.audio_player.add_to_playlist(file_path)
            self.save_playlist()
            self.status_label.setText(f"已添加 {len(dlg.selectedFiles())} 首歌曲")
    
    def remove_selected(self):
        selected_items = self.playlist_widget.selectedItems()
        if not selected_items:
            return
        
        for item in selected_items:
            row = self.playlist_widget.row(item)
            self.audio_player.remove_from_playlist(row)
        
        self.save_playlist()
        self.status_label.setText(f"已移除 {len(selected_items)} 首歌曲")
    
    def clear_playlist(self):
        reply = QMessageBox.question(
            self, "确认", "确定要清空播放列表吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.audio_player.clear_playlist()
            self.save_playlist()
            self.song_info_label.setText("等待播放")
            self.artist_label.setText("选择一首歌曲开始播放")
            self.cover_label.setCoverPixmap(None)
            self.status_label.setText("播放列表已清空")
    
    def filter_playlist(self, text):
        query = text.strip().lower()
        
        for i in range(self.playlist_widget.count()):
            item = self.playlist_widget.item(i)
            if not query:
                item.setHidden(False)
            else:
                item.setHidden(query not in item.text().lower())
    
    def load_playlist(self):
        # 兼容旧接口：加载当前选择的播放列表文件
        if hasattr(self, 'current_playlist_file') and self.current_playlist_file:
            self.audio_player.load_playlist(self.current_playlist_file)
        else:
            # 回退至默认 Data/playlist.json
            base_dir = get_base_path()
            data_dir = os.path.join(base_dir, "Data")
            os.makedirs(data_dir, exist_ok=True)
            playlist_file = os.path.join(data_dir, "playlist.json")
            self.current_playlist_file = playlist_file
            self.audio_player.load_playlist(playlist_file)
    
    def save_playlist(self):
        # 将当前内存播放列表保存到当前选择的播放列表文件
        if not hasattr(self, 'current_playlist_file') or not self.current_playlist_file:
            base_dir = get_base_path()
            self.current_playlist_file = os.path.join(base_dir, 'Data', 'playlist.json')
        self.audio_player.save_playlist(self.current_playlist_file)
    
    def play_next(self):
        self.audio_player.play_next()
    
    def play_previous(self):
        self.audio_player.play_previous()
    
    def on_progress_slider_pressed(self):
        """进度条按下时调用"""
        self.progress_slider_dragging = True
        logger.info("进度条拖动开始")
    
    def on_progress_slider_released(self):
        """进度条释放时调用"""
        self.progress_slider_dragging = False
        position = self.progress_slider.value()
        logger.info(f"进度条拖动结束，跳转到位置: {position}")
        self.audio_player.seek(position)
    
    def seek_position(self, position):
        self.audio_player.seek(position)
    
    def set_volume(self, volume):
        self.audio_player.set_volume(volume)
        if volume == 0:
            self.volume_btn.setText("🔇")
        elif volume < 30:
            self.volume_btn.setText("🔉")
        else:
            self.volume_btn.setText("🔊")
    
    def toggle_playback_mode(self):
        # 切换播放模式
        self.audio_player.cycle_play_mode()
        mode_names = ["顺序播放", "随机播放", "单曲循环"]
        mode_icons = ["🔁", "🔀", "🔂"]
        mode = self.audio_player.play_mode
        
        if mode == 1:  # 随机播放模式
            # 获取当前随机子模式名称
            shuffle_mode_names = ["智能随机", "完全随机", "纯随机"]
            shuffle_mode_name = shuffle_mode_names[self.audio_player.shuffle_mode]
            self.mode_btn.setText("🔀")
            self.mode_btn.setToolTip(f"随机播放 ({shuffle_mode_name})")
            self.play_mode_label.setText(f"随机播放 ({shuffle_mode_name})")
            self.status_label.setText(f"播放模式: 随机播放 ({shuffle_mode_name})")
        else:
            self.mode_btn.setText(mode_icons[mode])
            self.mode_btn.setToolTip(mode_names[mode])
            self.play_mode_label.setText(mode_names[mode])
            self.status_label.setText(f"播放模式: {mode_names[mode]}")
    
    def toggle_shuffle_submode(self):
        """切换随机播放子模式（智能随机/完全随机/纯随机）"""
        if self.audio_player.play_mode == 1:  # 只有在随机播放模式下才切换子模式
            mode_name = self.audio_player.cycle_shuffle_mode()
            shuffle_mode_names = ["智能随机", "完全随机", "纯随机"]
            shuffle_mode_name = shuffle_mode_names[self.audio_player.shuffle_mode]
            self.mode_btn.setText("🔀")
            self.mode_btn.setToolTip(f"随机播放 ({shuffle_mode_name})")
            self.play_mode_label.setText(f"随机播放 ({shuffle_mode_name})")
            self.status_label.setText(f"播放模式: 随机播放 ({shuffle_mode_name})")
            # 清空随机历史
            self.audio_player.shuffle_history = []
        else:
            # 如果不在随机播放模式，切换到随机播放模式
            self.audio_player.set_play_mode(1)
            self.toggle_playback_mode()
    


    def toggle_vlc_engine(self):
        """切换播放引擎（VLC已移除，仅显示信息）"""
        QMessageBox.information(
            self, '播放引擎信息',
            "当前使用纯QMediaPlayer播放引擎\n\n"
            "VLC引擎支持已从当前版本中移除，以简化播放逻辑并提高稳定性。\n"
            "所有音频播放现在完全基于QMediaPlayer实现。\n\n"
            "如果遇到播放问题，请检查音频文件格式或尝试重新安装音频解码器。"
        )
        # 更新按钮状态以反映当前引擎
        self.vlc_btn.setText("🎵")
        self.vlc_btn.setToolTip("播放引擎: QMediaPlayer (VLC已移除)")
        self.vlc_btn.setStyleSheet("""
            QToolButton {
                background: rgba(76, 175, 80, 0.2);
                border-radius: 4px;
            }
        """)
        self.status_label.setText("使用纯QMediaPlayer播放引擎")

    # ---------- 播放列表管理相关 ----------
    def refresh_playlists(self):
        # 列出默认 playlist.json 与 Data/Playlists 下的自定义播放列表
        self.playlist_selector.blockSignals(True)
        self.playlist_selector.clear()
        # 默认播放列表
        default_file = os.path.join(self.data_dir, 'playlist.json')
        self.playlist_selector.addItem('默认播放列表', default_file)

        # 自定义播放列表目录
        try:
            for fname in os.listdir(self.playlists_dir):
                if fname.lower().endswith('.json'):
                    path = os.path.join(self.playlists_dir, fname)
                    display = os.path.splitext(fname)[0]
                    self.playlist_selector.addItem(display, path)
        except Exception as e:
            logger.debug(f"刷新播放列表失败: {e}")

        # 如果 current_playlist_file 在列表中，选中它
        idx = 0
        for i in range(self.playlist_selector.count()):
            if self.playlist_selector.itemData(i) == self.current_playlist_file:
                idx = i
                break
        self.playlist_selector.setCurrentIndex(idx)
        self.playlist_selector.blockSignals(False)

    def on_playlist_selected(self, index):
        path = self.playlist_selector.itemData(index)
        if path:
            self.select_playlist(path)

    def select_playlist(self, file_path):
        # 选择一个播放列表文件并加载
        try:
            if not os.path.isabs(file_path):
                file_path = os.path.join(self.data_dir, file_path)
            # 若文件不存在，创建空播放列表文件
            if not os.path.exists(file_path):
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump({"version":"1.0","playlist":[],"timestamp":time.time(),"current_index":-1}, f, ensure_ascii=False, indent=2)
            self.current_playlist_file = file_path
            self.audio_player.load_playlist(file_path)
            self.audio_player._update_ui_playlist()
            self.status_label.setText(f"已加载播放列表: {os.path.basename(file_path)}")
        except Exception as e:
            logger.error(f"选择播放列表失败: {e}")
            self.status_label.setText("加载播放列表失败")

    def create_new_playlist(self):
        name, ok = QInputDialog.getText(self, '新建播放列表', '播放列表名称:')
        if not ok or not name:
            return
        safe_name = re.sub(r'[^0-9a-zA-Z_\-\u4e00-\u9fff]', '_', name)
        file_name = safe_name + '.json'
        file_path = os.path.join(self.playlists_dir, file_name)
        if os.path.exists(file_path):
            QMessageBox.warning(self, '提示', '播放列表已存在')
            return
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({"version":"1.0","playlist":[],"timestamp":time.time(),"current_index":-1}, f, ensure_ascii=False, indent=2)
            self.refresh_playlists()
            # 选中新创建的
            for i in range(self.playlist_selector.count()):
                if self.playlist_selector.itemData(i) == file_path:
                    self.playlist_selector.setCurrentIndex(i)
                    break
            self.status_label.setText('已创建播放列表')
        except Exception as e:
            logger.error(f"创建播放列表失败: {e}")
            QMessageBox.critical(self, '错误', f'创建失败: {e}')

    def bulk_add_files(self):
        dlg = QFileDialog()
        dlg.setFileMode(QFileDialog.ExistingFiles)
        dlg.setNameFilter('音频文件 (*.mp3 *.wav *.aac *.flac *.m4a *.ogg *.wma)')
        if dlg.exec() == QFileDialog.DialogCode.Accepted:
            added = 0
            for file_path in dlg.selectedFiles():
                if self.audio_player.add_to_playlist(file_path):
                    added += 1
            self.save_playlist()
            self.status_label.setText(f'已批量添加 {added} 首歌曲')

    def auto_add_from_folder(self):
        folder = QFileDialog.getExistingDirectory(self, '选择文件夹')
        if not folder:
            return
        supported = ('.mp3', '.wav', '.aac', '.flac', '.m4a', '.ogg', '.wma')
        added = 0
        for root, dirs, files in os.walk(folder):
            for f in files:
                if f.lower().endswith(supported):
                    full = os.path.join(root, f)
                    if self.audio_player.add_to_playlist(full):
                        added += 1
        self.save_playlist()
        self.status_label.setText(f'已从文件夹识别并添加 {added} 首歌曲')
    
    def on_state_changed(self, state):
        from PyQt5.QtMultimedia import QMediaPlayer
        
        if state == QMediaPlayer.PlayingState:
            self.play_pause_btn.setText("⏸️")
            self.cover_label.setRotating(True)
            self.status_label.setText("正在播放")
        else:
            self.play_pause_btn.setText("▶️")
            self.cover_label.setRotating(False)
            if state == QMediaPlayer.PausedState:
                self.status_label.setText("已暂停")
            else:
                self.status_label.setText("已停止")
    
    def on_position_changed(self, position):
        # 如果正在拖动进度条，跳过自动更新，避免冲突
        if not self.progress_slider_dragging:
            duration = self.audio_player.duration
            if duration > 0:
                self.progress_slider.setValue(position)
        self.current_time_label.setText(AudioPlayer.format_time(position))
    
    def on_duration_changed(self, duration):
        self.progress_slider.setRange(0, duration)
        self.total_time_label.setText(AudioPlayer.format_time(duration))
    
    def on_media_status_changed(self, status):
        from PyQt5.QtMultimedia import QMediaPlayer
        
        status_map = {
            QMediaPlayer.NoMedia: "无媒体",
            QMediaPlayer.LoadingMedia: "加载中...",
            QMediaPlayer.LoadedMedia: "准备就绪",
            QMediaPlayer.StalledMedia: "播放卡顿",
            QMediaPlayer.BufferingMedia: "缓冲中...",
            QMediaPlayer.BufferedMedia: "已缓冲",
            QMediaPlayer.EndOfMedia: "播放结束",
            QMediaPlayer.InvalidMedia: "无法播放"
        }
        
        if status in status_map:
            self.status_label.setText(status_map[status])
    
    def on_current_song_changed(self, song_info):
        if song_info:
            name = song_info.get('title', song_info.get('name', '未知'))
            artist = song_info.get('author', song_info.get('artists', ''))
            self.song_info_label.setText(name)
            self.artist_label.setText(artist if artist else "未知艺术家")
            
            self.load_lyrics_for_file(song_info)
            self.load_cover_for_file(song_info)
    
    def on_status_message_changed(self, message):
        self.status_label.setText(message)
    
    def load_lyrics_for_file(self, song_info_or_path):
        """
        优先从 `song_info` 中的 `lyrics_path` / `lrc` 字段加载歌词；
        若不存在则回退到根据文件名在默认数据目录查找。
        """
        self.lyrics_data = []

        # 支持传入 song_info dict 或直接的文件路径字符串
        song_info = None
        if isinstance(song_info_or_path, dict):
            song_info = song_info_or_path
            file_path = song_info.get('path', '')
        else:
            file_path = song_info_or_path or ''

        # 1) song_info 中指定的歌词路径
        lyrics_candidates = []
        if song_info:
            lp = song_info.get('lyrics_path') or song_info.get('lrc') or song_info.get('lyrics')
            if lp:
                lyrics_candidates.append(lp)

        # 2) 根据文件名的默认位置
        if file_path:
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            lyrics_candidates.extend([
                os.path.join('Data', 'Lyrics', base_name + '.lrc'),
                os.path.join('Data', 'Lyrics', os.path.basename(file_path).replace('.mp3', '.lrc')),
                os.path.join('Lyrics', base_name + '.lrc'),
            ])

        found = False
        for lrc_path in lyrics_candidates:
            # 如果是相对路径且存在 Data 目录，尝试补全
            try_paths = [lrc_path]
            if not os.path.isabs(lrc_path):
                base_dir = get_base_path()
                try_paths.insert(0, os.path.join(base_dir, lrc_path))

            for p in try_paths:
                if os.path.exists(p):
                    try:
                        with open(p, 'r', encoding='utf-8') as f:
                            self.parse_lyrics(f.read())
                        found = True
                        self.status_label.setText("已加载歌词")
                        break
                    except Exception as e:
                        logger.error(f"加载歌词失败: {e}")
            if found:
                break

        if not found:
            # 未找到歌词，清空展示并提示
            self.lyrics_data = []
            if hasattr(self.lyrics_display, 'clear_lyrics'):
                self.lyrics_display.clear_lyrics()
            else:
                self.lyrics_display.clear()
            # 清空外置歌词窗口
            if self.external_lyrics_window and hasattr(self.external_lyrics_window, 'clear_lyrics'):
                self.external_lyrics_window.clear_lyrics()
            self.status_label.setText("未找到歌词")
    
    def parse_lyrics(self, text):
        pattern = re.compile(r'\[(\d+):(\d+\.\d+)\](.*)')
        lines = text.splitlines()
        time_points = []
        
        for line in lines:
            match = pattern.match(line)
            if match:
                minutes, seconds, lyric_text = match.groups()
                start_time = int(minutes) * 60 + float(seconds)
                time_points.append((start_time, lyric_text.strip()))
        
        time_points.sort(key=lambda x: x[0])
        
        for i, (start_time, lyric_text) in enumerate(time_points):
            end_time = time_points[i + 1][0] if i + 1 < len(time_points) else start_time + 10
            self.lyrics_data.append((start_time, end_time, lyric_text))
        
        if hasattr(self.lyrics_display, 'set_lyrics'):
            self.lyrics_display.set_lyrics(self.lyrics_data)
        
        # 加载歌词数据到外置歌词窗口
        if self.external_lyrics_window and hasattr(self.external_lyrics_window, 'load_lyrics_data'):
            # 注意：需要将时间从秒转换为毫秒
            lyrics_data_ms = [(start * 1000, end * 1000, text) for start, end, text in self.lyrics_data]
            self.external_lyrics_window.load_lyrics_data(lyrics_data_ms)
    
    def load_cover_for_file(self, song_info_or_path):
        """
        优先从 `song_info` 中的 `cover_path`/`pic` 字段加载封面；
        若不存在则回退到根据文件名在默认数据目录查找。
        """
        pixmap = None

        song_info = None
        if isinstance(song_info_or_path, dict):
            song_info = song_info_or_path
            file_path = song_info.get('path', '')
        else:
            file_path = song_info_or_path or ''

        cover_candidates = []
        if song_info:
            cp = song_info.get('cover_path') or song_info.get('pic') or song_info.get('cover') or song_info.get('image')
            if cp:
                cover_candidates.append(cp)

        if file_path:
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            cover_candidates.extend([
                os.path.join('Data', 'Pics', base_name + '.jpg'),
                os.path.join('Data', 'Pics', os.path.basename(file_path).replace('.mp3', '.jpg')),
                os.path.join('Pics', base_name + '.jpg'),
                os.path.join('covers', base_name + '.jpg'),
            ])

        found = False
        base_dir = get_base_path()

        # 如果没有在 song_info 中找到封面，尝试在 Data/Pics 中按严格文件名匹配
        if not cover_candidates and file_path:
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            pics_dir = os.path.join(base_dir, 'Data', 'Pics')
            try:
                if os.path.isdir(pics_dir):
                    # 严格匹配：文件名（不含扩展）完全等于歌曲 base_name，支持 jpg/jpeg/png
                    pattern = re.compile(rf'^{re.escape(base_name)}\.(jpg|jpeg|png)$', re.IGNORECASE)
                    for fname in os.listdir(pics_dir):
                        if pattern.match(fname):
                            candidate = os.path.join(pics_dir, fname)
                            pm = QPixmap(candidate)
                            if not pm.isNull():
                                pixmap = pm
                                found = True
                                break
            except Exception as e:
                logger.debug(f"在 Data/Pics 中查找封面时出错: {e}")

        # 如果有指定候选路径（来自 song_info 或回退列表），按此前逻辑检查
        if not found:
            for pic_path in cover_candidates:
                try_paths = [pic_path]
                if not os.path.isabs(pic_path):
                    try_paths.insert(0, os.path.join(base_dir, pic_path))

                for p in try_paths:
                    if os.path.exists(p):
                        pm = QPixmap(p)
                        if not pm.isNull():
                            pixmap = pm
                            found = True
                            break
                if found:
                    break

        # 若仍未找到，根据设置决定是否使用 Data/default.jpg 作为占位封面
        use_default_cover = True
        try:
            cfg_val = self.config_manager.get_config("features.use_default_cover")
            if cfg_val is not None:
                use_default_cover = bool(cfg_val)
        except Exception:
            use_default_cover = True

        if not found and use_default_cover:
            default_pic = os.path.join(base_dir, 'Data', 'default.jpg')
            if os.path.exists(default_pic):
                pm = QPixmap(default_pic)
                if not pm.isNull():
                    pixmap = pm
                    found = True
                    self.status_label.setText("使用默认封面")
            else:
                self.status_label.setText("未找到封面，且默认封面缺失")
        elif not found and not use_default_cover:
            # 用户选择不使用默认封面，保持音乐符图标（即不设置 pixmap）
            self.status_label.setText("未启用默认封面")

        if pixmap and not pixmap.isNull():
            self.cover_label.setCoverPixmap(pixmap)
            if not self.status_label.text().startswith("使用默认"):
                self.status_label.setText("已加载封面")
        else:
            self.cover_label.setCoverPixmap(None)
    
    def update_lyrics(self):
        if not self.lyrics_data:
            return
        
        position = self.audio_player.position
        position_ms = position
        
        if hasattr(self.lyrics_display, 'update_position'):
            self.lyrics_display.update_position(position_ms)
        
        # 更新外置歌词窗口
        if self.external_lyrics_window and hasattr(self.external_lyrics_window, 'update_position'):
            self.external_lyrics_window.update_position(position_ms)

    def toggle_left_panel(self):
        """折叠/展开左侧播放列表面板，并同步中部折叠入口的显示状态（带动画）。"""
        try:
            start = 0
            end = 0
            if getattr(self, 'left_panel_collapsed', False):
                # 从折叠状态展开
                start = 0
                end = self.left_panel_width
                if hasattr(self, 'playlist_fold_btn'):
                    self.playlist_fold_btn.setText('◀')
                    self.playlist_fold_btn.setToolTip('收起播放列表')
                self.left_panel_collapsed = False
                
                # 展开左侧面板时增加窗口宽度，保持位置不变
                new_width = self.width() + self.left_panel_width
                self.resize(new_width, self.height())
            else:
                # 从展开状态折叠
                start = self.left_panel_width
                end = 0
                if hasattr(self, 'playlist_fold_btn'):
                    self.playlist_fold_btn.setText('▶')
                    self.playlist_fold_btn.setToolTip('展开播放列表')
                self.left_panel_collapsed = True
                
                # 折叠左侧面板时减少窗口宽度，保持位置不变
                new_width = max(500, self.width() - self.left_panel_width)
                self.resize(new_width, self.height())

            anim = QPropertyAnimation(self.left_panel, b"maximumWidth")
            anim.setDuration(260)
            anim.setStartValue(start)
            anim.setEndValue(end)
            anim.setEasingCurve(QEasingCurve.InOutCubic)
            anim.start()
            # 保持引用，避免被垃圾回收导致动画停止
            self._left_panel_anim = anim
        except Exception as e:
            logger.error(f"切换左侧面板失败: {e}")
    
    def on_toggle_lyrics_checkbox(self, state):
        """通过复选框切换歌词面板显示"""
        enabled = bool(state == Qt.Checked)
        self.show_embedded_lyrics = enabled
        
        try:
            if not hasattr(self, 'right_panel') or self.right_panel is None:
                return
            
            if enabled:
                # 显示歌词
                self.right_panel.setFixedWidth(self.right_panel_width)
                # 恢复窗口宽度，保持位置不变
                if hasattr(self, '_window_width_without_lyrics') and self._window_width_without_lyrics:
                    new_width = self._window_width_without_lyrics
                    self._window_width_without_lyrics = None
                    self.resize(new_width, self.height())
                else:
                    # 如果没有保存的宽度，增加窗口宽度，保持位置不变
                    new_width = self.width() + self.right_panel_width
                    self.resize(new_width, self.height())
            else:
                # 隐藏歌词
                self._window_width_without_lyrics = self.width()
                self.right_panel.setFixedWidth(0)
                # 缩小窗口，保持位置不变
                new_width = max(500, self.width() - self.right_panel_width)
                self.resize(new_width, self.height())
            
            # 保存设置
            self.config_manager.set_config("features.show_embedded_lyrics", enabled)
                
        except Exception as e:
            print(f"切换歌词面板失败: {e}")

    def on_toggle_external_lyrics(self):
        """切换外置歌词窗口显示"""
        if not self.external_lyrics_window:
            return
            
        if self.external_lyrics_window.isVisible():
            self.external_lyrics_window.hide()
            self.external_lyrics_btn.setChecked(False)
        else:
            self.external_lyrics_window.show()
            self.external_lyrics_btn.setChecked(True)
            # 如果当前有歌词数据，将其加载到外置歌词窗口
            if self.lyrics_data and hasattr(self.external_lyrics_window, 'load_lyrics_data'):
                lyrics_data_ms = [(start * 1000, end * 1000, text) for start, end, text in self.lyrics_data]
                self.external_lyrics_window.load_lyrics_data(lyrics_data_ms)

    def on_search_lyrics(self):
        """打开歌词搜索对话框"""
        if not self.audio_player.current_song_info:
            QMessageBox.information(self, "提示", "请先选择一首歌曲")
            return
            
        song_title = self.audio_player.current_song_info.get('title', '')
        artist = self.audio_player.current_song_info.get('artist', '')
        
        if not song_title:
            song_title = os.path.splitext(os.path.basename(
                self.audio_player.current_song_info.get('path', '')
            ))[0]
        
        dialog = LyricsSearchDialog(song_title, artist, self.config_manager, self)
        dialog.lyrics_ready.connect(self.on_lyrics_search_result)
        dialog.exec_()
        
    def on_lyrics_search_result(self, lrc_content: str):
        """处理歌词搜索结果"""
        if not lrc_content:
            return
            
        self.lyrics_data = []
        self.parse_lyrics(lrc_content)
        
        # 保存歌词到文件
        if self.audio_player.current_song_info:
            file_path = self.audio_player.current_song_info.get('path', '')
            if file_path:
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                lrc_path = os.path.join('Data', 'Lyrics', base_name + '.lrc')
                
                base_dir = get_base_path()
                full_lrc_path = os.path.join(base_dir, lrc_path)
                
                os.makedirs(os.path.dirname(full_lrc_path), exist_ok=True)
                
                try:
                    with open(full_lrc_path, 'w', encoding='utf-8') as f:
                        f.write(lrc_content)
                    self.status_label.setText("歌词已保存")
                except Exception as e:
                    logger.error(f"保存歌词失败: {e}")

    def on_toggle_default_cover(self, state):
        enabled = bool(state == Qt.Checked)
        try:
            self.config_manager.set_config("features.use_default_cover", enabled)
            # 重新加载当前歌曲封面以反映新设置
            if self.audio_player and self.audio_player.current_song_info:
                self.load_cover_for_file(self.audio_player.current_song_info)
        except Exception as e:
            logger.error(f"保存默认封面设置失败: {e}")

    def on_edit_song_name(self):
        # 编辑当前歌曲的显示名称，并可选择同时重命名本地文件；修改后同步保存到 playlist.json
        song_info = None
        if self.audio_player:
            song_info = self.audio_player.current_song_info

        if not song_info:
            QMessageBox.warning(self, "提示", "当前没有正在播放的歌曲可编辑")
            return

        current_title = song_info.get('title') or song_info.get('filename') or ''
        new_title, ok = QInputDialog.getText(self, "编辑歌名", "新歌名：", QLineEdit.Normal, current_title)
        if not ok:
            return

        new_title = new_title.strip()
        if not new_title:
            QMessageBox.warning(self, "提示", "歌名不能为空")
            return

        if new_title == current_title:
            return

        # 询问是否同时重命名本地文件
        reply = QMessageBox.question(self, "重命名文件", "是否同时重命名本地文件？", QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        rename_file = (reply == QMessageBox.Yes)

        old_path = song_info.get('path')
        new_path = None
        if rename_file and old_path and os.path.exists(old_path):
            dir_name = os.path.dirname(old_path)
            _, ext = os.path.splitext(old_path)
            candidate = os.path.join(dir_name, new_title + ext)
            if os.path.exists(candidate):
                QMessageBox.warning(self, "提示", f"目标文件已存在：{candidate}")
                return
            try:
                os.rename(old_path, candidate)
                new_path = candidate
            except Exception as e:
                QMessageBox.critical(self, "错误", f"重命名文件失败: {e}")
                logger.error(f"重命名文件失败: {e}")
                return

        # 更新 playlist 中的条目
        # 查找当前歌曲在播放列表中的索引
        idx = -1
        for i, s in enumerate(self.audio_player.playlist):
            if s.get('path') == old_path or (new_path and s.get('path') == new_path):
                idx = i
                break

        # 修改 song_info
        song_info['title'] = new_title
        if new_path:
            song_info['path'] = new_path
            song_info['filename'] = os.path.basename(new_path)

        # 如果在播放列表中，更新并刷新 UI 列表项
        if idx != -1 and self.playlist_widget is not None and idx < self.playlist_widget.count():
            item = self.playlist_widget.item(idx)
            if item:
                item.setText(new_title)
                item.setData(Qt.UserRole, song_info)

        # 更新显示与保存playlist.json
        self.song_info_label.setText(new_title)
        try:
            self.save_playlist()
            self.status_label.setText("已更新歌名并保存播放列表")
        except Exception as e:
            logger.error(f"保存播放列表失败: {e}")
            QMessageBox.warning(self, "提示", f"保存播放列表失败: {e}")
    
    def closeEvent(self, event):
        self.cover_label.setRotating(False)
        self.audio_player.cleanup()
        self.save_playlist()
        event.accept()


def main():
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    config_manager = ConfigManager()
    window = MusicPlayerWindow(config_manager)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
