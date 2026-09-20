# -*- coding: utf-8 -*-
"""
原神 CP 壁纸套件 8 —— 命令行

本套件有三张素材(胡桃、芙宁娜), 每张三种摆法, 共 9 种壁纸:

  genshen-cp8                 # 默认: single1 卡片式(模糊背景 + 居中圆角卡片)
  genshen-cp8 cover           # 满屏: cover 裁切铺满整屏, 无边框
  genshen-cp8 showall         # 完整: 等比放进纯色底, 一个像素都不裁
  genshen-cp8 1               # 等价于 single1(兼容按张编号的写法)
  genshen-cp8 list            # 列出所有可切换样式
  genshen-cp8 random          # 随机来一张
  genshen-cp8 all             # 生成全部样式到 ~/.genshen-cp8/wallpapers
  genshen-cp8 all --out DIR   # 生成到指定目录(JetBrains 背景图用)
  genshen-cp8 cycle 30        # 每 30 分钟自动随机换壁纸
  genshen-cp8 switcher        # 打开可视化切换器
  genshen-cp8 pet             # 启动桌面桌宠
  genshen-cp8 deepking        # 生成 DeepKing 界面皮肤 + 离线预览
  genshen-cp8 copy            # 只合成不设置
  genshen-cp8 info            # 环境与素材自检
"""
import argparse
import os
import sys
import time

from ..characters import cp8_pair as C
from . import skin_core as sc


def _cmd_apply(args):
    # 位置参数可以是模式名(cover / showall / single1), 也可以是按张编号(1)
    raw = args.mode
    if raw is not None and str(raw).strip().lower() == "cover":
        # 单张套件: `cover` 直接指满屏那张, 而不是「第几张」
        raw = "cover1"
    mode = sc.resolve_mode(raw)
    if getattr(args, "cover", False) and mode.startswith("single"):
        mode = "cover1"
    size = sc.parse_size(args.size) if args.size else None
    out = sc.build(mode, size, force=True)
    print("[%s] 已生成: %s  (%s)" % (C.APP_SLUG, out, sc.mode_label(mode)))
    if args.no_set:
        return 0
    sc.set_wallpaper(out)
    return 0


def _cmd_list(args):
    size = sc.screen_size()
    print("%s  (%dx%d)" % (C.DISPLAY_NAME, size[0], size[1]))
    print("-" * 58)
    for key, label in sc.MODES:
        mark = " *默认" if key == sc.DEFAULT_MODE else ""
        print("  %-9s %s%s" % (key, label, mark))
    print("-" * 58)
    if sc.count() > 1:
        print("  用法: %s <模式名或序号>  |  %s random  |  %s switcher"
              % (C.APP_SLUG, C.APP_SLUG, C.APP_SLUG))
    else:
        print("  用法: %s [card|cover|showall]  |  %s switcher  |  %s pet"
              % (C.APP_SLUG, C.APP_SLUG, C.APP_SLUG))
        print("  说明: 三张素材 x 三种摆法 = 9 种壁纸, 用序号选图、用 single/cover/showall 选摆法。")
    return 0


def _cmd_all(args):
    size = sc.parse_size(args.size) if args.size else None
    rows = sc.build_all(args.out, size)
    print("[%s] 已生成 %d 个样式 尺寸 %dx%d:" % (
        C.APP_SLUG, len(rows), *(size or sc.screen_size())))
    for key, label, path in rows:
        print("  OK  %-9s %-14s %s" % (key, label, path))
    return 0


def _cmd_random(args):
    mode = sc.pick_random()
    size = sc.parse_size(args.size) if args.size else None
    out = sc.build(mode, size, force=True)
    print("[%s] 随机到: %s" % (C.APP_SLUG, sc.mode_label(mode)))
    if args.no_set:
        print("[%s] 已生成: %s" % (C.APP_SLUG, out))
        return 0
    sc.set_wallpaper(out)
    return 0


def _cmd_cycle(args):
    minutes = max(1, int(args.minutes))
    print("[%s] 每 %d 分钟随机换壁纸, Ctrl+C 停止。" % (C.APP_SLUG, minutes))
    try:
        while True:
            mode = sc.pick_random()
            sc.apply(mode)
            time.sleep(minutes * 60)
    except KeyboardInterrupt:
        print("\n[%s] 已停止。" % C.APP_SLUG)
    return 0


