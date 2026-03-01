import json
import os
import sys
from typing import Any

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class ConfigManager:
    """配置文件管理类，负责settings.json的读写与修改"""
    
    def __init__(self, config_path: str = None):
        """
        初始化配置管理器
        Args:
            config_path (str): 配置文件路径，默认项目根目录的settings.json
        Raises:
            FileNotFoundError: 配置文件不存在且无法自动创建时抛出
            json.JSONDecodeError: 配置文件格式错误时抛出
        """
        if config_path is None:
            config_path = os.path.join(get_base_path(), "settings.json")
        self.config_path = config_path
        self.default_config = {
            "window": {"width": 1200, "height": 800, "x": 100, "y": 100},
            "paths": {"data": "./Data", "ffmpeg": "./ffmpeg.exe", "download": "./Data/Downloads"},
            "features": {
                "ai_chat": True,
                "auto_update": False,
                "diagnostic_cooldown": 60,
                "use_default_cover": True,
                "use_external_lyrics": True
            },
            "ui": {
                "theme": {
                    "frame_bg": "#1f0b2b",  # 深紫色背景
                    "accent": "#7b3fe4",    # 高亮色
                    "text": "#ECEAF6"
                },
                "entry_background": ""  # 主入口背景图片路径（可由用户设置）
            },
            "ai": {
                "default_provider": "openai",
                "providers": {
                    "openai": {
                        "name": "OpenAI",
                        "api_key": "",
                        "base_url": "https://api.openai.com/v1",
                        "model": "gpt-3.5-turbo",
                        "temperature": 0.7,
                        "max_tokens": 2000,
                        "stream": True
                    },
                    "deepseek": {
                        "name": "DeepSeek",
                        "api_key": "",
                        "base_url": "https://api.deepseek.com",
                        "model": "deepseek-chat",
                        "temperature": 0.7,
                        "max_tokens": 2000,
                        "stream": True
                    },
                    "zhipu": {
                        "name": "智谱AI",
                        "api_key": "",
                        "base_url": "https://open.bigmodel.cn/api/paas/v4",
                        "model": "glm-4",
                        "temperature": 0.7,
                        "max_tokens": 2000,
                        "stream": True
                    },
                    "custom": {
                        "name": "自定义",
                        "api_key": "",
                        "base_url": "",
                        "model": "",
                        "temperature": 0.7,
                        "max_tokens": 2000,
                        "stream": True
                    }
                }
            }
        }
        self.config = self.load_config()

    def load_config(self) -> dict:
        """
        加载配置文件，若文件不存在则创建默认配置
        Returns:
            dict: 配置字典
        """
        if not os.path.exists(self.config_path):
            self.save_config(self.default_config)
            return self.default_config
        with open(self.config_path, "r", encoding="utf-8") as f:
            loaded_config = json.load(f)
        
        # 合并默认配置，确保所有新键都存在
        merged_config = self._merge_configs(self.default_config, loaded_config)
        
        # 如果合并后的配置与已加载的不同，保存更新后的配置
        if merged_config != loaded_config:
            self.save_config(merged_config)
        
        return merged_config
    
    def _merge_configs(self, default: dict, loaded: dict) -> dict:
        """
        递归合并配置字典，确保默认配置中的所有键都存在
        Args:
            default (dict): 默认配置字典
            loaded (dict): 已加载的配置字典
        Returns:
            dict: 合并后的配置字典
        """
        result = loaded.copy()
        for key, default_value in default.items():
            if key not in result:
                result[key] = default_value
            elif isinstance(default_value, dict) and isinstance(result[key], dict):
                result[key] = self._merge_configs(default_value, result[key])
        return result

    def save_config(self, new_config: dict) -> None:
        """
        保存配置到文件
        Args:
            new_config (dict): 新的配置字典
        Raises:
            PermissionError: 无文件写入权限时抛出
        """
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(new_config, f, indent=4, ensure_ascii=False)

    def get_config(self, key: str) -> Any:
        """
        获取指定配置项
        Args:
            key (str): 配置键名（支持层级，如"window.width"）
        Returns:
            any: 配置值，若键不存在返回None
        """
        keys = key.split(".")
        value = self.config
        for k in keys:
            if k not in value:
                return None
            value = value[k]
        return value

    def set_config(self, key: str, value: Any) -> None:
        """
        修改指定配置项并保存
        Args:
            key (str): 配置键名（支持层级，如"paths.data"）
            value (any): 新的配置值
        """
        keys = key.split(".")
        config_ref = self.config
        for k in keys[:-1]:
            if k not in config_ref:
                config_ref[k] = {}
            config_ref = config_ref[k]
        config_ref[keys[-1]] = value
        self.save_config(self.config)
    
    def get_all_config(self) -> dict:
        """
        获取所有配置
        Returns:
            dict: 完整的配置字典
        """
        return self.config
    
    def update_config(self, new_config: dict) -> None:
        """
        更新配置（合并新配置到现有配置中）
        Args:
            new_config (dict): 新的配置字典
        """
        # 递归合并新配置到现有配置中
        merged_config = self._merge_configs(self.config, new_config)
        self.config = merged_config
        self.save_config(self.config)