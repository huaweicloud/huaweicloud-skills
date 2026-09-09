#!/usr/bin/env node
// build-cover.mjs — 封面一键生成（单图/多图自动决策 + 概率抽样 + 截图 + 合成 + 校验）
//
// 作用: 把 SKILL.md Step 4 的「字体门禁 → 截图 → 封面合成」整条链封装为一条命令，
//       agent 无需感知布局种类/截图数量/概率抽样——全部内部闭环，输出一行结果。
//
// 决策模型（统一概率池，一次抽样）:
//   单页项目: 方案池 = [classic, split, hero, showcase, polaroid, blur, topbar]        (7 个单图)
//   多页项目: 方案池 = [classic, split, hero, showcase, polaroid, blur, topbar,
//                       collage-h, collage-v, collage-grid]                             (7 单图 + 3 多图)
//   从池中等概率抽 1 个 → 决定布局/截图数量。多页时多图出现概率 = 3/10。
//
// 多页判定: 项目内 .html 文件数 ≥ 2。候选页 = 其余 html 文件（排除 index.html / 404 等）。
//          SPA（单 html 但带 hash 路由）暂视为单页（不触发多图），后续可扩展。
//
// 用法:
//   node build-cover.mjs --url http://127.0.0.1:8080 --project-dir <workDir> \
//       --title "<workName>" --tagline "<一句话>" --description "<介绍>" \
//       --out <cover.png> [--scheme auto] [--force-layout classic]
//
// 输出: 成功 stdout 仅一行（省 token）:
//   #cover=<abs path> layout=<name> multi=yes|no pages=<n> scheme=<scheme>
// 失败: exit 1，stderr 输出错误原因。
//
// 退出码: 0=成功; 1=失败; 2=参数错误

import { execFileSync, spawnSync } from "node:child_process";
import { existsSync, readdirSync, readFileSync, mkdtempSync, rmSync } from "node:fs";
import path from "node:path";
import os from "node:os";
import { fileURLToPath } from "node:url";

const thisDir = path.dirname(fileURLToPath(import.meta.url));
const SCREENSHOT = path.join(thisDir, "screenshot_guard.py");
const PREFLIGHT = path.join(thisDir, "preflight.ps1"); // Windows 优先；非 win 自动换 preflight.sh
const PREFLIGHT_SH = path.join(thisDir, "preflight.sh");
const GEN_COVER = path.join(thisDir, "generate_cover.py");
const VERIFY = path.join(thisDir, "verify-glyphs.py");

const SINGLE_LAYOUTS = ["classic", "split", "hero", "showcase", "polaroid", "blur", "topbar"];
const MULTI_LAYOUTS = ["collage-h", "collage-v", "collage-grid"];

const HELP = `build-cover.mjs — 封面一键生成（单图/多图自动决策 + 概率抽样 + 截图 + 合成 + 校验）

用法:
  node build-cover.mjs --url <appUrl> --project-dir <dir> --title <name> \\
      --out <cover.png> [--tagline <t>] [--description <d>] [--scheme <s>] [--force-layout <l>]

选项:
  --url <u>            应用访问地址（Step 2 已启动，http://127.0.0.1:<port>）
  --project-dir <dir>  项目目录（用于探测页数/候选页面）
  --title <t>          作品名称（必填）
  --tagline <t>        副标题
  --description <d>    主体介绍文字
  --out <png>          封面输出路径（必填）
  --scheme <s>         色调（默认 auto 按标题哈希选）
  --force-layout <l>   强制布局（跳过概率抽样；多图布局需项目多页，否则回退单图）
  --screenshot <png>   已有截图（跳过截图门禁直接用该图；多图时忽略）
  --keywords <a,b,c>   关键词徽章（逗号分隔 3~5 词；不传则从项目探测，30% 概率不带徽章）
  --quiet              静默（stdout 仅结果行，失败才输出详情）
  -h, --help           显示本帮助

退出码: 0=成功; 1=失败; 2=参数错误`;

