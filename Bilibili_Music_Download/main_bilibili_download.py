#!/usr/bin/env python3
"""Bilibili音乐下载模块 - 集成B站音频下载功能"""

import random
import sys
import os
import re
import logging
import asyncio
import time
import traceback
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler
from typing import Optional, Dict
import json

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# 第三方库导入
try:
    import httpx
    import aiofiles
    from bs4 import BeautifulSoup
    REQUIRED_LIBS_AVAILABLE = True
except ImportError as e:
    print(f"缺少依赖库: {e}")
    print("请安装所需依赖: pip install httpx aiofiles beautifulsoup4")
    REQUIRED_LIBS_AVAILABLE = False

from PyQt5.QtCore import (
    QObject, QThread, Qt, pyqtSignal, QSize, QEvent
)
from PyQt5.QtGui import (
    QFont, QIcon, QPixmap, QCursor
)
from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QMessageBox, QProgressBar, QFrame, QFileDialog, QWidget
)

# 导入RAILGUN的日志和设置系统
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from settings_manager import ConfigManager
    from Music_Download.crawler import load_settings, save_settings
except ImportError:
    # 如果无法导入，创建替代函数
    def load_settings():
        return {
            "save_paths": {
                "music": os.path.join(os.path.expanduser("~"), "Music"),
                "cache": os.path.join(get_base_path(), "cache")
            }
        }
    def save_settings(settings_dict):
        """简单的回退保存实现：写入项目上层目录下的 `bilibili_settings.json` 文件。"""
        try:
            base = get_base_path()
            path = os.path.join(base, "bilibili_settings.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(settings_dict, f, ensure_ascii=False, indent=4)
            logger.info(f"回退保存设置到: {path}")
        except Exception:
            logger.error("回退保存设置失败:\n" + traceback.format_exc())

def setup_logging():
    """设置日志记录，同时输出到控制台和文件"""
    base_dir = get_base_path()
    log_dir = os.path.join(base_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, "bilibili_download.log")
    
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    
    if logger.handlers:
        logger.handlers.clear()
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    file_handler = TimedRotatingFileHandler(
        log_file, when='midnight', interval=1, backupCount=7, encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

logger = setup_logging()

class ModernButton(QPushButton):
    """现代化按钮样式"""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(42)
        self.setFont(QFont("Microsoft YaHei UI", 11, QFont.Medium))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #EF4444, stop:1 #FB7185);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 20px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #DC2626, stop:1 #F43F5E);
            }
            QPushButton:pressed {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #B91C1C, stop:1 #E11D48);
            }
            QPushButton:disabled {
                background-color: #CBD5E1;
                color: #94A3B8;
            }
        """)

class ModernLineEdit(QLineEdit):
    """现代化输入框样式"""
    def __init__(self, placeholder="", parent=None):
        super().__init__(placeholder, parent)
        self.setFont(QFont("Microsoft YaHei UI", 11))
        self.setStyleSheet("""
            QLineEdit {
                background-color: white;
                border: 2px solid #E1E5E9;
                border-radius: 10px;
                padding: 12px 16px;
                font-size: 14px;
                color: #1E293B;
                selection-background-color: #EF4444;
                selection-color: white;
            }
            QLineEdit:focus {
                border-color: #EF4444;
                background-color: #FFFFFF;
            }
            QLineEdit:hover {
                border-color: #CBD5E1;
                background-color: #FEFEFF;
            }
            QLineEdit::placeholder {
                color: #94A3B8;
            }
        """)

class BilibiliAudioAPI(QObject):
    """B站音频API类（修改版）"""
    download_progress = pyqtSignal(int)
    
    def __init__(self, cookie: str = "", parent=None):
        super().__init__(parent)
        self.BILIBILI_SEARCH_API = "https://api.bilibili.com/x/web-interface/search/type"
        self.BILIBILI_HEADER = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com",
            "Origin": "https://www.bilibili.com",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "Cookie": cookie,
        }
        self.audio_info_cache = {}
        self.cookie = cookie
        self.retry_strategy = {
            "max_retries": 3,
            "base_delay": 1.0,
            "max_delay": 10.0,
            "backoff_factor": 1.5
        }
        self.request_count = 0
        self.last_request_time = 0
        self.min_request_interval = 0.5  # 最小请求间隔（秒）
    
    async def _rate_limit(self):
        """速率限制控制"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_request_interval:
            wait_time = self.min_request_interval - time_since_last
            logger.debug(f"速率限制：等待 {wait_time:.2f} 秒")
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
        
        # 每10个请求增加一点延迟
        if self.request_count % 10 == 0:
            self.min_request_interval = min(self.min_request_interval + 0.1, 2.0)
            logger.debug(f"调整最小请求间隔为: {self.min_request_interval}")
    
    async def _calculate_retry_delay(self, attempt: int) -> float:
        """计算重试延迟，使用指数退避策略"""
        delay = self.retry_strategy["base_delay"] * (self.retry_strategy["backoff_factor"] ** attempt)
        delay = min(delay, self.retry_strategy["max_delay"])
        # 添加随机抖动
        jitter = delay * 0.1 * (random.random() * 2 - 1)
        delay = max(0.5, delay + jitter)
        logger.debug(f"第 {attempt+1} 次重试延迟: {delay:.2f} 秒")
        return delay
    
    async def search_video(self, keyword: str, page: int = 1) -> list:
        """搜索视频"""
        params = {"search_type": "video", "keyword": keyword, "page": page}
        
        max_retries = self.retry_strategy["max_retries"]
        
        for attempt in range(max_retries):
            try:
                await self._rate_limit()
                
                async with httpx.AsyncClient() as client:
                    # 添加随机延迟，模拟人类行为
                    if attempt > 0:
                        delay = await self._calculate_retry_delay(attempt)
                        await asyncio.sleep(delay)
                    
                    response = await client.get(
                        self.BILIBILI_SEARCH_API, 
                        params=params, 
                        headers=self.BILIBILI_HEADER,
                        timeout=30.0
                    )
                    
                    # 检查412错误（B站风控）
                    if response.status_code == 412:
                        logger.warning(f"B站风控拦截（412），尝试 {attempt + 1}/{max_retries}")
                        if attempt < max_retries - 1:
                            continue
                        else:
                            logger.error("B站风控拦截，所有重试均失败")
                            return []
                    
                    response.raise_for_status()
                    data = response.json()
                    
                    if data["code"] == 0:
                        video_list = data["data"].get("result", [])
                        logger.info(f"B站搜索成功，找到 {len(video_list)} 个视频")
                        return video_list
                    else:
                        logger.error(f"B站搜索API返回错误: {data.get('message', '未知错误')}")
                        # 如果是特定的API错误，也尝试重试
                        if data.get("code") in [412, 429] and attempt < max_retries - 1:
                            logger.warning(f"API返回错误码 {data.get('code')}，尝试重试")
                            continue
                        return []
                        
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 412:
                    logger.warning(f"HTTP 412错误（B站风控），尝试 {attempt + 1}/{max_retries}")
                    if attempt < max_retries - 1:
                        continue
                    else:
                        logger.error("B站风控拦截，所有重试均失败")
                        return []
                else:
                    logger.error(f"B站搜索HTTP错误 {e.response.status_code}: {str(e)}")
                    if attempt < max_retries - 1:
                        logger.warning(f"HTTP错误，尝试重试 {attempt + 1}/{max_retries}")
                        continue
                    return []
                    
            except Exception as e:
                logger.error(f"B站搜索发生错误: {str(e)}")
                if attempt < max_retries - 1:
                    logger.warning(f"尝试重试 {attempt + 1}/{max_retries}")
                    continue
                logger.error(f"异常详情:\n{traceback.format_exc()}")
                return []
        
        return []  # 所有重试都失败
    
    async def get_audio_info(self, bvid: str) -> Optional[Dict]:
        """获取音频信息（包含真实音频URL）"""
        if bvid in self.audio_info_cache:
            return self.audio_info_cache[bvid]
        
        max_retries = self.retry_strategy["max_retries"]
        
        for attempt in range(max_retries):
            try:
                await self._rate_limit()
                
                if attempt > 0:
                    delay = await self._calculate_retry_delay(attempt)
                    await asyncio.sleep(delay)
                
                video_info_url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
                async with httpx.AsyncClient() as client:
                    response = await client.get(video_info_url, headers=self.BILIBILI_HEADER, timeout=30.0)
                    
                    # 检查412错误（B站风控）
                    if response.status_code == 412:
                        logger.warning(f"获取视频信息时B站风控拦截（412），尝试 {attempt + 1}/{max_retries}")
                        if attempt < max_retries - 1:
                            continue
                        else:
                            logger.error("B站风控拦截，所有重试均失败")
                            return None
                    
                    data = response.json()
                    if data["code"] != 0:
                        logger.error(f"获取视频信息失败: {data.get('message', '未知错误')}")
                        # 如果是风控错误，尝试重试
                        if data.get("code") in [412, 429] and attempt < max_retries - 1:
                            logger.warning(f"视频信息API返回错误码 {data.get('code')}，尝试重试")
                            continue
                        return None
                    
                    cid = data["data"]["cid"]
                    title = data["data"]["title"]
                    author = data["data"]["owner"]["name"]
                    duration = data["data"]["duration"]
                    cover_url = data["data"]["pic"]
                    
                    audio_url = f"https://api.bilibili.com/x/player/playurl?bvid={bvid}&cid={cid}&qn=0&fnval=16"
                    response = await client.get(audio_url, headers=self.BILIBILI_HEADER, timeout=30.0)
                    
                    # 检查412错误（B站风控）
                    if response.status_code == 412:
                        logger.warning(f"获取音频URL时B站风控拦截（412），尝试 {attempt + 1}/{max_retries}")
                        if attempt < max_retries - 1:
                            continue
                        else:
                            logger.error("B站风控拦截，所有重试均失败")
                            return None
                    
                    data = response.json()
                    if data["code"] != 0:
                        logger.error(f"获取音频URL失败: {data.get('message', '未知错误')}")
                        # 如果是风控错误，尝试重试
                        if data.get("code") in [412, 429] and attempt < max_retries - 1:
                            logger.warning(f"音频URL API返回错误码 {data.get('code')}，尝试重试")
                            continue
                        return None
                    
                    if "dash" not in data["data"] or "audio" not in data["data"]["dash"]:
                        logger.error(f"音频格式不支持: {data}")
                        return None
                    
                    audio_url = data["data"]["dash"]["audio"][0]["baseUrl"]
                    audio_info = {
                        "title": title,
                        "author": author,
                        "duration": duration,
                        "cover_url": cover_url,
                        "audio_url": audio_url
                    }
                    self.audio_info_cache[bvid] = audio_info
                    logger.info(f"获取音频信息成功: {title}")
                    return audio_info
                    
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 412:
                    logger.warning(f"HTTP 412错误（B站风控），尝试 {attempt + 1}/{max_retries}")
                    if attempt < max_retries - 1:
                        continue
                    else:
                        logger.error("B站风控拦截，所有重试均失败")
                        return None
                else:
                    logger.error(f"获取音频信息HTTP错误 {e.response.status_code}: {str(e)}")
                    if attempt < max_retries - 1:
                        logger.warning(f"HTTP错误，尝试重试 {attempt + 1}/{max_retries}")
                        continue
                    return None
                    
            except Exception as e:
                logger.error(f"获取音频信息失败: {str(e)}")
                if attempt < max_retries - 1:
                    logger.warning(f"尝试重试 {attempt + 1}/{max_retries}")
                    continue
                logger.error(f"异常详情:\n{traceback.format_exc()}")
                return None
        
        return None  # 所有重试都失败
    
    async def download_audio(self, bvid: str, file_path: str, search_keyword: Optional[str] = None) -> bool:
        """下载B站音频并保存到指定路径，使用搜索关键词重命名"""
        try:
            logger.info(f"开始下载音频: bvid={bvid}, 目标路径={file_path}, 搜索关键词={search_keyword}")
            
            audio_info = await self.get_audio_info(bvid)
            if not audio_info:
                logger.error("获取音频信息失败")
                return False
            
            directory = os.path.dirname(file_path)
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            
            # 使用搜索关键词作为文件名（如果提供）
            if search_keyword and search_keyword.strip():
                safe_name = self.safe_filename(search_keyword.strip())  # type: ignore
                logger.info(f"使用搜索关键词作为文件名: {safe_name}")
            else:
                # 否则使用视频标题
                title = audio_info["title"]
                safe_name = self.safe_filename(title)  # type: ignore
                logger.info(f"使用视频标题作为文件名: {safe_name}")
            
            # 下载音频文件
            audio_url = audio_info["audio_url"]
            temp_file = os.path.join(directory, f"temp_{safe_name}")
            
            success = await self._download_audio_file(audio_url, temp_file)
            if not success:
                logger.error("下载音频文件失败")
                return False
            
            # 确定文件扩展名
            content_type = await self.get_content_type(audio_url)  # type: ignore
            if 'm4a' in content_type:
                ext = '.m4a'
            elif 'mp3' in content_type:
                ext = '.mp3'
            elif 'flac' in content_type:
                ext = '.flac'
            else:
                ext = '.m4a'  # 默认使用m4a
            
            # 构建最终文件名
            final_path = os.path.join(directory, f"{safe_name}{ext}")
            logger.info(f"最终保存路径: {final_path}")
            
            # 重命名文件
            if os.path.exists(temp_file):
                os.rename(temp_file, final_path)
                logger.info(f"文件重命名成功: {temp_file} -> {final_path}")
                return True
            
            logger.error(f"临时文件不存在: {temp_file}")
            return False
            
        except Exception as e:
            logger.error(f"下载音频失败: {str(e)}")
            logger.error(f"异常详情:\n{traceback.format_exc()}")
            return False
    
    async def _download_audio_file(self, url: str, file_path: str) -> bool:
        """下载音频文件到指定路径"""
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "GET", url, headers=self.BILIBILI_HEADER, timeout=60.0
                ) as response:
                    if response.status_code != 200:
                        logger.error(f"下载请求失败，状态码: {response.status_code}")
                        return False
                    
                    total_size = int(response.headers.get("content-length", 0))
                    downloaded = 0
                    
                    async with aiofiles.open(file_path, "wb") as f:
                        async for chunk in response.aiter_bytes():
                            thread_obj = self.thread()
                            if thread_obj and thread_obj.isInterruptionRequested():
                                logger.info("下载被中断")
                                return False
                            
                            downloaded += len(chunk)
                            await f.write(chunk)
                            
                            # 发射下载进度
                            if total_size > 0:
                                progress = int(downloaded / total_size * 100)
                                self.download_progress.emit(progress)
                    
                    logger.info(f"文件下载完成: {file_path}, 大小: {downloaded} bytes")
                    return True
        except Exception as e:
            logger.error(f"下载文件失败: {str(e)}")
            logger.error(f"异常详情:\n{traceback.format_exc()}")
            return False
    
    async def get_content_type(self, url: str) -> str:
        """获取URL的内容类型"""
        max_retries = self.retry_strategy["max_retries"]
        
        for attempt in range(max_retries):
            try:
                await self._rate_limit()
                
                if attempt > 0:
                    delay = await self._calculate_retry_delay(attempt)
                    await asyncio.sleep(delay)
                
                async with httpx.AsyncClient() as client:
                    response = await client.head(url, headers=self.BILIBILI_HEADER, timeout=10.0)
                    
                    # 检查412错误（B站风控）
                    if response.status_code == 412:
                        logger.warning(f"获取内容类型时B站风控拦截（412），尝试 {attempt + 1}/{max_retries}")
                        if attempt < max_retries - 1:
                            continue
                        else:
                            logger.error("B站风控拦截，所有重试均失败")
                            return ""
                    
                    return response.headers.get("content-type", "")
                    
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 412 and attempt < max_retries - 1:
                    logger.warning(f"HTTP 412错误（B站风控），尝试 {attempt + 1}/{max_retries}")
                    continue
                logger.error(f"获取内容类型HTTP错误 {e.response.status_code}: {str(e)}")
                return ""
                
            except Exception as e:
                logger.error(f"获取内容类型失败: {str(e)}")
                if attempt < max_retries - 1:
                    logger.warning(f"尝试重试 {attempt + 1}/{max_retries}")
                    continue
                return ""
        
        return ""  # 所有重试都失败
    
    def safe_filename(self, filename: str) -> str:
        """确保文件名安全，移除非法字符"""
        if not filename:
            return "unknown"
        
        # 移除非法字符
        illegal_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in illegal_chars:
            filename = filename.replace(char, '_')
        
        # 移除控制字符
        filename = ''.join(char for char in filename if ord(char) >= 32)
        
        # 限制文件名长度
        if len(filename) > 100:
            filename = filename[:100]
        
        # 确保文件名不为空
        if not filename.strip():
            filename = "bilibili_audio"
        
        logger.debug(f"安全文件名转换: {filename}")
        return filename.strip()

