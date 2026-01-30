#!/usr/bin/env python3
"""
比较新旧去重算法
"""
import re
import sys
from difflib import SequenceMatcher
from typing import List, Dict, Tuple, Set
from sentence_transformers import SentenceTransformer
import numpy as np

# ---------- 旧算法 ----------
def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def normalize_sentence(s: str) -> str:
    s = s.lower()
    s = re.sub(r'[^\w\s]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def deduplicate_sentences_old(qa_pairs: List[Dict[str, str]], threshold: float = 0.75) -> Tuple[List[Dict[str, str]], Dict[str, List[str]]]:
    """
    去除相似的句子，返回去重后的句子列表和来源映射
    """
    all_sentences = []
    
    # 首先收集所有句子
    for qa in qa_pairs:
        answer = qa['answer']
        # 使用更智能的分句（保留缩写）
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', answer)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        for sent in sentences:
            # 过滤太短的句子
            if len(sent.split()) < 3:
                continue
            
            all_sentences.append({
                'sentence': sent,
                'topic': qa['topic'],
                'question': qa['question'],
                'full_answer': answer
            })
    
    print(f"  共提取 {len(all_sentences)} 个原始句子")
    
    # 去重
    unique_sentences = []
    source_map = {}  # sentence -> list of sources
    normalized_set = set()  # 用于快速检测完全重复
    
    for item in all_sentences:
        sent = item['sentence']
        normalized = normalize_sentence(sent)
        
        # 检查是否与已保存的句子相似
        is_duplicate = False
        for existing in unique_sentences:
            existing_sent = existing['sentence']
            
            # 如果长度相差太大，跳过相似度计算
            len_ratio = len(sent) / len(existing_sent) if existing_sent else 0
            if len_ratio < 0.7 or len_ratio > 1.43:
                continue
            
            sim = similarity(sent, existing_sent)
            if sim >= threshold:
                is_duplicate = True
                # 记录来源
                key = existing_sent
                if key not in source_map:
                    source_map[key] = []
                source_map[key].append(f"{item['topic']} - {item['question']}")
                break
        
        # 如果未发现相似，但规范化后完全相同，也视为重复
        if not is_duplicate and normalized in normalized_set:
            # 找到对应的原始句子
            for existing in unique_sentences:
                if normalize_sentence(existing['sentence']) == normalized:
                    is_duplicate = True
                    key = existing['sentence']
                    if key not in source_map:
                        source_map[key] = []
                    source_map[key].append(f"{item['topic']} - {item['question']}")
                    break
        
        if not is_duplicate:
            unique_sentences.append(item)
            source_map[sent] = [f"{item['topic']} - {item['question']}"]
            normalized_set.add(normalized)
    
    print(f"  去重后剩余 {len(unique_sentences)} 个句子")
    print(f"  去除了 {len(all_sentences) - len(unique_sentences)} 个重复句子")
    
    return unique_sentences, source_map

# ---------- 新算法 ----------
model = SentenceTransformer('all-MiniLM-L6-v2')

def compute_embeddings(sentences: List[str]) -> np.ndarray:
    return model.encode(sentences, convert_to_tensor=False)

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    from numpy import dot
    from numpy.linalg import norm
    return dot(a, b) / (norm(a) * norm(b))

def deduplicate_sentences_semantic(qa_pairs: List[Dict[str, str]], threshold: float = 0.75) -> Tuple[List[Dict[str, str]], Dict[str, List[str]]]:
    """
    基于语义相似度去重
    """
    all_sentences = []
    
    for qa in qa_pairs:
        answer = qa['answer']
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', answer)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        for sent in sentences:
            if len(sent.split()) < 3:
                continue
            all_sentences.append({
                'sentence': sent,
                'topic': qa['topic'],
                'question': qa['question'],
                'full_answer': answer
            })
    
    print(f"  共提取 {len(all_sentences)} 个原始句子")
    
    # 提取句子文本
    sentence_texts = [item['sentence'] for item in all_sentences]
    embeddings = compute_embeddings(sentence_texts)
    
    unique_sentences = []
    unique_embeddings = []
    source_map = {}
    
    for idx, (item, emb) in enumerate(zip(all_sentences, embeddings)):
        sent = item['sentence']
        duplicate = False
        for j, (u_item, u_emb) in enumerate(zip(unique_sentences, unique_embeddings)):
            sim = cosine_similarity(emb, u_emb)
            if sim >= threshold:
                duplicate = True
                key = u_item['sentence']
                if key not in source_map:
                    source_map[key] = []
                source_map[key].append(f"{item['topic']} - {item['question']}")
                break
        if not duplicate:
            unique_sentences.append(item)
            unique_embeddings.append(emb)
            source_map[sent] = [f"{item['topic']} - {item['question']}"]
    
    print(f"  去重后剩余 {len(unique_sentences)} 个句子")
    print(f"  去除了 {len(all_sentences) - len(unique_sentences)} 个重复句子")
    
    return unique_sentences, source_map

# ---------- 解析函数 ----------
def parse_part1_text(content: str) -> List[Dict[str, str]]:
    qa_pairs = []
    lines = content.split('\n')
    
    current_topic = ""
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith('话题:'):
            current_topic = line.replace('话题:', '').strip()
            i += 1
            continue
        
        question_match = re.match(r'问题:\s*(\d+)\.\s*(.+)', line)
        if question_match:
            question_num = question_match.group(1)
            question_text = question_match.group(2).strip()
            
            answer_lines = []
            i += 1
            
            while i < len(lines) and not lines[i].strip().startswith('回答:'):
                i += 1
            
            if i < len(lines) and lines[i].strip().startswith('回答:'):
                i += 1
            
            while i < len(lines):
                current_line = lines[i]
                stripped = current_line.strip()
                
                if (re.match(r'问题:\s*\d+\.', stripped) or
                    stripped.startswith('话题:') or
                    stripped == '---'):
                    break
                
                if stripped.startswith('关键词:'):
                    i += 1
                    continue
                
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

# ---------- 主测试 ----------
def main():
    print("读取 Part1 文本...")
    with open('Part1文本.md', 'r', encoding='utf-8') as f:
        content = f.read()
    
    qa_pairs = parse_part1_text(content)
    
    print("\n=== 旧算法（基于字符串相似度）===")
    old_unique, old_map = deduplicate_sentences_old(qa_pairs)
    
    print("\n=== 新算法（基于语义相似度）===")
    new_unique, new_map = deduplicate_sentences_semantic(qa_pairs)
    
    print("\n=== 比较结果 ===")
    print(f"旧算法去重后句子数: {len(old_unique)}")
    print(f"新算法去重后句子数: {len(new_unique)}")
    print(f"差异: {len(old_unique) - len(new_unique)}")
    
    # 检查哪些句子被新算法去除了，但旧算法保留了
    old_sentences = set(item['sentence'] for item in old_unique)
    new_sentences = set(item['sentence'] for item in new_unique)
    
    removed_by_new = old_sentences - new_sentences
    added_by_new = new_sentences - old_sentences
    
    print(f"\n新算法额外去除的句子数: {len(removed_by_new)}")
    print(f"新算法额外保留的句子数: {len(added_by_new)}")
    
    if removed_by_new:
        print("\n示例：新算法认为重复（但旧算法未发现）的句子:")
        for sent in list(removed_by_new)[:3]:
            print(f"  - {sent[:80]}...")
    
    # 检查重复组
    print("\n新算法重复组示例（重复次数 > 1）:")
    count = 0
    for sent, sources in new_map.items():
        if len(sources) > 1:
            print(f"保留句子: {sent[:80]}...")
            print(f"  来源: {sources[:3]}")
            count += 1
            if count >= 3:
                break

if __name__ == "__main__":
    main()