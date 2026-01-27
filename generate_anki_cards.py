#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
雅思口语 Anki 卡片生成器
使用 DeepSeek API 拆解句子，Edge-TTS 生成语音，最后导出为 .apkg 文件
"""

import os
import sys
import json
import asyncio
import re
from pathlib import Path
from typing import List, Dict
import openai
import edge_tts
import genanki
from dotenv import load_dotenv


# ============= 加载环境变量 =============
# 从 .env 文件加载环境变量
load_dotenv()

# ============= 配置项 =============
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
VOICE = "en-US-ChristopherNeural"  # Edge-TTS 语音
INPUT_FILE = Path("输入文本.md")  # 输入文本文件
QUESTION_FILE = Path("问题本身.md")  # 雅思题目文件
OUTPUT_DIR = Path("output")  # 输出目录
TEMP_AUDIO_DIR = OUTPUT_DIR / "temp_audio"  # 临时音频文件目录
# OUTPUT_APKG 将根据题目动态生成

# Anki Model ID (随机生成的唯一ID)
MODEL_ID = 1607392319
# DECK_ID 将根据题目动态生成（使用题目哈希值确保唯一性）


# ============= 读取输入文本 =============
def load_input_text() -> str:
    """
    从输入文件读取文本内容
    
    Returns:
        文件内容字符串
    """
    try:
        if not INPUT_FILE.exists():
            print(f"✗ 错误: 找不到输入文件 '{INPUT_FILE}'")
            print(f"  请确保文件存在于当前目录")
            sys.exit(1)
        
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        if not content:
            print(f"✗ 错误: 输入文件 '{INPUT_FILE}' 是空的")
            sys.exit(1)
        
        print(f"✓ 成功读取输入文件: {INPUT_FILE}")
        print(f"  文本长度: {len(content)} 字符")
        return content
        
    except Exception as e:
        print(f"✗ 读取文件失败: {e}")
        sys.exit(1)


def load_question() -> str:
    """
    从题目文件读取雅思 Part 2 题目
    
    Returns:
        题目内容字符串
    """
    try:
        if not QUESTION_FILE.exists():
            print(f"⚠️  警告: 找不到题目文件 '{QUESTION_FILE}'")
            print(f"  将使用默认题目格式")
            return ""
        
        with open(QUESTION_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        print(f"✓ 成功读取题目文件: {QUESTION_FILE}")
        return content
        
    except Exception as e:
        print(f"⚠️  警告: 读取题目文件失败: {e}")
        return ""


def sanitize_filename(text: str) -> str:
    """
    清理文本使其适合作为文件名
    
    Args:
        text: 原始文本
        
    Returns:
        清理后的文件名
    """
    # 获取第一行
    first_line = text.split('\n')[0].strip()
    
    # 移除或替换非法字符
    # Windows 文件名不允许的字符: < > : " / \ | ? *
    illegal_chars = '<>:"/\\|?*'
    for char in illegal_chars:
        first_line = first_line.replace(char, '')
    
    # 移除多余的空格
    first_line = ' '.join(first_line.split())
    
    # 限制长度（避免文件名过长）
    max_length = 100
    if len(first_line) > max_length:
        first_line = first_line[:max_length].strip()
    
    # 如果清理后为空，使用默认名称
    if not first_line:
        first_line = "IELTS_Speaking"
    
    return first_line


# ============= AI 拆解函数 =============
def parse_text_with_ai(text: str, question: str) -> tuple[List[Dict[str, str]], str]:
    """
    使用 DeepSeek API 将文本拆解为句子，并生成中文翻译和关键词提示
    
    Args:
        text: 原始英文文本
        question: 雅思 Part 2 题目
        
    Returns:
        (句子列表, 1分钟笔记) 的元组
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
        # 第一次调用：拆解句子
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that returns only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        content = response.choices[0].message.content.strip()
        
        # 移除可能的 Markdown 代码块标记
        content = re.sub(r'^```json\s*', '', content)
        content = re.sub(r'^```\s*', '', content)
        content = re.sub(r'\s*```$', '', content)
        
        # 解析 JSON
        data = json.loads(content)
        
        print(f"✓ 成功解析 {len(data)} 个句子")
        
        # 第二次调用：生成1分钟笔记
        print("📋 生成1分钟准备笔记...")
        
        if question:
            notes_prompt = f"""
你是一个雅思口语教学助手。考生在雅思口语 Part 2 有1分钟的准备时间，需要在题目卡上快速写下关键词笔记。

请根据以下题目和回答内容，生成一个简洁的关键词笔记，要求：
1. 按照题目的要点顺序组织（Who, How often, How/why, How feel）
2. 每个要点下只写2-4个关键词
3. 使用简写、符号，能在1分钟内快速写下
4. 帮助考生按正确顺序串联句子

题目：
{question}

回答内容：
{text}

请直接返回笔记内容，格式如下：

Who: cousin Li Hua, software engineer, Shenzhen
How often: every week, community center
How/why: teach elderly, smartphones, developed app
How feel: proud, inspired, help classmates
"""
        else:
            notes_prompt = f"""
你是一个雅思口语教学助手。考生在雅思口语 Part 2 有1分钟的准备时间，需要快速写下关键词笔记。

请根据以下回答内容，生成一个简洁的关键词笔记，要求：
1. 按照故事发展顺序组织
2. 每个部分只写2-4个关键词
3. 使用简写、符号，能在1分钟内快速写下
4. 帮助考生按正确顺序串联句子

回答内容：
{text}

请直接返回笔记内容。
"""
        
        notes_response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": notes_prompt}
            ],
            temperature=0.3
        )
        
        notes = notes_response.choices[0].message.content.strip()
        print(f"✓ 成功生成1分钟笔记")
        
        return data, notes
        
    except json.JSONDecodeError as e:
        print(f"✗ JSON 解析失败: {e}")
        print(f"API 返回内容:\n{content}")
        raise
    except Exception as e:
        print(f"✗ API 调用失败: {e}")
        raise


