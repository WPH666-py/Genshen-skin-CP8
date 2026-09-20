# -*- coding: utf-8 -*-
"""
原神 CP 壁纸套件 8 —— DeepKing 皮肤适配层

DeepKing(设置 → 界面皮肤)支持粘贴 GitHub 仓库地址, 由其内置转换器
`src/utils/skinConverter.ts` 抓取仓库里的:

    1. `skin.json`                            名称 / 强调色 / 描述
    2. `src/client/*.module.css` 或任意 .css   配色变量 --name: #hex
    3. `assets/background/` 下的图片           编辑区右下角吉祥物

再推导出 32 槽位的 `SkinPalette`, 生成自定义皮肤。

本模块在 Python 侧**复刻同一套推导规则**, 于是可以:

  * `check()`        —— 校验本仓库是否满足转换契约(色值格式、必需变量、暗色作用域、吉祥物)
  * `convert()`      —— 本地离线跑出 DeepKing 会得到的那份 SkinDefinition
  * `preview_html()` —— 生成可视化预览, 让人在导入 DeepKing 前先看效果
  * `export_json()`  —— 落盘 SkinDefinition, 便于对比/排查

因为契约一致, DeepKing 里粘仓库地址的结果与本地 convert() 一致。
"""
import json
import os
import re

from . import _color as col
from ..characters import cp8_pair as C

SKIN_VERSION = "0.1.0"

# ---------------------------------------------------------------- 变量提取

# 与 skinConverter.ts 的 extractVars 正则等价
_VAR_RE = re.compile(r"(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{3,8})\b")
# 与 extractDarkVars 等价: 选择器里含 dark 的块
_BLOCK_RE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.S)
# CSS 注释: 必须先剥离, 否则注释里的 `{` `}` 和色值会被当成选择器与变量
_COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)


def strip_comments(css_text):
    """剥离 /* ... */ 注释。

    DeepKing 的转换器不做这一步, 但注释里的花括号会让它的块正则错位。
    我们自己写 CSS 时避开注释中的花括号即可, 这里做防御性剥离让结果可预期。
    """
    return _COMMENT_RE.sub(" ", css_text)

# DeepKing 会识别的关键词(按优先级), 缺失时其转换器会走自动派生
KEY_VARS = {
    "bg": ("bg-layer-1", "bg-base", "background", "bg-100", "neutral-50"),
    "text": ("label-primary", "ink", "text", "neutral-1000", "neutral-900"),
    "layer2": ("bg-layer-2", "bg-200", "neutral-100"),
    "layer3": ("bg-layer-3", "bg-300", "neutral-200"),
    "accent": ("brand-primary", "accent", "primary"),
    "border": ("border-l2", "border-l1", "border"),
    "hover": ("interactive-bg-hover-solid", "bg-hover"),
    "selected": ("interactive-bg-active", "bg-active"),
    "secondary": ("label-secondary", "label-tertiary", "muted"),
}


def extract_vars(css_text):
    """提取全部 --变量: #色值 定义(先剥离注释)。"""
    return {m.group(1): m.group(2).lower()
            for m in _VAR_RE.finditer(strip_comments(css_text))}


def extract_dark_vars(css_text):
    """只提取选择器中含 dark 的块内的变量(先剥离注释)。"""
    out = {}
    for m in _BLOCK_RE.finditer(strip_comments(css_text)):
        selector = m.group(1)
        if "dark" in selector.lower():
            out.update(extract_vars(m.group(2)))
    return out


def _pick(vars_map, key):
    """按关键词优先级从变量表里取值; 匹配「变量名包含关键词」。"""
    for kw in KEY_VARS.get(key, ()):
        for name, value in vars_map.items():
            if kw in name.lower():
                return value
    return None


# ---------------------------------------------------------------- 仓库定位

