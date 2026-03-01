"""
External Lyrics Window - 外置歌词窗口
独立的歌词显示窗口，支持自定义样式和位置
"""

import os
import re
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, QApplication,
    QMenu, QInputDialog, QMessageBox, QFontDialog, QColorDialog
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPoint, QRect, QByteArray
from PyQt5.QtGui import QFont, QColor, QPalette, QMouseEvent, QFontDatabase

# 导入配置管理器
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from settings_manager import ConfigManager


class ExternalLyricsWindow(QMainWindow):
    """外置歌词窗口"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowOpacity(0.9)
        self.setWindowTitle("外置歌词 - Railgun Player")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(1000, 200)
        
        # 配置管理器
        self.config_manager = ConfigManager()
        
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 歌词标签 - 使用双行显示
        self.lyrics_layout = QVBoxLayout()
        self.lyrics_layout.setSpacing(15)
        self.lyrics_layout.setContentsMargins(30, 30, 30, 30)

        # 当前行标签
        self.current_line_label = QLabel("")
        self.current_line_label.setAlignment(Qt.AlignCenter)
        self.current_line_label.setStyleSheet("font-size: 48px; font-weight: bold; color: white;")
        self.current_line_label.setWordWrap(True)
        
        # 下一行标签
        self.next_line_label = QLabel("")
        self.next_line_label.setAlignment(Qt.AlignCenter)
        self.next_line_label.setStyleSheet("font-size: 36px; color: #AAAAAA;")
        self.next_line_label.setWordWrap(True)
        
        # 添加标签到布局
        self.lyrics_layout.addWidget(self.current_line_label)
        self.lyrics_layout.addWidget(self.next_line_label)
        layout.addLayout(self.lyrics_layout)
        

        
        # 右键菜单
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        # 歌词数据
        self.lyrics_data = []  # [(开始时间, 结束时间, 歌词文本), ...]
        self.current_line_index = -1
        
        # 添加默认样式属性
        self.normal_color = QColor("#FFFFFF")
        self.highlight_color = QColor("#FF5722")
        self.next_line_color = QColor("#AAAAAA")
        self.font = QFont("Microsoft YaHei", 36)
        
        # 应用保存的样式设置
        self.apply_style_settings()
        
        # 如果窗口没有有效位置，重置到默认位置
        if self.x() == 0 and self.y() == 0:
            self.reset_position()

        # 添加锁定状态属性
        self.locked = False
        
        # 鼠标拖动相关
        self.dragging = False
        self.drag_position = QPoint()
        
    def reset_position(self):
        """重置歌词窗口位置到屏幕底部中央"""
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        self.setGeometry(
            (screen_geometry.width() - 1000) // 2,
            screen_geometry.height() - 250,
            1000,
            200
        )
        self.save_settings()
        
    def mousePressEvent(self, event: QMouseEvent):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton and not self.locked:
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
            
    def mouseMoveEvent(self, event: QMouseEvent):
        """鼠标移动事件"""
        if self.dragging and not self.locked:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
            
    def mouseReleaseEvent(self, event: QMouseEvent):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton and self.dragging:
            self.dragging = False
            self.save_settings()
            event.accept()
            
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """鼠标双击事件 - 切换锁定状态"""
        if event.button() == Qt.LeftButton:
            self.toggle_lock()
            
    def show_context_menu(self, pos):
        """显示右键菜单"""
        menu = QMenu(self)
        
        # 字体设置
        font_action = menu.addAction("设置字体")
        font_action.triggered.connect(self.set_font_dialog)
        
        # 颜色设置
        color_action = menu.addAction("设置颜色")
        color_action.triggered.connect(self.set_color_dialog)
        
        # 透明度设置
        opacity_action = menu.addAction("设置透明度")
        opacity_action.triggered.connect(self.set_opacity_dialog)
        
        menu.addSeparator()
        
        # 锁定/解锁
        lock_text = "解锁" if self.locked else "锁定"
        lock_action = menu.addAction(lock_text)
        lock_action.triggered.connect(self.toggle_lock)
        
        # 重置位置
        reset_action = menu.addAction("重置位置")
        reset_action.triggered.connect(self.reset_position)
        
        menu.addSeparator()
        
        # 关闭
        close_action = menu.addAction("关闭")
        close_action.triggered.connect(self.hide)
        
        menu.exec_(self.mapToGlobal(pos))
        
    def set_font_dialog(self):
        """设置字体对话框"""
        font, ok = QFontDialog.getFont(self.font, self, "选择字体")
        if ok:
            self.font = font
            self.apply_font()
            self.save_settings()
            
    def set_color_dialog(self):
        """设置颜色对话框"""
        color = QColorDialog.getColor(self.normal_color, self, "选择歌词颜色")
        if color.isValid():
            self.normal_color = color
            self.apply_colors()
            self.save_settings()
            
    def set_opacity_dialog(self):
        """设置透明度对话框"""
        current_opacity = int(self.windowOpacity() * 100)
        opacity, ok = QInputDialog.getInt(
            self, "设置透明度", "透明度 (0-100):", 
            current_opacity, 0, 100
        )
        if ok:
            self.setWindowOpacity(opacity / 100.0)
            self.save_settings()
            
    def toggle_lock(self):
        """切换窗口锁定状态"""
        self.locked = not self.locked
        self.save_settings()
        
    def apply_font(self):
        """应用字体设置"""
        self.current_line_label.setFont(self.font)
        # 调整下一行字体大小
        smaller_font = QFont(self.font)
        smaller_font.setPointSize(int(self.font.pointSize() * 0.8))
        self.next_line_label.setFont(smaller_font)
        
    def apply_colors(self):
        """应用颜色设置"""
        style_sheet = f"color: {self.normal_color.name()};"
        self.current_line_label.setStyleSheet(
            f"font-size: 48px; font-weight: bold; {style_sheet}"
        )
        
        # 下一行使用较浅的颜色
        next_line_color = QColor(self.normal_color)
        next_line_color.setAlpha(180)
        self.next_line_label.setStyleSheet(
            f"font-size: 36px; color: {next_line_color.name()};"
        )
        
    def apply_style_settings(self):
        """应用保存的样式设置"""
        # 从配置加载设置
        settings = self.config_manager.get_all_config()
        lyrics_settings = settings.get("external_lyrics", {})
        
        # 加载字体信息
        font_str = lyrics_settings.get("font", "")
        if font_str:
            self.font = QFont()
            self.font.fromString(font_str)
        else:
            self.font = QFont("Microsoft YaHei", 36)
        self.apply_font()
        
        # 加载颜色信息
        color_str = lyrics_settings.get("color", "#FFFFFF")
        self.normal_color = QColor(color_str)
        self.apply_colors()
        
        # 加载透明度
        opacity = lyrics_settings.get("opacity", 90)
        self.setWindowOpacity(opacity / 100.0)
        
        # 加载锁定状态
        self.locked = lyrics_settings.get("locked", False)
        
        # 加载几何信息
        geometry_hex = lyrics_settings.get("geometry", "")
        if geometry_hex:
            try:
                self.restoreGeometry(QByteArray.fromHex(geometry_hex.encode()))
            except:
                self.reset_position()
                
        # 加载显示状态
        show_lyrics = lyrics_settings.get("show_lyrics", False)
        if show_lyrics:
            self.show()
        else:
            self.hide()
            
    def save_settings(self):
        """保存歌词窗口设置"""
        settings = self.config_manager.get_all_config()
        lyrics_settings = settings.get("external_lyrics", {})
        
        # 保存几何信息
        from PyQt5.QtCore import QByteArray
        lyrics_settings["geometry"] = self.saveGeometry().toHex().data().decode()
        
        # 保存字体信息
        lyrics_settings["font"] = self.current_line_label.font().toString()
        
        # 保存颜色信息
        lyrics_settings["color"] = self.normal_color.name()
        
        # 保存透明度
        lyrics_settings["opacity"] = int(self.windowOpacity() * 100)
        
        # 保存锁定状态
        lyrics_settings["locked"] = self.locked
        
        # 保存显示状态
        lyrics_settings["show_lyrics"] = self.isVisible()
        
        settings["external_lyrics"] = lyrics_settings
        self.config_manager.update_config(settings)
        
    def update_lyrics(self, current_text="", next_text=""):
        """更新歌词显示
        
        Args:
            current_text: 当前行歌词文本
            next_text: 下一行歌词文本
        """
        try:
            # 支持传入 None 的情况
            current = current_text or ""
            nxt = next_text or ""
            
            # 设置文本
            self.current_line_label.setText(current)
            self.next_line_label.setText(nxt)
            
            # 强制刷新
            self.current_line_label.repaint()
            self.next_line_label.repaint()
        except Exception as e:
            print(f"ExternalLyricsWindow.update_lyrics error: {e}")
            
    def clear_lyrics(self):
        """清空歌词显示"""
        self.current_line_label.setText("")
        self.next_line_label.setText("")
        self.lyrics_data = []
        self.current_line_index = -1
        
    def load_lyrics_data(self, lyrics_data):
        """加载歌词数据
        
        Args:
            lyrics_data: 歌词数据列表，格式为 [(开始时间(ms), 结束时间(ms), 歌词文本), ...]
        """
        self.lyrics_data = lyrics_data
        self.current_line_index = -1
        
    def update_position(self, position_ms):
        """根据播放位置更新当前显示的歌词行
        
        Args:
            position_ms: 当前播放位置（毫秒）
        """
        if not self.lyrics_data:
            return
            
        # 查找当前时间对应的歌词行
        new_index = -1
        for i, (start_time, end_time, text) in enumerate(self.lyrics_data):
            if start_time <= position_ms <= end_time:
                new_index = i
                break
                
        # 如果找到新行，更新显示
        if new_index != -1 and new_index != self.current_line_index:
            self.current_line_index = new_index
            current_text = self.lyrics_data[new_index][2]
            
            # 获取下一行文本
            next_text = ""
            if new_index + 1 < len(self.lyrics_data):
                next_text = self.lyrics_data[new_index + 1][2]
                
            self.update_lyrics(current_text, next_text)
            
    def showEvent(self, event):
        """窗口显示事件 - 保存显示状态"""
        super().showEvent(event)
        self.save_settings()
        
    def hideEvent(self, event):
        """窗口隐藏事件 - 保存显示状态"""
        super().hideEvent(event)
        self.save_settings()
        
    def closeEvent(self, event):
        """窗口关闭事件 - 保存设置并隐藏而非关闭"""
        event.ignore()
        self.hide()
        self.save_settings()