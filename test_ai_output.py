#!/usr/bin/env python3
"""
测试 AI 输出
"""
import sys
sys.path.insert(0, '.')
from generate_part1_anki import parse_part1_text, deduplicate_sentences, parse_text_with_ai

with open("Part1文本.md", "r", encoding="utf-8") as f:
    content = f.read()

qa_pairs = parse_part1_text(content)
unique_items, source_map = deduplicate_sentences(qa_pairs)

# 取前5个句子
sample = unique_items[:5]
combined = " ".join([item['sentence'] for item in sample])
print("原始句子:")
for item in sample:
    print(f"  - {item['sentence']}")

print("\n调用 AI 拆解...")
parsed = parse_text_with_ai(combined)
print("AI 输出:")
for p in parsed:
    print(f"  english: {p['english']}")
    print(f"  chinese: {p['chinese']}")
    print(f"  keywords: {p['keywords']}")
    print()