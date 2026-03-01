"""
工具集合模块 API 服务
"""

import os
import sys
import json
import threading
import logging
import base64
from flask import Flask, jsonify, request
from flask_cors import CORS

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)


class ToolsService:
    """工具集合 API 服务"""
    
    def __init__(self):
        self.running = False
        self.port = 5004
        self.app = None
        self.screenshots = []
        self.color_history = []
        
    def start(self):
        """启动工具集合 API 服务"""
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
        
        logger.info(f"工具集合 API 服务已启动，端口: {self.port}")
        
    def stop(self):
        """停止服务"""
        self.running = False
        
    def setup_routes(self):
        """设置 API 路由"""
        
        @self.app.route('/api/status', methods=['GET'])
        def get_status():
            """获取工具服务状态"""
            return jsonify({
                'running': self.running,
                'screenshots_count': len(self.screenshots),
                'color_history_count': len(self.color_history)
            })
            
        @self.app.route('/api/tools/screenshot/capture', methods=['POST'])
        def capture_screenshot():
            """捕获截图"""
            # 模拟截图功能
            # 在实际应用中，这里应该调用截图工具
            
            screenshot_data = {
                'id': len(self.screenshots) + 1,
                'timestamp': '2025-02-27T21:10:00Z',
                'size': '1920x1080',
                'format': 'PNG',
                'preview_url': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=='
            }
            
            self.screenshots.append(screenshot_data)
            
            return jsonify({
                'success': True,
                'message': '截图已捕获',
                'screenshot': screenshot_data
            })
            
        @self.app.route('/api/tools/screenshot/list', methods=['GET'])
        def list_screenshots():
            """列出所有截图"""
            return jsonify({
                'success': True,
                'screenshots': self.screenshots,
                'count': len(self.screenshots)
            })
            
        @self.app.route('/api/tools/screenshot/<int:screenshot_id>', methods=['GET'])
        def get_screenshot(screenshot_id):
            """获取特定截图"""
            screenshot = next((s for s in self.screenshots if s['id'] == screenshot_id), None)
            
            if not screenshot:
                return jsonify({
                    'success': False,
                    'message': '截图不存在'
                })
                
            return jsonify({
                'success': True,
                'screenshot': screenshot
            })
            
        @self.app.route('/api/tools/color/pick', methods=['POST'])
        def pick_color():
            """取色器功能"""
            data = request.get_json()
            x = data.get('x', 0)
            y = data.get('y', 0)
            
            # 模拟取色功能
            # 在实际应用中，这里应该调用取色器工具
            
            color_data = {
                'id': len(self.color_history) + 1,
                'timestamp': '2025-02-27T21:10:00Z',
                'position': {'x': x, 'y': y},
                'hex': '#3b82f6',
                'rgb': {'r': 59, 'g': 130, 'b': 246},
                'hsl': {'h': 217, 's': 91, 'l': 60}
            }
            
            self.color_history.append(color_data)
            
            return jsonify({
                'success': True,
                'message': '颜色已获取',
                'color': color_data
            })
            
        @self.app.route('/api/tools/color/history', methods=['GET'])
        def color_history():
            """获取颜色历史"""
            return jsonify({
                'success': True,
                'colors': self.color_history,
                'count': len(self.color_history)
            })
            
        @self.app.route('/api/tools/convert/image', methods=['POST'])
        def convert_image():
            """图片格式转换"""
            data = request.get_json()
            image_data = data.get('image_data', '')
            target_format = data.get('format', 'PNG')
            
            if not image_data:
                return jsonify({
                    'success': False,
                    'message': '未提供图片数据'
                })
                
            # 模拟格式转换
            # 在实际应用中，这里应该调用图片转换工具
            
            converted_data = {
                'original_format': '未知',
                'target_format': target_format,
                'converted_data': image_data,  # 模拟转换后的数据
                'size': len(image_data),
                'timestamp': '2025-02-27T21:10:00Z'
            }
            
            return jsonify({
                'success': True,
                'message': f'图片已转换为 {target_format} 格式',
                'converted': converted_data
            })
            
        @self.app.route('/api/tools/random/name', methods=['POST'])
        def generate_random_name():
            """生成随机名称"""
            data = request.get_json()
            gender = data.get('gender', 'random')
            count = data.get('count', 1)
            
            # 随机名称生成器
            first_names = ['张', '王', '李', '赵', '刘', '陈', '杨', '黄', '周', '吴']
            last_names = ['伟', '芳', '娜', '秀英', '敏', '静', '丽', '强', '磊', '军']
            
            import random
            names = []
            
            for _ in range(min(count, 10)):  # 限制最多生成10个
                first_name = random.choice(first_names)
                last_name = random.choice(last_names)
                name = f"{first_name}{last_name}"
                names.append(name)
            
            return jsonify({
                'success': True,
                'names': names,
                'count': len(names),
                'gender': gender
            })
            
        @self.app.route('/api/tools/hash/generate', methods=['POST'])
        def generate_hash():
            """生成哈希值"""
            data = request.get_json()
            text = data.get('text', '')
            algorithm = data.get('algorithm', 'md5')
            
            if not text:
                return jsonify({
                    'success': False,
                    'message': '未提供文本内容'
                })
                
            # 模拟哈希生成
            import hashlib
            
            if algorithm == 'md5':
                hash_obj = hashlib.md5(text.encode())
            elif algorithm == 'sha1':
                hash_obj = hashlib.sha1(text.encode())
            elif algorithm == 'sha256':
                hash_obj = hashlib.sha256(text.encode())
            else:
                hash_obj = hashlib.md5(text.encode())
                algorithm = 'md5'
            
            hash_value = hash_obj.hexdigest()
            
            return jsonify({
                'success': True,
                'algorithm': algorithm,
                'hash': hash_value,
                'text': text
            })
            
        @self.app.route('/api/tools/qrcode/generate', methods=['POST'])
        def generate_qrcode():
            """生成二维码"""
            data = request.get_json()
            content = data.get('content', '')
            size = data.get('size', 200)
            
            if not content:
                return jsonify({
                    'success': False,
                    'message': '未提供二维码内容'
                })
                
            # 模拟二维码生成
            # 在实际应用中，这里应该调用二维码生成库
            
            qrcode_data = {
                'content': content,
                'size': size,
                'format': 'PNG',
                'image_data': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==',
                'timestamp': '2025-02-27T21:10:00Z'
            }
            
            return jsonify({
                'success': True,
                'message': '二维码已生成',
                'qrcode': qrcode_data
            })
            
        @self.app.route('/api/tools/calculator/evaluate', methods=['POST'])
        def evaluate_expression():
            """计算器功能"""
            data = request.get_json()
            expression = data.get('expression', '')
            
            if not expression:
                return jsonify({
                    'success': False,
                    'message': '未提供表达式'
                })
                
            try:
                # 安全地计算表达式
                # 在实际应用中，应该使用更安全的计算方式
                result = eval(expression)
                
                return jsonify({
                    'success': True,
                    'expression': expression,
                    'result': result
                })
                
            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'计算错误: {str(e)}',
                    'expression': expression
                })


# 注册到主API系统
from module_api import api_manager
api_manager.register_module('tools', ToolsService)