# -*- coding: utf-8 -*-
"""
原神 CP 壁纸套件 8 —— 桌面桌宠
用法: genshen-cp8 pet

功能:
  * 透明无边框置顶小立绘, 可拖动
  * 右键菜单: 切换 3 张立绘 / 随机 / 打开切换器 / 设为壁纸 / 退出
  * 自动保存位置与当前立绘
  * 左键拖动移动, Esc 退出

立绘处理: 素材是整幅插画(无干净白底), 因此采用「方形取景裁剪 + 圆角羽化」,
把两人主体框进一个独立小窗, 而不是做泛洪抠图 —— 跨平台观感稳定。
"""
import json
import math
import os
import random
import subprocess
import sys
import time
import tkinter as tk

from ..characters import cp8_pair as C
from . import gui_launch
from . import skin_core as sc

WORK_SIZE = 640        # 取景工作分辨率
DISPLAY_SIZE = 240     # 桌宠显示尺寸
MAGIC = "#010203"      # Windows 透明色键
STATE_FILE = os.path.join(sc.APP_DIR, "pet.json")
RANDOM_SECONDS = 30

# 每张素材的取景框: (中心x比例, 中心y比例, 半边长占最短边比例)
PET_CROPS = {name: meta["pet_crop"] for name, meta in C.IMAGE_META.items()}
LABELS = list(zip(sc.IMAGE_FILES, sc.IMAGE_NAMES))


def _rounded_mask(size, radius):
    from PIL import Image, ImageDraw
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, size[0] - 1, size[1] - 1], radius=radius, fill=255)
    return mask


def load_cut(name):
    """加载并缓存桌宠立绘(方形取景 + 圆角羽化), 返回 RGBA。"""
    cache = os.path.join(sc.CACHE_DIR, "pet-%s.png" % os.path.splitext(name)[0])
    from PIL import Image, ImageFilter, ImageDraw

    if os.path.exists(cache) and os.path.getmtime(cache) >= sc._source_freshness():
        return Image.open(cache).convert("RGBA")

    full = Image.open(sc.asset_path_by_name(name)).convert("RGB")
    cx, cy, half = PET_CROPS.get(name, (0.5, 0.5, 0.46))
    side = int(min(full.width, full.height) * half * 2)
    x0 = int(cx * full.width - side / 2)
    y0 = int(cy * full.height - side / 2)
    x0 = max(0, min(full.width - side, x0))
    y0 = max(0, min(full.height - side, y0))
    cut = full.crop((x0, y0, x0 + side, y0 + side)).resize(
        (WORK_SIZE, WORK_SIZE), Image.LANCZOS).convert("RGBA")

    # 圆形内切 -> 柔和圆形立绘(比硬边方形更像桌宠)
    mask = Image.new("L", (WORK_SIZE, WORK_SIZE), 0)
    ImageDraw.Draw(mask).ellipse(
        [2, 2, WORK_SIZE - 3, WORK_SIZE - 3], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(2))
    cut.putalpha(mask)
    cut.save(cache)
    return cut


