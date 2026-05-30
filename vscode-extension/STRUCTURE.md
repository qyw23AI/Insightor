# Insightor VSCode Extension - 项目结构

```
vscode-extension/
├── .vscode/                      # VSCode 配置
│   ├── extensions.json           # 推荐扩展
│   ├── launch.json               # 调试配置
│   └── tasks.json                # 构建任务
│
├── resources/                    # 资源文件
│   ├── sidebar-icon.svg          # 侧边栏图标
│   └── icon.png.txt              # 图标占位符
│
├── src/                          # 源代码
│   ├── commands/
│   │   └── commandHandler.ts    # 命令处理器 (450 行)
│   ├── services/
│   │   └── insightorService.ts  # CLI 服务 (280 行)
│   ├── views/
│   │   └── reviewTreeProvider.ts # 树视图 (180 行)
│   └── extension.ts              # 插件入口 (120 行)
│
├── out/                          # 编译输出
│   ├── commands/
│   │   └── commandHandler.js
│   ├── services/
│   │   └── insightorService.js
│   ├── views/
│   │   └── reviewTreeProvider.js
│   └── extension.js
│
├── node_modules/                 # 依赖包 (335 个)
│
├── .eslintrc.json                # ESLint 配置
├── .gitignore                    # Git 忽略
├── .vscodeignore                 # 打包忽略
├── CHANGELOG.md                  # 变更日志
├── COMPLETION_REPORT.md          # 完成报告
├── DEVELOPMENT.md                # 开发指南
├── INSTALL.md                    # 安装指南
├── package.json                  # 插件清单
├── PROJECT_SUMMARY.md            # 项目总结
├── QUICKSTART.md                 # 快速开始
├── QUICKSTART_5MIN.md            # 5分钟启动
├── README.md                     # 用户文档
└── tsconfig.json                 # TypeScript 配置

总计:
- 源文件: 4 个 TypeScript 文件 (~1,030 行)
- 配置: 6 个配置文件
- 文档: 8 个 Markdown 文件 (~2,500 行)
- 编译输出: 4 个 JavaScript 文件
- 依赖: 335 个 npm 包
```

## 核心文件说明

### 源代码 (src/)

| 文件 | 行数 | 职责 |
|------|------|------|
| `extension.ts` | 120 | 插件激活入口，注册命令和视图 |
| `commands/commandHandler.ts` | 450 | 实现所有命令逻辑，处理用户交互 |
| `services/insightorService.ts` | 280 | 封装 CLI 调用，管理进程和结果 |
| `views/reviewTreeProvider.ts` | 180 | 提供侧边栏树视图数据 |

### 配置文件

| 文件 | 用途 |
|------|------|
| `package.json` | 插件清单，定义命令、视图、配置 |
| `tsconfig.json` | TypeScript 编译配置 |
| `.eslintrc.json` | 代码规范配置 |
| `.vscode/launch.json` | 调试配置 |
| `.vscode/tasks.json` | 构建任务配置 |

### 文档文件

| 文件 | 内容 |
|------|------|
| `README.md` | 用户文档，功能介绍 |
| `INSTALL.md` | 详细安装指南 |
| `QUICKSTART.md` | 快速开始教程 |
| `QUICKSTART_5MIN.md` | 5分钟快速启动 |
| `DEVELOPMENT.md` | 开发者指南 |
| `PROJECT_SUMMARY.md` | 项目总结 |
| `COMPLETION_REPORT.md` | 完成报告 |
| `CHANGELOG.md` | 版本变更记录 |

## 数据流

```
用户操作 (命令面板)
    ↓
extension.ts (命令注册)
    ↓
commandHandler.ts (处理逻辑)
    ↓
insightorService.ts (调用 CLI)
    ↓
Python CLI (insightor)
    ↓
JSON 结果文件
    ↓
reviewTreeProvider.ts (解析显示)
    ↓
侧边栏树视图 + Webview 详情
```

## 构建流程

```
TypeScript 源码 (src/)
    ↓
tsc 编译
    ↓
JavaScript 输出 (out/)
    ↓
vsce 打包
    ↓
VSIX 安装包
```
