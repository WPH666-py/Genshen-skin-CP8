# -*- coding: utf-8 -*-
"""
原神 CP 壁纸套件 8 —— 核心库
跨平台: Windows / macOS / Linux

职责:
  * 素材定位 —— pip 安装(wheel 内包数据) 与 git 仓库(assets/) 两种形态都能跑
  * 单张样式合成 —— 模糊填充背景 + 居中圆角卡片(不裁切) / cover 满屏裁切
  * 系统壁纸设置 —— Windows / macOS / Linux
  * 热更新 —— 素材或本文件改动后自动重新合成, 无需手动清缓存

只依赖 Pillow, 其余全部标准库。
"""
import os
import platform
import subprocess
import sys

from ..characters import cp8_pair as C

# ---------------------------------------------------------------- 目录

APP_DIR = C.APP_DIR
WALLPAPER_DIR = C.WALLPAPER_DIR
CACHE_DIR = C.CACHE_DIR

IMAGE_FILES = C.IMAGE_FILES
IMAGE_NAMES = C.IMAGE_NAMES
MODES = C.MODES
DEFAULT_MODE = C.DEFAULT_MODE

# 卡片圆角比例 / 边距比例(单张样式)
CARD_MARGIN_RATIO = 0.035
CARD_RADIUS_RATIO = 0.035
# 模糊背景的缩小尺寸与模糊半径
BG_SMALL = 96
BG_BLUR = 32


def prepare_console():
    """Windows GBK 控制台避免 Unicode 打印崩溃。"""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def ensure_dirs():
    for d in (APP_DIR, WALLPAPER_DIR, CACHE_DIR):
        os.makedirs(d, exist_ok=True)


def ensure_pillow():
    """确保 Pillow 可用; 缺失时自动 pip 安装。"""
    try:
        import PIL  # noqa: F401
        return
    except ImportError:
        pass
    print("[%s] 未检测到 Pillow, 正在自动安装 ..." % C.APP_SLUG)
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "--user", "pillow"]
    )
    import PIL  # noqa: F401


# ---------------------------------------------------------------- 素材定位

def _repo_assets_dir():
    """素材目录候选(按优先级)。

    CP8 的包是嵌套结构(src/genshen_skin_cp8/engine/), 素材放在 engine/assets/,
    因此这里比 CP1 多一层候选:
      1. <包>/engine/assets/            —— 本仓库与 wheel 的实际位置
      2. <仓库根>/assets/               —— 允许把素材放仓库根统一管理
      3. <仓库根>/src/genshen_skin_cp8/assets/ —— 兼容素材提到包根的写法

    只有在**仓库根**存在(即 src/client 这类仓库标志齐全)时才探测 2/3,
    否则 pip 形态下会把 site-packages 的上级目录当成仓库根乱找。
    """
    here = os.path.dirname(os.path.abspath(__file__))
    pkg = os.path.dirname(here)                      # .../genshen_skin_cp8
    cands = [os.path.join(here, "assets")]
    # 仓库根: 从包往上找带 skin.json 的那层
    d = pkg
    for _ in range(4):
        if os.path.exists(os.path.join(d, "skin.json")):
            cands.append(os.path.join(d, "assets"))
            cands.append(os.path.join(pkg, "assets"))
            break
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    for cand in cands:
        if os.path.isdir(cand) and os.path.exists(os.path.join(cand, IMAGE_FILES[0])):
            return cand
    return None


def assets_dir():
    """返回素材目录(带缓存)。优先仓库内 assets/, 回退 wheel 内包数据。"""
    if C.ASSETS_DIR and os.path.isdir(C.ASSETS_DIR):
        return C.ASSETS_DIR
    found = _repo_assets_dir()
    if found:
        C.ASSETS_DIR = found
        return found
    # pip 安装形态: 包数据目录(engine/assets)
    for cand in (
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets"),
    ):
        if os.path.isdir(cand):
            C.ASSETS_DIR = cand
            return cand
    # 最后尝试 importlib.resources(某些 zip 安装方式)
    try:
        from importlib.resources import files as _files
        for rel in ("engine/assets", "assets"):
            p = _files("genshen_skin_cp8")
            for part in rel.split("/"):
                p = p.joinpath(part)
            sp = str(p)
            if os.path.isdir(sp):
                C.ASSETS_DIR = sp
                return sp
    except Exception:
        pass
    raise FileNotFoundError(
        "未找到素材目录。请确认安装完整: pip install --force-reinstall %s" % C.PACKAGE_NAME
    )


def asset_path(idx):
    """idx: 1..N, 返回第 idx 张素材路径。"""
    return os.path.join(assets_dir(), IMAGE_FILES[idx - 1])


def asset_path_by_name(name):
    return os.path.join(assets_dir(), name)


def count():
    return len(IMAGE_FILES)