def _cmd_copy(args):
    size = sc.parse_size(args.size) if args.size else None
    rows = sc.build_all(args.out, size)
    print("[%s] 已生成 %d 张到 %s (未设置壁纸):" % (
        C.APP_SLUG, len(rows), os.path.abspath(args.out or C.WALLPAPER_DIR)))
    for key, label, path in rows:
        print("  OK  %-9s %s" % (key, path))
    return 0


def _cmd_gui(args, script):
    from . import gui_launch
    return gui_launch(script)


def _cmd_deepking(args):
    from . import deepking_cli
    argv = []
    if getattr(args, "check", False):
        argv.append("--check")
    if getattr(args, "what", False):
        argv.append("--what")
    if getattr(args, "out", None):
        argv += ["--out", args.out]
    return deepking_cli.main(argv)


def _cmd_info(args):
    print("=" * 58)
    print("  " + C.DISPLAY_NAME)
    print("=" * 58)
    print("  版本      : %s" % C.VERSION)
    print("  PyPI 包名 : %s" % C.PACKAGE_NAME)
    print("  仓库      : %s" % C.REPO_URL)
    print("  Python    : %s" % sys.version.split()[0])
    print("  运行目录  : %s" % sc.APP_DIR)
    try:
        print("  素材目录  : %s" % sc.assets_dir())
    except FileNotFoundError as e:
        print("  素材目录  : [缺失] %s" % e)
        return 1
    print("  屏幕尺寸  : %dx%d" % sc.screen_size())
    try:
        import PIL
        print("  Pillow    : %s" % getattr(PIL, "__version__", "?"))
    except ImportError:
        print("  Pillow    : [缺失] 将自动安装")
    print("-" * 58)
    for i, name in enumerate(sc.IMAGE_NAMES, 1):
        p = sc.asset_path(i)
        ok = os.path.exists(p)
        print("  %d. %-8s %s  %s" % (
            i, name, "OK " if ok else "缺失", sc.IMAGE_FILES[i - 1]))
    print("-" * 58)
    return 0


