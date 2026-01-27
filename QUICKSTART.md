# 快速开始指南

## 3 分钟快速上手

### 1️⃣ 安装依赖

```bash
pip install -r requirements.txt
```

或者：
```bash
pip install openai edge-tts genanki python-dotenv
```

### 2️⃣ 配置 API Key

1. 获取 DeepSeek API Key：https://platform.deepseek.com/
2. 复制配置文件模板：

**Windows:**
```cmd
copy .env.example .env
```

**Linux/Mac:**
```bash
cp .env.example .env
```

3. 编辑 `.env` 文件，填入你的 API Key：

```env
DEEPSEEK_API_KEY=sk-your-actual-api-key-here
```

### 3️⃣ 准备输入文本

编辑 `输入文本.md` 文件，粘贴你的雅思口语文本。

### 4️⃣ 测试环境（可选）

```bash
python test_setup.py
```

确保所有测试都通过。

### 5️⃣ 运行脚本

```bash
python generate_anki_cards.py
```

### 6️⃣ 导入 Anki

打开 Anki → 文件 → 导入 → 选择 `output/IELTS_Speaking_LiHua.apkg`

## 完成！🎉

现在你可以在 Anki 中开始学习了！

---

## 常见问题

**Q: 提示找不到 .env 文件？**
A: 确保已经从 `.env.example` 复制创建了 `.env` 文件。

**Q: API Key 错误？**
A: 检查 `.env` 文件中的 API Key 是否正确，格式为 `DEEPSEEK_API_KEY=sk-...`

**Q: 找不到输入文件？**
A: 确保 `输入文本.md` 文件存在于当前目录。

---

**遇到其他问题？** 查看完整的 [README.md](README.md) 文档。