"""
格式转换工具模块
使用FFmpeg实现多种格式间的文件转换
"""

import os
import sys
import subprocess
import logging
from typing import List, Optional

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QComboBox,
    QFileDialog, QProgressBar, QMessageBox, QGroupBox, QCheckBox, QFormLayout,
    QListWidget, QSpinBox
)
from PyQt5.QtCore import Qt, QProcess, pyqtSignal, QThread
from PyQt5.QtGui import QFont

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from settings_manager import ConfigManager

logger = logging.getLogger(__name__)


class ConvertWorker(QThread):
    """转换工作线程"""
    
    # 信号定义
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, ffmpeg_path: str, input_file: str, output_file: str, extra_args: List[str] = None):
        super().__init__()
        self.ffmpeg_path = ffmpeg_path
        self.input_file = input_file
        self.output_file = output_file
        self.extra_args = extra_args or []
        self.process = None
    
    def run(self):
        """执行转换"""
        try:
            # 构建FFmpeg命令
            cmd = [
                self.ffmpeg_path,
                "-y",  # 覆盖现有文件
                "-i", self.input_file,
                *self.extra_args,
                self.output_file
            ]
            
            logger.info(f"执行转换命令: {' '.join(cmd)}")
            self.progress.emit("开始转换...")
            
            # 执行命令
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            self.process = process
            
            # 读取输出
            for line in process.stdout:
                if line:
                    self.progress.emit(line.strip())
            
            # 等待完成
            process.wait()
            
            if process.returncode == 0:
                self.finished.emit(True, "转换成功！")
                logger.info("转换成功")
            else:
                self.finished.emit(False, f"转换失败，返回码: {process.returncode}")
                logger.error(f"转换失败，返回码: {process.returncode}")
                
        except Exception as e:
            error_msg = f"执行转换时出错: {str(e)}"
            self.finished.emit(False, error_msg)
            logger.error(error_msg)
        finally:
            if self.process:
                try:
                    self.process.terminate()
                except:
                    pass
    
    def stop(self):
        """停止转换"""
        if self.process:
            try:
                self.process.terminate()
            except:
                pass


