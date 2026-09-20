# -*- coding: utf-8 -*-
"""
引擎同步工具 —— 让 CP1~CP8 共用同一套皮肤引擎, 不再各改一份。

背景
----
CP1(Genshen-Skin-CP1 · 米提亚×沃雅妮莎)先做出来, 引擎代码直接放在
`src/genshin_skin_cp1/` 里; CP2 起把通用逻辑抽到 `src/genshen_skin_cp2/engine/`,
角色数据放 `src/genshen_skin_cp2/characters/`; CP3 沿用同样的两层结构。
各套件的包名/目录不同, 但引擎文件本该一致, 否则修一个 bug 要改三处。

用法
----
    python tools/sync_engine.py --check                 # 报告各套件之间的差异
    python tools/sync_engine.py --to CP1 --dry-run      # 看会把 CP2 的引擎盖到 CP1 哪些文件
    python tools/sync_engine.py --to CP1                # 实际同步(会先备份 *.bak)
    python tools/sync_engine.py --from CP2 --to CP3     # 指定源与目标

注意
----
* 只同步**引擎**文件; 角色数据(characters/、config.py、skin.json、CSS、素材)从不同步。
* 默认源是 CP2 —— 它是改动最活跃、且带全部修复的一份(showall 模式、
  repo_root/pkg_root 分离、find_css/find_mascots 收窄、cover_bias)。
* CP1 是扁平结构(常量在 config.py), CP2/CP3 是两层结构(常量在 characters/)。
  normalize() 会自动改写这个导入差异, 两个方向都支持。
"""
import argparse
import difflib
import hashlib
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
# tools/ 在仓库里, 所以工作区还要再往上一层
WORKSPACE = os.path.dirname(os.path.dirname(HERE))

# 引擎文件清单(相对包内 engine/ 目录; CP1 是包根)
ENGINE_FILES = [
    "_color.py",
    "skin_core.py",
    "cli.py",
    "switcher.py",
    "pet.py",
    "mcp_server.py",
    "autoinstall.py",
    "gui_launch.py",
    "deepking.py",
    "deepking_cli.py",
    "deepking_skin.py",
]

# 每个套件: 名字 -> 仓库目录 / 引擎目录 / 角色数据模块 / 包名
PACKS = {
    "CP1": {
        "repo": os.path.join(WORKSPACE, "Genshen-Skin-CP1"),
        "pkg": ("Genshen-Skin-CP1", "src", "genshin_skin_cp1"),
        "flat": True,          # 常量在 config.py, 引擎就在包根
        "slug": "genshin_skin_cp1",
    },
    "CP2": {
        "repo": os.path.join(WORKSPACE, "Genshen-skin-CP2"),
        "pkg": ("Genshen-skin-CP2", "src", "genshen_skin_cp2"),
        "flat": False,
        "slug": "genshen_skin_cp2",
    },
    "CP3": {
        "repo": os.path.join(WORKSPACE, "Genshen-skin-CP3"),
        "pkg": ("Genshen-skin-CP3", "src", "genshen_skin_cp3"),
        "flat": False,
        "slug": "genshen_skin_cp3",
    },
    "CP4": {
        "repo": os.path.join(WORKSPACE, "Genshen-skin-CP4"),
        "pkg": ("Genshen-skin-CP4", "src", "genshen_skin_cp4"),
        "flat": False,
        "slug": "genshen_skin_cp4",
    },
    "CP5": {
        "repo": os.path.join(WORKSPACE, "Genshen-skin-CP5"),
        "pkg": ("Genshen-skin-CP5", "src", "genshen_skin_cp5"),
        "flat": False,
        "slug": "genshen_skin_cp5",
    },
    "CP6": {
        "repo": os.path.join(WORKSPACE, "Genshen-skin-CP6"),
        "pkg": ("Genshen-skin-CP6", "src", "genshen_skin_cp6"),
        "flat": False,
        "slug": "genshen_skin_cp6",
    },
    "CP7": {
        "repo": os.path.join(WORKSPACE, "Genshen-skin-CP7"),
        "pkg": ("Genshen-skin-CP7", "src", "genshen_skin_cp7"),
        "flat": False,
        "slug": "genshen_skin_cp7",
    },
    "CP8": {
        "repo": os.path.join(WORKSPACE, "Genshen-skin-CP8"),
        "pkg": ("Genshen-skin-CP8", "src", "genshen_skin_cp8"),
        "flat": False,
        "slug": "genshen_skin_cp8",
    },
}

