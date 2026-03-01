"""
AI 聊天模块 API 服务
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


class AIChatService:
    """AI 聊天 API 服务"""
    
    def __init__(self):
        self.running = False
        self.port = 5003
        self.app = None
        self.chat_sessions = {}
        self.available_models = [
            {'id': 'gpt-3.5', 'name': 'GPT-3.5', 'provider': 'OpenAI'},
            {'id': 'gpt-4', 'name': 'GPT-4', 'provider': 'OpenAI'},
            {'id': 'claude', 'name': 'Claude', 'provider': 'Anthropic'},
            {'id': 'gemini', 'name': 'Gemini', 'provider': 'Google'},
            {'id': 'local', 'name': '本地模型', 'provider': '本地'}
        ]
        
    def start(self):
        """启动 AI 聊天 API 服务"""
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
        
        logger.info(f"AI 聊天 API 服务已启动，端口: {self.port}")
        
    def stop(self):
        """停止服务"""
        self.running = False
        
    def setup_routes(self):
        """设置 API 路由"""
        
        @self.app.route('/api/status', methods=['GET'])
        def get_status():
            """获取聊天服务状态"""
            return jsonify({
                'running': self.running,
                'active_sessions': len(self.chat_sessions),
                'available_models': len(self.available_models)
            })
            
        @self.app.route('/api/models', methods=['GET'])
        def get_models():
            """获取可用模型列表"""
            return jsonify({
                'models': self.available_models,
                'count': len(self.available_models)
            })
            
        @self.app.route('/api/chat/new', methods=['POST'])
        def new_chat():
            """创建新聊天会话"""
            data = request.get_json()
            model_id = data.get('model_id', 'gpt-3.5')
            session_name = data.get('session_name', '新对话')
            
            # 生成会话ID
            import uuid
            session_id = str(uuid.uuid4())
            
            # 创建新会话
            session = {
                'id': session_id,
                'name': session_name,
                'model': model_id,
                'messages': [],
                'created_at': '2025-02-27T21:10:00Z',
                'updated_at': '2025-02-27T21:10:00Z'
            }
            
            self.chat_sessions[session_id] = session
            
            return jsonify({
                'success': True,
                'session_id': session_id,
                'session': session
            })
            
        @self.app.route('/api/chat/<session_id>/send', methods=['POST'])
        def send_message(session_id):
            """发送消息"""
            if session_id not in self.chat_sessions:
                return jsonify({
                    'success': False,
                    'message': '会话不存在'
                })
                
            data = request.get_json()
            message_content = data.get('message', '')
            
            if not message_content:
                return jsonify({
                    'success': False,
                    'message': '消息内容不能为空'
                })
                
            session = self.chat_sessions[session_id]
            
            # 添加用户消息
            user_message = {
                'id': len(session['messages']) + 1,
                'role': 'user',
                'content': message_content,
                'timestamp': '2025-02-27T21:10:00Z'
            }
            session['messages'].append(user_message)
            
            # 模拟AI回复
            ai_response = self.generate_ai_response(message_content, session['model'])
            
            # 添加AI消息
            ai_message = {
                'id': len(session['messages']) + 1,
                'role': 'assistant',
                'content': ai_response,
                'timestamp': '2025-02-27T21:10:30Z'
            }
            session['messages'].append(ai_message)
            
            session['updated_at'] = '2025-02-27T21:10:30Z'
            
            return jsonify({
                'success': True,
                'user_message': user_message,
                'ai_message': ai_message,
                'session': session
            })
            
        @self.app.route('/api/chat/<session_id>/messages', methods=['GET'])
        def get_messages(session_id):
            """获取会话消息"""
            if session_id not in self.chat_sessions:
                return jsonify({
                    'success': False,
                    'message': '会话不存在'
                })
                
            session = self.chat_sessions[session_id]
            
            return jsonify({
                'success': True,
                'messages': session['messages'],
                'count': len(session['messages'])
            })
            
        @self.app.route('/api/chat/<session_id>', methods=['GET'])
        def get_session(session_id):
            """获取会话信息"""
            if session_id not in self.chat_sessions:
                return jsonify({
                    'success': False,
                    'message': '会话不存在'
                })
                
            session = self.chat_sessions[session_id]
            
            return jsonify({
                'success': True,
                'session': session
            })
            
        @self.app.route('/api/chat/sessions', methods=['GET'])
        def list_sessions():
            """列出所有会话"""
            sessions = list(self.chat_sessions.values())
            
            return jsonify({
                'success': True,
                'sessions': sessions,
                'count': len(sessions)
            })
            
        @self.app.route('/api/chat/<session_id>/rename', methods=['POST'])
        def rename_session(session_id):
            """重命名会话"""
            if session_id not in self.chat_sessions:
                return jsonify({
                    'success': False,
                    'message': '会话不存在'
                })
                
            data = request.get_json()
            new_name = data.get('new_name', '')
            
            if not new_name:
                return jsonify({
                    'success': False,
                    'message': '新名称不能为空'
                })
                
            session = self.chat_sessions[session_id]
            session['name'] = new_name
            session['updated_at'] = '2025-02-27T21:10:00Z'
            
            return jsonify({
                'success': True,
                'session': session,
                'message': '会话已重命名'
            })
            
        @self.app.route('/api/chat/<session_id>/delete', methods=['POST'])
        def delete_session(session_id):
            """删除会话"""
            if session_id not in self.chat_sessions:
                return jsonify({
                    'success': False,
                    'message': '会话不存在'
                })
                
            del self.chat_sessions[session_id]
            
            return jsonify({
                'success': True,
                'message': '会话已删除'
            })
            
        @self.app.route('/api/stream/chat', methods=['POST'])
        def stream_chat():
            """流式聊天（模拟）"""
            data = request.get_json()
            message = data.get('message', '')
            model_id = data.get('model_id', 'gpt-3.5')
            
            def generate():
                # 模拟流式响应
                response_text = self.generate_ai_response(message, model_id)
                words = response_text.split(' ')
                
                for i, word in enumerate(words):
                    chunk = {
                        'id': i + 1,
                        'content': word + ' ',
                        'finished': i == len(words) - 1
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
                    import time
                    time.sleep(0.1)
                
            return self.app.response_class(generate(), mimetype='text/plain')
    
    def generate_ai_response(self, user_message, model_id):
        """生成AI回复（模拟）"""
        responses = {
            'gpt-3.5': f"作为GPT-3.5模型，我对您的问题 '{user_message}' 的回复是：这是一个很好的问题！让我为您详细解答...",
            'gpt-4': f"作为GPT-4模型，我对您的问题 '{user_message}' 的回复是：这是一个非常有趣的问题！让我从多个角度为您分析...",
            'claude': f"作为Claude模型，我对您的问题 '{user_message}' 的回复是：让我仔细思考一下这个问题...",
            'gemini': f"作为Gemini模型，我对您的问题 '{user_message}' 的回复是：基于我的知识库，我可以为您提供以下信息...",
            'local': f"作为本地模型，我对您的问题 '{user_message}' 的回复是：让我为您提供本地化的解决方案..."
        }
        
        return responses.get(model_id, responses['gpt-3.5'])


# 注册到主API系统
from module_api import api_manager
api_manager.register_module('ai-chat', AIChatService)