class ConvertToolsWindow(QWidget):
    """格式转换工具窗口"""
    
    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config_manager = config_manager
        self.worker = None
        # 批量/队列管理
        self.queue = []  # list of input file paths
        self.active_workers = []  # running ConvertWorker instances
        self.max_parallel = 1
        self.setup_ui()
        self.setup_paths()
    
    def setup_paths(self):
        """设置路径"""
        # 获取FFmpeg路径
        self.ffmpeg_path = os.path.join(
            self.config_manager.get_config("paths.data"),
            "ffmpeg.exe"
        )
        
        if not os.path.exists(self.ffmpeg_path):
            # 尝试其他可能的位置
            possible_paths = [
                os.path.join(os.path.dirname(__file__), "ffmpeg.exe"),
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "ffmpeg.exe"),
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "ffmpeg.exe"),
                os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "Data", "ffmpeg.exe")
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    self.ffmpeg_path = path
                    break
            else:
                logger.error("未找到FFmpeg可执行文件")
        
        logger.info(f"使用FFmpeg: {self.ffmpeg_path}")
    
    def setup_ui(self):
        """设置UI界面"""
        self.setWindowTitle("🎯 格式转换工具")
        self.setGeometry(200, 200, 600, 500)
        
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # 标题
        title_label = QLabel("多媒体格式转换")
        title_label.setFont(QFont("Microsoft YaHei UI", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #2C3E50;")
        main_layout.addWidget(title_label)
        
        # 输入文件组
        input_group = QGroupBox("输入文件")
        input_group.setFont(QFont("Microsoft YaHei UI", 11, QFont.Bold))
        input_layout = QVBoxLayout()
        
        # 文件选择
        file_layout = QHBoxLayout()
        self.input_file_edit = QLineEdit()
        self.input_file_edit.setPlaceholderText("请选择要转换的文件...")
        self.input_file_edit.setFont(QFont("Microsoft YaHei UI", 10))
        file_layout.addWidget(self.input_file_edit, 1)
        
        browse_btn = QPushButton("浏览")
        browse_btn.setFont(QFont("Microsoft YaHei UI", 10))
        browse_btn.clicked.connect(self.browse_input_file)
        file_layout.addWidget(browse_btn)
        # 批量添加按钮
        add_files_btn = QPushButton("添加文件到队列")
        add_files_btn.setFont(QFont("Microsoft YaHei UI", 10))
        add_files_btn.clicked.connect(self.browse_input_files)
        file_layout.addWidget(add_files_btn)
        
        input_layout.addLayout(file_layout)
        # 队列显示与管理
        self.file_list_widget = QListWidget()
        self.file_list_widget.setFixedHeight(120)
        input_layout.addWidget(self.file_list_widget)

        file_ops_layout = QHBoxLayout()
        remove_btn = QPushButton("移除选中")
        remove_btn.setFont(QFont("Microsoft YaHei UI", 10))
        remove_btn.clicked.connect(self.remove_selected_from_queue)
        file_ops_layout.addWidget(remove_btn)

        clear_btn = QPushButton("清空队列")
        clear_btn.setFont(QFont("Microsoft YaHei UI", 10))
        clear_btn.clicked.connect(self.clear_queue)
        file_ops_layout.addWidget(clear_btn)

        input_layout.addLayout(file_ops_layout)
        input_group.setLayout(input_layout)
        main_layout.addWidget(input_group)
        
        # 输出设置组
        output_group = QGroupBox("输出设置")
        output_group.setFont(QFont("Microsoft YaHei UI", 11, QFont.Bold))
        output_layout = QVBoxLayout()
        
        # 输出格式选择
        format_layout = QHBoxLayout()
        format_label = QLabel("输出格式:")
        format_label.setFont(QFont("Microsoft YaHei UI", 10))
        format_layout.addWidget(format_label)
        
        self.output_format = QComboBox()
        self.output_format.setFont(QFont("Microsoft YaHei UI", 10))
        self.output_format.addItems([
            "mp3", "wav", "aac", "flac", "ogg",  # 音频格式
            "mp4", "avi", "mov", "wmv", "mkv",  # 视频格式
            "jpg", "png", "gif"  # 图像格式
        ])
        format_layout.addWidget(self.output_format, 1)
        output_layout.addLayout(format_layout)
        
        # 输出目录选择
        output_dir_layout = QHBoxLayout()
        output_dir_label = QLabel("输出目录:")
        output_dir_label.setFont(QFont("Microsoft YaHei UI", 10))
        output_dir_layout.addWidget(output_dir_label)
        
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("请选择输出目录...")
        self.output_dir_edit.setFont(QFont("Microsoft YaHei UI", 10))
        output_dir_layout.addWidget(self.output_dir_edit, 1)
        
        output_dir_btn = QPushButton("浏览")
        output_dir_btn.setFont(QFont("Microsoft YaHei UI", 10))
        output_dir_btn.clicked.connect(self.browse_output_dir)
        output_dir_layout.addWidget(output_dir_btn)
        output_layout.addLayout(output_dir_layout)
        
        # 输出文件名
        output_name_layout = QHBoxLayout()
        output_name_label = QLabel("输出文件名:")
        output_name_label.setFont(QFont("Microsoft YaHei UI", 10))
        output_name_layout.addWidget(output_name_label)
        
        self.output_name_edit = QLineEdit()
        self.output_name_edit.setPlaceholderText("留空使用默认名称...")
        self.output_name_edit.setFont(QFont("Microsoft YaHei UI", 10))
        output_name_layout.addWidget(self.output_name_edit, 1)
        output_layout.addLayout(output_name_layout)
        
        # 覆盖选项
        overwrite_layout = QHBoxLayout()
        self.overwrite_check = QCheckBox("覆盖现有文件")
        self.overwrite_check.setFont(QFont("Microsoft YaHei UI", 10))
        self.overwrite_check.setChecked(True)
        overwrite_layout.addWidget(self.overwrite_check)
        output_layout.addLayout(overwrite_layout)
        
        output_group.setLayout(output_layout)
        main_layout.addWidget(output_group)
        
        # 高级选项组
        advanced_group = QGroupBox("高级选项")
        advanced_group.setFont(QFont("Microsoft YaHei UI", 11, QFont.Bold))
        advanced_layout = QFormLayout()
        
        # 视频质量
        self.video_quality_combo = QComboBox()
        self.video_quality_combo.setFont(QFont("Microsoft YaHei UI", 10))
        self.video_quality_combo.addItems(["低质量", "中质量", "高质量", "原始质量"])
        self.video_quality_combo.setCurrentIndex(1)
        advanced_layout.addRow("视频质量:", self.video_quality_combo)
        
        # 音频质量
        self.audio_quality_combo = QComboBox()
        self.audio_quality_combo.setFont(QFont("Microsoft YaHei UI", 10))
        self.audio_quality_combo.addItems(["低质量", "中质量", "高质量", "原始质量"])
        self.audio_quality_combo.setCurrentIndex(1)
        advanced_layout.addRow("音频质量:", self.audio_quality_combo)
        # 并行转换选项
        self.parallel_check = QCheckBox("并行转换")
        self.parallel_check.setFont(QFont("Microsoft YaHei UI", 10))
        self.parallel_spin = QSpinBox()
        self.parallel_spin.setMinimum(1)
        self.parallel_spin.setMaximum(8)
        self.parallel_spin.setValue(1)
        parallel_layout = QHBoxLayout()
        parallel_layout.addWidget(self.parallel_check)
        parallel_layout.addWidget(QLabel("并发数:"))
        parallel_layout.addWidget(self.parallel_spin)
        advanced_layout.addRow("并行选项:", parallel_layout)
        
        advanced_group.setLayout(advanced_layout)
        main_layout.addWidget(advanced_group)
        
        # 进度显示
        self.progress_label = QLabel("准备就绪")
        self.progress_label.setFont(QFont("Microsoft YaHei UI", 10))
        self.progress_label.setStyleSheet("color: #7F8C8D;")
        main_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # 按钮组
        button_layout = QHBoxLayout()
        
        self.convert_btn = QPushButton("开始转换")
        self.convert_btn.setFont(QFont("Microsoft YaHei UI", 11, QFont.Bold))
        self.convert_btn.setMinimumHeight(40)
        self.convert_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A90D9;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
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
        self.convert_btn.clicked.connect(self.start_conversion)
        button_layout.addWidget(self.convert_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setFont(QFont("Microsoft YaHei UI", 11))
        self.cancel_btn.setMinimumHeight(40)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #E85C4C;
            }
            QPushButton:pressed {
                background-color: #D73C2C;
            }
        """)
        self.cancel_btn.clicked.connect(self.cancel_conversion)
        self.cancel_btn.setEnabled(False)
        button_layout.addWidget(self.cancel_btn)
        
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        
        # 应用整体样式
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
            QLineEdit {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 6px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #4A90D9;
            }
            QComboBox {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 6px;
                font-size: 14px;
            }
            QProgressBar {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background-color: #F8F9FA;
            }
            QProgressBar::chunk {
                background-color: #4A90D9;
                border-radius: 4px;
            }
        """)
    
    def browse_input_file(self):
        """浏览输入文件"""
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilters([
            "所有支持的文件 (*.mp4 *.avi *.mov *.wmv *.mkv *.mp3 *.wav *.aac *.flac *.ogg *.jpg *.jpeg *.png *.gif)",
            "视频文件 (*.mp4 *.avi *.mov *.wmv *.mkv)",
            "音频文件 (*.mp3 *.wav *.aac *.flac *.ogg)",
            "图像文件 (*.jpg *.jpeg *.png *.gif)",
            "所有文件 (*.*)"
        ])
        
        if file_dialog.exec() == QFileDialog.DialogCode.Accepted:
            file_path = file_dialog.selectedFiles()[0]
            self.input_file_edit.setText(file_path)
            
            # 自动填充输出文件名
            if not self.output_name_edit.text():
                base_name = os.path.basename(file_path)
                name_without_ext = os.path.splitext(base_name)[0]
                self.output_name_edit.setText(name_without_ext)

    def browse_input_files(self):
        """浏览多文件并添加到队列"""
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        file_dialog.setNameFilters([
            "所有支持的文件 (*.mp4 *.avi *.mov *.wmv *.mkv *.mp3 *.wav *.aac *.flac *.ogg *.jpg *.jpeg *.png *.gif)",
            "视频文件 (*.mp4 *.avi *.mov *.wmv *.mkv)",
            "音频文件 (*.mp3 *.wav *.aac *.flac *.ogg)",
            "图像文件 (*.jpg *.jpeg *.png *.gif)",
            "所有文件 (*.*)"
        ])
        if file_dialog.exec() == QFileDialog.DialogCode.Accepted:
            files = file_dialog.selectedFiles()
            self.add_files_to_queue(files)

    def add_files_to_queue(self, files: List[str]):
        """将多个文件路径加入队列并显示"""
        for f in files:
            if f not in self.queue:
                self.queue.append(f)
                self.file_list_widget.addItem(f)
    
    def browse_output_dir(self):
        """浏览输出目录"""
        dir_dialog = QFileDialog()
        dir_dialog.setFileMode(QFileDialog.FileMode.Directory)
        dir_dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        
        if dir_dialog.exec() == QFileDialog.DialogCode.Accepted:
            dir_path = dir_dialog.selectedFiles()[0]
            self.output_dir_edit.setText(dir_path)
    
    def get_output_file_path(self) -> str:
        """获取输出文件路径"""
        input_file = self.input_file_edit.text()
        if not input_file:
            raise ValueError("请选择输入文件")
        
        output_dir = self.output_dir_edit.text()
        if not output_dir:
            # 使用输入文件所在目录
            output_dir = os.path.dirname(input_file)
        
        # 获取输出文件名
        output_name = self.output_name_edit.text()
        if not output_name:
            # 使用输入文件名（不含扩展名）
            base_name = os.path.basename(input_file)
            output_name = os.path.splitext(base_name)[0]
        
        # 获取输出格式
        output_format = self.output_format.currentText()
        
        # 构建输出文件路径
        output_file = os.path.join(output_dir, f"{output_name}.{output_format}")
        
        # 处理覆盖情况
        if not self.overwrite_check.isChecked() and os.path.exists(output_file):
            # 添加数字后缀
            counter = 1
            while True:
                new_output_file = os.path.join(output_dir, f"{output_name}_{counter}.{output_format}")
                if not os.path.exists(new_output_file):
                    output_file = new_output_file
                    break
                counter += 1
        
        return output_file

    def get_output_file_for(self, input_file: str) -> str:
        """为指定输入文件计算输出文件路径（遵循覆盖策略与输出目录/格式）"""
        output_dir = self.output_dir_edit.text() or os.path.dirname(input_file)
        base_name = os.path.splitext(os.path.basename(input_file))[0]
        output_name = self.output_name_edit.text() or base_name
        output_format = self.output_format.currentText()

        output_file = os.path.join(output_dir, f"{output_name}.{output_format}")

        if not self.overwrite_check.isChecked() and os.path.exists(output_file):
            counter = 1
            while True:
                new_output_file = os.path.join(output_dir, f"{output_name}_{counter}.{output_format}")
                if not os.path.exists(new_output_file):
                    output_file = new_output_file
                    break
                counter += 1

        return output_file
    
    def get_conversion_args(self, input_file: str, output_file: str) -> List[str]:
        """获取转换参数"""
        args = []
        
        # 根据输出格式添加特定参数
        output_format = self.output_format.currentText()
        
        # 视频质量设置
        if output_format in ["mp4", "avi", "mov", "wmv", "mkv"]:
            quality = self.video_quality_combo.currentIndex()
            if quality == 0:  # 低质量
                args.extend(["-crf", "30", "-preset", "veryfast"])
            elif quality == 1:  # 中质量
                args.extend(["-crf", "23", "-preset", "medium"])
            elif quality == 2:  # 高质量
                args.extend(["-crf", "18", "-preset", "slow"])
            # 原始质量：使用默认参数
        
        # 音频质量设置
        if output_format in ["mp3", "wav", "aac", "flac", "ogg"]:
            quality = self.audio_quality_combo.currentIndex()
            if quality == 0:  # 低质量
                if output_format == "mp3":
                    args.extend(["-b:a", "128k"])
            elif quality == 1:  # 中质量
                if output_format == "mp3":
                    args.extend(["-b:a", "192k"])
            elif quality == 2:  # 高质量
                if output_format == "mp3":
                    args.extend(["-b:a", "320k"])
            # 原始质量：使用默认参数
        
        return args
    
    def start_conversion(self):
        """开始转换"""
        try:
            # 检查输入文件
            input_file = self.input_file_edit.text()
            if not input_file:
                QMessageBox.warning(self, "错误", "请选择要转换的文件")
                return
            
            if not os.path.exists(input_file):
                QMessageBox.warning(self, "错误", "选择的文件不存在")
                return
            
            # 检查FFmpeg
            if not os.path.exists(self.ffmpeg_path):
                QMessageBox.critical(self, "错误", f"未找到FFmpeg可执行文件: {self.ffmpeg_path}")
                return
            
            # 获取输出文件路径
            # 如果队列中有文件，执行批量转换；否则执行单文件转换
            if self.queue:
                # 并行设置
                parallel = self.parallel_check.isChecked()
                self.max_parallel = max(1, int(self.parallel_spin.value())) if parallel else 1
                # 禁用按钮
                self.convert_btn.setEnabled(False)
                self.cancel_btn.setEnabled(True)
                self.progress_label.setText("正在开始批量转换...")
                self.progress_bar.setVisible(True)
                self.progress_bar.setValue(0)
                # 启动队列
                self.start_batch_conversion()
            else:
                # 单文件转换逻辑保持原样
                output_file = self.get_output_file_path()
                extra_args = self.get_conversion_args(input_file, output_file)
                self.worker = ConvertWorker(
                    ffmpeg_path=self.ffmpeg_path,
                    input_file=input_file,
                    output_file=output_file,
                    extra_args=extra_args
                )
                self.worker.progress.connect(self.update_progress)
                self.worker.finished.connect(self.conversion_finished)
                self.progress_label.setText("正在转换...")
                self.progress_bar.setVisible(True)
                self.progress_bar.setValue(0)
                self.convert_btn.setEnabled(False)
                self.cancel_btn.setEnabled(True)
                self.worker.start()
                logger.info(f"开始转换: {input_file} -> {output_file}")
            
        except Exception as e:
            error_msg = f"准备转换时出错: {str(e)}"
            QMessageBox.critical(self, "错误", error_msg)
            logger.error(error_msg)
    
    def cancel_conversion(self):
        """取消转换"""
        # 停止所有活动的 worker
        self.stop_all_workers()
        self.progress_label.setText("转换已取消")
        self.progress_bar.setVisible(False)
        self.convert_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

    def stop_all_workers(self):
        """停止所有正在执行的转换任务"""
        for w in list(self.active_workers):
            try:
                w.stop()
                w.wait()
            except Exception:
                pass
        self.active_workers.clear()
    
    def update_progress(self, message: str):
        """更新进度"""
        self.progress_label.setText(message)
        # 简单的进度更新（实际应该解析FFmpeg输出）
        if hasattr(self, 'progress_value'):
            self.progress_value = min(self.progress_value + 5, 95)
        else:
            self.progress_value = 0
        self.progress_bar.setValue(self.progress_value)

    def start_batch_conversion(self):
        """基于队列启动批量转换（顺序或并行，受 self.max_parallel 控制）"""
        # 如果不并行，max_parallel == 1，依次启动
        # 启动初始的一批任务
        to_start = min(self.max_parallel, len(self.queue))
        for _ in range(to_start):
            self._start_next_in_queue()

    def _start_next_in_queue(self):
        if not self.queue:
            # 全部完成
            if not self.active_workers:
                self.progress_bar.setValue(100)
                self.progress_label.setText("批量转换完成")
                QTimer.singleShot(1000, lambda: self.progress_bar.setVisible(False))
                self.convert_btn.setEnabled(True)
                self.cancel_btn.setEnabled(False)
            return

        input_file = self.queue.pop(0)
        # 从队列 UI 中移除首项
        if self.file_list_widget.count() > 0:
            self.file_list_widget.takeItem(0)

        output_file = self.get_output_file_for(input_file)
        extra_args = self.get_conversion_args(input_file, output_file)

        worker = ConvertWorker(
            ffmpeg_path=self.ffmpeg_path,
            input_file=input_file,
            output_file=output_file,
            extra_args=extra_args
        )
        # 连接信号
        worker.progress.connect(lambda msg, f=input_file: self.progress_label.setText(f"{os.path.basename(f)}: {msg}"))
        worker.finished.connect(lambda success, msg, w=worker: self.worker_finished(w, success, msg))
        self.active_workers.append(worker)
        worker.start()

    def worker_finished(self, worker: ConvertWorker, success: bool, message: str):
        try:
            if worker in self.active_workers:
                self.active_workers.remove(worker)
        except Exception:
            pass

        # 更新进度条（简单策略：每完成一个增加一定比例）
        total = 1 + len(self.queue) + len(self.active_workers)
        done = 0
        # 估算已完成数量
        done = 0
        if total > 0:
            # 计算完成比率
            completed = 1  # 当前完成的
            processed = completed
            progress_val = min(100, int(100 * processed / (processed + len(self.queue) + len(self.active_workers))))
            self.progress_bar.setValue(progress_val)

        # 记录日志并显示消息
        logger.info(f"文件转换完成: {worker.input_file} -> {worker.output_file} : {message}")

        # 如果还有队列且并行允许，继续启动下一个
        if self.parallel_check.isChecked():
            # 并行：保持活跃 worker 数不超过 max_parallel
            while len(self.active_workers) < self.max_parallel and self.queue:
                self._start_next_in_queue()
        else:
            # 顺序：启动下一个
            if self.queue:
                self._start_next_in_queue()
            else:
                # 队列空且无活跃任务 -> 完成
                if not self.active_workers:
                    self.progress_bar.setValue(100)
                    self.progress_label.setText("批量转换完成")
                    QTimer.singleShot(1000, lambda: self.progress_bar.setVisible(False))
                    self.convert_btn.setEnabled(True)
                    self.cancel_btn.setEnabled(False)

    def remove_selected_from_queue(self):
        items = self.file_list_widget.selectedItems()
        for it in items:
            text = it.text()
            try:
                self.queue.remove(text)
            except ValueError:
                pass
            self.file_list_widget.takeItem(self.file_list_widget.row(it))

    def clear_queue(self):
        self.queue.clear()
        self.file_list_widget.clear()
    
    def conversion_finished(self, success: bool, message: str):
        """转换完成"""
        self.worker = None
        self.progress_bar.setValue(100 if success else 0)
        
        if success:
            QMessageBox.information(self, "成功", message)
            self.progress_label.setText("转换成功")
        else:
            QMessageBox.critical(self, "错误", message)
            self.progress_label.setText("转换失败")
        
        # 恢复UI
        QTimer.singleShot(1000, lambda: self.progress_bar.setVisible(False))
        self.convert_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
    
    def closeEvent(self, event):
        """关闭事件"""
        if self.worker:
            self.worker.stop()
            self.worker.wait()
        event.accept()


# 导入QtCore用于QTimer
from PyQt5.QtCore import QTimer


def main():
    """独立测试函数"""
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    config_manager = ConfigManager()
    window = ConvertToolsWindow(config_manager)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
