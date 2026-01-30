#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
雅思口语 Part 1 Anki 卡片生成器
用于处理 Part1 文本，自动去重相似句子，生成 Anki 卡片
"""

import os
import sys
import json
import asyncio
import re
import hashlib
from pathlib import Path
from typing import List, Dict, Tuple, Set, Optional
from difflib import SequenceMatcher
import openai
import edge_tts
import genanki
from dotenv import load_dotenv

# 尝试导入 sentence-transformers（用于语义去重）
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False
    SentenceTransformer = None
    np = None


# ============= 加载环境变量 =============
load_dotenv()

# ============= 配置项 =============
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
VOICE = "en-US-ChristopherNeural"  # Edge-TTS 语音
INPUT_FILE = Path("Part1文本.md")  # Part1 输入文件
OUTPUT_DIR = Path("output")  # 输出目录
TEMP_AUDIO_DIR = OUTPUT_DIR / "temp_audio_part1"  # 临时音频文件目录
OUTPUT_APKG = OUTPUT_DIR / "IELTS_Part1_Speaking.apkg"

# Anki Model ID (随机生成的唯一ID)
MODEL_ID = 1607392320
DECK_ID = 1607392321

# ============= 相似度阈值 =============
SIMILARITY_THRESHOLD = 0.75  # 句子相似度超过此阈值认为是重复

# ============= 去重算法配置 =============
USE_SEMANTIC_DEDUP = True  # 使用语义相似度去重（需要 sentence-transformers）
SEMANTIC_THRESHOLD = 0.75   # 语义相似度阈值


def similarity(a: str, b: str) -> float:
    """
    计算两个字符串的相似度
    
    Args:
        a: 字符串1
        b: 字符串2
        
    Returns:
        相似度分数 (0.0 - 1.0)
    """
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


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


def normalize_sentence(s: str) -> str:
    """
    规范化句子以便比较：小写、去除标点、去除多余空格
    """
    # 转换为小写
    s = s.lower()
    # 移除标点符号（保留字母、数字和空格）
    s = re.sub(r'[^\w\s]', '', s)
    # 合并多余空格
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def deduplicate_sentences_string(qa_pairs: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], Dict[str, List[str]]]:
    """
    去除相似的句子，返回去重后的句子列表和来源映射

    Args:
        qa_pairs: 问题-回答对列表

    Returns:
        (去重后的句子列表, 来源映射)
    """
    all_sentences = []
    
    # 首先收集所有句子
    for qa in qa_pairs:
        # 将回答按句子分割
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
            if sim >= SIMILARITY_THRESHOLD:
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


def deduplicate_sentences(qa_pairs: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], Dict[str, List[str]]]:
    """
    去重句子的主函数，根据配置选择算法
    """
    if USE_SEMANTIC_DEDUP and SEMANTIC_AVAILABLE:
        print("使用语义相似度去重算法")
        return deduplicate_sentences_semantic(qa_pairs)
    else:
        if USE_SEMANTIC_DEDUP and not SEMANTIC_AVAILABLE:
            print("警告: 配置了使用语义去重但 sentence-transformers 不可用，回退到字符串相似度")
        print("使用字符串相似度去重算法")
        return deduplicate_sentences_string(qa_pairs)


def deduplicate_sentences_semantic(qa_pairs: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], Dict[str, List[str]]]:
    """
    基于语义相似度去重（使用 sentence-transformers）
    
    Args:
        qa_pairs: 问题-回答对列表
        
    Returns:
        (去重后的句子列表, 来源映射)
    """
    if not SEMANTIC_AVAILABLE:
        print("警告: sentence-transformers 不可用，回退到基于字符串的相似度去重")
        return deduplicate_sentences_string(qa_pairs)
    
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
    
    # 提取句子文本
    sentence_texts = [item['sentence'] for item in all_sentences]
    
    # 加载模型（惰性加载）
    assert SEMANTIC_AVAILABLE and SentenceTransformer is not None
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = model.encode(sentence_texts, convert_to_tensor=False)
    
    # 余弦相似度计算辅助函数
    def cosine_sim(a, b):
        from numpy import dot
        from numpy.linalg import norm
        return dot(a, b) / (norm(a) * norm(b))
    
    # 去重
    unique_sentences = []
    unique_embeddings = []
    source_map = {}
    
    for idx, (item, emb) in enumerate(zip(all_sentences, embeddings)):
        sent = item['sentence']
        duplicate = False
        for j, (u_item, u_emb) in enumerate(zip(unique_sentences, unique_embeddings)):
            sim = cosine_sim(emb, u_emb)
            if sim >= SEMANTIC_THRESHOLD:
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




def parse_text_with_ai(text: str, max_retries: int = 3) -> List[Dict[str, str]]:
    """
    使用 DeepSeek API 将文本拆解为句子，并生成中文翻译和关键词提示

    Args:
        text: 原始英文文本
        max_retries: 最大重试次数

    Returns:
        句子列表，每个包含 english, chinese, keywords
    """
    # 检查 API Key
    if not DEEPSEEK_API_KEY:
        print("✗ 错误: 未设置 DEEPSEEK_API_KEY")
        print("  请在 .env 文件中设置: DEEPSEEK_API_KEY=your-api-key-here")
        sys.exit(1)
    
    client = openai.OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url=DEEPSEEK_BASE_URL
    )
    
    prompt = f"""
