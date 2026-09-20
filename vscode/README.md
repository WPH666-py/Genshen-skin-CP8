# 原神CP8 — 胡桃×芙宁娜 · VSCode / Trae / CodeX 扩展

单张样式壁纸一键切换 · 桌面桌宠 · 多 IDE 皮肤。

## 安装

```bash
code --install-extension genshen-skin-cp8-0.1.0.vsix
```

`code` 换成 `trae` / `cursor` / `windsurf` 即可装到对应编辑器。

无网 / 没有命令行时: 把本目录整个复制到
`%USERPROFILE%\.vscode\extensions\wp666.genshen-skin-cp8-0.1.0\`, 然后重启编辑器。

## 使用

1. 活动栏点 **原神CP8** 图标 → 打开「皮肤画廊」
2. 点任意卡片的「设为壁纸」即可切换到该系统壁纸
3. 底部四个按钮: 随机换一张 / 生成全部样式 / 壁纸切换器 / 桌面桌宠

命令面板(`Ctrl+Shift+P`)搜 `原神CP8` 也能用全部命令。

## 依赖

- Python 3.9+ 与 Pillow(扩展检测到 Pillow 缺失会**自动** `pip install pillow`)
- 本套件的 Python 包: `pip install genshen-skin-cp8`

扩展按以下顺序查找 Python 包: 已 pip 安装 → `genshen_skin_cp8.repoPath` 设置项 →
`%USERPROFILE%\Genshen-skin-CP8` → 当前工作区。

## 设置项

| 设置 | 默认 | 说明 |
|---|---|---|
| `genshincp1.pythonPath` | 空 | Python 解释器路径, 留空自动查找 `python` / `python3` / `py` |
| `genshincp1.repoPath` | 空 | 仓库路径(含 `src/genshen_skin_cp8`), 留空自动检测 |

## 打包(维护者)

```bash
cd vscode
npm install -g @vscode/vsce      # 只需一次
vsce package --allow-missing-repository --skip-license
```

`vscode:prepublish` 钩子会自动调用 `gen_media.py` 生成缺失的缩略图与图标
(需要装有 Pillow 的 Python)。
