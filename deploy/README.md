# Insightor 远程部署指南 (conda + systemd)

## 前置要求

- 云主机: Ubuntu 22.04+ / Debian 12+（x86_64）
- 本地 VS Code 安装 **Remote - SSH** 插件
- 云主机开放端口 8000

---

## 一键部署

```bash
# 1. Remote SSH 连接到云主机
# 2. clone 仓库
git clone https://github.com/SCU-GuGuGaGa/Insightor.git /tmp/insightor-deploy

# 3. 执行部署脚本
sudo bash /tmp/insightor-deploy/deploy/setup.sh
```

脚本会自动完成：

- 创建 `insightor` 用户
- 安装 Miniconda + 创建 conda 环境
- 拉取代码 + 安装依赖
- 构建 React 前端
- 初始化 SQLite 数据库
- 安装并启动 systemd 服务

---

## 部署后配置

**不需要 `.env` 文件。** 所有 API Key 和 Token 在 Web 控制台中配置：

1. 浏览器打开 `http://<服务器IP>:8000/`
2. 用默认管理员账户登录: `admin` / `admin123`
3. 进入配置页面，填入你的 Key：

```text
GITHUB_TOKEN        ← GitHub Personal Access Token
DEEPSEEK_API_KEY    ← DeepSeek API Key
DEEPSEEK_API_BASE   ← 第三方 API 地址（如 https://api.deepseek.com/v1）
OPENAI_API_KEY      ← OpenAI API Key（可选）
ANTHROPIC_API_KEY   ← Anthropic API Key（可选）
```

配置加密存储在 SQLite 数据库中，每个用户独立配置。

---

## 配置流转

```text
用户登录 Web UI → 配置页面填入 API Key → 加密存入 SQLite
                                              ↓
发起分析请求 → analyze.py 从 DB 读取当前用户 Key
              → 注入 os.environ (临时)
              → ReviewPipeline 调用 LiteLLM
              → 分析完成后恢复/删除环境变量
```

---

## 常用管理命令

```bash
# 查看状态
systemctl status insightor-api

# 重启服务
systemctl restart insightor-api

# 停止服务
systemctl stop insightor-api

# 查看实时日志
journalctl -u insightor-api -f

# 代码更新后重新部署
cd /home/insightor/Insightor
git pull
/home/insightor/miniconda3/envs/insightor/bin/pip install -e ".[web]"
cd web/frontend && npm install --production && npm run build
systemctl restart insightor-api
```

---

## 开发模式

在远程主机上开发调试时，用 tmux 避免进程随 SSH 断开退出：

```bash
systemctl stop insightor-api

# 终端 1: 后端
tmux new -s backend
cd /home/insightor/Insightor
/home/insightor/miniconda3/envs/insightor/bin/uvicorn web.backend.app:app --reload --host 0.0.0.0 --port 8000
# Ctrl+B D 分离

# 终端 2: 前端
tmux new -s frontend
cd /home/insightor/Insightor/web/frontend
npm run dev -- --host 0.0.0.0
# Ctrl+B D 分离
```

---

## 一键 HTTPS（需域名）

```bash
# 1. 先部署服务
sudo bash deploy/setup.sh

# 2. 将域名 DNS 解析到服务器 IP

# 3. 一键配置 HTTPS
sudo bash deploy/setup_https.sh insightor.your-domain.com
```

即可通过 `https://insightor.your-domain.com/` 访问，HTTP 自动跳转 HTTPS，证书 90 天自动续期。

> Let's Encrypt 必须绑定域名，无法给 IP 签发证书。`.xyz` / `.top` 等域名首年只需几块钱。
