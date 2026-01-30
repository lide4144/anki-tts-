#!/usr/bin/env python3
"""
测试语义相似度去重
"""
import re
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Tuple

def parse_part1_text(content: str) -> List[Dict[str, str]]:
    """
    解析 Part1 文本，提取话题、问题和回答
    """
    qa_pairs = []
    lines = content.split('\n')
    
    current_topic = ""
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # 匹配话题行
        if line.startswith('话题:'):
            current_topic = line.replace('话题:', '').strip()
            i += 1
            continue
        
        # 匹配问题行
        question_match = re.match(r'问题:\s*(\d+)\.\s*(.+)', line)
        if question_match:
            question_num = question_match.group(1)
            question_text = question_match.group(2).strip()
            
            # 查找对应的回答
            answer_lines = []
            i += 1
            
            # 跳过空行和关键词行，直到找到"回答:"
            while i < len(lines) and not lines[i].strip().startswith('回答:'):
                i += 1
            
            # 跳过"回答:"行
            if i < len(lines) and lines[i].strip().startswith('回答:'):
                i += 1
            
            # 收集回答内容（直到下一个问题、话题或分隔符）
            while i < len(lines):
                current_line = lines[i]
                stripped = current_line.strip()
                
                # 如果遇到下一个问题、话题或分隔符，停止
                if (re.match(r'问题:\s*\d+\.', stripped) or
                    stripped.startswith('话题:') or
                    stripped == '---'):
                    break
                
                # 跳过关键词行
                if stripped.startswith('关键词:'):
                    i += 1
                    continue
                
                # 只添加非空行
                if stripped:
                    answer_lines.append(current_line)
                
                i += 1
            
            answer = '\n'.join(answer_lines).strip()
            
            if answer:
                qa_pairs.append({
                    'topic': current_topic,
                    'question_num': question_num,
                    'question': question_text,
                    'answer': answer
                })
            
            continue
        
        i += 1
    
    print(f"✓ 解析到 {len(qa_pairs)} 个问题-回答对")
    return qa_pairs

# 加载模型
print("加载 sentence-transformers 模型...")
model = SentenceTransformer('all-MiniLM-L6-v2')

def compute_embeddings(sentences: List[str]) -> np.ndarray:
    """计算句子嵌入"""
    return model.encode(sentences, convert_to_tensor=False)  # 返回 numpy 数组

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """计算余弦相似度"""
    from numpy import dot
    from numpy.linalg import norm
    return dot(a, b) / (norm(a) * norm(b))

def deduplicate_semantic(sentences: List[str], threshold: float = 0.75) -> Tuple[List[str], Dict[str, List[int]]]:
    """
    基于语义相似度去重
    
    Args:
        sentences: 句子列表
        threshold: 相似度阈值
        
    Returns:
        (去重后的句子列表, 映射: 保留句子 -> 重复句子索引列表)
    """
    embeddings = compute_embeddings(sentences)
    unique_sentences = []
    unique_embeddings = []
    source_map = {}  # 保留句子索引 -> 重复句子索引列表
    
    for i, (sent, emb) in enumerate(zip(sentences, embeddings)):
        duplicate = False
        for j, (u_sent, u_emb) in enumerate(zip(unique_sentences, unique_embeddings)):
            sim = cosine_similarity(emb, u_emb)
            if sim >= threshold:
                duplicate = True
                # 记录重复
                if u_sent not in source_map:
                    source_map[u_sent] = []
                source_map[u_sent].append(i)
                break
        if not duplicate:
            unique_sentences.append(sent)
            unique_embeddings.append(emb)
            source_map[sent] = [i]
    
    return unique_sentences, source_map

# 读取数据
print("读取 Part1 文本...")
with open('Part1文本.md', 'r', encoding='utf-8') as f:
    content = f.read()

qa_pairs = parse_part1_text(content)
print(f"解析到 {len(qa_pairs)} 个 QA 对")

# 提取所有句子
all_sentences = []
for qa in qa_pairs:
    answer = qa['answer']
    # 简单分句
    sentences = [s.strip() for s in answer.split('.') if s.strip()]
    all_sentences.extend(sentences)

print(f"提取到 {len(all_sentences)} 个原始句子")
# 取前50个句子进行测试
test_sentences = all_sentences[:50]
print(f"测试前 {len(test_sentences)} 个句子")

# 去重
unique, mapping = deduplicate_semantic(test_sentences, threshold=0.75)
print(f"去重后剩余 {len(unique)} 个句子")
print(f"去除了 {len(test_sentences) - len(unique)} 个重复句子")

# 显示一些重复组
print("\n重复组示例:")
for sent, indices in mapping.items():
    if len(indices) > 1:
        print(f"保留句子: {sent[:80]}...")
        print(f"  重复索引: {indices}")
        for idx in indices[1:]:
            print(f"    - {test_sentences[idx][:80]}...")
        print()