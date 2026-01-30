#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
sys.path.insert(0, '.')

from generate_part1_anki import parse_part1_text, deduplicate_sentences

with open('Part1文本.md', 'r', encoding='utf-8') as f:
    content = f.read()

print("解析 QA 对...")
qa_pairs = parse_part1_text(content)
print(f"找到 {len(qa_pairs)} 个 QA 对")

print("\n去重相似句子...")
unique_items, source_map = deduplicate_sentences(qa_pairs)

print(f"原始句子总数: {sum(len(qa['answer'].split('. ')) for qa in qa_pairs)}")
print(f"去重后句子数: {len(unique_items)}")

# 打印一些重复的例子
print("\n重复句子来源示例:")
for sent, sources in list(source_map.items())[:5]:
    if len(sources) > 1:
        print(f"句子: {sent[:80]}...")
        print(f"  来源: {sources}")
        print()

# 打印一些独特句子
print("\n独特句子示例:")
for item in unique_items[:5]:
    print(f"句子: {item['sentence'][:80]}...")
    print(f"  话题: {item['topic']}")
    print(f"  问题: {item['question'][:60]}...")
    print()