def repo_root():
    """本套件的**仓库根目录**; pip 安装形态返回 None。

    注意区别: 包内也有一份 skin.json(供 pip 形态读取元信息), 但那不是仓库根。
    仓库根的判据是「skin.json + src/client 目录」同时存在 —— 后者是放
    DeepKing 配色 CSS 的地方, 只有真正的仓库才有。
    """
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        if (os.path.exists(os.path.join(d, "skin.json"))
                and os.path.isdir(os.path.join(d, "src", "client"))):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return None


def pkg_root():
    """包目录 .../genshen_skin_cp8(本模块在它的 engine/ 下, 故向上一层)。

    pip 安装形态下 skin.json 与 engine/assets 都在这一层, 是「读包内文件」的基准。
    """
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def api_root():
    """「只是想读到皮肤文件」时的基准目录。

    仓库形态用仓库根(里面有 skin.json + src/client);
    pip 形态用包目录(里面有随包发布的 skin.json)。
    """
    return repo_root() or pkg_root()


def is_repo_checkout():
    return repo_root() is not None


def skin_meta():
    """读 skin.json(仓库形态读仓库根, pip 形态读包目录)。"""
    for base in (repo_root(), pkg_root()):
        if not base:
            continue
        p = os.path.join(base, "skin.json")
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f), p
            except Exception:
                continue
    return {}, None


# 兜底配色: pip 安装形态下仓库里没有 CSS 文件可读, 用与
# src/client/genshen-cp8.module.css 完全一致的取值, 保证在线转换与离线生成一致。
# 改 CSS 时请同步这里(deepking --what 会打印实际取到的值供比对)。
FALLBACK_CSS = """:root {
  --bg-base: #fdf8f3;
  --bg-layer-1: #fdf8f3;
  --bg-layer-2: #f7ece7;
  --bg-layer-3: #edd9d2;
  --label-primary: #2a1c1a;
  --label-secondary: #5c4340;
  --label-tertiary: #8d7370;
  --brand-primary: #c8433a;
  --accent: #c8433a;
  --primary: #c8433a;
  --interactive-bg-hover-solid: #f6e2dd;
  --interactive-bg-active: #ecc9c1;
  --border-l1: #eddad3;
  --border-l2: #dcc2b9;
  --border: #dcc2b9;
}
"""


def find_css(root):
    """按 DeepKing 的优先级挑选 CSS 文件。

    只认 <根>/src/client/ 下的 .module.css —— 这是 DeepKing 转换器的首选路径,
    也正是我们放配色的地方。不做全仓库通配, 否则会误取构建产物或其它套件的 CSS。
    """
    client = os.path.join(root, "src", "client")
    if not os.path.isdir(client):
        return None
    module_css = sorted(f for f in os.listdir(client) if f.endswith(".module.css"))
    if module_css:
        return os.path.join(client, module_css[0])
    any_css = sorted(f for f in os.listdir(client) if f.endswith(".css"))
    return os.path.join(client, any_css[0]) if any_css else None


# 扫描吉祥物时要跳过的目录: 构建产物、依赖、以及**包内素材**
# (engine/assets 里是壁纸用的插画, 不是编辑区水印; DeepKing 在线转换看到的是
#  GitHub 上的仓库, 不会去 engine/assets 里挑图, 本地也不该挑。)
_SKIP_DIR_PARTS = (".git", "node_modules", "__pycache__", "dist", "build",
                   "engine", "vscode", "tools", "preview")


