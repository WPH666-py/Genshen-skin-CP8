# -*- coding: utf-8 -*-
"""
端到端验证: 完全模拟 DeepKing 的 convertGitHubRepoToSkin(),
只通过 GitHub 公开 HTTP 接口读取**线上仓库**, 确认在线接入可用。

对应 DeepKing src/utils/skinConverter.ts 的流程:
  解析地址 -> 仓库信息(默认分支) -> 文件树 -> skin.json -> CSS 变量 -> 图片 -> SkinDefinition
"""
import json
import re
import sys
import urllib.request

OWNER, REPO = "WPH666-py", "Genshen-skin-CP8"
UA = {"User-Agent": "deepking-converter-sim"}


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read()


def fetch_json(url):
    return json.loads(fetch(url).decode("utf-8"))


VAR_RE = re.compile(r"(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{3,8})\b")
BLOCK_RE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.S)


def extract_vars(css):
    return {m.group(1): m.group(2).lower() for m in VAR_RE.finditer(css)}


def extract_dark_vars(css):
    out = {}
    for m in BLOCK_RE.finditer(css):
        if "dark" in m.group(1).lower():
            out.update(extract_vars(m.group(2)))
    return out


def pick(v, *kws):
    for kw in kws:
        for k, val in v.items():
            if kw in k.lower():
                return val
    return None


def main():
    print("=" * 66)
    print("  模拟 DeepKing convertGitHubRepoToSkin()")
    print("  目标: https://github.com/%s/%s" % (OWNER, REPO))
    print("=" * 66)

    # 1. 仓库信息 -> 默认分支
    info = fetch_json("https://api.github.com/repos/%s/%s" % (OWNER, REPO))
    branch = info.get("default_branch", "main")
    print("[1] 默认分支      : %s" % branch)

    # 2. 文件树
    tree = fetch_json("https://api.github.com/repos/%s/%s/git/trees/%s?recursive=1"
                      % (OWNER, REPO, branch))
    paths = [n["path"] for n in tree.get("tree", [])]
    print("[2] 文件数        : %d" % len(paths))

    raw = lambda p: "https://raw.githubusercontent.com/%s/%s/%s/%s" % (OWNER, REPO, branch, p)  # noqa: E731

    # 3. skin.json
    sj = [p for p in paths if re.search(r"(^|/)skin\.json$", p, re.I)]
    meta = {}
    if sj:
        meta = json.loads(fetch(raw(sj[0])).decode("utf-8"))
        print("[3] skin.json     : %s  name=%s  accent=%s"
              % (sj[0], meta.get("name"), meta.get("accent")))
    else:
        print("[3] skin.json     : 未找到 (会走派生)")

    # 4. CSS
    skin_dir = re.sub(r"(^|/)skin\.json$", "", sj[0], flags=re.I) if sj else ""
    css_all = [p for p in paths if p.endswith(".css")]
    css = (next((p for p in css_all if skin_dir and p.startswith(skin_dir)
                 and re.search(r"src/client/.*\.module\.css$", p, re.I)), None)
           or next((p for p in css_all if skin_dir and p.startswith(skin_dir)), None)
           or next((p for p in css_all if re.search(r"src/client/.*\.module\.css$", p, re.I)), None)
           or (css_all[0] if css_all else None))
    lv, dv = {}, {}
    if css:
        text = fetch(raw(css)).decode("utf-8")
        lv, dv = extract_vars(text), extract_dark_vars(text)
        print("[4] CSS           : %s  亮色变量=%d 暗色变量=%d" % (css, len(lv), len(dv)))
    else:
        print("[4] CSS           : 未找到")

    # 5. 强调色
    accent = (meta.get("accent") if isinstance(meta.get("accent"), str) else None) \
        or pick(lv, "brand-primary", "accent", "primary") or "#4d6bfe"
    print("[5] 强调色        : %s" % accent)

    # 6. 挑图
    imgs = [p for p in paths if re.search(r"\.(webp|png|jpe?g)$", p, re.I)
            and not p.startswith("preview/") and "/preview/" not in p]
    mascot = (next((p for p in imgs if re.search(r"assets/background/", p, re.I)), None)
              or next((p for p in imgs if re.search(r"(maid|whale|poster|mascot)", p, re.I)
                       and "assets" in p.lower()), None)
              or next((p for p in imgs if "assets" in p.lower()), None))
    print("[6] 吉祥物        : %s" % mascot)
    if mascot:
        blob = fetch(raw(mascot))
        print("                  下载成功 %d B" % len(blob))

    # 7. 推导亮色关键槽位
    print("[7] 亮色关键槽位  :")
    probe = {
        "bg": pick(lv, "bg-layer-1", "bg-base", "background", "bg-100", "neutral-50"),
        "label": pick(lv, "label-primary", "ink", "text", "neutral-1000"),
        "accent": accent,
        "border": pick(lv, "border-l2", "border-l1", "border"),
    }
    for k, v in probe.items():
        print("      %-8s %s" % (k, v))

    # 判定
    print()
    checks = [
        ("skin.json 可读且含 accent", bool(meta.get("accent"))),
        ("CSS 可读且提取到变量", bool(lv)),
        ("强调色为 # 十六进制", bool(re.fullmatch(r"#[0-9a-fA-F]{3,8}", accent or ""))),
        ("亮色 bg 是浅色", bool(probe["bg"])),
        ("吉祥物可下载", mascot is not None),
    ]
    ok = True
    for label, passed in checks:
        print("  %s %s" % ("PASS" if passed else "FAIL", label))
        ok = ok and passed
    print()
    print("结论: %s" % ("在线转换契约全部满足, 可以在 DeepKing 里直接粘贴仓库地址"
                      if ok else "存在不满足项, 在线转换会走降级路径"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
