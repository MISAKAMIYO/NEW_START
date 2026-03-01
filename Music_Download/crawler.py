"""
音乐爬虫模块
提供音乐搜索和下载功能，支持可配置的API
"""

import requests
import json
import os
import re
import urllib.parse
from typing import Dict, List, Optional
import logging
import logging.handlers
import traceback

def setup_logging():
    """设置日志记录，同时输出到控制台和文件"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_dir = os.path.join(base_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, "crawler.log")
    
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    
    if logger.handlers:
        logger.handlers.clear()
    
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_file, when='midnight', interval=1, backupCount=7, encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

logger = setup_logging()

def log_exception(func):
    """异常处理装饰器"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_msg = f"函数 {func.__name__} 执行出错: {str(e)}"
            logger.error(error_msg)
            logger.error(f"异常详情:\n{traceback.format_exc()}")
            raise
    return wrapper


def get_settings_path():
    """获取设置文件路径"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "settings.json")


def load_settings():
    """加载设置"""
    settings_path = get_settings_path()
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    default_settings = {
        "save_paths": {
            "music": os.path.join(base_dir, "Songs"),
            "cache": os.path.join(base_dir, "cache")
        },
        "sources": {
            "active_source": "QQ音乐",
            "sources_list": [
                {
                    "name": "QQ音乐",
                    "url": "https://music.txqq.pro/",
                    "params": {"input": "{query}", "filter": "name", "type": "qq", "page": 1},
                    "method": "POST",
                    "api_key": "",
                    "headers": {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "X-Requested-With": "XMLHttpRequest"
                    }
                },
                {
                    "name": "网易云音乐",
                    "url": "https://api.itxq.top/",
                    "params": {"input": "{query}", "filter": "name", "type": "netease", "page": 1},
                    "method": "POST",
                    "api_key": "",
                    "headers": {}
                }
            ]
        },
        "other": {
            "max_results": 20,
            "auto_play": False
        }
    }
    
    if not os.path.exists(settings_path):
        return default_settings
    
    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)
            
            if "sources" not in settings:
                settings["sources"] = default_settings["sources"]
            if "save_paths" not in settings:
                settings["save_paths"] = default_settings["save_paths"]
            if "other" not in settings:
                settings["other"] = default_settings["other"]
                
            logger.info(f"设置加载成功，激活音源: {settings['sources']['active_source']}")
            return settings
    except Exception as e:
        error_msg = f"加载设置失败: {str(e)}"
        logger.error(error_msg)
        logger.error(f"异常详情:\n{traceback.format_exc()}")
        return default_settings


def get_active_source_config():
    """获取当前激活的音源配置"""
    try:
        settings = load_settings()
        active_source = settings["sources"]["active_source"]
        for source in settings["sources"]["sources_list"]:
            if source["name"] == active_source:
                logger.info(f"获取激活音源配置: {active_source}")
                return source
        logger.warning(f"未找到激活音源 '{active_source}'，使用默认音源")
        return settings["sources"]["sources_list"][0]
    except Exception as e:
        error_msg = f"获取激活音源配置失败: {str(e)}"
        logger.error(error_msg)
        logger.error(f"异常详情:\n{traceback.format_exc()}")
        raise


def get_source_names():
    """获取所有音源名称"""
    try:
        settings = load_settings()
        names = [source["name"] for source in settings["sources"]["sources_list"]]
        logger.info(f"获取音源名称列表: {names}")
        return names
    except Exception as e:
        error_msg = f"获取音源名称列表失败: {str(e)}"
        logger.error(error_msg)
        logger.error(f"异常详情:\n{traceback.format_exc()}")
        raise


def save_settings(settings):
    """保存设置"""
    try:
        settings_path = get_settings_path()
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
        logger.info(f"设置保存成功: {settings_path}")
        logger.debug(f"保存的设置内容: {json.dumps(settings, ensure_ascii=False, indent=2)}")
        return True
    except Exception as e:
        error_msg = f"保存设置失败: {str(e)}"
        logger.error(error_msg)
        logger.error(f"异常详情:\n{traceback.format_exc()}")
        logger.error(f"尝试保存的设置: {json.dumps(settings, ensure_ascii=False, indent=2)}")
        return False


class MusicCrawler:
    """音乐爬虫类"""
    
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "X-Requested-With": "XMLHttpRequest"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def search(self, keyword: str, source_name: Optional[str] = None, max_results: int = 20) -> Dict:
        """
        搜索音乐
        
        Args:
            keyword: 搜索关键词
            source_name: 数据源名称（默认使用配置中的激活音源）
            max_results: 最大返回结果数
        
        Returns:
            搜索结果字典
        """
        try:
            if source_name is None:
                config = get_active_source_config()
            else:
                settings = load_settings()
                config = None
                for source in settings["sources"]["sources_list"]:
                    if source["name"] == source_name:
                        config = source
                        break
                if config is None:
                    config = get_active_source_config()
            
            logger.info(f"使用音源: {config.get('name', '未知音源')}")
            
            url = config.get("url", "")
            method = config.get("method", "POST").upper()
            params = config.get("params", {}).copy()
            headers = config.get("headers", {}).copy()
            api_key = config.get("api_key", "")
            
            for key, value in params.items():
                if isinstance(value, str) and "{query}" in value:
                    params[key] = value.replace("{query}", keyword)
            
            if api_key and "Authorization" not in headers:
                params["api_key"] = api_key
            
            logger.info(f"请求URL: {url}")
            logger.info(f"请求参数: {params}")
            
            if method == "GET":
                url_with_params = url + "?" + urllib.parse.urlencode(params)
                response = self.session.get(url_with_params, headers=headers, timeout=30)
            else:
                response = self.session.post(url, data=params, headers=headers, timeout=30)
            
            response.raise_for_status()
            
            if response.status_code == 200:
                json_data = response.json()
                
                if not isinstance(json_data, dict):
                    if isinstance(json_data, list):
                        json_data = {"data": json_data}
                    else:
                        json_data = {"data": []}
                
                if "data" not in json_data:
                    json_data["data"] = []
                
                if not isinstance(json_data["data"], list):
                    json_data["data"] = []
                
                if len(json_data["data"]) > max_results:
                    json_data["data"] = json_data["data"][:max_results]
                
                return json_data
            else:
                logger.error(f"请求失败，状态码: {response.status_code}")
                return {"data": []}
                
        except requests.exceptions.RequestException as e:
            error_msg = f"网络请求失败: {str(e)}"
            logger.error(error_msg)
            logger.error(f"异常详情:\n{traceback.format_exc()}")
            return {"data": []}
        except Exception as e:
            error_msg = f"搜索失败: {str(e)}"
            logger.error(error_msg)
            logger.error(f"异常详情:\n{traceback.format_exc()}")
            return {"data": []}
    
    def download(self, url: str, file_path: str, progress_callback=None) -> bool:
        """
        下载音乐文件
        
        Args:
            url: 音乐文件URL
            file_path: 保存路径
            progress_callback: 进度回调函数
        
        Returns:
            是否下载成功
        """
        try:
            download_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://music.163.com/"
            }
            
            response = self.session.get(url, headers=download_headers, stream=True, timeout=30)
            
            if response.status_code != 200:
                return False
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if progress_callback and total_size > 0:
                            progress = int(100 * downloaded / total_size)
                            progress_callback(progress)
            
            logger.info(f"文件下载成功: {file_path}")
            return True
        except Exception as e:
            error_msg = f"下载失败: {str(e)}"
            logger.error(error_msg)
            logger.error(f"异常详情:\n{traceback.format_exc()}")
            logger.error(f"下载URL: {url}, 保存路径: {file_path}")
            return False
    
    def download_cover(self, pic_url: str, save_path: str) -> bool:
        """
        下载专辑封面
        
        Args:
            pic_url: 封面图片URL
            save_path: 保存路径
        
        Returns:
            是否下载成功
        """
        try:
            if not pic_url:
                return False
            
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            response = self.session.get(pic_url, timeout=10)
            if response.status_code == 200:
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"封面下载成功: {save_path}")
                return True
            logger.warning(f"封面下载失败，状态码: {response.status_code}")
            return False
        except Exception as e:
            error_msg = f"封面下载失败: {str(e)}"
            logger.error(error_msg)
            logger.error(f"异常详情:\n{traceback.format_exc()}")
            logger.error(f"封面URL: {pic_url}, 保存路径: {save_path}")
            return False


def search_song(keyword: str, max_results: int = 20) -> Dict:
    """
    搜索歌曲（便捷函数）
    
    Args:
        keyword: 搜索关键词
        max_results: 最大结果数
    
    Returns:
        搜索结果字典
    """
    try:
        logger.info(f"搜索歌曲: {keyword}, 最大结果: {max_results}")
        crawler = MusicCrawler()
        result = crawler.search(keyword, max_results=max_results)
        logger.info(f"搜索完成，找到 {len(result.get('data', []))} 个结果")
        return result
    except Exception as e:
        error_msg = f"搜索歌曲失败: {str(e)}"
        logger.error(error_msg)
        logger.error(f"异常详情:\n{traceback.format_exc()}")
        return {"data": []}


def download_song(audio_url: str, file_path: str, progress_callback=None) -> bool:
    """
    下载歌曲（便捷函数）
    
    Args:
        audio_url: 音频URL
        file_path: 保存路径
        progress_callback: 进度回调
    
    Returns:
        是否成功
    """
    try:
        logger.info(f"开始下载歌曲: {audio_url}")
        crawler = MusicCrawler()
        success = crawler.download(audio_url, file_path, progress_callback)
        if success:
            logger.info(f"歌曲下载成功: {file_path}")
        else:
            logger.error(f"歌曲下载失败: {file_path}")
        return success
    except Exception as e:
        error_msg = f"歌曲下载失败: {str(e)}"
        logger.error(error_msg)
        logger.error(f"异常详情:\n{traceback.format_exc()}")
        return False


if __name__ == "__main__":
    crawler = MusicCrawler()
    
    print("测试搜索功能...")
    results = crawler.search("周杰伦", max_results=5)
    
    songs = results.get("data", [])
    if songs:
        print(f"找到 {len(songs)} 首歌曲:")
        for i, song in enumerate(songs):
            print(f"{i+1}. {song.get('title', '未知')} - {song.get('author', '未知')}")
    else:
        print("未找到歌曲")
