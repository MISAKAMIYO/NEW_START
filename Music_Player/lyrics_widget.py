"""
Lyrics Widget - 滚动歌词组件
支持类似市面音乐软件的滚动歌词效果
"""

import os
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QScrollArea
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt5.QtGui import QFont, QColor, QPainter, QPainterPath, QLinearGradient, QPalette, QCursor


class LyricsLineWidget(QWidget):
    """单行歌词组件"""

    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.text = text
        self.setFixedHeight(50)
        self._is_active = False
        self._opacity = 0.5

    def setText(self, text):
        self.text = text
        self.update()

    def getText(self):
        return self.text

    def setActive(self, active):
        self._is_active = active
        self.update()

    def setOpacity(self, opacity):
        self._opacity = opacity
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if self._is_active:
            font = QFont("Microsoft YaHei UI", 18, QFont.Bold)
            color = QColor(255, 255, 255)
        else:
            font = QFont("Microsoft YaHei UI", 14)
            color = QColor(200, 200, 200)

        color.setAlpha(int(255 * self._opacity))
        painter.setFont(font)
        painter.setPen(color)

        # 绘制文字
        painter.drawText(self.rect(), Qt.AlignCenter, self.text)


class LyricsWidget(QWidget):
    """滚动歌词组件"""

    current_lyric_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.lyrics_data = []  # [(时间戳, 歌词文本), ...]
        self.current_index = -1
        self.animation = None

        self._setup_ui()
        self._setup_animation()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(0)

        # 滚动区域
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollArea QScrollBar:vertical {
                width: 6px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 3px;
            }
            QScrollArea QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.3);
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollArea QScrollBar::add-line:vertical, QScrollArea QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        # 歌词容器
        self.lyrics_container = QWidget()
        self.lyrics_layout = QVBoxLayout(self.lyrics_container)
        self.lyrics_layout.setContentsMargins(0, 0, 0, 0)
        self.lyrics_layout.setSpacing(0)
        self.lyrics_layout.addStretch()

        self.scroll_area.setWidget(self.lyrics_container)
        layout.addWidget(self.scroll_area)

        # 占位标签（无歌词时显示）
        self.placeholder = QLabel("暂无歌词")
        self.placeholder.setAlignment(Qt.AlignCenter)
        self.placeholder.setStyleSheet("""
            QLabel {
                color: rgba(255, 255, 255, 0.3);
                font-size: 16px;
            }
        """)
        self.placeholder.setParent(self)
        self.placeholder.setGeometry(self.rect())
        self.placeholder.show()

    def _setup_animation(self):
        self.animation = QPropertyAnimation(self.scroll_area.verticalScrollBar(), b"value")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.placeholder.setGeometry(self.rect())

    def clear_lyrics(self):
        """清空歌词"""
        self.lyrics_data = []
        self.current_index = -1

        # 清除所有歌词行
        while self.lyrics_layout.count() > 1:
            item = self.lyrics_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            self.lyrics_layout.removeItem(item)

        self.placeholder.show()
        self.update()

    def set_lyrics(self, lyrics_data):
        """
        设置歌词数据
        lyrics_data: [(start_time, end_time, text), ...]
        """
        self.lyrics_data = sorted(lyrics_data, key=lambda x: x[0])
        self.current_index = -1

        # 清除旧的歌词行
        while self.lyrics_layout.count() > 1:
            item = self.lyrics_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            self.lyrics_layout.removeItem(item)

        # 创建新的歌词行
        for start, end, text in self.lyrics_data:
            if text.strip():
                line = LyricsLineWidget(text)
                line.setCursor(QCursor(Qt.PointingHandCursor))
                line.setOpacity(0.4)
                self.lyrics_layout.insertWidget(self.lyrics_layout.count() - 1, line)

        # 更新占位符状态
        if self.lyrics_data:
            self.placeholder.hide()
        else:
            self.placeholder.show()

        self.update()

    def update_position(self, position_ms):
        """
        更新歌词位置
        position_ms: 当前播放位置（毫秒）
        """
        if not self.lyrics_data:
            return

        position_sec = position_ms / 1000.0

        # 找到当前应该高亮的歌词行
        new_index = -1
        for i, (start, end, text) in enumerate(self.lyrics_data):
            if start <= position_sec < end:
                new_index = i
                break

        # 如果没有找到，检查是否在最后一行之后
        if new_index == -1 and self.lyrics_data:
            if position_sec >= self.lyrics_data[-1][0]:
                new_index = len(self.lyrics_data) - 1

        # 如果索引发生变化，更新显示
        if new_index != self.current_index:
            old_index = self.current_index
            self.current_index = new_index

            if new_index >= 0:
                self._update_display(new_index)

                # 滚动到当前行
                self._scroll_to_line(new_index)

                # 发送当前歌词信号
                current_text = self.lyrics_data[new_index][2] if new_index < len(self.lyrics_data) else ""
                self.current_lyric_changed.emit(current_text)

    def _update_display(self, active_index):
        """更新所有歌词行的显示状态"""
        lines = []
        for i in range(self.lyrics_layout.count() - 1):
            item = self.lyrics_layout.itemAt(i)
            if item.widget():
                lines.append(item.widget())

        for i, line in enumerate(lines):
            if i == active_index:
                line.setActive(True)
                line.setOpacity(1.0)
            elif i < active_index:
                line.setActive(False)
                line.setOpacity(0.4)
            else:
                line.setActive(False)
                line.setOpacity(0.7)

    def _scroll_to_line(self, index):
        """滚动到指定行"""
        if index < 0:
            return

        lines = []
        for i in range(self.lyrics_layout.count() - 1):
            item = self.lyrics_layout.itemAt(i)
            if item.widget():
                lines.append(item.widget())

        if index < len(lines):
            target_line = lines[index]

            # 计算滚动位置
            scroll_bar = self.scroll_area.verticalScrollBar()
            line_pos = target_line.y()
            container_height = self.lyrics_container.height()
            viewport_height = self.scroll_area.viewport().height()

            # 将当前行滚动到视口中间偏上的位置
            target_value = line_pos - viewport_height // 3
            target_value = max(0, min(target_value, scroll_bar.maximum()))

            # 使用动画滚动
            self.animation.stop()
            self.animation.setStartValue(scroll_bar.value())
            self.animation.setEndValue(target_value)
            self.animation.start()

    def get_current_lyric(self):
        """获取当前歌词"""
        if 0 <= self.current_index < len(self.lyrics_data):
            return self.lyrics_data[self.current_index][2]
        return ""

    def has_lyrics(self):
        """是否有歌词"""
        return len(self.lyrics_data) > 0
