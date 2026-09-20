// 原神 CP 壁纸套件 8 — 胡桃 × 芙宁娜 · 单张素材三种呈现 (VSCode / Trae / CodeX / Cursor / Windsurf)
const vscode = require('vscode');
const { spawn, spawnSync } = require('child_process');
const os = require('os');
const path = require('path');
const fs = require('fs');

const REPO_URL = 'https://github.com/WPH666-py/Genshen-skin-CP8.git';
const EXT_ID = 'wp666.genshen-skin-cp8';

// ---------------------------------------------------------------- 环境探测

function expand(p) {
  if (!p) return p;
  if (p === '~') return os.homedir();
  if (p.startsWith('~/') || p.startsWith('~\\')) return path.join(os.homedir(), p.slice(2));
  return p;
}

function fileOk(p) {
  try {
    return !!p && fs.existsSync(p);
  } catch (e) {
    return false;
  }
}

function detectPython() {
  const cfg = expand(vscode.workspace.getConfiguration('genshencp8').get('pythonPath', ''));
  if (cfg && fileOk(cfg)) return cfg;
  for (const cand of ['python', 'python3', 'py']) {
    try {
      const r = spawnSync(cand, ['-c', 'import sys;print(sys.version_info[0])'], {
        encoding: 'utf8',
        timeout: 8000,
        windowsHide: true
      });
      if (r.status === 0 && (r.stdout || '').trim().startsWith('3')) return cand;
    } catch (e) { /* 继续试下一个 */ }
  }
  return null;
}

function pilOk(py) {
  try {
    const r = spawnSync(py, ['-c', 'import PIL'], { encoding: 'utf8', timeout: 20000, windowsHide: true });
    return r.status === 0;
  } catch (e) {
    return false;
  }
}

function ensurePil(py) {
  if (pilOk(py)) return true;
  try {
    spawnSync(py, ['-m', 'pip', 'install', '--user', 'pillow'], {
      encoding: 'utf8',
      timeout: 300000,
      windowsHide: true
    });
  } catch (e) { /* 忽略 */ }
  return pilOk(py);
}

/** 优先用 pip 安装的包; 回退到仓库源码目录(需已 pip install 或设置 PYTHONPATH)。 */
function findRepo() {
  const cfg = expand(vscode.workspace.getConfiguration('genshencp8').get('repoPath', ''));
  const cands = [
    cfg,
    process.env.GENSHIN_CP1_REPO,
    path.join(os.homedir(), 'Genshen-skin-CP8'),
    process.env.USERPROFILE ? path.join(process.env.USERPROFILE, 'Genshen-skin-CP8') : null,
    vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0]
      ? vscode.workspace.workspaceFolders[0].uri.fsPath
      : null
  ].filter(Boolean);
  for (const c of cands) {
    try {
      if (fs.existsSync(path.join(c, 'src', 'genshen_skin_cp8', 'cli.py'))) return c;
      if (fs.existsSync(path.join(c, 'tools', 'wallpaper.py'))) return c;
    } catch (e) { /* 忽略 */ }
  }
  return null;
}

/** 构造运行壁纸命令的 (py, args, cwd, env)。 */
function buildInvocation(sub) {
  const py = detectPython();
  if (!py) return { error: '未找到 Python 3。请先安装: winget install Python.Python.3.11' };
  if (!ensurePil(py)) return { error: 'Pillow 安装失败, 请手动执行: ' + py + ' -m pip install pillow' };

  const repo = findRepo();
  const env = Object.assign({}, process.env);
  if (repo) {
    env.PYTHONPATH = (env.PYTHONPATH ? env.PYTHONPATH + path.delimiter : '') +
      path.join(repo, 'src');
    return { py: py, args: ['-m', 'genshen_skin_cp8.cli'].concat(sub), cwd: repo, env: env };
  }
  // pip 安装形态: 直接用模块
  return { py: py, args: ['-m', 'genshen_skin_cp8.cli'].concat(sub), cwd: os.homedir(), env: env };
}

function envError(msg) {
  vscode.window.showWarningMessage(
    msg + ' 请先安装: pip install ' + 'genshen-skin-cp8' +
    '  (或克隆 ' + REPO_URL + ' 到 ' + path.join(os.homedir(), 'Genshen-skin-CP8') + ')'
  );
}

