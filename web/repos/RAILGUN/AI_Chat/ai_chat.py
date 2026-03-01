"""
AI聊天线程模块
处理AI对话的异步请求和流式输出
"""

import json
import sys
import os
import asyncio
import logging
from typing import List, Dict, Optional, Any
from PyQt5.QtCore import QThread, pyqtSignal, QObject

# 添加项目根目录到路径，以便导入其他模块
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from settings_manager import ConfigManager
from .ai_model import AIManager

logger = logging.getLogger(__name__)


class AIChatWorker(QObject):
    """AI聊天工作器，处理异步AI请求"""
    
    # 信号定义
    reply_chunk = pyqtSignal(str)  # 流式输出块
    reply_complete = pyqtSignal(str)  # 完整回复
    error_occurred = pyqtSignal(str)  # 错误信息
    status_update = pyqtSignal(str)  # 状态更新
    
    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config_manager = config_manager
        self.ai_manager = AIManager(config_manager)
        self.provider: Optional[Any] = None
        self.is_streaming = True  # 默认使用流式输出
        
    def set_streaming(self, enabled: bool):
        """设置是否使用流式输出"""
        self.is_streaming = enabled
        
    def set_provider(self, provider_id: str):
        """设置AI提供商"""
        self.provider = self.ai_manager.create_provider(provider_id)
        if self.provider:
            logger.info(f"已设置AI提供商: {provider_id}")
        else:
            logger.error(f"设置AI提供商失败: {provider_id}")
    
    async def _process_streaming_response(self, messages: List[Dict[str, str]]):
        """处理流式响应"""
        try:
            full_response = ""
            provider = self.provider
            if provider is None:
                raise RuntimeError("AI 提供商未初始化，无法处理流式响应")

            async for chunk in provider.chat_completion_stream(messages):
                if chunk:
                    full_response += chunk
                    self.reply_chunk.emit(chunk)
                    # 短暂暂停以避免UI阻塞
                    await asyncio.sleep(0.01)
            
            self.reply_complete.emit(full_response)
            logger.debug(f"流式响应完成，总长度: {len(full_response)}")
            
        except Exception as e:
            error_msg = f"流式请求失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
    
    async def _process_non_streaming_response(self, messages: List[Dict[str, str]]):
        """处理非流式响应"""
        try:
            provider = self.provider
            if provider is None:
                raise RuntimeError("AI 提供商未初始化，无法处理非流式响应")

            response = await provider.chat_completion(messages)
            self.reply_complete.emit(response)
            logger.debug(f"非流式响应完成，长度: {len(response)}")
            
        except Exception as e:
            error_msg = f"非流式请求失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
    
    async def process_message(self, message: str, history: Optional[List[Dict[str, str]]] = None):
        """
        处理用户消息，获取AI回复
        
        Args:
            message (str): 用户消息
            history (List[Dict[str, str]]): 对话历史
        """
        try:
            # 确保有可用的提供商
            if not self.provider:
                default_provider = self.config_manager.get_config("ai.default_provider")
                self.provider = self.ai_manager.create_provider(default_provider)
                
                if not self.provider:
                    self.error_occurred.emit("无法创建AI提供商，请检查配置")
                    return
            
            # 准备消息历史
            if history is None:
                history = []
            
            messages = history.copy()
            messages.append({"role": "user", "content": message})
            
            # 检查是否启用流式输出
            provider_id = self.config_manager.get_config("ai.default_provider")
            provider_config = self.config_manager.get_config(f"ai.providers.{provider_id}")
            stream_enabled = provider_config.get("stream", True) if provider_config else True
            
            self.status_update.emit("正在生成回复...")
            
            if stream_enabled and self.is_streaming:
                await self._process_streaming_response(messages)
            else:
                await self._process_non_streaming_response(messages)
                
            self.status_update.emit("就绪")
            
        except Exception as e:
            error_msg = f"处理消息失败: {str(e)}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)


