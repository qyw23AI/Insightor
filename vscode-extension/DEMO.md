# 🎯 Insightor VSCode 插件 - 使用演示

## 演示场景 1: 快速审查 PR

### 步骤

1. **启动插件**
   - 在 VSCode 中按 `F5` 启动扩展开发主机
   - 或安装 VSIX 后直接使用

2. **打开命令面板**
   ```
   按 Ctrl+Shift+P (Mac: Cmd+Shift+P)
   ```

3. **选择命令**
   ```
   输入: Insightor: Review PR
   ```

4. **输入 PR URL**
   ```
   示例: https://github.com/SCU-GuGuGaGa/Insightor/pull/21
   ```

5. **选择分析深度**
   ```
   选择: standard (推荐)
   ```

6. **查看结果**
   - 侧边栏显示审查树
   - 点击发现跳转到代码
   - 查看详情面板

### 预期结果

```
✅ 分析完成
📊 显示发现列表
🔴 Critical: 2 个
🟡 High: 5 个
🔵 Medium: 8 个
⚪ Low: 3 个
```

---

## 演示场景 2: 完整审查并发布

### 步骤

1. **运行完整审查**
   ```
   Ctrl+Shift+P → Insightor: Full Review
   输入 PR URL
   选择 standard 深度
   ```

2. **等待分析**
   ```
   进度通知显示:
   [describe] 分析中...
   [risks] 分析中...
   [review] 分析中...
   ```

3. **查看生成的报告**
   ```
   自动打开: insightor-full-review-{pr}.md
   
   内容包括:
   1. PR 总结
   2. 风险分析
   3. 代码审查
   4. 改进建议
   ```

4. **编辑报告**
   ```markdown
   #### 1. 🔴 [critical] SQL Injection vulnerability
   
   - [x] confirmed        ← 勾选确认
   - [ ] false_positive
   - [ ] addressed
   - [ ] ignored
   - **审查者:** @yourname
   - **备注:** 需要立即修复
   ```

5. **发布到 GitHub**
   ```
   Ctrl+Shift+P → Insightor: Publish Review
   选择编辑的 Markdown 文件
   选择 "No - Publish to GitHub"
   ```

### 预期结果

```
✅ 生成完整报告
✅ 人工确认发现
✅ 发布到 GitHub PR
✅ 在 PR 页面看到评论
```

---

## 演示场景 3: 应用代码修复

### 步骤

1. **查看发现**
   - 在侧边栏点击任意发现
   - 自动跳转到代码位置
   - 显示详情面板

2. **查看建议**
   ```
   详情面板显示:
   - 当前代码
   - 建议代码
   - 置信度: 85%
   ```

3. **应用修复**
   - 点击 "Apply Fix" 按钮
   - 代码自动替换
   - 显示成功提示

### 预期结果

```
✅ 代码自动更新
✅ 修复已应用
✅ 可以继续编辑
```

---

## 演示场景 4: 配置自定义规则

### 步骤

1. **创建配置文件**
   ```bash
   # 在项目根目录
   touch .insightor.yml
   ```

2. **添加自定义规则**
   ```yaml
   review:
     custom_rules: |
       1. 所有 API 端点必须有认证
       2. 禁止使用字符串拼接 SQL
       3. 敏感数据不能记录到日志
     
     conventions: |
       - 使用 async/await
       - 错误消息使用中文
     
     focus_categories: ["security", "performance"]
     min_severity: medium
   ```

3. **运行审查**
   ```
   Insightor: Review PR
   ```

4. **验证规则应用**
   - 查看发现是否包含自定义规则
   - 检查是否聚焦指定类别

### 预期结果

```
✅ 自定义规则生效
✅ 发现符合项目规范
✅ 聚焦关键类别
```

---

## 演示场景 5: 故障排查

### 场景: "Insightor CLI not found"

#### 诊断步骤

1. **检查 Python**
   ```bash
   python --version
   # 应该显示 Python 3.11+
   ```

2. **检查 Insightor CLI**
   ```bash
   python -m insightor --version
   # 应该显示版本号
   ```

3. **配置 Python 路径**
   ```
   VSCode Settings → insightor.pythonPath
   设置为: C:\Python311\python.exe (Windows)
   或: /usr/bin/python3 (Linux/Mac)
   ```

