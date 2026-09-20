# DeepKing 皮肤文件维护说明

本目录的 `genshen-cp8.module.css` 同时服务两个消费者，改它之前请读完本文。

## 谁在读这个文件

DeepKing 的皮肤转换器 `src/utils/skinConverter.ts`（函数 `convertGitHubRepoToSkin`）
会在用户「设置 → 界面皮肤」里粘贴本仓库地址时，从仓库抓取三样东西：

| 抓什么 | 从哪里抓 | 用途 |
|---|---|---|
| 元信息 | 仓库根的 `skin.json` | 皮肤名、强调色、描述 |
| 配色 | 优先 `src/client/*.module.css`，否则任意 `.css` | 推导 32 槽位调色板 |
| 吉祥物 | 优先 `assets/background/` 下的图片 | 编辑区右下角水印 |

## 转换器的三条实现细节（决定了写法）

1. **它不剥离注释。** 正则直接跑在全文上。所以注释里的内容会被当成真实声明
   —— 详见下面「四个禁区」。

2. **取色是「变量名包含关键词」，不是精确匹配。** 优先级如下：

   ```
   bg      <- bg-layer-1, bg-base, background, bg-100, neutral-50
   text    <- label-primary, ink, text, neutral-1000, neutral-900
   layer2  <- bg-layer-2, bg-200, neutral-100
   accent  <- brand-primary, accent, primary
   border  <- border-l2, border-l1, border
   ```

   所以变量名叫 `--my-bg-base-color` 也会被认作背景色。

3. **`extractVars()` 是无作用域的全文扫描，同名变量后者覆盖前者。**
   这是最坑的一条：如果在暗色作用域里再写一次 `--bg-base`，
   那么**亮色调色板也会拿到暗色值**，结果亮、暗两套都变成深色。

## 四个禁区

`genshen-cp8.module.css` 的注释里绝对不能出现：

| 禁区 | 后果 |
|---|---|
| 花括号 `{` `}` | 块正则会以注释为起点切出一个假选择器块，把注释内容当变量抽取 |
| `dark` 字样 | `extractDarkVars()` 会把这个块当成暗色作用域 |
| 十六进制色值（如 `#3f8fd8`） | 配合上面的假选择器块，会真的污染提取结果 |
| `--名称: 值` 形式 | 会被当成一个真实变量声明 |

这就是为什么本目录的 CSS 里几乎没有说明性注释 —— 文档全部挪到了本文件。

## 本仓库的应对策略

- **亮色**用 `:root`，变量名使用上表里的规范关键词，让转换器精确取到。
- **夜景**用 `--duskcolor-` 前缀，且这些名字**可以**含 `bg-base` 这类关键词
  —— 没关系，因为转换器只在 `:root`/非暗色块里找，而且这些名字不会和亮色同名，
  不会发生「后者覆盖前者」。
- 夜景作用域选择器用 `[data-theme="midnight"]`，**不含 `dark` 字样**，
  这样转换器找不到暗色变量，就会退回到它的内置规则「从亮色派生暗色」
  —— 与内置皮肤同样的行为，观感中性但可用。
- 想保留夜景蓝紫的逐槽位校色版本，用：

  ```bash
  genshen-cp8 deepking          # 导出 ~/.genshen-cp8/deepking/*.skin.json
  ```

  那份是手工校色的，不经过派生算法。

## 改完必须自检

```bash
genshen-cp8 deepking --check    # 应输出「通过」
genshen-cp8 deepking --what     # 看转换器实际会取到什么值
```

`--check` 会检查色值格式、必需关键词、以及上面四个禁区。

## 吉祥物图片

转换器按 `assets/background/` → 文件名含 `maid|whale|poster|mascot` →
任意 `assets/` 下图片的顺序挑图。本仓库提供两张（**同一张素材的两段取景**，
本套件三张素材, 取两张作水印）：

- `mascot-cp8-light.jpg` —— 取「女仆」那张的明亮庭院, 配浅色界面
- `mascot-cp8-dark.jpg` —— 取「节日」那张的灯火夜景, 配深色界面

两张分别由 `02-cafe.jpg` 与 `01-street.jpg` 生成。重做方式：调整 `crop` 的中心比例与取景边长，
重新导出 900×900 即可（见仓库 README 的「素材」一节）。

注意：**在线转换只会用其中一张**（转换器对亮暗都用同一张 URL），
两张分别生效只在手工校色版的 `mascot.light` / `mascot.dark` 里。
