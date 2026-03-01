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
            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6366F1, stop:0.5 #8B5CF6, stop:1 #7C3AED);
                color: white;
                border: none;
                border-radius: 14px;
                padding: 12px 24px;
                font-weight: 600;
                font-size: 14px;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4F46E5, stop:0.5 #7C3AED, stop:1 #6D28D9);
            }
            QPushButton:pressed {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4338CA, stop:0.5 #5B21B6, stop:1 #4C1D95);
            }
            QPushButton:disabled {
                background-color: #CBD5E1;
                color: #94A3B8;
            }
        """)


class GlowButton(QPushButton):
    def __init__(self, text, parent=None, color="#6366F1"):
        super().__init__(text, parent)
        self.setMinimumHeight(44)
        self.setFont(QFont("Microsoft YaHei UI", 11, QFont.Medium))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 12px;
                padding: 10px 20px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {color};
                filter: brightness(1.1);
            }}
        """)


class ModernCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.95);
                border-radius: 20px;
                border: 1px solid rgba(226, 232, 240, 0.8);
            }
        """)


class ModernLineEdit(QLineEdit):
    def __init__(self, placeholder="", parent=None):
        super().__init__(placeholder, parent)
        self.setFont(QFont("Microsoft YaHei UI", 13))
        self.setStyleSheet("""
            QLineEdit {
                background-color: rgba(248, 250, 252, 0.9);
                border: 2px solid #E2E8F0;
                border-radius: 14px;
                padding: 14px 18px;
                font-size: 14px;
                color: #1E293B;
                selection-background-color: #6366F1;
                selection-color: white;
            }
            QLineEdit:focus {
                border-color: #6366F1;
                background-color: #FFFFFF;
            }
            QLineEdit:hover {
                border-color: #CBD5E1;
                background-color: #FFFFFF;
            }
            QLineEdit::placeholder {
                color: #94A3B8;
            }
        """)


class PulseProgressBar(QProgressBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 10px;
                text-align: center;
                height: 12px;
                background-color: rgba(241, 245, 249, 0.9);
                font-size: 11px;
                font-weight: 600;
                color: #6366F1;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6366F1, stop:0.5 #8B5CF6, stop:1 #A855F7);
                border-radius: 10px;
            }
        """)


class ModernListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QFont("Microsoft YaHei UI", 12))
        self.setStyleSheet("""
            QListWidget {
                border: none;
                border-radius: 16px;
                padding: 12px;
                font-size: 14px;
                background-color: rgba(248, 250, 252, 0.5);
                outline: none;
            }
            QListWidget::item {
                padding: 14px 16px;
                border-radius: 12px;
                margin: 4px 0;
                background-color: rgba(255, 255, 255, 0.8);
                border: 1px solid transparent;
            }
            QListWidget::item:hover {
                background-color: rgba(99, 102, 241, 0.08);
                border-color: rgba(99, 102, 241, 0.2);
            }
            QListWidget::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(99, 102, 241, 0.15), stop:1 rgba(139, 92, 246, 0.15));
                border: 2px solid #6366F1;
                font-weight: 600;
                color: #6366F1;
            }
        """)
