#!/usr/bin/env bash
# 快捷运行脚本，自动激活虚拟环境
# 用法：./run.sh demo_01_login.py
#       ./run.sh demo_07_camera.py photo

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$SCRIPT_DIR/.venv"

# 首次运行时自动建虚拟环境并装依赖
if [ ! -f "$VENV/bin/python3" ]; then
    echo "[*] 初始化虚拟环境..."
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install -q -r "$SCRIPT_DIR/requirements.txt"
    echo "[✓] 虚拟环境就绪"
fi

if [ -z "$1" ]; then
    echo "用法: ./run.sh <demo文件名> [参数]"
    echo ""
    echo "可用 demo："
    ls "$SCRIPT_DIR"/demo_*.py | xargs -n1 basename
    exit 0
fi

exec "$VENV/bin/python3" "$SCRIPT_DIR/$@"