def find_mascots(root):
    """挑选吉祥物图片, 优先级与 skinConverter.ts 一致。

    首选 <根>/assets/background/, 其次文件名含 maid/whale/poster/mascot 的,
    最后任意 assets/ 下的图片。engine/assets 与 vscode/media 一律排除,
    以免取到壁纸插画或扩展缩略图。
    """
    imgs = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIR_PARTS]
        if any(part in _SKIP_DIR_PARTS for part in base.split(os.sep)):
            continue
        for f in files:
            if re.search(r"\.(webp|png|jpe?g)$", f, re.I):
                imgs.append(os.path.join(base, f))
    rel = lambda p: os.path.relpath(p, root).replace("\\", "/")  # noqa: E731
    imgs.sort(key=lambda p: rel(p))

    def first(pred):
        for p in imgs:
            if pred(rel(p)):
                return p
        return None

    bg = [p for p in imgs if re.search(r"(^|/)assets/background/", rel(p), re.I)]
    if bg:
        light = first_containing(bg, rel, ("light", "day")) or bg[0]
        dark = first_containing(bg, rel, ("dark", "night")) or bg[0]
        return light, dark, None
    one = (
        first(lambda r: re.search(r"(maid|whale|poster|mascot)", r, re.I) and "assets" in r.lower())
        or first(lambda r: "assets" in r.lower())
    )
    return one, one, "assets/background/ 下没有图片, 已回退到其它候选"


def first_containing(paths, rel, keywords):
    for p in paths:
        low = rel(p).lower()
        if any(k in low for k in keywords):
            return p
    return None


# ---------------------------------------------------------------- 调色板推导

def derive_palette(vars_map, accent, light_theme, warnings, label):
    """复刻 skinConverter.ts 的 derivePalette(): 32 槽位。"""
    bg = _pick(vars_map, "bg") or _pick({"x": "#ffffff"}, "bg")
    bg = _pick(vars_map, "bg") or "#ffffff"
    light = col.is_light_color(bg)

    text = _pick(vars_map, "text") or ("#1f2937" if light else "#e5e7eb")
    layer2 = _pick(vars_map, "layer2") or (col.darken(bg, 0.04) if light else col.lighten(bg, 0.06))
    layer3 = _pick(vars_map, "layer3") or (col.darken(bg, 0.09) if light else col.lighten(bg, 0.12))
    border = _pick(vars_map, "border") or (col.darken(bg, 0.12) if light else col.lighten(bg, 0.18))
    hover = _pick(vars_map, "hover") or (col.darken(bg, 0.07) if light else col.lighten(bg, 0.09))
    selected = _pick(vars_map, "selected") or col.lighten(accent, 0.72 if light else 0.1)
    secondary_text = _pick(vars_map, "secondary") or (
        col.lighten(text, 0.35) if light else col.darken(text, 0.3))

    if not vars_map:
        warnings.append("%s：未提取到 CSS 变量，已使用默认派生配色" % label)

    user_bubble = col.lighten(accent, 0.78) if light else col.darken(accent, 0.35)
    return {
        "bg": bg,
        "bgText": text,
        "sidebarBg": layer2,
        "sidebarText": text,
        "sidebarHover": hover,
        "sidebarSelected": selected,
        "sidebarHeader": secondary_text,
        "editorBg": bg,
        "tabsBg": layer2,
        "tabBg": layer2,
        "tabText": secondary_text,
        "tabActiveBg": bg,
        "tabActiveText": text,
        "aiBg": layer2,
        "aiText": text,
        "aiTabText": secondary_text,
        "userBubbleBg": user_bubble,
        "userBubbleText": col.best_text_on(user_bubble),
        "aiBubbleBg": col.lighten(bg, 0.02) if light else col.lighten(bg, 0.08),
        "aiBubbleText": text,
        "aiBubbleBorder": border,
        "systemBubbleBg": "#fff8e6" if light else "#3d3420",
        "systemBubbleText": "#876800" if light else "#e8d9a0",
        "inputBg": col.lighten(bg, 0.02) if light else col.lighten(bg, 0.08),
        "inputText": text,
        "inputBorder": border,
        "accent": accent,
        "accentText": col.darken(accent, 0.75) if col.is_light_color(accent) else "#ffffff",
        "border": border,
        "chipBg": col.lighten(accent, 0.82) if light else col.darken(accent, 0.3),
        "chipText": col.darken(accent, 0.35) if light else col.lighten(accent, 0.55),
        "chipBorder": col.lighten(accent, 0.45) if light else accent,
    }


