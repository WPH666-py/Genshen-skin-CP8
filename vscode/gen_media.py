# -*- coding: utf-8 -*-
"""
生成 VSCode 扩展画廊所需的缩略图与图标。

  python vscode/gen_media.py

优先从仓库源码(src/)导入本套件; 若已 pip 安装则直接用已安装的包。
输出到 vscode/media/:
  thumb-single1..3.png / thumb-cover1..3.png  画廊卡片缩略图 (640x360)
  thumb-grid.png                              所有样式拼版 (文档用)
  icon.png                                    扩展市场图标 (256x256)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
MEDIA = os.path.join(HERE, "media")
THUMB = (640, 360)

# 优先仓库源码, 回退已安装包
sys.path.insert(0, os.path.join(REPO, "src"))
try:
    from genshen_skin_cp8.engine import skin_core as sc
except ImportError:  # 已 pip 安装的情况
    from genshen_skin_cp8.engine import skin_core as sc


def ensure_media():
    os.makedirs(MEDIA, exist_ok=True)


def make_thumbs():
    from PIL import Image
    modes = [m[0] for m in sc.MODES]
    made = []
    for mode in modes:
        img = sc.compose(mode, THUMB)
        out = os.path.join(MEDIA, "thumb-%s.png" % mode)
        img.save(out, optimize=True)
        made.append(out)
        print("  OK  %-9s -> %s" % (mode, os.path.basename(out)))

    # 拼版总览图: 按实际样式数量排成一行(本套件 3 个), 不留空行
    modes_n = len(modes)
    cols = modes_n if modes_n <= 3 else 3
    rows = (modes_n + cols - 1) // cols
    tw, th = THUMB
    gap = 12
    sheet = Image.new("RGB", (cols * tw + (cols + 1) * gap,
                              rows * th + (rows + 1) * gap), (14, 20, 38))
    for i, mode in enumerate(modes):
        r, c = divmod(i, cols)
        sheet.paste(sc.compose(mode, THUMB),
                    (gap + c * (tw + gap), gap + r * (th + gap)))
    sheet_out = os.path.join(MEDIA, "thumb-grid.png")
    sheet.save(sheet_out, optimize=True)
    print("  OK  grid      -> %s (%dx%d, %d 格)"
          % (os.path.basename(sheet_out), sheet.width, sheet.height, modes_n))
    return made


def heart_polygon(cx, cy, size, steps=720):
    """用参数方程生成一颗**无缝**爱心, 返回多边形顶点列表。

    参数方程: x = 16sin³t, y = 13cos t − 5cos2t − 2cos3t − cos4t
    这个曲线天然对称且连续, 不会出现「两圆 + 三角」拼合时的接缝。
    """
    import math
    pts = []
    scale = size / 32.0  # 曲线 x 范围约 ±16, y 约 ±17
    for i in range(steps):
        t = 2.0 * math.pi * i / steps
        x = 16 * math.sin(t) ** 3
        y = (13 * math.cos(t) - 5 * math.cos(2 * t)
             - 2 * math.cos(3 * t) - math.cos(4 * t))
        # y 轴翻转(PIL 的 y 向下), 再按中心定位
        pts.append((cx + x * scale, cy - y * scale))
    return pts


def make_icon():
    """扩展图标: 钴蓝到薰衣草紫渐变圆角底 + 白色爱心 + 一颗星。

    配色取自插画: 纳西妲的草绿与安柏的琥珀棕红。
    """
    from PIL import Image, ImageDraw
    S = 256
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # 渐变底: 上朱红 -> 下墨蓝(与皮肤 accent #c8433a 同源)
    top = (200, 67, 58)       # #c8433a 胡桃的朱红
    bottom = (31, 41, 66)     # #1f2942 芙宁娜的墨蓝
    for y in range(S):
        t = y / (S - 1)
        d.line([(0, y), (S, y)], fill=tuple(
            int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)) + (255,))
    # 圆角遮罩
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, S - 1, S - 1], radius=56, fill=255)
    img.putalpha(mask)

    # 爱心: 4 倍超采样 + 参数曲线, 边缘平滑且无接缝
    SS = 4
    big = Image.new("RGBA", (S * SS, S * SS), (0, 0, 0, 0))
    ImageDraw.Draw(big).polygon(
        heart_polygon(S * SS // 2, int(S * SS * 0.46), int(S * SS * 0.78)),
        fill=(255, 255, 255, 255))
    img = Image.alpha_composite(img, big.resize((S, S), Image.LANCZOS))

    # 左下角一颗四角星, 呼应插画里的星星装饰(避开爱心主体)
    star = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    sd = ImageDraw.Draw(star)
    sx, sy, sr = int(S * 0.20), int(S * 0.80), int(S * 0.10)
    sd.polygon([(sx, sy - sr), (sx + sr // 3, sy - sr // 3),
                (sx + sr, sy), (sx + sr // 3, sy + sr // 3),
                (sx, sy + sr), (sx - sr // 3, sy + sr // 3),
                (sx - sr, sy), (sx - sr // 3, sy - sr // 3)],
               fill=(216, 233, 255, 255))
    img = Image.alpha_composite(img, star)

    out = os.path.join(MEDIA, "icon.png")
    img.save(out)
    print("  OK  icon      -> %s" % os.path.basename(out))
    return out


def main():
    ensure_media()
    sc.ensure_pillow()
    print("[gen_media] 生成缩略图 %s" % MEDIA)
    make_thumbs()
    make_icon()
    print("[gen_media] 完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
