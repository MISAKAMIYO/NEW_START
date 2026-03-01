"""
歌词搜索与生成模块
支持三种歌词获取方式：
1. AI生成歌词 - 利用已有AI功能生成歌词
2. 网络搜索下载 - 从网络搜索并下载LRC歌词文件
3. 文本转LRC - 将纯文本歌词转换为带时间轴的LRC格式
"""

import os
import re
import json
import time
import asyncio
import aiohttp
import logging
from typing import List, Tuple, Optional, Dict, Any
from PyQt5.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class LyricsSearcher(QThread):
    """歌词搜索线程"""
    
    progress = pyqtSignal(str)
    lyrics_found = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    finished = pyqtSignal()
    
    def __init__(self, song_title: str = "", artist: str = "", parent=None):
        super().__init__(parent)
        self.song_title = song_title
        self.artist = artist
        self.search_results = []
        self.canceled = False
        
    def run(self):
        """执行歌词搜索"""
        try:
            self.progress.emit("正在搜索歌词...")
            lyrics = self.search_from_network(self.song_title, self.artist)
            if lyrics:
                self.lyrics_found.emit(lyrics)
            else:
                self.error_occurred.emit("未找到歌词")
        except Exception as e:
            self.error_occurred.emit(f"搜索失败: {str(e)}")
        finally:
            self.finished.emit()
            
    def search_from_network(self, title: str, artist: str) -> Optional[str]:
        """从多个网络源搜索歌词"""
        if not title:
            return None
            
        import urllib.request
        import urllib.parse
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/html, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }
        
        apis = [
            (f"https://api.lyrics.ovh/v1/{urllib.parse.quote(artist)}/{urllib.parse.quote(title)}", "lyrics.ovh"),
            (f"https://lrclib.net/api/get?track_name={urllib.parse.quote(title)}&artist_name={urllib.parse.quote(artist)}", "lrclib.net"),
            (f"https://lyrics-2.onrender.com/lyrics?artist={urllib.parse.quote(artist)}&title={urllib.parse.quote(title)}", "lyrics-2"),
        ]
        
        for api_url, source_name in apis:
            try:
                if self.canceled:
                    return None
                    
                self.progress.emit(f"搜索中: {source_name}...")
                req = urllib.request.Request(api_url, headers=headers)
                with urllib.request.urlopen(req, timeout=8) as response:
                    content_type = response.headers.get('Content-Type', '')
                    data = response.read().decode('utf-8')
                    
                    if 'application/json' in content_type:
                        result = json.loads(data)
                        
                        if 'lyrics' in result and result['lyrics']:
                            self.progress.emit(f"从 {source_name} 找到歌词!")
                            return result['lyrics']
                        elif 'plainLyrics' in result and result['plainLyrics']:
                            self.progress.emit(f"从 {source_name} 找到歌词!")
                            return result['plainLyrics']
                        elif ' lyrics' in result and result.get(' lyrics'):
                            self.progress.emit(f"从 {source_name} 找到歌词!")
                            return result[' lyrics']
                    elif 'text/plain' in content_type or 'html' not in content_type:
                        if data and len(data) > 20:
                            self.progress.emit(f"从 {source_name} 找到歌词!")
                            return data
                            
            except Exception as e:
                logger.debug(f"{source_name} 请求失败: {e}")
                continue
        
        self.progress.emit("尝试音乐平台搜索...")
        platform_lyrics = self._search_from_music_platforms(title, artist)
        if platform_lyrics:
            return platform_lyrics
        
        self.progress.emit("API搜索未果，尝试网页搜索...")
        html_lyrics = self._search_from_html(title, artist)
        if html_lyrics:
            return html_lyrics
        
        return None
    
    def _search_from_music_platforms(self, title: str, artist: str) -> Optional[str]:
        """从音乐平台API搜索歌词"""
        import urllib.request
        import urllib.parse
        import re
        
        keyword = f"{artist} {title}".strip()
        
        platform_apis = [
            ("https://netease-cloud-music-api-five-roan-25.vercel.app/search?keywords=" + urllib.parse.quote(keyword) + "&type=1&limit=5", "网易云", self._parse_netease_lyrics),
            ("https://c.y.qq.com/soso/fcgi-bin/client_search_cp?ct=24&qqmusic_ver=1001&remoteplace=sizer.yqqListMain&t=0&aggr=1&cr=1&p=1&n=5&w=" + urllib.parse.quote(keyword), "QQ音乐", self._parse_qqmusic_lyrics),
            ("https://searchapi.kugou.com/switch/song?keyword=" + urllib.parse.quote(keyword), "酷狗", self._parse_kugou_lyrics),
        ]
        
        for api_url, platform_name, parser in platform_apis:
            try:
                if self.canceled:
                    return None
                    
                self.progress.emit(f"搜索: {platform_name}...")
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                }
                req = urllib.request.Request(api_url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = response.read().decode('utf-8')
                    result = json.loads(data)
                    
                    lyrics = parser(result, title, artist)
                    if lyrics:
                        self.progress.emit(f"从 {platform_name} 找到歌词!")
                        return lyrics
                        
            except Exception as e:
                logger.debug(f"{platform_name} 搜索失败: {e}")
                continue
        
        return None
    
    def _parse_netease_lyrics(self, data: dict, title: str, artist: str) -> Optional[str]:
        """解析网易云歌词"""
        try:
            if 'result' in data and 'songs' in data['result'] and data['result']['songs']:
                song = data['result']['songs'][0]
                song_id = song.get('id')
                if song_id:
                    import urllib.request
                    lrc_url = f"https://netease-cloud-music-api-five-roan-25.vercel.app/lyric?id={song_id}"
                    req = urllib.request.Request(lrc_url)
                    with urllib.request.urlopen(req, timeout=10) as response:
                        lrc_data = json.loads(response.read().decode('utf-8'))
                        if 'lrc' in lrc_data and 'lyric' in lrc_data['lrc']:
                            return lrc_data['lrc']['lyric']
        except Exception as e:
            logger.debug(f"网易云歌词解析失败: {e}")
        return None
    
    def _parse_qqmusic_lyrics(self, data: dict, title: str, artist: str) -> Optional[str]:
        """解析QQ音乐歌词"""
        try:
            if 'data' in data and 'song' in data['data'] and data['data']['song']['list']:
                song = data['data']['song']['list'][0]
                songmid = song.get('songmid')
                if songmid:
                    import urllib.request
                    lrc_url = f"https://c.y.qq.com/lyric/fcgi-bin/fcg_get_lyric.lrc?songmid={songmid}&format=json"
                    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://y.qq.com/'}
                    req = urllib.request.Request(lrc_url, headers=headers)
                    with urllib.request.urlopen(req, timeout=10) as response:
                        lrc_data = json.loads(response.read().decode('utf-8'))
                        if 'lyric' in lrc_data:
                            import base64
                            decoded = base64.b64decode(lrc_data['lyric']).decode('utf-8')
                            return decoded
        except Exception as e:
            logger.debug(f"QQ音乐歌词解析失败: {e}")
        return None
    
    def _parse_kugou_lyrics(self, data: dict, title: str, artist: str) -> Optional[str]:
        """解析酷狗歌词"""
        try:
            if 'data' in data and data['data']:
                song_info = data['data'][0]
                hash_val = song_info.get('hash')
                if hash_val:
                    import urllib.request
                    lrc_url = f"https://lyrics.kugou.com/search?ver=1&client=pc&hash={hash_val}&keyword={urllib.parse.quote(artist + ' ' + title)}"
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    req = urllib.request.Request(lrc_url, headers=headers)
                    with urllib.request.urlopen(req, timeout=10) as response:
                        search_result = json.loads(response.read().decode('utf-8'))
                        if 'candidates' in search_result and search_result['candidates']:
                            accesskey = search_result['candidates'][0].get('accesskey')
                            id_str = search_result['candidates'][0].get('id')
                            if accesskey and id_str:
                                download_url = f"https://lyrics.kugou.com/download?ver=1&client=pc&id={id_str}&accesskey={accesskey}&fmt=lrc&charset=utf8"
                                req2 = urllib.request.Request(download_url, headers=headers)
                                with urllib.request.urlopen(req2, timeout=10) as resp2:
                                    dl_data = json.loads(resp2.read().decode('utf-8'))
                                    if 'content' in dl_data:
                                        import base64
                                        decoded = base64.b64decode(dl_data['content']).decode('utf-8')
                                        return decoded
        except Exception as e:
            logger.debug(f"酷狗歌词解析失败: {e}")
        return None
    
    def _search_from_html(self, title: str, artist: str) -> Optional[str]:
        """从网页搜索歌词"""
        import urllib.request
        import urllib.parse
        import re
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        
        search_engines = [
            ("https://www.google.com/search?q={artist}+{title}+歌词", "Google"),
            ("https://www.bing.com/search?q={artist}+{title}+歌词", "Bing"),
        ]
        
        for search_url, engine_name in search_engines:
            try:
                query = f"{artist} {title} 歌词".strip()
                url = search_url.format(
                    artist=urllib.parse.quote(artist),
                    title=urllib.parse.quote(title),
                    query=urllib.parse.quote(query)
                )
                
                self.progress.emit(f"从 {engine_name} 搜索...")
                req = urllib.request.Request(url, headers=headers)
                
                with urllib.request.urlopen(req, timeout=10) as response:
                    html = response.read().decode('utf-8', errors='ignore')
                    
                    lyrics = self._extract_lyrics_from_html(html)
                    if lyrics:
                        self.progress.emit(f"从 {engine_name} 找到歌词!")
                        return lyrics
                        
            except Exception as e:
                logger.debug(f"{engine_name} 搜索失败: {e}")
                continue
        
        return None
    
    def _extract_lyrics_from_html(self, html: str) -> Optional[str]:
        """从HTML中提取歌词"""
        import re
        
        lrc_pattern = re.compile(r'\[(\d+):(\d+\.\d+)\](.+?)(?=\[|$)', re.MULTILINE)
        matches = lrc_pattern.findall(html)
        
        if matches:
            lyrics_lines = []
            for min_sec, sec, text in matches:
                time_str = f"[{min_sec}:{sec}]{text}"
                lyrics_lines.append(time_str)
            return '\n'.join(lyrics_lines)
        
        text_patterns = [
            r'lyrics["\s:]+["\'](.+?)["\']',
            r'class=["\']lyrics["\']>(.+?)</div>',
            r'class=["\'](?:lyric|song lyrics)["\'][\s>](.+?)(?:</p>|</div>)',
        ]
        
        for pattern in text_patterns:
            match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
            if match:
                lyrics = match.group(1).strip()
                if len(lyrics) > 50:
                    return self._clean_lyrics(lyrics)
        
        return None
    
    def _clean_lyrics(self, text: str) -> str:
        """清理歌词文本"""
        import re
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\\n|\\t', '\n', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()
        
    def cancel(self):
        """取消搜索"""
        self.canceled = True


class TextToLRCConverter:
    """文本转LRC转换器"""
    
    @staticmethod
    def convert(lyrics_text: str, duration_per_line: float = 5.0) -> str:
        """
        将纯文本歌词转换为LRC格式
        
        Args:
            lyrics_text: 纯文本歌词，每行一句
            duration_per_line: 每行歌词的默认时长（秒）
            
        Returns:
            LRC格式的歌词
        """
        lines = lyrics_text.strip().split('\n')
        lrc_lines = []
        current_time = 0.0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            minutes = int(current_time // 60)
            seconds = current_time % 60
            time_str = f"[{minutes:02d}:{seconds:05.2f}]"
            lrc_lines.append(f"{time_str}{line}")
            current_time += duration_per_line
            
        return '\n'.join(lrc_lines)
    
    @staticmethod
    def save_to_file(lrc_content: str, file_path: str) -> bool:
        """
        保存LRC内容到文件
        
        Args:
            lrc_content: LRC格式的歌词内容
            file_path: 保存路径
            
        Returns:
            是否保存成功
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(lrc_content)
            return True
        except Exception as e:
            logger.error(f"保存LRC文件失败: {e}")
            return False


class AILyricsGenerator(QThread):
    """AI歌词生成线程"""
    
    progress = pyqtSignal(str)
    lyrics_generated = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    finished = pyqtSignal()
    
    def __init__(self, song_title: str, artist: str, config_manager=None, parent=None):
        super().__init__(parent)
        self.song_title = song_title
        self.artist = artist
        self.config_manager = config_manager
        self.canceled = False
        
    def run(self):
        """执行AI歌词生成"""
        try:
            self.progress.emit("正在调用AI生成歌词...")
            
            if not self.config_manager:
                self.error_occurred.emit("配置管理器未初始化")
                return
                
            lyrics = self._generate_lyrics_ai()
            if lyrics:
                self.lyrics_generated.emit(lyrics)
            else:
                self.error_occurred.emit("AI生成歌词失败")
        except Exception as e:
            self.error_occurred.emit(f"生成失败: {str(e)}")
        finally:
            self.finished.emit()
            
    def _generate_lyrics_ai(self) -> Optional[str]:
        """使用AI生成歌词（先尝试网络搜索，再调用AI）"""
        try:
            from AI_Chat.ai_model import AIManager
            
            self.progress.emit("正在搜索歌词...")
            search_result = self._search_lyrics_online()
            
            if search_result:
                self.progress.emit("找到歌词，正在处理...")
                return search_result
            
            self.progress.emit("未找到网络歌词，正在调用AI生成...")
            ai_manager = AIManager(self.config_manager)
            
            provider_id = self.config_manager.get_config("ai.default_provider")
            if not provider_id:
                provider_id = "openai"
                
            provider = ai_manager.create_provider(provider_id)
            if not provider:
                self.error_occurred.emit(f"无法创建AI提供商: {provider_id}")
                return None
                
            prompt = self._build_prompt(search_result)
            
            self.progress.emit("正在生成歌词（这可能需要几秒钟）...")
            
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            if hasattr(provider, 'chat_completion'):
                result = loop.run_until_complete(
                    provider.chat_completion([
                        {"role": "system", "content": "你是一个专业的歌词创作助手。请根据歌曲信息生成歌词。"},
                        {"role": "user", "content": prompt}
                    ])
                )
                return self._parse_ai_response(result)
            else:
                self.error_occurred.emit("AI提供商不支持此功能")
                return None
                
        except ImportError as e:
            logger.error(f"导入AI模块失败: {e}")
            self.error_occurred.emit("AI模块不可用")
            return None
        except Exception as e:
            logger.error(f"AI生成歌词失败: {e}")
            self.error_occurred.emit(f"生成失败: {str(e)}")
            return None
    
    def _search_lyrics_online(self) -> Optional[str]:
        """先在网上搜索歌词（多源）"""
        if not self.song_title:
            return None
            
        import urllib.request
        import urllib.parse
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/html, */*',
        }
        
        apis = [
            (f"https://api.lyrics.ovh/v1/{urllib.parse.quote(self.artist)}/{urllib.parse.quote(self.song_title)}", "lyrics.ovh"),
            (f"https://lrclib.net/api/get?track_name={urllib.parse.quote(self.song_title)}&artist_name={urllib.parse.quote(self.artist)}", "lrclib.net"),
            (f"https://lyrics-2.onrender.com/lyrics?artist={urllib.parse.quote(self.artist)}&title={urllib.parse.quote(self.song_title)}", "lyrics-2"),
        ]
        
        for api_url, source_name in apis:
            try:
                req = urllib.request.Request(api_url, headers=headers)
                with urllib.request.urlopen(req, timeout=8) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    
                    if 'lyrics' in data and data['lyrics']:
                        logger.info(f"从 {source_name} 找到歌词")
                        return data['lyrics']
                    elif 'plainLyrics' in data and data['plainLyrics']:
                        logger.info(f"从 {source_name} 找到歌词")
                        return data['plainLyrics']
            except Exception as e:
                logger.debug(f"{source_name} 请求失败: {e}")
                continue
        
        logger.info("API搜索未找到歌词，尝试音乐平台搜索...")
        platform_lyrics = self._search_from_music_platforms(self.song_title, self.artist)
        if platform_lyrics:
            return platform_lyrics
        
        logger.info("API搜索未找到歌词，尝试网页搜索...")
        html_lyrics = self._search_from_html(self.song_title, self.artist)
        if html_lyrics:
            return html_lyrics
            
        return None
    
    def _search_from_html(self, title: str, artist: str) -> Optional[str]:
        """从网页搜索歌词"""
        import urllib.request
        import urllib.parse
        import re
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        
        search_engines = [
            ("https://www.google.com/search?q={artist}+{title}+歌词", "Google"),
            ("https://www.bing.com/search?q={artist}+{title}+歌词", "Bing"),
        ]
        
        for search_url, engine_name in search_engines:
            try:
                url = search_url.format(
                    artist=urllib.parse.quote(artist),
                    title=urllib.parse.quote(title)
                )
                
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as response:
                    html = response.read().decode('utf-8', errors='ignore')
                    
                    lyrics = self._extract_lyrics_from_html(html)
                    if lyrics:
                        logger.info(f"从 {engine_name} 找到歌词")
                        return lyrics
                        
            except Exception as e:
                logger.debug(f"{engine_name} 搜索失败: {e}")
                continue
        
        return None
    
    def _extract_lyrics_from_html(self, html: str) -> Optional[str]:
        """从HTML中提取歌词"""
        import re
        
        lrc_pattern = re.compile(r'\[(\d+):(\d+\.\d+)\](.+?)(?=\[|$)', re.MULTILINE)
        matches = lrc_pattern.findall(html)
        
        if matches:
            lyrics_lines = []
            for min_sec, sec, text in matches:
                time_str = f"[{min_sec}:{sec}]{text}"
                lyrics_lines.append(time_str)
            return '\n'.join(lyrics_lines)
        
        text_patterns = [
            r'lyrics["\s:]+["\'](.+?)["\']',
            r'class=["\']lyrics["\']>(.+?)</div>',
            r'class=["\'](?:lyric|song lyrics)["\'][\s>](.+?)(?:</p>|</div>)',
        ]
        
        for pattern in text_patterns:
            match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
            if match:
                lyrics = match.group(1).strip()
                if len(lyrics) > 50:
                    return self._clean_lyrics(lyrics)
        
        return None
    
    def _clean_lyrics(self, text: str) -> str:
        """清理歌词文本"""
        import re
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\\n|\\t', '\n', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()
    
    def _build_prompt(self, search_result: str = None) -> str:
        """构建AI提示词"""
        if search_result:
            prompt = f"""请根据以下搜索到的歌词内容，整理并输出完整的歌词：

搜索到的歌词内容：
{search_result}

要求：
1. 请整理并输出搜索到的完整歌词
2. 如果搜索到的歌词不完整，请尝试补充完整
3. 请直接输出歌词内容，不要添加任何解释或格式

歌词："""
        else:
            prompt = f"""请为以下歌曲创作歌词：

歌曲名称：{self.song_title}
艺术家：{self.artist}

要求：
1. 请创作完整的中文歌词
2. 歌词要有情感和诗意
3. 请直接输出歌词内容，不要添加任何解释或格式

歌词："""
        return prompt
    
    def _parse_ai_response(self, response: str) -> Optional[str]:
        """解析AI响应，提取歌词"""
        if not response:
            return None
            
        lyrics = response.strip()
        
        if lyrics.startswith("```"):
            lines = lyrics.split('\n')
            lyrics = '\n'.join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            
        return lyrics
    
    def cancel(self):
        """取消生成"""
        self.canceled = True


class LyricsSearchManager:
    """歌词搜索管理器"""
    
    def __init__(self, config_manager=None):
        self.config_manager = config_manager
        
    def search_online(self, title: str, artist: str = "") -> Optional[str]:
        """
        在线搜索歌词
        
        Args:
            title: 歌曲名称
            artist: 艺术家
            
        Returns:
            歌词内容，如果没有找到返回None
        """
        searcher = LyricsSearcher(title, artist)
        result = [None]
        error_msg = [None]
        finished = [False]
        
        def on_lyrics_found(lyrics):
            result[0] = lyrics
            finished[0] = True
            
        def on_error(msg):
            error_msg[0] = msg
            finished[0] = True
            
        searcher.lyrics_found.connect(on_lyrics_found)
        searcher.error_occurred.connect(on_error)
        searcher.finished.connect(lambda: setattr(finished, '0', True))
        
        searcher.start()
        searcher.wait(30000)
        
        return result[0]
    
    def generate_with_ai(self, title: str, artist: str = "") -> Optional[str]:
        """
        使用AI生成歌词
        
        Args:
            title: 歌曲名称
            artist: 艺术家
            
        Returns:
            生成的歌词内容
        """
        generator = AILyricsGenerator(title, artist, self.config_manager)
        result = [None]
        
        def on_lyrics_generated(lyrics):
            result[0] = lyrics
            
        generator.lyrics_generated.connect(on_lyrics_generated)
        generator.start()
        generator.wait(60000)
        
        return result[0]
    
    @staticmethod
    def convert_text_to_lrc(text: str, duration_per_line: float = 5.0) -> str:
        """
        将文本转换为LRC格式
        
        Args:
            text: 原始歌词文本
            duration_per_line: 每行时长（秒）
            
        Returns:
            LRC格式歌词
        """
        return TextToLRCConverter.convert(text, duration_per_line)
    
    @staticmethod
    def save_lrc(lyrics: str, file_path: str) -> bool:
        """
        保存LRC歌词到文件
        
        Args:
            lyrics: LRC格式歌词
            file_path: 保存路径
            
        Returns:
            是否成功
        """
        return TextToLRCConverter.save_to_file(lyrics, file_path)