def derive_dark_from_light(light, accent, warnings):
    """未声明暗色作用域时, DeepKing 会按这套规则从亮色派生暗色。此处同款复刻。"""
    d = {
        **light,
        "bg": col.darken(light["bg"], 0.82), "bgText": col.lighten(light["bgText"], 0.85),
        "sidebarBg": col.darken(light["sidebarBg"], 0.86), "sidebarText": col.lighten(light["sidebarText"], 0.7),
        "sidebarHover": col.darken(light["sidebarBg"], 0.74), "sidebarSelected": col.darken(accent, 0.45),
        "sidebarHeader": col.darken(light["sidebarText"], 0.2),
        "editorBg": col.darken(light["editorBg"], 0.82),
        "tabsBg": col.darken(light["tabsBg"], 0.86), "tabBg": col.darken(light["tabBg"], 0.82),
        "tabText": col.darken(light["sidebarText"], 0.2),
        "tabActiveBg": col.darken(light["tabActiveBg"], 0.72),
        "tabActiveText": col.lighten(light["tabActiveText"], 0.85),
        "aiBg": col.darken(light["aiBg"], 0.86), "aiText": col.lighten(light["aiText"], 0.85),
        "aiTabText": col.darken(light["sidebarText"], 0.2),
        "userBubbleBg": col.darken(accent, 0.4), "userBubbleText": "#ffffff",
        "aiBubbleBg": col.darken(light["aiBubbleBg"], 0.78),
        "aiBubbleText": col.lighten(light["aiBubbleText"], 0.85),
        "aiBubbleBorder": col.darken(light["border"], 0.5),
        "inputBg": col.darken(light["inputBg"], 0.78), "inputText": col.lighten(light["inputText"], 0.85),
        "inputBorder": col.darken(light["border"], 0.4),
        "border": col.darken(light["border"], 0.55),
        "chipBg": col.darken(accent, 0.45), "chipText": col.lighten(accent, 0.6),
        "chipBorder": col.darken(accent, 0.15),
    }
    warnings.append("未找到暗色 CSS 变量，暗色变体已基于亮色自动派生")
    return d


# ---------------------------------------------------------------- 主流程

def skin_id():
    return ("custom-%s" % C.REPO_NAME).lower().replace("_", "-")


def raw_url(rel_path, branch="main"):
    return "https://raw.githubusercontent.com/%s/%s/%s/%s" % (
        "WPH666-py", C.REPO_NAME, branch, rel_path.replace("\\", "/"))