def build_parser():
    ap = argparse.ArgumentParser(
        prog=C.APP_SLUG,
        description="%s —— 单张样式壁纸一键切换" % C.DISPLAY_NAME,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = ap.add_subparsers(dest="cmd")

    def add_common(p):
        p.add_argument("--size", default=None, help="壁纸尺寸, 如 2560x1440(默认取屏幕分辨率)")
        p.add_argument("--no-set", action="store_true", help="只生成, 不设置为系统壁纸")

    p = sub.add_parser("list", help="列出所有可切换样式")
    p.set_defaults(func=_cmd_list)

    p = sub.add_parser("all", help="生成全部样式")
    p.add_argument("--out", default=None, help="输出目录")
    p.add_argument("--size", default=None)
    p.set_defaults(func=_cmd_all)

    # 每一种模式都注册成子命令。
    # argparse 的子命令是"贪婪"的: 一旦注册了子解析器, `genshen-cp8 cover`
    # 会被当成子命令名去匹配, 未知就直接报错。所以下面这些名字全都要显式注册:
    #   * 规范编号名 singleN / coverN / showallN(无编号的 showall 归一成 showall1)
    #   * 裸序号 1..N(等价 singleN)
    #   * 摆法简写 cover / showall / card(作用第 1 张)
    # 用一个注册器统一处理重名, 避免 argparse 抛 "conflicting subparser"。
    _SUFFIX_HELP = {"single": "卡片式(模糊背景 + 居中卡片)",
                    "cover": "满屏(cover 裁切铺满)",
                    "showall": "完整(等比放进纯色底, 不裁切)"}

    def _register(name, mode, help_text):
        """注册子命令; 名字已存在就只更新它指向的模式。"""
        if name in _seen:
            _seen[name].set_defaults(func=_cmd_apply, mode=mode, cover=False)
            return None
        sp = sub.add_parser(name, help=help_text)
        add_common(sp)
        sp.set_defaults(func=_cmd_apply, mode=mode, cover=False)
        _seen[name] = sp
        return sp

    _seen = {}
    for _mode in sc.all_modes():
        _kind = "".join(c for c in _mode if not c.isdigit())
        _num = "".join(c for c in _mode if c.isdigit()) or "1"
        # 无编号的写法归一成编号形式, 让 mode_label() 一定命中 MODES
        _canon = _mode if _mode[-1:].isdigit() else "%s%s" % (_kind, _num)
        _register(_canon,
                  _canon,
                  "第 %s 张 · %s" % (_num, _SUFFIX_HELP.get(_kind, _kind)))

    for _i in range(1, sc.count() + 1):
        _register(str(_i), "single%d" % _i, "第 %d 张 · 卡片式" % _i)

    _register("cover", "cover1", "第 1 张满屏")
    _register("showall", "showall1", "第 1 张完整不裁")
    _register("card", "single1", "第 1 张卡片式(默认)")

    p = sub.add_parser("random", help="随机换一张")
    add_common(p)
    p.set_defaults(func=_cmd_random)

    p = sub.add_parser("copy", help="只合成不设置")
    p.add_argument("--out", default=None, help="输出目录")
    p.add_argument("--size", default=None)
    p.set_defaults(func=_cmd_copy)

    p = sub.add_parser("cycle", help="定时自动随机换壁纸")
    p.add_argument("minutes", nargs="?", type=int, default=30, help="间隔分钟数, 默认 30")
    p.set_defaults(func=_cmd_cycle)

    p = sub.add_parser("switcher", help="打开可视化切换器")
    p.set_defaults(func=lambda a: _cmd_gui(a, "switcher.py"))

    p = sub.add_parser("pet", help="启动桌面桌宠")
    p.set_defaults(func=lambda a: _cmd_gui(a, "pet.py"))

    p = sub.add_parser("info", help="环境与素材自检")
    p.set_defaults(func=_cmd_info)

    p = sub.add_parser("deepking", help="接入 DeepKing 界面皮肤(生成皮肤 JSON + 预览)")
    p.add_argument("--check", action="store_true", help="只做 DeepKing 转换契约自检")
    p.add_argument("--what", action="store_true", help="显示 DeepKing 会从仓库提取到什么")
    p.add_argument("--out", default=None, help="输出目录")
    p.set_defaults(func=_cmd_deepking)

    # 不再定义位置参数 mode。
    # 之前留了一个 `nargs="?"` 的 mode, 结果 argparse 会用它的默认值(None)
    # 覆盖掉子解析器 set_defaults 设的 mode, 于是 `genshen-cp8 cover2` 反而
    # 走了默认的 single1。现在每一种模式都是独立子命令, 不需要位置参数。
    ap.add_argument("--cover", action="store_true",
                    help="等价于 cover 子命令(第 1 张满屏裁切)")
    ap.add_argument("--size", default=None, help="壁纸尺寸, 如 2560x1440")
    ap.add_argument("--no-set", action="store_true", help="只生成, 不设置为系统壁纸")
    return ap


def main(argv=None):
    sc.prepare_console()
    ap = build_parser()
    args = ap.parse_args(argv)

    if getattr(args, "func", None):
        sc.ensure_pillow()
        sc.ensure_dirs()
        # 每个模式的子命令都通过 set_defaults(mode=...) 自带正确模式名,
        # 父解析器不再有同名位置参数, 所以不会被覆盖。
        try:
            return args.func(args)
        except KeyboardInterrupt:
            return 0
        except Exception as e:
            print("[%s] 出错: %s" % (C.APP_SLUG, e), file=sys.stderr)
            return 1

    # 无子命令: 应用默认壁纸(若带了 --cover 则用第 1 张满屏)
    sc.ensure_pillow()
    sc.ensure_dirs()
    args.mode = "cover1" if getattr(args, "cover", False) else sc.DEFAULT_MODE
    try:
        return _cmd_apply(args)
    except KeyboardInterrupt:
        return 0
    except Exception as e:
        print("[%s] 出错: %s" % (C.APP_SLUG, e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