class Pet:
    def __init__(self):
        from PIL import Image, ImageTk
        self.Image = Image
        self.ImageTk = ImageTk

        self.root = tk.Tk()
        self.root.title(C.APP_SLUG + "-pet")
        self.transparent = False
        try:
            self.root.overrideredirect(True)
            self.root.wm_attributes("-topmost", True)
            self.root.wm_attributes("-transparentcolor", MAGIC)
            self.transparent = True
        except tk.TclError:
            pass  # Linux 无透明色键: 退化为白底卡片

        state = self.load_state()
        w = DISPLAY_SIZE
        h = DISPLAY_SIZE + 16
        if state.get("x") is not None:
            geo = "%dx%d+%d+%d" % (w, h, state["x"], state["y"])
        else:
            sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
            geo = "%dx%d+%d+%d" % (w, h, sw - w - 80, sh - h - 140)
        self.root.geometry(geo)

        self.label = tk.Label(self.root, bg=MAGIC if self.transparent else "#ffffff", bd=0)
        self.label.place(x=0, y=0)

        # 预渲染三张立绘
        self.images = {}
        for name, _label in LABELS:
            cut = load_cut(name)
            box = Image.new("RGBA", (DISPLAY_SIZE, DISPLAY_SIZE), (0, 0, 0, 0))
            thumb = cut.copy()
            thumb.thumbnail((DISPLAY_SIZE, DISPLAY_SIZE), Image.LANCZOS)
            box.paste(thumb, ((DISPLAY_SIZE - thumb.width) // 2,
                              (DISPLAY_SIZE - thumb.height) // 2), thumb)
            if self.transparent:
                key = tuple(int(MAGIC[i:i + 2], 16) for i in (1, 3, 5)) + (255,)
            else:
                key = (255, 255, 255, 255)
            bg = Image.new("RGBA", box.size, key)
            self.images[name] = ImageTk.PhotoImage(
                Image.alpha_composite(bg, box).convert("RGB"))

        self.mode = int(state.get("mode", 0)) % len(LABELS)
        self.random_mode = bool(state.get("random", False))
        self.random_timer = time.time()

        menu = tk.Menu(self.root, tearoff=0)
        for i, (_name, label) in enumerate(LABELS):
            menu.add_command(label=label, command=lambda i=i: self.set_mode(i))
        menu.add_separator()
        menu.add_command(label="随机 30 秒", command=self.toggle_random)
        menu.add_command(label="设为壁纸", command=self.apply_wallpaper)
        menu.add_command(label="打开切换器", command=lambda: gui_launch.launch("switcher.py"))
        menu.add_separator()
        menu.add_command(label="退出", command=self.quit)
        self.menu = menu

        self.label.bind("<Button-1>", self.start_drag)
        self.label.bind("<B1-Motion>", self.on_drag)
        self.label.bind("<ButtonRelease-1>", self.end_drag)
        self.root.bind("<Button-3>", lambda e: self.menu.tk_popup(e.x_root, e.y_root))
        self.root.bind("<Escape>", lambda e: self.quit())

        self.t = 0.0
        self.drag_off = (0, 0)
        self.set_mode(self.mode, save=False)
        self.loop()

    # ------------------------------------------------------------ 状态
    def load_state(self):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_state(self):
        try:
            data = {
                "x": self.root.winfo_x(),
                "y": self.root.winfo_y(),
                "mode": self.mode,
                "random": self.random_mode,
            }
            sc.ensure_dirs()
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception:
            pass

    # ------------------------------------------------------------ 交互
    def set_mode(self, idx, save=True):
        self.mode = idx % len(LABELS)
        name = LABELS[self.mode][0]
        self.label.configure(image=self.images[name],
                             width=DISPLAY_SIZE, height=DISPLAY_SIZE)
        if save:
            self.save_state()

    def toggle_random(self):
        self.random_mode = not self.random_mode
        self.random_timer = time.time()
        self.save_state()

    def apply_wallpaper(self):
        mode = "single%d" % (self.mode + 1)
        try:
            out = sc.build(mode, force=True)
            sc.set_wallpaper(out)
        except Exception:
            pass

    def quit(self):
        self.save_state()
        self.root.destroy()

    def start_drag(self, e):
        self.drag_off = (e.x, e.y)

    def on_drag(self, e):
        x = self.root.winfo_x() + e.x - self.drag_off[0]
        y = self.root.winfo_y() + e.y - self.drag_off[1]
        self.root.geometry("+%d+%d" % (x, y))

    def end_drag(self, _e):
        self.save_state()

    # ------------------------------------------------------------ 动画
    def loop(self):
        self.t += 0.09
        bob = int((1 + math.sin(self.t * 2.0)) * 7.0)
        self.label.place(x=0, y=bob)
        if self.random_mode and time.time() - self.random_timer > RANDOM_SECONDS:
            self.random_timer = time.time()
            self.set_mode(random.randrange(len(LABELS)), save=False)
        self.root.after(40, self.loop)


def main():
    sc.prepare_console()
    sc.ensure_pillow()
    sc.ensure_dirs()
    try:
        pet = Pet()
    except tk.TclError as e:
        print("[%s] 无法打开桌宠窗口(远程/无桌面会话?): %s" % (C.APP_SLUG, e))
        return 1
    print("桌宠启动中 ... 左键拖动, 右键切换/退出, Esc 退出")
    pet.root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
