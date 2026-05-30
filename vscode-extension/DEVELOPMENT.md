# Insightor VSCode Extension - 开发指南

## 项目结构

```
vscode-extension/
├── src/
│   ├── extension.ts              # 插件入口
│   ├── commands/
│   │   └── commandHandler.ts     # 命令处理器
│   ├── services/
│   │   └── insightorService.ts   # Insightor CLI 服务
│   └── views/
│       └── reviewTreeProvider.ts # 侧边栏树视图
├── resources/
│   └── sidebar-icon.svg          # 侧边栏图标
├── package.json                  # 插件配置
├── tsconfig.json                 # TypeScript 配置
└── README.md                     # 用户文档
```

## 开发环境设置

### 1. 安装依赖

```bash
cd vscode-extension
npm install
```

### 2. 编译 TypeScript

```bash
npm run compile
```

或者使用 watch 模式自动编译：

```bash
npm run watch
```

### 3. 调试插件

1. 在 VSCode 中打开 `vscode-extension` 目录
2. 按 `F5` 启动扩展开发主机
3. 在新窗口中测试插件功能

## 功能说明

### 命令

插件提供以下命令（通过命令面板 `Ctrl+Shift+P` 访问）：

- **Insightor: Review PR** - 运行代码审查
- **Insightor: Describe PR** - 生成 PR 描述
- **Insightor: Analyze Risks** - 分析风险
- **Insightor: Full Review** - 完整审查（包含以上所有）
- **Insightor: Publish Review** - 发布审查结果到 GitHub

### 侧边栏视图

- 显示审查结果的树形结构
- 按严重程度分组显示发现
- 点击发现可跳转到代码位置
- 显示合并就绪评分

### 配置项

在 VSCode 设置中可配置：

- `insightor.pythonPath` - Python 可执行文件路径
- `insightor.defaultDepth` - 默认分析深度
- `insightor.model` - LLM 模型覆盖
- `insightor.autoOpenResults` - 自动打开结果
- `insightor.showNotifications` - 显示通知

## 构建和打包

### 编译

```bash
npm run compile
```

### 打包为 VSIX

```bash
npm run package
```

这会生成 `insightor-vscode-0.1.0.vsix` 文件，可以分发给用户安装。

### 发布到 VSCode Marketplace

1. 创建 [Visual Studio Marketplace](https://marketplace.visualstudio.com/) 账号
2. 获取 Personal Access Token
3. 使用 `vsce` 发布：

```bash
npx vsce login <publisher-name>
npx vsce publish
```

## 测试

### 手动测试

1. 按 `F5` 启动调试
2. 在扩展开发主机中：
   - 打开一个工作区
   - 运行 `Insightor: Full Review`
   - 输入测试 PR URL
   - 验证结果显示正确

### 单元测试

```bash
npm test
```

## 常见问题

### 插件无法激活

- 检查 `package.json` 中的 `activationEvents`
- 查看开发者工具控制台的错误信息

### 命令不显示

- 确保命令已在 `package.json` 的 `contributes.commands` 中注册
- 检查 `when` 条件是否满足

### Python 调用失败

- 验证 Python 路径配置正确
- 确保 Insightor CLI 已安装
- 查看输出面板的详细日志

## 代码规范

- 使用 TypeScript strict 模式
- 遵循 ESLint 规则
- 使用 async/await 处理异步操作
- 添加适当的错误处理

## 贡献

欢迎提交 Pull Request！请确保：

1. 代码通过 lint 检查：`npm run lint`
2. 编译无错误：`npm run compile`
3. 功能经过测试
4. 更新相关文档

## 许可证

MIT