# 只有本机真实存在的套件才参与, 缺一个不会报错
AVAILABLE = [k for k, v in PACKS.items() if os.path.isdir(v["repo"])]


def engine_dir(key):
    """引擎文件所在目录: CP1 是包根, CP2~CP8 是包内的 engine/。"""
    v = PACKS[key]
    base = os.path.join(WORKSPACE, *v["pkg"])
    return base if v["flat"] else os.path.join(base, "engine")


def sha(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:12]


def _role_of(key):
    """各套件的角色数据模块名(CP1 没有 characters 包, 返回 None)。"""
    return {"CP2": "odette_voj", "CP3": "cp3_trio",
            "CP4": "cp4_pair", "CP5": "cp5_pair", "CP6": "cp6_trio", "CP7": "cp7_pair",
            "CP8": "cp8_pair"}.get(key)


def _slug_forms(slug, repo_name):
    """一个套件的包名/命令名/仓库名可能出现的全部写法, 长->短排列。

    注意 CP1 的 slug 是 `genshin_skin_cp1`(genshin), 而命令前缀是 `genshin-cp1`
    —— 不能从 slug 拼出命令前缀, 必须用仓库名 `Genshen-Skin-CP1` 来推,
    否则 CP1 的 `genshin-cp1-switcher` 这类字符串永远换不掉。
    """
    short = slug.replace("genshin_", "").replace("genshen_", "")   # skin_cp1
    # 仓库名 Genshen-Skin-CP1 -> 命令前缀 genshen-cp1
    app = repo_name.lower().replace("genshen-skin-", "genshen-") \
                       .replace("genshin-skin-", "genshin-")
    return [
        slug,                             # genshen_skin_cp2
        slug.replace("_", "-"),           # genshen-skin-cp2
        repo_name,                        # Genshen-skin-CP2
        repo_name.lower(),                # genshen-skin-cp2
        slug.replace("skin_", ""),        # genshen_cp2
        short,                            # skin_cp2
        app,                              # genshen-cp2  <- 命令前缀, 最容易漏
    ]


