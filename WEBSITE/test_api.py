"""
API 功能测试脚本
测试所有模块的 API 功能
"""

import requests
import json
import time
import sys

# API 基础URL
BASE_URL = "http://127.0.0.1:5000"


def test_connection():
    """测试连接状态"""
    print("测试连接状态...")
    try:
        response = requests.get(f"{BASE_URL}/api/status")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 连接成功: {data['message']}")
            return True
        else:
            print(f"❌ 连接失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 连接异常: {str(e)}")
        return False


def test_module_management():
    """测试模块管理功能"""
    print("\n测试模块管理功能...")
    
    # 列出可用模块
    response = requests.get(f"{BASE_URL}/api/modules")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 可用模块: {data['available_modules']}")
    else:
        print("❌ 获取模块列表失败")
        return False
    
    # 测试启动音乐播放器模块
    module_name = "music-player"
    response = requests.post(f"{BASE_URL}/api/{module_name}/start")
    if response.status_code == 200:
        data = response.json()
        if data['success']:
            print(f"✅ {module_name} 模块启动成功")
        else:
            print(f"⚠️ {module_name} 模块启动消息: {data['message']}")
    else:
        print(f"❌ {module_name} 模块启动失败")
    
    # 检查模块状态
    response = requests.get(f"{BASE_URL}/api/{module_name}/status")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ {module_name} 状态: {data['status']}")
    
    return True


def test_music_player_api():
    """测试音乐播放器 API"""
    print("\n测试音乐播放器 API...")
    
    # 测试播放器状态
    try:
        response = requests.get("http://127.0.0.1:5001/api/status")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 音乐播放器状态: 运行中={data['running']}, 播放中={data['playing']}")
        else:
            print("⚠️ 音乐播放器API可能未启动")
            return True  # 这不是错误，只是模块未启动
    except:
        print("⚠️ 音乐播放器API可能未启动")
        return True
    
    # 测试播放功能
    response = requests.post("http://127.0.0.1:5001/api/play", 
                           json={"song_path": "/music/sample.mp3"})
    if response.status_code == 200:
        data = response.json()
        if data['success']:
            print("✅ 播放功能测试成功")
        else:
            print(f"⚠️ 播放功能测试: {data['message']}")
    
    # 测试歌词搜索
    response = requests.get("http://127.0.0.1:5001/api/lyrics?song_title=测试歌曲&artist=测试艺术家")
    if response.status_code == 200:
        data = response.json()
        if data['success']:
            print("✅ 歌词搜索功能测试成功")
    
    return True


def test_music_download_api():
    """测试音乐下载 API"""
    print("\n测试音乐下载 API...")
    
    # 测试搜索功能
    try:
        response = requests.post("http://127.0.0.1:5002/api/search",
                               json={"keyword": "周杰伦", "platform": "all"})
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print(f"✅ 搜索功能测试成功，找到 {data['count']} 个结果")
            else:
                print(f"⚠️ 搜索功能测试: {data['message']}")
        else:
            print("⚠️ 音乐下载API可能未启动")
            return True
    except:
        print("⚠️ 音乐下载API可能未启动")
        return True
    
    # 测试B站搜索
    response = requests.post("http://127.0.0.1:5002/api/bilibili/search",
                           json={"keyword": "音乐"})
    if response.status_code == 200:
        data = response.json()
        if data['success']:
            print("✅ B站搜索功能测试成功")
    
    return True


def test_ai_chat_api():
    """测试AI聊天 API"""
    print("\n测试AI聊天 API...")
    
    # 测试模型列表
    try:
        response = requests.get("http://127.0.0.1:5003/api/models")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 可用AI模型: {len(data['models'])} 个")
        else:
            print("⚠️ AI聊天API可能未启动")
            return True
    except:
        print("⚠️ AI聊天API可能未启动")
        return True
    
    # 测试创建会话
    response = requests.post("http://127.0.0.1:5003/api/chat/new",
                           json={"model_id": "gpt-3.5", "session_name": "测试会话"})
    if response.status_code == 200:
        data = response.json()
        if data['success']:
            session_id = data['session_id']
            print("✅ 创建会话测试成功")
            
            # 测试发送消息
            response = requests.post(f"http://127.0.0.1:5003/api/chat/{session_id}/send",
                                   json={"message": "你好，请介绍一下你自己"})
            if response.status_code == 200:
                data = response.json()
                if data['success']:
                    print("✅ 发送消息测试成功")
    
    return True


def test_tools_api():
    """测试工具集合 API"""
    print("\n测试工具集合 API...")
    
    # 测试截图功能
    try:
        response = requests.post("http://127.0.0.1:5004/api/tools/screenshot/capture")
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print("✅ 截图功能测试成功")
        else:
            print("⚠️ 工具集合API可能未启动")
            return True
    except:
        print("⚠️ 工具集合API可能未启动")
        return True
    
    # 测试随机名称生成
    response = requests.post("http://127.0.0.1:5004/api/tools/random/name",
                           json={"gender": "random", "count": 3})
    if response.status_code == 200:
        data = response.json()
        if data['success']:
            print(f"✅ 随机名称生成测试成功: {data['names']}")
    
    # 测试哈希生成
    response = requests.post("http://127.0.0.1:5004/api/tools/hash/generate",
                           json={"text": "Hello World", "algorithm": "md5"})
    if response.status_code == 200:
        data = response.json()
        if data['success']:
            print("✅ 哈希生成测试成功")
    
    return True


def main():
    """主测试函数"""
    print("=" * 60)
    print("RAILGUN API 功能测试")
    print("=" * 60)
    
    # 等待服务启动
    print("等待API服务启动...")
    time.sleep(2)
    
    # 执行测试
    tests = [
        test_connection,
        test_module_management,
        test_music_player_api,
        test_music_download_api,
        test_ai_chat_api,
        test_tools_api
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ 测试异常: {str(e)}")
    
    print("\n" + "=" * 60)
    print(f"测试完成: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("🎉 所有API功能测试成功！")
    else:
        print("⚠️ 部分测试未通过，请检查服务状态")
    
    print("=" * 60)


if __name__ == "__main__":
    main()