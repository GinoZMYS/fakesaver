#!/usr/bin/env python3
"""
fakesaver.py — 终端一键启动的"假屏幕保护程序"(多屏版)

用法:
    python3 fakesaver.py [图片路径]

行为:
    - 自动检测所有显示器,每块屏幕都盖上全黑窗口(图片/时钟分别适配各自分辨率)
    - 置顶显示,隐藏鼠标指针
    - 传入图片时:图片等比缩放铺满每块屏幕(黑边填充)
    - 不传图片时:每块屏幕显示居中时钟
    - 移动鼠标或按任意键,所有屏幕一起退出(和真屏保一致)
"""

import os
import sys

# 后备 Python 解释器(Tk 版本与 macOS 匹配时使用)。
# 默认从环境变量 FAKESAVER_MANAGED_PY 读取;为空则不切换,直接使用当前解释器。
# 系统 Python 的 Tk 在部分 macOS 版本上直接 abort 崩溃(触发"Python 意外退出"
# 弹窗),且系统 Python 往往没装 PIL,此时可设置该变量自动切换到正常解释器。
MANAGED_PY = os.environ.get("FAKESAVER_MANAGED_PY", "")

# 引导切换必须放在 tkinter / PIL 导入之前。
if not os.environ.get("FAKESAVER_TK_CHECKED") and os.path.exists(MANAGED_PY) \
        and os.path.realpath(MANAGED_PY) != os.path.realpath(sys.executable):
    os.environ["FAKESAVER_TK_CHECKED"] = "1"
    os.execv(MANAGED_PY, [MANAGED_PY, os.path.abspath(__file__)] + sys.argv[1:])

import ctypes
import time
import tkinter as tk
from pathlib import Path

from PIL import Image, ImageTk

# 鼠标移动超过该像素阈值才退出(避免传感器微小抖动误触发)
MOVE_THRESHOLD = 15


def get_displays():
    """通过 macOS CoreGraphics 枚举所有显示器,返回 [(x, y, w, h), ...]。
    失败时返回 None,退化为只盖主屏。"""
    try:
        cg = ctypes.cdll.LoadLibrary(
            "/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")

        class CGRect(ctypes.Structure):
            _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double),
                        ("w", ctypes.c_double), ("h", ctypes.c_double)]

        arr = (ctypes.c_uint32 * 16)()
        cnt = ctypes.c_uint32(0)
        if cg.CGGetActiveDisplayList(16, arr, ctypes.byref(cnt)) != 0 or cnt.value == 0:
            return None
        cg.CGDisplayBounds.restype = CGRect
        cg.CGDisplayBounds.argtypes = [ctypes.c_uint32]
        return [
            tuple(int(v) for v in (b.x, b.y, b.w, b.h))
            for b in (cg.CGDisplayBounds(arr[i]) for i in range(cnt.value))
        ]
    except Exception:
        return None


class FakeSaver:
    def __init__(self, image_path=None):
        self.root = tk.Tk()
        self.root.configure(bg="black")

        displays = get_displays() or [
            (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())]
        print(f"[fakesaver] 检测到 {len(displays)} 块屏幕,全部覆盖")

        self.image_path = Path(image_path) if image_path else None
        self._photos = []  # 防止 PhotoImage 被 GC
        self._canvases = []

        # 主屏:root 用原生 fullscreen(可遮住菜单栏)
        self._cover(self.root, displays[0], primary=True)
        # 其余屏幕:Toplevel 先移到目标显示器再全屏
        for geo in displays[1:]:
            top = tk.Toplevel(self.root)
            top.configure(bg="black")
            self._cover(top, geo, primary=False)

        self._start_pos = None
        for w in [self.root] + self.root.winfo_children():
            for seq, cb in (("<Key>", lambda e: self.quit()),
                            ("<Button>", lambda e: self.quit()),
                            ("<Motion>", self._on_motion)):
                w.bind(seq, cb)

        if self.image_path is None:
            self._tick()

    def _cover(self, win, geo, primary):
        x, y, w, h = geo
        if not primary:
            # 先移动到对应显示器区域,再全屏——macOS 会把该窗口
            # 在它所在的显示器上创建独立全屏 Space
            win.geometry(f"{w}x{h}+{x}+{y}")
            win.update_idletasks()
        win.attributes("-fullscreen", True)
        win.attributes("-topmost", True)
        try:
            win.config(cursor="none")  # macOS 上若不支持则忽略
        except tk.TclError:
            pass

        canvas = tk.Canvas(win, width=w, height=h, bg="black",
                           highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        self._canvases.append((canvas, w, h))

        if self.image_path:
            self._paint_image(canvas, w, h)

    def _paint_image(self, canvas, w, h):
        if not self.image_path.exists():
            print(f"[fakesaver] 图片不存在: {self.image_path},改为显示时钟",
                  file=sys.stderr)
            self.image_path = None
            self._tick()
            return
        img = Image.open(self.image_path).convert("RGB")
        img.thumbnail((w, h), Image.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        self._photos.append(photo)
        canvas.create_image(w // 2, h // 2, image=photo, anchor="center")

    def _tick(self):
        """时钟模式:每秒在每块屏幕上刷新。"""
        now = time.strftime("%H:%M:%S")
        date = time.strftime("%Y-%m-%d  %A")
        for canvas, w, h in self._canvases:
            canvas.delete("clock")
            canvas.create_text(w // 2, h // 2 - 40, text=now, fill="#e8e8e8",
                               font=("Helvetica Neue", 96, "bold"), tags="clock")
            canvas.create_text(w // 2, h // 2 + 50, text=date, fill="#888888",
                               font=("Helvetica Neue", 24), tags="clock")
        self.root.after(1000, self._tick)

    def _on_motion(self, event):
        if self._start_pos is None:
            self._start_pos = (event.x, event.y)
            return
        dx = abs(event.x - self._start_pos[0])
        dy = abs(event.y - self._start_pos[1])
        if dx > MOVE_THRESHOLD or dy > MOVE_THRESHOLD:
            self.quit()

    def quit(self):
        self.root.destroy()  # 销毁 root 会连带销毁所有 Toplevel

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    FakeSaver(sys.argv[1] if len(sys.argv) > 1 else None).run()