4. **重新测试**
   ```
   Ctrl+Shift+P → Insightor: Review PR
   ```

#### 预期结果

```
✅ CLI 找到
✅ 命令执行成功
✅ 结果正常显示
```

---

## 演示场景 6: 查看详细日志

### 步骤

1. **打开输出面板**
   ```
   View → Output
   选择: Insightor
   ```

2. **运行命令**
   ```
   Insightor: Review PR
   ```

3. **查看日志**
   ```
   Executing: python -m insightor review <url> --depth standard
   正在获取 PR 数据...
   正在处理代码变更...
   正在 AI 分析中...
   Process exited with code 0
   ```

### 预期结果

```
✅ 看到完整执行日志
✅ 可以诊断问题
✅ 了解执行过程
```

---

## 快速测试清单

### 基本功能测试

- [ ] 插件可以激活
- [ ] 命令面板显示 5 个命令
- [ ] 侧边栏显示 Insightor 图标
- [ ] Review PR 命令可以执行
- [ ] Describe PR 命令可以执行
- [ ] Risks 命令可以执行
- [ ] Full Review 命令可以执行
- [ ] Publish 命令可以执行

### UI 测试

- [ ] 侧边栏树视图显示正常
- [ ] 点击发现可以跳转
- [ ] Webview 详情面板显示正常
- [ ] Apply Fix 按钮可以点击
- [ ] 进度通知显示正常
- [ ] 错误提示友好

### 配置测试

- [ ] Python 路径配置生效
- [ ] 默认深度配置生效
- [ ] 模型覆盖配置生效
- [ ] 自动打开配置生效
- [ ] 通知配置生效

---

## 性能基准

### 分析时间（参考）

| 深度 | PR 大小 | 预计时间 |
|------|---------|----------|
| quick | 小 (< 10 文件) | 10-15 秒 |
| standard | 中 (10-30 文件) | 20-40 秒 |
| deep | 大 (30+ 文件) | 40-90 秒 |

### Token 消耗（参考）

| 深度 | Token 预算 | 成本估算 |
|------|-----------|----------|
| quick | ~3K | $0.01-0.02 |
| standard | ~8K | $0.03-0.05 |
| deep | ~16K | $0.06-0.10 |

---

## 常见问题演示

### Q: 如何审查私有仓库的 PR？

**A**: 配置 GitHub Token

```bash
# 在 .env 中添加
GITHUB_TOKEN=ghp_xxxxxxxxxxxxx
```

### Q: 如何使用不同的 LLM 模型？

**A**: 配置模型覆盖

```json
{
  "insightor.model": "gpt-4"
}
```

### Q: 如何批量审查多个 PR？

**A**: 使用脚本

```bash
#!/bin/bash
for pr in 1 2 3; do
  python -m insightor full "https://github.com/owner/repo/pull/$pr"
done
```

---

## 视频演示脚本

### 开场 (30 秒)

```
"大家好，今天演示 Insightor VSCode 插件。
这是一个 AI 驱动的代码审查工具，
可以直接在 VSCode 中审查 GitHub PR。"
```

### 功能演示 (2 分钟)

```
1. 打开命令面板
2. 选择 Full Review
3. 输入 PR URL
4. 等待分析完成
5. 查看侧边栏结果
6. 点击发现跳转代码
7. 应用修复建议
8. 发布审查到 GitHub
```

### 结尾 (30 秒)

```
"Insightor 插件让代码审查变得简单高效。
支持多种 LLM，可自定义规则，
完全开源，欢迎试用！"
```

---

## 截图建议

### 需要的截图

1. **命令面板** - 显示 5 个命令
2. **侧边栏视图** - 显示审查树
3. **详情面板** - 显示发现详情
4. **代码跳转** - 高亮显示问题行
5. **Apply Fix** - 应用修复前后对比
6. **Markdown 报告** - 完整报告示例
7. **配置界面** - 设置页面
8. **输出面板** - 日志显示

---

<div align="center">

## 🎬 准备好演示了！

所有功能都已实现并可以演示

[返回主文档](README.md) | [安装指南](INSTALL.md) | [快速开始](QUICKSTART.md)

</div>
