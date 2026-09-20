# AGENTS.md — 原神 CP 壁纸套件8 · AI 自动安装指引(AI 助手必读)

> **给 AI 的话**: 当用户把本仓库地址发给你, 并说「安装原神CP8壁纸 / 原神CP8 / 胡桃芙宁娜壁纸 /
> 换个壁纸」时, **你就是安装器**。请直接替用户执行下面的步骤, 不要让用户自己敲命令。
> 所有命令都是幂等的, 重复执行安全。

## 这套东西是什么

**原神 CP 壁纸套件 8 · 胡桃 × 芙宁娜** —— 壁纸包。

有**三张插画**(往生堂 × 枫丹廷: 女仆装、居家便装、节日和服), 每张都能切换
**三种摆法**, 所以共 **9 种壁纸**:

| 模式 id | 名称 | 说明 |
|---|---|---|
| `single1..3` | 卡片式 | **默认**。模糊填充背景 + 居中圆角卡片, 构图完整不裁切 |
| `cover1..3` | 满屏 | cover 铺满整屏, 无边框; 前两张是竖图, 取景窗上移保住脸 |
| `showall1..3` | 完整 | 等比放进同色纯色底, **一个像素都不裁**, 两侧留边 |

素材已打进发行包, **离线可用**。跨平台 Windows / macOS / Linux。

## 第 0 步: 选安装形态(优先 A)

```bash
# A. 用仓库里已打包的 wheel(不需要联网装依赖)
pip install "https://github.com/WPH666-py/Genshen-skin-CP8/raw/main/dist/genshen_skin_cp8-0.1.0-py3-none-any.whl"

# B. 源码
git clone https://github.com/WPH666-py/Genshen-skin-CP8.git "$HOME/Genshen-skin-CP8"
cd "$HOME/Genshen-skin-CP8"
```

验证: `genshen-cp8 info` 应打印素材路径与屏幕分辨率。
**若该命令不存在**, 说明 Scripts 目录不在 PATH, 改用 `python -m genshen_skin_cp8.engine.cli info`。

## 第 1 步: 识别用户环境

- 有 Python 3.9+ (`python --version` 或 `py -3 --version`) → 继续。
- 没有 Python → 先装:
  - Windows: `winget install Python.Python.3.11`
  - macOS: `brew install python`
  - Ubuntu/Debian: `sudo apt install -y python3 python3-pil`
- **Pillow 不用手动装**, 脚本检测到缺失会自动 `pip install pillow`。

## 第 2 步: 一键安装(所有平台)

```bash
genshen-cp8-install
```

依次完成: 装依赖 → 生成默认壁纸(按屏幕分辨率) → 设为系统桌面壁纸 →
自动注册已装 IDE(VSCode 系扩展 + JetBrains 背景图素材 + MCP 服务器 + DeepKing 皮肤)。

可选参数: `--no-wallpaper` / `--no-ide` / `--size 2560x1440` /
`--only vscode jetbrains mcp deepking`

源码形态等价命令: `python -m genshen_skin_cp8.engine.autoinstall`

## 第 3 步: 按用户环境补做

### A. 换壁纸(用户在聊天里说"换一张")

```bash
genshen-cp8            # 第 1 张 · 卡片式(默认)
genshen-cp8 2          # 第 2 张(居家)
genshen-cp8 3          # 第 3 张(节日)
genshen-cp8 cover      # 第 1 张满屏;   cover2 / cover3 同理
genshen-cp8 showall1   # 第 1 张完整不裁; showall2 / showall3 同理
genshen-cp8 random     # 随机一张(9 种里随机)
genshen-cp8 list       # 列出全部 9 种
genshen-cp8 all        # 一次生成 9 张到 ~/.genshen-cp8/wallpapers
```

### B. VSCode / Trae / CodeX / Cursor / Windsurf

```bash
genshen-cp8-install --only vscode
```

手动等价:
`code --install-extension <仓库>/vscode/genshen-skin-cp8-0.1.0.vsix`

无网时: 把 `vscode/` 整个目录复制到
`%USERPROFILE%\.vscode\extensions\wp666.genshen-skin-cp8-0.1.0\`, 然后重启编辑器。

装完提示用户: 活动栏 **原神CP8** 图标 → 皮肤画廊 **9 张卡片**, 点「设为壁纸」即可。

### C. PyCharm / WebStorm / IntelliJ

```bash
genshen-cp8 all --out "$HOME/GenshenCP8-Backgrounds"
```

生成 9 张。再引导用户:
Settings → Appearance & Behavior → Appearance → **Background Image**
→ 点 `+` 选图片(编辑器区推荐 `single3-*.jpg`, 横图留白舒服)。
细节见 [ide/jetbrains/README.md](ide/jetbrains/README.md)。

### D. DeepKing 界面皮肤(深度适配)

```bash
genshen-cp8 deepking           # 生成皮肤 JSON + 离线预览, 并打印接入步骤
genshen-cp8 deepking --check   # 校验仓库是否满足 DeepKing 转换契约
genshen-cp8 deepking --what    # 显示 DeepKing 会从仓库里提取到什么
```

给用户的两句话:

1. 打开 DeepKing → **设置 → 界面皮肤 / UI Skin**;
2. 粘贴 `https://github.com/WPH666-py/Genshen-skin-CP8` → 生成自定义皮肤。

