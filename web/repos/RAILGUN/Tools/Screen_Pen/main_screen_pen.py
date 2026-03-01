"""
希沃白板 - 全屏透明遮罩模式
覆盖整个桌面的透明白板，所有操作都在遮罩上进行
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                              QLabel, QSlider, QColorDialog, QFrame, QButtonGroup,
                              QApplication, QDialog, QDesktopWidget)
from PyQt5.QtCore import Qt, QPoint, QPointF, pyqtSignal, QTimer
from PyQt5.QtGui import (QPainter, QColor, QPen, QPixmap, QCursor, 
                          QFont, QPainterPath)


class DrawingCanvas(QWidget):
    """绘图画布"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        
        self.drawing = False
        self.last_point = QPoint()
        self.pen_color = QColor(255, 0, 0)
        self.pen_width = 3
        self.current_tool = 'pen'
        
        self.paths = []
        self.current_path = QPainterPath()
        
        self.setMouseTracking(True)
        self.update_cursor()
    
    def update_cursor(self):
        if self.current_tool == 'eraser':
            self.setCursor(QCursor(Qt.SizeAllCursor))
        else:
            self.setCursor(QCursor(Qt.CrossCursor))
    
    def set_tool(self, tool):
        self.current_tool = tool
        self.update_cursor()
    
    def set_pen_color(self, color):
        self.pen_color = QColor(color)
    
    def set_pen_width(self, width):
        self.pen_width = width
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        painter.eraseRect(self.rect())
        
        for path_data in self.paths:
            path, color, width, tool = path_data
            pen = QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            if tool == 'eraser':
                pen.setColor(Qt.white)
                pen.setWidth(25)
            elif tool == 'highlighter':
                pen.setColor(QColor(255, 255, 0, 80))
                pen.setWidth(25)
            painter.setPen(pen)
            painter.drawPath(path)
        
        if self.drawing and not self.current_path.isEmpty():
            pen = QPen(self.pen_color, self.pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            if self.current_tool == 'eraser':
                pen.setColor(Qt.white)
                pen.setWidth(25)
            elif self.current_tool == 'highlighter':
                pen.setColor(QColor(255, 255, 0, 80))
                pen.setWidth(25)
            painter.setPen(pen)
            painter.drawPath(self.current_path)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.last_point = event.pos()
            self.current_path = QPainterPath()
            self.current_path.moveTo(event.pos())
            self.update()
    
    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self.drawing:
            self.current_path.lineTo(event.pos())
            self.update()
        elif self.current_tool == 'eraser':
            self.setCursor(QCursor(Qt.CrossCursor))
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.drawing:
            self.drawing = False
            if not self.current_path.isEmpty():
                self.paths.append((QPainterPath(self.current_path), 
                                   QColor(self.pen_color), 
                                   self.pen_width, 
                                   self.current_tool))
            self.current_path = QPainterPath()
            self.update()
    
    def clear(self):
        self.paths.clear()
        self.current_path = QPainterPath()
        self.update()
    
    def undo(self):
        if self.paths:
            self.paths.pop()
            self.update()


class WhiteboardToolbar(QWidget):
    """工具栏"""
    
    tool_selected = pyqtSignal(str)
    color_changed = pyqtSignal(QColor)
    width_changed = pyqtSignal(int)
    undo_signal = pyqtSignal()
    clear_signal = pyqtSignal()
    save_signal = pyqtSignal()
    close_signal = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.dragging = False
        self.drag_position = QPoint()
        self.current_color = QColor(255, 0, 0)
        self.setup_ui()
    
    def setup_ui(self):
        self.setFixedHeight(48)
        self.setMinimumWidth(380)
        
        desktop = QDesktopWidget()
        screen_rect = desktop.screenGeometry()
        self.move(100, 100)
        
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(6)
        
        self.tool_buttons = {}
        
        tools = [
            ("✏", "pen", "画笔"),
            ("🖍", "highlighter", "荧光笔"),
            ("🧹", "eraser", "橡皮"),
        ]
        
        for icon, tool_id, tip in tools:
            btn = QPushButton(icon)
            btn.setToolTip(tip)
            btn.setCheckable(True)
            btn.setChecked(tool_id == "pen")
            btn.clicked.connect(lambda checked, t=tool_id, b=btn: self.on_tool_clicked(t, b))
            self.tool_buttons[tool_id] = btn
            layout.addWidget(btn)
        
        layout.addWidget(self.create_separator())
        
        shapes = [
            ("➖", "line", "直线"),
            ("⬜", "rect", "矩形"),
            ("⭕", "circle", "椭圆"),
        ]
        
        for icon, shape_id, tip in shapes:
            btn = QPushButton(icon)
            btn.setToolTip(tip)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, s=shape_id, b=btn: self.on_tool_clicked(s, b))
            self.tool_buttons[shape_id] = btn
            layout.addWidget(btn)
        
        layout.addWidget(self.create_separator())
        
        self.color_btn = QPushButton("🎨")
        self.color_btn.setFixedSize(32, 32)
        self.update_color_btn()
        layout.addWidget(self.color_btn)
        
        layout.addWidget(QLabel("粗"))
        
        self.width_slider = QSlider(Qt.Horizontal)
        self.width_slider.setMinimum(1)
        self.width_slider.setMaximum(15)
        self.width_slider.setValue(3)
        self.width_slider.setFixedWidth(60)
        layout.addWidget(self.width_slider)
        
        layout.addWidget(self.create_separator())
        
        self.undo_btn = QPushButton("↩")
        self.undo_btn.setFixedSize(32, 32)
        layout.addWidget(self.undo_btn)
        
        self.clear_btn = QPushButton("🗑")
        self.clear_btn.setFixedSize(32, 32)
        layout.addWidget(self.clear_btn)
        
        self.save_btn = QPushButton("💾")
        self.save_btn.setFixedSize(32, 32)
        layout.addWidget(self.save_btn)
        
        layout.addStretch()
        
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(32, 32)
        layout.addWidget(self.close_btn)
        
        self.setLayout(layout)
        
        self.color_btn.clicked.connect(self.choose_color)
        self.width_slider.valueChanged.connect(self.on_width_changed)
        self.undo_btn.clicked.connect(self.undo_signal)
        self.clear_btn.clicked.connect(self.clear_signal)
        self.save_btn.clicked.connect(self.save_signal)
        self.close_btn.clicked.connect(self.close_signal)
        
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(30, 30, 40, 230);
                border-radius: 10px;
            }
            QPushButton {
                background-color: rgba(60, 60, 80, 200);
                color: white;
                border: 1px solid rgba(100, 100, 120, 180);
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: rgba(80, 80, 100, 220);
            }
            QPushButton:checked {
                background-color: rgba(99, 102, 241, 200);
            }
            QLabel {
                color: rgba(200, 200, 210, 230);
                font-size: 11px;
            }
        """)
    
    def create_separator(self):
        frame = QFrame()
        frame.setFrameShape(QFrame.VLine)
        frame.setStyleSheet("color: rgba(100, 100, 120, 150);")
        frame.setFixedWidth(1)
        return frame
    
    def on_tool_clicked(self, tool_id, button):
        for tid, btn in self.tool_buttons.items():
            if tid in ['pen', 'highlighter', 'eraser', 'line', 'rect', 'circle']:
                btn.setChecked(btn == button)
        self.tool_selected.emit(tool_id)
    
    def choose_color(self):
        color = QColorDialog.getColor(self.current_color, self, "选择颜色")
        if color.isValid():
            self.current_color = color
            self.update_color_btn()
            self.color_changed.emit(color)
    
    def update_color_btn(self):
        self.color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.current_color.name()};
                border: 2px solid white;
                border-radius: 6px;
            }}
        """)
    
    def on_width_changed(self, value):
        self.width_changed.emit(value)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self.dragging:
            self.move(event.globalPos() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        self.dragging = False


class WhiteboardWindow(QWidget):
    """白板主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("希沃白板")
        
        desktop = QDesktopWidget()
        screen_rect = desktop.availableGeometry(desktop.primaryScreen())
        self.setGeometry(screen_rect)
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        
        self.canvas = DrawingCanvas(self)
        self.canvas.setGeometry(screen_rect)
        
        self.toolbar = WhiteboardToolbar()
        self.toolbar.show()
        
        self.status_label = QLabel("💡 拖动工具栏到任意位置 | 左键绘制 | ESC退出", self)
        self.status_label.setGeometry(
            screen_rect.width() // 2 - 160,
            screen_rect.height() - 50,
            320, 26
        )
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 12px;
                background-color: rgba(30, 30, 40, 180);
                border-radius: 13px;
            }
        """)
        self.status_label.show()
        
        self.toolbar.tool_selected.connect(self.canvas.set_tool)
        self.toolbar.color_changed.connect(self.canvas.set_pen_color)
        self.toolbar.width_changed.connect(self.canvas.set_pen_width)
        self.toolbar.undo_signal.connect(self.canvas.undo)
        self.toolbar.clear_signal.connect(self.canvas.clear)
        self.toolbar.save_signal.connect(self.save_canvas)
        self.toolbar.close_signal.connect(self.close)
        
        self.setStyleSheet("background: transparent;")
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_S and event.modifiers() & Qt.ControlModifier:
            self.save_canvas()
        super().keyPressEvent(event)
    
    def closeEvent(self, event):
        self.toolbar.close()
        super().closeEvent(event)
    
    def save_canvas(self):
        from PyQt5.QtWidgets import QFileDialog
        from datetime import datetime
        
        desktop = QDesktopWidget()
        screen_rect = desktop.availableGeometry(desktop.primaryScreen())
        
        pixmap = QPixmap(screen_rect.size())
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        for path_data in self.canvas.paths:
            path, color, width, tool = path_data
            pen = QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            if tool == 'eraser':
                pen.setColor(Qt.white)
                pen.setWidth(25)
            elif tool == 'highlighter':
                pen.setColor(QColor(255, 255, 0, 80))
                pen.setWidth(25)
            painter.setPen(pen)
            painter.drawPath(path)
        
        painter.end()
        
        default_name = f"白板_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath, _ = QFileDialog.getSaveFileName(
            self, "保存白板", default_name, "PNG图片 (*.png)"
        )
        
        if filepath:
            pixmap.save(filepath)
            self.status_label.setText(f"✓ 已保存: {os.path.basename(filepath)}")
            QTimer.singleShot(2000, lambda: 
                self.status_label.setText("💡 拖动工具栏到任意位置 | 左键绘制 | ESC退出")
            )
    
    def showEvent(self, event):
        super().showEvent(event)
        self.activateWindow()
        self.raise_()
        self.toolbar.raise_()
        self.status_label.raise_()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    whiteboard = WhiteboardWindow()
    whiteboard.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