def convert(root=None, branch="main"):
    """本地复刻 DeepKing 的转换结果。返回 (skin_dict, warnings)。

    root 缺省时用 repo_root(); 若当前是 pip 安装(没有仓库), 会自动回退到
    包内数据 + FALLBACK_CSS, 保证离线也能产出与线上一致的皮肤。
    """
    warnings = []
    root = root or repo_root()
    if not root:
        if not is_repo_checkout():
            warnings.append("当前是 pip 安装形态, 未找到仓库文件; "
                            "已改用包内兜底配色(与仓库 CSS 一致)")
        root = api_root()

    # 1) skin.json
    meta, meta_path = skin_meta()
    if meta_path:
        pass
    else:
        warnings.append("未找到 skin.json，名称与强调色将根据仓库信息派生")

    # 2) CSS 变量
    css_path = find_css(root)
    if css_path:
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()
    else:
        css = FALLBACK_CSS
        if not any("兜底" in w for w in warnings):
            warnings.append("未找到 CSS 文件，已使用包内兜底变量")
    light_vars = extract_vars(css)
    dark_vars = extract_dark_vars(css)

    # 3) 强调色: skin.json accent > CSS brand 变量 > DeepSeek 蓝
    accent = meta.get("accent") or _pick(light_vars, "accent") or "#4d6bfe"
    if not col.is_hex(accent):
        warnings.append("skin.json 的 accent=%r 不是 # 十六进制，已回退默认色" % accent)
        accent = "#4d6bfe"

    # 4) 调色板
    light = derive_palette(light_vars, accent, True, warnings, "亮色")
    if dark_vars:
        dark = derive_palette(dark_vars, accent, False, warnings, "暗色")
    else:
        dark = derive_dark_from_light(light, accent, warnings)

    # 5) 吉祥物
    light_img, dark_img, note = find_mascots(root)
    if note:
        warnings.append(note)
    mascot = None
    if light_img:
        rel_l = os.path.relpath(light_img, root)
        rel_d = os.path.relpath(dark_img, root) if dark_img else rel_l
        mascot = {"light": raw_url(rel_l, branch), "dark": raw_url(rel_d, branch)}
    else:
        warnings.append("未找到装饰图片，皮肤将不含角色水印")

    skin = {
        "id": skin_id(),
        "name": meta.get("name") or meta.get("nameEn") or C.DISPLAY_NAME,
        "source": C.REPO_URL,
        "builtin": False,
        "description": meta.get("tagline") or meta.get("description")
                       or "从 GitHub 转换的自定义皮肤",
        "palettes": {"light": light, "dark": dark},
    }
    if mascot:
        skin["mascot"] = mascot
    return skin, warnings


# ---------------------------------------------------------------- 契约自检

