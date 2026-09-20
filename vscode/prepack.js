// 打包前处理: 确保 media/ 里的图标与缩略图存在(缺失时用系统 Python + Pillow 生成)。
// vsce package / vsce publish 会自动调用 vscode:prepublish -> node prepack.js
const { spawnSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const here = __dirname;
const media = path.join(here, 'media');
const src = path.join(here, '..', 'src', 'genshen_skin_cp8', 'assets');

function ok(p) {
  try {
    return fs.existsSync(p);
  } catch (e) {
    return false;
  }
}

function pickPython() {
  for (const c of ['python', 'python3', 'py']) {
    const r = spawnSync(c, ['-c', 'import PIL'], { encoding: 'utf8', windowsHide: true });
    if (r.status === 0) return c;
  }
  return null;
}

function main() {
  fs.mkdirSync(media, { recursive: true });
  // 本套件单张素材, 三种呈现方式 -> 三张缩略图
  const need = [
    'icon.png',
    'thumb-single1.png',
    'thumb-single2.png',
    'thumb-single3.png',
    'thumb-cover1.png',
    'thumb-cover2.png',
    'thumb-cover3.png',
    'thumb-showall1.png',
    'thumb-showall2.png',
    'thumb-showall3.png'
  ];
  if (need.every((f) => ok(path.join(media, f)))) {
    console.log('[prepack] media/ 已完整, 跳过生成');
    return;
  }
  if (!ok(src)) {
    console.warn('[prepack] 未找到素材目录 ' + src + ', 保留现有 media/');
    return;
  }
  const py = pickPython();
  if (!py) {
    console.warn('[prepack] 未找到带 Pillow 的 Python, 无法生成缩略图');
    return;
  }
  const gen = path.join(here, 'gen_media.py');
  const r = spawnSync(py, [gen], { encoding: 'utf8', cwd: here, windowsHide: true });
  if (r.stdout) process.stdout.write(r.stdout);
  if (r.status !== 0) {
    console.warn('[prepack] 生成缩略图失败: ' + (r.stderr || '').slice(-500));
  }
}

main();