# ============= 音频生成函数 =============
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
        audio_file = TEMP_AUDIO_DIR / f"audio_{idx:03d}.mp3"
        audio_files.append(audio_file)
        tasks.append(generate_audio(sentence["english"], audio_file))
    
    print(f"\n开始生成 {len(tasks)} 个音频文件...")
    await asyncio.gather(*tasks)
    print("✓ 所有音频文件生成完成\n")
    
    return audio_files


# ============= Anki 卡片生成 =============
def create_anki_deck(sentences: List[Dict[str, str]], audio_files: List[Path], one_minute_notes: str, question: str, output_filename: str, deck_name: str) -> str:
    """
    创建 Anki 卡片包
    
    Args:
        sentences: 句子数据列表
        audio_files: 音频文件路径列表
        one_minute_notes: 1分钟准备笔记
        question: 雅思题目内容
        output_filename: 输出文件名
        deck_name: 牌组名称
        
    Returns:
        生成的 .apkg 文件路径
    """
    # 定义普通句子卡片模板
    model = genanki.Model(
        MODEL_ID,
        'IELTS Speaking Model',
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
                    <div style="font-size: 16px; color: #666; text-align: center; margin-top: 15px;">
                        <i>💡 提示: {{Keywords}}</i>
                    </div>
                ''',
                'afmt': '''
                    <div style="font-family: Arial; font-size: 24px; text-align: center; margin: 20px;">
                        {{Chinese}}
                    </div>
                    <div style="font-size: 16px; color: #666; text-align: center; margin-top: 15px;">
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
    
    # 定义1分钟笔记卡片模板（使用不同的 Model ID）
    notes_model = genanki.Model(
        MODEL_ID + 1,
        'IELTS Speaking Notes Model',
        fields=[
            {'name': 'Title'},
            {'name': 'Notes'},
        ],
        templates=[
            {
                'name': 'Notes Card',
                'qfmt': '''
                    <div style="font-family: Arial; text-align: center; padding: 30px; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; border-radius: 10px; margin: 20px;">
                        <h1 style="font-size: 32px; margin: 0;">⏱️ {{Title}}</h1>
                        <p style="font-size: 16px; margin-top: 10px; opacity: 0.9;">Part 2 准备时间笔记</p>
                    </div>
                    <div style="text-align: center; margin-top: 20px; padding: 20px;">
                        <p style="font-size: 18px; color: #555;">🤔 如果现在是考试，你会在题目卡上写什么？</p>
                        <p style="font-size: 14px; color: #999; margin-top: 10px;">（你有1分钟时间准备）</p>
                    </div>
                ''',
                'afmt': '''
                    <div style="font-family: Arial; text-align: center; padding: 30px; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; border-radius: 10px; margin: 20px;">
                        <h1 style="font-size: 32px; margin: 0;">⏱️ {{Title}}</h1>
                        <p style="font-size: 16px; margin-top: 10px; opacity: 0.9;">Part 2 准备时间笔记</p>
                    </div>
                    <div style="background-color: #fffbf0; padding: 30px; margin: 20px; border-radius: 10px; border: 2px dashed #ffa500; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                        <div style="font-size: 18px; line-height: 2; color: #333; text-align: left; font-family: 'Courier New', monospace; white-space: pre-wrap;">{{Notes}}</div>
                    </div>
                    <div style="text-align: center; margin-top: 20px; padding: 15px; background-color: #e7f3ff; border-radius: 5px; border-left: 4px solid #2196F3;">
                        <p style="font-size: 14px; color: #1565c0; margin: 0;">
                            ✏️ <strong>考试技巧：</strong>在1分钟准备时间内，快速写下这些关键词，帮助你按顺序串联句子！
                        </p>
                    </div>
                ''',
            },
        ],
        css='''
            .card {
                font-family: Arial, sans-serif;
                background-color: #ffffff;
                padding: 20px;
            }
        '''
    )
    
    # 创建 Deck
    # 使用题目内容生成唯一的 Deck ID（通过哈希）
    deck_id = hash(deck_name) % (10 ** 10)  # 生成一个10位数的ID
    if deck_id < 0:
        deck_id = abs(deck_id)
    
    deck = genanki.Deck(deck_id, deck_name)
    
    # 创建 Package
    package = genanki.Package(deck)
    
    print("开始创建 Anki 卡片...")
    
    # 添加普通句子卡片
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
        
        print(f"  ✓ 添加句子卡片 {idx + 1}/{len(sentences)}")
    
    # 添加1分钟笔记卡片
    # 如果有题目内容，使用题目作为标题；否则使用默认标题
    card_title = question if question else '1分钟笔记'
    notes_card = genanki.Note(
        model=notes_model,
        fields=[
            card_title,
            one_minute_notes
        ]
    )
    deck.add_note(notes_card)
    print(f"  ✓ 添加1分钟笔记卡片")
    
    # 导出 .apkg 文件
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{output_filename}.apkg"
    package.write_to_file(str(output_path))
    print(f"\n✓ 成功生成 Anki 包: {output_path}")
    print(f"  - {len(sentences)} 张句子卡片")
    print(f"  - 1 张1分钟笔记卡片")
    
    return str(output_path)


# ============= 清理临时文件 =============
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


# ============= 主函数 =============
async def main():
    """主执行流程"""
    print("=" * 60)
    print("雅思口语 Anki 卡片生成器".center(60))
    print("=" * 60)
    print()
    
    try:
        # Step 0: 读取输入文件
        print("📄 Step 0: 读取输入文件...")
        raw_text = load_input_text()
        question = load_question()
        print()
        
        # Step 1: 调用 AI 拆解文本并生成1分钟笔记
        print("📝 Step 1: 使用 DeepSeek API 拆解文本...")
        sentences, one_minute_notes = parse_text_with_ai(raw_text, question)
        print()
        
        # Step 2: 生成音频文件
        print("🔊 Step 2: 使用 Edge-TTS 生成语音文件...")
        audio_files = await generate_all_audio(sentences)
        
        # Step 3: 生成输出文件名和牌组名称
        if question:
            # 获取题目第一行作为名称
            question_first_line = question.split('\n')[0].strip()
            output_filename = sanitize_filename(question)
            deck_name = question_first_line
            print(f"📝 输出文件名: {output_filename}.apkg")
            print(f"📚 牌组名称: {deck_name}")
        else:
            output_filename = "IELTS_Speaking"
            deck_name = "IELTS Speaking"
            print(f"📝 使用默认文件名: {output_filename}.apkg")
            print(f"📚 使用默认牌组名称: {deck_name}")
        
        # Step 4: 创建 Anki 卡片包
        print("📦 Step 4: 生成 Anki 卡片包...")
        apkg_file = create_anki_deck(sentences, audio_files, one_minute_notes, question, output_filename, deck_name)
        
        print()
        print("=" * 60)
        print("✅ 全部完成！".center(60))
        print(f"输出文件: {apkg_file}".center(60))
        print("=" * 60)
        
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ 错误: {e}")
        print("=" * 60)
        raise
    
    finally:
        # Step 5: 清理临时文件
        print()
        print("🧹 清理临时文件...")
        cleanup_temp_files()


# ============= 程序入口 =============
if __name__ == "__main__":
    asyncio.run(main())