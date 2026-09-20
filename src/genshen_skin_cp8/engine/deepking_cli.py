# -*- coding: utf-8 -*-
"""
原神 CP 壁纸套件 8 —— DeepKing 皮肤命令行

  genshen-cp8 deepking              # 生成皮肤 JSON + 可视化预览, 并打印接入步骤
  genshen-cp8 deepking --check      # 校验仓库是否满足 DeepKing 转换契约
  genshen-cp8 deepking --what       # 只显示 DeepKing 会从仓库里提取到什么
  genshen-cp8 deepking --out DIR    # 指定输出目录
  genshen-cp8 deepking --css        # 额外导出「按 CSS 变量推导」的那一版(与 DeepKing 在线转换一致)
"""
import argparse
import json
import os
import sys

from ..characters import cp8_pair as C
from . import deepking as dk
from . import deepking_skin as ks


def _print_check(root):
    ok, errors, notes = dk.check(root)
    print("=" * 60)
    print("  DeepKing 转换契约自检")
    print("=" * 60)
    print("  结果: %s" % ("通过 ✔" if ok else "不通过 ✘"))
    for e in errors:
        print("  [错误] %s" % e)
    for n in notes:
        print("  [提示] %s" % n)
    print("-" * 60)
    if ok:
        print("  可以把这个地址粘进 DeepKing「设置 → 界面皮肤」:")
        print("    %s" % C.REPO_URL)
    return 0 if ok else 1


def _print_what(root, pip_mode=False):
    print("=" * 60)
    print("  DeepKing 会从本仓库提取到的内容")
    print("=" * 60)
    skin_json = os.path.join(root, "skin.json")
    if os.path.exists(skin_json):
        with open(skin_json, "r", encoding="utf-8") as f:
            meta = json.load(f)
        print("  skin.json")
        print("    name   : %s" % meta.get("name"))
        print("    accent : %s" % meta.get("accent"))
        print("    tagline: %s" % meta.get("tagline"))
    css = dk.find_css(root)
    print("  CSS      : %s" % (os.path.relpath(css, root) if css else "(未找到)"))
    if css:
        with open(css, "r", encoding="utf-8") as f:
            text = f.read()
        lv = dk.extract_vars(text)
        dv = dk.extract_dark_vars(text)
        print("    亮色变量 %d 个, 暗色变量 %d 个" % (len(lv), len(dv)))
        for key in ("bg", "text", "accent", "border"):
            print("    %-7s <- %s" % (key, dk._pick(lv, key) or "(缺失, 将派生)"))
    light_img, dark_img, note = dk.find_mascots(root)
    if light_img:
        print("  吉祥物   : %s" % os.path.relpath(light_img, root))
        if dark_img and dark_img != light_img:
            print("             暗色用 %s" % os.path.relpath(dark_img, root))
    elif pip_mode:
        print("  吉祥物   : (pip 形态无仓库文件, 导出时会内联包内插画)")
    else:
        print("  吉祥物   : (未找到)")
    print()
    print("  注意: 在线转换的「亮色」精确取自上面的 CSS 变量;")
    print("        「暗色」由 DeepKing 内置算法从亮色派生(偏中性)。")
    print("        想要逐槽位校色、保留夜景蓝紫的版本, 用本命令导出的 skin JSON。")
    return 0