class BilibiliSearchThread(QThread):
    """B站搜索线程"""
    results_ready = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, keyword, audio_api):
        super().__init__()
        self.keyword = keyword
        self.audio_api = audio_api
        
    def run(self):
        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            if self.isInterruptionRequested():
                return
            results = loop.run_until_complete(self.audio_api.search_video(self.keyword))
            if self.isInterruptionRequested():
                return
            self.results_ready.emit(results or [])
        except Exception as e:
            error_msg = f"搜索失败: {str(e)}"
            logger.error(error_msg)
            logger.error(f"异常详情:\n{traceback.format_exc()}")
            
            # 为412错误提供更友好的错误消息
            if "412" in str(e) or "Precondition Failed" in str(e):
                friendly_msg = "B站安全风控拦截\n\n可能的原因：\n1. 搜索频率过高，请稍后重试\n2. 需要等待几分钟再尝试\n3. 可尝试更换搜索关键词\n\n错误详情：" + str(e)
                self.error_occurred.emit(friendly_msg)
            else:
                self.error_occurred.emit(str(e))
        finally:
            if loop and not loop.is_closed():
                loop.call_soon_threadsafe(loop.stop)
                loop.close()
    
    def stop(self):
        self.requestInterruption()
        self.quit()
        if not self.wait(2000):
            self.terminate()
            self.wait()

