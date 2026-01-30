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
from typing import List, Dict, Tuple, Set
from difflib import SequenceMatcher
import openai
import edge_tts
import genanki
from dotenv import load_dotenv


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


def deduplicate_sentences(qa_pairs: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], Dict[str, List[str]]]:
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
    
    for item in all_sentences:
        sent = item['sentence']
        
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
        
        if not is_duplicate:
            unique_sentences.append(item)
            source_map[sent] = [f"{item['topic']} - {item['question']}"]
    
    print(f"  去重后剩余 {len(unique_sentences)} 个句子")
    print(f"  去除了 {len(all_sentences) - len(unique_sentences)} 个重复句子")
    
    return unique_sentences, source_map


def parse_text_with_ai(text: str) -> List[Dict[str, str]]:
    """
    使用 DeepSeek API 将文本拆解为句子，并生成中文翻译和关键词提示
    
    Args:
        text: 原始英文文本
        
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
        
        # 解析 JSON
        data = json.loads(content)
        
        print(f"✓ 成功解析 {len(data)} 个句子")
        return data
        
    except json.JSONDecodeError as e:
        print(f"✗ JSON 解析失败: {e}")
        print(f"API 返回内容:\n{content}")
        raise
    except Exception as e:
        print(f"✗ API 调用失败: {e}")
        raise


async def generate_audio(text: str, filename: Path) -> None:
    """
    使用 Edge-TTS 生成英文语音
    
    Args:
        text: 要转换的英文文本
        filename: 输出的 MP3 文件路径
    """
    try:
        communicate = edge_tts.Communicate(text, VOICE)
        await communicate.save(str(filename))
        print(f"  ✓ 生成音频: {filename.name}")
    except Exception as e:
        print(f"  ✗ 音频生成失败 ({filename.name}): {e}")
        raise


async def generate_all_audio(sentences: List[Dict[str, str]]) -> List[Path]:
    """
    批量生成所有句子的音频文件
    
    Args:
        sentences: 句子数据列表
        
    Returns:
        生成的音频文件路径列表
    """
    TEMP_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    
    tasks = []
    audio_files = []
    
    for idx, sentence in enumerate(sentences):
        # 使用句子内容生成哈希作为文件名，避免重复
        sent_hash = hashlib.md5(sentence['english'].encode()).hexdigest()[:8]
        audio_file = TEMP_AUDIO_DIR / f"part1_{sent_hash}.mp3"
        audio_files.append(audio_file)
        tasks.append(generate_audio(sentence["english"], audio_file))
    
    print(f"\n开始生成 {len(tasks)} 个音频文件...")
    await asyncio.gather(*tasks)
    print("✓ 所有音频文件生成完成\n")
    
    return audio_files


def create_anki_deck(sentences: List[Dict[str, str]], audio_files: List[Path]) -> str:
    """
    创建 Anki 卡片包
    
    Args:
        sentences: 句子数据列表
        audio_files: 音频文件路径列表
        
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
    for idx, (sentence, audio_file) in enumerate(zip(sentences, audio_files)):
        # 创建 Note
        note = genanki.Note(
            model=model,
            fields=[
                sentence['chinese'],
                sentence['keywords'],
                sentence['english'],
                f'[sound:{audio_file.name}]'
            ]
        )
        deck.add_note(note)
        
        # 添加音频文件到 Package
        package.media_files.append(str(audio_file))
        
        if (idx + 1) % 10 == 0 or idx == len(sentences) - 1:
            print(f"  ✓ 添加句子卡片 {idx + 1}/{len(sentences)}")
    
    # 导出 .apkg 文件
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    package.write_to_file(str(OUTPUT_APKG))
    print(f"\n✓ 成功生成 Anki 包: {OUTPUT_APKG}")
    print(f"  - {len(sentences)} 张句子卡片")
    
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