def _write_outputs(root, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    rel = lambda p: os.path.relpath(p, root).replace("\\", "/") if p else None  # noqa: E731

    # 吉祥物地址的取法分两种形态:
    #   仓库形态 —— 用 raw URL, DeepKing 从 GitHub 拉取;
    #   pip 形态 —— 本机没有仓库, 但素材已打进 wheel, 直接内联成 data URI,
    #               这样导出的 skin JSON 完全自包含, 不依赖任何网络。
    pip_mode = not dk.is_repo_checkout()
    if pip_mode:
        # 素材已打进 wheel: 直接取包内插画内联成 data URI, 生成的 skin JSON 完全自包含。
        # 找不到才退回仓库里的公开 raw 地址(需联网)。
        light_url = dark_url = None
        try:
            from . import skin_core as _sc
            picks = []
            for i in range(1, _sc.count() + 1):
                p = _sc.asset_path(i)
                if os.path.exists(p):
                    picks.append(p)
            if picks:
                # 亮/暗用同一张, 保证水印角色一致(包内只有壁纸插画, 没有专门的
                # 亮暗水印; 仓库形态才用 mascot-*-light/dark 两张)
                light_url = dark_url = dk._data_uri(picks[0])
        except Exception:
            pass
        if not light_url:
            light_url = dk.raw_url(C.DEEPKING_MASCOT_LIGHT)
            dark_url = dk.raw_url(C.DEEPKING_MASCOT_DARK)
    else:
        light_img, dark_img, _ = dk.find_mascots(root)
        light_url = dk.raw_url(rel(light_img)) if light_img else None
        dark_url = dk.raw_url(rel(dark_img)) if dark_img else None

    written = []

    # 1) 手工校色版(推荐)
    curated = ks.definition(light_url, dark_url, C.REPO_URL)
    p1 = os.path.join(out_dir, "%s.skin.json" % C.APP_SLUG)
    with open(p1, "w", encoding="utf-8") as f:
        json.dump(curated, f, ensure_ascii=False, indent=2)
    written.append(("手工校色版 SkinDefinition", p1))

    # 2) 可视化预览(手工校色版, 图片已内联)
    p2 = os.path.join(out_dir, "%s-preview.html" % C.APP_SLUG)
    with open(p2, "w", encoding="utf-8") as f:
        f.write(dk.preview_html(curated))
    written.append(("可视化预览(离线, 双击打开)", p2))

    # 3) 按 CSS 推导版(与 DeepKing 在线转换同口径, 便于对照)
    derived, warns = dk.convert(root)
    p3 = os.path.join(out_dir, "%s.derived.skin.json" % C.APP_SLUG)
    with open(p3, "w", encoding="utf-8") as f:
        json.dump(derived, f, ensure_ascii=False, indent=2)
    written.append(("CSS 推导版(对照用)", p3))
    return written, derived, warns


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog=C.APP_SLUG + " deepking",
        description="接入 DeepKing 界面皮肤系统",
    )
    ap.add_argument("--check", action="store_true", help="只做契约自检")
    ap.add_argument("--what", action="store_true", help="显示 DeepKing 会提取到什么")
    ap.add_argument("--out", default=None, help="输出目录(默认 ~/.genshen-cp8/deepking)")
    args = ap.parse_args(argv)

    root = dk.repo_root()
    pip_mode = root is None
    if pip_mode:
        # pip 安装形态: 仓库文件不在本机, 但仍然能离线生成(用包内兜底配色),
        # 且 DeepKing 在线转换照样能用 —— 它抓的是 GitHub 上的仓库, 不是本地。
        root = dk.api_root()

    if args.check:
        if pip_mode:
            print("[%s] 当前是 pip 安装形态, 本机没有仓库文件可校验。" % C.APP_SLUG)
            print("  在线转换契约可以直接验证(DeepKing 抓的是 GitHub):")
            print("    %s" % C.REPO_URL)
            print("  想跑完整自检请克隆仓库后在仓库目录里执行:")
            print("    git clone %s.git && cd %s && %s deepking --check"
                  % (C.REPO_URL, C.REPO_NAME, C.APP_SLUG))
            return 0
        return _print_check(root)
    if args.what:
        return _print_what(root, pip_mode)

    # 手工校色版自检
    problems = ks.validate()
    if problems:
        print("[%s] 皮肤调色板自检未通过:" % C.APP_SLUG)
        for p in problems:
            print("  - %s" % p)
        return 1

    out_dir = args.out or os.path.join(C.APP_DIR, "deepking")
    written, derived, warns = _write_outputs(root, out_dir)

    print("=" * 60)
    print("  %s —— DeepKing 皮肤已生成" % C.DISPLAY_NAME)
    print("=" * 60)
    for label, path in written:
        print("  %-28s %s" % (label, path))
    print("-" * 60)
    print("  两块调色板: 亮色 bg=%s / 暗色 bg=%s (%d 槽位)"
          % (ks.LIGHT["bg"], ks.DARK["bg"], len(ks.PALETTE_SLOTS)))
    light_img, dark_img, _ = dk.find_mascots(root)
    if light_img:
        mascot_note = os.path.basename(light_img)
    elif pip_mode:
        mascot_note = "已内联包内插画(pip 形态, 无仓库文件)"
    else:
        mascot_note = "无"
    print("  吉祥物    : %s" % mascot_note)
    if warns:
        for w in warns:
            print("  [提示] %s" % w)
    print("-" * 60)
    print("  接入 DeepKing 的两种方式:")
    print()
    print("  A) 在线转换(最快) —— DeepKing「设置 → 界面皮肤」粘贴:")
    print("       %s" % C.REPO_URL)
    print("     拉取 skin.json + CSS 变量自动生成; 亮色精确, 暗色由内置算法派生。")
    print()
    print("  B) 导入手工校色版(推荐, 暗色保留夜景蓝紫) —— 用上面生成的:")
    print("       %s" % written[0][1])
    print("     先双击预览确认效果: %s" % written[1][1])
    print()
    print("  两者只影响 DeepKing 的界面配色, 与桌面壁纸互不干扰。")
    print("  桌面壁纸请用: %s <样式>" % C.APP_SLUG)
    return 0


if __name__ == "__main__":
    sys.exit(main())
