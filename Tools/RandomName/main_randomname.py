from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QListWidget, QComboBox, QLineEdit, QSpinBox, 
                             QSlider, QCheckBox, QGroupBox, QFrame, QGridLayout,
                             QWidget, QApplication)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QPainter, QPen, QLinearGradient
import random
import string
import uuid
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from modern_window import ModernWindow


DARK_STYLESHEET = """
    QWidget {
        background-color: #1a1a2e;
        color: #eaeaea;
        font-family: 'Microsoft YaHei UI', 'Segoe UI', sans-serif;
        font-size: 13px;
    }
    QGroupBox {
        font-weight: bold;
        border: 1px solid #3a3a5e;
        border-radius: 10px;
        margin-top: 12px;
        padding-top: 8px;
        color: #a0a0c0;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 8px;
        color: #a0a0c0;
    }
    QLabel {
        color: #c0c0d0;
    }
    QComboBox {
        padding: 8px 12px;
        border-radius: 8px;
        background-color: #2a2a4e;
        color: #eaeaea;
        border: 1px solid #3a3a5e;
        min-width: 120px;
    }
    QComboBox::drop-down {
        border: none;
        width: 24px;
    }
    QComboBox::down-arrow {
        image: none;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid #8888aa;
    }
    QSpinBox {
        padding: 8px 12px;
        border-radius: 6px;
        background-color: #2a2a4e;
        color: #eaeaea;
        border: 1px solid #3a3a5e;
    }
    QLineEdit {
        padding: 8px 12px;
        border-radius: 6px;
        background-color: #2a2a4e;
        color: #eaeaea;
        border: 1px solid #3a3a5e;
    }
    QLineEdit:focus {
        border-color: #6366f1;
    }
    QCheckBox {
        spacing: 8px;
        color: #c0c0d0;
    }
    QCheckBox::indicator {
        width: 16px;
        height: 16px;
        border-radius: 4px;
        border: 1px solid #5a5a7e;
        background-color: #2a2a4e;
    }
    QCheckBox::indicator:hover {
        border-color: #6366f1;
    }
    QCheckBox::indicator:checked {
        background-color: #6366f1;
        border-color: #6366f1;
    }
    QSlider::groove:horizontal {
        height: 6px;
        background-color: #2a2a4e;
        border-radius: 3px;
    }
    QSlider::handle:horizontal {
        width: 16px;
        height: 16px;
        margin: -5px 0;
        background-color: #6366f1;
        border-radius: 8px;
    }
    QSlider::handle:horizontal:hover {
        background-color: #818cf8;
    }
    QListWidget {
        background-color: #16162a;
        border: 1px solid #2a2a4e;
        border-radius: 8px;
        padding: 4px;
        color: #d0d0e0;
    }
    QListWidget::item {
        padding: 8px 12px;
        border-radius: 6px;
        background-color: transparent;
    }
    QListWidget::item:selected {
        background-color: #3b3b6e;
        color: #ffffff;
    }
    QListWidget::item:hover:!selected {
        background-color: #2a2a4e;
    }
"""


BTN_PRIMARY_STYLE = """
    QPushButton {
        font-size: 14px;
        font-weight: bold;
        padding: 12px 20px;
        border-radius: 8px;
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4f46e5, stop:1 #3730a3);
        color: #ffffff;
        border: none;
    }
    QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6366f1, stop:1 #4f46e5);
    }
    QPushButton:pressed {
        background: qlineargradient(x1:0, y1:0, x2:0, y2=1, stop:0 #3730a3, stop:1 #312e81);
    }
"""


BTN_SECONDARY_STYLE = """
    QPushButton {
        font-size: 13px;
        padding: 10px 16px;
        border-radius: 8px;
        background-color: #2a2a4e;
        color: #c0c0d0;
        border: 1px solid #3a3a5e;
    }
    QPushButton:hover {
        background-color: #3a3a6e;
        color: #eaeaea;
        border-color: #5a5a8e;
    }
"""


