"""
模块化 API 系统
为每个功能模块提供独立的 API 服务
支持按需启动和停止模块服务
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


class ModuleAPIManager:
    """模块 API 管理器"""
    
    def __init__(self):
        self.modules = {}
        self.active_services = {}
        
    def register_module(self, module_name, module_class):
        """注册模块"""
        self.modules[module_name] = module_class
        logger.info(f"模块已注册: {module_name}")
        
    def start_module_service(self, module_name):
        """启动模块服务"""
        if module_name not in self.modules:
            return False, f"模块未注册: {module_name}"
            
        if module_name in self.active_services:
            return True, f"模块服务已在运行: {module_name}"
            
        try:
            module_class = self.modules[module_name]
            service = module_class()
            
            # 在新线程中启动服务
            thread = threading.Thread(target=service.start, daemon=True)
            thread.start()
            
            self.active_services[module_name] = {
                'service': service,
                'thread': thread
            }
            
            logger.info(f"模块服务已启动: {module_name}")
            return True, f"模块服务启动成功: {module_name}"
            
        except Exception as e:
            logger.error(f"启动模块服务失败: {module_name}, 错误: {str(e)}")
            return False, f"启动失败: {str(e)}"
            
    def stop_module_service(self, module_name):
        """停止模块服务"""
        if module_name not in self.active_services:
            return False, f"模块服务未运行: {module_name}"
            
        try:
            service_info = self.active_services[module_name]
            service_info['service'].stop()
            del self.active_services[module_name]
            
            logger.info(f"模块服务已停止: {module_name}")
            return True, f"模块服务停止成功: {module_name}"
            
        except Exception as e:
            logger.error(f"停止模块服务失败: {module_name}, 错误: {str(e)}")
            return False, f"停止失败: {str(e)}"
            
    def get_module_status(self, module_name):
        """获取模块状态"""
        is_registered = module_name in self.modules
        is_running = module_name in self.active_services
        
        return {
            'module': module_name,
            'registered': is_registered,
            'running': is_running,
            'status': 'running' if is_running else 'stopped'
        }


# 创建全局管理器实例
api_manager = ModuleAPIManager()


class BaseModuleService:
    """基础模块服务类"""
    
    def __init__(self):
        self.running = False
        self.port = None
        self.app = None
        
    def start(self):
        """启动服务"""
        self.running = True
        
    def stop(self):
        """停止服务"""
        self.running = False
        
    def get_status(self):
        """获取服务状态"""
        return {
            'running': self.running,
            'port': self.port
        }


class MusicPlayerService(BaseModuleService):
    """音乐播放器 API 服务"""
    
    def __init__(self):
        super().__init__()
        self.port = 5001
        self.current_song = None
        self.playlist = []
        self.is_playing = False
        
    def start(self):
        """启动音乐播放器 API 服务"""
        super().start()
        
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
        
        logger.info(f"音乐播放器 API 服务已启动，端口: {self.port}")
        
    def setup_routes(self):
        """设置 API 路由"""
        
        @self.app.route('/api/status', methods=['GET'])
        def get_status():
            """获取播放器状态"""
            return jsonify({
                'running': self.running,
                'playing': self.is_playing,
                'current_song': self.current_song,
                'playlist_count': len(self.playlist)
            })
            
        @self.app.route('/api/play', methods=['POST'])
        def play_song():
            """播放歌曲"""
            data = request.get_json()
            song_path = data.get('song_path')
            
            if song_path:
                self.current_song = song_path
                self.is_playing = True
                
                # 这里应该调用实际的音乐播放器功能
                # 暂时模拟播放
                
                return jsonify({
                    'success': True,
                    'message': f'开始播放: {song_path}',
                    'current_song': self.current_song
                })
            else:
                return jsonify({
                    'success': False,
                    'message': '未提供歌曲路径'
                })
                
        @self.app.route('/api/pause', methods=['POST'])
        def pause_song():
            """暂停播放"""
            self.is_playing = False
            
            return jsonify({
                'success': True,
                'message': '播放已暂停',
                'playing': self.is_playing
            })
            
        @self.app.route('/api/resume', methods=['POST'])
        def resume_song():
            """恢复播放"""
            if self.current_song:
                self.is_playing = True
                
                return jsonify({
                    'success': True,
                    'message': '播放已恢复',
                    'playing': self.is_playing
                })
            else:
                return jsonify({
                    'success': False,
                    'message': '没有正在播放的歌曲'
                })
                
        @self.app.route('/api/stop', methods=['POST'])
        def stop_song():
            """停止播放"""
            self.is_playing = False
            self.current_song = None
            
            return jsonify({
                'success': True,
                'message': '播放已停止'
            })
            
        @self.app.route('/api/playlist', methods=['GET'])
        def get_playlist():
            """获取播放列表"""
            return jsonify({
                'playlist': self.playlist,
                'count': len(self.playlist)
            })
            
        @self.app.route('/api/playlist/add', methods=['POST'])
        def add_to_playlist():
            """添加到播放列表"""
            data = request.get_json()
            song_path = data.get('song_path')
            
            if song_path and song_path not in self.playlist:
                self.playlist.append(song_path)
                
                return jsonify({
                    'success': True,
                    'message': '歌曲已添加到播放列表',
                    'playlist_count': len(self.playlist)
                })
            else:
                return jsonify({
                    'success': False,
                    'message': '添加失败，歌曲已存在或路径无效'
                })
                
        @self.app.route('/api/lyrics', methods=['GET'])
        def get_lyrics():
            """获取歌词"""
            song_title = request.args.get('song_title', '')
            artist = request.args.get('artist', '')
            
            # 这里应该调用歌词搜索功能
            # 暂时返回模拟数据
            
            lyrics = f"正在搜索 {artist} - {song_title} 的歌词..."
            
            return jsonify({
                'success': True,
                'song_title': song_title,
                'artist': artist,
                'lyrics': lyrics
            })


# 注册音乐播放器模块
api_manager.register_module('music-player', MusicPlayerService)


# 创建主 API 应用
app = Flask(__name__)
CORS(app)


@app.route('/api/<module_name>/start', methods=['POST'])
def start_module(module_name):
    """启动模块服务"""
    success, message = api_manager.start_module_service(module_name)
    
    return jsonify({
        'success': success,
        'message': message,
        'module': module_name
    })


@app.route('/api/<module_name>/stop', methods=['POST'])
def stop_module(module_name):
    """停止模块服务"""
    success, message = api_manager.stop_module_service(module_name)
    
    return jsonify({
        'success': success,
        'message': message,
        'module': module_name
    })


@app.route('/api/<module_name>/status', methods=['GET'])
def get_module_status(module_name):
    """获取模块状态"""
    status = api_manager.get_module_status(module_name)
    
    return jsonify(status)


@app.route('/api/modules', methods=['GET'])
def list_modules():
    """列出所有可用模块"""
    modules = list(api_manager.modules.keys())
    active_modules = list(api_manager.active_services.keys())
    
    return jsonify({
        'available_modules': modules,
        'active_modules': active_modules,
        'total_modules': len(modules)
    })


@app.route('/api/status', methods=['GET'])
def overall_status():
    """获取整体状态"""
    return jsonify({
        'online': True,
        'message': 'RAILGUN API 服务运行正常',
        'timestamp': '2025-02-27T21:10:00Z'
    })


if __name__ == '__main__':
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("RAILGUN 模块化 API 服务启动中...")
    print("可用模块:", list(api_manager.modules.keys()))
    
    # 启动主 API 服务
    app.run(host='127.0.0.1', port=5000, debug=True)