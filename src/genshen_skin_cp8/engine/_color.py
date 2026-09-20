# -*- coding: utf-8 -*-
"""
颜色工具 —— 与 DeepKing src/utils/skins.ts 的 darken / lighten / isLightColor 行为一致。

DeepKing 的皮肤调色板里, 不少槽位是在基础色上按比例提亮/压暗派生出来的。
本模块用同样的公式复刻, 保证「本地生成的预览」与「DeepKing 实际转换结果」一致。
"""
import colorsys

# 与 skins.ts 的 HEX 正则等价: #RGB / #RRGGBB / #RRGGBBAA
_HEX_CHARS = set("0123456789abcdefABCDEF")


def is_hex(value):
    """判断是否为 DeepKing 转换器能识别的 # 开头十六进制色值。"""
    if not isinstance(value, str):
        return False
    s = value.strip()
    if not s.startswith("#"):
        return False
    body = s[1:]
    if len(body) not in (3, 4, 6, 8):
        return False
    return all(c in _HEX_CHARS for c in body)


def to_rgb(value):
    """#RGB / #RRGGBB / #RRGGBBAA -> (r, g, b), 0-255。"""
    s = value.strip().lstrip("#")
    if len(s) in (3, 4):
        s = "".join(c * 2 for c in s[:3])
    elif len(s) in (6, 8):
        s = s[:6]
    else:
        raise ValueError("无法解析颜色: %r" % value)
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def to_hex(rgb, alpha=None):
    r, g, b = (max(0, min(255, int(round(c)))) for c in rgb)
    if alpha is None:
        return "#%02x%02x%02x" % (r, g, b)
    return "#%02x%02x%02x%02x" % (r, g, b, max(0, min(255, int(round(alpha * 255)))))


def _hls_adjust(value, amount, lighter):
    """在 HLS 空间按绝对量调整亮度, 对应 skins.ts 的 lighten/darken。"""
    r, g, b = to_rgb(value)
    h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
    l = l + amount if lighter else l - amount
    l = max(0.0, min(1.0, l))
    r2, g2, b2 = colorsys.hls_to_rgb(h, l, s)
    return to_hex((r2 * 255, g2 * 255, b2 * 255))


def lighten(value, amount=0.1):
    return _hls_adjust(value, abs(amount), True)


def darken(value, amount=0.1):
    return _hls_adjust(value, abs(amount), False)


def is_light_color(value):
    """感知亮度 > 0.6 视为浅色(与 skins.ts 的 isLightColor 口径一致)。"""
    r, g, b = to_rgb(value)
    # 相对亮度(ITU-R BT.601), 与前端常用的简化实现一致
    lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
    return lum > 0.6


def best_text_on(value):
    """在给定底色上选一个可读的文字色。"""
    return "#16243a" if is_light_color(value) else "#ffffff"


def mix(a, b, t=0.5):
    """线性混色, t=0 取 a, t=1 取 b。"""
    ra, ga, ba = to_rgb(a)
    rb, gb, bb = to_rgb(b)
    return to_hex((ra + (rb - ra) * t, ga + (gb - ga) * t, ba + (bb - ba) * t))
