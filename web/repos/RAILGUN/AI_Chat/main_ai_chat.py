"""
AI聊天模块 - 现代化聊天界面
支持多AI提供商、流式输出和自定义配置
"""

import sys
import os
import logging
from typing import List, Dict, Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QLabel, QComboBox, QCheckBox, QDialog,
    QFormLayout, QScrollArea, QFrame, QGroupBox, QMessageBox,
    QApplication, QSizePolicy, QSpacerItem
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt5.QtGui import QFont, QTextCursor, QColor, QPalette, QIcon

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from settings_manager import ConfigManager
from AI_Chat.ai_chat import AIChatThread, ChatHistoryManager
from AI_Chat.ai_model import AIManager

logger = logging.getLogger(__name__)


class ModernButton(QPushButton):
    """现代化按钮，与RAILGUN主界面风格一致"""

    def __init__(self, text: str, parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.setMinimumHeight(45)
        self.setFont(QFont("Microsoft YaHei UI", 10))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background-color: #4A90D9;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 20px;
                font-weight: bold;
                text-align: center;
            }
            QPushButton:hover {
                background-color: #5BA0E9;
            }
            QPushButton:pressed {
                background-color: #3A80C9;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
                color: #888888;
            }
        """)


class GradientHeader(QLabel):
    """渐变标题头"""

    def __init__(self, text: str, parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.setFont(QFont("Microsoft YaHei UI", 18, QFont.Bold))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                color: #2C3E50;
                padding: 20px;
            }
        """)
        self.setFixedHeight(80)

    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter, QLinearGradient
        painter = QPainter(self)
        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0, QColor("#4A90D9"))
        gradient.setColorAt(1, QColor("#67B8F7"))
        painter.fillRect(self.rect(), gradient)

        painter.setPen(QColor("#FFFFFF"))
        painter.setFont(self.font())
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text())