// ---------------- 参数解析 ----------------
const argv = process.argv.slice(2);
const cli = { url: "", dir: "", title: "", tagline: "", desc: "", out: "", scheme: "auto", layout: "", screenshot: "", keywords: "", quiet: false };
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  const val = () => argv[++i];
  if (a === "-h" || a === "--help") { console.log(HELP); process.exit(0); }
  else if (a === "--url") cli.url = val();
  else if (a === "--project-dir") cli.dir = val();
  else if (a === "--title") cli.title = val();
  else if (a === "--tagline") cli.tagline = val();
  else if (a === "--description") cli.desc = val();
  else if (a === "--out") cli.out = val();
  else if (a === "--scheme") cli.scheme = val();
  else if (a === "--force-layout") cli.layout = val();
  else if (a === "--screenshot") cli.screenshot = val();
  else if (a === "--keywords") cli.keywords = val();
  else if (a === "--quiet") cli.quiet = true;
  else if (a.startsWith("--")) { console.error(`❌ 未知参数: ${a}`); process.exit(2); }
}
if (!cli.url || !cli.dir || !cli.title || !cli.out) {
  console.error("❌ 缺少必要参数: --url / --project-dir / --title / --out");
  console.error(HELP);
  process.exit(2);
}
if (!existsSync(cli.dir)) { console.error(`❌ 项目目录不存在: ${cli.dir}`); process.exit(2); }

const log = cli.quiet ? () => {} : (m) => console.error(`[build-cover] ${m}`);
const isWindows = process.platform === "win32";

// ---------------- 工具函数 ----------------
function pyCmd() {
  // Windows 优先 python；非 win 用 python3
  if (isWindows) {
    for (const c of ["python", "python3"]) {
      try { const r = spawnSync(c, ["--version"], { stdio: "ignore" }); if (!r.error && r.status === 0) return c; } catch {}
    }
    return "python"; // 都不存在时回退，runPython 会给出明确报错
  }
  return "python3";
}

