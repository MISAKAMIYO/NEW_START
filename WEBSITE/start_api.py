"""
RAILGUN 模块化 API 服务启动器
启动所有模块的 API 服务
"""

import os
import sys
import logging

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def start_all_services():
    """启动所有模块服务"""
    
    # 导入所有模块API
    try:
        # 导入主API系统
        from module_api import api_manager, app
        
        # 导入各个模块API（这会自动注册模块）
        import music_download_api
        import ai_chat_api
        import tools_api
        
        logger.info("所有模块API已导入并注册")
        
        # 显示可用模块
        modules = list(api_manager.modules.keys())
        logger.info(f"可用模块: {modules}")
        
        # 启动主API服务
        logger.info("启动主API服务...")
        
        # 在主线程中运行Flask应用
        app.run(host='127.0.0.1', port=5000, debug=False, threaded=True)
        
    except Exception as e:
        logger.error(f"启动服务失败: {str(e)}")
        import traceback
        traceback.print_exc()


def start_specific_module(module_name):
    """启动特定模块服务"""
    
    try:
        from module_api import api_manager
        
        # 根据模块名称导入对应的API
        if module_name == 'music-player':
            from module_api import MusicPlayerService
            api_manager.register_module('music-player', MusicPlayerService)
        elif module_name == 'music-download':
            import music_download_api
        elif module_name == 'ai-chat':
            import ai_chat_api
        elif module_name == 'tools':
            import tools_api
        else:
            logger.error(f"未知模块: {module_name}")
            return False
        
        # 启动模块服务
        success, message = api_manager.start_module_service(module_name)
        
        if success:
            logger.info(f"模块服务启动成功: {module_name}")
        else:
            logger.error(f"模块服务启动失败: {module_name} - {message}")
        
        return success
        
    except Exception as e:
        logger.error(f"启动模块服务失败: {module_name} - {str(e)}")
        return False


if __name__ == '__main__':
    print("=" * 50)
    print("RAILGUN 模块化 API 服务")
    print("=" * 50)
    
    # 检查命令行参数
    import sys
    
    if len(sys.argv) > 1:
        # 启动特定模块
        module_name = sys.argv[1]
        print(f"启动模块: {module_name}")
        start_specific_module(module_name)
    else:
        # 启动所有服务
        print("启动所有模块服务...")
        start_all_services()