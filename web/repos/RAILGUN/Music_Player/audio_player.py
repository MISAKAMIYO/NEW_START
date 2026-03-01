# audio_player.py
"""
音乐播放器核心音频播放模块
负责处理音频文件的播放、控制、状态管理和播放列表功能
基于 test/player_audio.py
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

# 延迟导入 VLC：避免在模块导入时因 libvlc.dll 缺失导致整个应用崩溃。
# 在 `_init_vlc_fallback` 中尝试导入并根据结果设置 `VLC_AVAILABLE`。
vlc = None
VLC_AVAILABLE = False

# 延迟导入 pygame：避免在模块导入时因 pygame 缺失导致整个应用崩溃。
# 在 `_init_pygame_fallback` 中尝试导入并根据结果设置 `PYGAME_AVAILABLE`。
pygame = None
PYGAME_AVAILABLE = False

logger = logging.getLogger("MusicApp")


class AudioPlayer(QObject):
    """核心音频播放器类"""
    
    state_changed = pyqtSignal(int)
    position_changed = pyqtSignal(int)
    duration_changed = pyqtSignal(int)
    media_status_changed = pyqtSignal(int)
    volume_changed = pyqtSignal(int)
    current_song_changed = pyqtSignal(dict)
    playlist_updated = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, settings=None, parent=None):
        super().__init__(parent)
        
        self.settings = settings or self._load_default_settings()
        
        self.media_player = QMediaPlayer()
        self.media_player.setNotifyInterval(50)
        
        self.vlc_player = None
        self.use_vlc_fallback = False
        self.pygame_player = None
        self.use_pygame_fallback = False
        self._init_pygame_fallback()
        self._init_vlc_fallback()
        
        self.current_song_path = None
        self.current_song_info = None
        self.current_play_index = -1
        
        self.playlist = []
        self.playlist_widget = None
        
        self.play_mode = 0
        
        self.play_history = []
        self.max_history_size = 100
        
        self._load_player_settings()
        self._setup_connections()
        
        self.recovery_attempts = 0
        self.max_recovery_attempts = 3
        
        logger.info("音频播放器初始化完成")
        print("[播放器内核] 音频播放器初始化完成，准备就绪")
    
    def _init_pygame_fallback(self):
        """初始化Pygame回退播放器。尝试在运行时导入 pygame，并捕获所有异常。
        这样可以避免在模块导入阶段因 pygame 缺失导致的崩溃。
        """
        global pygame, PYGAME_AVAILABLE
        try:
            # 尝试导入 pygame（可能在导入时尝试加载 SDL 库，会抛出异常）
            import pygame as _pygame
            pygame = _pygame
            PYGAME_AVAILABLE = True
            print("[播放器内核] Pygame 库可用")
        except Exception as e:
            pygame = None
            PYGAME_AVAILABLE = False
            logger.warning(f"pygame 初始化失败，Pygame回退功能不可用: {e}")
            print(f"[播放器内核] Pygame 库不可用: {e}")
            return

        # 如果导入成功，再尝试创建 PygamePlayer 实例
        if PYGAME_AVAILABLE:
            try:
                self.pygame_player = PygamePlayer(self)
                logger.info("Pygame回退播放器初始化成功")
                print("[播放器内核] Pygame播放器初始化成功")
            except Exception as e:
                logger.warning(f"Pygame回退播放器初始化失败: {e}")
                print(f"[播放器内核] Pygame播放器初始化失败: {e}")
                self.pygame_player = None
    
    def _init_vlc_fallback(self):
        """初始化VLC回退播放器。尝试在运行时导入 python-vlc，并捕获所有异常。
        这样可以避免在模块导入阶段因 libvlc.dll 等依赖缺失导致的崩溃。
        """
        global vlc, VLC_AVAILABLE
        try:
            # 尝试导入 python-vlc（可能在导入时尝试加载本地 libvlc，会抛出 FileNotFoundError）
            import vlc as _vlc
            vlc = _vlc
            VLC_AVAILABLE = True
            print("[播放器内核] VLC 库可用")
        except Exception as e:
            vlc = None
            VLC_AVAILABLE = False
            logger.warning(f"python-vlc 初始化失败，VLC回退功能不可用: {e}")
            print(f"[播放器内核] VLC 库不可用: {e}")
            return

        # 如果导入成功，再尝试创建 VLCPlayer 实例
        if VLC_AVAILABLE:
            try:
                self.vlc_player = VLCPlayer(self)
                logger.info("VLC回退播放器初始化成功")
                print("[播放器内核] VLC播放器初始化成功")
            except Exception as e:
                logger.warning(f"VLC回退播放器初始化失败: {e}")
                print(f"[播放器内核] VLC播放器初始化失败: {e}")
                self.vlc_player = None
    
    def _load_default_settings(self):
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
                "playback_mode": "list"
            },
            "lyrics": {
                "show_lyrics": True,
                "auto_save": True
            }
        }
    
    def _load_player_settings(self):
        settings = QSettings("Railgun_lover", "MusicPlayer")
        
        volume = settings.value("player/volume", 80, int)
        self.media_player.setVolume(volume)
        
        self.play_mode = settings.value("player/play_mode", 0, int)
        
        last_song = settings.value("player/last_song")
        if last_song and os.path.exists(last_song):
            self.current_song_path = last_song
            last_position = settings.value("player/last_position", 0, int)
            
            def restore_position():
                if self.media_player.duration() > 0:
                    self.media_player.setPosition(min(last_position, self.media_player.duration()))
            
            QTimer.singleShot(500, restore_position)
    
    def save_player_settings(self):
        settings = QSettings("Railgun_lover", "MusicPlayer")
        
        settings.setValue("player/volume", self.media_player.volume())
        settings.setValue("player/play_mode", self.play_mode)
        
        if self.current_song_path:
            settings.setValue("player/last_song", self.current_song_path)
            settings.setValue("player/last_position", self.media_player.position())
        
        settings.sync()
        logger.debug("播放器设置已保存")
    
    def _setup_connections(self):
        self.media_player.stateChanged.connect(self._on_state_changed)
        self.media_player.positionChanged.connect(self._on_position_changed)
        self.media_player.durationChanged.connect(self._on_duration_changed)
        self.media_player.mediaStatusChanged.connect(self._on_media_status_changed)
        self.media_player.volumeChanged.connect(self._on_volume_changed)
        
        try:
            if hasattr(self.media_player, 'error'):
                self.media_player.error.connect(self._on_media_error)
            if hasattr(self.media_player, 'errorOccurred'):
                self.media_player.errorOccurred.connect(self._on_media_error)
        except Exception as e:
            logger.warning(f"无法连接错误信号: {e}")
    
    def play_audio(self, file_path):
        if not file_path:
            logger.warning("播放音频: 文件路径为空")
            print("[播放器内核] 错误: 文件路径为空")
            return False
        
        if not os.path.exists(file_path):
            logger.error(f"播放音频: 文件不存在 - {file_path}")
            print(f"[播放器内核] 错误: 文件不存在 - {os.path.basename(file_path)}")
            self.error_occurred.emit(f"文件不存在: {os.path.basename(file_path)}")
            return False
        
        # 三层播放引擎优先级: QMediaPlayer -> Pygame -> VLC
        # 首先尝试使用QMediaPlayer（除非已经启用了其他回退）
        if not self.use_vlc_fallback and not self.use_pygame_fallback:
            try:
                if self.media_player.state() == QMediaPlayer.PlayingState:
                    self.media_player.stop()
                
                self.current_song_path = file_path
                self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile(file_path)))
                self.media_player.play()
                
                self._update_current_song_info(file_path)
                self._add_to_play_history(file_path)
                
                logger.info(f"使用QMediaPlayer播放音频: {os.path.basename(file_path)}")
                print(f"[播放器内核] 正在使用 QMediaPlayer 播放: {os.path.basename(file_path)}")
                return True
                
            except Exception as e:
                logger.warning(f"QMediaPlayer播放失败: {e}")
                print(f"[播放器内核] QMediaPlayer 播放失败: {e}")
                # QMediaPlayer失败，尝试Pygame回退
                if self.pygame_player is not None:
                    logger.info("尝试使用Pygame播放器")
                    print("[播放器内核] 切换到 Pygame 播放器...")
                    return self._play_with_pygame(file_path)
                else:
                    # Pygame不可用，尝试VLC回退
                    if self.vlc_player is not None:
                        logger.info("尝试使用VLC回退播放器")
                        print("[播放器内核] 切换到 VLC 播放器...")
                        return self._play_with_vlc(file_path)
                    else:
                        logger.error("播放音频失败且无回退可用")
                        print("[播放器内核] 错误: 所有播放器都不可用!")
                        self.error_occurred.emit(f"播放失败: {str(e)}")
                        
                        if self.recovery_attempts < self.max_recovery_attempts:
                            self.recovery_attempts += 1
                            QTimer.singleShot(100, lambda: self._recover_and_retry(file_path))
                        
                        return False
        elif self.use_pygame_fallback and not self.use_vlc_fallback:
            # 已经启用了Pygame回退，直接使用Pygame播放器
            print("[播放器内核] 当前使用 Pygame 播放器")
            return self._play_with_pygame(file_path)
        else:
            # 已经启用了VLC回退，直接使用VLC播放器
            print("[播放器内核] 当前使用 VLC 播放器")
            return self._play_with_vlc(file_path)
    
    def _play_with_pygame(self, file_path):
        """使用Pygame播放器播放音频文件"""
        if self.pygame_player is None:
            logger.error("Pygame播放器不可用")
            print("[播放器内核] Pygame播放器不可用")
            self.error_occurred.emit("Pygame播放器不可用")
            return False
        
        try:
            # 停止当前播放
            if self.media_player.state() == QMediaPlayer.PlayingState:
                self.media_player.stop()
            
            self.current_song_path = file_path
            
            # 使用Pygame播放器
            media_content = QMediaContent(QUrl.fromLocalFile(file_path))
            if self.pygame_player.setMedia(media_content):
                self.use_pygame_fallback = True
                self.use_vlc_fallback = False  # 确保VLC回退标志为False
                # 连接Pygame播放器信号
                self._setup_pygame_connections()
                
                if self.pygame_player.play():
                    self._update_current_song_info(file_path)
                    self._add_to_play_history(file_path)
                    
                    logger.info(f"使用Pygame播放器播放音频: {os.path.basename(file_path)}")
                    print(f"[播放器内核] Pygame播放器开始播放: {os.path.basename(file_path)}")
                    return True
                else:
                    logger.error("Pygame播放器播放失败")
                    print("[播放器内核] Pygame播放器播放失败")
                    self.error_occurred.emit("Pygame播放器播放失败")
                    return False
            else:
                logger.error("Pygame播放器设置媒体失败")
                print("[播放器内核] Pygame播放器设置媒体失败")
                self.error_occurred.emit("Pygame播放器设置媒体失败")
                return False
                
        except Exception as e:
            logger.error(f"Pygame播放音频失败: {e}")
            print(f"[播放器内核] Pygame播放音频失败: {e}")
            self.error_occurred.emit(f"Pygame播放失败: {str(e)}")
            return False
    
    def _play_with_vlc(self, file_path):
        """使用VLC播放器播放音频文件"""
        if self.vlc_player is None:
            logger.error("VLC播放器不可用")
            print("[播放器内核] VLC播放器不可用")
            self.error_occurred.emit("VLC播放器不可用")
            return False
        
        try:
            # 停止当前播放
            if self.media_player.state() == QMediaPlayer.PlayingState:
                self.media_player.stop()
            
            self.current_song_path = file_path
            
            # 使用VLC播放器
            media_content = QMediaContent(QUrl.fromLocalFile(file_path))
            if self.vlc_player.setMedia(media_content):
                self.use_vlc_fallback = True
                self.use_pygame_fallback = False  # 确保Pygame回退标志为False
                # 连接VLC播放器信号
                self._setup_vlc_connections()
                
                if self.vlc_player.play():
                    self._update_current_song_info(file_path)
                    self._add_to_play_history(file_path)
                    
                    logger.info(f"使用VLC播放器播放音频: {os.path.basename(file_path)}")
                    print(f"[播放器内核] VLC播放器开始播放: {os.path.basename(file_path)}")
                    return True
                else:
                    logger.error("VLC播放器播放失败")
                    print("[播放器内核] VLC播放器播放失败")
                    self.error_occurred.emit("VLC播放器播放失败")
                    return False
            else:
                logger.error("VLC播放器设置媒体失败")
                print("[播放器内核] VLC播放器设置媒体失败")
                self.error_occurred.emit("VLC播放器设置媒体失败")
                return False
                
        except Exception as e:
            logger.error(f"VLC播放音频失败: {e}")
            print(f"[播放器内核] VLC播放音频失败: {e}")
            self.error_occurred.emit(f"VLC播放失败: {str(e)}")
            return False
    
    def _setup_vlc_connections(self):
        """设置VLC播放器信号连接"""
        if self.vlc_player is None:
            logger.warning("_setup_vlc_connections: vlc_player为None，无法连接信号")
            return
        
        try:
            logger.debug("开始连接VLC播放器信号...")
            # 连接VLC播放器信号到AudioPlayer信号
            self.vlc_player.state_changed.connect(self._on_state_changed)
            logger.debug("state_changed信号连接成功")
            
            self.vlc_player.position_changed.connect(self._on_position_changed)
            logger.debug("position_changed信号连接成功")
            
            self.vlc_player.duration_changed.connect(self._on_duration_changed)
            logger.debug("duration_changed信号连接成功")
            
            self.vlc_player.media_status_changed.connect(self._on_media_status_changed)
            logger.debug("media_status_changed信号连接成功")
            
            self.vlc_player.volume_changed.connect(self._on_volume_changed)
            logger.debug("volume_changed信号连接成功")
            
            self.vlc_player.error_occurred.connect(self._on_media_error)
            logger.debug("error_occurred信号连接成功")
            
            logger.debug("VLC播放器所有信号连接已设置")
        except Exception as e:
            logger.error(f"设置VLC播放器信号连接失败: {e}")
    
    def _setup_pygame_connections(self):
        """设置Pygame播放器信号连接"""
        if self.pygame_player is None:
            logger.warning("_setup_pygame_connections: pygame_player为None，无法连接信号")
            return
        
        try:
            logger.debug("开始连接Pygame播放器信号...")
            # 连接Pygame播放器信号到AudioPlayer信号
            self.pygame_player.state_changed.connect(self._on_state_changed)
            logger.debug("state_changed信号连接成功")
            
            self.pygame_player.position_changed.connect(self._on_position_changed)
            logger.debug("position_changed信号连接成功")
            
            self.pygame_player.duration_changed.connect(self._on_duration_changed)
            logger.debug("duration_changed信号连接成功")
            
            self.pygame_player.media_status_changed.connect(self._on_media_status_changed)
            logger.debug("media_status_changed信号连接成功")
            
            self.pygame_player.volume_changed.connect(self._on_volume_changed)
            logger.debug("volume_changed信号连接成功")
            
            self.pygame_player.error_occurred.connect(self._on_media_error)
            logger.debug("error_occurred信号连接成功")
            
            logger.debug("Pygame播放器所有信号连接已设置")
        except Exception as e:
            logger.error(f"设置Pygame播放器信号连接失败: {e}")
    
    def play_file_safe(self, file_path):
        try:
            if not self.play_audio(file_path):
                self.error_occurred.emit("无法播放文件，请检查格式或文件完整性")
        except Exception as e:
            logger.error(f"安全播放失败: {e}")
            self.error_occurred.emit(f"播放错误: {str(e)}")
    
    def play(self):
        if self.use_pygame_fallback and self.pygame_player is not None:
            # 使用Pygame播放器
            self.pygame_player.play()
        elif self.use_vlc_fallback and self.vlc_player is not None:
            # 使用VLC播放器
            self.vlc_player.play()
        else:
            # 使用QMediaPlayer
            if self.media_player.media().isNull():
                if self.current_song_path:
                    self.play_audio(self.current_song_path)
                else:
                    logger.warning("播放: 没有可播放的歌曲")
            else:
                self.media_player.play()
    
    def pause(self):
        if self.use_pygame_fallback and self.pygame_player is not None:
            self.pygame_player.pause()
        elif self.use_vlc_fallback and self.vlc_player is not None:
            self.vlc_player.pause()
        else:
            self.media_player.pause()
    
    def stop(self):
        if self.use_pygame_fallback and self.pygame_player is not None:
            self.pygame_player.stop()
        elif self.use_vlc_fallback and self.vlc_player is not None:
            self.vlc_player.stop()
        else:
            self.media_player.stop()
    
    def toggle_play_pause(self):
        if self.use_pygame_fallback and self.pygame_player is not None:
            if self.pygame_player.state() == 1:
                self.pause()
            else:
                self.play()
        elif self.use_vlc_fallback and self.vlc_player is not None:
            if self.vlc_player.state() == 1:
                self.pause()
            else:
                self.play()
        else:
            if self.media_player.state() == QMediaPlayer.PlayingState:
                self.pause()
            else:
                self.play()
    
    def seek(self, position):
        try:
            if self.use_pygame_fallback and self.pygame_player is not None:
                if self.pygame_player.isSeekable():
                    self.pygame_player.setPosition(position)
                else:
                    logger.warning("跳转(Pygame): 当前媒体不支持定位")
            elif self.use_vlc_fallback and self.vlc_player is not None:
                if self.vlc_player.isSeekable():
                    self.vlc_player.setPosition(position)
                else:
                    logger.warning("跳转(VLC): 当前媒体不支持定位")
            else:
                if self.media_player.isSeekable():
                    self.media_player.setPosition(position)
                else:
                    logger.warning("跳转: 当前媒体不支持定位")
        except Exception as e:
            logger.error(f"跳转失败: {e}")
    
    def seek_percentage(self, percentage):
        if self.use_pygame_fallback and self.pygame_player is not None:
            duration = self.pygame_player.duration()
        elif self.use_vlc_fallback and self.vlc_player is not None:
            duration = self.vlc_player.duration()
        else:
            duration = self.media_player.duration()
        
        if duration > 0:
            position = int(duration * percentage / 100)
            self.seek(position)
    
    def set_volume(self, volume):
        volume = max(0, min(100, volume))
        if self.use_pygame_fallback and self.pygame_player is not None:
            self.pygame_player.setVolume(volume)
        elif self.use_vlc_fallback and self.vlc_player is not None:
            self.vlc_player.setVolume(volume)
        else:
            self.media_player.setVolume(volume)
    
    def volume_up(self, increment=5):
        if self.use_pygame_fallback and self.pygame_player is not None:
            current_volume = self.pygame_player.volume()
        elif self.use_vlc_fallback and self.vlc_player is not None:
            current_volume = self.vlc_player.volume()
        else:
            current_volume = self.media_player.volume()
        new_volume = min(100, current_volume + increment)
        self.set_volume(new_volume)
    
    def volume_down(self, decrement=5):
        if self.use_pygame_fallback and self.pygame_player is not None:
            current_volume = self.pygame_player.volume()
        elif self.use_vlc_fallback and self.vlc_player is not None:
            current_volume = self.vlc_player.volume()
        else:
            current_volume = self.media_player.volume()
        new_volume = max(0, current_volume - decrement)
        self.set_volume(new_volume)
    
    def add_to_playlist(self, file_path, song_info=None):
        if not file_path or not os.path.exists(file_path):
            logger.warning(f"添加到播放列表: 文件不存在 - {file_path}")
            return False
        
        for song in self.playlist:
            if song.get('path') == file_path:
                logger.info(f"添加到播放列表: 歌曲已存在 - {os.path.basename(file_path)}")
                return False
        
        if song_info is None:
            song_info = self._create_song_info_from_file(file_path)
        
        self.playlist.append(song_info)
        
        if self.playlist_widget is not None:
            self._add_to_ui_playlist(song_info)
        
        self.playlist_updated.emit(self.playlist)
        
        logger.info(f"添加到播放列表: {song_info.get('name', os.path.basename(file_path))}")
        return True
    
    def remove_from_playlist(self, index):
        if 0 <= index < len(self.playlist):
            removed_song = self.playlist.pop(index)
            
            if self.playlist_widget is not None and self.playlist_widget.count() > index:
                self.playlist_widget.takeItem(index)
            
            if index == self.current_play_index:
                self.current_play_index = -1
                self.current_song_path = None
                self.stop()
            
            self.playlist_updated.emit(self.playlist)
            
            logger.info(f"从播放列表移除: {removed_song.get('name', '未知歌曲')}")
            return True
        
        return False
    
    def clear_playlist(self):
        self.playlist.clear()
        
        if self.playlist_widget:
            self.playlist_widget.clear()
        
        self.current_play_index = -1
        
        self.playlist_updated.emit(self.playlist)
        
        logger.info("播放列表已清空")
    
    def play_by_index(self, index):
        if 0 <= index < len(self.playlist):
            song_info = self.playlist[index]
            file_path = song_info.get('path')
            
            if file_path and os.path.exists(file_path):
                self.current_play_index = index
                self.current_song_info = song_info
                
                self.current_song_changed.emit(song_info)
                
                return self.play_audio(file_path)
        
        return False
    
    def play_next(self):
        logger.debug(f"play_next被调用，当前播放模式: {self.play_mode}, 当前索引: {self.current_play_index}, 播放列表长度: {len(self.playlist)}")
        if not self.playlist:
            logger.debug("播放列表为空，无法播放下一首")
            return False
        
        next_index = self._get_next_song_index()
        logger.debug(f"计算出的下一首索引: {next_index}")
        if 0 <= next_index < len(self.playlist):
            logger.debug(f"播放下一首，索引: {next_index}")
            return self.play_by_index(next_index)
        
        logger.debug(f"下一首索引无效: {next_index}")
        return False
    
    def play_previous(self):
        if not self.playlist:
            return False
        
        prev_index = self._get_previous_song_index()
        if 0 <= prev_index < len(self.playlist):
            return self.play_by_index(prev_index)
        
        return False
    
    def shuffle_playlist(self):
        if len(self.playlist) > 1:
            current_song = None
            if 0 <= self.current_play_index < len(self.playlist):
                current_song = self.playlist[self.current_play_index]
            
            random.shuffle(self.playlist)
            
            if current_song and current_song in self.playlist:
                current_idx = self.playlist.index(current_song)
                if current_idx > 0:
                    self.playlist.remove(current_song)
                    self.playlist.insert(0, current_song)
                    self.current_play_index = 0
            
            if self.playlist_widget is not None:
                self._update_ui_playlist()
            
            self.playlist_updated.emit(self.playlist)
            
            logger.info("播放列表已随机打乱")
    
    def save_playlist(self, file_path):
        try:
            playlist_data = {
                "version": "1.0",
                "playlist": self.playlist,
                "timestamp": time.time(),
                "current_index": self.current_play_index
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(playlist_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"播放列表已保存: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存播放列表失败: {e}")
            return False
    
    def load_playlist(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                playlist_data = json.load(f)
            
            if "playlist" not in playlist_data:
                logger.error("加载播放列表: 数据格式错误")
                return False
            
            self.clear_playlist()
            
            loaded_count = 0
            for song_info in playlist_data["playlist"]:
                # 兼容两种字段名：音乐下载模块使用'file'，音乐播放器使用'path'
                file_path = song_info.get('path') or song_info.get('file')
                # 如果file_path是相对路径，转换为绝对路径
                if file_path and not os.path.isabs(file_path):
                    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    file_path = os.path.join(base_dir, file_path)
                
                if file_path and os.path.exists(file_path):
                    # 标准化歌曲信息字段
                    standardized_info = self._standardize_song_info(song_info, file_path)
                    self.add_to_playlist(file_path, standardized_info)
                    loaded_count += 1
                else:
                    logger.warning(f"加载播放列表: 文件不存在 - {file_path}")
            
            if "current_index" in playlist_data:
                self.current_play_index = playlist_data["current_index"]
                if 0 <= self.current_play_index < len(self.playlist):
                    self.current_song_info = self.playlist[self.current_play_index]
            
            logger.info(f"播放列表已加载: {file_path} ({loaded_count} 首歌曲)")
            return True
            
        except Exception as e:
            logger.error(f"加载播放列表失败: {e}")
            return False
    
    def _standardize_song_info(self, song_info, file_path):
        """标准化歌曲信息字段，兼容音乐下载模块和音乐播放器的字段名"""
        # 基础字段
        title = song_info.get('title') or song_info.get('name', '未知歌曲')
        author = song_info.get('author') or song_info.get('artist') or song_info.get('artists', '未知艺术家')
        album = song_info.get('album', '未知专辑')
        duration = song_info.get('duration', '00:00')
        
        # 构建标准化信息
        standardized = {
            'id': song_info.get('id', ''),
            'title': title,
            'author': author,
            'duration': duration,
            'album': album,
            'url': song_info.get('url', ''),
            'pic': song_info.get('pic') or song_info.get('cover', ''),
            'lrc': song_info.get('lrc', ''),
            'lyrics_path': song_info.get('lrc') or song_info.get('lyrics') or song_info.get('lyrics_path', ''),
            'path': file_path,
            'filename': os.path.basename(file_path),
            'extension': os.path.splitext(file_path)[1].lower() if file_path else '',
            'file_size': os.path.getsize(file_path) if file_path and os.path.exists(file_path) else 0,
            'last_modified': os.path.getmtime(file_path) if file_path and os.path.exists(file_path) else 0
        }
        
        # 保留原始信息中的其他字段
        # 支持多种封面/图片字段名称
        cover_field = song_info.get('cover') or song_info.get('pic') or song_info.get('cover_path') or song_info.get('image')
        if cover_field:
            standardized['cover_path'] = cover_field

        for key, value in song_info.items():
            if key not in standardized:
                standardized[key] = value
                
        return standardized
    
    def set_play_mode(self, mode):
        self.play_mode = max(0, min(2, mode))
        logger.info(f"播放模式设置为: {self._get_play_mode_name()}")
        self.save_player_settings()
    
    def cycle_play_mode(self):
        new_mode = (self.play_mode + 1) % 3
        self.set_play_mode(new_mode)
    
    def _get_play_mode_name(self):
        modes = ["顺序播放", "随机播放", "单曲循环"]
        return modes[self.play_mode] if self.play_mode < len(modes) else "未知"
    
    def _get_next_song_index(self):
        if not self.playlist:
            logger.debug("_get_next_song_index: 播放列表为空")
            return -1
        
        logger.debug(f"_get_next_song_index: 当前播放模式={self.play_mode}, 当前索引={self.current_play_index}, 列表长度={len(self.playlist)}")
        
        if self.play_mode == 2:
            logger.debug(f"单曲循环模式，返回当前索引: {self.current_play_index}")
            return self.current_play_index
        elif self.play_mode == 1:
            random_index = random.randint(0, len(self.playlist) - 1)
            logger.debug(f"随机播放模式，返回随机索引: {random_index}")
            return random_index
        else:
            next_index = self.current_play_index + 1
            if next_index >= len(self.playlist):
                repeat_mode = self.settings["other"].get("repeat_mode", "all")
                logger.debug(f"顺序播放模式，已到列表末尾，重复模式: {repeat_mode}")
                if repeat_mode == "all":
                    logger.debug("重复模式为'all'，返回索引0")
                    return 0
                else:
                    logger.debug("重复模式不为'all'，返回-1")
                    return -1
            logger.debug(f"顺序播放模式，返回下一个索引: {next_index}")
            return next_index
    
    def _get_previous_song_index(self):
        if not self.playlist:
            return -1
        
        if self.play_mode == 2:
            return self.current_play_index
        elif self.play_mode == 1:
            return random.randint(0, len(self.playlist) - 1)
        else:
            prev_index = self.current_play_index - 1
            return prev_index if prev_index >= 0 else len(self.playlist) - 1
    
    def _update_current_song_info(self, file_path):
        if not file_path:
            return
        
        song_info = None
        for i, song in enumerate(self.playlist):
            if song.get('path') == file_path:
                song_info = song
                self.current_play_index = i
                break
        
        if song_info is None:
            song_info = self._create_song_info_from_file(file_path)
        
        self.current_song_info = song_info
        self.current_song_changed.emit(song_info)
    
    def _create_song_info_from_file(self, file_path):
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
    
    def _add_to_play_history(self, file_path):
        if file_path:
            self.play_history.append({
                'path': file_path,
                'timestamp': time.time(),
                'position': self.media_player.position()
            })
            
            if len(self.play_history) > self.max_history_size:
                self.play_history.pop(0)
    
    def _add_to_ui_playlist(self, song_info):
        if self.playlist_widget is None:
            return
        
        item = QListWidgetItem(song_info.get('title', song_info.get('name', '未知歌曲')))
        item.setData(Qt.UserRole, song_info)
        item.setToolTip(song_info.get('path', ''))
        
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
    
    def _update_ui_playlist(self):
        if self.playlist_widget is None:
            return
        
        self.playlist_widget.clear()
        for song_info in self.playlist:
            self._add_to_ui_playlist(song_info)
    
    def _recover_and_retry(self, file_path):
        try:
            logger.info(f"尝试恢复播放 (第{self.recovery_attempts}次)")
            
            self.media_player.stop()
            self.media_player.setMedia(QMediaContent())
            QApplication.processEvents()
            time.sleep(0.1)
            
            self._recreate_media_player()
            
            QTimer.singleShot(300, lambda: self.play_audio(file_path))
            
        except Exception as e:
            logger.error(f"恢复播放失败: {e}")
            self.error_occurred.emit(f"恢复播放失败: {str(e)}")
    
    def _recreate_media_player(self):
        try:
            current_volume = self.media_player.volume()
            
            try:
                self.media_player.stateChanged.disconnect()
                self.media_player.positionChanged.disconnect()
                self.media_player.durationChanged.disconnect()
                self.media_player.mediaStatusChanged.disconnect()
                self.media_player.volumeChanged.disconnect()
            except:
                pass
            
            new_player = QMediaPlayer()
            new_player.setNotifyInterval(50)
            new_player.setVolume(current_volume)
            
            self.media_player.deleteLater()
            self.media_player = new_player
            
            self._setup_connections()
            
            self.recovery_attempts = 0
            
            logger.info("媒体播放器重新创建成功")
            
        except Exception as e:
            logger.error(f"重新创建媒体播放器失败: {e}")
    
    def _on_state_changed(self, state):
        self.state_changed.emit(state)
        
        state_names = {
            QMediaPlayer.StoppedState: "停止",
            QMediaPlayer.PlayingState: "播放",
            QMediaPlayer.PausedState: "暂停"
        }
        logger.debug(f"播放状态改变: {state_names.get(state, '未知')}")
    
    def _on_position_changed(self, position):
        self.position_changed.emit(position)
    
    def _on_duration_changed(self, duration):
        self.duration_changed.emit(duration)
        
        if self.current_song_info and duration > 0:
            self.current_song_info['duration'] = duration
    
    def _on_media_status_changed(self, status):
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
        logger.debug(f"媒体状态改变: {status_name} (状态值: {status}, VLC回退: {self.use_vlc_fallback})")
        
        # 检查是否为播放结束状态
        is_end_of_media = False
        if self.use_vlc_fallback and self.vlc_player is not None:
            # VLC回退模式，使用VLCPlayer的EndOfMedia常量
            is_end_of_media = (status == self.vlc_player.EndOfMedia)
            logger.debug(f"VLC回退模式，结束状态检查: {is_end_of_media} (VLC.EndOfMedia={self.vlc_player.EndOfMedia})")
        else:
            # 正常模式，使用QMediaPlayer的EndOfMedia常量
            is_end_of_media = (status == QMediaPlayer.EndOfMedia)
        
        if is_end_of_media:
            logger.info(f"歌曲播放结束 (VLC回退: {self.use_vlc_fallback})")
            auto_next_enabled = self.settings["other"].get("auto_next", True)
            logger.debug(f"自动下一首设置: {auto_next_enabled}")
            if auto_next_enabled:
                logger.debug("触发自动下一首播放")
                QTimer.singleShot(500, self.play_next)
            else:
                logger.debug("自动下一首已禁用")
    
    def _on_volume_changed(self, volume):
        self.volume_changed.emit(volume)
    
    def _on_media_error(self, error=None):
        try:
            # 调试日志：记录错误处理被调用
            logger.info(f"_on_media_error 被调用，error={error}")
            logger.info(f"当前状态: use_vlc_fallback={self.use_vlc_fallback}, VLC_AVAILABLE={VLC_AVAILABLE}, vlc_player={self.vlc_player is not None}")
            logger.info(f"current_song_path={self.current_song_path}, recovery_attempts={self.recovery_attempts}")
            
            # 确定错误来源与描述
            if self.use_vlc_fallback and self.vlc_player is not None:
                error_str = error or "VLC 媒体错误"
            else:
                if hasattr(self.media_player, 'errorString'):
                    try:
                        error_str = self.media_player.errorString() or str(error or "未知媒体错误")
                    except Exception:
                        error_str = str(error or "未知媒体错误")
                else:
                    error_str = str(error or "未知媒体错误")

            logger.error(f"媒体错误: {error_str}")
            
            # 检查是否为 DirectShow 错误
            if "DirectShow" in error_str or "0x80040266" in error_str:
                logger.warning("检测到 DirectShow 错误，将尝试使用 VLC 回退播放")
            
            self.error_occurred.emit(error_str)

            # 自动轮换策略：
            # 1) 如果当前使用 QMediaPlayer 且可用 VLC，则切换到 VLC 并尝试播放。
            # 2) 如果当前使用 VLC 且发生错误，则尝试重建 QMediaPlayer 并切回重试（有限次数）。
            if not self.use_vlc_fallback and VLC_AVAILABLE:
                if self.vlc_player is None:
                    logger.info("VLC播放器实例为None，尝试重新初始化VLC播放器")
                    self._init_vlc_fallback()
                
                if self.vlc_player is not None:
                    logger.info("检测到 QMediaPlayer 错误，切换为 VLC 回退播放内核并重试")
                    self.use_vlc_fallback = True
                    QTimer.singleShot(200, lambda: self._play_with_vlc(self.current_song_path))
                    return
                else:
                    logger.warning("VLC播放器初始化失败，无法切换到VLC回退")
                    self.error_occurred.emit("VLC回退播放器初始化失败，请检查VLC安装")
                    return

            if self.use_vlc_fallback:
                # VLC 出错 -> 尝试切回 QMediaPlayer 并重试（防止无限循环）
                if self.recovery_attempts < self.max_recovery_attempts:
                    self.recovery_attempts += 1
                    logger.info(f"VLC 播放出错，尝试重建 QMediaPlayer 并重试 (尝试 {self.recovery_attempts}/{self.max_recovery_attempts})")
                    self.use_vlc_fallback = False
                    # 先重建播放器，然后重试播放
                    QTimer.singleShot(300, lambda: (self._recreate_media_player(), self.play_audio(self.current_song_path)))
                    return
                else:
                    logger.error("已达到最大恢复次数，VLC -> QMediaPlayer 切换失败")
                    return

            # 对于 QMediaPlayer 的非致命错误，尝试恢复并重试
            if not self.use_vlc_fallback:
                if self.recovery_attempts < self.max_recovery_attempts:
                    self.recovery_attempts += 1
                    logger.info(f"尝试恢复播放 (第 {self.recovery_attempts} 次)")
                    QTimer.singleShot(100, lambda: self._recover_and_retry(self.current_song_path))
                else:
                    logger.error("已达到最大恢复次数，无法恢复 QMediaPlayer 播放")

        except Exception as e:
            logger.error(f"处理媒体错误时发生异常: {e}")
    
    @property
    def is_playing(self):
        if self.use_vlc_fallback and self.vlc_player is not None:
            return self.vlc_player._state == self.vlc_player.PlayingState
        return self.media_player.state() == QMediaPlayer.PlayingState
    
    @property
    def is_paused(self):
        if self.use_vlc_fallback and self.vlc_player is not None:
            return self.vlc_player._state == self.vlc_player.PausedState
        return self.media_player.state() == QMediaPlayer.PausedState
    
    @property
    def is_stopped(self):
        if self.use_vlc_fallback and self.vlc_player is not None:
            return self.vlc_player._state == self.vlc_player.StoppedState
        return self.media_player.state() == QMediaPlayer.StoppedState
    
    @property
    def volume(self):
        if self.use_pygame_fallback and self.pygame_player is not None:
            return self.pygame_player.volume()
        elif self.use_vlc_fallback and self.vlc_player is not None:
            return self.vlc_player.volume()
        return self.media_player.volume()
    
    @property
    def position(self):
        if self.use_pygame_fallback and self.pygame_player is not None:
            return self.pygame_player.position()
        elif self.use_vlc_fallback and self.vlc_player is not None:
            return self.vlc_player.position()
        return self.media_player.position()
    
    @property
    def duration(self):
        if self.use_pygame_fallback and self.pygame_player is not None:
            return self.pygame_player.duration()
        elif self.use_vlc_fallback and self.vlc_player is not None:
            return self.vlc_player.duration()
        return self.media_player.duration()
    
    @property
    def current_song(self):
        return self.current_song_info
    
    @property
    def playlist_count(self):
        return len(self.playlist)
    
    @property
    def has_next(self):
        return self._get_next_song_index() != -1
    
    @property
    def has_previous(self):
        return self._get_previous_song_index() != -1
    
    @staticmethod
    def format_time(milliseconds):
        if milliseconds <= 0:
            return "00:00"
        
        total_seconds = milliseconds // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        
        return f"{minutes:02d}:{seconds:02d}"
    
    @staticmethod
    def format_detailed_time(milliseconds):
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
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    
    def cleanup(self):
        logger.info("清理音频播放器资源")
        
        self.save_player_settings()
        
        self.stop()
        
        # 清理VLC播放器
        if self.vlc_player is not None:
            try:
                self.vlc_player.cleanup()
            except Exception as e:
                logger.error(f"清理VLC播放器时出错: {e}")
        
        # 清理Pygame播放器
        if self.pygame_player is not None:
            try:
                self.pygame_player.cleanup()
            except Exception as e:
                logger.error(f"清理Pygame播放器时出错: {e}")
        
        try:
            self.media_player.stateChanged.disconnect()
            self.media_player.positionChanged.disconnect()
            self.media_player.durationChanged.disconnect()
            self.media_player.mediaStatusChanged.disconnect()
            self.media_player.volumeChanged.disconnect()
        except:
            pass
        
        self.media_player.setMedia(QMediaContent())
        
        logger.info("音频播放器资源清理完成")


class PygamePlayer(QObject):
    """Pygame播放器实现，作为QMediaPlayer的备用方案"""
    
    state_changed = pyqtSignal(int)
    position_changed = pyqtSignal(int)
    duration_changed = pyqtSignal(int)
    media_status_changed = pyqtSignal(int)
    volume_changed = pyqtSignal(int)
    error_occurred = pyqtSignal(str)
    
    # 状态常量，与QMediaPlayer保持一致
    StoppedState = 0
    PlayingState = 1
    PausedState = 2
    
    # 媒体状态常量
    NoMedia = 0
    LoadingMedia = 1
    LoadedMedia = 2
    StalledMedia = 3
    BufferingMedia = 4
    BufferedMedia = 5
    EndOfMedia = 6
    InvalidMedia = 7
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        if not PYGAME_AVAILABLE:
            raise ImportError("pygame 库不可用")
        
        # 初始化pygame mixer
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
            logger.info("Pygame mixer初始化成功")
        except Exception as e:
            logger.error(f"Pygame mixer初始化失败: {e}")
            raise
        
        self._current_file = None
        self._current_position = 0
        self._duration = 0  # 未知时长
        self._volume = 80
        self._state = self.StoppedState
        self._media_status = self.NoMedia
        
        self.position_timer = QTimer()
        self.position_timer.timeout.connect(self._update_position)
        self.position_timer.setInterval(100)  # 每100ms更新一次位置
        
        logger.info("Pygame播放器初始化完成")
    
    def _update_position(self):
        try:
            if self._state in [self.PlayingState, self.PausedState]:
                try:
                    # pygame.mixer.music.get_pos() 返回已播放的毫秒数
                    position = pygame.mixer.music.get_pos()
                    if position >= 0:
                        self._current_position = position
                        self.position_changed.emit(position)
                    
                    # 检查是否播放结束（pygame.mixer.music.get_busy() 返回False）
                    if not pygame.mixer.music.get_busy() and self._state == self.PlayingState:
                        logger.debug("Pygame播放结束检测")
                        self._state = self.StoppedState
                        self.state_changed.emit(self._state)
                        self.media_status_changed.emit(self.EndOfMedia)
                        self.position_timer.stop()
                except Exception as e:
                    logger.debug(f"获取Pygame播放器位置时出错: {e}")
            else:
                self.position_timer.stop()
        except Exception as e:
            logger.debug(f"更新Pygame播放器位置时出错: {e}")
    
    def setMedia(self, media_content):
        if not media_content or media_content.isNull():
            self._current_file = None
            self._media_status = self.NoMedia
            return
        
        try:
            url = media_content.canonicalUrl()
            if url.isLocalFile():
                file_path = url.toLocalFile()
            else:
                # 不支持网络URL
                logger.error("Pygame播放器不支持网络URL")
                self._media_status = self.InvalidMedia
                self.media_status_changed.emit(self.InvalidMedia)
                self.error_occurred.emit("Pygame播放器不支持网络URL")
                return False
            
            # 停止当前播放
            pygame.mixer.music.stop()
            self._state = self.StoppedState
            
            # 加载新文件
            try:
                pygame.mixer.music.load(file_path)
                self._current_file = file_path
                self._media_status = self.LoadedMedia
                self.media_status_changed.emit(self.LoadedMedia)
                self._duration = 0  # 重置时长
                self._current_position = 0
                logger.debug(f"Pygame设置媒体: {file_path}")
                return True
            except Exception as e:
                logger.error(f"Pygame加载媒体失败: {e}")
                self._media_status = self.InvalidMedia
                self.media_status_changed.emit(self.InvalidMedia)
                self.error_occurred.emit(f"Pygame加载媒体失败: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"Pygame设置媒体失败: {e}")
            self._media_status = self.InvalidMedia
            self.media_status_changed.emit(self.InvalidMedia)
            self.error_occurred.emit(f"Pygame设置媒体失败: {str(e)}")
            return False
    
    def play(self):
        try:
            pygame.mixer.music.play()
            self._state = self.PlayingState
            self.state_changed.emit(self._state)
            self.position_timer.start()
            self._media_status = self.BufferedMedia
            self.media_status_changed.emit(self.BufferedMedia)
            logger.debug("Pygame开始播放")
            return True
        except Exception as e:
            logger.error(f"Pygame播放异常: {e}")
            self._state = self.StoppedState
            self.state_changed.emit(self._state)
            self._media_status = self.InvalidMedia
            self.media_status_changed.emit(self.InvalidMedia)
            self.error_occurred.emit(f"Pygame播放异常: {str(e)}")
            return False
    
    def pause(self):
        if self._state == self.PlayingState:
            pygame.mixer.music.pause()
            self._state = self.PausedState
            self.state_changed.emit(self._state)
            logger.debug("Pygame暂停")
    
    def stop(self):
        pygame.mixer.music.stop()
        self._state = self.StoppedState
        self.state_changed.emit(self._state)
        self.position_timer.stop()
        self._current_position = 0
        self._media_status = self.NoMedia
        self.media_status_changed.emit(self.NoMedia)
        logger.debug("Pygame停止")
    
    def setPosition(self, position):
        try:
            # pygame.mixer.music.set_pos() 需要秒数，且可能不支持所有格式
            # 这里我们使用rewind和播放来实现定位
            if self._current_file and self._state != self.StoppedState:
                # 停止当前播放
                pygame.mixer.music.stop()
                # 重新加载并设置位置
                pygame.mixer.music.load(self._current_file)
                # 计算秒数
                seconds = position / 1000.0
                # 播放并跳过指定位置
                pygame.mixer.music.play()
                pygame.mixer.music.set_pos(seconds)
                self._current_position = position
                self.position_changed.emit(position)
                logger.debug(f"Pygame设置位置: {position}ms")
        except Exception as e:
            logger.error(f"Pygame设置位置失败: {e}")
            # 即使设置失败，也尝试更新UI位置
            self._current_position = position
            self.position_changed.emit(position)
    
    def position(self):
        return self._current_position
    
    def duration(self):
        return self._duration
    
    def volume(self):
        return self._volume
    
    def setVolume(self, volume):
        volume = max(0, min(100, volume))
        self._volume = volume
        # pygame.mixer.music.set_volume 接受0.0到1.0的值
        pygame.mixer.music.set_volume(volume / 100.0)
        self.volume_changed.emit(volume)
        logger.debug(f"Pygame设置音量: {volume}")
    
    def state(self):
        return self._state
    
    def mediaStatus(self):
        return self._media_status
    
    def isSeekable(self):
        # pygame.mixer.music支持有限的定位功能
        return True
    
    def cleanup(self):
        logger.info("清理Pygame播放器资源")
        self.position_timer.stop()
        try:
            pygame.mixer.music.stop()
            pygame.mixer.quit()
        except Exception as e:
            logger.error(f"清理Pygame播放器资源时出错: {e}")
        logger.info("Pygame播放器资源清理完成")


class VLCPlayer(QObject):
    """VLC播放器实现，作为QMediaPlayer的备用方案"""
    
    state_changed = pyqtSignal(int)
    position_changed = pyqtSignal(int)
    duration_changed = pyqtSignal(int)
    media_status_changed = pyqtSignal(int)
    volume_changed = pyqtSignal(int)
    error_occurred = pyqtSignal(str)
    
    # 状态常量，与QMediaPlayer保持一致
    StoppedState = 0
    PlayingState = 1
    PausedState = 2
    
    # 媒体状态常量
    NoMedia = 0
    LoadingMedia = 1
    LoadedMedia = 2
    StalledMedia = 3
    BufferingMedia = 4
    BufferedMedia = 5
    EndOfMedia = 6
    InvalidMedia = 7
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        if not VLC_AVAILABLE:
            raise ImportError("python-vlc 库不可用")
        
        self.instance = None
        self.player = None
        
        try:
            # 尝试多种初始化策略
            init_success = False
            
            # 策略1: 使用最小参数初始化（解决解码器问题）
            try:
                vlc_args = ["--quiet"]  # 只使用quiet参数，避免无效参数导致初始化失败
                logger.info(f"尝试使用参数初始化VLC实例: {vlc_args}")
                self.instance = vlc.Instance(vlc_args)
                if self.instance is not None:
                    self.player = self.instance.media_player_new()
                    if self.player is not None:
                        init_success = True
                        logger.info("VLC实例创建成功（使用参数）")
            except Exception as e1:
                logger.warning(f"使用参数初始化VLC失败: {e1}")
                # 继续尝试其他策略
            
            # 策略2: 不使用参数初始化（兼容性更好）
            if not init_success:
                try:
                    logger.info("尝试不使用参数初始化VLC实例")
                    self.instance = vlc.Instance()
                    if self.instance is not None:
                        self.player = self.instance.media_player_new()
                        if self.player is not None:
                            init_success = True
                            logger.info("VLC实例创建成功（无参数）")
                except Exception as e2:
                    logger.warning(f"无参数初始化VLC失败: {e2}")
            
            # 策略3: 尝试使用空参数列表
            if not init_success:
                try:
                    empty_args = []  # 空参数列表
                    logger.info(f"尝试使用空参数列表初始化VLC实例: {empty_args}")
                    self.instance = vlc.Instance(empty_args)
                    if self.instance is not None:
                        self.player = self.instance.media_player_new()
                        if self.player is not None:
                            init_success = True
                            logger.info("VLC实例创建成功（空参数列表）")
                except Exception as e3:
                    logger.warning(f"空参数列表初始化VLC失败: {e3}")
            
            # 如果所有策略都失败
            if not init_success:
                raise RuntimeError("无法创建VLC实例，所有初始化策略都失败")
                
        except Exception as e:
            logger.error(f"VLC播放器初始化失败: {e}")
            self.instance = None
            self.player = None
            raise
        
        self._current_media = None
        self._current_position = 0
        self._duration = 0
        self._volume = 80
        self._state = self.StoppedState
        self._media_status = self.NoMedia
        
        self.position_timer = QTimer()
        self.position_timer.timeout.connect(self._update_position)
        self.position_timer.setInterval(100)  # 每100ms更新一次位置
        
        # 连接播放结束事件
        if self.player is not None:
            try:
                self.player.event_manager().event_attach(
                    vlc.EventType.MediaPlayerEndReached,
                    self._on_media_end
                )
                logger.debug("VLC播放结束事件连接成功")
            except Exception as e:
                logger.warning(f"连接VLC播放结束事件失败: {e}")
        else:
            logger.warning("VLC播放器实例为None，无法连接事件")
        
        logger.info("VLC播放器初始化完成")
    
    def _update_position(self):
        try:
            # 检查player是否可用
            if self.player is None:
                logger.debug("VLC播放器不可用，停止位置定时器")
                self.position_timer.stop()
                return
            
            # 即使播放器不在播放状态，也尝试获取位置信息
            # 这对于处理解码器错误但仍然能获取时间信息的场景很重要
            if self._state in [self.PlayingState, self.PausedState]:
                try:
                    position = self.player.get_time()  # 毫秒
                    duration = self.player.get_length()  # 毫秒
                    
                    # 调试日志：记录获取到的位置和时长
                    logger.debug(f"VLC位置获取 - 位置: {position}ms, 时长: {duration}ms, 状态: {self._state}")
                    
                    if position >= 0:
                        self._current_position = position
                        self.position_changed.emit(position)
                    
                    if duration > 0 and duration != self._duration:
                        self._duration = duration
                        self.duration_changed.emit(duration)
                except Exception as e:
                    # 如果获取位置失败，记录调试信息但不中断定时器
                    logger.debug(f"获取VLC播放器位置时出错: {e}")
                    
                    # 如果播放器在播放状态但无法获取位置，可能是解码器问题
                    # 尝试发出一个位置信号以保持UI响应
                    if self._state == self.PlayingState and self._duration > 0:
                        # 如果没有有效位置，使用估计的位置
                        estimated_position = self._current_position + 100  # 增加100ms
                        if estimated_position < self._duration:
                            self._current_position = estimated_position
                            self.position_changed.emit(estimated_position)
            else:
                # 停止状态，停止定时器
                self.position_timer.stop()
        except Exception as e:
            logger.debug(f"更新VLC播放器位置时出错: {e}")
    
    def _on_media_end(self, event):
        logger.debug(f"VLC媒体播放结束，发出EndOfMedia状态: {self.EndOfMedia}")
        self._state = self.StoppedState
        self.state_changed.emit(self._state)
        self.media_status_changed.emit(self.EndOfMedia)
    
    def setMedia(self, media_content):
        if not media_content or media_content.isNull():
            self._current_media = None
            self._media_status = self.NoMedia
            return
        
        # 检查VLC实例和播放器是否可用
        if self.instance is None or self.player is None:
            logger.error("VLC设置媒体失败: VLC实例或播放器不可用")
            self._media_status = self.InvalidMedia
            self.media_status_changed.emit(self.InvalidMedia)
            self.error_occurred.emit("VLC实例或播放器不可用")
            return False
        
        try:
            url = media_content.canonicalUrl()
            if url.isLocalFile():
                file_path = url.toLocalFile()
                media = self.instance.media_new(file_path)
            else:
                media = self.instance.media_new(url.toString())
            
            self.player.set_media(media)
            self._current_media = media
            self._media_status = self.LoadedMedia
            self.media_status_changed.emit(self.LoadedMedia)
            
            logger.debug(f"VLC设置媒体: {url.toString()}")
            return True
        except Exception as e:
            logger.error(f"VLC设置媒体失败: {e}")
            self._media_status = self.InvalidMedia
            self.media_status_changed.emit(self.InvalidMedia)
            self.error_occurred.emit(f"VLC设置媒体失败: {str(e)}")
            return False
    
    def play(self):
        try:
            if self.player is None:
                logger.error("VLC播放失败: 播放器实例不可用")
                self.error_occurred.emit("VLC播放器实例不可用")
                return False
            
            if self.player.play() == 0:
                self._state = self.PlayingState
                self.state_changed.emit(self._state)
                self.position_timer.start()
                self._media_status = self.BufferedMedia
                self.media_status_changed.emit(self.BufferedMedia)
                logger.debug("VLC开始播放")
                return True
            else:
                logger.error("VLC播放失败")
                self._state = self.StoppedState
                self.state_changed.emit(self._state)
                self._media_status = self.InvalidMedia
                self.media_status_changed.emit(self.InvalidMedia)
                self.error_occurred.emit("VLC播放失败")
                return False
        except Exception as e:
            logger.error(f"VLC播放异常: {e}")
            self.error_occurred.emit(f"VLC播放异常: {str(e)}")
            return False
    
    def pause(self):
        if self.player is None:
            logger.warning("VLC暂停失败: 播放器实例不可用")
            return
        
        if self._state == self.PlayingState:
            self.player.pause()
            self._state = self.PausedState
            self.state_changed.emit(self._state)
            logger.debug("VLC暂停")
    
    def stop(self):
        if self.player is None:
            logger.warning("VLC停止失败: 播放器实例不可用")
            return
        
        self.player.stop()
        self._state = self.StoppedState
        self.state_changed.emit(self._state)
        self.position_timer.stop()
        self._current_position = 0
        self._media_status = self.NoMedia
        self.media_status_changed.emit(self.NoMedia)
        logger.debug("VLC停止")
    
    def setPosition(self, position):
        try:
            # 检查播放器是否可用
            if self.player is None:
                logger.warning("VLC设置位置失败: 播放器实例不可用")
                # 即使播放器不可用，也尝试更新UI位置
                if 0 <= position <= (self._duration if self._duration > 0 else position + 1000):
                    self._current_position = position
                    self.position_changed.emit(position)
                return
            
            # 边界检查：确保位置在有效范围内
            if position < 0:
                position = 0
            if self._duration > 0 and position > self._duration:
                position = self._duration
            
            # 检查播放器是否支持定位
            if not self.isSeekable():
                logger.warning("VLC设置位置失败: 媒体不支持定位")
                return
            
            # 设置位置
            self.player.set_time(position)
            self._current_position = position
            
            # 立即发出位置变化信号，更新UI
            self.position_changed.emit(position)
            logger.debug(f"VLC设置位置: {position}ms")
            
            # 如果播放器在暂停状态，设置位置后可能需要重新启动定时器
            if self._state == self.PausedState and not self.position_timer.isActive():
                self.position_timer.start()
                
        except Exception as e:
            logger.error(f"VLC设置位置失败: {e}")
            # 即使设置失败，也尝试更新UI位置
            if 0 <= position <= (self._duration if self._duration > 0 else position + 1000):
                self._current_position = position
                self.position_changed.emit(position)
    
    def position(self):
        return self._current_position
    
    def duration(self):
        return self._duration
    
    def setVolume(self, volume):
        try:
            volume = max(0, min(100, volume))
            self.player.audio_set_volume(volume)
            self._volume = volume
            self.volume_changed.emit(volume)
            logger.debug(f"VLC设置音量: {volume}")
        except Exception as e:
            logger.error(f"VLC设置音量失败: {e}")
    
    def volume(self):
        return self._volume
    
    def state(self):
        return self._state
    
    def mediaStatus(self):
        return self._media_status
    
    def isSeekable(self):
        try:
            if self.player is None:
                return False
            return self.player.is_seekable()
        except:
            return False
    
    def cleanup(self):
        logger.info("清理VLC播放器资源")
        self.position_timer.stop()
        
        # 清理播放器资源
        if self.player is not None:
            try:
                self.player.event_manager().event_detach(vlc.EventType.MediaPlayerEndReached)
            except:
                pass
            try:
                self.player.release()
            except:
                pass
            self.player = None
        
        # 清理实例资源
        if self.instance is not None:
            try:
                self.instance.release()
            except:
                pass
            self.instance = None
        
        logger.info("VLC播放器资源清理完成")


class SimpleAudioPlayer(AudioPlayer):
    """简化版音频播放器，提供更简单的接口"""
    
    def __init__(self, settings=None, parent=None):
        super().__init__(settings, parent)
        
        self.auto_play_next = True
        self.loop_single = False
    
    def play_file(self, file_path):
        return self.play_audio(file_path)
    
    def next_track(self):
        return self.play_next()
    
    def prev_track(self):
        return self.play_previous()
    
    def toggle_loop(self):
        self.loop_single = not self.loop_single
        if self.loop_single:
            self.set_play_mode(2)
        else:
            self.set_play_mode(0)
        return self.loop_single


class AudioPlayerManager(QObject):
    """音频播放器管理器，管理多个播放器实例"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.players = {}
        self.default_player = None
        self.current_player = None
        
        logger.info("音频播放器管理器初始化")
    
    def create_player(self, name="default", settings=None):
        if name in self.players:
            logger.warning(f"播放器已存在: {name}")
            return self.players[name]
        
        player = AudioPlayer(settings, self)
        self.players[name] = player
        
        if self.default_player is None:
            self.default_player = player
            self.current_player = player
        
        logger.info(f"创建播放器: {name}")
        return player
    
    def get_player(self, name="default"):
        return self.players.get(name)
    
    def set_current_player(self, name):
        if name in self.players:
            self.current_player = self.players[name]
            logger.info(f"设置当前播放器: {name}")
            return True
        return False
    
    def remove_player(self, name):
        if name in self.players:
            player = self.players.pop(name)
            player.cleanup()
            
            if player == self.current_player:
                if self.players:
                    self.current_player = next(iter(self.players.values()))
                else:
                    self.current_player = None
            
            logger.info(f"移除播放器: {name}")
            return True
        return False
    
    def cleanup_all(self):
        logger.info("清理所有播放器")
        
        for name, player in list(self.players.items()):
            player.cleanup()
        
        self.players.clear()
        self.default_player = None
        self.current_player = None
        
        logger.info("所有播放器已清理")


def create_audio_player(player_type="default", settings=None, name="default", manager=None):
    if player_type == "simple":
        player = SimpleAudioPlayer(settings)
    else:
        player = AudioPlayer(settings)
    
    if manager and isinstance(manager, AudioPlayerManager):
        if name in manager.players:
            logger.warning(f"播放器名称已存在，将使用新名称: {name}_new")
            name = f"{name}_new"
        
        manager.players[name] = player
        if manager.current_player is None:
            manager.current_player = player
    
    return player
