#!/bin/bash
# WeWrite 一键安装脚本

set -e

echo "=========================================="
echo "  WeWrite - AI 知识库助手 安装脚本"
echo "=========================================="

# 检查 Python 版本
echo "检查 Python 版本..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python 版本: $python_version"

# 创建虚拟环境
echo "创建虚拟环境..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "虚拟环境创建成功"
else
    echo "虚拟环境已存在"
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 安装依赖
echo "安装依赖..."
pip install -r requirements.txt

# 创建必要的目录
echo "创建目录结构..."
mkdir -p knowledge/raw
mkdir -p knowledge/articles
mkdir -p knowledge/wechat
mkdir -p logs

# 复制环境变量文件
if [ ! -f ".env" ]; then
    echo "创建 .env 文件..."
    cp .env.example .env
    echo ""
    echo "=========================================="
    echo "  请编辑 .env 文件，填入你的 API Key"
    echo "=========================================="
    echo ""
    echo "必需的环境变量："
    echo "  - DEEPSEEK_API_KEY (或其他 LLM 提供商的 Key)"
    echo ""
    echo "可选的环境变量："
    echo "  - GITHUB_TOKEN (提高 API 限额)"
    echo "  - WECHAT_APP_ID (微信公众号发布)"
    echo "  - WECHAT_APP_SECRET (微信公众号发布)"
    echo ""
else
    echo ".env 文件已存在"
fi

echo "=========================================="
echo "  安装完成！"
echo "=========================================="
echo ""
echo "下一步："
echo "  1. 编辑 .env 文件，填入你的 API Key"
echo "  2. 运行 ./start.sh 启动程序"
echo ""
