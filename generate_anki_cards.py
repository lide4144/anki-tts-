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
OUTPUT_DIR = Path("output")  # 输出目录
TEMP_AUDIO_DIR = OUTPUT_DIR / "temp_audio"  # 临时音频文件目录
OUTPUT_APKG = OUTPUT_DIR / "IELTS_Speaking_LiHua.apkg"

# Anki Model ID (随机生成的唯一ID)
MODEL_ID = 1607392319
DECK_ID = 2059400110


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


# ============= AI 拆解函数 =============
def parse_text_with_ai(text: str) -> List[Dict[str, str]]:
    """
    使用 DeepSeek API 将文本拆解为句子，并生成中文翻译和关键词提示
    
    Args:
        text: 原始英文文本
        
    Returns:
        包含 english, chinese, keywords 的字典列表
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
        
        content = response.choices[0].message.content.strip()
        
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
    
    # 创建 Deck
    deck = genanki.Deck(DECK_ID, 'IELTS Speaking - Li Hua Story')
    
    # 创建 Package
    package = genanki.Package(deck)
    
    print("开始创建 Anki 卡片...")
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
        
        print(f"  ✓ 添加卡片 {idx + 1}/{len(sentences)}")
    
    # 导出 .apkg 文件
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    package.write_to_file(str(OUTPUT_APKG))
    print(f"\n✓ 成功生成 Anki 包: {OUTPUT_APKG}")
    
    return str(OUTPUT_APKG)


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
        # Step 0: 读取输入文本
        print("📄 Step 0: 读取输入文本...")
        raw_text = load_input_text()
        print()
        
        # Step 1: 调用 AI 拆解文本
        print("📝 Step 1: 使用 DeepSeek API 拆解文本...")
        sentences = parse_text_with_ai(raw_text)
        print()
        
        # Step 2: 生成音频文件
        print("🔊 Step 2: 使用 Edge-TTS 生成语音文件...")
        audio_files = await generate_all_audio(sentences)
        
        # Step 3: 创建 Anki 卡片包
        print("📦 Step 3: 生成 Anki 卡片包...")
        apkg_file = create_anki_deck(sentences, audio_files)
        
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
        # Step 4: 清理临时文件
        print()
        print("🧹 清理临时文件...")
        cleanup_temp_files()


# ============= 程序入口 =============
if __name__ == "__main__":
    asyncio.run(main())