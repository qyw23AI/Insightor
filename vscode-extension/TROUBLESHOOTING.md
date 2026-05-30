# 🔧 Insightor VSCode 插件 - 故障排查指南

## 问题：执行命令后没有发现

### 可能的原因

1. **Insightor CLI 未安装**
2. **API Key 未配置**
3. **Python 路径不正确**
4. **网络连接问题**
5. **工作区未打开**

---

## 🔍 逐步排查

### 步骤 1: 检查 Insightor CLI 是否安装

```bash
# 在终端中执行
python -m insightor --version
```

**预期输出**: `insightor, version 0.x.x`

**如果失败**:
```bash
# 安装 Insightor CLI
cd d:\Files\项目\qyw_insightor
pip install -e .

# 再次验证
python -m insightor --version
```

---

### 步骤 2: 检查 API Key 配置

```bash
# 检查 .env 文件是否存在
cd d:\Files\项目\qyw_insightor
cat .env

# 或在 Windows 中
type .env
```

**应该包含**:
```
DEEPSEEK_API_KEY=sk-xxx
# 或
OPENAI_API_KEY=sk-xxx
# 或
ANTHROPIC_API_KEY=sk-xxx
```

**如果文件不存在**:
```bash
# 创建 .env 文件
echo "DEEPSEEK_API_KEY=sk-your-key-here" > .env
```

---

### 步骤 3: 测试 CLI 是否正常工作

```bash
# 直接测试 CLI
cd d:\Files\项目\qyw_insightor
python -m insightor describe https://github.com/SCU-GuGuGaGa/Insightor/pull/21 --depth quick
```

**预期结果**: 
- 应该开始分析
- 输出分析结果
- 生成 Markdown 文件

**如果失败**: 查看错误信息，通常是 API Key 问题

---

### 步骤 4: 检查 VSCode 插件配置

在 VSCode 中:

```
1. 按 Ctrl+, 打开设置
2. 搜索 "insightor"
3. 检查 "Insightor: Python Path"
4. 确保设置为正确的 Python 路径
```

**Windows 示例**:
- `python` (如果 Python 在 PATH 中)
- `C:\Python311\python.exe` (完整路径)
- `C:\Users\YourName\AppData\Local\Programs\Python\Python311\python.exe`

---

### 步骤 5: 查看插件输出日志

在 VSCode 中:

```
1. View → Output (或按 Ctrl+Shift+U)
2. 在下拉菜单中选择 "Insightor"
3. 查看详细日志
```

**日志应该显示**:
```
Executing: python -m insightor describe <url> --depth quick
正在获取 PR 数据...
正在处理代码变更...
正在 AI 分析中...
Process exited with code 0
```

**如果看到错误**: 记下错误信息

---

## 🎯 完整测试流程

### 测试 1: 命令行测试（验证 CLI）

```bash
# 1. 进入项目目录
cd d:\Files\项目\qyw_insightor

# 2. 测试 CLI
python -m insightor describe https://github.com/SCU-GuGuGaGa/Insightor/pull/21 --depth quick

# 3. 查看结果
# 应该生成 insightor-review-21-xxxxx.md 文件
ls -la insightor-review-*.md
```

### 测试 2: VSCode 插件测试

```bash
# 1. 启动插件
cd vscode-extension
code .
# 按 F5

# 2. 在新窗口中打开工作区
File → Open Folder → 选择 d:\Files\项目\qyw_insightor

# 3. 运行命令
Ctrl+Shift+P → "Insightor: Describe PR"
输入: https://github.com/SCU-GuGuGaGa/Insightor/pull/21
选择: quick

# 4. 查看输出
View → Output → 选择 "Insightor"
```

---

## 📋 常见错误及解决方案

### 错误 1: "Insightor CLI not found"

**错误信息**:
```
Error: Command failed: python -m insightor
/usr/bin/python: No module named insightor
```

**解决方案**:
```bash
cd d:\Files\项目\qyw_insightor
pip install -e .
```

---

### 错误 2: "API Key not configured"

**错误信息**:
```
Error: DEEPSEEK_API_KEY not found in environment
```

**解决方案**:
```bash
# 创建 .env 文件
cd d:\Files\项目\qyw_insightor
echo "DEEPSEEK_API_KEY=sk-your-key-here" > .env
```

---

### 错误 3: "Failed to fetch PR"

**错误信息**:
```
Error: Failed to fetch PR: 404 Not Found
```

**解决方案**:
- 检查 PR URL 是否正确
- 检查网络连接
- 如果是私有仓库，需要配置 GITHUB_TOKEN

---

### 错误 4: "Python not found"

**错误信息**:
```
Error: spawn python ENOENT
```

**解决方案**:
```
1. 在 VSCode 设置中配置完整的 Python 路径
2. Settings → insightor.pythonPath
3. 设置为: C:\Python311\python.exe
```

---

## 🚀 推荐的测试步骤

### 第一步：验证环境

```bash
# 1. 检查 Python
python --version

# 2. 检查 Insightor CLI
python -m insightor --version

# 3. 检查 API Key
cat .env  # 或 type .env (Windows)

# 4. 测试 CLI
python -m insightor describe https://github.com/SCU-GuGuGaGa/Insightor/pull/21 --depth quick
```

### 第二步：测试插件

```bash
# 1. 启动插件
cd vscode-extension
code .
# 按 F5

# 2. 打开工作区
File → Open Folder

# 3. 运行命令
Ctrl+Shift+P → "Insightor: Describe PR"

# 4. 查看日志
View → Output → Insightor
```

---

## 📞 获取帮助

如果以上步骤都无法解决问题：

1. **查看输出日志**: View → Output → Insightor
2. **记录错误信息**: 复制完整的错误消息
3. **检查环境**: Python 版本、Insightor 版本、API Key
4. **提供信息**: 
   - 操作系统
   - Python 版本
   - 错误日志
   - 执行的命令

---

## ✅ 成功的标志

当一切正常时，你应该看到：

1. **命令执行**:
   ```
   ✅ 右下角显示 "Insightor 分析中..."
   ✅ 进度通知更新
   ```

2. **结果显示**:
   ```
   ✅ 侧边栏显示审查结果树
   ✅ 自动打开 Markdown 文件
   ✅ 输出面板有详细日志
   ```

3. **文件生成**:
   ```
   ✅ .insightor/reviews/ 目录下有 JSON 文件
   ✅ 项目根目录有 Markdown 文件
   ```

---

## 🎯 快速诊断命令

```bash
# 一键诊断脚本
cd d:\Files\项目\qyw_insightor

echo "=== 环境检查 ==="
python --version
python -m insightor --version
cat .env | grep -E "API_KEY" || echo "❌ .env 文件不存在或无 API Key"

echo ""
echo "=== CLI 测试 ==="
python -m insightor describe https://github.com/SCU-GuGuGaGa/Insightor/pull/21 --depth quick --debug

echo ""
echo "=== 检查结果 ==="
ls -la insightor-review-*.md
ls -la .insightor/reviews/
```

---

<div align="center">

**按照以上步骤逐一排查，应该能找到问题所在！**

如果还有问题，请提供详细的错误日志。

</div>
