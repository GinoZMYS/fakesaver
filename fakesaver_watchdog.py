#!/usr/bin/env python3
"""
fakesaver_watchdog.py — 假屏保看门狗

持续监测 macOS 键鼠闲置时间,闲置超过阈值(默认 180 秒)自动启动 fakesaver.py。
用户动鼠标/按键后 fakesaver 自行退出,看门狗重新待命。

用法:
    python3 fakesaver_watchdog.py [闲置秒数] [图片路径]

建议通过 launchd (com.local.fakesaver.plist) 常驻运行,开机自启。
"""

import ctypes
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SAVER = HERE / "fakesaver.py"
POLL_INTERVAL = 5  # 每 5 秒检查一次


def idle_seconds():
    """键鼠(任意输入事件)闲置秒数,读取失败返回 0(当作不闲置)。"""
    try:
        cg = ctypes.cdll.LoadLibrary(
            "/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
        cg.CGEventSourceSecondsSinceLastEventType.restype = ctypes.c_double
        cg.CGEventSourceSecondsSinceLastEventType.argtypes = [
            ctypes.c_int, ctypes.c_uint32]
        # 0 = kCGEventSourceStateCombinedSessionState, 0xFFFFFFFF = kCGAnyInputEventType
        return cg.CGEventSourceSecondsSinceLastEventType(0, 0xFFFFFFFF)
    except Exception:
        return 0.0


def saver_running():
    return subprocess.run(
        ["pgrep", "-f", "fakesaver.py"], capture_output=True
    ).returncode == 0


def main():
    threshold = float(sys.argv[1]) if len(sys.argv) > 1 else 180.0
    image = sys.argv[2] if len(sys.argv) > 2 else None
    cmd = [sys.executable, str(SAVER)] + ([image] if image else [])

    print(f"[watchdog] 闲置超过 {threshold:.0f} 秒将启动假屏保,每 {POLL_INTERVAL} 秒检查一次")
    armed = True  # 只有闲置曾回落到阈值以下才允许再次触发,避免崩溃循环刷进程
    while True:
        time.sleep(POLL_INTERVAL)
        idle = idle_seconds()
        if idle < threshold:
            armed = True
            continue
        if armed and not saver_running():
            print(f"[watchdog] 闲置 {idle:.0f}s ≥ {threshold:.0f}s,启动假屏保")
            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env={**dict(__import__("os").environ), "FAKESAVER_TK_CHECKED": "1"},
            )
            armed = False  # 等待用户活动(idle 回落)后再重新待命


if __name__ == "__main__":
    main()
