"""
音乐下载模块
提供音乐搜索和下载功能，支持可配置的API
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import re
import requests
import logging
import logging.handlers
import traceback
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QListWidget, QListWidgetItem, QProgressBar, QMessageBox, QComboBox,
    QGroupBox, QFormLayout, QFileDialog, QFrame, QDialog, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QSpinBox, QCheckBox, QAction, QMenu
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtGui import QFont, QIcon, QPixmap, QColor, QLinearGradient, QPainter

import importlib.util
def import_module_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None:
        raise ImportError(f"无法从路径 {file_path} 加载模块规范")
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise ImportError(f"无法从路径 {file_path} 获取加载器")
    spec.loader.exec_module(module)
    return module

def import_ui_components():
    ui_components = {}
    
    modern_btn_code = '''
from PyQt5.QtWidgets import QPushButton, QFrame, QLineEdit, QProgressBar, QListWidget
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont

class ModernButton(QPushButton):
    def __init__(self, text, parent=None, icon=None):
        super().__init__(text, parent)
        self.setMinimumHeight(48)
        self.setFont(QFont("Microsoft YaHei UI", 11, QFont.Medium))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if icon:
            self.setIcon(icon)
            self.setIconSize(QSize(20, 20))
        self.setStyleSheet("""
            QPushButton { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366F1, stop:0.5 #8B5CF6, stop:1 #7C3AED); color: white; border: none; border-radius: 14px; padding: 12px 24px; font-weight: 600; font-size: 14px; letter-spacing: 0.5px; }
            QPushButton:hover { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4F46E5, stop:0.5 #7C3AED, stop:1 #6D28D9); }
            QPushButton:pressed { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4338CA, stop:0.5 #5B21B6, stop:1 #4C1D95); }
            QPushButton:disabled { background-color: #CBD5E1; color: #94A3B8; }
        """)

class GlowButton(QPushButton):
    def __init__(self, text, parent=None, color="#10B981"):
        super().__init__(text, parent)
        self.setMinimumHeight(44)
        self.setFont(QFont("Microsoft YaHei UI", 11, QFont.Medium))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"QPushButton {{ background-color: {color}; color: white; border: none; border-radius: 12px; padding: 10px 20px; font-weight: 600; }}")

class ModernCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("QFrame { background-color: rgba(255, 255, 255, 0.95); border-radius: 20px; border: 1px solid rgba(226, 232, 240, 0.8); }")

class ModernLineEdit(QLineEdit):
    def __init__(self, placeholder="", parent=None):
        super().__init__(placeholder, parent)
        self.setFont(QFont("Microsoft YaHei UI", 13))
        self.setStyleSheet("QLineEdit { background-color: rgba(248, 250, 252, 0.9); border: 2px solid #E2E8F0; border-radius: 14px; padding: 14px 18px; font-size: 14px; color: #1E293B; selection-background-color: #6366F1; selection-color: white; } QLineEdit:focus { border-color: #6366F1; background-color: #FFFFFF; } QLineEdit:hover { border-color: #CBD5E1; background-color: #FFFFFF; } QLineEdit::placeholder { color: #94A3B8; }")

class PulseProgressBar(QProgressBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("QProgressBar { border: none; border-radius: 10px; text-align: center; height: 12px; background-color: rgba(241, 245, 249, 0.9); font-size: 11px; font-weight: 600; color: #6366F1; } QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366F1, stop:0.5 #8B5CF6, stop:1 #A855F7); border-radius: 10px; }")

class ModernListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QFont("Microsoft YaHei UI", 12))
        self.setStyleSheet("QListWidget { border: none; border-radius: 16px; padding: 12px; background-color: rgba(248, 250, 252, 0.5); outline: none; } QListWidget::item { padding: 14px 16px; border-radius: 12px; margin: 4px 0; background-color: rgba(255, 255, 255, 0.8); border: 1px solid transparent; } QListWidget::item:hover { background-color: rgba(99, 102, 241, 0.08); border-color: rgba(99, 102, 241, 0.2); } QListWidget::item:selected { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(99, 102, 241, 0.15), stop:1 rgba(139, 92, 246, 0.15)); border: 2px solid #6366F1; font-weight: 600; color: #6366F1; }")
'''
    
    exec(modern_btn_code, ui_components)
    
    return ui_components

ui_components = import_ui_components()
ModernButton = ui_components['ModernButton']
GlowButton = ui_components['GlowButton']
ModernCard = ui_components['ModernCard']
ModernLineEdit = ui_components['ModernLineEdit']
PulseProgressBar = ui_components['PulseProgressBar']
ModernListWidget = ui_components['ModernListWidget']

import importlib.util
def import_module_from_path(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None:
        raise ImportError(f"无法从路径 {file_path} 加载模块规范")
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise ImportError(f"无法从路径 {file_path} 获取加载器")
    spec.loader.exec_module(module)
    return module

def setup_logging():
    """设置日志记录，同时输出到控制台和文件"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_dir = os.path.join(base_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, "music_download.log")
    
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    
    if logger.handlers:
        logger.handlers.clear()
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_file, when='midnight', interval=1, backupCount=7, encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

logger = setup_logging()

crawler = import_module_from_path("crawler", os.path.join(os.path.dirname(__file__), "crawler.py"))
load_settings = crawler.load_settings
save_settings = crawler.save_settings
get_active_source_config = crawler.get_active_source_config
get_source_names = crawler.get_source_names


class MusicSearchThread(QThread):
    """音乐搜索线程"""
    search_finished = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(int)
    
    def __init__(self, keyword, source_name, max_results=20):
        super().__init__()
        self.keyword = keyword
        self.source_name = source_name
        self.max_results = max_results
    
    def run(self):
        try:
            self.progress_updated.emit(30)
            
            crawler_instance = crawler.MusicCrawler()
            result = crawler_instance.search(self.keyword, self.source_name, self.max_results)
            
            songs = result.get("data", [])
            formatted_songs = []
            
            for song in songs:
                formatted_songs.append({
                    "id": song.get("songid", ""),
                    "title": song.get("title", "未知歌曲"),
                    "author": song.get("author", "未知艺术家"),
                    "duration": song.get("duration", "00:00"),
                    "album": song.get("album", "未知专辑"),
                    "url": song.get("url", ""),
                    "pic": song.get("pic", ""),
                    "lrc": song.get("lrc", "")
                })
            
            self.progress_updated.emit(100)
            self.search_finished.emit(formatted_songs)
            
        except Exception as e:
            error_msg = f"音乐搜索线程出错: {str(e)}"
            logger.error(error_msg)
            logger.error(f"异常详情:\n{traceback.format_exc()}")
            logger.error(f"搜索参数: 关键词='{self.keyword}', 音源='{self.source_name}', 最大结果={self.max_results}")
            self.error_occurred.emit(str(e))
            self.progress_updated.emit(100)


class MusicDownloadThread(QThread):
    """音乐下载线程"""
    download_progress = pyqtSignal(int)
    download_finished = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, url, file_path):
        super().__init__()
        self.url = url
        self.file_path = file_path
    
    def run(self):
        try:
            crawler_instance = crawler.MusicCrawler()
            
            def progress_callback(progress):
                self.download_progress.emit(progress)
            
            success = crawler_instance.download(self.url, self.file_path, progress_callback)
            
            if success:
                self.download_finished.emit(self.file_path)
            else:
                self.error_occurred.emit("下载失败")
                
        except Exception as e:
            error_msg = f"音乐下载线程出错: {str(e)}"
            logger.error(error_msg)
            logger.error(f"异常详情:\n{traceback.format_exc()}")
            logger.error(f"下载参数: URL='{self.url}', 文件路径='{self.file_path}'")
            self.error_occurred.emit(str(e))


class SettingsDialog(QDialog):
    """设置对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ 设置")
        self.setGeometry(200, 200, 650, 500)
        self.settings = load_settings()
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        
        self.tabs = QTabWidget()
        
        save_tab = QWidget()
        save_layout = QVBoxLayout()
        
        save_group = QGroupBox("📁 保存位置")
        save_form = QFormLayout()
        
        self.music_dir_edit = QLineEdit()
        self.music_dir_btn = QPushButton("浏览...")
        self.music_dir_btn.clicked.connect(lambda: self.select_directory(self.music_dir_edit))
        
        self.cache_dir_edit = QLineEdit()
        self.cache_dir_btn = QPushButton("浏览...")
        self.cache_dir_btn.clicked.connect(lambda: self.select_directory(self.cache_dir_edit))
        
        row1 = QHBoxLayout()
        row1.addWidget(self.music_dir_edit)
        row1.addWidget(self.music_dir_btn)
        w1 = QWidget()
        w1.setLayout(row1)
        save_form.addRow("音乐保存位置:", w1)
        
        row2 = QHBoxLayout()
        row2.addWidget(self.cache_dir_edit)
        row2.addWidget(self.cache_dir_btn)
        w2 = QWidget()
        w2.setLayout(row2)
        save_form.addRow("缓存文件位置:", w2)
        
        save_group.setLayout(save_form)
        save_layout.addWidget(save_group)
        
        other_group = QGroupBox("⚡ 其他设置")
        other_form = QFormLayout()
        
        self.max_results_spin = QSpinBox()
        self.max_results_spin.setRange(5, 100)
        
        self.auto_play_check = QCheckBox("下载后自动播放")
        
        other_form.addRow("最大搜索结果:", self.max_results_spin)
        other_form.addRow(self.auto_play_check)
        
        other_group.setLayout(other_form)
        save_layout.addWidget(other_group)
        save_layout.addStretch()
        save_tab.setLayout(save_layout)
        
        source_tab = QWidget()
        source_layout = QVBoxLayout()
        
        source_group = QGroupBox("🎵 当前音源")
        source_form = QFormLayout()
        
        self.source_combo = QComboBox()
        self.source_combo.addItems(get_source_names())
        
        source_form.addRow("选择音源:", self.source_combo)
        source_group.setLayout(source_form)
        source_layout.addWidget(source_group)
        
        source_layout.addStretch()
        source_tab.setLayout(source_layout)
        
        self.tabs.addTab(save_tab, "保存设置")
        self.tabs.addTab(source_tab, "音源设置")
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.save_btn = QPushButton("💾 保存")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A90D9;
                color: white;
                padding: 8px 20px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #5BA0E9; }
        """)
        self.save_btn.clicked.connect(self.save_settings)
        
        self.cancel_btn = QPushButton("❌ 取消")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #95A5A6;
                color: white;
                padding: 8px 20px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #BDC3C7; }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addWidget(self.tabs)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def select_directory(self, edit):
        directory = QFileDialog.getExistingDirectory(self, "选择目录")
        if directory:
            edit.setText(directory)
    
    def load_settings(self):
        try:
            self.music_dir_edit.setText(self.settings["save_paths"]["music"])
            self.cache_dir_edit.setText(self.settings["save_paths"]["cache"])
            self.max_results_spin.setValue(self.settings["other"]["max_results"])
            self.auto_play_check.setChecked(self.settings["other"]["auto_play"])
            self.source_combo.setCurrentText(self.settings["sources"]["active_source"])
            logger.info("设置对话框加载设置成功")
        except Exception as e:
            error_msg = f"设置对话框加载设置失败: {str(e)}"
            logger.error(error_msg)
            logger.error(f"异常详情:\n{traceback.format_exc()}")
            QMessageBox.warning(self, "警告", f"加载设置失败: {str(e)}")
    
    def save_settings(self):
        try:
            self.settings["save_paths"]["music"] = self.music_dir_edit.text()
            self.settings["save_paths"]["cache"] = self.cache_dir_edit.text()
            self.settings["other"]["max_results"] = self.max_results_spin.value()
            self.settings["other"]["auto_play"] = self.auto_play_check.isChecked()
            self.settings["sources"]["active_source"] = self.source_combo.currentText()
            
            logger.info(f"正在保存设置: 音乐目录={self.settings['save_paths']['music']}, 音源={self.settings['sources']['active_source']}")
            
            success = save_settings(self.settings)
            if success:
                logger.info("设置保存成功")
                self.accept()
            else:
                error_msg = "设置保存失败，请检查日志"
                logger.error(error_msg)
                QMessageBox.critical(self, "错误", error_msg)
        except Exception as e:
            error_msg = f"设置保存失败: {str(e)}"
            logger.error(error_msg)
            logger.error(f"异常详情:\n{traceback.format_exc()}")
            QMessageBox.critical(self, "错误", error_msg)


class MusicDownloadWindow(QWidget):
    """音乐下载窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎵 音乐下载器")
        self.setGeometry(100, 100, 900, 750)
        self.search_results = []
        self.current_song = None
        self.download_thread = None
        self.search_thread = None
        try:
            self.settings = load_settings()
            logger.info("音乐下载窗口初始化，设置加载成功")
        except Exception as e:
            error_msg = f"音乐下载窗口初始化失败，加载设置出错: {str(e)}"
            logger.error(error_msg)
            logger.error(f"异常详情:\n{traceback.format_exc()}")
            QMessageBox.critical(self, "错误", f"初始化失败: {str(e)}\n使用默认设置继续运行。")
            self.settings = {
                "save_paths": {
                    "music": os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Songs"),
                    "cache": os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")
                },
                "sources": {
                    "active_source": "QQ音乐",
                    "sources_list": []
                },
                "other": {
                    "max_results": 20,
                    "auto_play": False
                }
            }
        
        self.setup_ui()
        self.setup_styles()
    
    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(24)
        
        header = QLabel("🎵 音乐搜索与下载")
        header.setFont(QFont("Microsoft YaHei UI", 26, QFont.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("""
            QLabel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2=0,
                    stop:0 #6366F1, stop:0.3 #8B5CF6, stop:0.7 #A855F7, stop:1 #C084FC);
                color: white;
                border-radius: 24px;
                font-size: 28px;
                padding: 24px;
                box-shadow: 0 8px 32px rgba(99, 102, 241, 0.4);
            }
        """)
        header.setFixedHeight(90)
        main_layout.addWidget(header)
        
        search_card = ModernCard()
        search_layout = QHBoxLayout()
        search_layout.setSpacing(16)
        search_layout.setContentsMargins(20, 20, 20, 20)
        
        self.source_combo = QComboBox()
        self.source_combo.addItems(get_source_names())
        self.source_combo.setCurrentText(self.settings["sources"]["active_source"])
        self.source_combo.setFont(QFont("Microsoft YaHei UI", 12))
        self.source_combo.setStyleSheet("""
            QComboBox {
                padding: 14px 18px;
                border: 2px solid #E2E8F0;
                border-radius: 14px;
                min-width: 150px;
                background-color: white;
                color: #1E293B;
                font-size: 14px;
                font-weight: 500;
                selection-background-color: #6366F1;
                selection-color: white;
            }
            QComboBox:hover {
                border-color: #CBD5E1;
                background-color: #F8FAFC;
            }
            QComboBox:focus {
                border-color: #6366F1;
                box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.1);
            }
            QComboBox::drop-down {
                border: none;
                width: 36px;
            }
            QComboBox::down-arrow {
                border-left: 6px solid transparent;
                border-right: 6px solid transparent;
                border-top: 8px solid #94A3B8;
                margin-right: 12px;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #F1F5F9;
                background-color: white;
                padding: 10px 0;
                selection-background-color: #6366F1;
                selection-color: white;
                border-radius: 12px;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
            }
            QComboBox QAbstractItemView::item {
                padding: 14px 20px;
                margin: 2px 8px;
                border-radius: 8px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #F1F5F9;
            }
        """)
        
        self.search_input = ModernLineEdit("")
        self.search_input.setPlaceholderText("🔍 输入歌曲名称、歌手名...")
        self.search_input.setMinimumWidth(300)
        self.search_input.textChanged.connect(self.on_search_text_changed)
        self.search_input.returnPressed.connect(self.start_search)
        
        self.clear_btn = QPushButton("✕")
        self.clear_btn.setFixedSize(40, 40)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 18px;
                color: #94A3B8;
                border-radius: 12px;
            }
            QPushButton:hover {
                color: #EF4444;
                background-color: #FEE2E2;
            }
            QPushButton:pressed {
                color: #DC2626;
                background-color: #FECACA;
            }
        """)
        self.clear_btn.clicked.connect(self.clear_search)
        self.clear_btn.setVisible(False)
        
        self.search_btn = ModernButton("🔍 搜索音乐")
        self.search_btn.setMinimumWidth(140)
        self.search_btn.clicked.connect(self.start_search)
        
        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setFixedSize(52, 52)
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(241, 245, 249, 0.9);
                color: #64748B;
                border: 2px solid #E2E8F0;
                border-radius: 16px;
                font-size: 22px;
            }
            QPushButton:hover {
                background-color: #6366F1;
                color: white;
                border-color: #6366F1;
                box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3);
            }
            QPushButton:pressed {
                background-color: #4F46E5;
            }
        """)
        self.settings_btn.clicked.connect(self.open_settings)
        
        search_layout.addWidget(self.source_combo)
        search_layout.addWidget(self.search_input, 1)
        search_layout.addWidget(self.clear_btn)
        search_layout.addWidget(self.search_btn)
        search_layout.addWidget(self.settings_btn)
        
        search_card.setLayout(search_layout)
        main_layout.addWidget(search_card)
        
        results_area = QHBoxLayout()
        results_area.setSpacing(24)
        
        list_card = ModernCard()
        list_layout = QVBoxLayout()
        list_layout.setContentsMargins(20, 20, 20, 20)
        list_layout.setSpacing(12)
        
        list_header = QHBoxLayout()
        list_icon = QLabel("📋")
        list_icon.setStyleSheet("font-size: 20px;")
        list_title = QLabel("搜索结果")
        list_title.setFont(QFont("Microsoft YaHei UI", 16, QFont.Bold))
        list_title.setStyleSheet("color: #1E293B;")
        list_count = QLabel("0 首")
        list_count.setFont(QFont("Microsoft YaHei UI", 12))
        list_count.setStyleSheet("color: #94A3B8;")
        list_header.addWidget(list_icon)
        list_header.addWidget(list_title)
        list_header.addWidget(list_count)
        list_header.addStretch()
        
        list_layout.addLayout(list_header)
        
        self.results_list = ModernListWidget()
        self.results_list.setIconSize(QSize(56, 56))
        self.results_list.itemClicked.connect(self.on_song_selected)
        self.results_list.itemDoubleClicked.connect(self.download_song)
        list_layout.addWidget(self.results_list)
        
        list_card.setLayout(list_layout)
        results_area.addWidget(list_card, 1)
        
        detail_card = ModernCard()
        detail_layout = QVBoxLayout()
        detail_layout.setContentsMargins(24, 24, 24, 24)
        detail_layout.setSpacing(20)
        
        detail_header = QHBoxLayout()
        detail_icon = QLabel("🎵")
        detail_icon.setStyleSheet("font-size: 20px;")
        detail_title = QLabel("歌曲详情")
        detail_title.setFont(QFont("Microsoft YaHei UI", 16, QFont.Bold))
        detail_title.setStyleSheet("color: #1E293B;")
        detail_header.addWidget(detail_icon)
        detail_header.addWidget(detail_title)
        detail_header.addStretch()
        detail_layout.addLayout(detail_header)
        
        self.song_info = QLabel("""<div style="text-align: center; padding: 30px; color: #94A3B8; font-size: 15px;">
            <div style="font-size: 48px; margin-bottom: 16px;">🎧</div>
            选择一首歌曲查看详情<br>
            <span style="font-size: 13px;">双击即可下载</span>
        </div>""")
        self.song_info.setWordWrap(True)
        self.song_info.setFont(QFont("Microsoft YaHei UI", 13))
        self.song_info.setStyleSheet("""
            QLabel {
                background: qlineargradient(135deg, #F8FAFC 0%, #F1F5F9 100%);
                border-radius: 20px;
                padding: 24px;
                font-size: 14px;
                color: #475569;
                line-height: 1.8;
                border: 2px dashed #E2E8F0;
            }
        """)
        detail_layout.addWidget(self.song_info)
        
        action_buttons = QHBoxLayout()
        action_buttons.setSpacing(16)
        
        self.download_btn = ModernButton("⬇️ 开始下载")
        self.download_btn.setEnabled(False)
        self.download_btn.setMinimumWidth(160)
        self.download_btn.clicked.connect(self.download_song)
        action_buttons.addWidget(self.download_btn)
        
        self.open_folder_btn = GlowButton("📂 打开文件夹", color="#10B981")
        self.open_folder_btn.setMinimumWidth(140)
        self.open_folder_btn.clicked.connect(self.open_download_folder)
        action_buttons.addWidget(self.open_folder_btn)
        
        detail_layout.addLayout(action_buttons)
        
        progress_area = QVBoxLayout()
        progress_area.setSpacing(12)
        
        self.progress_bar = PulseProgressBar()
        self.progress_bar.setVisible(False)
        progress_area.addWidget(self.progress_bar)
        
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setFont(QFont("Microsoft YaHei UI", 12))
        self.status_label.setStyleSheet("""
            color: #6366F1;
            font-size: 13px;
            padding: 10px;
            font-weight: 600;
            background: rgba(99, 102, 241, 0.08);
            border-radius: 12px;
        """)
        progress_area.addWidget(self.status_label)
        
        detail_layout.addLayout(progress_area)
        detail_card.setLayout(detail_layout)
        results_area.addWidget(detail_card, 1)
        
        main_layout.addLayout(results_area, 1)
        
        footer = QLabel("💡 提示：双击搜索结果可直接下载 | 点击 ⚙️ 按钮可设置保存路径和音源")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setFont(QFont("Microsoft YaHei UI", 11))
        footer.setStyleSheet("""
            color: #94A3B8; 
            font-size: 12px; 
            padding: 14px 20px; 
            background-color: rgba(241, 245, 249, 0.8); 
            border-radius: 14px;
            border: 1px solid #E2E8F0;
        """)
        main_layout.addWidget(footer)
        
        self.setLayout(main_layout)
        
        self.results_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results_list.customContextMenuRequested.connect(self.show_context_menu)
    
    def setup_styles(self):
        self.setStyleSheet("""
            QWidget {
                font-family: "Microsoft YaHei UI", "Segoe UI", "微软雅黑", sans-serif;
                background: qlineargradient(135deg, #F8FAFC 0%, #E2E8F0 100%);
            }
            QScrollBar:vertical {
                border: none;
                background-color: rgba(241, 245, 249, 0.8);
                width: 10px;
                margin: 0px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: #CBD5E1;
                border-radius: 5px;
                min-height: 24px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #94A3B8;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
    
    def show_context_menu(self, pos):
        logger.info(f"显示上下文菜单，位置: {pos}")
        item = self.results_list.itemAt(pos)
        logger.info(f"itemAt 返回的 item，类型: {type(item)}, 值: {item}")
        if not item:
            logger.info("没有找到 item，不显示上下文菜单")
            return
        
        menu = QMenu()
        menu.setFont(QFont("Microsoft YaHei UI", 11))
        menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #F1F5F9;
                border-radius: 12px;
                padding: 8px 0;
            }
            QMenu::item {
                padding: 12px 20px;
                border-radius: 6px;
                margin: 2px 8px;
                color: #334155;
                font-weight: 500;
            }
            QMenu::item:selected {
                background-color: #6366F1;
                color: white;
            }
            QMenu::item:disabled {
                color: #94A3B8;
            }
        """)
        
        download_action = QAction("⬇️ 下载此歌曲", self)
        download_action.triggered.connect(lambda: self.download_song(item))
        menu.addAction(download_action)
        
        info_action = QAction("📝 查看详情", self)
        info_action.triggered.connect(lambda: self.show_song_info(item))
        menu.addAction(info_action)
        
        menu.exec_(self.results_list.mapToGlobal(pos))
    
    def show_song_info(self, item):
        logger.info(f"show_song_info 被调用，item 类型: {type(item)}, item 值: {item}")
        
        if not hasattr(item, 'data'):
            logger.error(f"show_song_info 接收到无效的 item 对象，类型: {type(item)}, 值: {item}")
            QMessageBox.warning(self, "错误", "无法获取歌曲详情：无效的项目对象")
            return
        
        try:
            index = item.data(Qt.ItemDataRole.UserRole)
            logger.info(f"从 item 获取索引: {index}")
            
            if index is None:
                logger.error("从 item 获取的索引为 None")
                QMessageBox.warning(self, "错误", "无法获取歌曲详情：索引为空")
                return
            
            if index < len(self.search_results):
                song = self.search_results[index]
                info = f"""<b>歌曲名称:</b> {song['title']}<br>
<b>艺术家:</b> {song['author']}<br>
<b>专辑:</b> {song['album']}<br>
<b>时长:</b> {song['duration']}"""
                QMessageBox.information(self, "歌曲详情", info)
                logger.info(f"显示歌曲详情: {song['title']} - {song['author']}")
            else:
                logger.error(f"索引超出范围: {index} >= {len(self.search_results)}")
                QMessageBox.warning(self, "错误", f"索引超出范围: {index}")
        except Exception as e:
            error_msg = f"显示歌曲详情失败: {str(e)}"
            logger.error(error_msg)
            logger.error(f"异常详情:\n{traceback.format_exc()}")
            QMessageBox.critical(self, "错误", f"显示歌曲详情失败: {str(e)}")
    
    def on_search_text_changed(self, text):
        if text:
            self.clear_btn.setVisible(True)
        else:
            self.clear_btn.setVisible(False)
    
    def clear_search(self):
        self.search_input.clear()
        self.results_list.clear()
        self.song_info.setText("选择一首歌曲查看详情")
        self.download_btn.setEnabled(False)
        self.status_label.setText("")
        self.search_results = []
        self.current_song = None
        self.search_input.setFocus()
    
    def open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.settings = load_settings()
            self.source_combo.clear()
            self.source_combo.addItems(get_source_names())
            self.source_combo.setCurrentText(self.settings["sources"]["active_source"])
            QMessageBox.information(self, "设置", "设置已保存！")
    
    def start_search(self):
        keyword = self.search_input.text().strip()
        if not keyword:
            QMessageBox.warning(self, "提示", "请输入歌曲名称")
            return
        
        self.results_list.clear()
        self.song_info.setText("🔍 正在搜索...")
        self.download_btn.setEnabled(False)
        self.status_label.setText("🔍 正在搜索...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        source = self.source_combo.currentText()
        max_results = self.settings["other"]["max_results"]
        
        self.search_thread = MusicSearchThread(keyword, source, max_results)
        self.search_thread.search_finished.connect(self.on_search_finished)
        self.search_thread.error_occurred.connect(self.on_search_error)
        self.search_thread.progress_updated.connect(self.progress_bar.setValue)
        self.search_thread.start()
    
    def on_search_finished(self, songs):
        self.progress_bar.setVisible(False)
        
        if not songs:
            self.song_info.setText("❌ 未找到相关歌曲")
            self.status_label.setText("❌ 未找到相关歌曲")
            return
        
        self.search_results = songs
        self.status_label.setText(f"✅ 找到 {len(songs)} 首歌曲")
        
        for i, song in enumerate(songs):
            duration = song.get("duration", "00:00")
            item_text = f"{i+1}. {song['title']} - {song['author']} ({duration})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, i)
            
            pic_url = song.get("pic", "")
            if pic_url:
                try:
                    cache_dir = self.settings["save_paths"]["cache"]
                    os.makedirs(cache_dir, exist_ok=True)
                    safe_name = re.sub(r'[\\/*?:"<>|]', "", song['title'])
                    image_path = os.path.join(cache_dir, f"{safe_name}.jpg")
                    
                    if not os.path.exists(image_path):
                        response = requests.get(pic_url, timeout=10)
                        if response.status_code == 200:
                            with open(image_path, 'wb') as f:
                                f.write(response.content)
                    
                    if os.path.exists(image_path):
                        pixmap = QPixmap(image_path)
                        if not pixmap.isNull():
                            pixmap = pixmap.scaled(50, 50, Qt.AspectRatioMode.KeepAspectRatio)
                            item.setIcon(QIcon(pixmap))
                except:
                    pass
            
            self.results_list.addItem(item)
    
    def on_search_error(self, error):
        self.progress_bar.setVisible(False)
        self.song_info.setText(f"❌ 搜索失败: {error}")
        self.status_label.setText("❌ 搜索失败")
        logger.error(f"搜索失败: {error}")
        QMessageBox.critical(self, "错误", f"搜索失败: {error}")
    
    def on_song_selected(self, item):
        logger.info(f"on_song_selected 被调用，item 类型: {type(item)}, item 值: {item}")
        
        if not hasattr(item, 'data'):
            logger.error(f"on_song_selected 接收到无效的 item 对象，类型: {type(item)}, 值: {item}")
            QMessageBox.warning(self, "错误", "无法选择歌曲：无效的项目对象")
            return
        
        try:
            index = item.data(Qt.ItemDataRole.UserRole)
            logger.info(f"从 item 获取索引: {index}")
            
            if index is None:
                logger.error("从 item 获取的索引为 None")
                QMessageBox.warning(self, "错误", "无法选择歌曲：索引为空")
                return
            
            if index < len(self.search_results):
                self.current_song = self.search_results[index]
                logger.info(f"设置当前歌曲: {self.current_song.get('title', '未知')}")
                
                info = f"""<b>歌曲名称:</b> {self.current_song['title']}<br>
<b>艺术家:</b> {self.current_song['author']}<br>
<b>专辑:</b> {self.current_song['album']}<br>
<b>时长:</b> {self.current_song['duration']}<br>
<b>状态:</b> <span style='color: #4A90D9;'>准备下载</span>"""
                
                self.song_info.setText(info)
                self.download_btn.setEnabled(True)
                self.status_label.setText("📀 可以下载了")
            else:
                logger.error(f"索引超出范围: {index} >= {len(self.search_results)}")
                QMessageBox.warning(self, "错误", f"索引超出范围: {index}")
        except Exception as e:
            error_msg = f"选择歌曲失败: {str(e)}"
            logger.error(error_msg)
            logger.error(f"异常详情:\n{traceback.format_exc()}")
            QMessageBox.critical(self, "错误", f"选择歌曲失败: {str(e)}")
    
    def download_song(self, item=None):
        logger.info(f"download_song 被调用，item 类型: {type(item)}, item 值: {item}")
        
        if item is None:
            item = self.results_list.currentItem()
            logger.info(f"从 results_list.currentItem() 获取 item，类型: {type(item)}")
        
        if item is None and self.current_song is None:
            logger.warning("没有可用的歌曲信息，用户未选择歌曲")
            QMessageBox.warning(self, "提示", "请先选择要下载的歌曲")
            return
        
        if item is not None:
            if hasattr(item, 'data'):
                try:
                    index = item.data(Qt.ItemDataRole.UserRole)
                    logger.info(f"从 item 获取索引: {index}")
                    if index is not None and index < len(self.search_results):
                        self.current_song = self.search_results[index]
                        logger.info(f"设置当前歌曲: {self.current_song.get('title', '未知')}")
                    else:
                        logger.warning(f"索引无效: {index}, 搜索结果数量: {len(self.search_results)}")
                except Exception as e:
                    error_msg = f"从 item 获取数据失败: {str(e)}"
                    logger.error(error_msg)
                    logger.error(f"异常详情:\n{traceback.format_exc()}")
            else:
                logger.warning(f"item 没有 data 方法，类型: {type(item)}, 值: {item}")
                logger.warning("跳过从 item 获取歌曲信息，使用当前歌曲")
        
        if not self.current_song or 'url' not in self.current_song:
            QMessageBox.warning(self, "提示", "没有可下载的歌曲")
            return
        
        default_name = f"{self.current_song['title']}.mp3"
        default_name = default_name.replace("/", "_").replace("\\", "_")
        
        download_dir = self.settings["save_paths"]["music"]
        os.makedirs(download_dir, exist_ok=True)
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "保存歌曲",
            os.path.join(download_dir, default_name),
            "MP3文件 (*.mp3)"
        )
        
        if not file_path:
            return
        
        self.download_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("⬇️ 正在下载...")
        
        self.download_thread = MusicDownloadThread(self.current_song['url'], file_path)
        self.download_thread.download_progress.connect(self.on_download_progress)
        self.download_thread.download_finished.connect(self.on_download_finished)
        self.download_thread.error_occurred.connect(self.on_download_error)
        self.download_thread.start()
    
    def on_download_progress(self, progress):
        self.progress_bar.setValue(progress)
        self.status_label.setText(f"⬇️ 下载中... {progress}%")
    
    def on_download_finished(self, file_path):
        self.progress_bar.setVisible(False)
        self.download_btn.setEnabled(True)
        self.status_label.setText("✅ 下载完成")
        
        info = self.song_info.text().replace("准备下载", f"✅ 已下载")
        self.song_info.setText(info)
        
        self.open_folder_btn.setEnabled(True)
        
        # 尝试同时下载歌词与封面，并将信息写入 Data/playlist.json
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(project_root, "Data")
            lrc_dir = os.path.join(data_dir, "Lyrics")
            pics_dir = os.path.join(data_dir, "Pics")
            os.makedirs(lrc_dir, exist_ok=True)
            os.makedirs(pics_dir, exist_ok=True)

            base_name = os.path.splitext(os.path.basename(file_path))[0]

            # 处理歌词（.lrc）
            lrc_path = ""
            lrc_source = self.current_song.get("lrc") if isinstance(self.current_song, dict) else None
            if lrc_source:
                try:
                    if isinstance(lrc_source, str) and lrc_source.strip().startswith("http"):
                        r = requests.get(lrc_source, timeout=10)
                        if r.ok and r.text:
                            lrc_path = os.path.join(lrc_dir, f"{base_name}.lrc")
                            with open(lrc_path, "w", encoding="utf-8") as f:
                                f.write(r.text)
                    else:
                        # 直接保存歌词文本
                        content = str(lrc_source)
                        if content.strip():
                            lrc_path = os.path.join(lrc_dir, f"{base_name}.lrc")
                            with open(lrc_path, "w", encoding="utf-8") as f:
                                f.write(content)
                except Exception:
                    logger.warning("保存歌词失败", exc_info=True)

            # 处理封面
            cover_path = ""
            pic_url = self.current_song.get("pic") if isinstance(self.current_song, dict) else None
            if pic_url and isinstance(pic_url, str) and pic_url.strip().startswith("http"):
                try:
                    r = requests.get(pic_url, timeout=10)
                    if r.ok and r.content:
                        # 尝试从URL或响应头推断扩展名
                        ext = None
                        if ".jpg" in pic_url.lower() or ".jpeg" in pic_url.lower():
                            ext = ".jpg"
                        elif ".png" in pic_url.lower():
                            ext = ".png"
                        else:
                            ctype = r.headers.get("content-type", "")
                            if "jpeg" in ctype:
                                ext = ".jpg"
                            elif "png" in ctype:
                                ext = ".png"
                        if not ext:
                            ext = ".jpg"
                        cover_path = os.path.join(pics_dir, f"{base_name}{ext}")
                        with open(cover_path, "wb") as f:
                            f.write(r.content)
                except Exception:
                    logger.warning("下载封面失败", exc_info=True)

            # 更新 Data/playlist.json
            try:
                playlist_file = os.path.join(data_dir, "playlist.json")
                playlist = []
                if os.path.exists(playlist_file):
                    try:
                        with open(playlist_file, "r", encoding="utf-8") as pf:
                            loaded = json.load(pf)
                            if isinstance(loaded, list):
                                playlist = loaded
                            elif isinstance(loaded, dict) and "playlist" in loaded and isinstance(loaded["playlist"], list):
                                playlist = loaded["playlist"]
                    except Exception:
                        logger.warning("读取 playlist.json 失败，正在重建列表", exc_info=True)

                # 构建条目并避免重复（按文件路径）
                rel_file = os.path.relpath(file_path, project_root)
                rel_lrc = os.path.relpath(lrc_path, project_root) if lrc_path else ""
                rel_cover = os.path.relpath(cover_path, project_root) if cover_path else ""

                entry = {
                    "title": self.current_song.get("title", "") if isinstance(self.current_song, dict) else "",
                    "artist": self.current_song.get("author", "") if isinstance(self.current_song, dict) else "",
                    "file": rel_file.replace('\\', '/'),
                    "lrc": rel_lrc.replace('\\', '/') if rel_lrc else "",
                    "cover": rel_cover.replace('\\', '/') if rel_cover else ""
                }

                # 检查重复
                exists = False
                for it in playlist:
                    if isinstance(it, dict) and it.get("file") == entry["file"]:
                        exists = True
                        break

                if not exists:
                    playlist.append(entry)
                    # 如果原来是 dict 包含 playlist 键，则写回相同结构，否则写入为列表
                    if os.path.exists(playlist_file):
                        try:
                            with open(playlist_file, "r", encoding="utf-8") as pf:
                                loaded = json.load(pf)
                                if isinstance(loaded, dict) and "playlist" in loaded:
                                    loaded["playlist"] = playlist
                                    with open(playlist_file, "w", encoding="utf-8") as pfw:
                                        json.dump(loaded, pfw, ensure_ascii=False, indent=2)
                                else:
                                    with open(playlist_file, "w", encoding="utf-8") as pfw:
                                        json.dump(playlist, pfw, ensure_ascii=False, indent=2)
                        except Exception:
                            with open(playlist_file, "w", encoding="utf-8") as pfw:
                                json.dump(playlist, pfw, ensure_ascii=False, indent=2)
                    else:
                        with open(playlist_file, "w", encoding="utf-8") as pfw:
                            json.dump(playlist, pfw, ensure_ascii=False, indent=2)
            except Exception:
                logger.warning("更新 playlist.json 失败", exc_info=True)

        except Exception:
            logger.warning("下载后处理（歌词/封面/playlist）失败", exc_info=True)

        QMessageBox.information(self, "下载完成", f"歌曲已保存到:\n{file_path}")
    
    def on_download_error(self, error):
        self.progress_bar.setVisible(False)
        self.download_btn.setEnabled(True)
        self.status_label.setText("❌ 下载失败")
        logger.error(f"下载失败: {error}")
        QMessageBox.critical(self, "错误", f"下载失败: {error}")
    
    def open_download_folder(self):
        download_dir = self.settings["save_paths"]["music"]
        if not os.path.exists(download_dir):
            os.makedirs(download_dir, exist_ok=True)
        
        import subprocess
        subprocess.run(f'explorer "{download_dir}"')
    
    def closeEvent(self, event):
        if self.search_thread and self.search_thread.isRunning():
            self.search_thread.terminate()
            self.search_thread.wait()
        
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.terminate()
            self.download_thread.wait()
        
        event.accept()