def normalize(text, src_slug, dst_slug, dst_key=None, src_key=None, src_repo=None,
              dst_repo=None):
    """把源套件的包名/命令名换成目标套件的, 使文件内容可直接落盘。

    还要改写「常量模块」的导入, 各套件结构不同:
      CP1: from . import config as C                (常量在 config.py)
      CP2: from ..characters import odette_voj as C (常量在 characters/<角色>.py)
      CP3: from ..characters import cp3_trio as C
      CP4: from ..characters import cp8_pair as C
    dst_key 决定往哪个方向改写; src_key 用于先把源的角色模块名归一化。

    替换按「长 -> 短」顺序进行, 避免短串先把长串切碎。
    """
    out = text
    if src_repo and dst_repo:
        pairs = list(zip(_slug_forms(src_slug, src_repo),
                         _slug_forms(dst_slug, dst_repo)))
    else:
        # 兼容旧调用: 只换包名/命令名的常见几种写法
        src_short = src_slug.replace("genshin_", "").replace("genshen_", "")
        dst_short = dst_slug.replace("genshin_", "").replace("genshen_", "")
        pairs = [
            (src_slug, dst_slug),
            (src_slug.replace("_", "-"), dst_slug.replace("_", "-")),
            (src_short, dst_short),
            (src_short.replace("_", "-"), dst_short.replace("_", "-")),
        ]
    for a, b in pairs:
        if a and a != b:
            out = out.replace(a, b)

    # 中文名与运行时目录: 不是标识符, 但同样随套件变化, 不然 --check 会一直报假漂移
    CN = {
        "CP1": ("原神 CP 壁纸套件 1", "原神CP1", "米提亚 × 沃雅妮莎", "~/.genshin-cp1"),
        "CP2": ("原神 CP 壁纸套件 2", "原神CP2", "奥黛塔 × 沃雅妮莎", "~/.genshen-cp2"),
        "CP3": ("原神 CP 壁纸套件 3", "原神CP3", "胡桃 × 芙宁娜", "~/.genshen-cp3"),
        "CP4": ("原神 CP 壁纸套件 8", "原神CP8", "胡桃 × 芙宁娜", "~/.genshen-cp8"),
    }
    if src_key in CN and dst_key in CN:
        for a, b in zip(CN[src_key], CN[dst_key]):
            if a != b:
                out = out.replace(a, b)
        # 顺序敏感: 先把长的整名换掉, 再换短的
        for a, b in zip(CN[src_key][:2], CN[dst_key][:2]):
            if a != b:
                out = out.replace(a, b)

    # 先把「常量模块导入」统一成占位符, 再按目标形态落回。
    # 注意: 源与目标的角色模块名可能不同(cp8_pair vs odette_voj),
    # 所以这里用正则匹配任意模块名, 而不是写死某一个。
    import re
    CONST_IMPORT = re.compile(r"from \.\.characters import \w+ as C|from \. import config as C")
    CONST_MULTI = re.compile(r"from \.\.characters\.\w+ import \(|from \.config import \(")
    out = CONST_IMPORT.sub("@@CONST_IMPORT@@", out)
    out = CONST_MULTI.sub("@@CONST_IMPORT_MULTI@@@", out)

    if dst_key == "CP1":
        out = out.replace("@@CONST_IMPORT@@", "from . import config as C")
        out = out.replace("@@CONST_IMPORT_MULTI@@@", "from .config import (")
        out = out.replace("from ..engine import _color as col",
                          "from . import _color as col")
    elif dst_key:
        role = _role_of(dst_key) or "odette_voj"
        out = out.replace("@@CONST_IMPORT@@",
                          "from ..characters import %s as C" % role)
        out = out.replace("@@CONST_IMPORT_MULTI@@@",
                          "from ..characters.%s import (" % role)
        out = out.replace("from . import _color as col",
                          "from ..engine import _color as col")
    else:
        out = out.replace("@@CONST_IMPORT@@", "from . import config as C")
        out = out.replace("@@CONST_IMPORT_MULTI@@@", "from .config import (")
    return out


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def sync(src_key, dst_key, dry_run=False, backup=True):
    src_dir, dst_dir = engine_dir(src_key), engine_dir(dst_key)
    src_slug, dst_slug = PACKS[src_key]["slug"], PACKS[dst_key]["slug"]
    changed, same, missing = [], [], []

    for name in ENGINE_FILES:
        sp = os.path.join(src_dir, name)
        dp = os.path.join(dst_dir, name)
        if not os.path.exists(sp):
            missing.append(name)
            continue
        s_text = normalize(read(sp), src_slug, dst_slug, dst_key,
                           src_key=src_key,
                           src_repo=PACKS[src_key]["pkg"][0],
                           dst_repo=PACKS[dst_key]["pkg"][0])
        d_text = read(dp) if os.path.exists(dp) else None
        if d_text == s_text:
            same.append(name)
            continue
        changed.append(name)
        print("  ~ %-20s %s -> %s" % (name, sha(sp) or "(新)", sha(dp) or "(缺失)"))
        if not dry_run:
            if d_text is not None and backup:
                shutil.copy2(dp, dp + ".bak")
            write(dp, s_text)

    print()
    print("  %s -> %s : 改动 %d, 一致 %d, 源缺失 %d"
          % (src_key, dst_key, len(changed), len(same), len(missing)))
    if missing:
        print("  源里没有这些文件, 跳过: %s" % ", ".join(missing))
    return changed


