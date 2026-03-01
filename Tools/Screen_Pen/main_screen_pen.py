"""
专业屏幕画笔工具
半透明覆盖，可看到桌面内容
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                              QLabel, QSlider, QColorDialog, QFrame, QApplication, 
                              QDesktopWidget)
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QPixmap, QCursor


class ModernToolbar(QWidget):
    """独立悬浮工具栏"""
    
    def __init__(self, canvas=None):
        super().__init__()
        self.canvas = canvas
        self.dragging = False
        self.drag_position = QPoint()
        self.current_color = QColor("#FF3B30")
        self.current_tool = "pen"
        self.current_size = 5
        
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        container = QWidget()
        container.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1a1a2e, stop:1 #16213e);
                border-radius: 16px;
            }
        """)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)
        
        tools_group = QHBoxLayout()
        tools_group.setSpacing(6)
        
        self.tool_btns = {}
        tools = [
            ("pen", "✏️", "画笔"),
            ("marker", "🖊️", "马克笔"),
            ("highlighter", "🖍️", "荧光笔"),
            ("eraser", "🧹", "橡皮"),
        ]
        
        for tool_id, icon, tip in tools:
            btn = self.create_tool_btn(icon, tip)
            btn.clicked.connect(lambda checked, t=tool_id: self.select_tool(t))
            self.tool_btns[tool_id] = btn
            tools_group.addWidget(btn)
        
        layout.addLayout(tools_group)
        layout.addWidget(self.create_separator())
        
        self.color_palette = self.create_color_palette()
        layout.addLayout(self.color_palette)
        
        layout.addWidget(self.create_separator())
        
        size_layout = QVBoxLayout()
        size_layout.setSpacing(4)
        size_label = QLabel("粗细")
        size_label.setStyleSheet("color: #aaa; font-size: 10px;")
        size_label.setAlignment(Qt.AlignCenter)
        size_layout.addWidget(size_label)
        
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setMinimum(1)
        self.size_slider.setMaximum(20)
        self.size_slider.setValue(5)
        self.size_slider.setFixedWidth(80)
        self.size_slider.setStyleSheet(self.get_slider_style())
        size_layout.addWidget(self.size_slider)
        
        layout.addLayout(size_layout)
        layout.addWidget(self.create_separator())
        
        action_layout = QHBoxLayout()
        action_layout.setSpacing(6)
        
        self.undo_btn = self.create_action_btn("↩️", "撤销")
        self.undo_btn.clicked.connect(lambda: self.action_triggered.emit("undo"))
        action_layout.addWidget(self.undo_btn)
        
        self.clear_btn = self.create_action_btn("🗑️", "清空")
        self.clear_btn.clicked.connect(lambda: self.action_triggered.emit("clear"))
        action_layout.addWidget(self.clear_btn)
        
        self.save_btn = self.create_action_btn("💾", "保存")
        self.save_btn.clicked.connect(lambda: self.action_triggered.emit("save"))
        action_layout.addWidget(self.save_btn)
        
        layout.addLayout(action_layout)
        layout.addWidget(self.create_separator())
        
        self.close_btn = self.create_action_btn("✕", "关闭")
        self.close_btn.setStyleSheet("""
            QPushButton {
                background: #FF3B30;
                border-radius: 8px;
            }
            QPushButton:hover {
                background: #FF534A;
            }
        """)
        self.close_btn.clicked.connect(lambda: self.action_triggered.emit("close"))
        layout.addWidget(self.close_btn)
        
        container.setLayout(layout)
        main_layout.addWidget(container)
        self.setLayout(main_layout)
        
        self.size_slider.valueChanged.connect(self.on_size_changed)
        
        self.select_tool("pen")
        self.update_color_display()
        
    def create_tool_btn(self, icon, tip):
        btn = QPushButton(icon)
        btn.setFixedSize(40, 40)
        btn.setToolTip(tip)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.05);
                border: 2px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                font-size: 18px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
                border-color: rgba(255, 255, 255, 0.2);
            }
            QPushButton:checked {
                background: rgba(59, 130, 246, 0.3);
                border-color: #3B82F6;
            }
        """)
        btn.setCheckable(True)
        return btn
    
    def create_action_btn(self, icon, tip):
        btn = QPushButton(icon)
        btn.setFixedSize(40, 40)
        btn.setToolTip(tip)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.05);
                border: 2px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                font-size: 16px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
                border-color: rgba(255, 255, 255, 0.2);
            }
        """)
        return btn
    
    def create_separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.VLine)
        line.setStyleSheet("background: rgba(255, 255, 255, 0.1);")
        line.setFixedWidth(1)
        return line
    
    def create_color_palette(self):
        layout = QHBoxLayout()
        layout.setSpacing(4)
        
        self.color_btns = []
        colors = [
            "#FF3B30", "#FF9500", "#FFCC00", "#4CD964",
            "#5AC8FA", "#007AFF", "#5856D6", "#FF2D55",
            "#FFFFFF", "#8E8E93"
        ]
        
        for color in colors:
            btn = QPushButton()
            btn.setFixedSize(24, 24)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {color};
                    border: 2px solid rgba(255, 255, 255, 0.3);
                    border-radius: 12px;
                }}
                QPushButton:hover {{
                    border-color: white;
                }}
            """)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, c=color: self.select_color(c))
            layout.addWidget(btn)
            self.color_btns.append((btn, color))
        
        custom_btn = QPushButton("🎨")
        custom_btn.setFixedSize(24, 24)
        custom_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 red, stop:0.5 green, stop:1 blue);
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 12px;
                font-size: 12px;
            }
        """)
        custom_btn.setCursor(Qt.PointingHandCursor)
        custom_btn.clicked.connect(self.choose_custom_color)
        layout.addWidget(custom_btn)
        
        return layout
    
    def get_slider_style(self):
        return """
            QSlider::groove:horizontal {
                height: 6px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #3B82F6;
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background: #60A5FA;
            }
        """
    
    def on_size_changed(self, value):
        self.current_size = value
        self.size_changed.emit(value)
        if self.canvas:
            self.canvas.set_pen(self.current_color, value)
    
    def select_tool(self, tool):
        self.current_tool = tool
        for tool_id, btn in self.tool_btns.items():
            btn.setChecked(tool_id == tool)
        self.tool_selected.emit(tool)
        
        if self.canvas:
            self.canvas.set_tool(tool)
    
    def select_color(self, color):
        self.current_color = QColor(color)
        self.color_changed.emit(self.current_color)
        self.update_color_display()
        
        if self.canvas:
            self.canvas.set_pen(self.current_color, self.current_size)
    
    def choose_custom_color(self):
        color = QColorDialog.getColor(self.current_color, self, "选择颜色")
        if color.isValid():
            self.current_color = color
            self.color_changed.emit(color)
            self.update_color_display()
            
            if self.canvas:
                self.canvas.set_pen(self.current_color, self.current_size)
    
    def update_color_display(self):
        for btn, color in self.color_btns:
            is_selected = QColor(color) == self.current_color
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {color};
                    border: 3px solid {'white' if is_selected else 'rgba(255, 255, 255, 0.3)'};
                    border-radius: 12px;
                }}
                QPushButton:hover {{
                    border-color: white;
                }}
            """)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPos() - self.pos()
    
    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
    
    def mouseReleaseEvent(self, event):
        self.dragging = False
    
    tool_selected = pyqtSignal(str)
    color_changed = pyqtSignal(QColor)
    size_changed = pyqtSignal(int)
    action_triggered = pyqtSignal(str)


class TranslucentCanvas(QWidget):
    """半透明画布 - 可看到桌面"""
    
    def __init__(self):
        super().__init__()
        
        desktop = QDesktopWidget()
        screen = desktop.availableGeometry(desktop.primaryScreen())
        
        # 关键：使用半透明背景 + 窗口置顶
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setGeometry(screen)
        
        self.drawing = False
        self.paths = []
        self.current_path = []
        
        self.pen_color = QColor("#FF3B30")
        self.pen_size = 5
        self.current_tool = "pen"
        
        self.setMouseTracking(True)
        
        self.tip_label = QLabel("✏️ 画笔 | 红色 | 粗细 5", self)
        self.tip_label.setStyleSheet("""
            QLabel {
                color: white;
                background: rgba(0, 0, 0, 150);
                padding: 8px 16px;
                border-radius: 20px;
                font-size: 13px;
            }
        """)
        self.tip_label.adjustSize()
        self.tip_label.move(screen.width() // 2 - self.tip_label.width() // 2, screen.height() - 60)
        self.tip_label.show()
        
        QTimer.singleShot(5000, lambda: self.tip_label.setText("按 ESC 退出 | Ctrl+Z 撤销 | C 清空 | S 保存"))
        QTimer.singleShot(8000, self.tip_label.hide)
    
    def set_pen(self, color, size):
        self.pen_color = QColor(color)
        self.pen_size = size
        self.update_tip()
    
    def set_tool(self, tool):
        self.current_tool = tool
        if tool == "eraser":
            self.setCursor(QCursor(Qt.OpenHandCursor))
        else:
            self.setCursor(QCursor(Qt.CrossCursor))
        self.update_tip()
    
    def update_tip(self):
        tool_names = {
            "pen": "✏️ 画笔",
            "marker": "🖊️ 马克笔",
            "highlighter": "🖍️ 荧光笔",
            "eraser": "🧹 橡皮"
        }
        tip = f"{tool_names.get(self.current_tool, '✏️')} | {self.pen_color.name()} | 粗细 {self.pen_size}"
        self.tip_label.setText(tip)
        self.tip_label.adjustSize()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        for path_data in self.paths:
            self.draw_path(painter, path_data)
        
        if self.current_path:
            self.draw_path(painter, self.current_path)
    
    def draw_path(self, painter, path_data):
        if len(path_data) < 4:
            return
        
        points = path_data[:-3]
        color = path_data[-3]
        size = path_data[-2]
        tool = path_data[-1]
        
        if tool == "pen":
            pen = QPen(color, size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
        elif tool == "marker":
            c = QColor(color)
            c.setAlpha(180)
            pen = QPen(c, size * 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
        elif tool == "highlighter":
            pen = QPen(QColor(255, 255, 0, 80), 20, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
        elif tool == "eraser":
            pen = QPen(QColor(0, 0, 0, 0), 30, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setCompositionMode(QPainter.CompositionMode_DestinationOut)
            painter.setPen(pen)
        
        for i in range(len(points) - 1):
            painter.drawLine(points[i], points[i + 1])
        
        if tool == "eraser":
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.current_path = [event.pos(), QColor(self.pen_color), int(self.pen_size), self.current_tool]
    
    def mouseMoveEvent(self, event):
        if self.drawing and event.buttons() & Qt.LeftButton:
            self.current_path.insert(-3, event.pos())
            self.update()
    
    def mouseReleaseEvent(self, event):
        if self.drawing:
            self.drawing = False
            if len(self.current_path) >= 4:
                self.paths.append(self.current_path)
            self.current_path = []
            self.update()
    
    def undo(self):
        if self.paths:
            self.paths.pop()
            self.update()
    
    def clear(self):
        self.paths.clear()
        self.current_path = []
        self.update()
    
    def get_pixmap(self):
        pixmap = QPixmap(self.size())
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        for path_data in self.paths:
            self.draw_path(painter, path_data)
        
        return pixmap
    
    def show_tip(self, text):
        self.tip_label.setText(text)
        self.tip_label.show()
        QTimer.singleShot(2000, self.tip_label.hide)
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_C and not event.modifiers():
            self.clear()
        elif event.key() == Qt.Key_S and event.modifiers() & Qt.ControlModifier:
            self.save_canvas()
        elif event.key() == Qt.Key_Z and event.modifiers() & Qt.ControlModifier:
            self.undo()
    
    def save_canvas(self):
        from PyQt5.QtWidgets import QFileDialog
        from datetime import datetime
        
        pixmap = self.get_pixmap()
        
        default_name = f"屏幕画笔_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath, _ = QFileDialog.getSaveFileName(
            self, "保存图片", default_name, "PNG 图片 (*.png)"
        )
        
        if filepath:
            pixmap.save(filepath)
            self.show_tip(f"✓ 已保存：{os.path.basename(filepath)}")


class ScreenPenApp:
    """屏幕画笔应用管理器"""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setStyle('Fusion')
        
        self.canvas = TranslucentCanvas()
        self.toolbar = ModernToolbar(self.canvas)
        
        self.connect_signals()
        
    def connect_signals(self):
        self.toolbar.tool_selected.connect(self.canvas.set_tool)
        self.toolbar.color_changed.connect(lambda c: self.canvas.set_pen(c, self.toolbar.current_size))
        self.toolbar.size_changed.connect(lambda s: self.canvas.set_pen(self.toolbar.current_color, s))
        self.toolbar.action_triggered.connect(self.handle_action)
    
    def handle_action(self, action):
        if action == "undo":
            self.canvas.undo()
        elif action == "clear":
            self.canvas.clear()
        elif action == "save":
            self.canvas.save_canvas()
        elif action == "close":
            self.close()
    
    def show(self):
        self.canvas.show()
        self.canvas.raise_()
        self.canvas.activateWindow()
        
        desktop = QDesktopWidget()
        screen = desktop.availableGeometry(desktop.primaryScreen())
        self.toolbar.move(screen.left() + screen.width() // 2 - 300, screen.top() + 20)
        self.toolbar.show()
        self.toolbar.raise_()
        self.toolbar.activateWindow()
        
        self.canvas.setFocus()
    
    def close(self):
        self.toolbar.close()
        self.canvas.close()
        self.app.quit()
    
    def run(self):
        self.show()
        sys.exit(self.app.exec_())


def main():
    app = ScreenPenApp()
    app.run()


if __name__ == "__main__":
    main()
