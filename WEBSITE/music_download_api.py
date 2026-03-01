"""
音乐下载模块 API 服务
"""

import os
import sys
import json
import threading
import logging
from flask import Flask, jsonify, request
from flask_cors import CORS

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)


class MusicDownloadService:
    """音乐下载 API 服务"""
    
    def __init__(self):
        self.running = False
        self.port = 5002
        self.app = None
        self.download_queue = []
        self.downloading = False
        self.current_download = None
        
    def start(self):
        """启动音乐下载 API 服务"""
        self.running = True
        
        # 创建 Flask 应用
        self.app = Flask(__name__)
        CORS(self.app)
        
        # 设置路由
        self.setup_routes()
        
        # 在新线程中运行 Flask 应用
        def run_app():
            self.app.run(host='127.0.0.1', port=self.port, debug=False, threaded=True)
            
        thread = threading.Thread(target=run_app, daemon=True)
        thread.start()
        
        logger.info(f"音乐下载 API 服务已启动，端口: {self.port}")
        
    def stop(self):
        """停止服务"""
        self.running = False
        
    def setup_routes(self):
        """设置 API 路由"""
        
        @self.app.route('/api/status', methods=['GET'])
        def get_status():
            """获取下载器状态"""
            return jsonify({
                'running': self.running,
                'downloading': self.downloading,
                'queue_count': len(self.download_queue),
                'current_download': self.current_download
            })
            
        @self.app.route('/api/search', methods=['POST'])
        def search_music():
            """搜索音乐"""
            data = request.get_json()
            keyword = data.get('keyword', '')
            platform = data.get('platform', 'all')
            
            if not keyword:
                return jsonify({
                    'success': False,
                    'message': '请输入搜索关键词'
                })
                
            # 模拟搜索结果
            results = [
                {
                    'id': 1,
                    'title': f'{keyword} - 歌曲1',
                    'artist': '未知艺术家',
                    'album': '未知专辑',
                    'duration': '03:45',
                    'platform': platform,
                    'download_url': f'http://example.com/{keyword}_1.mp3'
                },
                {
                    'id': 2,
                    'title': f'{keyword} - 歌曲2',
                    'artist': '未知艺术家',
                    'album': '未知专辑',
                    'duration': '04:20',
                    'platform': platform,
                    'download_url': f'http://example.com/{keyword}_2.mp3'
                }
            ]
            
            return jsonify({
                'success': True,
                'keyword': keyword,
                'platform': platform,
                'results': results,
                'count': len(results)
            })
            
        @self.app.route('/api/download', methods=['POST'])
        def download_music():
            """下载音乐"""
            data = request.get_json()
            download_url = data.get('download_url')
            title = data.get('title', '未知歌曲')
            
            if not download_url:
                return jsonify({
                    'success': False,
                    'message': '未提供下载链接'
                })
                
            # 添加到下载队列
            download_item = {
                'url': download_url,
                'title': title,
                'status': 'queued',
                'progress': 0
            }
            
            self.download_queue.append(download_item)
            
            # 如果没有正在下载的项目，开始下载
            if not self.downloading:
                self.start_download()
            
            return jsonify({
                'success': True,
                'message': f'已添加到下载队列: {title}',
                'queue_position': len(self.download_queue),
                'download_item': download_item
            })
            
        @self.app.route('/api/queue', methods=['GET'])
        def get_queue():
            """获取下载队列"""
            return jsonify({
                'queue': self.download_queue,
                'downloading': self.downloading,
                'current_download': self.current_download
            })
            
        @self.app.route('/api/queue/clear', methods=['POST'])
        def clear_queue():
            """清空下载队列"""
            self.download_queue.clear()
            self.downloading = False
            self.current_download = None
            
            return jsonify({
                'success': True,
                'message': '下载队列已清空'
            })
            
        @self.app.route('/api/bilibili/search', methods=['POST'])
        def search_bilibili():
            """搜索B站音乐"""
            data = request.get_json()
            keyword = data.get('keyword', '')
            
            if not keyword:
                return jsonify({
                    'success': False,
                    'message': '请输入搜索关键词'
                })
                
            # 模拟B站搜索结果
            results = [
                {
                    'id': 'BV1xxx',
                    'title': f'【B站音乐】{keyword} - 完整版',
                    'author': 'UP主1',
                    'duration': '03:30',
                    'view_count': 10000,
                    'cover_url': 'https://example.com/cover1.jpg',
                    'audio_url': f'https://example.com/{keyword}_bilibili.mp3'
                },
                {
                    'id': 'BV2xxx',
                    'title': f'【B站音乐】{keyword} - 纯音乐版',
                    'author': 'UP主2',
                    'duration': '04:15',
                    'view_count': 5000,
                    'cover_url': 'https://example.com/cover2.jpg',
                    'audio_url': f'https://example.com/{keyword}_bilibili2.mp3'
                }
            ]
            
            return jsonify({
                'success': True,
                'keyword': keyword,
                'platform': 'bilibili',
                'results': results,
                'count': len(results)
            })
            
        @self.app.route('/api/batch/download', methods=['POST'])
        def batch_download():
            """批量下载"""
            data = request.get_json()
            items = data.get('items', [])
            
            if not items:
                return jsonify({
                    'success': False,
                    'message': '未提供下载项'
                })
                
            # 添加到下载队列
            for item in items:
                download_item = {
                    'url': item.get('url'),
                    'title': item.get('title', '未知歌曲'),
                    'status': 'queued',
                    'progress': 0
                }
                self.download_queue.append(download_item)
            
            # 如果没有正在下载的项目，开始下载
            if not self.downloading:
                self.start_download()
            
            return jsonify({
                'success': True,
                'message': f'已添加 {len(items)} 个项目到下载队列',
                'queue_count': len(self.download_queue)
            })
    
    def start_download(self):
        """开始下载（模拟）"""
        if not self.download_queue:
            self.downloading = False
            self.current_download = None
            return
            
        self.downloading = True
        
        def download_worker():
            while self.download_queue and self.downloading:
                self.current_download = self.download_queue.pop(0)
                self.current_download['status'] = 'downloading'
                
                # 模拟下载过程
                for progress in range(0, 101, 10):
                    if not self.downloading:
                        break
                    self.current_download['progress'] = progress
                    # 模拟下载延迟
                    import time
                    time.sleep(0.5)
                
                if self.downloading:
                    self.current_download['status'] = 'completed'
                    self.current_download['progress'] = 100
                else:
                    self.current_download['status'] = 'cancelled'
                
                self.current_download = None
            
            self.downloading = False
        
        # 在新线程中运行下载器
        thread = threading.Thread(target=download_worker, daemon=True)
        thread.start()


# 注册到主API系统
from module_api import api_manager
api_manager.register_module('music-download', MusicDownloadService)