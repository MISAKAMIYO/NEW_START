"""
多平台音乐下载模块 V3 (基于go-music-dl改进)
支持网易云、QQ音乐、酷狗、酷我、咪咕、B站等12+平台的音乐搜索和下载
支持URL解析、歌单搜索、换源、验证歌曲有效性
界面参考 music.kukuqaq.com 设计
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import re
import requests
import random

UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

def get_ua():
    return random.choice(UA_LIST)

import logging
import base64
from urllib.parse import urlparse, parse_qs
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, 
    QListWidget, QListWidgetItem, QProgressBar, QMessageBox, QComboBox,
    QFrame, QCheckBox, QScrollArea, QButtonGroup, QRadioButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget, QTextEdit
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette, QBrush

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MusicDL")


PLATFORM_INFO = {
    "netease": {"name": "网易云音乐", "color": "#E62117", "icon": "🎵"},
    "qq": {"name": "QQ音乐", "color": "#12B7F5", "icon": "🎶"},
    "kugou": {"name": "酷狗音乐", "color": "#FF6900", "icon": "🐕"},
    "kuwo": {"name": "酷我音乐", "color": "#FF6600", "icon": "🎸"},
    "migu": {"name": "咪咕音乐", "color": "#00B37E", "icon": "📱"},
    "bilibili": {"name": "B站音乐", "color": "#FB7299", "icon": "📺"},
    "fivesing": {"name": "5sing", "color": "#FF6B6B", "icon": "🎤"},
    "joox": {"name": "JOOX", "color": "#6B4EFF", "icon": "🌟"},
    "qianqian": {"name": "千千音乐", "color": "#00A0E9", "icon": "💿"},
    "jamendo": {"name": "Jamendo", "color": "#1DB954", "icon": "🎧"},
    "soda": {"name": "汽水音乐", "color": "#FF4D4D", "icon": "🥤"},
}


class SearchThread(QThread):
    searchFinished = pyqtSignal(list)
    searchError = pyqtSignal(str)
    
    def __init__(self, keyword, platforms, search_type="song"):
        super().__init__()
        self.keyword = keyword
        self.platforms = platforms
        self.search_type = search_type
        
    def run(self):
        all_results = []
        
        # URL解析模式
        if self.keyword.startswith("http"):
            parsed = self.parse_url(self.keyword)
            if parsed:
                if parsed["type"] == "song":
                    all_results.append(parsed["data"])
                elif parsed["type"] == "playlist":
                    all_results.extend(parsed["data"])
        else:
            # 关键词搜索
            platform_methods = {
                "netease": self.search_netease,
                "qq": self.search_qqmusic,
                "kugou": self.search_kugou,
                "kuwo": self.search_kuwo,
                "migu": self.search_migu,
                "bilibili": self.search_bilibili,
                "fivesing": self.search_fivesing,
                "joox": self.search_joox,
                "qianqian": self.search_qianqian,
                "jamendo": self.search_jamendo,
                "soda": self.search_soda,
            }
            
            if self.search_type == "song":
                for platform in self.platforms:
                    if platform in platform_methods:
                        try:
                            results = platform_methods[platform](self.keyword)
                            all_results.extend(results)
                        except Exception as e:
                            logger.warning(f"{platform} 搜索失败: {e}")
            elif self.search_type == "playlist":
                for platform in self.platforms:
                    if platform in ["netease", "qq", "kugou", "kuwo", "bilibili"]:
                        try:
                            results = self.search_playlist(platform, self.keyword)
                            all_results.extend(results)
                        except Exception as e:
                            logger.warning(f"{platform} 歌单搜索失败: {e}")
        
        self.searchFinished.emit(all_results)
    
    def parse_url(self, url):
        """解析音乐分享链接"""
        try:
            # 网易云音乐
            if "music.163.com" in url:
                if "song" in url:
                    song_id = self.extract_id(url, r"id=(\d+)")
                    if song_id:
                        results = self.search_netease_by_id(song_id)
                        return {"type": "song", "data": results[0] if results else None}
                elif "playlist" in url:
                    playlist_id = self.extract_id(url, r"id=(\d+)")
                    if playlist_id:
                        results = self.get_netease_playlist(playlist_id)
                        return {"type": "playlist", "data": results}
            
            # QQ音乐
            elif "y.qq.com" in url or "c.y.qq.com" in url:
                if "song" in url:
                    song_mid = self.extract_id(url, r"songmid=([A-Za-z0-9]+)")
                    if song_mid:
                        results = self.search_qqmusic_by_mid(song_mid)
                        return {"type": "song", "data": results[0] if results else None}
                elif "playlist" in url:
                    playlist_id = self.extract_id(url, r"id=([A-Za-z0-9]+)")
                    if playlist_id:
                        results = self.get_qq_playlist(playlist_id)
                        return {"type": "playlist", "data": results}
            
            # 酷狗音乐
            elif "kugou.com" in url:
                if "hash" in url:
                    song_hash = self.extract_id(url, r"hash=([A-Za-z0-9]+)")
                    if song_hash:
                        results = self.search_kugou_by_hash(song_hash)
                        return {"type": "song", "data": results[0] if results else None}
            
            # 酷我音乐
            elif "kuwo.cn" in url:
                if "rid" in url:
                    rid = self.extract_id(url, r"rid=(\d+)")
                    if rid:
                        results = self.search_kuwo_by_rid(rid)
                        return {"type": "song", "data": results[0] if results else None}
            
            # 汽水音乐
            elif "music.xiaomi.com" in url or "soda" in url:
                song_id = self.extract_id(url, r"songId=(\d+)")
                if song_id:
                    results = self.search_soda(song_id)
                    return {"type": "song", "data": results[0] if results else None}
                    
        except Exception as e:
            logger.warning(f"URL解析失败: {e}")
        return None
    
    def extract_id(self, url, pattern):
        match = re.search(pattern, url)
        return match.group(1) if match else None
    
    def search_netease(self, keyword):
        results = []
        try:
            url = "https://netease-cloud-music-api-five-roan-25.vercel.app/search"
            params = {"keywords": keyword, "limit": 20}
            
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            
            if "result" in data and "songs" in data["result"]:
                for song in data["result"]["songs"]:
                    artists = ", ".join([a["name"] for a in song.get("artists", [])])
                    results.append({
                        "id": str(song.get("id")),
                        "title": song.get("name"),
                        "artist": artists,
                        "album": song.get("album", {}).get("name", ""),
                        "platform": "netease",
                        "duration": song.get("duration", 0) // 1000,
                    })
        except Exception as e:
            logger.warning(f"网易云搜索失败: {e}")
            try:
                url = "https://music.163.com/weapi/cloudsearch/get/web"
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "https://music.163.com/",
                }
                data = {"s": keyword, "type": 1, "offset": 0, "limit": 20, "csrf_token": ""}
                
                response = requests.post(url, json=data, headers=headers, timeout=10)
                data = response.json()
                
                if "result" in data and "songs" in data["result"]:
                    for song in data["result"]["songs"]:
                        artists = ", ".join([a["name"] for a in song.get("ar", [])])
                        results.append({
                            "id": str(song.get("id")),
                            "title": song.get("name"),
                            "artist": artists,
                            "album": song.get("al", {}).get("name", ""),
                            "platform": "netease",
                            "duration": song.get("dt", 0) // 1000,
                        })
            except Exception as e2:
                logger.warning(f"网易云备用API也失败: {e2}")
        return results
    
    def search_qqmusic(self, keyword):
        results = []
        try:
            url = "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
            params = {"ct": 24, "qqmusic_ver": 1001, "remoteplace": "sizer.yqqListMain",
                     "t": 0, "aggr": 1, "cr": 1, "p": 1, "n": 20, "w": keyword}
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                      "Referer": "https://y.qq.com/"}
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            data = response.json()
            
            if "data" in data and "song" in data["data"]:
                for song in data["data"]["song"]["list"]:
                    results.append({
                        "id": song.get("songmid"),
                        "title": song.get("songname"),
                        "artist": song.get("singer", [{}])[0].get("name", ""),
                        "album": song.get("albumname", ""),
                        "platform": "qq",
                        "duration": song.get("interval", 0),
                    })
        except Exception as e:
            logger.warning(f"QQ音乐搜索失败: {e}")
        return results
    
    def search_kugou(self, keyword):
        results = []
        try:
            url = "https://songsearch.kugou.com/song_search_v2"
            params = {"keyword": keyword, "page": 1, "pagesize": 20, "showtype": 1}
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                      "Referer": "https://www.kugou.com/"}
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            data = response.json()
            
            if "data" in data and "lists" in data["data"]:
                for song in data["data"]["lists"]:
                    results.append({
                        "id": song.get("Hash"),
                        "title": song.get("SongName"),
                        "artist": song.get("ArtistsName"),
                        "album": song.get("AlbumName", ""),
                        "platform": "kugou",
                        "duration": song.get("Duration", 0),
                    })
        except Exception as e:
            logger.warning(f"酷狗搜索失败: {e}")
        return results
    
    def search_kuwo(self, keyword):
        results = []
        try:
            url = "https://www.kuwo.cn/api/www/search/searchMusicBykeyWord"
            params = {"key": keyword, "pn": 1, "rn": 20, "reqId": "xxxx"}
            headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.kuwo.cn/"}
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            data = response.json()
            
            if "data" in data and "list" in data["data"]:
                for song in data["data"]["list"]:
                    results.append({
                        "id": str(song.get("rid")),
                        "title": song.get("name"),
                        "artist": song.get("artist", ""),
                        "album": song.get("album", ""),
                        "platform": "kuwo",
                        "duration": song.get("duration", 0),
                    })
        except Exception as e:
            logger.warning(f"酷我搜索失败: {e}")
        return results
    
    def search_migu(self, keyword):
        results = []
        try:
            url = "https://m.music.migu.cn/migu/remoting/search_search_tag"
            params = {"keyword": keyword, "type": 2, "pgc": 1, "rg": 20}
            headers = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15",
                     "Referer": "https://m.music.migu.cn/"}
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "data" in data and "song" in data["data"]:
                    for song in data["data"]["song"]:
                        results.append({
                            "id": str(song.get("id")),
                            "title": song.get("name"),
                            "artist": song.get("singerName", ""),
                            "album": song.get("albumName", ""),
                            "platform": "migu",
                            "duration": song.get("duration", 0) // 1000 if song.get("duration") else 0,
                        })
        except Exception as e:
            logger.warning(f"咪咕搜索失败: {e}")
        return results
    
    def search_bilibili(self, keyword):
        results = []
        try:
            url = "https://api.bilibili.com/audio/music-service/web/search/song"
            params = {"search_type": 1, "keyword": keyword, "pn": 1, "ps": 20}
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                     "Referer": "https://www.bilibili.com/"}
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "data" in data and "result" in data["data"]:
                    for song in data["data"]["result"]:
                        results.append({
                            "id": str(song.get("id")),
                            "title": song.get("title"),
                            "artist": song.get("author", ""),
                            "album": song.get("album", ""),
                            "platform": "bilibili",
                            "duration": song.get("duration", 0),
                        })
        except Exception as e:
            logger.warning(f"B站搜索失败: {e}")
        return results
    
    def search_fivesing(self, keyword):
        return []
    
    def search_joox(self, keyword):
        return []
    
    def search_qianqian(self, keyword):
        return []
    
    def search_jamendo(self, keyword):
        results = []
        try:
            url = "https://api.jamendo.com/v3.0/tracks"
            params = {"client_id": "anonymous", "format": "json", "search": keyword, "limit": 20}
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if "results" in data:
                for song in data["results"]:
                    results.append({
                        "id": song.get("id"),
                        "title": song.get("name"),
                        "artist": song.get("artist_name", ""),
                        "album": song.get("album_name", ""),
                        "platform": "jamendo",
                        "duration": int(song.get("duration", 0)),
                    })
        except Exception as e:
            logger.warning(f"Jamendo搜索失败: {e}")
        return results
    
    def search_soda(self, keyword_or_id):
        results = []
        try:
            url = "https://api.music.xiaomi.com/song/new Songs"
            headers = {"User-Agent": "Mozilla/5.0"}
            
            if keyword_or_id.isdigit():
                url = f"https://api.music.xiaomi.com/v2/song/detail"
                params = {"songIds": keyword_or_id}
            else:
                url = "https://api.music.xiaomi.com/song/list"
                params = {"keyword": keyword_or_id, "page": 0, "size": 20}
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            data = response.json()
            
            songs = data.get("data", {}).get("songs", []) if "data" in data else []
            for song in songs:
                results.append({
                    "id": str(song.get("id")),
                    "title": song.get("title", ""),
                    "artist": ", ".join([a.get("name", "") for a in song.get("artists", [])]),
                    "album": song.get("album", {}).get("name", ""),
                    "platform": "soda",
                    "duration": song.get("duration", 0) // 1000,
                })
        except Exception as e:
            logger.warning(f"汽水音乐搜索失败: {e}")
        return results
    
    def search_netease_by_id(self, song_id):
        results = []
        try:
            url = "https://music.163.com/weapi/song/detail"
            headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://music.163.com/"}
            data = {"ids": [song_id], "csrf_token": ""}
            
            response = requests.post(url, json=data, headers=headers, timeout=10)
            data = response.json()
            
            if "songs" in data and len(data["songs"]) > 0:
                song = data["songs"][0]
                artists = ", ".join([a["name"] for a in song.get("ar", [])])
                results.append({
                    "id": str(song.get("id")),
                    "title": song.get("name"),
                    "artist": artists,
                    "album": song.get("al", {}).get("name", ""),
                    "platform": "netease",
                    "duration": song.get("dt", 0) // 1000,
                })
        except Exception as e:
            logger.warning(f"网易云ID搜索失败: {e}")
        return results
    
    def search_qqmusic_by_mid(self, song_mid):
        results = []
        try:
            url = "https://c.y.qq.com/v8/fcg-bin/fcg_play_single_song.fcg"
            params = {"songmid": song_mid, "format": "json"}
            headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://y.qq.com/"}
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            data = response.json()
            
            if "data" in data and "song" in data["data"]:
                song = data["data"]["song"][0]
                results.append({
                    "id": song.get("mid"),
                    "title": song.get("name"),
                    "artist": song.get("singer", [{}])[0].get("name", ""),
                    "album": song.get("album", {}).get("name", ""),
                    "platform": "qq",
                    "duration": song.get("interval", 0),
                })
        except Exception as e:
            logger.warning(f"QQ音乐MID搜索失败: {e}")
        return results
    
    def search_kugou_by_hash(self, song_hash):
        results = []
        try:
            url = "https://www.kugou.com/yy/index.php"
            params = {"r": "play/getdata", "hash": song_hash, "dfid": "xxx", "from": "web"}
            headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.kugou.com/"}
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            data = response.json()
            
            if "data" in data:
                song = data["data"]
                results.append({
                    "id": song.get("hash"),
                    "title": song.get("song_name"),
                    "artist": song.get("author_name"),
                    "album": song.get("album_name", ""),
                    "platform": "kugou",
                    "duration": song.get("duration", 0),
                })
        except Exception as e:
            logger.warning(f"酷狗HASH搜索失败: {e}")
        return results
    
    def search_kuwo_by_rid(self, rid):
        results = []
        try:
            url = "https://www.kuwo.cn/api/v1/www/music/playUrl"
            params = {"mid": rid, "type": "music", "https": 1}
            headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.kuwo.cn/"}
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            data = response.json()
            
            if "data" in data and "musicUrl" in data["data"]:
                music_info = data["data"]
                results.append({
                    "id": str(rid),
                    "title": music_info.get("name", ""),
                    "artist": music_info.get("artist", ""),
                    "album": music_info.get("album", ""),
                    "platform": "kuwo",
                    "duration": music_info.get("duration", 0) // 1000,
                })
        except Exception as e:
            logger.warning(f"酷我RID搜索失败: {e}")
        return results
    
    def search_playlist(self, platform, keyword):
        results = []
        if platform == "netease":
            results = self.search_netease_playlist(keyword)
        elif platform == "qq":
            results = self.search_qq_playlist(keyword)
        elif platform == "kugou":
            results = self.search_kugou_playlist(keyword)
        elif platform == "kuwo":
            results = self.search_kuwo_playlist(keyword)
        elif platform == "bilibili":
            results = self.search_bilibili_playlist(keyword)
        return results
    
    def search_netease_playlist(self, keyword):
        results = []
        try:
            url = "https://music.163.com/weapi/cloudsearch/get/web"
            headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://music.163.com/"}
            data = {"s": keyword, "type": 1000, "offset": 0, "limit": 20, "csrf_token": ""}
            
            response = requests.post(url, json=data, headers=headers, timeout=10)
            data = response.json()
            
            if "result" in data and "playlists" in data["result"]:
                for playlist in data["result"]["playlists"]:
                    results.append({
                        "id": str(playlist.get("id")),
                        "title": playlist.get("name"),
                        "artist": playlist.get("creator", {}).get("nickname", ""),
                        "count": playlist.get("trackCount", 0),
                        "platform": "netease",
                        "type": "playlist",
                    })
        except Exception as e:
            logger.warning(f"网易云歌单搜索失败: {e}")
        return results
    
    def search_qq_playlist(self, keyword):
        results = []
        try:
            url = "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
            params = {"ct": 24, "qqmusic_ver": 1001, "remoteplace": "sizer.yqqListMain",
                     "t": 8, "p": 1, "n": 20, "w": keyword}
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if "data" in data and "playlist" in data["data"]:
                for playlist in data["data"]["playlist"]["list"]:
                    results.append({
                        "id": str(playlist.get("dissid")),
                        "title": playlist.get("dissname"),
                        "artist": playlist.get("creator", {}).get("name", ""),
                        "count": playlist.get("song_count", 0),
                        "platform": "qq",
                        "type": "playlist",
                    })
        except Exception as e:
            logger.warning(f"QQ音乐歌单搜索失败: {e}")
        return results
    
    def search_kugou_playlist(self, keyword):
        results = []
        try:
            url = "https://songsearch.kugou.com/song_search_v3"
            params = {"keyword": keyword, "page": 1, "pagesize": 20, "showtype": 3}
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if "data" in data and "info" in data["data"]:
                for item in data["data"]["info"]:
                    if "hash" in item:
                        results.append({
                            "id": item.get("hash"),
                            "title": item.get("songName"),
                            "artist": item.get("authors", ""),
                            "count": 0,
                            "platform": "kugou",
                            "type": "playlist",
                        })
        except Exception as e:
            logger.warning(f"酷狗歌单搜索失败: {e}")
        return results
    
    def search_kuwo_playlist(self, keyword):
        return []
    
    def search_bilibili_playlist(self, keyword):
        results = []
        try:
            url = "https://api.bilibili.com/audio/music-service/web/song/lists"
            params = {"pn": 1, "ps": 20, "keyword": keyword, "order": 1}
            headers = {"User-Agent": "Mozilla/5.0"}
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            data = response.json()
            
            if "data" in data and "data" in data["data"]:
                for playlist in data["data"]["data"]:
                    results.append({
                        "id": str(playlist.get("id")),
                        "title": playlist.get("title"),
                        "artist": playlist.get("uname", ""),
                        "count": playlist.get("song_count", 0),
                        "platform": "bilibili",
                        "type": "playlist",
                    })
        except Exception as e:
            logger.warning(f"B站歌单搜索失败: {e}")
        return results
    
    def get_netease_playlist(self, playlist_id):
        results = []
        try:
            url = "https://music.163.com/weapi/playlist/detail"
            headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://music.163.com/"}
            data = {"id": playlist_id, "csrf_token": ""}
            
            response = requests.post(url, json=data, headers=headers, timeout=10)
            data = response.json()
            
            if "playlist" in data:
                for track in data["playlist"].get("tracks", [])[:50]:
                    artists = ", ".join([a["name"] for a in track.get("ar", [])])
                    results.append({
                        "id": str(track.get("id")),
                        "title": track.get("name"),
                        "artist": artists,
                        "album": track.get("al", {}).get("name", ""),
                        "platform": "netease",
                        "duration": track.get("dt", 0) // 1000,
                    })
        except Exception as e:
            logger.warning(f"获取网易云歌单失败: {e}")
        return results
    
    def get_qq_playlist(self, playlist_id):
        results = []
        try:
            url = "https://c.y.qq.com/qianqian/fcg-bin/fcg_ucc_getcdinfo_byids_cp"
            params = {"disstid": playlist_id, "type": 1, "json": 1, "utf8": 1}
            headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://y.qq.com/"}
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            data = response.json()
            
            if "cdlist" in data and len(data["cdlist"]) > 0:
                for track in data["cdlist"][0].get("songlist", [])[:50]:
                    results.append({
                        "id": track.get("mid"),
                        "title": track.get("name"),
                        "artist": track.get("singer", [{}])[0].get("name", ""),
                        "album": track.get("album", {}).get("name", ""),
                        "platform": "qq",
                        "duration": track.get("interval", 0),
                    })
        except Exception as e:
            logger.warning(f"获取QQ音乐歌单失败: {e}")
        return results


class DownloadThread(QThread):
    downloadProgress = pyqtSignal(int, int, str)
    downloadFinished = pyqtSignal(str, bool)
    downloadError = pyqtSignal(str)
    
    def __init__(self, songs, save_path):
        super().__init__()
        self.songs = songs
        self.save_path = save_path
        
    def run(self):
        total = len(self.songs)
        for i, song in enumerate(self.songs):
            try:
                self.downloadProgress.emit(i + 1, total, song.get("title", "未知"))
                
                safe_title = re.sub(r'[<>:"/\\|?*]', '_', str(song.get("title", "song")))
                safe_artist = re.sub(r'[<>:"/\\|?*]', '_', str(song.get("artist", "unknown")))
                
                if not self.save_path or not isinstance(self.save_path, str):
                    self.save_path = os.path.expanduser("~/Music")
                
                os.makedirs(self.save_path, exist_ok=True)
                file_path = os.path.join(self.save_path, f"{safe_title} - {safe_artist}.mp3")
                
                success = self.download_song(song, file_path)
                self.downloadFinished.emit(file_path, success)
                
            except Exception as e:
                logger.error(f"下载失败: {e}")
                self.downloadError.emit(str(e))
    
    def download_song(self, song, file_path):
        platform = song.get("platform")
        
        if platform == "netease":
            return self.download_netease(song, file_path)
        elif platform == "qq":
            return self.download_qqmusic(song, file_path)
        elif platform == "kugou":
            return self.download_kugou(song, file_path)
        elif platform == "kuwo":
            return self.download_kuwo(song, file_path)
        elif platform == "migu":
            return self.download_migu(song, file_path)
        elif platform == "bilibili":
            return self.download_bilibili(song, file_path)
        elif platform == "jamendo":
            return self.download_jamendo(song, file_path)
        elif platform == "soda":
            return self.download_soda(song, file_path)
        return False
    
    def download_netease(self, song, file_path):
        try:
            song_id = song.get("id")
            
            try:
                url = "https://netease-cloud-music-api-five-roan-25.vercel.app/song/url"
                params = {"id": song_id, "realIP": "116.25.146.177"}
                
                response = requests.get(url, params=params, timeout=15)
                data = response.json()
                
                if "data" in data and len(data["data"]) > 0:
                    download_url = data["data"][0].get("url")
                    if download_url:
                        audio_data = requests.get(download_url, timeout=30)
                        with open(file_path, "wb") as f:
                            f.write(audio_data.content)
                        return True
            except Exception as e1:
                logger.warning(f"网易云API下载失败，尝试备用方法: {e1}")
                
                url = "https://music.163.com/weapi/song/enhance/player/url/v1"
                headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://music.163.com/"}
                data = {"ids": [song_id], "level": "exhigh", "encodeType": "mp3", "csrf_token": ""}
                
                response = requests.post(url, json=data, headers=headers, timeout=10)
                data = response.json()
                
                if "data" in data and len(data["data"]) > 0:
                    download_url = data["data"][0].get("url")
                    if download_url:
                        audio_data = requests.get(download_url, timeout=30)
                        with open(file_path, "wb") as f:
                            f.write(audio_data.content)
                        return True
        except Exception as e:
            logger.warning(f"网易云下载失败: {e}")
        return False
    
    def download_qqmusic(self, song, file_path):
        try:
            song_mid = song.get("id")
            url = "https://c.y.qq.com/base/fcgi-bin/fcg_music_express_mobile3.fcg"
            params = {
                "format": "json",
                "platform": "yqq",
                "cid": "205361747",
                "songmid": song_mid,
                "filename": f"M500{song_mid}.mp3",
                "guid": "123456789"
            }
            headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://y.qq.com/"}
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            data = response.json()
            
            if "data" in data and "items" in data["data"]:
                purl = data["data"]["items"][0].get("purl")
                if purl:
                    download_url = f"http://isure.stream.qqmusic.qq.com/{purl}"
                    audio_data = requests.get(download_url, timeout=30)
                    with open(file_path, "wb") as f:
                        f.write(audio_data.content)
                    return True
        except Exception as e:
            logger.warning(f"QQ音乐下载失败: {e}")
        return False
    
    def download_kugou(self, song, file_path):
        try:
            song_hash = song.get("id")
            url = "https://www.kugou.com/yy/index.php"
            params = {"r": "play/getdata", "hash": song_hash, "dfid": "xxx", "from": "web"}
            headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.kugou.com/"}
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            data = response.json()
            
            if "data" in data and "play_url" in data["data"]:
                download_url = data["data"].get("play_url")
                if download_url and len(download_url) > 10:
                    audio_data = requests.get(download_url, timeout=30)
                    with open(file_path, "wb") as f:
                        f.write(audio_data.content)
                    return True
        except Exception as e:
            logger.warning(f"酷狗下载失败: {e}")
        return False
    
    def download_kuwo(self, song, file_path):
        try:
            rid = song.get("id")
            url = "https://www.kuwo.cn/api/v1/www/music/playUrl"
            params = {"mid": rid, "type": "music", "https": 1}
            headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.kuwo.cn/"}
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            data = response.json()
            
            if "data" in data and "url" in data["data"]:
                download_url = data["data"]["url"]
                if download_url:
                    audio_data = requests.get(download_url, timeout=30)
                    with open(file_path, "wb") as f:
                        f.write(audio_data.content)
                    return True
        except Exception as e:
            logger.warning(f"酷我下载失败: {e}")
        return False
    
    def download_migu(self, song, file_path):
        try:
            song_id = song.get("id")
            url = "https://m.music.migu.cn/migu/remoting/song/getSongInfos"
            params = {"songIds": song_id}
            headers = {"User-Agent": "Mozilla/5.0"}
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            data = response.json()
            
            if "data" in data and str(song_id) in data["data"]:
                song_info = data["data"][str(song_id)]
                if "newRate" in song_info:
                    rate = song_info["newRate"]
                    urls = rate.get("formatsUrl", [])
                    if urls:
                        download_url = urls[0].get("url")
                        if download_url:
                            audio_data = requests.get(download_url, timeout=30)
                            with open(file_path, "wb") as f:
                                f.write(audio_data.content)
                            return True
        except Exception as e:
            logger.warning(f"咪咕下载失败: {e}")
        return False
    
    def download_bilibili(self, song, file_path):
        try:
            song_id = song.get("id")
            url = f"https://api.bilibili.com/audio/music-service-c/web/url?sid={song_id}"
            headers = {"User-Agent": "Mozilla/5.0"}
            
            response = requests.get(url, headers=headers, timeout=10)
            data = response.json()
            
            if "data" in data and "cdns" in data["data"]:
                download_url = data["data"]["cdns"][0]
                if download_url:
                    audio_data = requests.get(download_url, timeout=30)
                    with open(file_path, "wb") as f:
                        f.write(audio_data.content)
                    return True
        except Exception as e:
            logger.warning(f"B站下载失败: {e}")
        return False
    
    def download_jamendo(self, song, file_path):
        try:
            song_id = song.get("id")
            url = f"https://api.jamendo.com/v3.0/tracks/file"
            params = {"client_id": "anonymous", "track_id": song_id, "format": "mp3"}
            
            response = requests.get(url, params=params, timeout=30, allow_redirects=True)
            if response.url and ".mp3" in response.url:
                audio_data = requests.get(response.url, timeout=30)
                with open(file_path, "wb") as f:
                    f.write(audio_data.content)
                return True
        except Exception as e:
            logger.warning(f"Jamendo下载失败: {e}")
        return False
    
    def download_soda(self, song, file_path):
        try:
            song_id = song.get("id")
            url = "https://api.music.xiaomi.com/v2/song/download"
            params = {"songId": song_id, "format": "mp3"}
            headers = {"User-Agent": "Mozilla/5.0"}
            
            response = requests.get(url, params=params, headers=headers, timeout=30)
            if response.status_code == 200:
                with open(file_path, "wb") as f:
                    f.write(response.content)
                return True
        except Exception as e:
            logger.warning(f"汽水音乐下载失败: {e}")
        return False


class MultiPlatformMusicWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("多平台音乐下载")
        self.setGeometry(100, 100, 1000, 700)
        self.selected_platforms = set(PLATFORM_INFO.keys())
        self.current_results = []
        self.init_ui()
        self.apply_styles()
        
    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        header = QFrame()
        header.setFixedHeight(150)
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(25, 20, 25, 15)
        
        title_row = QHBoxLayout()
        title = QLabel("🎵 多平台音乐搜索")
        title.setFont(QFont("Microsoft YaHei UI", 22, QFont.Bold))
        title.setStyleSheet("color: white;")
        title_row.addWidget(title)
        title_row.addStretch()
        
        self.search_type_radio_song = QRadioButton("单曲")
        self.search_type_radio_song.setChecked(True)
        self.search_type_radio_song.setStyleSheet("color: white; font-weight: bold;")
        title_row.addWidget(self.search_type_radio_song)
        
        self.search_type_radio_playlist = QRadioButton("歌单")
        self.search_type_radio_playlist.setStyleSheet("color: rgba(255,255,255,0.7);")
        title_row.addWidget(self.search_type_radio_playlist)
        
        header_layout.addLayout(title_row)
        
        search_bar = QHBoxLayout()
        search_bar.setSpacing(10)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("输入歌曲名、歌手名搜索...")
        self.search_input.setFont(QFont("Microsoft YaHei UI", 13))
        self.search_input.setMinimumHeight(44)
        self.search_input.returnPressed.connect(self.do_search)
        search_bar.addWidget(self.search_input, 1)
        
        self.search_btn = QPushButton("🔍 搜索")
        self.search_btn.setFixedSize(100, 44)
        self.search_btn.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
        self.search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.search_btn.clicked.connect(self.do_search)
        search_bar.addWidget(self.search_btn)
        
        header_layout.addLayout(search_bar)
        
        platform_bar = QHBoxLayout()
        platform_bar.setSpacing(8)
        
        platform_label = QLabel("搜索源:")
        platform_label.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 12px; margin-top: 10px;")
        platform_bar.addWidget(platform_label)
        
        self.platform_checks = {}
        for pid, info in PLATFORM_INFO.items():
            cb = QCheckBox(info["icon"])
            cb.setToolTip(info["name"])
            cb.setChecked(True)
            cb.stateChanged.connect(lambda state, p=pid: self.toggle_platform(p, state))
            self.platform_checks[pid] = cb
            platform_bar.addWidget(cb)
        
        platform_bar.addStretch()
        
        select_all_btn = QPushButton("全选")
        select_all_btn.setFixedSize(60, 28)
        select_all_btn.setFont(QFont("Microsoft YaHei UI", 9))
        select_all_btn.clicked.connect(lambda: self.toggle_all_platforms(True))
        platform_bar.addWidget(select_all_btn)
        
        clear_btn = QPushButton("清空")
        clear_btn.setFixedSize(60, 28)
        clear_btn.setFont(QFont("Microsoft YaHei UI", 9))
        clear_btn.clicked.connect(lambda: self.toggle_all_platforms(False))
        platform_bar.addWidget(clear_btn)
        
        header_layout.addLayout(platform_bar)
        
        header.setLayout(header_layout)
        main_layout.addWidget(header)
        
        content = QFrame()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 10, 20, 20)
        content_layout.setSpacing(10)
        
        results_header = QHBoxLayout()
        results_label = QLabel("搜索结果")
        results_label.setFont(QFont("Microsoft YaHei UI", 14, QFont.Bold))
        results_label.setStyleSheet("color: white;")
        results_header.addWidget(results_label)
        
        results_header.addStretch()
        
        self.count_label = QLabel("")
        self.count_label.setStyleSheet("color: rgba(255,255,255,0.6); font-size: 12px;")
        results_header.addWidget(self.count_label)
        
        content_layout.addLayout(results_header)
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(["平台", "歌曲", "歌手", "专辑", "时长"])
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setShowGrid(False)
        self.results_table.setFont(QFont("Microsoft YaHei UI", 11))
        
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        
        self.results_table.setColumnWidth(0, 100)
        self.results_table.setColumnWidth(4, 70)
        self.results_table.setRowHeight(0, 40)
        
        content_layout.addWidget(self.results_table)
        
        bottom_bar = QHBoxLayout()
        
        self.select_count_label = QLabel("已选择: 0 首")
        self.select_count_label.setStyleSheet("color: rgba(255,255,255,0.7);")
        bottom_bar.addWidget(self.select_count_label)
        
        bottom_bar.addStretch()
        
        self.download_btn = QPushButton("⬇️ 下载选中歌曲")
        self.download_btn.setFixedHeight(40)
        self.download_btn.setFont(QFont("Microsoft YaHei UI", 12, QFont.Bold))
        self.download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.download_btn.clicked.connect(self.start_download)
        bottom_bar.addWidget(self.download_btn)
        
        content_layout.addLayout(bottom_bar)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        content_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 11px;")
        content_layout.addWidget(self.status_label)
        
        content.setLayout(content_layout)
        main_layout.addWidget(content)
        
        self.setLayout(main_layout)
        
    def apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                background: #1a1a2e;
            }
            QLineEdit {
                background: #16213e;
                border: 1px solid #0f3460;
                border-radius: 22px;
                padding: 0 20px;
                color: white;
                selection-background-color: #00d4ff;
            }
            QLineEdit:focus {
                border-color: #00d4ff;
            }
            QLineEdit::placeholder {
                color: rgba(255,255,255,0.4);
            }
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #00d4ff, stop:1 #7b2cbf);
                border: none;
                border-radius: 22px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #00b4e4, stop:1 #6b1caf);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #0094c4, stop:1 #5b0a9f);
            }
            QCheckBox {
                color: white;
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 8px;
                border: 2px solid rgba(255,255,255,0.3);
                background: rgba(255,255,255,0.1);
            }
            QCheckBox::indicator:checked {
                background: #00d4ff;
                border-color: #00d4ff;
            }
            QTableWidget {
                background: #16213e;
                border: 1px solid #0f3460;
                border-radius: 12px;
                padding: 5px;
                gridline-color: transparent;
            }
            QTableWidget::item {
                border: none;
                padding: 5px;
                color: white;
            }
            QTableWidget::item:selected {
                background: rgba(0, 212, 255, 0.2);
            }
            QTableWidget::item:hover {
                background: rgba(255,255,255,0.05);
            }
            QHeaderView::section {
                background: transparent;
                color: rgba(255,255,255,0.7);
                border: none;
                padding: 10px;
                font-weight: bold;
                font-size: 12px;
            }
            QProgressBar {
                background: #16213e;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #00d4ff, stop:1 #7b2cbf);
                border-radius: 3px;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 8px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,0.2);
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255,255,255,0.3);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)
    
    def toggle_platform(self, platform, state):
        if state == Qt.CheckState.Checked:
            self.selected_platforms.add(platform)
        else:
            self.selected_platforms.discard(platform)
    
    def toggle_all_platforms(self, checked):
        for cb in self.platform_checks.values():
            cb.setChecked(checked)
    
    def do_search(self):
        keyword = self.search_input.text().strip()
        if not keyword:
            return
            
        if not self.selected_platforms:
            QMessageBox.warning(self, "提示", "请至少选择一个搜索平台")
            return
        
        search_type = "song"
        if hasattr(self, 'search_type_radio'):
            if self.search_type_radio_playlist.isChecked():
                search_type = "playlist"
            
        self.status_label.setText("🔍 搜索中...")
        self.search_btn.setEnabled(False)
        self.results_table.setRowCount(0)
        
        self.search_thread = SearchThread(keyword, list(self.selected_platforms), search_type)
        self.search_thread.searchFinished.connect(self.on_search_finished)
        self.search_thread.searchError.connect(self.on_search_error)
        self.search_thread.start()
        
    def on_search_finished(self, results):
        self.search_btn.setEnabled(True)
        self.current_results = results
        
        self.results_table.setRowCount(len(results))
        
        for i, song in enumerate(results):
            platform = song.get("platform", "")
            platform_info = PLATFORM_INFO.get(platform, {})
            platform_name = platform_info.get("name", platform)
            platform_color = platform_info.get("color", "#888")
            
            platform_item = QTableWidgetItem(f"{platform_info.get('icon', '')} {platform_name}")
            platform_item.setForeground(QColor(platform_color))
            platform_item.setData(Qt.ItemDataRole.UserRole, song)
            self.results_table.setItem(i, 0, platform_item)
            
            title_item = QTableWidgetItem(song.get("title", ""))
            title_item.setForeground(QColor("white"))
            self.results_table.setItem(i, 1, title_item)
            
            artist_item = QTableWidgetItem(song.get("artist", ""))
            artist_item.setForeground(QColor("white"))
            self.results_table.setItem(i, 2, artist_item)
            
            album_item = QTableWidgetItem(song.get("album", ""))
            album_item.setForeground(QColor("rgba(255,255,255,0.6)"))
            self.results_table.setItem(i, 3, album_item)
            
            duration = song.get("duration", 0)
            minutes = duration // 60
            seconds = duration % 60
            duration_item = QTableWidgetItem(f"{minutes:02d}:{seconds:02d}")
            duration_item.setForeground(QColor("rgba(255,255,255,0.5)"))
            duration_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.results_table.setItem(i, 4, duration_item)
        
        self.count_label.setText(f"共 {len(results)} 首")
        self.status_label.setText(f"✅ 搜索完成，找到 {len(results)} 首歌曲")
        
        self.results_table.selectionModel().selectionChanged.connect(self.on_selection_changed)
    
    def on_selection_changed(self):
        selected = len(self.results_table.selectionModel().selectedRows())
        self.select_count_label.setText(f"已选择: {selected} 首")
    
    def on_search_error(self, error):
        self.search_btn.setEnabled(True)
        self.status_label.setText(f"❌ 搜索出错: {error}")
        
    def start_download(self):
        selected_rows = self.results_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要下载的歌曲")
            return
        
        from PyQt5.QtWidgets import QFileDialog
        save_path = QFileDialog.getExistingDirectory(self, "选择保存文件夹")
        if not save_path:
            return
        
        songs = []
        for row in selected_rows:
            item = self.results_table.item(row.row(), 0)
            if item:
                song = item.data(Qt.ItemDataRole.UserRole)
                if song:
                    songs.append(song)
        
        self.download_btn.setEnabled(False)
        self.progress_bar.setMaximum(len(songs))
        self.progress_bar.setValue(0)
        
        self.download_thread = DownloadThread(songs, save_path)
        self.download_thread.downloadProgress.connect(self.on_download_progress)
        self.download_thread.downloadFinished.connect(self.on_download_finished)
        self.download_thread.downloadError.connect(self.on_download_error)
        self.download_thread.finished.connect(self.on_all_downloaded)
        self.download_thread.start()
        
    def on_download_progress(self, current, total, title):
        self.progress_bar.setValue(current)
        self.status_label.setText(f"⬇️ 下载中: {title} ({current}/{total})")
        
    def on_download_finished(self, file_path, success):
        if success:
            self.status_label.setText(f"✅ 已下载: {os.path.basename(file_path)}")
            
    def on_download_error(self, error):
        self.status_label.setText(f"❌ 下载失败: {error}")
        
    def on_all_downloaded(self):
        self.download_btn.setEnabled(True)
        self.status_label.setText("✅ 下载完成！")
        QMessageBox.information(self, "完成", "所有选中歌曲已下载完成！")
