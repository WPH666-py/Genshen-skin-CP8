# -*- coding: utf-8 -*-
"""
原神 CP 壁纸套件 8 —— 可视化切换器
用法: genshen-cp8 switcher   (或 python -m genshen_skin_cp8.switcher)

功能:
  * 左侧实时预览当前样式
  * 右侧单选切换 + 一键应用到桌面
  * 随机来一张 / 每 30 分钟自动随机
  * 一键启动桌面桌宠
"""
import os
import random
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk

from ..characters import cp8_pair as C
from . import gui_launch
from . import skin_core as sc

PREVIEW_SIZE = (1280, 720)
AUTO_INTERVAL = 30 * 60  # 秒
THEME_BG = "#eef4fb"
THEME_ACCENT = "#1c4e9c"


class App:
    def __init__(self, root):
        import PIL.Image
        import PIL.ImageTk
        self.PIL = PIL
        self.root = root
        root.title("%s · 壁纸切换器" % C.APP_NAME)
        root.configure(bg=THEME_BG)
        root.geometry("1000x500")
        root.resizable(False, False)

        self.canvas = tk.Label(root, bg="#dde7f4", bd=1, relief="solid")
        self.canvas.pack(side="left", padx=14, pady=14)

        right = ttk.Frame(root)
        right.pack(side="left", fill="y", padx=(6, 14), pady=14)
        ttk.Label(right, text="选择壁纸样式", font=("", 11, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 8))

        self.var = tk.StringVar(value=sc.DEFAULT_MODE)
        for i, (key, label) in enumerate(sc.MODES):
            ttk.Radiobutton(right, text="%s  (%s)" % (label, key), value=key,
                            variable=self.var, command=self.show_preview).grid(
                row=1 + i, column=0, sticky="w", pady=2)

        row = 1 + len(sc.MODES)
        ttk.Button(right, text="应用到桌面", command=lambda: self.apply(self.var.get())).grid(
            row=row, column=0, sticky="ew", pady=(14, 4))
        ttk.Button(right, text="随机来一张",
                   command=lambda: self.apply(sc.pick_random())).grid(
            row=row + 1, column=0, sticky="ew", pady=4)
        self.auto = tk.BooleanVar(value=False)
        ttk.Checkbutton(right, text="每 30 分钟自动随机", variable=self.auto).grid(
            row=row + 2, column=0, sticky="w", pady=4)
        ttk.Button(right, text="启动桌面桌宠",
                   command=lambda: gui_launch.launch("pet.py")).grid(
            row=row + 3, column=0, sticky="ew", pady=(10, 0))
        ttk.Button(right, text="打开壁纸目录", command=self.open_dir).grid(
            row=row + 4, column=0, sticky="ew", pady=4)

        self.size_text = ttk.Label(right, text="", foreground="#5a6b80")
        self.size_text.grid(row=row + 5, column=0, sticky="w", pady=(10, 0))
        self.status = ttk.Label(right, text="就绪", foreground=THEME_ACCENT)
        self.status.grid(row=row + 6, column=0, sticky="w", pady=(6, 0))

        sw, sh = sc.screen_size()
        self.size_text.configure(text="目标分辨率: %dx%d" % (sw, sh))

        self.last_auto = time.time()
        self.root.after(60000, self._tick)
        self.show_preview()

    # ------------------------------------------------------------ 行为
    def _tick(self):
        if self.auto.get() and time.time() - self.last_auto >= AUTO_INTERVAL:
            self.last_auto = time.time()
            self.apply(sc.pick_random())
        self.root.after(60000, self._tick)

    def show_preview(self, *_):
        mode = self.var.get()
        try:
            img = sc.compose(mode, PREVIEW_SIZE)
            tmp = os.path.join(sc.APP_DIR, "preview-%s.png" % mode)
            sc.ensure_dirs()
            img.save(tmp)
            ph = self.PIL.ImageTk.PhotoImage(self.PIL.Image.open(tmp))
            self.canvas.configure(image=ph)
            self.canvas.image = ph  # 防止被 GC
            self.status.configure(text="预览: %s" % sc.mode_label(mode))
        except Exception as e:
            self.status.configure(text="预览失败: %s" % e)

    def apply(self, mode):
        def work():
            try:
                out = sc.build(mode, force=True)
                sc.set_wallpaper(out)
                self.root.after(0, lambda: self.status.configure(
                    text="已应用: %s" % sc.mode_label(mode)))
            except Exception as e:
                self.root.after(0, lambda: self.status.configure(text="应用失败: %s" % e))
        threading.Thread(target=work, daemon=True).start()

    def open_dir(self):
        sc.ensure_dirs()
        path = sc.WALLPAPER_DIR
        try:
            if os.name == "nt":
                os.startfile(path)  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            self.status.configure(text="打开失败: %s" % e)


def main():
    sc.prepare_console()
    sc.ensure_pillow()
    sc.ensure_dirs()
    try:
        root = tk.Tk()
    except tk.TclError as e:
        print("[%s] 无法打开图形界面(远程/无桌面会话?): %s" % (C.APP_SLUG, e))
        print("请在本地图形桌面运行: %s switcher" % C.APP_SLUG)
        return 1
    App(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
