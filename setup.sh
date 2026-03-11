#!/bin/bash

echo "=== 开始安装 PodScribe ==="
echo ""

# 创建虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
else
    echo "虚拟环境已存在，跳过创建。"
fi

# 激活虚拟环境
source venv/bin/activate

# 升级 pip（避免旧版本不支持 pyproject.toml）
echo "升级 pip..."
pip install --upgrade pip -q

# 安装项目（开发模式）
echo "安装依赖..."
pip install -e . -q

echo ""
echo "=== 安装完成 ==="
echo ""
echo "使用方法："
echo "  1. 激活虚拟环境：source venv/bin/activate"
echo "  2. 运行：podscribe"
echo "  首次运行会引导你配置 API Key。"
echo ""
