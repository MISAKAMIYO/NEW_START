"""
External Lyrics Window
"""

from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QWidget, QLabel
from PyQt5.QtCore import Qt

class ExternalLyricsWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowOpacity(0.9)
        self.setWindowTitle("歌词 - RAILGUN")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(600, 200)
        
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 当前行标签
        self.current_line_label = QLabel("")
        self.current_line_label.setAlignment(Qt.AlignCenter)
        self.current_line_label.setStyleSheet("font-size: 36px; font-weight: bold; color: white;")
        
        # 下一行标签
        self.next_line_label = QLabel("")
        self.next_line_label.setAlignment(Qt.AlignCenter)
        self.next_line_label.setStyleSheet("font-size: 24px; color: #AAAAAA;")
        
        layout.addWidget(self.current_line_label)
        layout.addWidget(self.next_line_label)
        
        # 初始位置
        from PyQt5.QtWidgets import QApplication
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        self.setGeometry(
            (screen_geometry.width() - 600) // 2,
            screen_geometry.height() - 250,
            600,
            200
        )

    def update_lyrics(self, current_text="", next_text=""):
        self.current_line_label.setText(current_text)
        self.next_line_label.setText(next_text)