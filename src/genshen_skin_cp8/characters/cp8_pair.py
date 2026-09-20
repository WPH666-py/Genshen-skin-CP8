# -*- coding: utf-8 -*-
"""
原神 CP 壁纸套件 8 —— 胡桃 × 芙宁娜 · 角色与素材定义

这是**唯一需要为本套件改动的文件**。引擎(engine/)与各 CLI/IDE 适配层全部
读取本文件里的常量, 因此把本文件换成别的角色组合, 整套工具即刻复用。

本套件有**三张素材**(往生堂 × 枫丹廷: 女仆装、居家便装、节日和服), 每张三种摆法:

    single1..3   卡片式  模糊填充背景 + 居中圆角卡片, 构图完整不裁切
    cover1..3    满屏    cover 铺满整屏, 无边框
    showall1..3  完整    contain 等比放进纯色底, 保证一个像素都不裁

与 CP1~CP7 的命名空间完全隔离: 包名 / 命令前缀 / 运行时目录 /
vscode 扩展 ID / DeepKing 皮肤 id 均不冲突, 八个套件可以同时安装。
"""

# ---------------------------------------------------------------- 身份
VERSION = "0.1.0"
PACKAGE_NAME = "genshen-skin-cp8"        # PyPI 分发包名
APP_SLUG = "genshen-cp8"                 # 命令前缀 / 运行时目录名
APP_NAME = "原神CP8"
DISPLAY_NAME = "原神 CP 壁纸套件 8 · 胡桃 × 芙宁娜"
REPO_NAME = "Genshen-skin-CP8"
REPO_URL = "https://github.com/WPH666-py/Genshen-skin-CP8"

# 与其它套件并列展示用
SERIES = "CP8"
PAIR = "胡桃 × 芙宁娜"

# ---------------------------------------------------------------- 运行时目录
# 生成物一律放这里, 不改动仓库/安装目录
import os as _os

APP_DIR = _os.path.join(_os.path.expanduser("~"), "." + APP_SLUG)
WALLPAPER_DIR = _os.path.join(APP_DIR, "wallpapers")
CACHE_DIR = _os.path.join(APP_DIR, "cache")

# 素材目录: 引擎包数据(engine/assets), 由 engine.skin_core 解析
ASSETS_DIR = ""

# ---------------------------------------------------------------- 素材
# 三张插画, 比例各异(竖 / 竖 / 横)。
IMAGE_FILES = ["01-maid.jpg", "02-home.jpg", "03-festival.jpg"]
IMAGE_NAMES = ["女仆", "居家", "节日"]

# 每张素材的说明(画廊/README 用), 键为 IMAGE_FILES 中的文件名
#   pet_crop   桌宠取景: (中心x比例, 中心y比例, 半边长占最短边比例)
#   cover_bias 满屏取景偏向, 用于避免裁到脸
IMAGE_META = {
    "01-maid.jpg": {
        "title": "女仆",
        "desc": "拱门里的双人女仆装合影: 胡桃比着剪刀手眨眼, 芙宁娜红着脸比耶, "
                "背景是庭院栏杆与绿叶",
        # 1242x1801 竖图(0.690), 两人头在上三分之一, 取景窗上移
        "pet_crop": (0.50, 0.32, 0.30),
        "cover_bias": (0.50, 0.30),
    },
    "02-home.jpg": {
        "title": "居家",
        "desc": "窗边床上的居家便装: 胡桃红衫格裙, 芙宁娜蓝衫黑裙, 两人挨着坐",
        # 1080x1440 竖图(0.750)
        "pet_crop": (0.50, 0.34, 0.32),
        "cover_bias": (0.50, 0.34),
    },
    "03-festival.jpg": {
        "title": "节日",
        "desc": "灯火与烟花下的夜景: 胡桃着朱红和服比耶, 芙宁娜拿糖葫芦, "
                "背景是满屏孔明灯与烟花",
        # 1080x672 横图(1.607), 与 16:9 接近, 几乎不需要裁
        "pet_crop": (0.55, 0.50, 0.38),
        "cover_bias": (0.50, 0.50),
    },
}


# ---------------------------------------------------------------- 布局
# 三张素材 × 三种摆法。MODES 由上面的清单自动推导, 不用手写。
def _build_modes():
    """按 IMAGE_NAMES 自动生成 卡片/满屏/完整 三组模式。"""
    out = []
    for suffix, label in (("single", "卡片"), ("cover", "满屏"), ("showall", "完整")):
        for i, name in enumerate(IMAGE_NAMES):
            out.append(("%s%d" % (suffix, i + 1), "%s · %s" % (name, label)))
    return out


MODES = _build_modes()
DEFAULT_MODE = "single1"

# ---------------------------------------------------------------- DeepKing 皮肤
DEEPKING_SKIN_ID = "genshen-cp8-hutao-furina"
DEEPKING_SKIN_NAME = "原神CP8 · 胡桃×芙宁娜"
DEEPKING_SKIN_DESC = (
    "往生堂 × 枫丹廷: 主色取自插画采样 —— 胡桃的赤褐与朱红, 对撞芙宁娜的冰蓝与霜白。"
    "亮色为宣纸暖白, 夜景为墨蓝夜色。32 槽位逐项校色。"
)
# DeepKing 转换器只认 assets/background/ 下的图片作为编辑区水印
DEEPKING_MASCOT_LIGHT = "assets/background/mascot-cp8-light.jpg"
DEEPKING_MASCOT_DARK = "assets/background/mascot-cp8-dark.jpg"
