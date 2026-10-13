#!/bin/bash
# 假屏保一键启动器
# 用法:
#   双击本文件,或终端运行:
#     ./启动假屏保.command              # 时钟屏保
#     ./启动假屏保.command 图片路径      # 显示指定图片
# 退出: 动一下鼠标 / 按任意键

cd "$(dirname "$0")"

PY="$(command -v python3)"

if [ -z "$PY" ]; then
    echo "找不到 python3,请先安装 Python。" >&2
    read -r -p "按回车退出..."
    exit 1
fi

exec "$PY" fakesaver.py "$@"
