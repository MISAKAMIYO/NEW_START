"""
歌词搜索对话框
提供三种获取歌词的方式：
1. 网络搜索 - 从网络搜索并下载LRC歌词
2. AI生成 - 使用AI生成歌词
3. 文本转LRC - 将手动输入的文本转换为LRC格式
"""

import os
import re
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QLineEdit, QPushButton, QTextEdit,
    QMessageBox, QGroupBox, QSpinBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from .lyrics_search import LyricsSearcher, AILyricsGenerator, TextToLRCConverter


class LyricsSearchDialog(QDialog):
    """歌词搜索对话框"""
    
    lyrics_ready = pyqtSignal(str)
    
    def __init__(self, song_title: str = "", artist: str = "", config_manager=None, parent=None):
        super().__init__(parent)
        self.song_title = song_title
        self.artist = artist
        self.config_manager = config_manager
        self.current_lrc = ""
        self.searcher = None
        self.ai_generator = None
        
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("歌词搜索")
        self.setMinimumSize(600, 500)
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        info_label = QLabel(f"当前歌曲: {self.artist} - {self.song_title}")
        info_label.setStyleSheet("font-weight: bold; padding: 5px;")
        layout.addWidget(info_label)
        
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self.create_network_tab(), "网络搜索")
        self.tab_widget.addTab(self.create_ai_tab(), "AI生成")
        self.tab_widget.addTab(self.create_text_tab(), "文本转LRC")
        
        layout.addWidget(self.tab_widget)
        
        result_group = QGroupBox("歌词预览")
        result_layout = QVBoxLayout()
        
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setPlaceholderText("获取的歌词将在此显示...")
        result_layout.addWidget(self.result_text)
        
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)
        
        button_layout = QHBoxLayout()
        
        self.apply_btn = QPushButton("应用歌词")
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self.apply_lyrics)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def create_network_tab(self) -> QWidget:
        """创建网络搜索标签页"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        info = QLabel("从网络搜索歌词")
        info.setStyleSheet("font-weight: bold;")
        layout.addWidget(info)
        
        search_layout = QHBoxLayout()
        
        self.network_title_input = QLineEdit()
        self.network_title_input.setPlaceholderText("歌曲名称")
        self.network_title_input.setText(self.song_title)
        
        self.network_artist_input = QLineEdit()
        self.network_artist_input.setPlaceholderText("艺术家")
        self.network_artist_input.setText(self.artist)
        
        self.network_search_btn = QPushButton("搜索")
        self.network_search_btn.clicked.connect(self.search_online)
        
        search_layout.addWidget(QLabel("歌曲:"))
        search_layout.addWidget(self.network_title_input)
        search_layout.addWidget(QLabel("艺术家:"))
        search_layout.addWidget(self.network_artist_input)
        search_layout.addWidget(self.network_search_btn)
        
        layout.addLayout(search_layout)
        
        self.network_progress = QLabel("")
        layout.addWidget(self.network_progress)
        
        layout.addStretch()
        
        widget.setLayout(layout)
        return widget
        
    def create_ai_tab(self) -> QWidget:
        """创建AI生成标签页"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        info = QLabel("使用AI生成歌词（需要配置AI API）")
        info.setStyleSheet("font-weight: bold;")
        layout.addWidget(info)
        
        desc = QLabel("AI将根据歌曲信息生成歌词。如果原歌曲有歌词，AI会尝试创作相似风格的歌词；如果无法获取原歌词，AI会创作原创歌词。")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: gray;")
        layout.addWidget(desc)
        
        layout.addStretch()
        
        self.ai_generate_btn = QPushButton("开始生成")
        self.ai_generate_btn.clicked.connect(self.generate_with_ai)
        layout.addWidget(self.ai_generate_btn)
        
        self.ai_progress = QLabel("")
        layout.addWidget(self.ai_progress)
        
        widget.setLayout(layout)
        return widget
        
    def create_text_tab(self) -> QWidget:
        """创建文本转LRC标签页"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        info = QLabel("将纯文本歌词转换为LRC格式")
        info.setStyleSheet("font-weight: bold;")
        layout.addWidget(info)
        
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("每行时长:"))
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(2, 30)
        self.duration_spin.setValue(5)
        self.duration_spin.setSuffix(" 秒")
        duration_layout.addWidget(self.duration_spin)
        duration_layout.addStretch()
        layout.addLayout(duration_layout)
        
        self.raw_text_input = QTextEdit()
        self.raw_text_input.setPlaceholderText("在此输入歌词文本，每行一句...")
        self.raw_text_input.setMinimumHeight(150)
        layout.addWidget(self.raw_text_input)
        
        self.text_convert_btn = QPushButton("转换为LRC")
        self.text_convert_btn.clicked.connect(self.convert_text_to_lrc)
        layout.addWidget(self.text_convert_btn)
        
        widget.setLayout(layout)
        return widget
        
    def search_online(self):
        """从网络搜索歌词"""
        title = self.network_title_input.text().strip()
        artist = self.network_artist_input.text().strip()
        
        if not title:
            QMessageBox.warning(self, "提示", "请输入歌曲名称")
            return
            
        self.network_search_btn.setEnabled(False)
        self.network_progress.setText("正在搜索...")
        
        self.searcher = LyricsSearcher(title, artist)
        self.searcher.progress.connect(self.on_search_progress)
        self.searcher.lyrics_found.connect(self.on_lyrics_found)
        self.searcher.error_occurred.connect(self.on_search_error)
        self.searcher.finished.connect(self.on_search_finished)
        self.searcher.start()
        
    def on_search_progress(self, msg: str):
        """搜索进度更新"""
        self.network_progress.setText(msg)
        
    def on_lyrics_found(self, lyrics: str):
        """找到歌词"""
        self.current_lrc = lyrics
        self.result_text.setPlainText(lyrics)
        self.apply_btn.setEnabled(True)
        self.network_progress.setText("搜索成功！")
        
    def on_search_error(self, msg: str):
        """搜索错误"""
        self.network_progress.setText(msg)
        QMessageBox.warning(self, "搜索失败", msg)
        
    def on_search_finished(self):
        """搜索完成"""
        self.network_search_btn.setEnabled(True)
        
    def generate_with_ai(self):
        """使用AI生成歌词"""
        if not self.config_manager:
            QMessageBox.warning(self, "提示", "配置管理器未初始化")
            return
            
        self.ai_generate_btn.setEnabled(False)
        self.ai_progress.setText("正在调用AI...")
        
        self.ai_generator = AILyricsGenerator(
            self.song_title, 
            self.artist, 
            self.config_manager
        )
        self.ai_generator.progress.connect(self.on_ai_progress)
        self.ai_generator.lyrics_generated.connect(self.on_ai_generated)
        self.ai_generator.error_occurred.connect(self.on_ai_error)
        self.ai_generator.finished.connect(self.on_ai_finished)
        self.ai_generator.start()
        
    def on_ai_progress(self, msg: str):
        """AI生成进度"""
        self.ai_progress.setText(msg)
        
    def on_ai_generated(self, lyrics: str):
        """AI生成完成"""
        self.current_lrc = lyrics
        self.result_text.setPlainText(lyrics)
        self.apply_btn.setEnabled(True)
        self.ai_progress.setText("生成成功！")
        
    def on_ai_error(self, msg: str):
        """AI生成错误"""
        self.ai_progress.setText(msg)
        QMessageBox.warning(self, "AI生成失败", msg)
        
    def on_ai_finished(self):
        """AI生成完成"""
        self.ai_generate_btn.setEnabled(True)
        
    def convert_text_to_lrc(self):
        """将文本转换为LRC"""
        raw_text = self.raw_text_input.toPlainText().strip()
        
        if not raw_text:
            QMessageBox.warning(self, "提示", "请输入歌词文本")
            return
            
        duration = self.duration_spin.value()
        
        lrc = TextToLRCConverter.convert(raw_text, duration)
        
        lrc_with_header = f"[ti:{self.song_title or 'Unknown'}]\n"
        lrc_with_header += f"[ar:{self.artist or 'Unknown'}]\n"
        lrc_with_header += lrc
        
        self.current_lrc = lrc_with_header
        self.result_text.setPlainText(lrc_with_header)
        self.apply_btn.setEnabled(True)
        
    def apply_lyrics(self):
        """应用歌词"""
        if self.current_lrc:
            self.lyrics_ready.emit(self.current_lrc)
            self.accept()
            
    def get_lrc_content(self) -> str:
        """获取LRC内容"""
        return self.current_lrc
