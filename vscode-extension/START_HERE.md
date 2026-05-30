# 🎯 Insightor VSCode 插件 - 立即开始

## 快速启动（3 步）

### 1️⃣ 安装依赖

```bash
cd vscode-extension
npm install
```

### 2️⃣ 编译代码

```bash
npm run compile
```

### 3️⃣ 启动调试

```bash
code .
# 在 VSCode 中按 F5
```

---

## 🎮 测试插件

在新打开的 VSCode 窗口中：

### 测试 1: 查看命令

```
1. 按 Ctrl+Shift+P
2. 输入 "Insightor"
3. 应该看到 5 个命令
```

### 测试 2: 运行审查

```
1. 选择 "Insightor: Describe PR"
2. 输入: https://github.com/SCU-GuGuGaGa/Insightor/pull/21
3. 选择: quick
4. 查看侧边栏结果
```

### 测试 3: 查看侧边栏

```
1. 点击活动栏的 Insightor 图标
2. 查看审查结果树
3. 点击发现跳转到代码
```

---

## 📦 打包安装

### 生成 VSIX

```bash
npm run package
```

### 安装 VSIX

```
1. VSCode → Extensions
2. 点击 ... 菜单
3. Install from VSIX
4. 选择 insightor-vscode-0.1.0.vsix
```

---

## 📚 文档导航

| 文档 | 用途 |
|------|------|
| [README.md](README.md) | 用户文档 |
| [INSTALL.md](INSTALL.md) | 安装指南 |
| [QUICKSTART_5MIN.md](QUICKSTART_5MIN.md) | 5分钟启动 |
| [DEMO.md](DEMO.md) | 演示指南 |
| [DEVELOPMENT.md](DEVELOPMENT.md) | 开发指南 |

---

## ✅ 功能清单

- ✅ **5 个命令**: Review, Describe, Risks, Full, Publish
- ✅ **侧边栏视图**: 树形结构显示结果
- ✅ **详情面板**: Webview 显示发现详情
- ✅ **代码跳转**: 点击跳转到代码位置
- ✅ **Apply Fix**: 一键应用修复建议
- ✅ **配置系统**: 5 个可配置选项

---

## 🎉 项目完成

**状态**: ✅ 开发完成，可立即使用

**包含**:
- 901 行 TypeScript 代码
- 14 个详细文档
- 5 个核心命令
- 完整的用户界面
- 灵活的配置系统

**立即开始**: 按照上面的 3 步快速启动！

---

<div align="center">

**Insightor VSCode Extension v0.1.0**

Made with ❤️

</div>
