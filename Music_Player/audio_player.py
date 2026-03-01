# audio_player.py
"""
音乐播放器核心音频播放模块
负责处理音频文件的播放、控制、状态管理和播放列表功能
完全基于QMediaPlayer实现，无VLC/Pygame回退
"""

import os
import json
import re
import hashlib
import time
import logging
from pathlib import Path
import random

from PyQt5.QtCore import (
    QObject, QTimer, Qt, QUrl, pyqtSignal, QByteArray, QSettings
)
from PyQt5.QtGui import QIcon, QColor, QFont, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QMessageBox, QFileDialog, QListWidgetItem
)
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget

logger = logging.getLogger("MusicApp")


class AudioPlayer(QObject):
    """核心音频播放器类 - 完全基于QMediaPlayer"""
    
    # 信号定义
    state_changed = pyqtSignal(int)  # 播放状态改变
    position_changed = pyqtSignal(int)  # 播放位置改变
    duration_changed = pyqtSignal(int)  # 歌曲时长改变
    media_status_changed = pyqtSignal(int)  # 媒体状态改变
    volume_changed = pyqtSignal(int)  # 音量改变
    current_song_changed = pyqtSignal(dict)  # 当前歌曲改变
    playlist_updated = pyqtSignal(list)  # 播放列表更新
    error_occurred = pyqtSignal(str)  # 错误发生
    status_message_changed = pyqtSignal(str)  # 状态消息改变
    vlc_detected = pyqtSignal(bool)  # VLC检测信号（向后兼容）
    
    def __init__(self, settings=None, parent=None):
        """初始化音频播放器
        
        Args:
            settings: 设置字典，包含各种配置
            parent: 父对象
        """
        super().__init__(parent)
        
        # 初始化设置
        self.settings = settings or self._load_default_settings()
        
        # 播放器核心组件 - 仅使用QMediaPlayer
        self.media_player = QMediaPlayer()
        self.media_player.setNotifyInterval(50)  # 50ms更新间隔
        
        # 向后兼容属性（VLC相关）
        self.vlc_preferred = False  # VLC是否为首选引擎
        self.vlc_player = None  # 保持None以兼容
        
        # 播放状态
        self.current_song_path = None
        self.current_song_info = None
        self.current_play_index = -1
        
        # 播放列表
        self.playlist = []  # 存储歌曲信息字典
        self.playlist_widget = None  # 可选的UI播放列表组件
        logger.info(f"AudioPlayer.__init__: playlist_widget初始化为None")
        
        # 播放模式 (0:顺序播放, 1:随机播放, 2:单曲循环)
        self.play_mode = 0
        
        # 随机播放模式 (0:智能随机, 1:完全随机, 2:纯随机)
        self.shuffle_mode = 0
        self.shuffle_history = []
        self.max_shuffle_history = 10
        
        # 播放历史
        self.play_history = []
        self.max_history_size = 100
        
        # 错误恢复机制
        self.recovery_attempts = 0
        self.max_recovery_attempts = 3
        
        # 加载保存的设置
        self._load_player_settings()
        
        # 连接信号
        self._setup_connections()
        
        logger.info("音频播放器初始化完成（纯QMediaPlayer实现）")
        print("[播放器内核] 音频播放器初始化完成，准备就绪（纯QMediaPlayer）")
    
    def _load_default_settings(self):
        """加载默认设置"""
        return {
            "save_paths": {
                "music": os.path.join(os.path.expanduser("~"), "Music"),
                "cache": os.path.join(os.path.expanduser("~"), ".cache", "music_player"),
                "videos": os.path.join(os.path.expanduser("~"), "Videos")
            },
            "other": {
                "max_results": 20,
                "auto_play": True,
                "show_translation": True,
                "repeat_mode": "all",
                "volume": 80,
                "playback_mode": "list",
                "auto_next": True
            },
            "lyrics": {
                "show_lyrics": True,
                "auto_save": True
            }
        }
    
    def _load_player_settings(self):
        """从QSettings加载播放器设置"""
        settings = QSettings("Railgun_lover", "MusicPlayer")
        
        # 加载音量
        volume = settings.value("player/volume", 80, int)
        self.media_player.setVolume(volume)
        
        # 加载播放模式
        self.play_mode = settings.value("player/play_mode", 0, int)
        
        # 加载VLC首选项（向后兼容）
        self.vlc_preferred = settings.value("player/vlc_preferred", False, bool)
        
        # 加载最后播放的歌曲
        last_song = settings.value("player/last_song")
        if last_song and os.path.exists(last_song):
            self.current_song_path = last_song
            last_position = settings.value("player/last_position", 0, int)
            
            # 恢复播放位置
            def restore_position():
                if self.media_player.duration() > 0:
                    self.media_player.setPosition(min(last_position, self.media_player.duration()))
            
            QTimer.singleShot(500, restore_position)
    
    def save_player_settings(self):
        """保存播放器设置到QSettings"""
        settings = QSettings("Railgun_lover", "MusicPlayer")
        
        # 保存音量
        settings.setValue("player/volume", self.media_player.volume())
        
        # 保存播放模式
        settings.setValue("player/play_mode", self.play_mode)
        
        # 保存VLC首选项（向后兼容）
        settings.setValue("player/vlc_preferred", self.vlc_preferred)
        
        # 保存当前播放的歌曲和位置
        if self.current_song_path:
            settings.setValue("player/last_song", self.current_song_path)
            settings.setValue("player/last_position", self.media_player.position())
        
        settings.sync()
        logger.debug("播放器设置已保存")
    
    def _setup_connections(self):
        """设置信号连接"""
        # 连接媒体播放器信号
        self.media_player.stateChanged.connect(self._on_state_changed)
        self.media_player.positionChanged.connect(self._on_position_changed)
        self.media_player.durationChanged.connect(self._on_duration_changed)
        self.media_player.mediaStatusChanged.connect(self._on_media_status_changed)
        self.media_player.volumeChanged.connect(self._on_volume_changed)
        
        # 连接错误信号
        try:
            if hasattr(self.media_player, 'error'):
                self.media_player.error.connect(self._on_media_error)
            if hasattr(self.media_player, 'errorOccurred'):
                self.media_player.errorOccurred.connect(self._on_media_error)
        except Exception as e:
            logger.warning(f"无法连接错误信号: {e}")
    
    # =============== 基础播放控制 ===============
    
    def play_audio(self, file_path):
        """播放指定音频文件
        
        Args:
            file_path: 音频文件路径
            
        Returns:
            bool: 是否成功播放
        """
        if not file_path:
            logger.warning("播放音频: 文件路径为空")
            print("[播放器内核] 错误: 文件路径为空")
            return False
        
        if not os.path.exists(file_path):
            logger.error(f"播放音频: 文件不存在 - {file_path}")
            print(f"[播放器内核] 错误: 文件不存在 - {os.path.basename(file_path)}")
            self.error_occurred.emit(f"文件不存在: {os.path.basename(file_path)}")
            return False
        
        file_path = os.path.abspath(file_path)
        
        try:
            # 停止当前播放
            if self.media_player.state() == QMediaPlayer.PlayingState:
                self.media_player.stop()
            
            # 重置状态并设置新媒体
            self.current_song_path = file_path
            self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(file_path)))
            
            # 播放
            self.media_player.play()
            
            # 更新当前歌曲信息
            self._update_current_song_info(file_path)
            
            # 添加到播放历史
            self._add_to_play_history(file_path)
            
            logger.info(f"播放音频: {os.path.basename(file_path)}")
            print(f"[播放器内核] 正在播放: {os.path.basename(file_path)}")
            return True
            
        except Exception as e:
            logger.error(f"播放音频失败: {e}")
            print(f"[播放器内核] 播放失败: {e}")
            self.error_occurred.emit(f"播放失败: {str(e)}")
            
            # 尝试错误恢复
            if self.recovery_attempts < self.max_recovery_attempts:
                self.recovery_attempts += 1
                logger.info(f"尝试恢复播放 (第{self.recovery_attempts}次)")
                QTimer.singleShot(100, lambda: self._recover_and_retry(file_path))
            
            return False
    
    def play_file_safe(self, file_path):
        """安全播放文件（带错误处理）
        
        Args:
            file_path: 音频文件路径
        """
        try:
            if not self.play_audio(file_path):
                self.error_occurred.emit("无法播放文件，请检查格式或文件完整性")
        except Exception as e:
            logger.error(f"安全播放失败: {e}")
            self.error_occurred.emit(f"播放错误: {str(e)}")
    
    def play(self):
        """开始播放当前歌曲"""
        if self.media_player.media().isNull():
            if self.current_song_path:
                self.play_audio(self.current_song_path)
            else:
                logger.warning("播放: 没有可播放的歌曲")
        else:
            self.media_player.play()
    
    def pause(self):
        """暂停播放"""
        self.media_player.pause()
    
    def stop(self):
        """停止播放"""
        self.media_player.stop()
    
    def toggle_play_pause(self):
        """切换播放/暂停状态"""
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.pause()
        else:
            self.play()
    
    def seek(self, position):
        """跳转到指定位置
        
        Args:
            position: 位置（毫秒）
        """
        try:
            # 检查媒体是否已加载
            if self.media_player.media().isNull():
                logger.warning("跳转: 媒体未加载")
                return
            
            # 检查媒体状态
            from PyQt5.QtMultimedia import QMediaPlayer
            media_status = self.media_player.mediaStatus()
            
            # 只有在媒体已加载或缓冲完成时才允许跳转
            if media_status not in [QMediaPlayer.LoadedMedia, QMediaPlayer.BufferedMedia, QMediaPlayer.StalledMedia]:
                logger.warning(f"跳转: 媒体状态不适合跳转 (状态: {media_status})")
                # 可以尝试延迟跳转
                QTimer.singleShot(100, lambda: self._safe_seek_retry(position))
                return
            
            # 检查是否可定位
            if self.media_player.isSeekable():
                self.media_player.setPosition(position)
                logger.info(f"跳转到位置: {position}ms")
            else:
                logger.warning("跳转: 当前媒体不支持定位")
                
        except Exception as e:
            logger.error(f"跳转失败: {e}")
            # 尝试恢复
            self._safe_seek_retry(position)
    
    def seek_percentage(self, percentage):
        """按百分比跳转
        
        Args:
            percentage: 百分比 (0-100)
        """
        duration = self.media_player.duration()
        if duration > 0:
            position = int(duration * percentage / 100)
            self.seek(position)
    
    def set_volume(self, volume):
        """设置音量
        
        Args:
            volume: 音量值 (0-100)
        """
        self.media_player.setVolume(max(0, min(100, volume)))
    
    def volume_up(self, increment=5):
        """增加音量"""
        new_volume = min(100, self.media_player.volume() + increment)
        self.set_volume(new_volume)
    
    def volume_down(self, decrement=5):
        """降低音量"""
        new_volume = max(0, self.media_player.volume() - decrement)
        self.set_volume(new_volume)
    
    # =============== 播放列表管理 ===============
    
    def add_to_playlist(self, file_path, song_info=None):
        """添加歌曲到播放列表
        
        Args:
            file_path: 歌曲文件路径
            song_info: 歌曲信息字典（可选）
            
        Returns:
            bool: 是否成功添加
        """
        if not file_path or not os.path.exists(file_path):
            logger.warning(f"添加到播放列表: 文件不存在 - {file_path}")
            return False
        
        # 检查是否已在播放列表中
        for song in self.playlist:
            if song.get('path') == file_path:
                logger.info(f"添加到播放列表: 歌曲已存在 - {os.path.basename(file_path)}")
                return False
        
        # 创建歌曲信息
        if song_info is None:
            song_info = self._create_song_info_from_file(file_path)
        
        # 标准化歌曲信息到原始格式
        song_info = self._standardize_song_info(song_info)
        
        # 添加到播放列表
        self.playlist.append(song_info)
        
        # 更新UI播放列表（如果存在）
        try:
            logger.info(f"add_to_playlist: 添加到UI播放列表 - {song_info.get('title', song_info.get('name', os.path.basename(file_path)))}")
            self._add_to_ui_playlist(song_info)
        except Exception as e:
            logger.warning(f"add_to_playlist: 添加到UI播放列表失败: {e}, playlist_widget: {self.playlist_widget}")
        
        # 发送信号
        self.playlist_updated.emit(self.playlist)
        
        logger.info(f"添加到播放列表: {song_info.get('title', song_info.get('name', os.path.basename(file_path)))}")
        return True
    
    def remove_from_playlist(self, index):
        """从播放列表中移除歌曲
        
        Args:
            index: 歌曲索引
            
        Returns:
            bool: 是否成功移除
        """
        if 0 <= index < len(self.playlist):
            removed_song = self.playlist.pop(index)
            
            # 更新UI播放列表（如果存在）
            try:
                if self.playlist_widget.count() > index:
                    self.playlist_widget.takeItem(index)
            except Exception as e:
                logger.warning(f"remove_from_playlist: 从UI移除项目失败: {e}, playlist_widget: {self.playlist_widget}")
            
            # 如果移除的是当前播放的歌曲
            if index == self.current_play_index:
                self.current_play_index = -1
                self.current_song_path = None
                self.stop()
            
            # 发送信号
            self.playlist_updated.emit(self.playlist)
            
            logger.info(f"从播放列表移除: {removed_song.get('title', removed_song.get('name', '未知歌曲'))}")
            return True
        
        return False
    
    def clear_playlist(self):
        """清空播放列表"""
        logger.info(f"clear_playlist: 开始检查, playlist_widget对象: {self.playlist_widget}, id: {id(self.playlist_widget)}, bool值: {bool(self.playlist_widget)}")
        self.playlist.clear()
        
        # 清空UI播放列表（如果存在）
        try:
            self.playlist_widget.clear()
            logger.info(f"clear_playlist: 已清空UI播放列表")
        except Exception as e:
            logger.warning(f"clear_playlist: 清空UI播放列表失败: {e}, playlist_widget: {self.playlist_widget}")
        
        # 重置当前播放索引
        self.current_play_index = -1
        
        # 发送信号
        self.playlist_updated.emit(self.playlist)
        
        logger.info("播放列表已清空")
    
    def play_by_index(self, index):
        """播放指定索引的歌曲
        
        Args:
            index: 歌曲索引
            
        Returns:
            bool: 是否成功播放
        """
        if 0 <= index < len(self.playlist):
            song_info = self.playlist[index]
            file_path = song_info.get('path')
            
            if file_path and os.path.exists(file_path):
                self.current_play_index = index
                self.current_song_info = song_info
                
                # 发送当前歌曲改变信号
                self.current_song_changed.emit(song_info)
                
                return self.play_audio(file_path)
        
        return False
    
    def play_next(self):
        """播放下一首歌曲
        
        Returns:
            bool: 是否成功播放下一首
        """
        if not self.playlist:
            return False
        
        next_index = self._get_next_song_index()
        if 0 <= next_index < len(self.playlist):
            return self.play_by_index(next_index)
        
        return False
    
    def play_previous(self):
        """播放上一首歌曲
        
        Returns:
            bool: 是否成功播放上一首
        """
        if not self.playlist:
            return False
        
        prev_index = self._get_previous_song_index()
        if 0 <= prev_index < len(self.playlist):
            return self.play_by_index(prev_index)
        
        return False
    
    # =============== 播放模式管理 ===============
    
    def set_play_mode(self, mode):
        """设置播放模式
        
        Args:
            mode: 播放模式 (0:顺序, 1:随机, 2:单曲循环)
        """
        self.play_mode = max(0, min(2, mode))
        logger.info(f"播放模式设置为: {self._get_play_mode_name()}")
    
    def cycle_play_mode(self):
        """循环切换播放模式"""
        self.play_mode = (self.play_mode + 1) % 3
        logger.info(f"播放模式切换为: {self._get_play_mode_name()}")
    
    def _get_play_mode_name(self):
        """获取播放模式名称"""
        modes = ["顺序播放", "随机播放", "单曲循环"]
        return modes[self.play_mode] if self.play_mode < len(modes) else "未知"
    
    def _get_next_song_index(self):
        """根据播放模式获取下一首歌曲索引"""
        if not self.playlist:
            return -1
        
        if self.play_mode == 2:  # 单曲循环
            return self.current_play_index
        elif self.play_mode == 1:  # 随机播放
            return self._get_shuffle_next_index()
        else:  # 顺序播放
            next_index = self.current_play_index + 1
            if next_index >= len(self.playlist):
                # 检查是否循环播放
                if self.settings["other"].get("repeat_mode") == "all":
                    return 0  # 循环到第一首
                else:
                    return -1  # 不循环播放
            return next_index
    
    def _get_previous_song_index(self):
        """根据播放模式获取上一首歌曲索引"""
        if not self.playlist:
            return -1
        
        if self.play_mode == 2:  # 单曲循环
            return self.current_play_index
        elif self.play_mode == 1:  # 随机播放
            return self._get_shuffle_previous_index()
        else:  # 顺序播放
            prev_index = self.current_play_index - 1
            return prev_index if prev_index >= 0 else len(self.playlist) - 1
    
    # =============== 随机播放模式管理 ===============
    
    def _get_shuffle_next_index(self):
        """获取随机播放模式下的下一首索引"""
        playlist_length = len(self.playlist)
        if playlist_length <= 0:
            return -1
        
        # 如果播放列表只有一首歌曲
        if playlist_length == 1:
            return 0
        
        if self.shuffle_mode == 0:  # 智能随机（避免重复）
            # 从所有可能的索引中排除当前索引
            possible_indices = list(range(playlist_length))
            
            # 如果最近播放过，避免重复
            if len(self.shuffle_history) >= 3:
                recent = set(self.shuffle_history[-3:])
                possible_indices = [i for i in possible_indices if i not in recent]
            
            # 如果没有可用的索引，清空历史重新开始
            if not possible_indices:
                possible_indices = list(range(playlist_length))
                self.shuffle_history = []
            
            next_index = random.choice(possible_indices)
            self.shuffle_history.append(next_index)
            
            # 限制历史记录大小
            if len(self.shuffle_history) > self.max_shuffle_history:
                self.shuffle_history.pop(0)
            
            logger.debug(f"智能随机播放，返回索引: {next_index}, 历史: {self.shuffle_history}")
            return next_index
            
        elif self.shuffle_mode == 1:  # 完全随机（随机播放所有歌曲）
            # 从所有未播放的歌曲中随机选择
            remaining = [i for i in range(playlist_length) if i != self.current_play_index and i not in self.shuffle_history]
            
            # 如果没有可用的，清空历史重新开始
            if not remaining:
                remaining = list(range(playlist_length))
                self.shuffle_history = []
            
            next_index = random.choice(remaining)
            self.shuffle_history.append(next_index)
            
            # 限制历史记录大小
            if len(self.shuffle_history) > self.max_shuffle_history:
                self.shuffle_history.pop(0)
            
            return next_index
            
        else:  # 纯随机（完全随机）
            return random.randint(0, playlist_length - 1)
    
    def _get_shuffle_previous_index(self):
        """获取随机播放模式下的上一首索引"""
        playlist_length = len(self.playlist)
        if playlist_length <= 0:
            return -1
        
        # 如果有播放历史，从历史中获取上一首
        if len(self.shuffle_history) > 0:
            # 移除当前歌曲（如果有）
            if self.current_play_index in self.shuffle_history:
                self.shuffle_history.remove(self.current_play_index)
            
            # 如果历史不为空，返回最后一个
            if len(self.shuffle_history) > 0:
                return self.shuffle_history.pop()
        
        # 如果没有历史，返回随机一首
        return random.randint(0, playlist_length - 1)
    
    def cycle_shuffle_mode(self):
        """循环切换随机播放模式"""
        self.shuffle_mode = (self.shuffle_mode + 1) % 3
        mode_names = ["智能随机", "完全随机", "纯随机"]
        mode_name = mode_names[self.shuffle_mode]
        
        logger.info(f"随机模式切换为: {mode_name}")
        return mode_name
    
    def shuffle_playlist(self):
        """随机排序播放列表"""
        if len(self.playlist) > 1:
            random.shuffle(self.playlist)
            
            # 更新UI播放列表（如果存在）
            if self.playlist_widget:
                self._update_ui_playlist()
            
            logger.info("播放列表已随机排序")
            return True
        return False
    
    # =============== 辅助方法 ===============
    
    def _update_current_song_info(self, file_path):
        """更新当前歌曲信息"""
        if not file_path:
            return
        
        # 查找播放列表中的歌曲信息
        song_info = None
        for i, song in enumerate(self.playlist):
            if song.get('path') == file_path:
                song_info = song
                self.current_play_index = i
                break
        
        # 如果没有找到，创建新的歌曲信息
        if song_info is None:
            song_info = self._create_song_info_from_file(file_path)
        
        self.current_song_info = song_info
        self.current_song_changed.emit(song_info)
    
    def _create_song_info_from_file(self, file_path):
        """从文件创建歌曲信息"""
        filename = os.path.basename(file_path)
        name, ext = os.path.splitext(filename)
        
        return {
            'id': '',
            'title': name,
            'author': '未知艺术家',
            'duration': '00:00',
            'album': '未知专辑',
            'url': '',
            'pic': '',
            'lrc': '',
            'path': file_path,
            'filename': filename,
            'extension': ext.lower(),
            'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
            'last_modified': os.path.getmtime(file_path) if os.path.exists(file_path) else 0
        }
    
    def _standardize_song_info(self, song_info):
        """标准化歌曲信息到原始格式
        
        Args:
            song_info: 歌曲信息字典
            
        Returns:
            dict: 标准化后的歌曲信息
        """
        # 获取原始值
        raw_duration = song_info.get('duration', '00:00')
        # 处理duration：如果是数字则格式化为时间字符串
        if isinstance(raw_duration, (int, float)):
            duration_str = self.format_time(raw_duration)
        else:
            duration_str = str(raw_duration)
        
        # 创建原始格式的字典
        standardized = {
            'id': song_info.get('id', ''),
            'title': song_info.get('title', song_info.get('name', '')),
            'author': song_info.get('author', song_info.get('artists', '未知艺术家')),
            'duration': duration_str,
            'album': song_info.get('album', '未知专辑'),
            'url': song_info.get('url', ''),
            'pic': song_info.get('pic', ''),
            'lrc': song_info.get('lrc', ''),
            'path': song_info.get('path', ''),
            'filename': song_info.get('filename', ''),
            'extension': song_info.get('extension', ''),
            'file_size': song_info.get('file_size', 0),
            'last_modified': song_info.get('last_modified', 0)
        }
        return standardized
    
    def _add_to_play_history(self, file_path):
        """添加到播放历史"""
        if file_path:
            self.play_history.append({
                'path': file_path,
                'timestamp': time.time(),
                'position': self.media_player.position()
            })
            
            # 限制历史记录大小
            if len(self.play_history) > self.max_history_size:
                self.play_history.pop(0)
    
    def _add_to_ui_playlist(self, song_info):
        """添加歌曲到UI播放列表"""
        try:
            # 兼容两种格式：优先使用title，不存在则使用name
            song_name = song_info.get('title', song_info.get('name', '未知歌曲'))
            logger.info(f"_add_to_ui_playlist: 添加歌曲 - {song_name}")
            item = QListWidgetItem(song_name)
            item.setData(Qt.UserRole, song_info)
            item.setToolTip(song_info.get('path', ''))
            # 确保文本颜色可见
            item.setForeground(QColor('#E8E8E8'))
            
            # 设置图标（如果有封面）
            cover_path = song_info.get('cover_path')
            if cover_path and os.path.exists(cover_path):
                try:
                    pixmap = QPixmap(cover_path)
                    if not pixmap.isNull():
                        pixmap = pixmap.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        item.setIcon(QIcon(pixmap))
                except Exception as e:
                    logger.debug(f"设置封面图标失败: {e}")
            
            self.playlist_widget.addItem(item)
        except Exception as e:
            logger.error(f"_add_to_ui_playlist: 添加歌曲到UI失败: {e}, playlist_widget: {self.playlist_widget}")
    
    def _update_ui_playlist(self):
        """更新UI播放列表"""
        logger.info(f"_update_ui_playlist: playlist_widget对象: {self.playlist_widget}, bool值: {bool(self.playlist_widget)}, playlist长度 = {len(self.playlist)}")
        
        # 即使playlist_widget被认为是None/False，也尝试更新UI
        try:
            self.playlist_widget.clear()
            logger.info(f"_update_ui_playlist: 清空UI播放列表，开始添加{len(self.playlist)}首歌曲")
            for song_info in self.playlist:
                self._add_to_ui_playlist(song_info)
            logger.info(f"_update_ui_playlist: UI更新完成")
            # 确保UI刷新
            self.playlist_widget.update()
            self.playlist_widget.repaint()
        except Exception as e:
            logger.error(f"_update_ui_playlist: 更新UI时发生异常: {e}")
            # 如果异常发生，可能widget真的无效，记录详细状态
            if self.playlist_widget is None:
                logger.error(f"_update_ui_playlist: playlist_widget is None")
            else:
                logger.error(f"_update_ui_playlist: playlist_widget类型: {type(self.playlist_widget)}, id: {id(self.playlist_widget)}")
    
    # =============== 错误恢复 ===============
    
    def _recover_and_retry(self, file_path):
        """尝试恢复并重播
        
        Args:
            file_path: 要重播的文件路径
        """
        try:
            logger.info(f"尝试恢复播放 (第{self.recovery_attempts}次)")
            
            # 重置媒体播放器
            self.media_player.stop()
            self.media_player.setMedia(QMediaContent())
            QApplication.processEvents()
            time.sleep(0.1)
            
            # 重新创建媒体播放器
            self._recreate_media_player()
            
            # 重新尝试播放
            QTimer.singleShot(300, lambda: self.play_audio(file_path))
            
        except Exception as e:
            logger.error(f"恢复播放失败: {e}")
            self.error_occurred.emit(f"恢复播放失败: {str(e)}")
    
    def _recreate_media_player(self):
        """重新创建媒体播放器"""
        try:
            # 保存当前状态
            current_volume = self.media_player.volume()
            
            # 断开连接
            try:
                self.media_player.stateChanged.disconnect()
                self.media_player.positionChanged.disconnect()
                self.media_player.durationChanged.disconnect()
                self.media_player.mediaStatusChanged.disconnect()
                self.media_player.volumeChanged.disconnect()
            except:
                pass
            
            # 创建新的媒体播放器
            new_player = QMediaPlayer()
            new_player.setNotifyInterval(50)
            new_player.setVolume(current_volume)
            
            # 替换旧的播放器
            self.media_player.deleteLater()
            self.media_player = new_player
            
            # 重新连接信号
            self._setup_connections()
            
            # 重置恢复尝试计数
            self.recovery_attempts = 0
            
            logger.info("媒体播放器重新创建成功")
            
        except Exception as e:
            logger.error(f"重新创建媒体播放器失败: {e}")
    
    # =============== 信号处理 ===============
    
    def _on_state_changed(self, state):
        """处理播放状态改变"""
        self.state_changed.emit(state)
        
        # 记录状态变化
        state_names = {
            QMediaPlayer.StoppedState: "停止",
            QMediaPlayer.PlayingState: "播放",
            QMediaPlayer.PausedState: "暂停"
        }
        logger.debug(f"播放状态改变: {state_names.get(state, '未知')}")
    
    def _on_position_changed(self, position):
        """处理播放位置改变"""
        self.position_changed.emit(position)
    
    def _on_duration_changed(self, duration):
        """处理歌曲时长改变"""
        self.duration_changed.emit(duration)
        
        # 更新当前歌曲的时长信息
        if self.current_song_info and duration > 0:
            self.current_song_info['duration'] = duration
    
    def _on_media_status_changed(self, status):
        """处理媒体状态改变"""
        self.media_status_changed.emit(status)
        
        status_names = {
            QMediaPlayer.NoMedia: "无媒体",
            QMediaPlayer.LoadingMedia: "加载中",
            QMediaPlayer.LoadedMedia: "已加载",
            QMediaPlayer.StalledMedia: "卡顿",
            QMediaPlayer.BufferingMedia: "缓冲中",
            QMediaPlayer.BufferedMedia: "已缓冲",
            QMediaPlayer.EndOfMedia: "播放结束",
            QMediaPlayer.InvalidMedia: "无效媒体"
        }
        
        status_name = status_names.get(status, f"未知({status})")
        logger.debug(f"媒体状态改变: {status_name}")
        
        # 处理播放结束
        if status == QMediaPlayer.EndOfMedia:
            logger.info("歌曲播放结束")
            if self.settings["other"].get("auto_next", True):
                QTimer.singleShot(500, self.play_next)
    
    def _on_volume_changed(self, volume):
        """处理音量改变"""
        self.volume_changed.emit(volume)
    
    def _on_media_error(self, error=None):
        """处理媒体错误"""
        try:
            logger.error(f"_on_media_error called with error: {error}, error type: {type(error)}")
            # 获取错误信息
            error_str = ""
            if hasattr(self.media_player, 'errorString'):
                error_str = self.media_player.errorString()
            elif error:
                error_str = str(error)
            else:
                error_str = "未知媒体错误"
            
            logger.error(f"媒体错误: {error_str}")
            
            # 发送错误信号
            self.error_occurred.emit(error_str)
            
            # 检查是否为会话严重错误
            if "session" in error_str.lower() or "serious" in error_str.lower() or "-1072871856" in error_str:
                logger.warning("检测到媒体会话严重错误")
                QTimer.singleShot(100, lambda: self._recover_and_retry(self.current_song_path))
            
        except Exception as e:
            logger.error(f"处理媒体错误时发生异常: {e}")
    
    # =============== 向后兼容方法（VLC相关） ===============
    
    def is_vlc_available(self):
        """检查VLC是否可用（总是返回False，因为我们已经移除了VLC）"""
        return False
    
    def enable_vlc(self):
        """启用VLC引擎（空实现，仅用于向后兼容）"""
        logger.warning("VLC引擎已移除，此方法仅用于向后兼容")
        self.vlc_preferred = True
    
    def disable_vlc(self):
        """禁用VLC引擎（空实现，仅用于向后兼容）"""
        logger.warning("VLC引擎已移除，此方法仅用于向后兼容")
        self.vlc_preferred = False
    
    def toggle_vlc_preference(self):
        """切换VLC首选项（空实现，仅用于向后兼容）"""
        logger.warning("VLC引擎已移除，此方法仅用于向后兼容")
        self.vlc_preferred = not self.vlc_preferred
        return self.vlc_preferred
    
    # =============== 公共属性 ===============
    
    @property
    def is_playing(self):
        """是否正在播放"""
        return self.media_player.state() == QMediaPlayer.PlayingState
    
    @property
    def is_paused(self):
        """是否暂停"""
        return self.media_player.state() == QMediaPlayer.PausedState
    
    @property
    def is_stopped(self):
        """是否停止"""
        return self.media_player.state() == QMediaPlayer.StoppedState
    
    @property
    def volume(self):
        """获取当前音量"""
        return self.media_player.volume()
    
    @property
    def position(self):
        """获取当前播放位置"""
        return self.media_player.position()
    
    @property
    def duration(self):
        """获取当前歌曲时长"""
        return self.media_player.duration()
    
    @property
    def current_song(self):
        """获取当前歌曲信息"""
        return self.current_song_info
    
    @property
    def playlist_count(self):
        """获取播放列表歌曲数量"""
        return len(self.playlist)
    
    @property
    def has_next(self):
        """是否有下一首歌曲"""
        return self._get_next_song_index() != -1
    
    @property
    def has_previous(self):
        """是否有上一首歌曲"""
        return self._get_previous_song_index() != -1
    
    # =============== 工具方法 ===============
    
    @staticmethod
    def format_time(milliseconds):
        """格式化时间显示
        
        Args:
            milliseconds: 毫秒数
            
        Returns:
            str: 格式化后的时间字符串 (MM:SS)
        """
        if milliseconds <= 0:
            return "00:00"
        
        total_seconds = milliseconds // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        
        return f"{minutes:02d}:{seconds:02d}"
    
    @staticmethod
    def format_detailed_time(milliseconds):
        """格式化详细时间显示
        
        Args:
            milliseconds: 毫秒数
            
        Returns:
            str: 格式化后的时间字符串 (HH:MM:SS)
        """
        if milliseconds <= 0:
            return "00:00:00"
        
        total_seconds = milliseconds // 1000
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    def get_file_info(self, file_path):
        """获取文件信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            dict: 文件信息字典
        """
        if not os.path.exists(file_path):
            return None
        
        try:
            file_stat = os.stat(file_path)
            
            return {
                'path': file_path,
                'filename': os.path.basename(file_path),
                'size': file_stat.st_size,
                'size_formatted': self._format_file_size(file_stat.st_size),
                'created': file_stat.st_ctime,
                'modified': file_stat.st_mtime,
                'accessed': file_stat.st_atime,
                'extension': os.path.splitext(file_path)[1].lower()
            }
        except Exception as e:
            logger.error(f"获取文件信息失败: {e}")
            return None
    
    @staticmethod
    def _format_file_size(size_bytes):
        """格式化文件大小
        
        Args:
            size_bytes: 字节数
            
        Returns:
            str: 格式化后的文件大小
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    
    def save_playlist(self, file_path):
        """保存播放列表到文件
        
        Args:
            file_path: 文件保存路径
            
        Returns:
            bool: 是否成功保存
        """
        try:
            playlist_data = {
                "playlist": self.playlist,
                "current_index": self.current_play_index,
                "timestamp": time.time()
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(playlist_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"播放列表已保存: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存播放列表失败: {e}")
            return False
    
    def load_playlist(self, file_path):
        """从文件加载播放列表
        
        Args:
            file_path: 播放列表文件路径
            
        Returns:
            bool: 是否成功加载
        """
        logger.info(f"load_playlist开始，文件路径: {file_path}")
        logger.info(f"load_playlist: playlist_widget对象: {self.playlist_widget}, id: {id(self.playlist_widget)}, bool值: {bool(self.playlist_widget)}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                playlist_data = json.load(f)
            
            # 验证数据格式
            if "playlist" not in playlist_data:
                logger.error("加载播放列表: 数据格式错误")
                return False
            
            # 清空当前播放列表
            self.clear_playlist()
            
            # 加载歌曲
            loaded_count = 0
            for song_info in playlist_data["playlist"]:
                song_path = song_info.get('path')
                if song_path and os.path.exists(song_path):
                    self.add_to_playlist(song_path, song_info)
                    loaded_count += 1
                else:
                    logger.warning(f"加载播放列表: 文件不存在 - {song_path}")
            
            # 恢复当前播放索引
            if "current_index" in playlist_data:
                self.current_play_index = playlist_data["current_index"]
                if 0 <= self.current_play_index < len(self.playlist):
                    self.current_song_info = self.playlist[self.current_play_index]
            
            logger.info(f"播放列表已加载: {file_path} ({loaded_count} 首歌曲)")
            return True
            
        except Exception as e:
            logger.error(f"加载播放列表失败: {e}")
            return False
    
    def _safe_seek_retry(self, position, attempt=1):
        """安全的重试跳转方法
        
        Args:
            position: 目标位置（毫秒）
            attempt: 当前尝试次数
        """
        max_attempts = 3
        
        if attempt > max_attempts:
            logger.error(f"跳转重试失败，已达到最大尝试次数: {max_attempts}")
            return
        
        try:
            logger.info(f"跳转重试 (第{attempt}次): {position}ms")
            
            # 检查媒体状态
            from PyQt5.QtMultimedia import QMediaPlayer
            media_status = self.media_player.mediaStatus()
            
            # 等待媒体准备好
            if media_status not in [QMediaPlayer.LoadedMedia, QMediaPlayer.BufferedMedia]:
                logger.info(f"媒体状态未就绪: {media_status}，等待后重试")
                QTimer.singleShot(200, lambda: self._safe_seek_retry(position, attempt + 1))
                return
            
            # 尝试跳转
            if self.media_player.isSeekable():
                self.media_player.setPosition(position)
                logger.info(f"跳转重试成功: {position}ms")
            else:
                logger.warning(f"跳转重试: 媒体不支持定位")
                
        except Exception as e:
            logger.error(f"跳转重试失败: {e}")
            # 继续重试
            QTimer.singleShot(200, lambda: self._safe_seek_retry(position, attempt + 1))
    
    def cleanup(self):
        """清理资源"""
        logger.info("清理音频播放器资源")
        
        # 保存设置
        self.save_player_settings()
        
        # 停止播放
        self.stop()
        
        # 断开所有连接
        try:
            self.media_player.stateChanged.disconnect()
            self.media_player.positionChanged.disconnect()
            self.media_player.durationChanged.disconnect()
            self.media_player.mediaStatusChanged.disconnect()
            self.media_player.volumeChanged.disconnect()
        except:
            pass
        
        # 清理媒体
        self.media_player.setMedia(QMediaContent())
        
        logger.info("音频播放器资源清理完成")