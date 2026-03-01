"""
AI模型管理模块
支持多提供商AI对话，包括自定义API、DeepSeek和智谱AI等
"""

import json
import logging
import asyncio
import httpx
from typing import Dict, List, Optional, AsyncGenerator, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AIProviderConfig:
    """AI提供商配置"""
    name: str
    api_key: str
    base_url: str
    model: str
    temperature: float
    max_tokens: int
    stream: bool = True


class AIProvider:
    """AI提供商基类"""

    def __init__(self, config: AIProviderConfig):
        self.config = config
        self._client: Optional[httpx.AsyncClient] = httpx.AsyncClient(
            timeout=30.0,
            headers=self._get_headers(),
            follow_redirects=True
        )

    def _get_headers(self) -> Dict[str, str]:
        """获取API请求头"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "RAILGUN-AI-Chat/1.0"
        }

        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        return headers

    def _get_api_endpoint(self) -> str:
        """获取API端点"""
        return f"{self.config.base_url.rstrip('/')}/chat/completions"

    def _build_request_data(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """构建请求数据"""
        return {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": False
        }

    def _extract_content_from_response(self, response_data: Dict[str, Any]) -> str:
        """从响应数据中提取内容"""
        if "choices" in response_data and len(response_data["choices"]) > 0:
            return response_data["choices"][0].get("message", {}).get("content", "")
        return "无法从响应中提取内容"

    def _extract_stream_content(self, chunk: Dict[str, Any]) -> Optional[str]:
        """从流式响应块中提取内容"""
        if "choices" in chunk and chunk["choices"]:
            delta = chunk["choices"][0].get("delta", {})
            return delta.get("content", "")
        return None

    async def chat_completion(self, messages: List[Dict[str, str]]) -> str:
        """非流式聊天补全"""
        if self._client is None:
            return "错误：AI客户端未初始化"

        try:
            endpoint = self._get_api_endpoint()
            data = self._build_request_data(messages)

            logger.debug(f"发送AI请求到 {endpoint}, 模型: {self.config.model}")

            response = await self._client.post(endpoint, json=data, headers=self._get_headers())
            response.raise_for_status()
            response_data = response.json()

            content = self._extract_content_from_response(response_data)
            logger.debug(f"收到AI响应，长度: {len(content)}")

            return content

        except httpx.HTTPStatusError as e:
            error_msg = f"API请求失败: {e.response.status_code}"
            logger.error(f"HTTP错误: {e.response.status_code} - {e.response.text}")
            return error_msg
        except httpx.RequestError as e:
            error_msg = f"网络连接失败: {str(e)}"
            logger.error(f"请求错误: {str(e)}")
            return error_msg

    async def chat_completion_stream(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        """流式聊天补全，逐块返回内容"""
        if self._client is None:
            yield "错误：AI客户端未初始化"
            return

        try:
            endpoint = self._get_api_endpoint()
            data = self._build_request_data(messages)
            data["stream"] = True

            logger.debug(f"发送流式AI请求到 {endpoint}, 模型: {self.config.model}")

            async with self._client.stream("POST", endpoint, json=data, headers=self._get_headers()) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        chunk_data = line[6:]

                        if chunk_data.strip() == "[DONE]":
                            break

                        try:
                            chunk_json = json.loads(chunk_data)
                            content = self._extract_stream_content(chunk_json)
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue

        except httpx.HTTPStatusError as e:
            error_msg = f"API流式请求失败: {e.response.status_code}"
            logger.error(f"流式HTTP错误: {e.response.status_code}")
            yield error_msg
        except httpx.RequestError as e:
            error_msg = f"网络流式请求失败: {str(e)}"
            logger.error(f"流式请求错误: {str(e)}")
            yield error_msg

    async def close(self):
        """关闭HTTP客户端"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None


class AIManager:
    """AI管理器，负责创建和管理AI提供商"""

    def __init__(self, config_manager):
        self.config_manager = config_manager
        self._provider: Optional[AIProvider] = None

    def get_provider_config(self, provider_id: Optional[str] = None) -> Optional[AIProviderConfig]:
        """获取指定提供商的配置"""
        if provider_id is None:
            raw_id = self.config_manager.get_config("ai.default_provider")
            provider_id = str(raw_id) if raw_id is not None else "default"

        provider_config = self.config_manager.get_config(f"ai.providers.{provider_id}")
        if not provider_config:
            logger.error(f"找不到提供商配置: {provider_id}")
            return None

        try:
            return AIProviderConfig(
                name=str(provider_config.get("name", provider_id)),
                api_key=str(provider_config.get("api_key", "")),
                base_url=str(provider_config.get("base_url", "")),
                model=str(provider_config.get("model", "")),
                temperature=float(provider_config.get("temperature", 0.7)),
                max_tokens=int(provider_config.get("max_tokens", 2000)),
                stream=bool(provider_config.get("stream", True))
            )
        except (ValueError, TypeError) as e:
            logger.error(f"提供商配置解析错误: {str(e)}")
            return None

    def create_provider(self, provider_id: Optional[str] = None) -> Optional[AIProvider]:
        """创建AI提供商实例并保存"""
        provider_config = self.get_provider_config(provider_id)
        if not provider_config:
            return None

        try:
            self._provider = AIProvider(provider_config)
            logger.info(f"已创建AI提供商: {provider_config.name}")
            return self._provider
        except Exception as e:
            logger.error(f"创建AI提供商失败: {str(e)}")
            return None

    async def chat(self, messages: List[Dict[str, str]], stream: bool = True):
        """统一对话接口"""
        if self._provider is None:
            if not self.create_provider():
                yield "错误：未配置有效的AI提供商"
                return

        if self._provider is not None:
            if stream:
                async for chunk in self._provider.chat_completion_stream(messages):
                    yield chunk
            else:
                yield await self._provider.chat_completion(messages)

    async def close_provider(self):
        """安全关闭客户端资源"""
        if self._provider is not None:
            await self._provider.close()
            self._provider = None

    def get_available_providers(self) -> List[str]:
        """获取所有可用的提供商ID"""
        providers = self.config_manager.get_config("ai.providers")
        if providers and isinstance(providers, dict):
            return list(providers.keys())
        return []

    def update_provider_config(self, provider_id: str, config_updates: Dict[str, Any]) -> bool:
        """更新提供商配置"""
        try:
            current_config = self.config_manager.get_config(f"ai.providers.{provider_id}")
            if current_config is None:
                logger.error(f"找不到要更新的提供商: {provider_id}")
                return False

            updated_config = {**current_config, **config_updates}
            self.config_manager.set_config(f"ai.providers.{provider_id}", updated_config)

            logger.info(f"已更新提供商配置: {provider_id}")
            return True
        except Exception as e:
            logger.error(f"更新提供商配置失败: {str(e)}")
            return False