function runCli(sub, okMsg) {
  const inv = buildInvocation(sub);
  if (inv.error) return envError(inv.error);
  const child = spawn(inv.py, inv.args, {
    cwd: inv.cwd,
    env: inv.env,
    windowsHide: true
  });
  child.stdout.setEncoding('utf8');
  child.stderr.setEncoding('utf8');
  let out = '';
  child.stdout.on('data', (d) => (out += d.toString()));
  child.stderr.on('data', (d) => (out += d.toString()));
  child.on('close', (code) => {
    if (code === 0) {
      vscode.window.setStatusBarMessage('💙 ' + (okMsg || '壁纸已应用!'), 5000);
    } else {
      envError('操作失败(' + code + '): ' + out.slice(-300));
    }
  });
  child.on('error', (e) => envError('启动 Python 失败: ' + e.message));
}

function spawnGui(moduleName, label) {
  const inv = buildInvocation([]);
  if (inv.error) return envError(inv.error);
  let exe = inv.py;
  if (process.platform === 'win32') {
    const w = path.join(path.dirname(exe), 'pythonw.exe');
    if (fileOk(w)) exe = w;
  }
  const child = spawn(exe, ['-m', 'genshen_skin_cp8.' + moduleName], {
    cwd: inv.cwd,
    env: inv.env,
    detached: true,
    stdio: 'ignore',
    windowsHide: true
  });
  child.unref();
  vscode.window.setStatusBarMessage('💙 已启动' + (label || moduleName), 4000);
}

// ---------------------------------------------------------------- 画廊视图

// 本套件只有一张素材(胡桃 × 芙宁娜 双人合影), 因此画廊给的是同一张的
// 三种呈现方式。ids 必须与 characters/cp8_pair.py 的 MODES 一致。
const CARDS = [
  { mode: 'single1', t: '女仆 · 卡片', img: 'thumb-single1.png', d: '模糊背景 + 居中卡片' },
  { mode: 'single2', t: '居家 · 卡片', img: 'thumb-single2.png', d: '模糊背景 + 居中卡片' },
  { mode: 'single3', t: '节日 · 卡片', img: 'thumb-single3.png', d: '模糊背景 + 居中卡片' },
  { mode: 'cover1', t: '女仆 · 满屏', img: 'thumb-cover1.png', d: 'cover 铺满整屏' },
  { mode: 'cover2', t: '居家 · 满屏', img: 'thumb-cover2.png', d: 'cover 铺满整屏' },
  { mode: 'cover3', t: '节日 · 满屏', img: 'thumb-cover3.png', d: 'cover 铺满整屏' },
  { mode: 'showall1', t: '女仆 · 完整', img: 'thumb-showall1.png', d: '不裁切, 两侧留边' },
  { mode: 'showall2', t: '居家 · 完整', img: 'thumb-showall2.png', d: '不裁切, 两侧留边' },
  { mode: 'showall3', t: '节日 · 完整', img: 'thumb-showall3.png', d: '不裁切, 两侧留边' }
];

class GalleryProvider {
  resolveWebviewView(view) {
    const ext = vscode.extensions.getExtension(EXT_ID);
    const media = path.join(ext.extensionPath, 'media');
    const thumb = (f) => view.webview.asWebviewUri(vscode.Uri.file(path.join(media, f)));
    view.webview.html = renderHtml(thumb, !!detectPython());
    view.webview.onDidReceiveMessage((msg) => {
      if (!msg) return;
      if (msg.cmd === 'apply') runCli([msg.mode], '已切换: ' + msg.mode);
      else if (msg.cmd === 'random') runCli(['random'], '已随机换一张!');
      else if (msg.cmd === 'switcher') spawnGui('switcher', '壁纸切换器');
      else if (msg.cmd === 'pet') spawnGui('pet', '桌面桌宠');
      else if (msg.cmd === 'all') runCli(['all'], '已生成全部样式!');
    });
  }
}

