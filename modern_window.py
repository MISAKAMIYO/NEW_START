from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QSpacerItem, QSizePolicy)
from PyQt5.QtCore import Qt, QPoint, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QIcon


MODERN_BLACK_TITLE_BAR = """
    QWidget#TitleBar {
        background-color: #1a1a1a;
        border-top-left-radius: 16px;
        border-top-right-radius: 16px;
    }
    
    QLabel#TitleLabel {
        color: #ffffff;
        font-family: 'Segoe UI', 'Microsoft YaHei UI', sans-serif;
        font-size: 14px;
        font-weight: bold;
    }
    
    QPushButton#TitleBtn {
        background-color: transparent;
        border: none;
        color: #888888;
        font-size: 16px;
        min-width: 36px;
        max-width: 36px;
        min-height: 36px;
        max-height: 36px;
        border-radius: 6px;
    }
    
    QPushButton#TitleBtn:hover {
        background-color: rgba(255, 255, 255, 0.1);
        color: #ffffff;
    }
    
    QPushButton#CloseBtn {
        background-color: transparent;
        border: none;
        color: #888888;
        font-size: 18px;
        min-width: 36px;
        max-width: 36px;
        min-height: 36px;
        max-height: 36px;
        border-radius: 6px;
    }
    
    QPushButton#CloseBtn:hover {
        background-color: #e81123;
        color: #ffffff;
    }
    
    QWidget#ContentWidget {
        background-color: #0D0D0D;
        border-bottom-left-radius: 16px;
        border-bottom-right-radius: 16px;
    }
"""


class ModernWindow(QWidget):
    window_closed = pyqtSignal()
    
    def __init__(self, parent=None, title="", icon=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        if icon:
            self.setWindowIcon(QIcon(icon))
        
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowFlags(Qt.FramelessWindowHint)
        
        self._drag_position = None
        
        self._setup_ui(title)
        self._setup_connections()
    
    def _setup_ui(self, title):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.title_bar = QWidget()
        self.title_bar.setObjectName("TitleBar")
        self.title_bar.setFixedHeight(48)
        
        title_bar_layout = QHBoxLayout()
        title_bar_layout.setContentsMargins(16, 0, 8, 0)
        title_bar_layout.setSpacing(8)
        
        self.title_label = QLabel(title)
        self.title_label.setObjectName("TitleLabel")
        self.title_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        title_bar_layout.addWidget(self.title_label)
        
        self.min_btn = QPushButton("─")
        self.min_btn.setObjectName("TitleBtn")
        self.min_btn.setToolTip("最小化")
        title_bar_layout.addWidget(self.min_btn)
        
        self.max_btn = QPushButton("□")
        self.max_btn.setObjectName("TitleBtn")
        self.max_btn.setToolTip("最大化")
        title_bar_layout.addWidget(self.max_btn)
        
        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("CloseBtn")
        self.close_btn.setToolTip("关闭")
        title_bar_layout.addWidget(self.close_btn)
        
        self.title_bar.setLayout(title_bar_layout)
        
        self.content_widget = QWidget()
        self.content_widget.setObjectName("ContentWidget")
        self.content_widget.setStyleSheet(MODERN_BLACK_TITLE_BAR)
        
        self._setup_content()
        
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self.content_widget)
        
        main_layout.addWidget(self.title_bar)
        main_layout.addLayout(content_layout)
        
        self.setLayout(main_layout)
    
    def _setup_content(self):
        pass
    
    def _setup_connections(self):
        self.min_btn.clicked.connect(self.showMinimized)
        self.max_btn.clicked.connect(self._toggle_maximize)
        self.close_btn.clicked.connect(self.close)
    
    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
            self.max_btn.setText("□")
        else:
            self.showMaximized()
            self.max_btn.setText("▣")
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_position:
            self.move(event.globalPos() - self._drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        self._drag_position = None
    
    def closeEvent(self, event):
        self.window_closed.emit()
        super().closeEvent(event)
    
    def setStyleSheet(self, sheet):
        combined = sheet + "\n" + MODERN_BLACK_TITLE_BAR
        super().setStyleSheet(combined)