# ---------------------------------------------------------------- 模式解析

def _mode_index(modelike):
    """'single1' / 'cover2' / 'showall3' / '1' -> 0-based 张序号。"""
    if isinstance(modelike, int):
        i = modelike
    else:
        s = str(modelike).strip().lower()
        if s in ("single", "cover", "showall", "full"):
            i = 1
        elif s and s[-1].isdigit():
            i = int(s.lstrip("singlecovershowallfullx-"))
        else:
            i = 1
    if not (1 <= i <= count()):
        raise ValueError("第 %s 张不存在, 本套件共 %d 张" % (i, count()))
    return i - 1


def resolve_mode(mode):
    """把用户输入归一化为合法模式名。

    会把无编号的写法补成第 1 张: cover -> cover1, showall -> showall1,
    card/single -> single1。这样后面的 compose() 只需处理带编号的名字。
    """
    if mode is None:
        return DEFAULT_MODE
    s = str(mode).strip().lower()
    if s in ("", "default", "random"):
        return DEFAULT_MODE if s != "random" else "random"
    s = {"card": "single"}.get(s, s)
    if s.isdigit():
        return "single" + s
    # 非按张编号的模式(如 showall)直接匹配
    if s in [m[0] for m in MODES]:
        # MODES 里可能存在无编号的写法(单张套件), 统一补成第 1 张
        return s if (s and s[-1].isdigit()) else s + "1"
    # 按张编号的三种摆法: single1 / cover2 / showall3(以及 fullN 别名)
    if s.startswith(("single", "cover", "showall", "full")):
        s = "showall" + s[4:] if s.startswith("full") else s
        _mode_index(s)  # 校验范围
        return s if s[-1].isdigit() else s + "1"
    if s.startswith("img"):
        s = "single" + s[3:]
        _mode_index(s)
        return s
    valid = ", ".join(m[0] for m in MODES)
    raise ValueError("未知模式 %r, 可用: %s" % (mode, valid))


def mode_label(mode):
    """模式的显示名。找不到时退一步: 去掉末尾编号再找一次。

    单张套件的 MODES 里写的是无编号的 `showall`, 而 resolve_mode 会把它
    归一成 `showall1`, 直接查表就落空、界面会显示生涩的 "showall1"。
    这里先精确匹配, 再去编号匹配, 最后才原样返回。
    """
    for key, label in MODES:
        if key == mode:
            return label
    stripped = mode.rstrip("0123456789")
    if stripped != mode:
        for key, label in MODES:
            if key == stripped:
                return label
    return mode


def all_modes():
    return [m[0] for m in MODES]


def pick_random():
    import random
    return random.choice(all_modes())


# ---------------------------------------------------------------- 屏幕尺寸

def screen_size():
    """返回主屏幕尺寸 (W, H); 失败回退 1920x1080。
    可用环境变量 DEEPSKIN_SIZE / GENSHIN_CP1_SIZE 覆盖, 如 2560x1440。
    """
    for env_name in ("GENSHIN_CP1_SIZE", "DEEPSKIN_SIZE"):
        env = os.environ.get(env_name, "").strip()
        if env:
            try:
                w, h = env.lower().split("x")
                return int(w), int(h)
            except ValueError:
                pass
    try:
        if platform.system() == "Windows":
            import ctypes
            user32 = ctypes.windll.user32
            try:
                user32.SetProcessDPIAware()
            except Exception:
                pass
            return int(user32.GetSystemMetrics(0)), int(user32.GetSystemMetrics(1))
    except Exception:
        pass
    try:
        if platform.system() == "Darwin":
            out = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],
                capture_output=True, text=True, timeout=10,
            ).stdout
            import re
            m = re.search(r"Resolution:\s*(\d+)\s*x\s*(\d+)", out)
            if m:
                return int(m.group(1)), int(m.group(2))
    except Exception:
        pass
    try:
        if platform.system() == "Linux":
            out = subprocess.run(
                ["xrandr", "--current"], capture_output=True, text=True, timeout=10
            ).stdout
            import re
            m = re.search(r"(\d+)x(\d+)\+0\+0", out)
            if m:
                return int(m.group(1)), int(m.group(2))
    except Exception:
        pass
    return 1920, 1080


def parse_size(text):
    w, h = str(text).lower().replace(" ", "").split("x")
    w, h = int(w), int(h)
    if w < 320 or h < 240:
        raise ValueError("尺寸太小: %s" % text)
    return w, h


# ---------------------------------------------------------------- 图像合成

