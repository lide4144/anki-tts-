#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境配置测试脚本
用于验证所有依赖是否正确安装
"""

import sys
import os


def test_python_version():
    """测试 Python 版本"""
    print("=" * 60)
    print("测试 Python 版本".center(60))
    print("=" * 60)
    
    version = sys.version_info
    print(f"当前版本: Python {version.major}.{version.minor}.{version.micro}")
    
    if version.major >= 3 and version.minor >= 10:
        print("✓ Python 版本符合要求 (>= 3.10)")
        return True
    else:
        print("✗ Python 版本过低，需要 >= 3.10")
        return False


def test_imports():
    """测试依赖包导入"""
    print("\n" + "=" * 60)
    print("测试依赖包".center(60))
    print("=" * 60)
    
    packages = {
        'openai': 'OpenAI SDK',
        'edge_tts': 'Edge-TTS',
        'genanki': 'Genanki',
        'dotenv': 'Python-dotenv',
    }
    
    all_ok = True
    for module, name in packages.items():
        try:
            __import__(module)
            print(f"✓ {name} ({module}) - 已安装")
        except ImportError:
            print(f"✗ {name} ({module}) - 未安装")
            all_ok = False
    
    return all_ok


def test_env_file():
    """测试 .env 文件"""
    print("\n" + "=" * 60)
    print("测试 .env 文件".center(60))
    print("=" * 60)
    
    from pathlib import Path
    env_file = Path(".env")
    
    if env_file.exists():
        print("✓ .env 文件存在")
        return True
    else:
        print("✗ .env 文件不存在")
        print("  请复制 .env.example 为 .env 并配置 API Key")
        return False


def test_api_key():
    """测试 API Key 配置"""
    print("\n" + "=" * 60)
    print("测试 API Key 配置".center(60))
    print("=" * 60)
    
    # 尝试从 .env 文件加载
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        print("⚠️  警告: python-dotenv 未安装")
    
    api_key = os.getenv("DEEPSEEK_API_KEY")
    
    if api_key and api_key != "your-api-key-here":
        print(f"✓ API Key 已配置")
        print(f"  前缀: {api_key[:10]}...")
        return True
    else:
        print("✗ API Key 未配置或使用默认值")
        print("  请在 .env 文件中设置: DEEPSEEK_API_KEY=your-api-key-here")
        return False


def test_input_file():
    """测试输入文件"""
    print("\n" + "=" * 60)
    print("测试输入文件".center(60))
    print("=" * 60)
    
    from pathlib import Path
    input_file = Path("输入文本.md")
    
    if input_file.exists():
        size = input_file.stat().st_size
        print(f"✓ 输入文件存在: {input_file}")
        print(f"  文件大小: {size} 字节")
        
        # 检查文件是否为空
        if size > 0:
            print("✓ 文件内容不为空")
            return True
        else:
            print("✗ 文件是空的")
            return False
    else:
        print(f"✗ 输入文件不存在: {input_file}")
        print("  请创建此文件并添加雅思口语文本")
        return False


def test_asyncio():
    """测试异步支持"""
    print("\n" + "=" * 60)
    print("测试异步支持".center(60))
    print("=" * 60)
    
    try:
        import asyncio
        
        async def test_async():
            return "OK"
        
        result = asyncio.run(test_async())
        print(f"✓ Asyncio 正常工作")
        return True
    except Exception as e:
        print(f"✗ Asyncio 测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + "雅思口语 Anki 卡片生成器 - 环境测试".center(58) + "║")
    print("╚" + "═" * 58 + "╝")
    print()
    
    results = []
    
    # 运行所有测试
    results.append(("Python 版本", test_python_version()))
    results.append(("依赖包", test_imports()))
    results.append((".env 文件", test_env_file()))
    results.append(("API Key", test_api_key()))
    results.append(("输入文件", test_input_file()))
    results.append(("异步支持", test_asyncio()))
    
    # 总结
    print("\n" + "=" * 60)
    print("测试总结".center(60))
    print("=" * 60)
    
    all_passed = all(result for _, result in results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{name}: {status}")
    
    print()
    if all_passed:
        print("🎉 所有测试通过！你可以开始使用脚本了。")
        print()
        print("下一步:")
        print("  1. 确保 输入文本.md 包含你的雅思口语文本")
        print("  2. 运行: python generate_anki_cards.py")
    else:
        print("⚠️  部分测试失败，请先解决上述问题。")
        print()
        print("常见解决方案:")
        print("  1. 安装依赖: pip install -r requirements.txt")
        print("  2. 创建 .env 文件: copy .env.example .env")
        print("  3. 在 .env 中设置 API Key")
        print("  4. 确保 输入文本.md 文件存在且不为空")
        print("  5. 升级 Python: 访问 https://www.python.org/downloads/")
    
    print("=" * 60)
    print()
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())