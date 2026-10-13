#!/bin/bash
# 安装 fakesaver 闲置自启服务(launchd)
# 用法: ./install.sh [闲置秒数,默认 180]
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
PY="$(command -v python3)"
IDLE="${1:-180}"

if [ -z "$PY" ]; then
    echo "错误: 未找到 python3" >&2
    exit 1
fi

# 检查 Pillow 和 tkinter
if ! "$PY" -c "import PIL, tkinter" 2>/dev/null; then
    echo "错误: 当前 python3 ($PY) 缺少 Pillow 或 tkinter" >&2
    echo "请先安装: $PY -m pip install Pillow" >&2
    exit 1
fi

PLIST=~/Library/LaunchAgents/com.local.fakesaver.plist
mkdir -p ~/Library/LaunchAgents
sed -e "s|__PYTHON__|$PY|g" \
    -e "s|__DIR__|$DIR|g" \
    -e "s|<string>180</string>|<string>$IDLE</string>|" \
    "$DIR/com.local.fakesaver.plist.template" > "$PLIST"

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"

echo "✅ 已安装并启动: 键鼠闲置 ${IDLE}s 后自动进入假屏保"
echo "   停用: launchctl unload $PLIST"
echo "   卸载: ./uninstall.sh"
