# -*- coding: utf-8 -*-
"""
以「无黑色控制台窗口」的方式启动 GUI 子脚本(切换器 / 桌宠)。

Windows 上优先用 pythonw.exe; 其余平台直接用当前解释器。
被 cli.py / pet.py / switcher.py 共用。
"""
import os
import subprocess
import sys


def _pythonw():
    exe = sys.executable
    if os.name == "nt":
        cand = os.path.join(os.path.dirname(exe), "pythonw.exe")
        if os.path.exists(cand):
            return cand
    return exe


def module_argv(module_name):
    """返回启动某个 gui 模块的 argv。"""
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    script = os.path.join(pkg_dir, module_name)
    return [_pythonw(), script]


def launch(module_name, background=True):
    argv = module_argv(module_name)
    if background:
        kw = {"cwd": os.path.dirname(os.path.abspath(__file__))}
        if os.name == "nt":
            kw["creationflags"] = 0x00000008 | 0x00000200  # DETACHED | NEW_PROCESS_GROUP
        subprocess.Popen(argv, **kw)
        return 0
    return subprocess.call(argv)


def main():
    """genshen-cp8-switcher 入口: 直接启动切换器。"""
    name = os.path.basename(sys.argv[0] or "")
    target = "pet.py" if "pet" in name else "switcher.py"
    if len(sys.argv) > 1 and sys.argv[1] in ("pet.py", "switcher.py"):
        target = sys.argv[1]
    return launch(target, background=False)


def gui_launch(module_name):
    """给 cli.py 用的包装。"""
    return launch(module_name, background=True)


if __name__ == "__main__":
    sys.exit(main())
