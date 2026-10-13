#!/bin/bash
# 卸载 fakesaver 闲置自启服务
PLIST=~/Library/LaunchAgents/com.local.fakesaver.plist
launchctl unload "$PLIST" 2>/dev/null || true
rm -f "$PLIST"
echo "✅ 已卸载 com.local.fakesaver"
