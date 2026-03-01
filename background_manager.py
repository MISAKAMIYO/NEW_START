"""
背景图片管理器
支持自定义背景图片和透明度调节
"""

import os
import json
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QSlider, QFileDialog, QFrame)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QPainter


class BackgroundManager(QWidget):
    """背景图片管理器"""
    
    background_changed = pyqtSignal(str)  # 背景图片改变信号
    opacity_changed = pyqtSignal(float)   # 透明度改变信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_background = None
        self.current_opacity = 0.8
        self.backgrounds_dir = os.path.join(os.path.dirname(__file__), "backgrounds")
        
        # 创建背景目录
        os.makedirs(self.backgrounds_dir, exist_ok=True)
        
        self.setup_ui()
        self.load_settings()
        
    def setup_ui(self):
        """设置UI"""
        self.setFixedSize(400, 300)
        self.setWindowTitle("背景设置")
        self.setStyleSheet("""
            QWidget {
                background: rgba(26, 26, 26, 0.9);
                border: 2px solid #333333;
                border-radius: 16px;
                color: white;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 标题
        title = QLabel("背景设置")
        title.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                font-family: "Microsoft YaHei", sans-serif;
                color: white;
            }
        """)
        title.setAlignment(Qt.AlignCenter)
        
        # 当前背景预览
        self.preview_label = QLabel()
        self.preview_label.setFixedSize(200, 120)
        self.preview_label.setStyleSheet("""
            QLabel {
                border: 2px solid #444444;
                border-radius: 8px;
                background: #1A1A1A;
            }
        """)
        self.preview_label.setAlignment(Qt.AlignCenter)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        self.select_btn = QPushButton("选择图片")
        self.select_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                          stop:0 #0099FF, stop:1 #CC66FF);
                border: none;
                border-radius: 8px;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                          stop:0 #00AAFF, stop:1 #DD77FF);
            }
        """)
        self.select_btn.clicked.connect(self.select_background)
        
        self.default_btn = QPushButton("默认背景")
        self.default_btn.setStyleSheet("""
            QPushButton {
                background: #333333;
                border: 1px solid #555555;
                border-radius: 8px;
                color: white;
                font-size: 14px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background: #444444;
            }
        """)
        self.default_btn.clicked.connect(self.set_default_background)
        
        button_layout.addWidget(self.select_btn)
        button_layout.addWidget(self.default_btn)
        
        # 透明度调节
        opacity_layout = QVBoxLayout()
        
        opacity_label = QLabel("背景透明度")
        opacity_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-family: "Microsoft YaHei", sans-serif;
                color: #CCCCCC;
            }
        """)
        
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(10, 100)
        self.opacity_slider.setValue(int(self.current_opacity * 100))
        self.opacity_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #444444;
                height: 6px;
                background: #333333;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                           stop:0 #0099FF, stop:1 #CC66FF);
                border: 1px solid #444444;
                width: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }
        """)
        self.opacity_slider.valueChanged.connect(self.on_opacity_changed)
        
        self.opacity_value = QLabel(f"{int(self.current_opacity * 100)}%")
        self.opacity_value.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #888888;
                font-family: "Microsoft YaHei", sans-serif;
            }
        """)
        
        opacity_layout.addWidget(opacity_label)
        opacity_layout.addWidget(self.opacity_slider)
        opacity_layout.addWidget(self.opacity_value)
        
        # 添加到主布局
        layout.addWidget(title)
        layout.addWidget(self.preview_label, alignment=Qt.AlignCenter)
        layout.addLayout(button_layout)
        layout.addLayout(opacity_layout)
        layout.addStretch()
        
        self.setLayout(layout)
        
    def select_background(self):
        """选择背景图片"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "选择背景图片", 
            "", 
            "图片文件 (*.jpg *.jpeg *.png *.bmp *.gif)"
        )
        
        if file_path:
            # 复制图片到背景目录
            filename = os.path.basename(file_path)
            dest_path = os.path.join(self.backgrounds_dir, filename)
            
            try:
                import shutil
                shutil.copy2(file_path, dest_path)
                self.set_background(dest_path)
                self.save_settings()
            except Exception as e:
                print(f"复制背景图片失败: {e}")
                
    def set_default_background(self):
        """设置为默认背景（无背景图片）"""
        self.current_background = None
        self.update_preview()
        self.background_changed.emit("")
        self.save_settings()
        
    def set_background(self, image_path):
        """设置背景图片"""
        if os.path.exists(image_path):
            self.current_background = image_path
            self.update_preview()
            self.background_changed.emit(image_path)
            
    def on_opacity_changed(self, value):
        """透明度改变事件"""
        self.current_opacity = value / 100.0
        self.opacity_value.setText(f"{value}%")
        self.opacity_changed.emit(self.current_opacity)
        self.save_settings()
        
    def update_preview(self):
        """更新预览"""
        if self.current_background:
            pixmap = QPixmap(self.current_background)
            scaled_pixmap = pixmap.scaled(180, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.preview_label.setPixmap(scaled_pixmap)
        else:
            self.preview_label.setText("默认背景")
            self.preview_label.setStyleSheet("""
                QLabel {
                    border: 2px solid #444444;
                    border-radius: 8px;
                    background: #1A1A1A;
                    color: #888888;
                    font-size: 14px;
                }
            """)
            
    def load_settings(self):
        """加载设置"""
        settings_file = os.path.join(self.backgrounds_dir, "settings.json")
        
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    
                if 'background' in settings and settings['background']:
                    if os.path.exists(settings['background']):
                        self.current_background = settings['background']
                    
                if 'opacity' in settings:
                    self.current_opacity = settings['opacity']
                    self.opacity_slider.setValue(int(self.current_opacity * 100))
                    
            except Exception as e:
                print(f"加载背景设置失败: {e}")
                
        self.update_preview()
        
    def save_settings(self):
        """保存设置"""
        settings_file = os.path.join(self.backgrounds_dir, "settings.json")
        
        settings = {
            'background': self.current_background if self.current_background else "",
            'opacity': self.current_opacity
        }
        
        try:
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存背景设置失败: {e}")


class BackgroundPreview(QLabel):
    """背景预览组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 80)
        self.setStyleSheet("""
            QLabel {
                border: 2px solid #444444;
                border-radius: 8px;
                background: #1A1A1A;
            }
        """)
        
    def set_background(self, image_path):
        """设置背景预览"""
        if image_path and os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            scaled_pixmap = pixmap.scaled(116, 76, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.setPixmap(scaled_pixmap)
        else:
            self.clear()
            self.setText("默认")
            self.setAlignment(Qt.AlignCenter)


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    manager = BackgroundManager()
    manager.show()
    
    sys.exit(app.exec_())