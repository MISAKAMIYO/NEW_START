import sys
import os
import ctypes
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from settings_manager import ConfigManager
from main_window import MainWindow

class RAILGUNApplication:
    """RAILGUN 应用主入口类，负责初始化应用与主窗口"""
    
    def __init__(self):
        """
        初始化应用配置与主窗口实例
        步骤：
        1. 初始化QApplication
        2. 加载配置文件
        3. 创建主窗口并显示
        """
        self.app = QApplication(sys.argv)
        self.config = ConfigManager()  # 加载配置管理实例
        self.main_window = MainWindow(self.config)  # 传入配置初始化主窗口

    def run(self) -> int:
        """
        启动应用事件循环
        Returns:
            int: 应用退出码（0为正常退出）
        """
        self.main_window.show()
        return self.app.exec_()

def main():
    """
    程序入口函数
    处理启动异常，如配置文件缺失、依赖库未安装等
    启动时检查管理员权限，如未获取则请求提升权限
    """
    try:
        railgun_app = RAILGUNApplication()
        sys.exit(railgun_app.run())
    except ImportError as e:
        error_msg = f"导入模块失败：{e}\n\n请检查依赖是否已安装：\npip install -r requirements.txt"
        print(f"[错误] {error_msg}")
        import traceback
        traceback.print_exc()
        try:
            QMessageBox.critical(None, "导入错误", error_msg)
        except:
            pass
        sys.exit(1)
    except Exception as e:
        error_msg = f"应用启动失败：{e}"
        print(f"[错误] {error_msg}")
        import traceback
        traceback.print_exc()
        error_details = traceback.format_exc()
        try:
            from PyQt5.QtWidgets import QTextEdit, QDialog, QVBoxLayout
            dialog = QDialog()
            dialog.setWindowTitle("错误详情")
            dialog.setMinimumSize(600, 400)
            layout = QVBoxLayout()
            text_edit = QTextEdit()
            text_edit.setPlainText(error_details)
            text_edit.setReadOnly(True)
            layout.addWidget(text_edit)
            dialog.setLayout(layout)
            dialog.exec_()
        except:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()