# -*- coding: utf-8 -*-
"""
原神 CP 壁纸套件 8 —— 自动安装器

  genshen-cp8-install                 # 自动: 装依赖 -> 生成壁纸 -> 设为桌面 -> 注册已装 IDE
  genshen-cp8-install --no-wallpaper  # 只做 IDE 注册, 不动桌面壁纸
  genshen-cp8-install --only vscode   # 只处理指定目标

覆盖目标:
  vscode / trae / codex / cursor / windsurf / vscodium  —— VSCode 系扩展
  jetbrains (PyCharm/IDEA/WebStorm)                     —— 生成背景图素材 + 指引
  claudecode / kimicode / harness / deepking            —— 注册 MCP 服务器
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys

from ..characters import cp8_pair as C
from . import skin_core as sc

MCP_KEY = C.APP_SLUG
MCP_COMMAND = C.APP_SLUG + "-mcp"

# ---------------------------------------------------------------- 小工具


def say(msg):
    print(msg)


def have(cmd):
    return shutil.which(cmd) is not None


def _run(cmd, **kw):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=180, **kw)
    except Exception as e:
        return subprocess.CompletedProcess(cmd, 1, "", str(e))


def home(*parts):
    return os.path.join(os.path.expanduser("~"), *parts)


def appdata(*parts):
    base = os.environ.get("APPDATA") or home("AppData", "Roaming")
    return os.path.join(base, *parts)


def localappdata(*parts):
    base = os.environ.get("LOCALAPPDATA") or home("AppData", "Local")
    return os.path.join(base, *parts)


def read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


# ---------------------------------------------------------------- MCP 注册

def mcp_stdio_entry():
    """MCP 服务器定义。用 <python> -m 形式最稳, 不依赖 PATH 里的脚本。"""
    return {
        "command": sys.executable,
        "args": ["-m", "genshen_skin_cp8.mcp_server"],
        "env": {},
    }


def register_mcp_json(path, label):
    """向 {"mcpServers": {...}} 形式的配置文件注册 MCP 服务器。"""
    data = read_json(path)
    if data is None:
        if os.path.exists(path):
            return "跳过(配置文件无法解析): %s" % path
        data = {}
    servers = data.setdefault("mcpServers", {})
    servers[MCP_KEY] = mcp_stdio_entry()
    write_json(path, data)
    return "已注册 %s -> %s" % (label, path)


def detect_mcp_targets():
    """返回 [(label, path, kind)] —— kind: 'json' | 'cli'"""
    targets = []

    # 1) 通用: 仓库/工作目录下的 .mcp.json
    targets.append(("通用 .mcp.json (当前目录)", os.path.join(os.getcwd(), ".mcp.json"), "json"))

    # 2) Claude Code  (用户级 ~/.claude.json, 以及 ~/.claude/mcp.json)
    claude_cfg = home(".claude.json")
    if os.path.exists(claude_cfg) or have("claude"):
        targets.append(("Claude Code", claude_cfg, "json"))
    if os.path.isdir(home(".claude")):
        targets.append(("Claude Code", home(".claude", "mcp.json"), "json"))

    # 3) Kimi Code
    for p in (home(".kimi", "mcp.json"), home(".kimicode", "mcp.json"),
              appdata("KimiCode", "mcp.json")):
        if os.path.isdir(os.path.dirname(p)):
            targets.append(("Kimi Code", p, "json"))

    # 4) DSH Harness
    dsh_home = os.environ.get("DSH_HOME") or home(".dsh")
    if os.path.isdir(dsh_home):
        targets.append(("DSH Harness", os.path.join(dsh_home, "mcp.json"), "json"))

    # 5) DeepKing
    for p in (appdata("DeepKing", "mcp.json"), home(".deepking", "mcp.json"),
              home("DeepKing", "mcp.json")):
        if os.path.isdir(os.path.dirname(p)):
            targets.append(("DeepKing", p, "json"))

    # 去重
    seen, out = set(), []
    for label, path, kind in targets:
        key = os.path.normcase(os.path.abspath(path))
        if key in seen:
            continue
        seen.add(key)
        out.append((label, path, kind))
    return out


def do_mcp(verbose=True):
    results = []
    for label, path, _kind in detect_mcp_targets():
        try:
            results.append(register_mcp_json(path, label))
        except Exception as e:
            results.append("失败 %s: %s" % (label, e))
    if verbose:
        for r in results:
            say("  " + r)
    return results


# ---------------------------------------------------------------- VSCode 系

VSCODE_FAMILY = {
    "vscode": ("code", ("Code",), "VSCode"),
    "trae": ("trae", ("Trae",), "Trae"),
    "codex": ("codex", ("CodeX", "Codex"), "CodeX"),
    "cursor": ("cursor", ("Cursor",), "Cursor"),
    "windsurf": ("windsurf", ("Windsurf",), "Windsurf"),
    "vscodium": ("codium", ("VSCodium",), "VSCodium"),
}


def find_vsix():
    """定位已打包的 vsix(优先包内, 其次仓库 vscode/)。"""
    here = os.path.dirname(os.path.abspath(__file__))
    cands = []
    for base in (os.path.dirname(os.path.dirname(here)),  # repo/vscode
                 os.path.join(os.path.dirname(here), "vscode"),
                 here):
        cands += glob.glob(os.path.join(base, "vscode", "*.vsix"))
        cands += glob.glob(os.path.join(base, "*.vsix"))
    for p in cands:
        if os.path.exists(p):
            return p
    return None


def install_vscode_extension(cli, label, vsix, verbose=True):
    if not have(cli):
        return "%s: 未找到命令 %s, 跳过" % (label, cli)
    if not vsix:
        return "%s: 未找到 .vsix 包, 跳过(可手动扩展面板安装)" % label
    r = _run([cli, "--install-extension", vsix, "--force"])
    if r.returncode == 0:
        return "%s: 已安装扩展 %s" % (label, os.path.basename(vsix))
    return "%s: 安装失败 %s" % (label, (r.stderr or r.stdout or "").strip()[:200])


def do_vscode_family(only=None, verbose=True):
    vsix = find_vsix()
    out = []
    for key, (cli, _dirs, label) in VSCODE_FAMILY.items():
        if only and key not in only:
            continue
        if not have(cli) and not only:
            continue
        out.append(install_vscode_extension(cli, label, vsix, verbose))
    if verbose:
        if not out:
            say("  未检测到 VSCode 系命令行工具 (code / trae / codex / cursor ...)")
        for r in out:
            say("  " + r)
    return out


# ---------------------------------------------------------------- JetBrains

JB_DIRS_WIN = [
    ("JetBrains", "PyCharm*"), ("JetBrains", "IntelliJ*"), ("JetBrains", "WebStorm*"),
    ("JetBrains", "GoLand*"), ("JetBrains", "CLion*"), ("JetBrains", "Rider*"),
]


def detect_jetbrains():
    found = []
    if os.name == "nt":
        for parent, pat in JB_DIRS_WIN:
            found += glob.glob(appdata(parent, pat))
            found += glob.glob(localappdata("JetBrains", pat))
    else:
        found += glob.glob(home(".config", "JetBrains", "*"))
        found += glob.glob(home("Library", "Application Support", "JetBrains", "*"))
    return sorted({os.path.basename(p).rstrip("/\\") for p in found})


def do_jetbrains(verbose=True):
    found = detect_jetbrains()
    out_dir = home("GenshinCP1-Backgrounds")
    rows = sc.build_all(out_dir)
    if verbose:
        if found:
            say("  检测到 JetBrains IDE: " + ", ".join(found))
        else:
            say("  未检测到 JetBrains IDE 安装目录")
        say("  已生成背景图素材 %d 张 -> %s" % (len(rows), out_dir))
        say("  手动启用: Settings -> Appearance & Behavior -> Appearance -> Background Image")
        say("            点 + 选择上面的图片 (推荐 single1 / cover1)")
    return rows


# ---------------------------------------------------------------- DeepKing

def detect_deepking():
    """探测 DeepKing / Deep-IDE 的安装痕迹与数据目录。"""
    found = []
    pats = [
        localappdata("Programs", "DeepKing*"),
        localappdata("DeepKing*"),
        appdata("DeepKing*"),
        appdata("com.deepking*"),
        home(".deepking"),
        localappdata("Programs", "Deep-IDE*"),
        localappdata("com.deepide*"),
    ]
    if os.name == "nt":
        for root in (localappdata(), appdata()):
            for pat in ("DeepKing*", "Deep-IDE*", "com.deepking*", "com.deepide*"):
                found += glob.glob(os.path.join(root, pat))
    for p in pats:
        found += glob.glob(p)
    return sorted({p.rstrip("/\\") for p in found})


def do_deepking(verbose=True):
    """生成 DeepKing 皮肤文件, 并打印两种接入方式。"""
    from . import deepking as dk
    from . import deepking_skin as ks

    root = dk.repo_root()
    if not root:
        if verbose:
            say("  未找到仓库根目录(含 skin.json), 跳过离线皮肤生成。")
            say("  仍可在 DeepKing「设置 → 界面皮肤」直接粘贴: %s" % C.REPO_URL)
        return None

    problems = ks.validate()
    if problems:
        if verbose:
            say("  皮肤调色板自检未通过, 已跳过:")
            for p in problems:
                say("    - %s" % p)
        return None

    out_dir = os.path.join(C.APP_DIR, "deepking")
    os.makedirs(out_dir, exist_ok=True)
    light_img, dark_img, _ = dk.find_mascots(root)
    rel = lambda p: os.path.relpath(p, root).replace("\\", "/") if p else None  # noqa: E731
    curated = ks.definition(
        dk.raw_url(rel(light_img)) if light_img else None,
        dk.raw_url(rel(dark_img)) if dark_img else None,
        C.REPO_URL,
    )
    skin_path = os.path.join(out_dir, "%s.skin.json" % C.APP_SLUG)
    with open(skin_path, "w", encoding="utf-8") as f:
        json.dump(curated, f, ensure_ascii=False, indent=2)
    preview_path = os.path.join(out_dir, "%s-preview.html" % C.APP_SLUG)
    with open(preview_path, "w", encoding="utf-8") as f:
        f.write(dk.preview_html(curated))

    installed = detect_deepking()
    if verbose:
        if installed:
            say("  检测到 DeepKing 相关目录: " + ", ".join(os.path.basename(p) for p in installed))
        else:
            say("  未检测到 DeepKing 安装目录(不影响: 皮肤在软件内导入)")
        say("  已生成 DeepKing 皮肤:")
        say("    %s" % skin_path)
        say("    预览: %s" % preview_path)
        say("  接入方式 A(在线): DeepKing「设置 → 界面皮肤」粘贴 %s" % C.REPO_URL)
        say("  接入方式 B(离线, 暗色保留夜景蓝紫): 用上面生成的 skin JSON")
    return {"skin": skin_path, "preview": preview_path}


# ---------------------------------------------------------------- 主流程


def main(argv=None):
    sc.prepare_console()
    ap = argparse.ArgumentParser(
        prog=C.APP_SLUG + "-install",
        description="%s —— 自动安装器" % C.DISPLAY_NAME,
    )
    ap.add_argument("--no-wallpaper", action="store_true", help="不改动桌面壁纸")
    ap.add_argument("--no-ide", action="store_true", help="不注册 IDE 扩展/MCP")
    ap.add_argument("--only", nargs="*", default=None,
                    help="只处理指定目标: vscode trae codex cursor jetbrains mcp deepking")
    ap.add_argument("--size", default=None, help="壁纸尺寸, 如 2560x1440")
    args = ap.parse_args(argv)

    only = set(args.only) if args.only else None
    want = lambda k: only is None or k in only  # noqa: E731

    say("=" * 62)
    say("  " + C.DISPLAY_NAME)
    say("  v%s   %s" % (C.VERSION, C.REPO_URL))
    say("=" * 62)

    say("[1/4] 检查依赖 ...")
    sc.ensure_pillow()
    sc.ensure_dirs()
    try:
        say("      素材目录: %s" % sc.assets_dir())
    except FileNotFoundError as e:
        say("      素材缺失: %s" % e)
        return 1

    size = sc.parse_size(args.size) if args.size else sc.screen_size()
    say("[2/4] 生成默认壁纸 (%dx%d) ..." % size)
    out = sc.build(sc.DEFAULT_MODE, size, force=True)
    say("      -> %s" % out)

    if args.no_wallpaper:
        say("[3/4] 已按 --no-wallpaper 跳过设置桌面。")
    else:
        say("[3/4] 设置为系统壁纸 ...")
        try:
            sc.set_wallpaper(out)
        except Exception as e:
            say("      设置失败(可手动选择上面的文件): %s" % e)

    if args.no_ide:
        say("[4/4] 已按 --no-ide 跳过 IDE 集成。")
    else:
        say("[4/4] 注册 IDE 集成 ...")
        if want("mcp"):
            do_mcp()
        if want("deepking"):
            do_deepking()
        if want("jetbrains"):
            do_jetbrains()
        fam = None
        if only:
            fam = only & set(VSCODE_FAMILY)
            fam = fam or None
            if fam is None and "vscode" in only:
                fam = {"vscode"}
        else:
            fam = None
        if only is None or fam:
            do_vscode_family(fam)

    say("-" * 62)
    say("完成! 常用命令(这张图有三种摆法):")
    say("  %s                卡片式(默认, 模糊背景 + 居中卡片)" % C.APP_SLUG)
    say("  %s cover          满屏, 无边框" % C.APP_SLUG)
    say("  %s showall        完整不裁, 两侧留边" % C.APP_SLUG)
    say("  %s switcher       可视化切换器" % C.APP_SLUG)
    say("  %s pet            桌面桌宠" % C.APP_SLUG)
    say("  %s cycle 30       每 30 分钟自动随机换" % C.APP_SLUG)
    say("-" * 62)
    say("给任意 AI 发仓库链接即可让它替你操作: %s" % C.REPO_URL)
    return 0


if __name__ == "__main__":
    sys.exit(main())
