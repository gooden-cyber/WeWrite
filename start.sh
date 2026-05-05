#!/bin/bash
# WeWrite 启动脚本

set -e

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印带颜色的消息
info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 检查 Python 版本
check_python_version() {
    local python_cmd=$1
    local version
    version=$($python_cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    local major
    major=$(echo "$version" | cut -d. -f1)
    local minor
    minor=$(echo "$version" | cut -d. -f2)

    if [ "$major" -lt 3 ] || ([ "$major" -eq 3 ] && [ "$minor" -lt 12 ]); then
        return 1
    fi
    return 0
}

# 查找合适的 Python 命令
find_python() {
    # 优先使用虚拟环境（已存在则跳过创建）
    if [ -d "venv" ] && [ -f "venv/bin/python" ]; then
        source venv/bin/activate
        PYTHON="python"
        if check_python_version "$PYTHON"; then
            return 0
        fi
        deactivate 2>/dev/null || true
    fi

    # 尝试 python3.13, python3.12, python3
    for cmd in python3.13 python3.12 python3; do
        if command -v "$cmd" &>/dev/null; then
            if check_python_version "$cmd"; then
                PYTHON="$cmd"
                return 0
            fi
        fi
    done

    return 1
}

# 检查并安装依赖（仅在需要时）
check_dependencies() {
    local python_cmd=$1

    # 如果没有虚拟环境，自动创建
    if [ ! -d "venv" ]; then
        info "首次运行，创建虚拟环境..."
        create_venv "$python_cmd"
        return 0
    fi

    # 快速检查：只检查核心依赖是否可导入
    if $python_cmd -c "import httpx, yaml, dotenv, fastapi, uvicorn, jinja2" 2>/dev/null; then
        return 0
    fi

    # 有缺失依赖才安装
    warn "缺少依赖，正在安装..."
    $python_cmd -m pip install -r requirements.txt -q --disable-pip-version-check 2>/dev/null
    if [ $? -eq 0 ]; then
        info "依赖安装完成"
    else
        error "依赖安装失败，请手动运行: pip install -r requirements.txt"
        exit 1
    fi
}

# 创建虚拟环境
create_venv() {
    local python_cmd=$1
    info "创建虚拟环境..."
    $python_cmd -m venv venv
    source venv/bin/activate
    PYTHON="python"
    info "安装依赖..."
    python -m pip install --upgrade pip -q --disable-pip-version-check
    pip install -r requirements.txt -q --disable-pip-version-check
    info "虚拟环境创建完成"
}

# 解析参数
MODE="${1:-once}"

# 查找 Python
if ! find_python; then
    error "未找到 Python >= 3.12"
    echo ""
    echo "请安装 Python 3.12 或更高版本:"
    echo "  macOS:   brew install python@3.12"
    echo "  Ubuntu:  sudo apt install python3.12"
    echo "  或访问:  https://www.python.org/downloads/"
    exit 1
fi

info "使用 Python: $PYTHON ($($PYTHON --version 2>&1))"

# 创建必要的目录
mkdir -p knowledge/raw knowledge/articles knowledge/wechat logs

# install 模式
if [ "$MODE" = "install" ]; then
    echo "=========================================="
    echo "  WeWrite - 安装依赖"
    echo "=========================================="
    create_venv "$PYTHON"
    info "安装完成！现在可以运行: ./start.sh web"
    exit 0
fi

# 检查依赖
check_dependencies "$PYTHON"

case "$MODE" in
    once)
        echo "=========================================="
        echo "  WeWrite - 运行一次流水线"
        echo "=========================================="
        $PYTHON pipeline/pipeline.py "${@:2}"
        ;;
    schedule)
        echo "=========================================="
        echo "  WeWrite - 启动定时调度"
        echo "=========================================="
        $PYTHON scripts/scheduler.py "${@:2}"
        ;;
    test)
        echo "=========================================="
        echo "  WeWrite - 测试模式"
        echo "=========================================="
        $PYTHON scripts/scheduler.py --test "${@:2}"
        ;;
    web)
        echo "=========================================="
        echo "  WeWrite - 启动 Web 服务"
        echo "=========================================="
        echo ""
        info "访问 http://localhost:8000"
        info "按 Ctrl+C 停止"
        echo ""
        $PYTHON web/app.py "${@:2}"
        ;;
    publish)
        echo "=========================================="
        echo "  WeWrite - 发布文章"
        echo "=========================================="
        $PYTHON scripts/publish_wechat.py "${@:2}"
        ;;
    *)
        echo "用法: ./start.sh [模式]"
        echo ""
        echo "模式:"
        echo "  once      运行一次流水线（默认）"
        echo "  schedule  启动定时调度（每天自动采集）"
        echo "  test      测试模式（立即执行一次）"
        echo "  web       启动 Web UI（推荐）"
        echo "  publish   发布文章到微信公众号"
        echo "  install   创建虚拟环境并安装依赖"
        echo ""
        echo "示例:"
        echo "  ./start.sh              # 运行一次"
        echo "  ./start.sh web          # 启动 Web UI"
        echo "  ./start.sh schedule     # 启动定时调度"
        echo "  ./start.sh publish      # 发布文章"
        echo "  ./start.sh install      # 安装依赖"
        exit 1
        ;;
esac