function runPython(script, args) {
  const cmd = pyCmd();
  const r = spawnSync(cmd, [script, ...args], { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
  if (r.error) {
    // 区分「Python 不存在」与「其他执行错误」，给出可操作的修复提示
    if (r.error.code === "ENOENT" || /not recognized|not.*command|无法找到|不是内部或外部命令/i.test(r.error.message || "")) {
      throw new Error(
        `❌ 找不到可用的 Python（已尝试 ${isWindows ? '"python"' : '"python3"'}${isWindows ? ' 和 "python3"' : ""}）。\n` +
        `  封面生成依赖 Python 3（截图/合成/校验脚本均为 .py）。请任选一种方式补齐：\n` +
        `  1) 手动安装（国内镜像加速）：${isWindows ? "在 https://mirrors.huaweicloud.com/python/ 下载 Windows installer（选最新 3.12/3.11）安装并勾选 Add to PATH（WindowsApps 里 python3 可能是 Store stub，务必用真实解释器）" : "系统包管理器安装（如 yum install -y python3 / apt-get install -y python3，或从华为云镜像 https://mirrors.huaweicloud.com/python/ 下载源码编译）"}\n` +
        `  2) 让 AI 助手（agent）代为安装并加入 PATH 后重试。\n` +
        `  3) 安装后验证：${isWindows ? '"python" --version' : '"python3" --version'}`
      );
    }
    throw new Error(`无法执行 ${cmd}: ${r.error.message}`);
  }
  return r;
}

// ---------------- 页数探测 ----------------
function detectPages(dir) {
  // 递归收集 .html（排除 node_modules/.git/dist）
  const htmls = [];
  const walk = (d) => {
    let entries;
    try { entries = readdirSync(d, { withFileTypes: true }); } catch { return; }
    for (const e of entries) {
      if (["node_modules", ".git", "dist", "build", ".venv", "__pycache__"].includes(e.name)) continue;
      const full = path.join(d, e.name);
      if (e.isDirectory()) walk(full);
      else if (e.name.toLowerCase().endsWith(".html")) htmls.push(full);
    }
  };
  walk(dir);
  return htmls;
}

function relPath(dir, full) {
  return path.relative(dir, full).split(path.sep).join("/");
}

// combineUrl: base http://host:port[/] + relative html path
function pageUrl(base, rel) {
  const clean = base.replace(/\/+$/, "");
  // 去掉 index.html 本身（首页）
  if (rel === "index.html") return clean + "/";
  const q = rel === "" ? "" : "/" + rel;
  return clean + q;
}

// ---------------- 概率抽样 ----------------
function pickLayout(multipage, forced) {
  if (forced) {
    if (MULTI_LAYOUTS.includes(forced) && !multipage) {
      log(`⚠️ 项目单页，多图布局 ${forced} 不可用，回退单图`);
      return "classic";
    }
    return forced;
  }
  const pool = multipage ? [...SINGLE_LAYOUTS, ...MULTI_LAYOUTS] : [...SINGLE_LAYOUTS];
  return pool[Math.floor(Math.random() * pool.length)];
}

// ---------------- 主流程 ----------------
function collectKeywords(dir) {
  // 从 package.json keywords / README 合成 3~5 个关键词（用于封面徽章）。
  // 优先级: package.json.keywords -> README 标题/首段关键词。不足则返回空（不渲染徽章）。
  try {
    const pkg = path.join(dir, "package.json");
    if (existsSync(pkg)) {
      const kws = JSON.parse(readFileSync(pkg, "utf8")).keywords;
      if (Array.isArray(kws)) {
        const valid = kws.map((k) => String(k).trim()).filter((k) => k && k.length <= 12);
        if (valid.length >= 3) return valid.slice(0, 5);
      }
    }
  } catch {}
  try {
    const readme = ["README.md", "readme.md", "README.txt"].map((n) => path.join(dir, n)).find(existsSync);
    if (readme) {
      const text = readFileSync(readme, "utf8").slice(0, 800);
      const hits = text.match(/[A-Za-z][A-Za-z0-9+-]{1,15}/g) || [];
      const pooled = new Set();
      for (const h of hits) {
        const low = h.toLowerCase();
        if (["the","and","for","with","this","that","from","your","how"].includes(low)) continue;
        if (/\d{3,}/.test(h)) continue;
        pooled.add(h);
      }
      const arr = [...pooled].filter((h) => h.length >= 3);
      if (arr.length >= 3) return arr.slice(0, 5);
    }
  } catch {}
  return [];
}

function main() {
  // 1) 页数判定
  const pages = detectPages(cli.dir);
  const htmlFiles = pages.map((f) => relPath(cli.dir, f));
  const nonIndex = htmlFiles.filter((f) => f.toLowerCase() !== "index.html");
  // 仅 ≥3 页（首页+≥2 候选）才启用多图布局；2 页（首页+1 候选）多图意义薄弱且小图太稀疏
  const multipage = nonIndex.length >= 2;
  const pagesCount = 1 + nonIndex.length;

  // 2) 布局抽样
  const want_multi = cli.layout ? MULTI_LAYOUTS.includes(cli.layout) : false;
  if (cli.layout && want_multi && !multipage) {
    // forced multi on single-page → 回退并提示
    cli.layout = "classic";
  }
  const layout = pickLayout(multipage, cli.layout);
  const isMulti = MULTI_LAYOUTS.includes(layout);
  log(`页数=${pagesCount} 多页=${multipage} 布局=${layout} 多图=${isMulti}`);

  // 3) 截图（多图: 首页 + 其余候选页；单图: 仅首页）
  const tmp = mkdtempSync(path.join(os.tmpdir(), "cover-build-"));
  const shots = {}; // rel -> abs path
  try {
    let mainShot = "";
    if (cli.screenshot && existsSync(cli.screenshot)) {
      mainShot = cli.screenshot;
      log(`复用已有截图 ${mainShot}`);
    } else {
      const shotPath = path.join(tmp, "shot-index.png");
      log(`截图首页 ${cli.url} → ${shotPath}`);
      const r = runPython(SCREENSHOT, [cli.url, "--out", shotPath, "--quiet"]);
      if (r.status !== 0) {
        console.error("❌ 首页截图失败（screenshot_guard.py 非 0）：\n" + (r.stderr || r.stdout));
        process.exitCode = 1;
        return;
      }
      mainShot = shotPath;
      log(`✅ 首页截图完成`);
    }

    // 候选小图（多图布局）
    const smallShots = [];
    if (isMulti) {
      const candidates = nonIndex.slice(0, 4);
      for (const rel of candidates) {
        const url = pageUrl(cli.url, rel);
        const outPath = path.join(tmp, "shot-" + rel.replace(/[^a-zA-Z0-9]/g, "_") + ".png");
        log(`截图候选页 ${url} → ${outPath}`);
        const r = runPython(SCREENSHOT, [url, "--out", outPath, "--quiet"]);
        if (r.status === 0 && existsSync(outPath)) {
          smallShots.push(outPath);
          log(`✅ 候选页截图完成: ${rel}`);
        } else {
          log(`⚠️ 候选页截图失败（跳过）: ${rel}`);
        }
        if (smallShots.length >= 3) break;
      }
    }

    // 4) 合成封面
    const genArgs = [
      "--screenshot", mainShot,
      "--title", cli.title,
      "--out", cli.out,
      "--scheme", cli.scheme,
      "--layout", layout,
    ];
    if (cli.tagline) { genArgs.push("--tagline", cli.tagline); }
    if (cli.desc) { genArgs.push("--description", cli.desc); }
    if (isMulti && smallShots.length > 0) {
      genArgs.push("--screenshots", smallShots.join(","));
    }
    // 关键词徽章：显式 --keywords 优先；否则从项目探测；30% 概率不用关键词（保持封面简洁多样）
    const useKeywords = !(Math.random() < 0.3);
    let keywords = cli.keywords ? cli.keywords.split(",").map((s) => s.trim()).filter(Boolean) : [];
    if (keywords.length === 0 && useKeywords) {
      keywords = collectKeywords(cli.dir);
    }
    if (useKeywords && keywords.length >= 3 && keywords.length <= 5) {
      genArgs.push("--keywords", keywords.join(","));
      log(`关键词徽章: ${keywords.join(", ")}`);
    } else {
      log(`本次无关键词徽章（30% 概率或候选不足）`);
    }
    log(`合成封面 (${layout})...`);
    const g = runPython(GEN_COVER, genArgs);
    if (g.status !== 0) {
      console.error("❌ 封面合成失败（generate_cover.py 非 0）：\n" + (g.stderr || g.stdout));
      process.exitCode = 1;
      return;
    }
    if (!existsSync(cli.out)) { console.error(`❌ 封面未生成: ${cli.out}`); process.exitCode = 1; return; }

    // 5) 校验
    const v = runPython(VERIFY, [cli.out, "--quiet"]);
    if (v.status !== 0) {
      console.error(`❌ 字形校验未通过（${cli.out}），禁止发布：\n${v.stderr || v.stdout}`);
      process.exitCode = 1;
      return;
    }
    log(`✅ 封面校验通过`);

    // 6) 输出一行
    const schemeUsed = cli.scheme; // generate_cover --scheme auto 内部按标题哈希选，脚本不解析，用输入值
    console.log(`#cover=${cli.out} layout=${layout} multi=${isMulti ? "yes" : "no"} pages=${pagesCount} scheme=${schemeUsed}`);
  } finally {
    try { rmSync(tmp, { recursive: true, force: true }); } catch {}
  }
}

main();