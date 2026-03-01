"""
Music Hub 后端API
提供多平台音乐搜索和下载接口
"""

import json
import re
import requests
import logging
import os
from flask import Blueprint, request, jsonify, send_file
from flask_cors import CORS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MusicHub")

music_bp = Blueprint('music', __name__, url_prefix='/api/music')
CORS(music_bp)

PLATFORM_INFO = {
    "netease": {"name": "网易云音乐", "color": "#E62117"},
    "qq": {"name": "QQ音乐", "color": "#12B7F5"},
    "kugou": {"name": "酷狗音乐", "color": "#FF6900"},
    "kuwo": {"name": "酷我音乐", "color": "#FF6600"},
    "migu": {"name": "咪咕音乐", "color": "#00B37E"},
    "bilibili": {"name": "B站音乐", "color": "#FB7299"},
    "fivesing": {"name": "5sing", "color": "#FF6B6B"},
    "joox": {"name": "JOOX", "color": "#6B4EFF"},
    "qianqian": {"name": "千千音乐", "color": "#00A0E9"},
    "jamendo": {"name": "Jamendo", "color": "#1DB954"},
}


def search_netease(keyword):
    results = []
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
                    "picUrl": song.get("al", {}).get("picUrl", ""),
                })
    except Exception as e:
        logger.warning(f"网易云搜索失败: {e}")
    return results


def search_qqmusic(keyword):
    results = []
    try:
        url = "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
        params = {"ct": 24, "qqmusic_ver": 1001, "remoteplace": "sizer.yqqListMain",
                 "t": 0, "aggr": 1, "cr": 1, "p": 1, "n": 20, "w": keyword}
        
        response = requests.get(url, params=params, timeout=10)
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
                    "picUrl": f"https://y.gtimg.cn/music/photo_new/T002R300x300M000{song.get('albummid', '')}.jpg",
                })
    except Exception as e:
        logger.warning(f"QQ音乐搜索失败: {e}")
    return results


def search_kugou(keyword):
    results = []
    try:
        url = "https://songsearch.kugou.com/song_search_v2"
        params = {"keyword": keyword, "page": 1, "pagesize": 20, "showtype": 1}
        
        response = requests.get(url, params=params, timeout=10)
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
                    "picUrl": song.get("ImgUrl", "").replace("{size}", "400"),
                })
    except Exception as e:
        logger.warning(f"酷狗搜索失败: {e}")
    return results


def search_kuwo(keyword):
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
                    "picUrl": song.get("pic", ""),
                })
    except Exception as e:
        logger.warning(f"酷我搜索失败: {e}")
    return results


def search_migu(keyword):
    results = []
    try:
        url = "https://m.music.migu.cn/migu/remoting/search_search_tag"
        params = {"keyword": keyword, "type": 2, "pgc": 1, "rg": 20}
        headers = {"User-Agent": "Mozilla/5.0"}
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        data = response.json()
        
        if "data" in data and "song" in data["data"]:
            for song in data["data"]["song"]:
                results.append({
                    "id": str(song.get("id")),
                    "title": song.get("name"),
                    "artist": song.get("singerName", ""),
                    "album": song.get("albumName", ""),
                    "platform": "migu",
                    "duration": song.get("duration", 0) // 1000,
                    "picUrl": song.get("mp3PicUrl", ""),
                })
    except Exception as e:
        logger.warning(f"咪咕搜索失败: {e}")
    return results


def search_bilibili(keyword):
    results = []
    try:
        url = "https://api.bilibili.com/audio/music-service/web/search/song"
        params = {"search_type": 1, "keyword": keyword, "pn": 1, "ps": 20}
        headers = {"User-Agent": "Mozilla/5.0"}
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
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
                    "picUrl": song.get("cover", ""),
                })
    except Exception as e:
        logger.warning(f"B站搜索失败: {e}")
    return results


def search_jamendo(keyword):
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
                    "picUrl": song.get("image", ""),
                })
    except Exception as e:
        logger.warning(f"Jamendo搜索失败: {e}")
    return results


SEARCH_METHODS = {
    "netease": search_netease,
    "qq": search_qqmusic,
    "kugou": search_kugou,
    "kuwo": search_kuwo,
    "migu": search_migu,
    "bilibili": search_bilibili,
    "jamendo": search_jamendo,
}


@music_bp.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        data = request.json or {}
        keyword = data.get('keyword', '')
        platforms = data.get('platforms', list(PLATFORM_INFO.keys()))
    else:
        keyword = request.args.get('keyword', '')
        platforms = request.args.getlist('platforms') or list(PLATFORM_INFO.keys())
    
    if not keyword:
        return jsonify({"success": False, "error": "请输入搜索关键词"})
    
    all_results = []
    
    for platform in platforms:
        if platform in SEARCH_METHODS:
            try:
                results = SEARCH_METHODS[platform](keyword)
                all_results.extend(results)
            except Exception as e:
                logger.warning(f"{platform} 搜索失败: {e}")
    
    return jsonify({
        "success": True,
        "results": all_results,
        "count": len(all_results)
    })


@music_bp.route('/platforms', methods=['GET'])
def get_platforms():
    return jsonify({
        "success": True,
        "platforms": PLATFORM_INFO
    })


@music_bp.route('/download', methods=['POST'])
def download():
    data = request.json or {}
    song = data.get('song', {})
    platform = song.get('platform', '')
    
    save_dir = data.get('save_dir', os.path.expanduser('~/Music'))
    os.makedirs(save_dir, exist_ok=True)
    
    safe_title = re.sub(r'[<>:"/\\|?*]', '_', song.get('title', 'song'))
    safe_artist = re.sub(r'[<>:"/\\|?*]', '_', song.get('artist', 'unknown'))
    file_path = os.path.join(save_dir, f"{safe_title} - {safe_artist}.mp3")
    
    success = False
    message = ""
    
    try:
        if platform == "netease":
            song_id = song.get("id")
            url = "https://music.163.com/weapi/song/enhance/player/url/v1"
            headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://music.163.com/"}
            data = {"ids": [song_id], "level": "exhigh", "encodeType": "mp3", "csrf_token": ""}
            
            response = requests.post(url, json=data, headers=headers, timeout=10)
            resp_data = response.json()
            
            if "data" in resp_data and len(resp_data["data"]) > 0:
                download_url = resp_data["data"][0].get("url")
                if download_url:
                    audio_data = requests.get(download_url, timeout=30)
                    with open(file_path, "wb") as f:
                        f.write(audio_data.content)
                    success = True
                    message = f"下载成功: {file_path}"
        
        elif platform == "jamendo":
            song_id = song.get("id")
            url = f"https://api.jamendo.com/v3.0/tracks/file"
            params = {"client_id": "anonymous", "track_id": song_id, "format": "mp3"}
            
            response = requests.get(url, params=params, timeout=30, allow_redirects=True)
            if response.url and ".mp3" in response.url:
                audio_data = requests.get(response.url, timeout=30)
                with open(file_path, "wb") as f:
                    f.write(audio_data.content)
                success = True
                message = f"下载成功: {file_path}"
        
        else:
            message = f"平台 {platform} 暂不支持下载"
            
    except Exception as e:
        message = f"下载失败: {str(e)}"
        logger.error(f"下载出错: {e}")
    
    return jsonify({
        "success": success,
        "message": message,
        "file_path": file_path if success else None
    })