你是一个雅思口语教学助手。请将下面的英文文本拆解成独立的句子，并为每个句子提供：
1. english: 原英文句子
2. chinese: 中文翻译
3. keywords: 3-5个英语关键词提示（用于帮助回忆句子）

**重要**: 请只返回纯JSON数组，不要包含任何Markdown标记（如 ```json）或其他文字说明。

输入文本：
{text}

返回格式示例：
[
  {{"english": "Li Hua is a student.", "chinese": "李华是一名学生。", "keywords": "Li Hua, student"}},
  {{"english": "He likes basketball.", "chinese": "他喜欢篮球。", "keywords": "he, likes, basketball"}}
]
"""
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that returns only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            
            if content is None:
                raise ValueError("API 返回内容为空")
            
            content = content.strip()
            
            # 移除可能的 Markdown 代码块标记
            content = re.sub(r'^```json\s*', '', content)
            content = re.sub(r'^```\s*', '', content)
            content = re.sub(r'\s*```$', '', content)
            
            # 尝试提取 JSON 数组（处理可能的多余文本）
            # 查找第一个 '[' 和最后一个 ']'
            start = content.find('[')
            end = content.rfind(']')
            if start != -1 and end != -1 and end > start:
                json_str = content[start:end+1]
            else:
                json_str = content
            
            # 解析 JSON
            data = json.loads(json_str)
            
            # 验证数据结构
            if not isinstance(data, list):
                raise ValueError("API 返回的不是 JSON 数组")
            
            for item in data:
                if not all(key in item for key in ('english', 'chinese', 'keywords')):
                    raise ValueError("API 返回的 JSON 缺少必要字段")
            
            print(f"✓ 成功解析 {len(data)} 个句子")
            return data
            
        except json.JSONDecodeError as e:
            print(f"✗ JSON 解析失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                print(f"API 返回内容:\n{content}")
                raise
            # 等待后重试
            import time
            time.sleep(2 ** attempt)  # 指数退避
        except Exception as e:
            print(f"✗ API 调用失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                raise
            import time
            time.sleep(2 ** attempt)
    
    # 不应到达这里
    raise RuntimeError("重试次数用尽")


async def generate_audio(text: str, filename: Path) -> bool:
    """
    使用 Edge-TTS 生成英文语音
    
    Args:
        text: 要转换的英文文本
        filename: 输出的 MP3 文件路径
        
    Returns:
        成功返回 True，失败返回 False
    """
    try:
        communicate = edge_tts.Communicate(text, VOICE)
        await communicate.save(str(filename))
        print(f"  ✓ 生成音频: {filename.name}")
        return True
    except Exception as e:
        print(f"  ✗ 音频生成失败 ({filename.name}): {e}")
        # 删除可能创建的空文件
        if filename.exists():
            try:
                filename.unlink()
            except:
                pass
        return False


async def generate_audio_with_retry(text: str, filename: Path, max_retries: int = 3) -> bool:
    """
    带重试的音频生成
    
    Args:
        text: 要转换的英文文本
        filename: 输出的 MP3 文件路径
        max_retries: 最大重试次数
        
    Returns:
        成功返回 True，失败返回 False
    """
    for attempt in range(max_retries):
        try:
            success = await generate_audio(text, filename)
            if success:
                return True
            else:
                # generate_audio 内部已打印错误，这里只记录重试
                if attempt < max_retries - 1:
                    print(f"  重试 {attempt + 1}/{max_retries}...")
                    await asyncio.sleep(1)  # 等待1秒后重试
        except Exception as e:
            print(f"  重试 {attempt + 1}/{max_retries} 异常: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
    
    print(f"  ✗ 音频生成重试 {max_retries} 次后仍失败: {filename.name}")
    return False


async def generate_all_audio(sentences: List[Dict[str, str]]) -> List[Optional[Path]]:
    """
    批量生成所有句子的音频文件
    
    Args:
        sentences: 句子数据列表
        
    Returns:
        生成的音频文件路径列表（失败的位置为 None）
    """
    TEMP_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    
    # 限制并发数，避免过多请求导致失败
    CONCURRENT_LIMIT = 3  # 进一步降低并发
    semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)
    
    # 记录失败句子到文件
    failed_log = OUTPUT_DIR / "audio_failed_sentences.txt"
    failed_sentences = []
    
    async def generate_with_limit(sentence: Dict[str, str], idx: int) -> Optional[Path]:
        """带并发限制的音频生成任务"""
        sent_hash = hashlib.md5(sentence['english'].encode()).hexdigest()[:8]
        audio_file = TEMP_AUDIO_DIR / f"part1_{sent_hash}.mp3"
        
        async with semaphore:
            # 在请求之间添加小延迟，避免速率限制
            await asyncio.sleep(0.3)
            success = await generate_audio_with_retry(sentence["english"], audio_file, max_retries=2)
        
        if success:
            return audio_file
        else:
            # 记录失败句子
            print(f"  ✗ 句子 {idx+1} 音频生成失败: {sentence['english'][:50]}...")
            failed_sentences.append({
                'index': idx,
                'english': sentence['english'],
                'chinese': sentence['chinese'],
                'keywords': sentence['keywords']
            })
            return None
    
    print(f"\n开始生成 {len(sentences)} 个音频文件 (并发限制: {CONCURRENT_LIMIT})...")
    
    # 创建所有任务
    tasks = [generate_with_limit(sentence, idx) for idx, sentence in enumerate(sentences)]
    results = await asyncio.gather(*tasks)
    
    # 统计结果
    successful_audio_files = []
    failed_count = 0
    for result in results:
        if result is None:
            successful_audio_files.append(None)
            failed_count += 1
        else:
            successful_audio_files.append(result)
    
    success_count = len(sentences) - failed_count
    print(f"✓ 音频文件生成完成，成功 {success_count} 个，失败 {failed_count} 个\n")
    
    # 保存失败句子日志
    if failed_sentences:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        with open(failed_log, 'w', encoding='utf-8') as f:
            f.write(f"音频生成失败句子 ({len(failed_sentences)} 个):\n\n")
            for item in failed_sentences:
                f.write(f"索引: {item['index']}\n")
                f.write(f"英文: {item['english']}\n")
                f.write(f"中文: {item['chinese']}\n")
                f.write(f"关键词: {item['keywords']}\n")
                f.write("-" * 80 + "\n")
        print(f"  失败句子日志已保存到: {failed_log}")
    
    return successful_audio_files


def create_anki_deck(sentences: List[Dict[str, str]], audio_files: List[Optional[Path]]) -> str:
    """
    创建 Anki 卡片包
    
    Args:
        sentences: 句子数据列表
        audio_files: 音频文件路径列表（可能包含 None）
        
    Returns:
        生成的 .apkg 文件路径
    """
    # 定义卡片模板
    model = genanki.Model(
        MODEL_ID,
        'IELTS Part1 Speaking Model',
        fields=[
            {'name': 'Chinese'},
            {'name': 'Keywords'},
            {'name': 'English'},
            {'name': 'Audio'},
        ],
        templates=[
            {
                'name': 'Card 1',
                'qfmt': '''
                    <div style="font-family: Arial; font-size: 24px; text-align: center; margin: 20px;">
                        {{Chinese}}
                    </div>
                    <div style="font-size: 14px; color: #888; text-align: center; margin-top: 15px;">
                        <i>💡 提示: {{Keywords}}</i>
                    </div>
                ''',
                'afmt': '''
                    <div style="font-family: Arial; font-size: 24px; text-align: center; margin: 20px;">
                        {{Chinese}}
                    </div>
                    <div style="font-size: 14px; color: #888; text-align: center; margin-top: 15px;">
                        <i>💡 提示: {{Keywords}}</i>
                    </div>
                    <hr>
                    <div style="font-size: 20px; color: #333; text-align: center; margin: 20px;">
                        {{English}}
                    </div>
                    <div style="text-align: center; margin-top: 15px;">
                        {{Audio}}
                    </div>
                ''',
            },
        ],
        css='''
            .card {
                font-family: Arial, sans-serif;
                background-color: #f9f9f9;
                padding: 20px;
            }
        '''
    )
    
    # 创建 Deck
    deck = genanki.Deck(DECK_ID, "IELTS Speaking Part 1")
    
    # 创建 Package
    package = genanki.Package(deck)
    
    print("开始创建 Anki 卡片...")
    
    # 添加卡片
    cards_with_audio = 0
    cards_without_audio = 0
    for idx, (sentence, audio_file) in enumerate(zip(sentences, audio_files)):
        # 音频字段
        audio_field = f'[sound:{audio_file.name}]' if audio_file is not None else ''
        # 创建 Note
        note = genanki.Note(
            model=model,
            fields=[
                sentence['chinese'],
                sentence['keywords'],
                sentence['english'],
                audio_field
            ]
        )
        deck.add_note(note)
        
        # 添加音频文件到 Package（如果存在）
        if audio_file is not None:
            package.media_files.append(str(audio_file))
            cards_with_audio += 1
        else:
            cards_without_audio += 1
        
        if (idx + 1) % 10 == 0 or idx == len(sentences) - 1:
            print(f"  ✓ 添加句子卡片 {idx + 1}/{len(sentences)}")
    
    # 导出 .apkg 文件
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    package.write_to_file(str(OUTPUT_APKG))
    print(f"\n✓ 成功生成 Anki 包: {OUTPUT_APKG}")
    print(f"  - {len(sentences)} 张句子卡片（{cards_with_audio} 张带音频，{cards_without_audio} 张无音频）")
    
    return str(OUTPUT_APKG)


def cleanup_temp_files():
    """删除临时音频文件"""
    if TEMP_AUDIO_DIR.exists():
        for file in TEMP_AUDIO_DIR.glob("*.mp3"):
            try:
                file.unlink()
            except Exception as e:
                print(f"警告: 无法删除 {file}: {e}")
        
        try:
            TEMP_AUDIO_DIR.rmdir()
            print("✓ 临时音频文件已清理")
        except Exception as e:
            print(f"警告: 无法删除临时目录: {e}")


async def main():
    """主执行流程"""
    print("=" * 60)
    print("雅思口语 Part 1 Anki 卡片生成器".center(60))
    print("=" * 60)
    print()
    
    try:
        # Step 0: 读取输入文件
        print("📄 Step 0: 读取 Part1 文本文件...")
        if not INPUT_FILE.exists():
            print(f"✗ 错误: 找不到输入文件 '{INPUT_FILE}'")
            sys.exit(1)
        
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"✓ 成功读取输入文件: {INPUT_FILE}")
        print(f"  文件大小: {len(content)} 字符")
        print()
        
        # Step 1: 解析文本，提取问题和回答
        print("📝 Step 1: 解析 Part1 文本结构...")
        qa_pairs = parse_part1_text(content)
        print()
        
        # Step 2: 去重相似句子
        print("🔍 Step 2: 检测并去除相似句子...")
        unique_items, source_map = deduplicate_sentences(qa_pairs)
        print()
        
        # 合并所有独特句子用于 AI 处理
        combined_text = " ".join([item['sentence'] for item in unique_items])
        
        # Step 3: 调用 AI 拆解句子
        print("🤖 Step 3: 使用 DeepSeek API 拆解句子...")
        # 为了效率，分批处理（每批最多 10 个句子）
        batch_size = 10
        all_parsed_sentences = []
        
        for i in range(0, len(unique_items), batch_size):
            batch = unique_items[i:i+batch_size]
            batch_text = " ".join([item['sentence'] for item in batch])
            
            print(f"\n  处理批次 {i//batch_size + 1}/{(len(unique_items) + batch_size - 1)//batch_size}...")
            parsed = parse_text_with_ai(batch_text)
            all_parsed_sentences.extend(parsed)
        
        print(f"\n✓ 共解析 {len(all_parsed_sentences)} 个句子")
        print()
        
        # Step 4: 生成音频文件
        print("🔊 Step 4: 使用 Edge-TTS 生成语音文件...")
        audio_files = await generate_all_audio(all_parsed_sentences)
        
        # Step 5: 创建 Anki 卡片包
        print("📦 Step 5: 生成 Anki 卡片包...")
        apkg_file = create_anki_deck(all_parsed_sentences, audio_files)
        
        print()
        print("=" * 60)
        print("✅ 全部完成！".center(60))
        print(f"输出文件: {apkg_file}".center(60))
        print("=" * 60)
        
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        raise
    
    finally:
        # Step 6: 清理临时文件
        print()
        print("🧹 清理临时文件...")
        cleanup_temp_files()


# ============= 程序入口 =============
if __name__ == "__main__":
    asyncio.run(main())