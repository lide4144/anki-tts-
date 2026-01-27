# 雅思口语 Anki 卡片生成器

这是一个自动化工具，用于将雅思口语文本转换为 Anki 记忆卡片。它会自动调用 DeepSeek API 拆解句子，使用 Edge-TTS 生成高质量语音，最后导出为可直接导入 Anki 的 `.apkg` 文件。

## 功能特点

✨ **AI 智能拆解** - 使用 DeepSeek API 自动将长文本拆解为独立句子，并生成中文翻译和关键词提示  
🔊 **高质量语音** - 使用 Edge-TTS 的 `en-US-ChristopherNeural` 声音生成真人般的英文语音  
📦 **一键导出** - 自动生成 Anki 卡片包，可直接导入 Anki 使用  
🎨 **精美卡片** - 卡片正面显示中文+关键词提示，背面显示英文+自动播放音频  
🧹 **自动清理** - 运行完成后自动删除临时音频文件

## 卡片样式

**正面（提问）：**
```
你是一个学习英语的学生。
💡 提示: you, learning, English, student
```

**背面（答案）：**
```
你是一个学习英语的学生。
💡 提示: you, learning, English, student
─────────────────────
You are a student learning English.
🔊 [自动播放音频]
```

## 安装依赖

### 1. 确保已安装 Python 3.10+

```bash
python --version
```

### 2. 安装所需的 Python 包

```bash
pip install -r requirements.txt
```

或者手动安装：

```bash
pip install openai edge-tts genanki python-dotenv
```

## 配置

### 1. 获取 DeepSeek API Key

