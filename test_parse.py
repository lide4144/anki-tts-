#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

def test_parse():
    with open('Part1文本.md', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f'总行数: {len(lines)}')
    print('\n前20行:')
    for i in range(min(20, len(lines))):
        line = lines[i].strip()
        if line:
            print(f'{i+1}: {repr(line[:80])}')
    
    # 查找"问题:"行
    print('\n\n查找包含"问题:"的行:')
    count = 0
    for i, line in enumerate(lines):
        if '问题:' in line:
            count += 1
            if count <= 3:
                print(f'{i+1}: {repr(line.strip())}')
    
    print(f'\n共找到 {count} 个问题')

if __name__ == '__main__':
    test_parse()