function renderHtml(thumb, hasPython) {
  const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
  const card = (c) =>
    '<div class="card"><div class="thumb"><img src="' + thumb(c.img) + '" alt="' + esc(c.t) + '"/></div>' +
    '<div class="t">' + esc(c.t) + '</div><div class="d">' + esc(c.d) + '</div>' +
    '<button data-mode="' + c.mode + '">设为壁纸</button></div>';
  const warn = hasPython ? '' :
    '<div class="warn">⚠ 未检测到 Python 3, 请先安装后重载窗口。' +
    '(Windows: winget install Python.Python.3.11)</div>';
  return '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><style>' +
    'body{background:var(--vscode-sideBar-background,#0f141b);color:var(--vscode-foreground,#e8eef7);' +
    'font-family:var(--vscode-font-family,system-ui);padding:10px;margin:0}' +
    '.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}' +
    '.card{background:var(--vscode-editorWidget-background,#182130);border-radius:10px;padding:8px;' +
    'text-align:center;border:1px solid rgba(127,127,127,.18)}' +
    '.thumb{aspect-ratio:16/9;overflow:hidden;border-radius:7px;background:#0b1017}' +
    '.card img{width:100%;height:100%;object-fit:cover;display:block}' +
    '.card .t{margin:6px 0 1px;font-weight:600;font-size:12px}' +
    '.card .d{font-size:10px;opacity:.6;margin-bottom:5px}' +
    'button{margin-top:2px;width:100%;border:none;border-radius:7px;padding:6px 0;cursor:pointer;' +
    'background:var(--vscode-button-background,#2f6fe4);color:var(--vscode-button-foreground,#fff);font-size:12px}' +
    'button:hover{background:var(--vscode-button-hoverBackground,#4b85f0)}' +
    '.warn{color:#f4c15a;font-size:11px;padding:8px;margin-bottom:10px;background:rgba(244,193,90,.1);' +
    'border-radius:8px;line-height:1.5}' +
    '.cmds{margin-top:12px;display:grid;grid-template-columns:1fr 1fr;gap:8px}' +
    '.cmds button{background:var(--vscode-button-secondaryBackground,#37455a);' +
    'color:var(--vscode-button-secondaryForeground,#e8eef7)}' +
    '.cmds button:hover{background:var(--vscode-button-secondaryHoverBackground,#46566e)}' +
    '.foot{margin-top:12px;font-size:10px;opacity:.55;line-height:1.6;text-align:center}' +
    '</style></head><body>' + warn +
    '<div class="grid">' + CARDS.map(card).join('') + '</div>' +
    '<div class="cmds">' +
    '<button class="alt" data-cmd="random">🎲 随机换一张</button>' +
    '<button class="alt" data-cmd="all">📁 生成全部样式</button>' +
    '<button class="alt" data-cmd="switcher">🖼️ 壁纸切换器</button>' +
    '<button class="alt" data-cmd="pet">💙 桌面桌宠</button>' +
    '</div>' +
    '<div class="foot">原神 CP 壁纸套件 8 · 胡桃 × 芙宁娜 v0.1.0<br/>' +
    '给任意 AI 发仓库链接即可自动安装</div>' +
    '<script>const vscode=acquireVsCodeApi();' +
    'document.querySelectorAll("button[data-mode]").forEach(function(b){' +
    'b.addEventListener("click",function(){vscode.postMessage({cmd:"apply",mode:b.dataset.mode})})});' +
    'document.querySelectorAll("button[data-cmd]").forEach(function(b){' +
    'b.addEventListener("click",function(){vscode.postMessage({cmd:b.dataset.cmd})})});' +
    '</script></body></html>';
}

// ---------------------------------------------------------------- 激活

function activate(ctx) {
  const reg = (cmd, fn) =>
    ctx.subscriptions.push(vscode.commands.registerCommand(cmd, fn));

  reg('genshencp8.set1', () => runCli(['1'], '已切换: 女仆'));
  reg('genshencp8.set2', () => runCli(['2'], '已切换: 居家'));
  reg('genshencp8.set3', () => runCli(['3'], '已切换: 节日'));
  reg('genshencp8.setCard', () => runCli(['card'], '已切换: 卡片式'));
  reg('genshencp8.setCover', () => runCli(['cover'], '已切换: 满屏'));
  reg('genshencp8.setShowall', () => runCli(['showall'], '已切换: 完整不裁'));
  reg('genshencp8.setRandom', () => runCli(['random'], '已随机换一张!'));
  reg('genshencp8.generateAll', () => runCli(['all'], '已生成全部样式!'));
  reg('genshencp8.openSwitcher', () => spawnGui('switcher', '壁纸切换器'));
  reg('genshencp8.startPet', () => spawnGui('pet', '桌面桌宠'));
  reg('genshencp8.showInfo', () => {
    const inv = buildInvocation(['info']);
    if (inv.error) return envError(inv.error);
    const term = vscode.window.createTerminal({ name: '原神CP8 自检', cwd: inv.cwd, env: inv.env });
    term.show();
    term.sendText('"' + inv.py + '" ' + inv.args.map((a) => '"' + a + '"').join(' '));
  });
  reg('genshencp8.openGallery', () =>
    vscode.commands.executeCommand('workbench.view.extension.genshencp8')
  );

  ctx.subscriptions.push(
    vscode.window.registerWebviewViewProvider('genshencp8.gallery', new GalleryProvider(), {
      webviewOptions: { retainContextWhenHidden: true }
    })
  );
}

function deactivate() {}

module.exports = { activate, deactivate };