def _paste_card(base, src, cell, margin_ratio=CARD_MARGIN_RATIO,
                radius_ratio=CARD_RADIUS_RATIO, shadow=True):
    """把 src 按 contain 方式贴进 cell, 圆角 + 柔和阴影(右侧/下侧投影)。"""
    from PIL import Image, ImageDraw, ImageFilter

    x0, y0, cw, ch = cell
    margin = max(6, int(min(cw, ch) * margin_ratio))
    tw, th = cw - 2 * margin, ch - 2 * margin
    scale = min(tw / src.width, th / src.height)
    nw, nh = max(1, int(src.width * scale)), max(1, int(src.height * scale))
    tile = src.resize((nw, nh), Image.LANCZOS)
    x, y = x0 + (cw - nw) // 2, y0 + (ch - nh) // 2
    radius = max(6, int(min(cw, ch) * radius_ratio))

    mask = Image.new("L", (nw, nh), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, nw - 1, nh - 1], radius=radius, fill=255
    )

    if shadow:
        pad = max(12, radius * 2)
        sh = Image.new("RGBA", (nw + 2 * pad, nh + 2 * pad), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle(
            [pad, pad + max(3, pad // 4), pad + nw - 1, pad + nh - 1 + max(3, pad // 4)],
            radius=radius, fill=(20, 40, 90, 72),
        )
        sh = sh.filter(ImageFilter.GaussianBlur(max(10, radius)))
        base.alpha_composite(sh, (x - pad, y - pad))
    base.paste(tile, (x, y), mask)


def compose_single(idx, size=None):
    """单张样式: 模糊填充背景 + 居中圆角卡片。竖图不裁切, 构图完整。"""
    ensure_pillow()
    from PIL import Image, ImageFilter

    if size is None:
        size = screen_size()
    w, h = size
    src = Image.open(asset_path(idx)).convert("RGB")

    # 背景: 原图缩小 -> 铺满 -> 重模糊, 得到同色系氛围底
    sw = BG_SMALL
    sh = max(1, int(sw * src.height / src.width))
    small = src.resize((sw, sh), Image.BOX)
    scale = max(w / sw, h / sh)
    bw, bh = max(w, int(sw * scale)), max(h, int(sh * scale))
    bg = small.resize((bw, bh), Image.BICUBIC)
    left, top = (bw - w) // 2, (bh - h) // 2
    bg = bg.crop((left, top, left + w, top + h))
    bg = bg.filter(ImageFilter.GaussianBlur(BG_BLUR))

    base = bg.convert("RGBA")
    _paste_card(base, src, (0, 0, w, h))
    return base.convert("RGB")


def compose_cover(idx, size=None):
    """满屏样式: 素材按 cover 裁切铺满整屏, 无边框。

    竖图对 16:9 做正中对半裁会把人物头部切掉, 因此按素材的
    IMAGE_META[...]["cover_bias"] 把取景窗偏向主体(缺省居中)。
    """
    ensure_pillow()
    from PIL import Image

    if size is None:
        size = screen_size()
    name = IMAGE_FILES[idx - 1]
    src = Image.open(asset_path(idx)).convert("RGB")
    W, H = size
    scale = max(W / src.width, H / src.height)
    nw, nh = max(W, int(round(src.width * scale))), max(H, int(round(src.height * scale)))
    img = src.resize((nw, nh), Image.LANCZOS)

    meta = C.IMAGE_META.get(name, {}) or {}
    bx, by = meta.get("cover_bias") or (0.5, 0.5)
    # 取景窗左上角: 让偏向点尽量落在画面中心, 再夹紧到合法范围
    x = int(round(bx * nw - W / 2.0))
    y = int(round(by * nh - H / 2.0))
    x = max(0, min(nw - W, x))
    y = max(0, min(nh - H, y))
    return img.crop((x, y, x + W, y + H))


def compose_showall(idx, size=None):
    """完整样式: 等比缩放整幅放进画面, 四周用同色系纯色补齐。

    一个像素都不裁 —— 适合「宁可两边留边, 也不能切掉人物」的场合。
    底色取素材四角的中位色, 因此白底插画得到白边、夜空插画得到深边。
    """
    ensure_pillow()
    from PIL import Image

    if size is None:
        size = screen_size()
    W, H = size
    src = Image.open(asset_path(idx)).convert("RGB")

    # 底色: 采样四角, 取通道中位数, 避免被单个角落的异色带偏
    w, h = src.size
    corners = [src.getpixel(p) for p in (
        (1, 1), (w - 2, 1), (1, h - 2), (w - 2, h - 2))]
    base = tuple(sorted(c[i] for c in corners)[len(corners) // 2] for i in range(3))

    scale = min(W / src.width, H / src.height)
    nw, nh = max(1, int(round(src.width * scale))), max(1, int(round(src.height * scale)))
    tile = src.resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("RGB", (W, H), base)
    canvas.paste(tile, ((W - nw) // 2, (H - nh) // 2))
    return canvas


def compose(mode, size=None):
    """按模式名合成壁纸, 返回 PIL.Image。"""
    mode = resolve_mode(mode)
    if size is None:
        size = screen_size()
    size = tuple(size)
    # 三种摆法都按张编号: singleN / coverN / showallN
    # (单张套件里 "showall" 也走这里, _mode_index 会把无编号的当第 1 张)
    if mode.startswith("showall"):
        return compose_showall(_mode_index(mode) + 1, size)
    if mode.startswith("cover"):
        return compose_cover(_mode_index(mode) + 1, size)
    if mode.startswith("single"):
        return compose_single(_mode_index(mode) + 1, size)
    raise ValueError("未知模式: %s" % mode)


# ---------------------------------------------------------------- 缓存 / 热更新

def wallpaper_path(mode, size):
    return os.path.join(WALLPAPER_DIR, "%s-%dx%d.jpg" % (mode, size[0], size[1]))


def _source_freshness():
    """素材与本包全部 .py 的最新修改时间, 用于判断输出是否过期(热更新)。"""
    paths = []
    try:
        ad = assets_dir()
        paths += [os.path.join(ad, f) for f in IMAGE_FILES]
    except FileNotFoundError:
        pass
    here = os.path.dirname(os.path.abspath(__file__))
    try:
        for f in os.listdir(here):
            if f.endswith(".py"):
                paths.append(os.path.join(here, f))
    except OSError:
        pass
    mt = 0.0
    for p in paths:
        try:
            mt = max(mt, os.path.getmtime(p))
        except OSError:
            pass
    return mt


def build(mode, size=None, force=False):
    """合成并保存, 返回文件路径。素材/代码更新后自动重新生成(热更新)。"""
    ensure_dirs()
    mode = resolve_mode(mode)
    size = tuple(size) if size else screen_size()
    out = wallpaper_path(mode, size)
    stale = (
        force
        or not os.path.exists(out)
        or os.path.getmtime(out) < _source_freshness()
    )
    if not stale:
        return out
    img = compose(mode, size)
    img.save(out, quality=93, subsampling=0)
    return out


def build_all(out_dir=None, size=None, force=True):
    """生成全部模式到 out_dir(默认 ~/.genshen-cp8/wallpapers), 返回 [(mode, label, path)]。"""
    ensure_dirs()
    size = tuple(size) if size else screen_size()
    out_dir = os.path.abspath(out_dir) if out_dir else WALLPAPER_DIR
    os.makedirs(out_dir, exist_ok=True)
    results = []
    for key in all_modes():
        path = os.path.join(out_dir, "%s-%dx%d.jpg" % (key, size[0], size[1]))
        if force or not os.path.exists(path):
            compose(key, size).save(path, quality=93, subsampling=0)
        results.append((key, mode_label(key), path))
    return results


# ---------------------------------------------------------------- 系统壁纸

def set_wallpaper(path):
    """跨平台设置系统壁纸。"""
    path = os.path.abspath(path)
    if not os.path.exists(path):
        raise FileNotFoundError("壁纸文件不存在: %s" % path)
    system = platform.system()
    if system == "Windows":
        import ctypes
        import time
        time.sleep(0.4)  # 留出写盘时间, 避免 Explorer 读到旧缓存以为"没变化"
        SPI_SETDESKWALLPAPER = 20
        SPIF_UPDATEINIFILE, SPIF_SENDWININICHANGE = 0x01, 0x02
        ok = ctypes.windll.user32.SystemParametersInfoW(
            SPI_SETDESKWALLPAPER, 0, path,
            SPIF_UPDATEINIFILE | SPIF_SENDWININICHANGE,
        )
        if not ok:
            raise RuntimeError("Windows 设置壁纸失败(可能被组策略禁用)")
    elif system == "Darwin":
        subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to set picture of every desktop '
             'to POSIX file "%s"' % path],
            check=True,
        )
    else:
        import pathlib
        uri = pathlib.Path(path).as_uri()
        ok = False
        for key in ("picture-uri", "picture-uri-dark"):
            r = subprocess.run(
                ["gsettings", "set", "org.gnome.desktop.background", key, uri],
                check=False,
            )
            ok = ok or r.returncode == 0
        if not ok:
            for cmd in (["feh", "--bg-fill", path],
                        ["nitrogen", "--set-zoom-fill", "--save", path],
                        ["pcmanfm", "--set-wallpaper", path]):
                try:
                    if subprocess.run(cmd, check=False).returncode == 0:
                        ok = True
                        break
                except FileNotFoundError:
                    continue
        if not ok:
            print("[%s] 未能自动设置壁纸, 请手动选择: %s" % (C.APP_SLUG, path))
    print("[%s] 壁纸已设置: %s" % (C.APP_SLUG, path))


def apply(mode, size=None, force=True):
    """合成 + 设为壁纸, 返回文件路径。"""
    out = build(mode, size, force=force)
    set_wallpaper(out)
    return out
