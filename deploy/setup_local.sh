#!/bin/bash
# =============================================================================
# Insightor 本地开发 Setup (Windows Git Bash / Linux / macOS)
# 跳过 systemd、useradd 等生产环境步骤，直接跑服务
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

CONDA_ENV="Insightor"
SERVICE_PORT=8000

echo "=== Insightor 本地开发 Setup ==="
echo "项目目录: $PROJECT_DIR"

# ---------- 1. 检查/创建 conda 环境 ----------
echo "[1/4] 检查 conda 环境..."
if conda env list | grep -q "^${CONDA_ENV} "; then
    echo "  conda 环境 '${CONDA_ENV}' 已存在"
else
    echo "  创建 conda 环境: ${CONDA_ENV} (Python 3.12)..."
    conda create -n "$CONDA_ENV" python=3.12 -y
fi

# ---------- 2. 安装 Python 依赖 ----------
echo "[2/4] 安装 Python 依赖..."
cd "$PROJECT_DIR"

# 找 conda 环境的 pip
CONDA_PYTHON="$(conda run -n "$CONDA_ENV" python -c "import sys; print(sys.executable)" 2>/dev/null || echo "")"
if [ -z "$CONDA_PYTHON" ]; then
    CONDA_PREFIX="$(conda info --base)/envs/${CONDA_ENV}"
else
    CONDA_PREFIX="$(dirname "$(dirname "$CONDA_PYTHON")")"
fi
PIP="${CONDA_PREFIX}/bin/pip"

# Windows 兼容：bin/pip 不存在时用 Scripts/pip
if [ ! -f "$PIP" ]; then
    PIP="${CONDA_PREFIX}/Scripts/pip.exe"
fi

"$PIP" install --upgrade pip -q
"$PIP" install -e ".[web]" -q
echo "  依赖安装完成"

# ---------- 3. 构建前端（如未构建） ----------
echo "[3/4] 构建前端..."
cd "$PROJECT_DIR/web/frontend"
if [ ! -f "dist/index.html" ]; then
    npm install --production
    npm run build
    echo "  前端构建完成"
else
    echo "  前端已构建，跳过"
fi

# ---------- 4. 初始化数据库 ----------
echo "[4/4] 初始化数据库..."
cd "$PROJECT_DIR"
"${CONDA_PREFIX}/bin/python" -m web.backend.seed 2>/dev/null || \
    "${CONDA_PREFIX}/Scripts/python.exe" -m web.backend.seed
echo "  数据库初始化完成"

# ---------- 启动 ----------
echo ""
echo "=== Setup 完成 ==="
echo ""
echo "启动服务 (在当前终端前台运行):"
echo ""
echo "  后端:"
echo "  cd $PROJECT_DIR"
echo "  conda activate $CONDA_ENV"
echo "  uvicorn web.backend.app:app --reload --host 0.0.0.0 --port ${SERVICE_PORT}"
echo ""
echo "  前端 (可选，后端已托管静态文件):"
echo "  cd $PROJECT_DIR/web/frontend"
echo "  npm run dev"
echo ""
echo "  然后打开: http://localhost:${SERVICE_PORT}/"
echo ""
echo "  默认管理员: admin / admin123"
echo ""
read -r -p "是否现在启动后端服务？[Y/n] " REPLY
if [[ ! "$REPLY" =~ ^[Nn] ]]; then
    echo "启动后端..."
    cd "$PROJECT_DIR"
    "${CONDA_PREFIX}/bin/uvicorn" web.backend.app:app --reload --host 127.0.0.1 --port ${SERVICE_PORT}
fi