class AIChatThread(QThread):
    """AI聊天线程，包装工作器以在QThread中运行"""
    
    # 信号定义（与工作器相同，用于与UI通信）
    reply_chunk = pyqtSignal(str)
    reply_complete = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    status_update = pyqtSignal(str)
    
    def __init__(self, message: str, config_manager: ConfigManager, 
                 history: Optional[List[Dict[str, str]]] = None, 
                 provider_id: str = None, 
                 streaming: bool = True):
        super().__init__()
        self.message = message
        self.history = history or []
        self.provider_id = provider_id
        self.streaming = streaming
        self.config_manager = config_manager
        self.worker = None
        
    def run(self):
        """线程主函数"""
        try:
            # 创建事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 创建工作器
            self.worker = AIChatWorker(self.config_manager)
            
            # 连接工作器信号到线程信号
            self.worker.reply_chunk.connect(self.reply_chunk.emit)
            self.worker.reply_complete.connect(self.reply_complete.emit)
            self.worker.error_occurred.connect(self.error_occurred.emit)
            self.worker.status_update.connect(self.status_update.emit)
            
            # 设置工作器参数
            self.worker.set_streaming(self.streaming)
            if self.provider_id:
                self.worker.set_provider(self.provider_id)
            
            # 运行异步任务
            loop.run_until_complete(
                self.worker.process_message(self.message, self.history)
            )

            # 尝试关闭提供商相关的异步客户端，避免未关闭的 async generator
            try:
                loop.run_until_complete(self.worker.ai_manager.close_provider())
            except Exception:
                # 忽略关闭时的错误，但记录日志
                logger.debug("关闭AI提供商时发生错误", exc_info=True)

            loop.close()
            
        except Exception as e:
            error_msg = f"线程运行失败: {str(e)}"
            logger.error(error_msg)
            try:
                # 尝试在异常路径也关闭底层提供商资源
                loop.run_until_complete(self.worker.ai_manager.close_provider())
            except Exception:
                logger.debug("异常时关闭提供商失败", exc_info=True)
            self.error_occurred.emit(error_msg)


class ChatHistoryManager:
    """聊天历史管理器（支持持久化到 Data 目录）

    默认会在 `paths.data` 下创建 `AIChat` 子目录，并保存两个文件：
    - `AIChat_history_latest.json`（保存最新会话）
    - `AIChat_history_<timestamp>.json`（按需归档）
    """

    def __init__(self, config_manager: Optional[ConfigManager] = None, max_history: int = 20):
        self.max_history = max_history
        self.history: List[Dict[str, str]] = []
        self.config_manager = config_manager

        # 计算存储目录
        base_data = None
        try:
            if config_manager:
                base_data = config_manager.get_config("paths.data")
        except Exception:
            base_data = None

        if not base_data:
            base_data = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "Data")
        # 归一化并创建子目录
        base_data = os.path.abspath(base_data)
        self.storage_dir = os.path.join(base_data, "AIChat")
        os.makedirs(self.storage_dir, exist_ok=True)

    def add_message(self, role: str, content: str):
        """添加消息到历史并裁剪长度"""
        self.history.append({"role": role, "content": content})
        # 限制历史长度（每轮包含 user+assistant）
        if len(self.history) > self.max_history * 2:
            self.history = self.history[-(self.max_history * 2):]

    def get_history(self) -> List[Dict[str, str]]:
        """返回历史的副本"""
        return self.history.copy()

    def clear_history(self):
        """清空历史（不会删除磁盘文件）"""
        self.history = []

    def get_conversation_count(self) -> int:
        return len(self.history) // 2

    # --- 持久化接口 ---
    def _latest_path(self) -> str:
        return os.path.join(self.storage_dir, "AIChat_history_latest.json")

    def save_to_file(self, filename: Optional[str] = None, archive: bool = False) -> str:
        """保存当前历史到指定文件；返回写入的路径

        如果不传 `filename`，默认写入 latest 文件；当 `archive=True` 时也写入带时间戳的归档文件。
        """
        data = {
            "meta": {
                "count": len(self.history),
            },
            "history": self.history
        }

        if not filename:
            filename = self._latest_path()

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        if archive:
            import datetime
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_name = os.path.join(self.storage_dir, f"AIChat_history_{ts}.json")
            with open(archive_name, "w", encoding="utf-8") as af:
                json.dump(data, af, ensure_ascii=False, indent=2)
            return archive_name

        return filename

    def load_from_file(self, filename: Optional[str] = None) -> bool:
        """从文件加载历史到内存，返回是否成功"""
        if not filename:
            filename = self._latest_path()
        if not os.path.exists(filename):
            return False
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
            hist = data.get("history", [])
            if isinstance(hist, list):
                self.history = hist[-(self.max_history * 2):]
                return True
        except Exception:
            return False
        return False

    def list_history_files(self) -> List[str]:
        """列出存储目录下的历史文件（不含路径）"""
        files = []
        try:
            for name in os.listdir(self.storage_dir):
                if name.endswith('.json'):
                    files.append(os.path.join(self.storage_dir, name))
        except Exception:
            pass
        return sorted(files)
