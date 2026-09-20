# -*- coding: utf-8 -*-
"""
把本地仓库目录推送到 GitHub(PATH 上没有 git, 所以走 Git Data API)。

  python _push_repo.py <repo_root> <owner/repo> [--message MSG] [--dry-run]

令牌从环境变量 GH_TOKEN 读取, 不落盘、不出现在命令行里。
"""
import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.github.com"

# 不进仓库的东西(构建产物 / 缓存 / 开发脚本)
SKIP_DIRS = {".git", "__pycache__", "build", ".eggs",
             "genshen_skin_cp8.egg-info", "node_modules", ".vscode-test"}
SKIP_SUFFIX = (".pyc", ".pyo", ".bak", ".orig", ".rej")
SKIP_FILES = {".mcp.json"}
SKIP_PREFIX = ("genshen_skin_cp8-",)

TEXT_SUFFIX = (".py", ".md", ".txt", ".json", ".toml", ".css", ".js", ".bat",
               ".sh", ".yaml", ".yml", ".gitignore", ".vscodeignore", ".cfg",
               ".svg", ".html")
TEXT_NAMES = {"LICENSE", ".gitignore", ".vscodeignore"}


def log(msg):
    sys.stdout.write(msg + "\n")
    sys.stdout.flush()


class GH(object):
    def __init__(self, token):
        self.token = token

    def _req(self, method, path, payload=None):
        url = API + path
        data = None
        headers = {
            "Authorization": "token " + self.token,
            "User-Agent": "genshen-cp8-push",
            "Accept": "application/vnd.github+json",
        }
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    body = r.read().decode("utf-8")
                    return json.loads(body) if body else {}
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "replace")[:400]
                if e.code in (502, 503, 504) and attempt < 3:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise RuntimeError("HTTP %s %s %s -> %s" % (method, path, e.code, detail))
            except urllib.error.URLError as e:
                if attempt < 3:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise RuntimeError("网络错误 %s %s -> %s" % (method, path, e))
        return {}

    def get(self, path):
        return self._req("GET", path)

    def post(self, path, payload):
        return self._req("POST", path, payload)


def collect(root):
    """返回 [(相对路径, 绝对路径, 是否文本)]。

    dist/ 里的 wheel 要随仓库发布(便于离线 pip install), sdist 不上传;
    build 期的 genshen_skin_cp8-0.1.0/ 源码副本、__pycache__ 等一律排除。
    """
    out = []
    for base, dirs, files in os.walk(root):
        rel_base = os.path.relpath(base, root).replace(os.sep, "/")
        parts = [] if rel_base == "." else rel_base.split("/")
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith("_")]
        for f in sorted(files):
            if f in SKIP_FILES or f.endswith(SKIP_SUFFIX):
                continue
            if any(p.startswith(pfx) for p in parts for pfx in SKIP_PREFIX):
                continue  # build 期的源码副本目录
            abs_p = os.path.join(base, f)
            rel = os.path.relpath(abs_p, root).replace(os.sep, "/")
            if rel.split("/")[0].startswith("_"):
                continue  # 下划线开头的开发脚本
            # 只放行 dist/ 下的 wheel
            if parts and parts[0] == "dist" and not f.endswith(".whl"):
                continue
            is_text = f.endswith(TEXT_SUFFIX) or f in TEXT_NAMES
            out.append((rel, abs_p, is_text))
    return sorted(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("repo", help="owner/repo")
    ap.add_argument("--message", default="feat: 原神CP壁纸套件2 · 胡桃×芙宁娜")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--branch", default="main")
    args = ap.parse_args()

    token = os.environ.get("GH_TOKEN", "").strip()
    if not token:
        log("缺少环境变量 GH_TOKEN")
        return 2
    gh = GH(token)

    files = collect(args.root)
    total = sum(os.path.getsize(p) for _r, p, _t in files)
    log("待上传 %d 个文件, 合计 %.2f MB" % (len(files), total / 1024.0 / 1024.0))
    for rel, p, is_text in files:
        log("   %9d  %-52s %s" % (os.path.getsize(p), rel, "text" if is_text else "bin"))
    if args.dry_run:
        return 0

    # 1) 为空仓库创建首个 commit, 需要先有一个 tree。
    #    逐文件建 blob(内容寻址, 已存在则复用)。
    log("\n[1/4] 上传 blob ...")
    tree = []
    for i, (rel, abs_p, is_text) in enumerate(files, 1):
        with open(abs_p, "rb") as f:
            raw = f.read()
        if is_text:
            try:
                payload = {"content": raw.decode("utf-8"), "encoding": "utf-8"}
            except UnicodeDecodeError:
                payload = {"content": base64.b64encode(raw).decode("ascii"),
                           "encoding": "base64"}
        else:
            payload = {"content": base64.b64encode(raw).decode("ascii"),
                       "encoding": "base64"}
        blob = gh.post("/repos/%s/git/blobs" % args.repo, payload)
        tree.append({"path": rel, "mode": "100644", "type": "blob", "sha": blob["sha"]})
        log("      [%2d/%d] %s" % (i, len(files), rel))

    # 2) tree
    # GitHub 的 Git Data API 是最终一致的: 刚创建的 blob 可能还没复制完成,
    # 立刻建 tree 会偶发 422 "tree.sha ... is not a valid blob"。这里退避重试。
    log("[2/4] 创建 tree ...")
    new_tree = None
    for attempt in range(6):
        try:
            new_tree = gh.post("/repos/%s/git/trees" % args.repo, {"tree": tree})
            break
        except RuntimeError as e:
            msg = str(e)
            if "not a valid blob" in msg and attempt < 5:
                wait = 2 * (attempt + 1)
                log("      blob 尚未就绪, %ds 后重试 (%d/5) ..." % (wait, attempt + 1))
                time.sleep(wait)
                continue
            raise
    log("      tree = %s" % new_tree["sha"])

    # 3) commit(空仓库没有 parent)
    log("[3/4] 创建 commit ...")
    commit_payload = {"message": args.message, "tree": new_tree["sha"]}
    try:
        ref = gh.get("/repos/%s/git/ref/heads/%s" % (args.repo, args.branch))
        commit_payload["parents"] = [ref["object"]["sha"]]
        log("      基于已有分支 %s (%s)" % (args.branch, ref["object"]["sha"][:8]))
    except RuntimeError:
        log("      空仓库, 创建首个 commit")
    commit = gh.post("/repos/%s/git/commits" % args.repo, commit_payload)
    log("      commit = %s" % commit["sha"])

    # 4) ref
    log("[4/4] 更新分支 %s ..." % args.branch)
    try:
        gh.post("/repos/%s/git/refs" % args.repo,
                {"ref": "refs/heads/" + args.branch, "sha": commit["sha"]})
        log("      已创建 refs/heads/%s" % args.branch)
    except RuntimeError:
        gh._req("PATCH", "/repos/%s/git/refs/heads/%s" % (args.repo, args.branch),
                {"sha": commit["sha"], "force": True})
        log("      已更新 refs/heads/%s" % args.branch)

    log("\n完成: https://github.com/%s" % args.repo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