class BilibiliDownloadThread(QThread):
    """B站下载线程"""
    download_complete = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, bvid, file_path, audio_api, search_keyword):
        super().__init__()
        self.bvid = bvid
        self.file_path = file_path
        self.audio_api = audio_api
        self.search_keyword = search_keyword
        
    def run(self):
        loop = None
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            if self.isInterruptionRequested():
                return
            success = loop.run_until_complete(
                self.audio_api.download_audio(self.bvid, self.file_path, self.search_keyword)
            )
            if self.isInterruptionRequested():
                return
            if success:
                # 获取最终的保存路径
                directory = os.path.dirname(self.file_path)
                base_name = os.path.splitext(os.path.basename(self.file_path))[0]
                safe_name = self.audio_api.safe_filename(base_name)  # type: ignore
                
                # 尝试确定最终文件路径
                possible_exts = ['.m4a', '.mp3', '.flac']
                final_path = None
                
                for ext in possible_exts:
                    test_path = os.path.join(directory, f"{safe_name}{ext}")
                    if os.path.exists(test_path):
                        final_path = test_path
                        break
                
                if final_path:
                    self.download_complete.emit(final_path)
                else:
                    self.error_occurred.emit("下载完成但找不到文件")
            else:
                self.error_occurred.emit("音频下载失败")
                
        except Exception as e:
            error_msg = f"下载失败: {str(e)}"
            logger.error(error_msg)
            logger.error(f"异常详情:\n{traceback.format_exc()}")
            self.error_occurred.emit(str(e))
        finally:
            if loop and not loop.is_closed():
                loop.call_soon_threadsafe(loop.stop)
                loop.close()
    
    def stop(self):
        self.requestInterruption()
        self.quit()
        if not self.wait(2000):
            self.terminate()
            self.wait()

