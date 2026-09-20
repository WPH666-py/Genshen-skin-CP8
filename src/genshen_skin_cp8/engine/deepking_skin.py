# -*- coding: utf-8 -*-
"""
原神CP8 · 胡桃×芙宁娜 —— DeepKing 皮肤(手工校色版)

DeepKing 支持两种接入方式:

  A. 在「设置 → 界面皮肤」粘贴本仓库地址 —— DeepKing 抓 skin.json + CSS 变量,
     按内置规则自动推导 32 槽位调色板。这条路的「亮色」精确取自
     src/client/genshen-cp8.module.css, 「暗色」由其内置算法从亮色派生。

  B. 直接用本文件: 下面两套调色板是**逐槽位手工校色**的结果, 不经过任何推导,
     夜景保留插画的深靛墨黑, 而不是派生算法给出的中性灰。

安装器(genshen-cp8 deepking)会把本调色板写成 genshen-cp8.skin.json,
并生成可视化预览 genshen-cp8-preview.html, 方便导入前先看效果。
"""
from ..characters import cp8_pair as C

SKIN_ID = C.DEEPKING_SKIN_ID
SKIN_NAME = C.DEEPKING_SKIN_NAME
SKIN_DESC = C.DEEPKING_SKIN_DESC

# ─────────────────────────────────────────────── 亮色 · 暖阳米白(夕照亮部)
LIGHT = {
    "bg": "#fdf8f3",
    "bgText": "#2a1c1a",
    "sidebarBg": "#f7ece7",
    "sidebarText": "#33231f",
    "sidebarHover": "#f6e2dd",
    "sidebarSelected": "#ecc9c1",
    "sidebarHeader": "#8d7370",
    "editorBg": "#fdf8f3",
    "tabsBg": "#fbf2ed",
    "tabBg": "#f5e7e1",
    "tabText": "#6b514c",
    "tabActiveBg": "#fdf8f3",
    "tabActiveText": "#2a1c1a",
    "aiBg": "#fcf5f1",
    "aiText": "#2a1c1a",
    "aiTabText": "#6b514c",
    "userBubbleBg": "#f0d3cc",
    "userBubbleText": "#2a1c1a",
    "aiBubbleBg": "#fdf8f3",
    "aiBubbleText": "#2a1c1a",
    "aiBubbleBorder": "#dcc2b9",
    "systemBubbleBg": "#fff4dd",
    "systemBubbleText": "#8a5a00",
    "inputBg": "#fdf8f3",
    "inputText": "#2a1c1a",
    "inputBorder": "#c9a79c",
    "accent": "#c8433a",
    "accentText": "#ffffff",
    "border": "#dcc2b9",
    "chipBg": "#f2ddd7",
    "chipText": "#8a2a24",
    "chipBorder": "#c9a79c",
}

# ─────────────────────────────────────────────── 夜景 · 深靛墨黑(夜海)
DARK = {
    "bg": "#141b2b",
    "bgText": "#e7edf7",
    "sidebarBg": "#1d2740",
    "sidebarText": "#c3cee1",
    "sidebarHover": "#283453",
    "sidebarSelected": "#36456b",
    "sidebarHeader": "#7f8fa8",
    "editorBg": "#141b2b",
    "tabsBg": "#182034",
    "tabBg": "#1d2740",
    "tabText": "#8b9bb4",
    "tabActiveBg": "#283453",
    "tabActiveText": "#e7edf7",
    "aiBg": "#1d2740",
    "aiText": "#e7edf7",
    "aiTabText": "#8b9bb4",
    "userBubbleBg": "#5c2a34",
    "userBubbleText": "#f6eef1",
    "aiBubbleBg": "#212c47",
    "aiBubbleText": "#e7edf7",
    "aiBubbleBorder": "#3b4b70",
    "systemBubbleBg": "#3a2f14",
    "systemBubbleText": "#ecd39a",
    "inputBg": "#1f2942",
    "inputText": "#e7edf7",
    "inputBorder": "#3b4b70",
    "accent": "#e2604f",
    "accentText": "#160d0c",
    "border": "#3b4b70",
    "chipBg": "#2e3a5c",
    "chipText": "#d6e2f4",
    "chipBorder": "#5a6f9e",
}

PALETTE_SLOTS = (
    "bg", "bgText", "sidebarBg", "sidebarText", "sidebarHover", "sidebarSelected",
    "sidebarHeader", "editorBg", "tabsBg", "tabBg", "tabText", "tabActiveBg",
    "tabActiveText", "aiBg", "aiText", "aiTabText", "userBubbleBg", "userBubbleText",
    "aiBubbleBg", "aiBubbleText", "aiBubbleBorder", "systemBubbleBg", "systemBubbleText",
    "inputBg", "inputText", "inputBorder", "accent", "accentText", "border",
    "chipBg", "chipText", "chipBorder",
)


def definition(mascot_light=None, mascot_dark=None, source=None):
    """返回完整的 DeepKing SkinDefinition(手工校色版)。"""
    skin = {
        "id": SKIN_ID,
        "name": SKIN_NAME,
        "builtin": False,
        "description": SKIN_DESC,
        "palettes": {"light": dict(LIGHT), "dark": dict(DARK)},
    }
    if source:
        skin["source"] = source
    if mascot_light or mascot_dark:
        skin["mascot"] = {
            "light": mascot_light or mascot_dark,
            "dark": mascot_dark or mascot_light,
        }
    return skin


def validate():
    """自检: 槽位齐全、色值合法、亮暗确实一浅一深、文字对比度够。"""
    from . import _color as col

    problems = []
    for label, pa in (("light", LIGHT), ("dark", DARK)):
        missing = [k for k in PALETTE_SLOTS if k not in pa]
        extra = [k for k in pa if k not in PALETTE_SLOTS]
        if missing:
            problems.append("%s 缺少槽位: %s" % (label, ", ".join(missing)))
        if extra:
            problems.append("%s 多余槽位: %s" % (label, ", ".join(extra)))
        for k, v in pa.items():
            if not col.is_hex(v):
                problems.append("%s.%s 不是合法 # 十六进制: %r" % (label, k, v))
    if not col.is_light_color(LIGHT["bg"]):
        problems.append("light.bg 不是浅色: %s" % LIGHT["bg"])
    if col.is_light_color(DARK["bg"]):
        problems.append("dark.bg 不是深色: %s" % DARK["bg"])
    for label, pa in (("light", LIGHT), ("dark", DARK)):
        for fg, bg in (("bgText", "bg"), ("sidebarText", "sidebarBg"),
                       ("aiBubbleText", "aiBubbleBg"), ("tabText", "tabsBg")):
            lf = sum(col.to_rgb(pa[fg])) / 3.0
            lb = sum(col.to_rgb(pa[bg])) / 3.0
            if abs(lf - lb) < 60:
                problems.append("%s: %s 与 %s 亮度太接近(%d), 文字可能看不清"
                                % (label, fg, bg, abs(lf - lb)))
    return problems