def check(root=None):
    """校验本仓库是否满足 DeepKing 转换契约。返回 (ok, [问题...], [提示...])。"""
    errors, notes = [], []
    root = root or repo_root()
    if not root:
        return False, ["找不到仓库根目录(需包含 skin.json)"], []

    # skin.json
    skin_json = os.path.join(root, "skin.json")
    if not os.path.exists(skin_json):
        errors.append("缺少 skin.json(DeepKing 读取名称与强调色)")
    else:
        try:
            with open(skin_json, "r", encoding="utf-8") as f:
                meta = json.load(f)
            if not col.is_hex(meta.get("accent", "")):
                errors.append("skin.json 的 accent 必须是 # 十六进制(转换器只认这种格式)")
            if not (meta.get("name") or meta.get("nameEn")):
                notes.append("skin.json 建议提供 name 或 nameEn")
        except Exception as e:
            errors.append("skin.json 不是合法 JSON: %s" % e)

    # CSS
    css = find_css(root)
    if not css:
        errors.append("找不到任何 .css 文件")
    else:
        with open(css, "r", encoding="utf-8") as f:
            text = f.read()
        clean = strip_comments(text)
        lv, dv = extract_vars(text), extract_dark_vars(text)
        if not lv:
            errors.append("CSS 中未提取到 --变量: #色值(注意色值必须是 # 开头)")
        for key in ("bg", "text", "accent", "border"):
            if not _pick(lv, key):
                notes.append("亮色缺少 %s 相关变量(DeepKing 会走自动派生): %s"
                             % (key, "/".join(KEY_VARS[key])))
        if not dv:
            notes.append("未声明暗色作用域(选择器含 dark 的块); DeepKing 会从亮色自动派生暗色")

        # DeepKing 的 extractVars() 是无作用域全文扫描且后者覆盖前者:
        # 亮/暗作用域各声明一次同名变量是**正常且必需**的写法(亮色取前、暗色块单独提取),
        # 但若在亮色作用域内重复声明不同色值, 或用了 @media (prefers-color-scheme),
        # 亮色调色板就会被后面的值污染。这里只报这两类真问题。
        in_dark = False
        light_seen, dup = {}, []
        for m in _BLOCK_RE.finditer(clean):
            selector, body = m.group(1), m.group(2)
            if "dark" in selector.lower():
                continue
            for vm in _VAR_RE.finditer(body):
                name, value = vm.group(1), vm.group(2).lower()
                if name in light_seen and light_seen[name] != value:
                    dup.append("%s(%s → %s)" % (name, light_seen[name], value))
                light_seen[name] = value
        if dup:
            notes.append("亮色作用域内重复声明了不同色值(后者生效): " + ", ".join(sorted(set(dup))[:6]))
        if re.search(r"@media[^{]*prefers-color-scheme", clean):
            notes.append("发现真实的 @media (prefers-color-scheme) 块: 若其中重复声明同名颜色变量, "
                         "DeepKing 的无作用域扫描会用它覆盖亮色调色板(内置皮肤均不用该写法)")
        # 非法色值(DeepKing 正则不认 rgb()/hsl()/颜色名)——
        # 只看剥掉注释后的正文, 否则文档里写的「--变量名: 说明」会被误判
        for m in re.finditer(r"(--[\w-]+)\s*:\s*([^;#}]+)", clean):
            val = m.group(2).strip()
            if val and not col.is_hex(val):
                notes.append("变量 %s 的值 %r 不是 # 十六进制, 转换器会忽略"
                             % (m.group(1), val[:40]))

        # 反向护栏: 注释里出现花括号会被 DeepKing 的块正则当成假选择器块,
        # 使其把注释内容当变量抽取(值恰好都是十六进制时还会真的污染调色板)。
        for c in _COMMENT_RE.finditer(text):
            body = c.group(0)
            if "{" in body or "}" in body:
                notes.append("CSS 注释里出现了花括号: DeepKing 不剥注释, 会把整段注释"
                             "误认作选择器块并尝试从中取色, 建议删掉注释里的花括号")
            if "dark" in body.lower():
                notes.append("CSS 注释里出现了 dark 字样: 会被 extractDarkVars 误判成"
                             "暗色作用域, 建议改写该词")
            for vm in _VAR_RE.finditer(body):
                notes.append("CSS 注释里出现了「%s: %s」形式: 转换器不剥注释, 会把它当成"
                             "真实变量取值, 建议在注释里避免这种写法"
                             % (vm.group(1), vm.group(2)))

    # 吉祥物
    light_img, dark_img, note = find_mascots(root)
    if not light_img:
        errors.append("找不到吉祥物图片(DeepKing 会提示“皮肤将不含角色水印”)")
    elif note:
        notes.append(note)
    else:
        for p in {light_img, dark_img}:
            if p:
                size_mb = os.path.getsize(p) / 1024.0 / 1024.0
                if size_mb > 3:
                    notes.append("%s 体积 %.1f MB, 偏大(DeepKing 每次转换都要下载)"
                                 % (os.path.relpath(p, root), size_mb))

    # 本地转换应能零告警通过
    try:
        _skin, warnings = convert(root)
        for w in warnings:
            notes.append("转换告警: %s" % w)
    except Exception as e:
        errors.append("本地转换失败: %s" % e)

    return (not errors), errors, notes


# ---------------------------------------------------------------- 预览 / 导出

def _data_uri(path):
    """把本地图片转成 data: URI, 让预览完全离线自包含。"""
    import base64
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp"}.get(ext, "jpeg")
    with open(path, "rb") as f:
        return "data:image/%s;base64,%s" % (mime, base64.b64encode(f.read()).decode("ascii"))