class BilibiliMusicDownloadWindow(QDialog):
    """B站音乐下载主窗口"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📺 B站音乐下载")
        self.setGeometry(100, 100, 900, 750)
        
        if not REQUIRED_LIBS_AVAILABLE:
            QMessageBox.critical(self, "错误", 
                "缺少必要的依赖库！\n请安装: pip install httpx aiofiles beautifulsoup4")
            self.close()
            return
        
        try:
            self.settings = load_settings()
            logger.info("B站音乐下载窗口初始化，设置加载成功")
            
            # 确保bilibili设置存在
            if "bilibili" not in self.settings:
                self.settings["bilibili"] = {
                    "cookie": "",
                    "max_duration": 600
                }
                save_settings(self.settings)
                logger.info("创建默认B站设置")
                
        except Exception as e:
            error_msg = f"加载设置失败: {str(e)}"
            logger.error(error_msg)
            logger.error(f"异常详情:\n{traceback.format_exc()}")
            self.settings = {
                "save_paths": {
                    "music": os.path.join(os.path.expanduser("~"), "Music"),
                    "cache": os.path.join(get_base_path(), "cache")
                },
                "bilibili": {
                    "cookie": "",
                    "max_duration": 600
                }
            }
        
        # 使用配置的cookie，强制转换为字符串以避免类型警告
        cookie = str(self.settings.get("bilibili", {}).get("cookie", ""))
        logger.info(f"使用B站cookie: {cookie[:30]}..." if cookie else "未配置B站cookie")
        
        self.audio_api = BilibiliAudioAPI(cookie, parent=self)
        self.audio_api.download_progress.connect(self.update_progress)
        
        self.search_thread = None
        self.download_thread = None
        self.search_results = []
        self.current_video = None
        self.search_keyword = ""  # 保存搜索关键词
        self.cookie_warning_shown = False  # 标记是否已显示cookie警告
        
        self.setup_ui()
        self.setup_styles()
        
    def setup_styles(self):
        self.setStyleSheet("""
            QWidget {
                font-family: "Microsoft YaHei UI", "Segoe UI", "微软雅黑", sans-serif;
                background-color: #F8FAFC;
            }
            QScrollBar:vertical {
                border: none;
                background-color: #F1F5F9;
                width: 10px;
                margin: 0px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background-color: #CBD5E1;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #94A3B8;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
    
    def check_cookie_status(self):
        """检查cookie状态，在状态栏显示提示（非弹窗）"""
        cookie = self.audio_api.cookie
        if not cookie or not cookie.strip():
            self.status_label.setText("⚠️ 未设置B站Cookie，部分功能可能受限。点击设置按钮配置Cookie。")
            self.status_label.setStyleSheet("color: #F59E0B; font-weight: bold; padding: 8px;")
        else:
            # Cookie已设置，清除可能的警告
            if self.status_label.text().startswith("⚠️"):
                self.status_label.setText("")
    
    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(25, 25, 25, 25)
        main_layout.setSpacing(20)
        
        # 标题
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)
        
        header = QLabel("📺 B站音乐下载")
        header.setFont(QFont("Microsoft YaHei UI", 22, QFont.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("""
            QLabel {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #EF4444, stop:0.5 #FB7185, stop:1 #F43F5E);
                color: white;
                border-radius: 16px;
                font-size: 24px;
                padding: 16px;
            }
        """)
        header.setFixedHeight(70)
        
        # 设置按钮
        self.settings_btn = ModernButton("⚙️ 设置")
        self.settings_btn.setFixedSize(100, 40)
        self.settings_btn.clicked.connect(self.open_settings)
        
        header_layout.addWidget(header, 1)
        header_layout.addWidget(self.settings_btn)
        main_layout.addLayout(header_layout)
        
        # 搜索区域
        search_frame = QFrame()
        search_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 16px;
                padding: 20px;
                border: 1px solid #F1F5F9;
            }
        """)
        
        search_layout = QVBoxLayout()
        
        # 搜索输入
        input_layout = QHBoxLayout()
        input_layout.setSpacing(15)
        
        self.search_input = ModernLineEdit("输入视频关键词...")
        self.search_input.returnPressed.connect(self.search_videos)
        input_layout.addWidget(self.search_input, 5)
        
        self.search_btn = ModernButton("搜索")
        self.search_btn.clicked.connect(self.search_videos)
        input_layout.addWidget(self.search_btn, 1)
        
        search_layout.addLayout(input_layout)
        
        # 状态标签
        self.status_label = QLabel("")
        self.status_label.setFont(QFont("Microsoft YaHei UI", 11))
        self.status_label.setStyleSheet("color: #64748B; padding: 8px;")
        search_layout.addWidget(self.status_label)
        
        search_frame.setLayout(search_layout)
        main_layout.addWidget(search_frame)
        
        # 结果区域
        results_frame = QFrame()
        results_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 16px;
                padding: 20px;
                border: 1px solid #F1F5F9;
            }
        """)
        
        results_layout = QVBoxLayout()
        
        list_label = QLabel("📋 搜索结果")
        list_label.setFont(QFont("Microsoft YaHei UI", 14, QFont.Bold))
        list_label.setStyleSheet("color: #1E293B; padding: 8px 0;")
        results_layout.addWidget(list_label)
        
        self.results_list = QListWidget()
        self.results_list.setFont(QFont("Microsoft YaHei UI", 11))
        self.results_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #E2E8F0;
                border-radius: 12px;
                padding: 8px;
                font-size: 14px;
                background-color: #F8FAFC;
                outline: none;
            }
            QListWidget::item {
                padding: 12px 16px;
                border-bottom: 1px solid #F1F5F9;
                border-radius: 8px;
                margin: 4px 0;
            }
            QListWidget::item:hover {
                background-color: #F1F5F9;
                border-left: 4px solid #CBD5E1;
                padding-left: 12px;
            }
            QListWidget::item:selected {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #EF4444, stop:1 #FB7185);
                color: white;
                border-left: 4px solid #DC2626;
                font-weight: 600;
            }
            QListWidget::item:selected:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #DC2626, stop:1 #F43F5E);
                border-left: 4px solid #B91C1C;
            }
        """)
        self.results_list.setIconSize(QSize(60, 60))
        self.results_list.itemSelectionChanged.connect(self.on_video_selected)
        self.results_list.itemDoubleClicked.connect(self.download_audio)
        # 增大初始列表尺寸，便于显示更多搜索结果
        self.results_list.setMinimumHeight(300)
        self.results_list.setMinimumWidth(420)
        results_layout.addWidget(self.results_list)
        
        results_frame.setLayout(results_layout)
        main_layout.addWidget(results_frame)
        
        # 详情和按钮区域
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(20)
        
        # 详情面板
        detail_frame = QFrame()
        detail_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 16px;
                padding: 20px;
                border: 1px solid #F1F5F9;
            }
        """)
        
        detail_layout = QVBoxLayout()
        
        detail_label = QLabel("📝 视频详情")
        detail_label.setFont(QFont("Microsoft YaHei UI", 14, QFont.Bold))
        detail_label.setStyleSheet("color: #1E293B; padding: 8px 0;")
        detail_layout.addWidget(detail_label)
        
        self.video_info = QLabel("选择视频查看详情")
        self.video_info.setWordWrap(True)
        self.video_info.setFont(QFont("Microsoft YaHei UI", 12))
        self.video_info.setStyleSheet("""
            QLabel {
                background-color: #F8FAFC;
                border: 2px solid #F1F5F9;
                border-radius: 16px;
                padding: 20px;
                font-size: 14px;
                color: #334155;
                min-height: 140px;
                line-height: 1.6;
            }
        """)
        detail_layout.addWidget(self.video_info)
        
        detail_frame.setLayout(detail_layout)
        bottom_layout.addWidget(detail_frame, 2)
        
        # 按钮区域
        button_frame = QFrame()
        button_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 16px;
                padding: 20px;
                border: 1px solid #F1F5F9;
            }
        """)
        
        button_layout = QVBoxLayout()
        
        self.download_btn = ModernButton("⬇️ 下载音频")
        self.download_btn.clicked.connect(self.download_audio)
        self.download_btn.setEnabled(False)
        button_layout.addWidget(self.download_btn)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #F1F5F9;
                border-radius: 12px;
                text-align: center;
                height: 24px;
                background-color: #F8FAFC;
                font-size: 12px;
                font-weight: 600;
                color: #64748B;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #10B981, stop:1 #34D399);
                border-radius: 10px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)
        self.progress_bar.setVisible(False)
        button_layout.addWidget(self.progress_bar)
        
        button_layout.addStretch()
        
        self.clear_btn = ModernButton("🗑️ 清除结果")
        self.clear_btn.clicked.connect(self.clear_results)
        button_layout.addWidget(self.clear_btn)
        
        self.close_btn = ModernButton("❌ 关闭")
        self.close_btn.clicked.connect(self.close)
        button_layout.addWidget(self.close_btn)
        
        button_frame.setLayout(button_layout)
        bottom_layout.addWidget(button_frame, 1)
        
        main_layout.addLayout(bottom_layout)
        
        # 页脚
        footer = QLabel("💡 提示：双击搜索结果可直接下载 | 音频将使用搜索关键词命名")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setFont(QFont("Microsoft YaHei UI", 10))
        footer.setStyleSheet("""
            color: #94A3B8; 
            font-size: 12px; 
            padding: 12px; 
            background-color: #F1F5F9; 
            border-radius: 12px;
            border: 1px solid #E2E8F0;
        """)
        main_layout.addWidget(footer)
        
        self.setLayout(main_layout)
        
        # 初始化完成后检查cookie状态
        self.check_cookie_status()
    
    def search_videos(self):
        self.search_keyword = self.search_input.text().strip()
        if not self.search_keyword:
            QMessageBox.warning(self, "提示", "请输入搜索关键词")
            return
        
        logger.info(f"开始搜索B站视频: {self.search_keyword}")
        
        # 清空之前的结果
        self.results_list.clear()
        self.video_info.setText("搜索中...")
        self.status_label.setText("🔍 搜索中...")
        self.download_btn.setEnabled(False)
        self.search_btn.setEnabled(False)
        
        # 创建并启动搜索线程
        if self.search_thread and self.search_thread.isRunning():
            self.search_thread.stop()
        
        self.search_thread = BilibiliSearchThread(self.search_keyword, self.audio_api)
        self.search_thread.results_ready.connect(self.display_results)
        self.search_thread.error_occurred.connect(self.on_search_error)
        self.search_thread.finished.connect(self.on_search_finished)
        self.search_thread.start()
    
    def display_results(self, videos):
        if not videos:
            self.video_info.setText("未找到相关视频")
            self.status_label.setText("❌ 未找到相关视频")
            logger.info("搜索完成，未找到相关视频")
            return
        
        self.search_results = videos
        self.status_label.setText(f"✅ 找到 {len(videos)} 个视频")
        logger.info(f"搜索完成，找到 {len(videos)} 个视频")
        
        for i, video in enumerate(videos):
            try:
                title = BeautifulSoup(video["title"], "html.parser").get_text()
                author = video.get("author", "未知作者")
                duration = video.get("duration", "未知时长")
                item_text = f"{title} - {author} ({duration})"
                item = QListWidgetItem(item_text)
                item.setData(int(Qt.UserRole), i)  # 存储索引（显式转换以避免类型检查警告）
                self.results_list.addItem(item)
            except Exception as e:
                logger.error(f"处理视频结果时出错: {str(e)}")
                logger.error(f"异常详情:\n{traceback.format_exc()}")
                continue
    
    def on_search_error(self, error):
        error_msg = f"搜索失败: {error}"
        logger.error(error_msg)
        self.video_info.setText(error_msg)
        
        # 检查是否是cookie相关错误
        error_lower = str(error).lower()
        cookie_related = any(keyword in error_lower for keyword in [
            'cookie', 'cookies', '身份验证', '未登录', '登录', 'auth', 'authentication',
            '412', '403', '401', '风控', '拦截'
        ])
        
        if cookie_related:
            self.status_label.setText("❌ 搜索失败：可能需要设置B站Cookie")
            # 只在首次显示cookie警告时提示
            if not self.cookie_warning_shown:
                self.status_label.setText("❌ 搜索失败：请设置B站Cookie以获得更好的搜索体验")
                self.cookie_warning_shown = True
        else:
            self.status_label.setText(f"❌ 搜索失败：{error[:50]}...")
    
    def on_search_finished(self):
        self.search_btn.setEnabled(True)
        self.search_thread = None
    
    def on_video_selected(self):
        selected_items = self.results_list.selectedItems()
        if not selected_items:
            return
        
        item = selected_items[0]
        index = int(item.data(int(Qt.UserRole)))
        if isinstance(index, int) and index < len(self.search_results):
            self.current_video = self.search_results[index]
            try:
                title = BeautifulSoup(self.current_video["title"], "html.parser").get_text()
                author = self.current_video.get("author", "未知作者")
                duration = self.current_video.get("duration", "未知时长")
                play_count = self.current_video.get("play", "未知播放量")
                bvid = self.current_video.get("bvid", "未知")
                
                info = f"""<b>标题:</b> {title}<br>