def check():
    """粗略报告各套件引擎的差异 —— **仅供人工参考, 不要当成 CI 断言**。

    局限(踩过的坑): 它只能把「基准套件」的文本按包名/中文名/角色模块名归一化后
    逐字节比对。于是任何**有意**的套件专属改动(例如 CP3 手写过的 CLI 文案、
    CP1 与 CP2 不同的 preview 说明)都会被报成「漂移」, 反之真实漂移也可能被
    归一化规则掩盖。真正判断某处改动该不该同步, 请直接看 diff:

        python tools/sync_engine.py --to CP1 --dry-run

    本工具的价值在于「批量把一份引擎搬到另一套件」, 而不是做一致性门禁。
    """
    if len(AVAILABLE) < 2:
        print("  本机只找到 %s, 无法比对" % (AVAILABLE or "任何套件"))
        return 0
    ref = "CP2" if "CP2" in AVAILABLE else AVAILABLE[0]
    others = [k for k in AVAILABLE if k != ref]
    print("  基准: %s  对比: %s   (仅供参考, 见本函数文档)" % (ref, ", ".join(others)))
    print()
    drift_total = 0
    for other in others:
        ref_dir, oth_dir = engine_dir(ref), engine_dir(other)
        ref_slug, oth_slug = PACKS[ref]["slug"], PACKS[other]["slug"]
        drift = []
        for name in ENGINE_FILES:
            rp, op = os.path.join(ref_dir, name), os.path.join(oth_dir, name)
            if not (os.path.exists(rp) and os.path.exists(op)):
                drift.append((name, "缺失"))
                continue
            norm = normalize(read(rp), ref_slug, oth_slug, other, src_key=ref,
                             src_repo=PACKS[ref]["pkg"][0],
                             dst_repo=PACKS[other]["pkg"][0])
            if read(op) != norm:
                drift.append((name, "★ 有差异"))
        print("  %s:" % other)
        if not drift:
            print("      全部一致")
        else:
            for name, why in drift:
                print("      %-20s %s" % (name, why))
        drift_total += len(drift)
    print()
    print("  共 %d 处差异。其中可能含**有意**的套件专属改动, 请逐个看 diff 再决定是否同步。" % drift_total)
    return drift_total


def main():
    ap = argparse.ArgumentParser(
        description="CP1~CP8 皮肤引擎同步工具(本机存在哪些套件就处理哪些)")
    ap.add_argument("--to", choices=sorted(PACKS), help="目标套件")
    ap.add_argument("--from", dest="src", choices=sorted(PACKS), default=None,
                    help="源套件(默认 CP2 起较新的那份)")
    ap.add_argument("--check", action="store_true", help="只报告各套件差异")
    ap.add_argument("--dry-run", action="store_true", help="只显示将要改动什么")
    args = ap.parse_args()

    if args.check:
        check()
        return 0
    if not args.to:
        ap.error("请用 --to 指定目标套件, 或用 --check 只看差异")
    src = args.src or ("CP2" if "CP2" in AVAILABLE else AVAILABLE[0])
    if args.to == src:
        ap.error("源和目标不能相同")

    print("=== 同步引擎 %s -> %s%s ===" % (src, args.to, "(dry-run)" if args.dry_run else ""))
    changed = sync(src, args.to, dry_run=args.dry_run)
    if changed and not args.dry_run:
        print()
        print("  已写入。原文件备份为 *.bak, 确认无误后请删除。")
        print("  下一步: 重建受影响套件的 wheel / vsix 并推送。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
