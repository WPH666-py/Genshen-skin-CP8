# -*- coding: utf-8 -*-
"""
原神 CP 壁纸套件 8 —— 胡桃 × 芙宁娜
三张素材 x 三种摆法(共 9 种壁纸) / 桌面桌宠 / 多 IDE 皮肤 / DeepKing 界面皮肤

    import genshen_skin_cp8 as gs
    gs.build("single1")          # 卡片式(默认), 返回文件路径
    gs.build("cover1")           # 满屏
    gs.build("showall")          # 完整不裁
    gs.set_wallpaper(path)       # 设为系统壁纸

本包与 CP1/CP2/CP3 并列, 命名空间完全隔离:
包名 genshen-skin-cp8 / 命令 genshen-cp8 / 运行时目录 ~/.genshen-cp8,
两个套件可同时安装、各自切换。
"""
from .characters.cp8_pair import (  # noqa: F401
    APP_DIR,
    APP_NAME,
    APP_SLUG,
    DEFAULT_MODE,
    DEEPKING_SKIN_ID,
    DEEPKING_SKIN_NAME,
    DISPLAY_NAME,
    IMAGE_FILES,
    IMAGE_META,
    IMAGE_NAMES,
    MODES,
    PACKAGE_NAME,
    PAIR,
    REPO_NAME,
    REPO_URL,
    SERIES,
    VERSION,
)
from .engine.skin_core import (  # noqa: F401
    asset_path,
    build,
    build_all,
    compose,
    ensure_dirs,
    ensure_pillow,
    mode_label,
    prepare_console,
    screen_size,
    set_wallpaper,
    wallpaper_path,
)

__all__ = [
    "APP_DIR", "APP_NAME", "APP_SLUG", "DEFAULT_MODE",
    "DEEPKING_SKIN_ID", "DEEPKING_SKIN_NAME", "DISPLAY_NAME",
    "IMAGE_FILES", "IMAGE_META", "IMAGE_NAMES", "MODES",
    "PACKAGE_NAME", "PAIR", "REPO_NAME", "REPO_URL", "SERIES", "VERSION",
    "asset_path", "build", "build_all", "compose", "ensure_dirs",
    "ensure_pillow", "mode_label", "prepare_console", "screen_size",
    "set_wallpaper", "wallpaper_path",
]

__version__ = VERSION