BTN_SUCCESS_STYLE = """
    QPushButton {
        font-size: 13px;
        padding: 10px 16px;
        border-radius: 8px;
        background-color: #166534;
        color: #dcfce7;
        border: 1px solid #22c55e;
    }
    QPushButton:hover {
        background-color: #15803d;
    }
"""


COLOR_PREVIEW_STYLE = """
    QLabel {
        background-color: #2a2a4e;
        border-radius: 8px;
        padding: 16px;
        font-size: 14px;
        font-family: 'Consolas', 'Monaco', monospace;
        color: #00ff00;
        border: 1px solid #3a3a5e;
    }
"""


RESULT_LABEL_STYLE = """
    QLabel {
        font-size: 15px;
        font-weight: bold;
        color: #ffffff;
        background-color: #2a2a4e;
        border-radius: 10px;
        padding: 16px 20px;
        border: 1px solid #3a3a5e;
    }
"""


class ColorPreviewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(50)
        self.color = "#6366f1"
        self.color_name = "#6366f1"
    
    def set_color(self, color, color_name=""):
        self.color = color
        self.color_name = color_name or color
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(self.color))
        
        text_color = "#ffffff" if self._is_dark(self.color) else "#000000"
        painter.setPen(QPen(QColor(text_color)))
        font = QFont("Consolas", 13)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignCenter, self.color_name)
    
    def _is_dark(self, color):
        c = QColor(color)
        return c.red() * 0.299 + c.green() * 0.587 + c.blue() * 0.114 < 128


