#!/usr/bin/env python3
"""
检查句子特征
"""
import re
from pathlib import Path

with open("Part1文本.md", "r", encoding="utf-8") as f:
    content = f.read()

# 提取英文句子（简单正则）
sentences = re.findall(r'[A-Z][^.!?]*[.!?]', content)
print(f"找到 {len(sentences)} 个句子")

# 检查每个句子的长度和非ASCII字符
for i, sent in enumerate(sentences[:50]):
    # 长度
    length = len(sent)
    # 非ASCII字符
    non_ascii = sum(1 for c in sent if ord(c) > 127)
    # 中文字符
    chinese = sum(1 for c in sent if '\u4e00' <= c <= '\u9fff')
    # 标点符号
    punctuation = sum(1 for c in sent if c in '.,;:!?\'"')
    
    if non_ascii > 0 or chinese > 0:
        print(f"{i}: 长度 {length}, 非ASCII {non_ascii}, 中文 {chinese}, 标点 {punctuation}")
        print(f"   {sent[:80]}...")
        print()