也可离线接入: 用 `genshen-cp8 deepking` 生成的
`~/.genshen-cp8/deepking/genshen-cp8.skin.json`。

**维护者注意**(改了皮肤文件务必重跑 `--check`):

| 文件 | 作用 |
|---|---|
| `skin.json` | DeepKing 读取 `name` / `accent` / `tagline`; `accent` 必须是 `#` 十六进制 |
| `src/client/genshen-cp8.module.css` | 配色变量 `--名: #hex`; 变量名需含 `bg-base`、`label-primary`、`brand-primary`、`border-l2` 等关键词 |
| `assets/background/mascot-cp8-light.jpg` / `-dark.jpg` | 编辑区右下角水印, 取自「女仆」与「节日」两张 |

**两个容易踩的坑**(`--check` 会报出来):

- 色值必须是 `#` 开头的十六进制, `rgb()` / `hsl()` / 颜色名一律被忽略。
- **不要在暗色作用域里重复声明同名变量**。DeepKing 的 `extractVars()` 是无作用域
  全文扫描、后者覆盖前者, 于是暗色值会把**亮色调色板也刷成深色**, 两套都变深色。
  本仓库的做法: 亮色用 `:root` 的规范变量名, 暗色用不与关键词冲突的 `--duskcolor-*`
  前缀且选择器不含 `dark` 字样, 让 DeepKing 按内置规则从亮色派生暗色。

### E. Claude Code / Kimi Code / Harness 等(聊天窗口形态)

这些环境支持 MCP。注册后 AI 可以**直接调工具换壁纸**:

```bash
genshen-cp8-install --only mcp
```

等价 MCP 配置(写入配置文件的 `mcpServers`):

```json
{
  "mcpServers": {
    "genshen-cp8": {
      "command": "python",
      "args": ["-m", "genshen_skin_cp8.engine.mcp_server"]
    }
  }
}
```

MCP 暴露 5 个工具: `list_wallpapers` / `set_wallpaper` / `next_wallpaper` /
`generate_all` / `wallpaper_info`。用户说"换壁纸"时调用 `next_wallpaper` 即可。

### F. 桌面桌宠 / 可视化切换器(需要图形桌面)

```bash
genshen-cp8 switcher    # 可视化切换器: 左侧预览 9 种模式, 右侧一键应用
genshen-cp8 pet         # 桌面桌宠: 左键拖动, 右键菜单, Esc 退出
genshen-cp8 cycle 30    # 每 30 分钟自动随机换
```

**注意**: 这三条需要本地图形会话。若你在远程/无桌面环境执行失败, 告诉用户在自己电脑上运行,
**不要说"安装失败"**。

## 约定与失败处理

- 只依赖 Pillow, 其余全部标准库; 素材已打进 wheel, 不联网也能用。
- 生成物放在 `~/.genshen-cp8/`(Windows: `C:\Users\<你>\.genshen-cp8`), **不会**改动仓库文件。
- 素材或代码更新后自动重新合成(热更新), 不需手动删缓存。
- Windows 控制台报 GBK/Unicode 错 → `chcp 65001` 后重跑(脚本已内置 UTF-8 兜底)。
- 高分屏生成慢 → 加 `--size 1920x1080` 降一档。
- 桌宠在个别 Linux 桌面不支持透明色键 → 退化为白底卡片, 功能不受影响, 告知用户即可。
- **与其它套件可共存**: CP1~CP7 与本套件的包名、命令前缀、运行时目录、
  vscode 扩展 ID、DeepKing 皮肤 id 全部独立, 同时安装不会互相覆盖。

## 一键复述(可直接念给用户)

> 已为你装好「原神 CP 壁纸套件8 · 胡桃 × 芙宁娜」。
> 三张图 × 三种摆法 = 9 种壁纸: `genshen-cp8 1|2|3` 换图,
> `genshen-cp8 cover` / `showall` 换摆法;
> 可视化切换器: `genshen-cp8 switcher`; 桌宠: `genshen-cp8 pet`;
> DeepKing 皮肤: 设置 → 界面皮肤 → 粘贴 `https://github.com/WPH666-py/Genshen-skin-CP8`;
> VSCode 活动栏的「原神CP8」图标里有 9 张卡片可一键换。
