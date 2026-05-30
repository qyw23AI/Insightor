# VSCode 插件调试说明

## 已修复的问题

1. **激活事件**：将 `activationEvents` 从 `onStartupFinished` 改为 `*`，确保插件立即激活
2. **添加调试日志**：在 `activate` 函数中添加了详细的日志输出

## 如何测试

### 步骤 1: 启动调试
1. 在 VSCode 中打开 `vscode-extension` 文件夹
2. 按 `F5` 启动调试（或点击 Run > Start Debugging）
3. 这会打开一个新的 VSCode 窗口（Extension Development Host）

### 步骤 2: 检查激活状态
在新窗口中：
1. 按 `Ctrl+Shift+I` 打开开发者工具
2. 切换到 **Console** 标签页
3. 你应该看到以下日志：
   ```
   === Insightor extension activation started ===
   Extension context: [路径]
   Registering commands...
   Commands registered successfully
   === Insightor extension activation completed ===
   ```

### 步骤 3: 测试命令
1. 按 `Ctrl+Shift+P` 打开命令面板
2. 输入 "Insightor"
3. 你应该看到以下 5 个命令：
   - ✅ **Insightor: Review PR**
   - ✅ **Insightor: Describe PR**
   - ✅ **Insightor: Analyze Risks**
   - ✅ **Insightor: Full Review**
   - ✅ **Insightor: Publish Review**

### 步骤 4: 验证命令注册（可选）
在开发者工具的 Console 中输入：
```javascript
vscode.commands.getCommands().then(cmds => {
    const insightorCmds = cmds.filter(c => c.includes('insightor'));
    console.log('Registered Insightor commands:', insightorCmds);
});
```

应该输出：
```
Registered Insightor commands: [
  "insightor.reviewPR",
  "insightor.describePR",
  "insightor.risksPR",
  "insightor.fullReview",
  "insightor.publishReview",
  "insightor.openSettings",
  "insightor.refreshView",
  "insightor.viewFinding",
  "insightor.applyFix"
]
```

## 如果命令仍然不显示

### 检查 1: 确认插件已激活
在开发者工具 Console 中运行：
```javascript
vscode.extensions.all.forEach(ext => {
    if (ext.id.includes('insightor')) {
        console.log('Extension ID:', ext.id);
        console.log('Is Active:', ext.isActive);
    }
});
```

### 检查 2: 查看错误信息
在开发者工具中查看是否有红色错误信息。常见错误：
- 模块加载失败
- 依赖缺失
- 语法错误

### 检查 3: 重新加载窗口
在调试窗口中：
1. 按 `Ctrl+Shift+P`
2. 输入 "Reload Window"
3. 选择 "Developer: Reload Window"

## 下一步优化（可选）

当前使用 `"activationEvents": ["*"]` 会在 VSCode 启动时立即激活插件。这对开发调试很有用，但会影响性能。

发布前可以改回更精确的激活事件：
```json
"activationEvents": [
  "onCommand:insightor.reviewPR",
  "onCommand:insightor.describePR",
  "onCommand:insightor.risksPR",
  "onCommand:insightor.fullReview",
  "onCommand:insightor.publishReview",
  "onView:insightorView"
]
```

## 常见问题

### Q: 看到 "Insightor CLI not found" 警告
**A:** 这是正常的。插件会检查 Python 环境中是否安装了 insightor。你可以：
- 点击 "Install Instructions" 查看安装说明
- 点击 "Configure Python Path" 配置 Python 路径

### Q: 命令执行时报错
**A:** 确保：
1. Python 已安装
2. insightor 包已安装（`pip install insightor`）
3. 在设置中配置了正确的 Python 路径

### Q: 侧边栏图标不显示
**A:** 检查 `resources/sidebar-icon.svg` 文件是否存在。如果不存在，创建一个简单的 SVG 图标。

## 成功标志

✅ 开发者工具 Console 显示激活日志  
✅ 命令面板中能搜索到 5 个 Insightor 命令  
✅ 左侧活动栏出现 Insightor 图标（如果图标文件存在）  
✅ 点击命令后能正常弹出输入框