<b>作者:</b> {author}<br>
<b>时长:</b> {duration}<br>
<b>播放量:</b> {play_count}<br>
<b>视频ID:</b> {bvid}"""
                
                self.video_info.setText(info)
                self.download_btn.setEnabled(True)
                logger.info(f"选择视频: {title}")
            except Exception as e:
                error_msg = f"显示视频详情失败: {str(e)}"
                logger.error(error_msg)
                logger.error(f"异常详情:\n{traceback.format_exc()}")
    
    def download_audio(self):
        if not self.current_video:
            QMessageBox.warning(self, "提示", "请先选择要下载的视频")
            return
        
        bvid = self.current_video.get("bvid", "")
        if not bvid:
            QMessageBox.warning(self, "错误", "无效的视频ID")
            return
        
        # 获取保存路径
        settings = self.settings
        audio_dir = settings["save_paths"].get("music", os.path.join(os.path.expanduser("~"), "Music"))
        
        # 使用搜索关键词作为默认文件名
        if self.search_keyword:
            safe_name = self.audio_api.safe_filename(self.search_keyword)  # type: ignore
            default_filename = f"{safe_name}.mp3"
        else:
            title = self.current_video.get("title", "bilibili_audio")
            safe_title = self.audio_api.safe_filename(title)  # type: ignore
            default_filename = f"{safe_title}.mp3"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "保存音频", 
            os.path.join(audio_dir, default_filename), 
            "音频文件 (*.mp3 *.m4a *.flac)"
        )
        
        if not file_path:
            return
        
        logger.info(f"开始下载音频: bvid={bvid}, 保存路径={file_path}")
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.download_btn.setEnabled(False)
        self.status_label.setText("⬇️ 下载中...")
        
        # 创建并启动下载线程
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.stop()
        
        self.download_thread = BilibiliDownloadThread(bvid, file_path, self.audio_api, self.search_keyword)
        self.download_thread.download_complete.connect(self.on_download_complete)
        self.download_thread.error_occurred.connect(self.on_download_error)
        self.download_thread.finished.connect(self.on_download_finished)
        self.download_thread.start()
    
    def update_progress(self, progress):
        self.progress_bar.setValue(progress)
    
    def on_download_complete(self, file_path):
        self.progress_bar.setVisible(False)
        self.download_btn.setEnabled(True)
        self.status_label.setText("✅ 下载完成")
        logger.info(f"音频下载完成: {file_path}")
        QMessageBox.information(self, "完成", f"音频已下载到:\n{file_path}")
    
    def on_download_error(self, error):
        self.progress_bar.setVisible(False)
        self.download_btn.setEnabled(True)
        
        # 检查是否是cookie相关错误
        error_lower = str(error).lower()
        cookie_related = any(keyword in error_lower for keyword in [
            'cookie', 'cookies', '身份验证', '未登录', '登录', 'auth', 'authentication',
            '412', '403', '401', '风控', '拦截'
        ])
        
        if cookie_related:
            self.status_label.setText("❌ 下载失败：可能需要设置B站Cookie")
        else:
            self.status_label.setText(f"❌ 下载失败：{error[:50]}...")
        
        logger.error(f"音频下载失败: {error}")
    
    def on_download_finished(self):
        self.download_thread = None
    
    def clear_results(self):
        self.results_list.clear()
        self.video_info.setText("选择视频查看详情")
        self.current_video = None
        self.download_btn.setEnabled(False)
        self.status_label.setText("")
        logger.info("已清除搜索结果")
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        # 停止搜索线程
        search_thread = getattr(self, 'search_thread', None)
        if search_thread and hasattr(search_thread, 'isRunning') and search_thread.isRunning():
            try:
                search_thread.stop()
            except Exception:
                pass
        
        # 停止下载线程
        download_thread = getattr(self, 'download_thread', None)
        if download_thread and hasattr(download_thread, 'isRunning') and download_thread.isRunning():
            try:
                download_thread.stop()
            except Exception:
                pass
        
        # 断开信号连接
        try:
            self.audio_api.download_progress.disconnect(self.update_progress)
        except:
            pass
        
        event.accept()
    
    def open_settings(self):
        """打开设置对话框"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton, QFormLayout
        
        dialog = QDialog(self)
        dialog.setWindowTitle("B站设置")
        dialog.setGeometry(300, 300, 600, 400)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #F8FAFC;
                font-family: 'Microsoft YaHei UI', sans-serif;
            }
            QLabel {
                color: #334155;
                font-size: 14px;
            }
            QTextEdit {
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 8px;
                font-family: 'Consolas', monospace;
                font-size: 12px;
            }
            QPushButton {
                background-color: #EF4444;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #F87171;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Cookie设置
        form_layout = QFormLayout()
        
        cookie_label = QLabel("B站 Cookie:")
        self.cookie_edit = QTextEdit()
        self.cookie_edit.setFixedHeight(120)
        current_cookie = self.settings.get("bilibili", {}).get("cookie", "")
        self.cookie_edit.setText(current_cookie)
        
        form_layout.addRow(cookie_label, self.cookie_edit)
        
        # 说明
        info_label = QLabel("如何获取B站 Cookie:")
        info_label.setStyleSheet("font-weight: bold;")
        steps_label = QLabel("""
1. 打开浏览器，访问 https://www.bilibili.com
2. 登录你的B站账号
3. 按 F12 打开开发者工具
4. 切换到 Network 选项卡
5. 刷新页面，找到一个B站请求
6. 在 Headers 中找到 Cookie 字段
7. 复制整个 Cookie 值粘贴到上方

注意: Cookie 包含你的登录信息，请妥善保管！
        """)
        steps_label.setWordWrap(True)
        steps_label.setStyleSheet("color: #64748B; font-size: 12px;")
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        save_btn = QPushButton("保存")
        save_btn.clicked.connect(lambda: self.save_settings(dialog))
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(form_layout)
        layout.addWidget(info_label)
        layout.addWidget(steps_label)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        dialog.exec_()
    
    def save_settings(self, dialog):
        """保存设置"""
        try:
            new_cookie = self.cookie_edit.toPlainText().strip()
            
            # 更新设置
            if "bilibili" not in self.settings:
                self.settings["bilibili"] = {}
            
            self.settings["bilibili"]["cookie"] = new_cookie
            
            # 保存到文件
            try:
                from Music_Download.crawler import save_settings
                save_settings(self.settings)
                logger.info("设置保存成功")
            except Exception as e:
                logger.error(f"保存设置失败: {e}")
            
            # 更新音频API的cookie
            self.audio_api.cookie = new_cookie
            self.audio_api.BILIBILI_HEADER["Cookie"] = new_cookie
            
            # 更新界面状态
            self.check_cookie_status()
            
            QMessageBox.information(self, "成功", "设置保存成功！")
            dialog.accept()
            
        except Exception as e:
            logger.error(f"保存设置时出错: {e}")
            QMessageBox.critical(self, "错误", f"保存设置失败: {str(e)}")

def main():
    """测试函数"""
    app = QApplication(sys.argv)
    window = BilibiliMusicDownloadWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()