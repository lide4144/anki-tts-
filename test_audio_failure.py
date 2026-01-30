#!/usr/bin/env python3
"""
测试音频生成失败原因
"""
import asyncio
import edge_tts
from pathlib import Path

VOICE = "en-US-ChristopherNeural"

async def test_sentence(text: str, idx: int):
    """测试单个句子"""
    try:
        communicate = edge_tts.Communicate(text, VOICE)
        # 尝试生成到临时文件
        filename = Path(f"test_{idx}.mp3")
        await communicate.save(str(filename))
        print(f"✓ 成功: {text[:50]}...")
        if filename.exists():
            filename.unlink()
        return True
    except Exception as e:
        print(f"✗ 失败 ({idx}): {e}")
        print(f"  句子: {text}")
        return False

async def main():
    # 从 Part1文本.md 中提取一些句子
    with open("Part1文本.md", "r", encoding="utf-8") as f:
        content = f.read()
    
    # 简单提取句子（粗略）
    import re
    # 匹配英文句子（以大写字母开头，以句号、问号、感叹号结尾）
    sentences = re.findall(r'[A-Z][^.!?]*[.!?]', content)
    # 过滤长度
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
    
    print(f"找到 {len(sentences)} 个句子")
    # 取前20个测试
    test_set = sentences[:20]
    
    results = []
    for i, sent in enumerate(test_set):
        success = await test_sentence(sent, i)
        results.append((sent, success))
    
    print("\n=== 结果汇总 ===")
    for sent, success in results:
        status = "✓" if success else "✗"
        print(f"{status} {sent[:60]}...")

if __name__ == "__main__":
    asyncio.run(main())