def preview_html(skin, embed_images=True):
    """把 SkinDefinition 渲染成一个自包含的 HTML 预览(模拟 DeepKing 各区域)。

    embed_images=True 时把吉祥物内联为 data: URI, 预览离线也能显示;
    False 则保留 mascot 里的原始 URL(用于观察 DeepKing 实际会加载哪个地址)。
    """
    p = skin["palettes"]["light"]
    d = skin["palettes"]["dark"]
    mascot = dict(skin.get("mascot") or {})

    if embed_images:
        root = repo_root()
        for key in ("light", "dark"):
            url = mascot.get(key)
            if not url or url.startswith("data:"):
                continue
            # raw URL -> 本地文件
            rel = None
            m = re.search(r"raw\.githubusercontent\.com/[^/]+/[^/]+/[^/]+/(.+)$", url)
            if m:
                rel = m.group(1)
            if rel and root:
                local = os.path.join(root, rel.replace("/", os.sep))
                if os.path.exists(local):
                    try:
                        mascot[key] = _data_uri(local)
                    except OSError:
                        pass

    REGION_CSS = """
    .mock{border-radius:12px;overflow:hidden;border:1px solid rgba(127,127,127,.25);margin-bottom:10px}
    .bar{display:flex;justify-content:space-between;align-items:center;padding:8px 12px;border-bottom:1px solid}
    .body{display:flex;min-height:250px}
    aside{width:190px;border-right:1px solid;padding:9px;font-size:12px}
    aside .hdr{font-size:11px;margin-bottom:7px}
    aside .item{padding:4px 6px;border-radius:5px;margin-bottom:2px}
    main{flex:1;display:flex;flex-direction:column}
    .tabs{display:flex;gap:5px;padding:6px 8px;font-size:12px}
    .tab{padding:3px 11px;border-radius:6px 6px 0 0}
    .tab.act{border-top:2px solid}
    .editor{position:relative;flex:1;padding:16px;display:flex;flex-direction:column;gap:9px}
    .mascot{position:absolute;right:16px;bottom:8px;width:150px;height:150px;object-fit:cover;
    border-radius:14px;opacity:.9;box-shadow:0 10px 26px rgba(0,0,0,.35)}
    .bubble{max-width:64%;padding:7px 12px;border-radius:11px;font-size:12.5px}
    .bubble.ai{border:1px solid}
    .bubble.user{align-self:flex-end}
    .input{margin-top:auto;border:1px solid;border-radius:9px;padding:7px 10px;font-size:12px}
    .swatches{display:flex;flex-wrap:wrap;gap:9px;margin-top:12px}
    .sw{display:flex;align-items:center;gap:7px;background:rgba(127,127,127,.1);border-radius:8px;padding:6px 9px}
    .sw i{width:22px;height:22px;border-radius:5px;display:block;border:1px solid rgba(127,127,127,.3)}
    .sw span{font-size:10.5px;line-height:1.35}.sw code{opacity:.7;font-size:10px}
    """

    def swatch(label, value):
        return ('<div class="sw"><i style="background:%s"></i>'
                '<span>%s<br/><code>%s</code></span></div>' % (value, label, value))

    def region(pa, title, mascot_url):
        return """
        <section class="mock" style="background:%(bg)s;color:%(bgText)s">
          <div class="bar" style="background:%(bg)s;color:%(bgText)s;border-color:%(border)s">
            <b>%(title)s</b>
            <span style="background:%(accent)s;color:%(accentText)s;padding:3px 10px;border-radius:6px">发送</span>
          </div>
          <div class="body">
            <aside style="background:%(sidebarBg)s;color:%(sidebarText)s;border-color:%(border)s">
              <div class="hdr" style="color:%(sidebarHeader)s">资源管理器</div>
              <div class="item">📁 Genshen-skin-CP8</div>
              <div class="item" style="background:%(sidebarHover)s">📄 skin.json</div>
              <div class="item" style="background:%(sidebarSelected)s">📄 skin_core.py</div>
            </aside>
            <main style="background:%(editorBg)s">
              <div class="tabs" style="background:%(tabsBg)s">
                <span class="tab" style="background:%(tabBg)s;color:%(tabText)s">wallpaper.py</span>
                <span class="tab act" style="background:%(tabActiveBg)s;color:%(tabActiveText)s;border-top-color:%(accent)s">skin.json</span>
              </div>
              <div class="editor">
                %(mascot)s
                <div class="bubble user" style="background:%(userBubbleBg)s;color:%(userBubbleText)s">换成满屏那张</div>
                <div class="bubble ai" style="background:%(aiBubbleBg)s;color:%(aiBubbleText)s;border-color:%(aiBubbleBorder)s">
                  已切换到「林间 · 满屏」(cover1)。
                </div>
                <div class="bubble" style="background:%(systemBubbleBg)s;color:%(systemBubbleText)s">
                  系统提示气泡样式
                </div>
                <div class="input" style="background:%(inputBg)s;color:%(inputText)s;border-color:%(inputBorder)s">
                  chip: <span style="background:%(chipBg)s;color:%(chipText)s;border:1px solid %(chipBorder)s;border-radius:9px;padding:1px 7px">skin.json</span>
                </div>
              </div>
            </main>
          </div>
        </section>
        <div class="swatches">%(swatches)s</div>
        """ % {
            "bg": pa["bg"], "bgText": pa["bgText"], "border": pa["border"],
            "accent": pa["accent"], "accentText": pa["accentText"],
            "sidebarBg": pa["sidebarBg"], "sidebarText": pa["sidebarText"],
            "sidebarHeader": pa["sidebarHeader"], "sidebarHover": pa["sidebarHover"],
            "sidebarSelected": pa["sidebarSelected"], "editorBg": pa["editorBg"],
            "tabsBg": pa["tabsBg"], "tabBg": pa["tabBg"], "tabText": pa["tabText"],
            "tabActiveBg": pa["tabActiveBg"], "tabActiveText": pa["tabActiveText"],
            "userBubbleBg": pa["userBubbleBg"], "userBubbleText": pa["userBubbleText"],
            "aiBubbleBg": pa["aiBubbleBg"], "aiBubbleText": pa["aiBubbleText"],
            "aiBubbleBorder": pa["aiBubbleBorder"],
            "systemBubbleBg": pa["systemBubbleBg"], "systemBubbleText": pa["systemBubbleText"],
            "inputBg": pa["inputBg"], "inputText": pa["inputText"], "inputBorder": pa["inputBorder"],
            "chipBg": pa["chipBg"], "chipText": pa["chipText"], "chipBorder": pa["chipBorder"],
            "title": title,
            "mascot": ('<img class="mascot" width="150" height="150" src="%s" alt="吉祥物"/>'
                       % mascot_url) if mascot_url else
                      '<div class="mascot nopic">未找到<br/>吉祥物</div>',
            "swatches": "".join(
                swatch(k, pa[k]) for k in
                ("bg", "sidebarBg", "editorBg", "accent", "border",
                 "userBubbleBg", "aiBubbleBg", "chipBg")),
        }

    return """<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<title>%(name)s — DeepKing 皮肤预览</title><style>
body{margin:0;padding:22px;background:#0e1520;color:#dbe6f2;font:14px/1.6 system-ui,"Microsoft YaHei",sans-serif}
h1{font-size:19px;margin:0 0 4px}p.sub{opacity:.6;margin:0 0 20px;font-size:12px}
h2{font-size:14px;margin:26px 0 10px;opacity:.75;font-weight:600}
%(region_css)s
</style></head><body>
<h1>%(name)s</h1>
<p class="sub">DeepKing 皮肤预览 · id <code>%(id)s</code> · 强调色 <code>%(accent)s</code> · 本地离线渲染<br/>
<code>%(source)s</code></p>
<h2>☀️ 亮色 Light</h2>%(light)s
<h2>🌙 暗色 Dark</h2>%(dark)s
</body></html>""" % {
        "name": skin["name"], "id": skin["id"], "source": skin.get("source", ""),
        "accent": p["accent"], "region_css": REGION_CSS,
        "light": region(p, "亮色 · 原神CP8", mascot.get("light")),
        "dark": region(d, "暗色 · 原神CP8", mascot.get("dark")),
    }


def export_json(skin, out_path):
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(skin, f, ensure_ascii=False, indent=2)
    return out_path
