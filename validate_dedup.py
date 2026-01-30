#!/usr/bin/env python3
"""
验证集成后的去重算法
"""
import sys
sys.path.insert(0, '.')
from generate_part1_anki import parse_part1_text, deduplicate_sentences

print("读取 Part1 文本...")
with open('Part1文本.md', 'r', encoding='utf-8') as f:
    content = f.read()

qa_pairs = parse_part1_text(content)
print(f"解析到 {len(qa_pairs)} 个 QA 对")

print("\n执行去重...")
unique_items, source_map = deduplicate_sentences(qa_pairs)

print(f"去重后句子数: {len(unique_items)}")
print(f"去重前句子总数: {sum(len(qa['answer'].split('. ')) for qa in qa_pairs)}")

# 检查重复组
print("\n重复组示例（重复次数 > 1）:")
count = 0
for sent, sources in source_map.items():
    if len(sources) > 1:
        print(f"保留句子: {sent[:80]}...")
        print(f"  来源: {sources[:3]}")
        count += 1
        if count >= 5:
            break

print("\n验证完成。")