1. 访问 [DeepSeek 平台](https://platform.deepseek.com/)
2. 注册账号并获取 API Key

### 2. 创建 .env 配置文件

复制示例配置文件并编辑：

```bash
# 复制示例文件
copy .env.example .env

# 或者在 Linux/Mac 上
cp .env.example .env
```

然后编辑 `.env` 文件，填入你的 API Key：

```env
DEEPSEEK_API_KEY=sk-your-actual-api-key-here
```

**注意**: `.env` 文件已被添加到 `.gitignore`，不会被提交到 Git 仓库，保护你的 API Key 安全。

## 使用方法

### 1. 准备输入文本

编辑 `输入文本.md` 文件，将你的雅思口语文本粘贴进去：

```markdown
你的雅思口语文本内容
可以是多个段落
每个句子都会被自动拆解
```

脚本会自动读取这个文件的内容。

### 2. 测试环境（可选但推荐）

运行测试脚本检查配置是否正确：

```bash
python test_setup.py
```

### 3. 运行脚本

```bash
python generate_anki_cards.py
```

### 4. 查看输出

脚本运行成功后，会在 `output` 目录下生成：
- `IELTS_Speaking_LiHua.apkg` - Anki 卡片包文件

### 5. 导入到 Anki

1. 打开 Anki 应用
2. 点击 "文件" → "导入"
3. 选择生成的 `.apkg` 文件
4. 开始学习！

## 运行示例

```
============================================================
                  雅思口语 Anki 卡片生成器
============================================================

📄 Step 0: 读取输入文本...
✓ 成功读取输入文件: 输入文本.md
  文本长度: 1234 字符

📝 Step 1: 使用 DeepSeek API 拆解文本...
✓ 成功解析 5 个句子

🔊 Step 2: 使用 Edge-TTS 生成语音文件...

开始生成 5 个音频文件...
  ✓ 生成音频: audio_000.mp3
  ✓ 生成音频: audio_001.mp3
  ✓ 生成音频: audio_002.mp3
  ✓ 生成音频: audio_003.mp3
  ✓ 生成音频: audio_004.mp3
✓ 所有音频文件生成完成

📦 Step 3: 生成 Anki 卡片包...
开始创建 Anki 卡片...
  ✓ 添加卡片 1/5
  ✓ 添加卡片 2/5
  ✓ 添加卡片 3/5
  ✓ 添加卡片 4/5
  ✓ 添加卡片 5/5

✓ 成功生成 Anki 包: output\IELTS_Speaking_LiHua.apkg

============================================================
                        ✅ 全部完成！                        
              输出文件: output\IELTS_Speaking_LiHua.apkg              
============================================================

🧹 清理临时文件...
✓ 临时音频文件已清理
```

## 自定义配置

你可以在 `generate_anki_cards.py` 开头修改以下配置项：

```python
# 输入文本文件
INPUT_FILE = Path("输入文本.md")

# 语音选择（可选其他 Edge-TTS 声音）
VOICE = "en-US-ChristopherNeural"

# 输出目录
OUTPUT_DIR = Path("output")

# 输出文件名
OUTPUT_APKG = OUTPUT_DIR / "IELTS_Speaking_LiHua.apkg"

# Anki Model/Deck ID（如果冲突可以修改）
MODEL_ID = 1607392319
DECK_ID = 2059400110
```

如果你想使用不同的输入文件，只需修改 `INPUT_FILE` 的值即可。

### 可用的 Edge-TTS 英文声音

- `en-US-ChristopherNeural` (男声，推荐)
- `en-US-JennyNeural` (女声)
- `en-US-GuyNeural` (男声)
- `en-GB-RyanNeural` (英式男声)
- `en-GB-SoniaNeural` (英式女声)

查看更多声音：
```bash
edge-tts --list-voices
```

## 故障排除

### 1. 导入错误

**错误信息：** `ModuleNotFoundError: No module named 'xxx'`

**解决方法：**
```bash
pip install -r requirements.txt
```

### 2. API Key 未配置

**错误信息：** `✗ 错误: 未设置 DEEPSEEK_API_KEY`

**解决方法：**
- 确保已创建 `.env` 文件
- 在 `.env` 文件中正确设置 `DEEPSEEK_API_KEY=your-api-key-here`
- 重新运行脚本

### 3. 找不到输入文件

**错误信息：** `✗ 错误: 找不到输入文件 '输入文本.md'`

**解决方法：**
- 确保 `输入文本.md` 文件存在于当前目录
- 或者修改 `generate_anki_cards.py` 中的 `INPUT_FILE` 配置指向正确的文件

### 4. API 调用失败

**错误信息：** `API 调用失败: xxx`

**可能原因：**
- API Key 错误
- 网络连接问题
- API 配额不足

**解决方法：**
- 检查 `.env` 文件中的 API Key 是否正确
- 确认网络连接正常
- 登录 DeepSeek 平台查看配额

### 5. JSON 解析失败

**错误信息：** `JSON 解析失败: xxx`

**可能原因：**
- API 返回格式不符合预期
- 输入文本过长或格式特殊

**解决方法：**
- 检查程序输出的 "API 返回内容"
- 尝试缩短输入文本
- 调整 Prompt 提示词

### 6. 音频生成失败

**错误信息：** `音频生成失败: xxx`

**可能原因：**
- 网络连接问题（Edge-TTS 需要联网）
- 磁盘空间不足

**解决方法：**
- 检查网络连接
- 确保有足够的磁盘空间

## 技术栈

- **Python 3.10+** - 编程语言
- **OpenAI SDK** - 用于调用 DeepSeek API
- **Edge-TTS** - 微软 Edge 浏览器的 TTS 引擎
- **genanki** - 生成 Anki 卡片包
- **python-dotenv** - 读取 .env 配置文件
- **asyncio** - 异步处理音频生成

## 项目结构

```
.
├── generate_anki_cards.py  # 主程序
├── requirements.txt        # 依赖列表
├── README.md              # 说明文档
├── QUICKSTART.md          # 快速开始指南
├── test_setup.py          # 环境测试脚本
├── .env.example           # API Key 配置模板
├── .env                   # API Key 配置文件（需自行创建）
├── .gitignore             # Git 忽略文件
├── 输入文本.md             # 输入文本文件
└── output/                # 输出目录
    └── IELTS_Speaking_LiHua.apkg  # 生成的 Anki 包
```

## License

MIT License

## 作者

Python 全栈专家 🚀

---

**提示：** 第一次运行时，Edge-TTS 可能需要下载语音数据，请耐心等待。