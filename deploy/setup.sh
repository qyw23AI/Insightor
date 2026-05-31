#!/bin/bash
# =============================================================================
# Insightor 远程部署脚本 (conda + systemd)
# 在云主机上以 root 权限执行: bash setup.sh
#
# 注意: API Key / GitHub Token 由用户在 Web 控制台配置后存入数据库，
#       不需要 .env 文件。LLM 调用时从数据库读取后注入环境变量。
# =============================================================================

set -euo pipefail

# ========================= 配置 (按需修改) =========================
APP_USER="insightor"
APP_DIR="/home/${APP_USER}/Insightor"
CONDA_DIR="/home/${APP_USER}/miniconda3"
CONDA_ENV="insightor"
PYTHON_VERSION="3.12"
REPO_URL="https://github.com/SCU-GuGuGaGa/Insightor.git"
BRANCH="main"
SERVICE_PORT=8000
# ==================================================================

echo "=== Insightor 生产部署 (conda) ==="

# ---------- 1. 创建用户 ----------
if ! id -u "$APP_USER" &>/dev/null; then
    echo "[1/8] 创建用户: $APP_USER"
    useradd --create-home --shell /bin/bash "$APP_USER"
else
    echo "[1/8] 用户 $APP_USER 已存在"
fi

# ---------- 2. 安装系统依赖 ----------
echo "[2/8] 安装系统依赖..."
apt-get update -qq
apt-get install -y -qq curl git nodejs npm 2>/dev/null || \
apt-get install -y -qq curl git nodejs npm

# ---------- 3. 安装 Miniconda (如果未安装) ----------
if [ -x "${CONDA_DIR}/bin/conda" ]; then
    echo "[3/8] Miniconda 已安装: ${CONDA_DIR}"
else
    echo "[3/8] 安装 Miniconda..."
    INSTALLER="/tmp/miniconda.sh"
    curl -fsSLo "$INSTALLER" https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
    bash "$INSTALLER" -b -p "$CONDA_DIR"
    rm -f "$INSTALLER"
    chown -R "$APP_USER:$APP_USER" "$CONDA_DIR"
fi

# ---------- 3.5. 配置 conda (bashrc) ----------
echo "[3.5/8] 配置 conda bashrc..."
BASHRC_USER="/home/${APP_USER}/.bashrc"
BASHRC_ROOT="/root/.bashrc"
CONDA_SH="${CONDA_DIR}/etc/profile.d/conda.sh"

for BASHRC in "$BASHRC_USER" "$BASHRC_ROOT"; do
    if [ -f "$BASHRC" ]; then
        sed -i '/# >>> conda initialize >>>/,/# <<< conda initialize <<</d' "$BASHRC"
    fi
    {
        echo ""
        echo "# >>> conda initialize >>>"
        echo "export PATH=\"${CONDA_DIR}/bin:\$PATH\""
        echo "if [ -f \"${CONDA_SH}\" ]; then"
        echo "    . \"${CONDA_SH}\""
        echo "fi"
        echo "# <<< conda initialize <<<"
    } >> "$BASHRC"
done

chown "$APP_USER:$APP_USER" "$BASHRC_USER"

"${CONDA_DIR}/bin/conda" config --system --set auto_activate_base false

# ---------- 4. 创建 conda 环境 ----------
echo "[4/8] 创建 conda 环境: ${CONDA_ENV} (Python ${PYTHON_VERSION})..."
if "${CONDA_DIR}/bin/conda" env list | grep -q "^${CONDA_ENV} "; then
    echo "  环境已存在，跳过创建"
else
    "${CONDA_DIR}/bin/conda" create -n "$CONDA_ENV" python="$PYTHON_VERSION" -y
fi

# ---------- 5. 拉取代码 ----------
if [ -d "$APP_DIR/.git" ]; then
    echo "[5/8] 代码已存在, 执行 git pull..."
    cd "$APP_DIR"
    # git fetch origin
    # git checkout "$BRANCH"
    # git reset --hard "origin/$BRANCH"
else
    echo "[5/8] 克隆仓库..."
    git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
fi

# ---------- 6. 安装 Python 依赖 ----------
echo "[6/8] 安装 Python 依赖..."
cd "$APP_DIR"
"${CONDA_DIR}/envs/${CONDA_ENV}/bin/pip" install --upgrade pip
"${CONDA_DIR}/envs/${CONDA_ENV}/bin/pip" install -e ".[web]"

# ---------- 7. 构建前端 + 初始化数据库 ----------
echo "[7/8] 构建前端 & 初始化数据库..."
cd "$APP_DIR/web/frontend"
npm install
npm run build
npm prune --omit=dev

cd "$APP_DIR"
"${CONDA_DIR}/envs/${CONDA_ENV}/bin/python" -m web.backend.seed

# ---------- 8. 安装 systemd 服务 ----------
echo "[8/8] 安装 systemd 服务..."
# 将服务文件中的路径替换为实际路径
sed -e "s|/home/insightor|/home/${APP_USER}|g" \
    "$APP_DIR/deploy/insightor-api.service" > /etc/systemd/system/insightor-api.service

chown -R "$APP_USER:$APP_USER" "$APP_DIR"

systemctl daemon-reload
systemctl enable insightor-api
if systemctl is-active --quiet insightor-api; then
    systemctl restart insightor-api
else
    systemctl start insightor-api
fi

# ---------- 检查状态 ----------
echo ""
echo "=== 部署完成 ==="
systemctl status insightor-api --no-pager || true
echo ""
echo "访问地址: http://$(hostname -I | awk '{print $1}'):${SERVICE_PORT}/"
echo "健康检查: curl http://localhost:${SERVICE_PORT}/api/health"
echo "查看日志: journalctl -u insightor-api -f"
echo ""
echo "默认管理员账户: admin / admin123"
echo "⚠  登录后在 Web 控制台配置你的 API Key 和 GitHub Token!"
