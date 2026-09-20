# -*- coding: utf-8 -*-
"""
原神 CP 壁纸套件 8 —— MCP (Model Context Protocol) 服务器

让任意支持 MCP 的 AI 助手直接调用本套件换壁纸:
  * DSH Harness / Claude Code / Kimi Code / CodeX / Cursor / Trae / Windsurf 等

协议: JSON-RPC 2.0 over stdio, 纯标准库实现(不依赖 mcp SDK)。
每次读一行 JSON, 回一行 JSON。

注册示例(任选其一):
  claude mcp add genshen-cp8 -- genshen-cp8-mcp
  # 或写入 .mcp.json / mcp_servers.json:
  {"mcpServers": {"genshen-cp8": {"command": "genshen-cp8-mcp", "args": []}}}

暴露的工具:
  list_wallpapers   列出所有可切换样式
  set_wallpaper     切换到指定样式并设为桌面壁纸
  next_wallpaper    随机换一张
  generate_all      生成全部样式到目录
  wallpaper_info    环境与素材自检
"""
import json
import sys

from ..characters import cp8_pair as C
from . import skin_core as sc

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = C.PACKAGE_NAME
SERVER_VERSION = C.VERSION

TOOLS = [
    {
        "name": "list_wallpapers",
        "description": "列出「%s」所有可切换的壁纸样式(id、名称、说明)。" % C.DISPLAY_NAME,
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "set_wallpaper",
        "description": (
            "把指定样式合成为当前屏幕分辨率并设为系统桌面壁纸。"
            "id 取值见 list_wallpapers: single1(卡片式) / cover1(满屏) / showall(完整不裁)。"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "id": {"type": "string",
                       "description": "样式 id: single1 / cover1 / showall"},
                "size": {"type": "string", "description": "可选, 如 2560x1440, 默认取屏幕分辨率"},
                "set_desktop": {
                    "type": "boolean",
                    "description": "是否真正设为桌面壁纸, 默认 true; false 则只生成文件",
                },
            },
            "required": ["id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "next_wallpaper",
        "description": "随机切换到一张壁纸并设为桌面壁纸。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "set_desktop": {"type": "boolean", "description": "是否设为桌面壁纸, 默认 true"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "generate_all",
        "description": "生成全部样式到指定目录(适合做 JetBrains 背景图素材)。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "out_dir": {"type": "string", "description": "输出目录, 默认 ~/.genshen-cp8/wallpapers"},
                "size": {"type": "string", "description": "可选, 如 2560x1440"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "wallpaper_info",
        "description": "环境自检: 版本、素材路径、屏幕分辨率、Pillow 状态、可切换样式。",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]


def _ok_text(text):
    return {"content": [{"type": "text", "text": text}]}


def _err_text(text):
    return {"content": [{"type": "text", "text": text}], "isError": True}


def _size_of(args):
    s = (args or {}).get("size")
    return sc.parse_size(s) if s else None


def tool_list_wallpapers(_args):
    lines = ["%s  v%s" % (C.DISPLAY_NAME, C.VERSION), ""]
    for key, label in sc.MODES:
        lines.append("  %-9s %s" % (key, label))
    if sc.count() > 1:
        lines += ["", "提示: 也可用序号 1-%d 指定 single 样式。" % sc.count()]
    else:
        lines += ["", "三张素材 x 三种摆法 = 9 种壁纸。换图用序号, 换摆法用 single/cover/showall 前缀。"]
    return _ok_text("\n".join(lines))


def tool_set_wallpaper(args):
    mode = sc.resolve_mode(args.get("id"))
    size = _size_of(args)
    out = sc.build(mode, size, force=True)
    set_desktop = args.get("set_desktop", True)
    if set_desktop:
        sc.set_wallpaper(out)
    return _ok_text("已切换到「%s」(%s)\n文件: %s\n%s" % (
        sc.mode_label(mode), mode, out,
        "已设为桌面壁纸。" if set_desktop else "仅生成文件, 未改动桌面。"))


def tool_next_wallpaper(args):
    mode = sc.pick_random()
    size = _size_of(args)
    out = sc.build(mode, size, force=True)
    set_desktop = (args or {}).get("set_desktop", True)
    if set_desktop:
        sc.set_wallpaper(out)
    return _ok_text("随机切换到「%s」(%s)\n文件: %s" % (sc.mode_label(mode), mode, out))


def tool_generate_all(args):
    args = args or {}
    size = _size_of(args)
    rows = sc.build_all(args.get("out_dir"), size)
    lines = ["已生成 %d 个样式:" % len(rows)]
    lines += ["  %-9s %s" % (k, p) for k, _l, p in rows]
    return _ok_text("\n".join(lines))


def tool_wallpaper_info(_args):
    lines = ["%s  v%s" % (C.DISPLAY_NAME, C.VERSION),
             "PyPI 包名 : %s" % C.PACKAGE_NAME,
             "仓库      : %s" % C.REPO_URL,
             "运行目录  : %s" % sc.APP_DIR]
    try:
        lines.append("素材目录  : %s" % sc.assets_dir())
    except FileNotFoundError as e:
        lines.append("素材目录  : [缺失] %s" % e)
    try:
        sw, sh = sc.screen_size()
        lines.append("屏幕分辨率: %dx%d" % (sw, sh))
    except Exception as e:
        lines.append("屏幕分辨率: 未知 (%s)" % e)
    try:
        import PIL
        lines.append("Pillow    : %s" % getattr(PIL, "__version__", "?"))
    except ImportError:
        lines.append("Pillow    : 缺失(首次调用时会自动 pip 安装)")
    lines.append("样式      : " + ", ".join(m[0] for m in sc.MODES))
    return _ok_text("\n".join(lines))


HANDLERS = {
    "list_wallpapers": tool_list_wallpapers,
    "set_wallpaper": tool_set_wallpaper,
    "next_wallpaper": tool_next_wallpaper,
    "generate_all": tool_generate_all,
    "wallpaper_info": tool_wallpaper_info,
}


def _handle(msg):
    """处理一条 JSON-RPC 消息, 返回响应 dict 或 None(通知无需响应)。"""
    if not isinstance(msg, dict):
        return None
    mid = msg.get("id")
    method = msg.get("method")
    params = msg.get("params") or {}

    if method == "initialize":
        return {
            "jsonrpc": "2.0", "id": mid,
            "result": {
                "protocolVersion": params.get("protocolVersion", PROTOCOL_VERSION),
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "instructions": (
                    "原神 CP 壁纸套件 8 (胡桃 × 芙宁娜)。"
                    "用户说「换壁纸/换一张/切壁纸」时调用 set_wallpaper 或 next_wallpaper;"
                    "不确定可用样式时先调用 list_wallpapers。"
                ),
            },
        }
    if method in ("notifications/initialized", "initialized"):
        return None
    if method == "ping":
        return {"jsonrpc": "2.0", "id": mid, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        fn = HANDLERS.get(name)
        if fn is None:
            return {
                "jsonrpc": "2.0", "id": mid,
                "error": {"code": -32602, "message": "未知工具: %s" % name},
            }
        try:
            sc.ensure_pillow()
            sc.ensure_dirs()
            return {"jsonrpc": "2.0", "id": mid, "result": fn(args)}
        except Exception as e:
            return {"jsonrpc": "2.0", "id": mid, "result": _err_text("执行失败: %s" % e)}
    if method in ("resources/list",):
        return {"jsonrpc": "2.0", "id": mid, "result": {"resources": []}}
    if method in ("prompts/list",):
        return {"jsonrpc": "2.0", "id": mid, "result": {"prompts": []}}

    if mid is None:
        return None  # 未知通知, 忽略
    return {
        "jsonrpc": "2.0", "id": mid,
        "error": {"code": -32601, "message": "未实现的方法: %s" % method},
    }


def main():
    """stdio 主循环。stdout 只允许输出 JSON-RPC, 日志一律走 stderr。"""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        resp = _handle(msg)
        if resp is None:
            continue
        try:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()
        except Exception as e:
            print("[%s-mcp] 输出失败: %s" % (C.APP_SLUG, e), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