class SettingsDialog(QDialog):
    """AI设置对话框"""

    def __init__(self, config_manager: ConfigManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.ai_manager = AIManager(config_manager)
        self.setup_ui()

    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("AI设置")
        self.setMinimumWidth(500)

        layout = QVBoxLayout()

        title_label = QLabel("AI提供商配置")
        title_label.setFont(QFont("Microsoft YaHei UI", 14, QFont.Bold))
        title_label.setStyleSheet("color: #2C3E50; padding: 10px 0;")
        layout.addWidget(title_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        provider_group = QGroupBox("默认提供商")
        provider_group.setFont(QFont("Microsoft YaHei UI", 11, QFont.Bold))
        provider_layout = QFormLayout()

        self.provider_combo = QComboBox()
        available_providers = self.ai_manager.get_available_providers()
        for provider_id in available_providers:
            provider_config = self.config_manager.get_config(f"ai.providers.{provider_id}")
            provider_name = provider_config.get("name", provider_id) if provider_config else provider_id
            self.provider_combo.addItem(provider_name, provider_id)

        default_provider = self.config_manager.get_config("ai.default_provider")
        if default_provider in available_providers:
            index = self.provider_combo.findData(default_provider)
            if index >= 0:
                self.provider_combo.setCurrentIndex(index)

        provider_layout.addRow("选择默认提供商:", self.provider_combo)
        provider_group.setLayout(provider_layout)
        scroll_layout.addWidget(provider_group)

        self.config_widgets = {}

        for provider_id in available_providers:
            provider_group = QGroupBox(f"{provider_id.upper()} 配置")
            provider_group.setFont(QFont("Microsoft YaHei UI", 11, QFont.Bold))
            provider_layout = QFormLayout()

            provider_config = self.config_manager.get_config(f"ai.providers.{provider_id}")
            if not provider_config:
                continue

            api_key_edit = QLineEdit()
            api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
            api_key_edit.setText(provider_config.get("api_key", ""))
            provider_layout.addRow("API密钥:", api_key_edit)

            base_url_edit = QLineEdit()
            base_url_edit.setText(provider_config.get("base_url", ""))
            provider_layout.addRow("API地址:", base_url_edit)

            model_edit = QLineEdit()
            model_edit.setText(provider_config.get("model", ""))
            provider_layout.addRow("模型名称:", model_edit)

            temp_edit = QLineEdit()
            temp_edit.setText(str(provider_config.get("temperature", 0.7)))
            provider_layout.addRow("温度 (0-2):", temp_edit)

            max_tokens_edit = QLineEdit()
            max_tokens_edit.setText(str(provider_config.get("max_tokens", 2000)))
            provider_layout.addRow("最大Token数:", max_tokens_edit)

            stream_check = QCheckBox()
            stream_check.setChecked(provider_config.get("stream", True))
            provider_layout.addRow("启用流式输出:", stream_check)

            provider_group.setLayout(provider_layout)
            scroll_layout.addWidget(provider_group)

            self.config_widgets[provider_id] = {
                "api_key": api_key_edit,
                "base_url": base_url_edit,
                "model": model_edit,
                "temperature": temp_edit,
                "max_tokens": max_tokens_edit,
                "stream": stream_check
            }

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        button_layout = QHBoxLayout()

        save_btn = ModernButton("保存设置")
        save_btn.clicked.connect(self.save_settings)
        button_layout.addWidget(save_btn)

        cancel_btn = ModernButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def save_settings(self):
        """保存设置"""
        try:
            default_provider = self.provider_combo.currentData()
            if default_provider:
                self.config_manager.set_config("ai.default_provider", default_provider)

            for provider_id, widgets in self.config_widgets.items():
                config_updates = {
                    "api_key": widgets["api_key"].text(),
                    "base_url": widgets["base_url"].text(),
                    "model": widgets["model"].text(),
                    "temperature": float(widgets["temperature"].text() or "0.7"),
                    "max_tokens": int(widgets["max_tokens"].text() or "2000"),
                    "stream": widgets["stream"].isChecked()
                }

                self.ai_manager.update_provider_config(provider_id, config_updates)

            QMessageBox.information(self, "成功", "设置已保存！")
            self.accept()

        except ValueError as e:
            QMessageBox.warning(self, "输入错误", f"请输入有效的数值: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存设置失败: {str(e)}")
            logger.error(f"保存设置失败: {str(e)}")


class AIChatWindow(QWidget):  # AI聊天主窗口
    """AI聊天主窗口"""

    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config_manager = config_manager
        self.ai_manager = AIManager(config_manager)
        self.history_manager = ChatHistoryManager(self.config_manager, max_history=50)
        self.current_response = ""
        self.is_streaming = True
        self.chat_thread: Optional[AIChatThread] = None

        self.setup_ui()
        self.setup_logging()
        # 延迟加载历史，避免在窗口创建时阻塞主线程
        QTimer.singleShot(0, self.load_history_deferred)

    def setup_logging(self):
        """设置日志"""
        if not logging.getLogger().handlers:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )

    def setup_ui(self):
        """设置UI界面"""
        self.setWindowTitle("AI智能对话")
        self.setGeometry(200, 200, 800, 600)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        header = GradientHeader("AI智能对话助手")
        main_layout.addWidget(header)

        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel)

        chat_display_group = QGroupBox("对话记录")
        chat_display_group.setFont(QFont("Microsoft YaHei UI", 11, QFont.Bold))
        chat_display_layout = QVBoxLayout()

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setFont(QFont("Microsoft YaHei UI", 11))
        # 增大初始对话记录框高度
        self.chat_display.setMinimumHeight(420)
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 2px solid #E0E0E0;
                border-radius: 8px;
                padding: 15px;
                line-height: 1.6;
            }
        """)
        chat_display_layout.addWidget(self.chat_display)

        # 尝试加载历史（优先 latest），如果存在则渲染；否则显示欢迎信息
        try:
            loaded = self.history_manager.load_from_file()
            if loaded and self.history_manager.get_history():
                for msg in self.history_manager.get_history():
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    # 直接传递历史中的 role，由 append_message 做识别和渲染
                    self.append_message(role, content)
            else:
                self.add_welcome_message()
        except Exception:
            self.add_welcome_message()

        chat_display_group.setLayout(chat_display_layout)
        main_layout.addWidget(chat_display_group, 1)

        input_group = QGroupBox("输入消息")
        input_group.setFont(QFont("Microsoft YaHei UI", 11, QFont.Bold))
        input_layout = QVBoxLayout()

        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("输入您的问题，按Enter发送...")
        self.message_input.setFont(QFont("Microsoft YaHei UI", 11))
        self.message_input.setMinimumHeight(45)
        self.message_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #4A90D9;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #5BA0E9;
            }
        """)
        self.message_input.returnPressed.connect(self.send_message)
        input_layout.addWidget(self.message_input)

        button_layout = QHBoxLayout()

        self.send_btn = ModernButton("发送消息")
        self.send_btn.clicked.connect(self.send_message)
        button_layout.addWidget(self.send_btn)

        clear_btn = ModernButton("清空对话")
        clear_btn.clicked.connect(self.clear_conversation)
        button_layout.addWidget(clear_btn)

        input_layout.addLayout(button_layout)
        input_group.setLayout(input_layout)
        main_layout.addWidget(input_group)

        self.status_label = QLabel("就绪")
        self.status_label.setFont(QFont("Microsoft YaHei UI", 9))
        self.status_label.setStyleSheet("color: #7F8C8D; padding: 5px;")
        main_layout.addWidget(self.status_label)

        self.setLayout(main_layout)

        self.setStyleSheet("""
            QGroupBox {
                border: 2px solid #4A90D9;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #2C3E50;
            }
        """)

    def create_control_panel(self) -> QFrame:
        """创建控制面板"""
        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        panel.setStyleSheet("""
            QFrame {
                background-color: #F8F9FA;
                border-radius: 8px;
                padding: 15px;
            }
        """)

        layout = QHBoxLayout()

        provider_label = QLabel("AI提供商:")
        provider_label.setFont(QFont("Microsoft YaHei UI", 10))
        layout.addWidget(provider_label)

        self.provider_combo = QComboBox()
        self.provider_combo.setFont(QFont("Microsoft YaHei UI", 10))
        self.provider_combo.setMinimumWidth(150)

        available_providers = self.ai_manager.get_available_providers()
        for provider_id in available_providers:
            provider_config = self.config_manager.get_config(f"ai.providers.{provider_id}")
            provider_name = provider_config.get("name", provider_id) if provider_config else provider_id
            self.provider_combo.addItem(provider_name, provider_id)

        default_provider = self.config_manager.get_config("ai.default_provider")
        if default_provider in available_providers:
            index = self.provider_combo.findData(default_provider)
            if index >= 0:
                self.provider_combo.setCurrentIndex(index)

        layout.addWidget(self.provider_combo)

        self.stream_check = QCheckBox("流式输出")
        self.stream_check.setFont(QFont("Microsoft YaHei UI", 10))
        self.stream_check.setChecked(True)
        layout.addWidget(self.stream_check)

        settings_btn = ModernButton("设置")
        settings_btn.setFixedWidth(80)
        settings_btn.clicked.connect(self.open_settings)
        layout.addWidget(settings_btn)

        layout.addStretch()
        panel.setLayout(layout)

        return panel

    def add_welcome_message(self):
        """添加欢迎消息"""
        welcome_msg = """
        <div style='color: #2C3E50; line-height: 1.6;'>
            <h3 style='color: #4A90D9;'>欢迎使用RAILGUN AI智能对话</h3>
            <p>我可以帮助您解答问题，提供建议、进行对话等。</p>
            <p><strong>使用前请确保：</strong></p>
            <ul>
                <li>已配置正确的AI提供商和API密钥</li>
                <li>网络连接正常</li>
                <li>如需更改设置，请点击右上角的"设置"按钮</li>
            </ul>
            <p>现在，请输入您的问题开始对话吧！</p>
        </div>
        """
        self.chat_display.setHtml(welcome_msg)

    def append_message(self, sender: str, message: str, is_html: bool = False):
        """添加消息到聊天显示"""
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        if not is_html:
            app_instance = QApplication.instance()
            timestamp = ""
            if app_instance:
                time_prop = app_instance.property("current_time")
                if time_prop:
                    timestamp = f" [{time_prop}]"

            role = sender.lower() if isinstance(sender, str) else "user"
            # 识别角色：包含 'assistant' 或等于 'ai' 的视为 AI；否则视为用户
            is_ai = (role == "ai") or ("assistant" in role)

            if is_ai:
                formatted_message = f"""
                <div style='margin: 10px 0;'>
                    <div style='color: #4A90D9; font-weight: bold;'>AI助手{timestamp}</div>
                    <div style='background-color: #F0F7FF; border-radius: 8px; padding: 12px; margin: 5px 0 15px 0; line-height: 1.6;'>
                        {message}
                    </div>
                </div>
                """
            else:
                formatted_message = f"""
                <div style='margin: 10px 0; text-align: right;'>
                    <div style='color: #27AE60; font-weight: bold;'>您{timestamp}</div>
                    <div style='background-color: #E8F5E9; border-radius: 8px; padding: 12px; margin: 5px 0 15px 0; line-height: 1.6; display: inline-block; max-width: 80%;'>
                        {message}
                    </div>
                </div>
                """
        else:
            formatted_message = message

        cursor.insertHtml(formatted_message)
        cursor.insertHtml("<br>")
        self.chat_display.ensureCursorVisible()

    def append_chunk(self, chunk: str):
        """添加流式输出块"""
        # 在文档末尾插入流式块头（仅第一次）并确保光标在末尾
        if not getattr(self, '_streaming_open', False):
            cursor = self.chat_display.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertHtml("""
            <div style='margin: 10px 0;'>
                <div style='color: #4A90D9; font-weight: bold;'>AI助手</div>
                <div style='background-color: #F0F7FF; border-radius: 8px; padding: 12px; margin: 5px 0 15px 0; line-height: 1.6;'>
            """)
            # 将编辑器的光标移动到末尾，确保可见性随内容增长
            self.chat_display.setTextCursor(cursor)
            self._streaming_open = True

        # 每次追加都在文档末尾插入文本并将光标设置到末尾，使滚动条跟随
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(chunk)
        self.chat_display.setTextCursor(cursor)
        self.current_response += chunk
        self.chat_display.ensureCursorVisible()

    def load_history_deferred(self):
        """在事件循环空闲时加载历史并渲染（避免阻塞界面创建）。"""
        try:
            loaded = self.history_manager.load_from_file()
            if loaded and self.history_manager.get_history():
                # 清空欢迎信息并渲染历史
                self.chat_display.clear()
                for msg in self.history_manager.get_history():
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    self.append_message(role, content)
                return
        except Exception:
            pass
        # 如果没有历史或加载失败，保留欢迎信息
        if not self.chat_display.toPlainText():
            self.add_welcome_message()

    def complete_streaming_response(self):
        """完成流式响应"""
        if getattr(self, '_streaming_open', False):
            cursor = self.chat_display.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertHtml("</div></div><br>")
            self.chat_display.setTextCursor(cursor)

            # 关闭流式标记并记录历史，立即持久化
            self._streaming_open = False
            self.history_manager.add_message("assistant", self.current_response)
            try:
                self.history_manager.save_to_file()
            except Exception:
                pass
            self.current_response = ""

    def send_message(self):
        """发送消息"""
        message = self.message_input.text().strip()
        if not message:
            return

        self.send_btn.setEnabled(False)
        self.message_input.setEnabled(False)
        self.status_label.setText("正在生成回复...")

        self.append_message("user", message)
        self.history_manager.add_message("user", message)
        try:
            # 每次发送保存最新对话
            self.history_manager.save_to_file()
        except Exception:
            pass
        self.message_input.clear()

        provider_id = self.provider_combo.currentData()
        streaming_enabled = self.stream_check.isChecked()

        self.chat_thread = AIChatThread(
            message=message,
            config_manager=self.config_manager,
            history=self.history_manager.get_history(),
            provider_id=provider_id,
            streaming=streaming_enabled
        )

        if streaming_enabled:
            self.chat_thread.reply_chunk.connect(self.append_chunk)
        self.chat_thread.reply_complete.connect(self.receive_reply)
        self.chat_thread.error_occurred.connect(self.receive_error)
        self.chat_thread.status_update.connect(self.status_label.setText)

        self.chat_thread.start()

    def receive_reply(self, reply: str):
        """接收完整回复"""
        if not self.stream_check.isChecked():
            self.append_message("ai", reply)
            self.history_manager.add_message("assistant", reply)
            try:
                self.history_manager.save_to_file()
            except Exception:
                pass
        else:
            self.complete_streaming_response()

        self.send_btn.setEnabled(True)
        self.message_input.setEnabled(True)
        self.message_input.setFocus()
        self.status_label.setText("就绪")

    def receive_error(self, error: str):
        """接收错误"""
        self.append_message("ai", f"<span style='color: #E74C3C;'>错误: {error}</span>", is_html=True)

        self.send_btn.setEnabled(True)
        self.message_input.setEnabled(True)
        self.message_input.setFocus()
        self.status_label.setText("错误，请重试")

        logger.error(f"AI对话错误: {error}")

    def clear_conversation(self):
        """清空对话"""
        reply = QMessageBox.question(
            self, "确认清空",
            "确定要清空当前对话记录吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.chat_display.clear()
            self.history_manager.clear_history()
            # 清空 latest 文件
            try:
                self.history_manager.save_to_file()
            except Exception:
                pass
            self.add_welcome_message()
            self.status_label.setText("对话已清空")

    def open_settings(self):
        """打开设置对话框"""
        dialog = SettingsDialog(self.config_manager, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_provider_list()

    def refresh_provider_list(self):
        """刷新提供商列表"""
        current_provider = self.provider_combo.currentData()

        self.provider_combo.clear()
        available_providers = self.ai_manager.get_available_providers()

        for provider_id in available_providers:
            provider_config = self.config_manager.get_config(f"ai.providers.{provider_id}")
            provider_name = provider_config.get("name", provider_id) if provider_config else provider_id
            self.provider_combo.addItem(provider_name, provider_id)

        if current_provider in available_providers:
            index = self.provider_combo.findData(current_provider)
            if index >= 0:
                self.provider_combo.setCurrentIndex(index)

        self.status_label.setText("提供商列表已更新")

    def closeEvent(self, event):
        """窗口关闭事件"""
        if self.chat_thread and self.chat_thread.isRunning():
            self.chat_thread.quit()
            self.chat_thread.wait()
        # 关闭前保存一次历史为归档文件
        try:
            self.history_manager.save_to_file(archive=True)
        except Exception:
            pass

        event.accept()


def main():
    """独立测试函数"""
    app = QApplication(sys.argv)
    config_manager = ConfigManager()
    window = AIChatWindow(config_manager)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