class RandomNameWindow(ModernWindow):
    def __init__(self):
        super().__init__(title="随机工具箱")
        self.setGeometry(200, 100, 550, 500)
        self.history = []
    
    def _setup_content(self):
        self.content_widget.setStyleSheet(DARK_STYLESHEET)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)
        
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        mode_label = QLabel("功能:")
        mode_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #a0a0c0;")
        header_layout.addWidget(mode_label)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "🎲 随机点名",
            "🔢 随机整数",
            "🔐 随机密码",
            "🎨 随机颜色",
            "🆔 UUID生成",
            "📜 历史记录"
        ])
        self.mode_combo.setStyleSheet("""
            QComboBox {
                padding: 10px 14px;
                font-size: 14px;
                min-width: 140px;
            }
        """)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        header_layout.addWidget(self.mode_combo)
        header_layout.addStretch()
        
        main_layout.addLayout(header_layout)
        
        self.stack_widget = QWidget()
        self.stack_layout = QVBoxLayout()
        self.stack_layout.setContentsMargins(0, 0, 0, 0)
        self.stack_layout.setSpacing(10)
        self.stack_widget.setLayout(self.stack_layout)
        main_layout.addWidget(self.stack_widget, 1)
        
        self._setup_name_ui()
        self._setup_int_ui()
        self._setup_password_ui()
        self._setup_color_ui()
        self._setup_uuid_ui()
        self._setup_history_ui()
        
        self.content_widget.setLayout(main_layout)
        
        self._on_mode_changed(0)
    
    def _clear_stack(self):
        while self.stack_layout.count():
            item = self.stack_layout.takeAt(0)
            if item.widget():
                item.widget().hide()
    
    def _add_to_stack(self, widget):
        self.stack_layout.addWidget(widget)
    
    def _setup_name_ui(self):
        self.name_widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        self.name_list = QListWidget()
        self._load_names()
        layout.addWidget(self.name_list)
        
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        
        gen_btn = QPushButton("🎲 随机抽取")
        gen_btn.setStyleSheet(BTN_PRIMARY_STYLE)
        gen_btn.clicked.connect(self._generate_name)
        btn_row.addWidget(gen_btn)
        
        add_btn = QPushButton("➕ 添加")
        add_btn.setStyleSheet(BTN_SECONDARY_STYLE)
        add_btn.clicked.connect(self._add_name)
        btn_row.addWidget(add_btn)
        
        layout.addLayout(btn_row)
        
        self.name_result = QLabel("点击按钮随机抽取")
        self.name_result.setStyleSheet(RESULT_LABEL_STYLE)
        layout.addWidget(self.name_result)
        
        self.name_widget.setLayout(layout)
        self._add_to_stack(self.name_widget)
    
    def _setup_int_ui(self):
        self.int_widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(12)
        
        range_box = QGroupBox("整数范围")
        range_layout = QHBoxLayout()
        range_layout.setSpacing(16)
        
        min_container = QVBoxLayout()
        min_container.addWidget(QLabel("最小值:"))
        self.int_min = QSpinBox()
        self.int_min.setRange(-999999, 999999)
        self.int_min.setValue(1)
        min_container.addWidget(self.int_min)
        range_layout.addLayout(min_container)
        
        range_layout.addStretch()
        
        max_container = QVBoxLayout()
        max_container.addWidget(QLabel("最大值:"))
        self.int_max = QSpinBox()
        self.int_max.setRange(-999999, 999999)
        self.int_max.setValue(100)
        max_container.addWidget(self.int_max)
        range_layout.addLayout(max_container)
        
        range_box.setLayout(range_layout)
        layout.addWidget(range_box)
        
        count_row = QHBoxLayout()
        count_row.addWidget(QLabel("生成数量:"))
        self.int_count = QSpinBox()
        self.int_count.setRange(1, 20)
        self.int_count.setValue(1)
        count_row.addWidget(self.int_count)
        count_row.addStretch()
        layout.addLayout(count_row)
        
        gen_btn = QPushButton("🔢 生成整数")
        gen_btn.setStyleSheet(BTN_PRIMARY_STYLE)
        gen_btn.clicked.connect(self._generate_int)
        layout.addWidget(gen_btn)
        
        self.int_result = QLabel("")
        self.int_result.setStyleSheet(RESULT_LABEL_STYLE)
        layout.addWidget(self.int_result)
        
        layout.addStretch()
        self.int_widget.setLayout(layout)
        self._add_to_stack(self.int_widget)
    
    def _setup_password_ui(self):
        self.pwd_widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(12)
        
        options_box = QGroupBox("密码选项")
        opts_layout = QGridLayout()
        opts_layout.setSpacing(10)
        
        self.pwd_upper = QCheckBox("大写 A-Z")
        self.pwd_upper.setChecked(True)
        self.pwd_lower = QCheckBox("小写 a-z")
        self.pwd_lower.setChecked(True)
        self.pwd_digits = QCheckBox("数字 0-9")
        self.pwd_digits.setChecked(True)
        self.pwd_special = QCheckBox("符号 !@#$%")
        self.pwd_special.setChecked(True)
        
        opts_layout.addWidget(self.pwd_upper, 0, 0)
        opts_layout.addWidget(self.pwd_lower, 0, 1)
        opts_layout.addWidget(self.pwd_digits, 1, 0)
        opts_layout.addWidget(self.pwd_special, 1, 1)
        
        options_box.setLayout(opts_layout)
        layout.addWidget(options_box)
        
        length_row = QHBoxLayout()
        length_row.addWidget(QLabel("长度:"))
        self.pwd_length = QSpinBox()
        self.pwd_length.setRange(4, 64)
        self.pwd_length.setValue(16)
        length_row.addWidget(self.pwd_length)
        
        self.pwd_slider = QSlider(Qt.Horizontal)
        self.pwd_slider.setRange(4, 64)
        self.pwd_slider.setValue(16)
        self.pwd_slider.valueChanged.connect(self.pwd_length.setValue)
        self.pwd_length.valueChanged.connect(self.pwd_slider.setValue)
        length_row.addWidget(self.pwd_slider)
        length_row.addStretch()
        layout.addLayout(length_row)
        
        gen_btn = QPushButton("🔐 生成密码")
        gen_btn.setStyleSheet(BTN_PRIMARY_STYLE)
        gen_btn.clicked.connect(self._generate_password)
        layout.addWidget(gen_btn)
        
        self.pwd_result = QLabel("")
        self.pwd_result.setStyleSheet(RESULT_LABEL_STYLE)
        layout.addWidget(self.pwd_result)
        
        copy_btn = QPushButton("📋 复制密码")
        copy_btn.setStyleSheet(BTN_SUCCESS_STYLE)
        copy_btn.clicked.connect(self._copy_password)
        layout.addWidget(copy_btn)
        
        layout.addStretch()
        self.pwd_widget.setLayout(layout)
        self._add_to_stack(self.pwd_widget)
    
    def _setup_color_ui(self):
        self.color_widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(12)
        
        self.color_preview = ColorPreviewWidget()
        layout.addWidget(self.color_preview)
        
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        
        hex_btn = QPushButton("🎨 HEX颜色")
        hex_btn.setStyleSheet(BTN_PRIMARY_STYLE)
        hex_btn.clicked.connect(self._generate_hex_color)
        btn_row.addWidget(hex_btn)
        
        rgb_btn = QPushButton("🌈 RGB颜色")
        rgb_btn.setStyleSheet(BTN_PRIMARY_STYLE)
        rgb_btn.clicked.connect(self._generate_rgb_color)
        btn_row.addWidget(rgb_btn)
        
        layout.addLayout(btn_row)
        
        self.color_result = QLabel("")
        self.color_result.setStyleSheet(RESULT_LABEL_STYLE)
        layout.addWidget(self.color_result)
        
        layout.addStretch()
        self.color_widget.setLayout(layout)
        self._add_to_stack(self.color_widget)
    
    def _setup_uuid_ui(self):
        self.uuid_widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(12)
        
        version_row = QHBoxLayout()
        version_row.addWidget(QLabel("版本:"))
        self.uuid_version = QComboBox()
        self.uuid_version.addItems(["UUID v4 (随机)", "UUID v1 (时间戳)", "UUID v5 (命名)"])
        version_row.addWidget(self.uuid_version)
        version_row.addStretch()
        layout.addLayout(version_row)
        
        self.uuid_namespace = QLineEdit()
        self.uuid_namespace.setPlaceholderText("命名空间 (UUID v5)")
        layout.addWidget(self.uuid_namespace)
        
        gen_btn = QPushButton("🆔 生成UUID")
        gen_btn.setStyleSheet(BTN_PRIMARY_STYLE)
        gen_btn.clicked.connect(self._generate_uuid)
        layout.addWidget(gen_btn)
        
        self.uuid_result = QLabel("")
        self.uuid_result.setStyleSheet(RESULT_LABEL_STYLE)
        layout.addWidget(self.uuid_result)
        
        copy_btn = QPushButton("📋 复制")
        copy_btn.setStyleSheet(BTN_SUCCESS_STYLE)
        copy_btn.clicked.connect(self._copy_uuid)
        layout.addWidget(copy_btn)
        
        layout.addStretch()
        self.uuid_widget.setLayout(layout)
        self._add_to_stack(self.uuid_widget)
    
    def _setup_history_ui(self):
        self.history_widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        self.history_list = QListWidget()
        layout.addWidget(self.history_list)
        
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        
        clear_btn = QPushButton("🗑️ 清空")
        clear_btn.setStyleSheet(BTN_SECONDARY_STYLE)
        clear_btn.clicked.connect(self._clear_history)
        btn_row.addWidget(clear_btn)
        
        copy_btn = QPushButton("📋 复制全部")
        copy_btn.setStyleSheet(BTN_SUCCESS_STYLE)
        copy_btn.clicked.connect(self._copy_all_history)
        btn_row.addWidget(copy_btn)
        
        layout.addLayout(btn_row)
        
        self.history_widget.setLayout(layout)
        self._add_to_stack(self.history_widget)
    
    def _on_mode_changed(self, index):
        self._clear_stack()
        
        widgets = [
            self.name_widget,
            self.int_widget,
            self.pwd_widget,
            self.color_widget,
            self.uuid_widget,
            self.history_widget
        ]
        
        for widget in widgets:
            widget.hide()
        
        widgets[index].show()
        self.stack_layout.addWidget(widgets[index])
    
    def _load_names(self):
        name_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "Data", "name.txt")
        if os.path.exists(name_file):
            with open(name_file, 'r', encoding='utf-8') as f:
                names = f.read().splitlines()
                self.name_list.addItems([n for n in names if n.strip()])
    
    def _generate_name(self):
        count = self.name_list.count()
        if count > 0:
            name = self.name_list.item(random.randint(0, count - 1)).text()
            self.name_result.setText(f"抽中: {name}")
            self._add_to_history(f"点名: {name}")
    
    def _add_name(self):
        from PyQt5.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "添加", "请输入名称:")
        if ok and name.strip():
            self.name_list.addItem(name.strip())
    
    def _generate_int(self):
        min_val = self.int_min.value()
        max_val = self.int_max.value()
        count = self.int_count.value()
        
        if min_val > max_val:
            min_val, max_val = max_val, min_val
        
        results = [str(random.randint(min_val, max_val)) for _ in range(count)]
        result_text = ", ".join(results)
        self.int_result.setText(result_text)
        self._add_to_history(f"整数 {min_val}-{max_val}: {result_text}")
    
    def _generate_password(self):
        chars = ""
        if self.pwd_upper.isChecked():
            chars += string.ascii_uppercase
        if self.pwd_lower.isChecked():
            chars += string.ascii_lowercase
        if self.pwd_digits.isChecked():
            chars += string.digits
        if self.pwd_special.isChecked():
            chars += "!@#$%^&*()_+-=[]{}|;:,.<>?"
        
        if not chars:
            self.pwd_result.setText("请选择字符类型")
            return
        
        length = self.pwd_length.value()
        pwd = ''.join(random.choice(chars) for _ in range(length))
        self.pwd_result.setText(pwd)
        self._add_to_history(f"密码 ({length}位)")
    
    def _copy_password(self):
        text = self.pwd_result.text()
        if text and text != "请选择字符类型":
            QApplication.clipboard().setText(text)
    
    def _generate_hex_color(self):
        color = "#{:06x}".format(random.randint(0, 0xFFFFFF))
        self.color_preview.set_color(color)
        self.color_result.setText(color)
        self._add_to_history(f"HEX: {color}")
    
    def _generate_rgb_color(self):
        r, g, b = random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)
        color_str = f"rgb({r}, {g}, {b})"
        self.color_preview.set_color(color_str, color_str)
        self.color_result.setText(color_str)
        self._add_to_history(f"RGB: {color_str}")
    
    def _generate_uuid(self):
        version = self.uuid_version.currentIndex()
        
        if version == 0:
            result = str(uuid.uuid4())
        elif version == 1:
            result = str(uuid.uuid1())
        else:
            namespace = self.uuid_namespace.text().strip()
            if namespace:
                result = str(uuid.uuid5(uuid.NAMESPACE_DNS, namespace))
            else:
                result = str(uuid.uuid5(uuid.NAMESPACE_DNS, "default"))
        
        self.uuid_result.setText(result)
        self._add_to_history(f"UUID: {result[:8]}...")
    
    def _copy_uuid(self):
        text = self.uuid_result.text()
        if text:
            QApplication.clipboard().setText(text)
    
    def _add_to_history(self, item):
        from datetime import datetime
        time_str = datetime.now().strftime("%H:%M:%S")
        self.history.insert(0, f"[{time_str}] {item}")
        if len(self.history) > 100:
            self.history.pop()
        self._update_history()
    
    def _update_history(self):
        self.history_list.clear()
        self.history_list.addItems(self.history)
    
    def _clear_history(self):
        self.history.clear()
        self.history_list.clear()
    
    def _copy_all_history(self):
        if self.history:
            QApplication.clipboard().setText("\n".join(self.history))
