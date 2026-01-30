#!/usr/bin/env python3
"""
测试音频生成的并发问题
"""
import asyncio
import sys
from pathlib import Path

# 添加当前目录到路径以便导入
sys.path.insert(0, '.')
from generate_part1_anki import (
    parse_part1_text,
    deduplicate_sentences,
    parse_text_with_ai,
    generate_all_audio,
    create_anki_deck,
    cleanup_temp_files,
    TEMP_AUDIO_DIR,
    OUTPUT_DIR,
    INPUT_FILE
)

async def test_limited():
    """测试前30个句子的音频生成"""
    print("读取输入文件...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    qa_pairs = parse_part1_text(content)
    unique_items, source_map = deduplicate_sentences(qa_pairs)
    
    # 限制为前30个句子
    limit = 30
    limited_items = unique_items[:limit]
    print(f"\n使用前 {len(limited_items)} 个句子进行测试")
    
    # 合并文本用于 AI 拆解
    combined_text = " ".join([item['sentence'] for item in limited_items])
    print("调用 AI 拆解...")
    parsed_sentences = parse_text_with_ai(combined_text)
    print(f"AI 解析出 {len(parsed_sentences)} 个句子")
    
    # 生成音频
    audio_files = await generate_all_audio(parsed_sentences)
    
    # 统计
    success = sum(1 for af in audio_files if af is not None)
    print(f"\n测试结果: 成功 {success}/{len(parsed_sentences)}")
    
    # 清理临时文件
    cleanup_temp_files()

if __name__ == "__main__":
    asyncio.run(test_limited())