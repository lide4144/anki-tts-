#!/usr/bin/env python3
"""
测试第31-80个句子的音频生成
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, '.')
from generate_part1_anki import (
    parse_part1_text,
    deduplicate_sentences,
    parse_text_with_ai,
    generate_all_audio,
    cleanup_temp_files,
    TEMP_AUDIO_DIR,
    INPUT_FILE
)

async def test_batch(start=30, count=50):
    """测试指定范围的句子"""
    print(f"读取输入文件...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    qa_pairs = parse_part1_text(content)
    unique_items, source_map = deduplicate_sentences(qa_pairs)
    
    # 选择范围
    end = min(start + count, len(unique_items))
    batch_items = unique_items[start:end]
    print(f"\n使用句子 {start} 到 {end-1} (共 {len(batch_items)} 个)")
    
    # 合并文本用于 AI 拆解
    combined_text = " ".join([item['sentence'] for item in batch_items])
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
    asyncio.run(test_batch(30, 50))