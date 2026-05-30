# 🚀 Insightor VSCode 插件 - 5 分钟快速启动

## 前提条件

- ✅ Python 3.11+ 已安装
- ✅ VSCode 1.85+ 已安装
- ✅ 有 LLM API Key (OpenAI/DeepSeek/Claude)

---

## 步骤 1: 安装 Insightor CLI (2 分钟)

```bash
# 克隆并安装
git clone https://github.com/SCU-GuGuGaGa/Insightor.git
cd Insightor
pip install -e .

# 验证
python -m insightor --version
```

## 步骤 2: 配置 API Key (1 分钟)

在项目根目录创建 `.env`:

```bash
# 选择一个
OPENAI_API_KEY=sk-xxx
# 或
DEEPSEEK_API_KEY=sk-xxx
# 或
ANTHROPIC_API_KEY=sk-xxx
```

## 步骤 3: 安装 VSCode 插件 (2 分钟)

```bash
cd vscode-extension
npm install
npm run compile

# 在 VSCode 中打开
code .

# 按 F5 启动调试
```

## 步骤 4: 测试 (30 秒)

在新打开的 VSCode 窗口中：

1. 按 `Ctrl+Shift+P`
2. 输入 "Insightor: Describe PR"
3. 输入测试 PR: `https://github.com/SCU-GuGuGaGa/Insightor/pull/21`
4. 选择 `quick`
5. 查看侧边栏结果

---

## ✅ 完成！

现在你可以：

- 审查任何 GitHub PR
- 查看 AI 生成的发现
- 应用代码修复建议
- 发布审查到 GitHub

## 📚 更多信息

- [完整安装指南](INSTALL.md)
- [使用文档](README.md)
- [开发指南](DEVELOPMENT.md)

## 🆘 遇到问题？

查看 [INSTALL.md](INSTALL.md) 的故障排查部分。
