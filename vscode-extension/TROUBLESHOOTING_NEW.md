# VSCode 插件命令不显示 - 故障排查指南

## 问题描述
在命令面板 (Ctrl+Shift+P) 中搜索 "Insightor" 时，5 个主要命令没有显示。

## 可能的原因和解决方案

### 1. 插件未正确激活
**检查方法：**
- 按 F5 启动调试后，在新窗口中按 `Ctrl+Shift+I` 打开开发者工具
- 查看 Console 标签页，应该看到 "Insightor extension is now active"
- 如果看到错误信息，记录下来

### 2. 激活事件配置问题
当前配置使用 `onStartupFinished`，这意味着插件会在 VSCode 启动完成后激活。

**尝试修改激活事件：**
将 `package.json` 中的 `activationEvents` 改为通配符（确保激活）：
```json
"activationEvents": [
  "*"
]
```

### 3. 调试步骤

#### 步骤 1: 在调试窗口中检查命令是否注册
1. 按 F5 启动调试
2. 在新窗口中按 `Ctrl+Shift+I` 打开开发者工具
3. 在 Console 中输入：
   ```javascript
   vscode.commands.getCommands().then(cmds => console.log(cmds.filter(c => c.includes('insightor'))))
   ```
4. 这会列出所有已注册的 insightor 命令

#### 步骤 2: 检查扩展是否加载
在开发者工具的 Console 中输入：
```javascript
vscode.extensions.all.filter(e => e.id.includes('insightor'))
```

## 快速修复方案

我将为你修改配置文件以确保插件能够正确激活。
