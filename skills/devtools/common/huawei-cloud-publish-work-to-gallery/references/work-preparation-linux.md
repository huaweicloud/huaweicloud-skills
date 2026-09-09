# Work Preparation — Linux / EulerOS (HCE) 专属

本文件只包含**Linux 平台（EulerOS/HCE/CentOS/Debian/Ubuntu）**专属的安装命令、包名映射与排障。运行环境为 Windows 时**不要读本文件**（环境指纹见 `scripts/detect-env.mjs`）。

跨平台统一流程与规则见 `work-preparation.md`；Windows 专属见 `work-preparation-windows.md`。

## Table of Contents

- [Platform Detection](#platform-detection)
- [Playwright/Chromium 安装前预检（bash）](#playwrightchromium-安装前预检bash)
- [Chromium 系统依赖包名映射（EulerOS/HCE vs Ubuntu）](#chromium-系统依赖包名映射euleroshce-vs-ubuntu)
- [安装预期警告（非错误）](#安装预期警告非错误)
- [字体安装速查表（apt/yum 列）](#字体安装速查表aptyum-列)
- [fontconfig 中文回退配置](#fontconfig-中文回退配置)
- [matplotlib `.ttc` 字体缓存问题](#matplotlib-ttc-字体缓存问题)
- [截图有效性校验（bash）](#截图有效性校验bash)
- [详情包 zip 打包（bash）](#详情包-zip-打包bash)

---

## Platform Detection

按顺序检测包管理器/发行版（无需费心，仅当需手动装包时参考）：

```bash
command -v apt-get   # Debian 系 → 用 apt
command -v yum       # RHEL 系（CentOS/EulerOS/HCE）→ 用 yum
grep -E '^(ID|ID_LIKE)=' /etc/os-release   # hce/euler → 是 EulerOS
```

---

## Playwright/Chromium 安装前预检（bash）

先预检，全部通过则跳过安装直接截图（Chromium 安装包 ~300MB，重复装浪费时间）：

```bash
# ===== Playwright/Chromium 安装前预检脚本（Linux/macOS）=====
# 检查项 1：Playwright Python 包是否已安装
PW_OK=false
python3 -m playwright --version >/dev/null 2>&1 && PW_OK=true

# 检查项 2：Chromium 浏览器二进制是否已缓存
CHROMIUM_OK=false
ls "$HOME/.cache/ms-playwright/"chromium* >/dev/null 2>&1 && CHROMIUM_OK=true

# 检查项 3（最可靠）：Chromium 能否实际启动——二进制存在 ≠ 能启动（可能缺系统依赖）
LAUNCH_OK=false
if [ "$PW_OK" = true ] && [ "$CHROMIUM_OK" = true ]; then
  python3 -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    b.close()
print('LAUNCH_OK')
  " 2>/dev/null | grep -q LAUNCH_OK && LAUNCH_OK=true
fi

# 汇总
echo "Playwright 包: $PW_OK | Chromium 二进制: $CHROMIUM_OK | 可启动: $LAUNCH_OK"

if [ "$LAUNCH_OK" = true ]; then
  echo "✅ Playwright + Chromium 已就绪，跳过所有安装步骤"
else
  echo "⚠️ 需要安装缺失组件："
  [ "$PW_OK" = false ]       && echo "  - Playwright Python 包未安装 → pip install playwright"
  [ "$CHROMIUM_OK" = false ] && echo "  - Chromium 二进制未缓存 → python3 -m playwright install chromium"
  [ "$PW_OK" = true ] && [ "$CHROMIUM_OK" = true ] && [ "$LAUNCH_OK" = false ] && \
    echo "  - 系统依赖缺失 → 按下方映射表 yum install"
fi
```

> **预检逻辑：** 三项全 true → 跳过所有安装直接截图；Playwright 包 false → 仅 `pip install playwright`；Chromium 二进制 false → `python3 -m playwright install chromium`；包+二进制就绪但启动 false → **系统依赖缺失**，按下方映射表 `yum install`，无需重装 Chromium。
>
> **系统 Chrome 复用（arm64 优化）：** `browser_launch.py` 与 `preflight.sh` 已支持 Linux 复用系统 Chrome（`channel: 'chrome'`）。若机器已装 Google Chrome / Chromium，Playwright 截图脚本自动复用，跳过 ~300MB bundled Chromium 下载。预检时 `preflight.sh` 会先试 `channel:'chrome'` 再试 bundled Chromium，两者均不可用才触发下载。

> **⚠️ `install --with-deps` 在 EulerOS/HCE 上不生效**（仅支持 apt-get）——需手动 `yum` 装对应系统库。依赖失败勿放弃截图，用下方正确 EulerOS 包名重试。

---

## Chromium 系统依赖包名映射（EulerOS/HCE vs Ubuntu）

`python3 -m playwright install --with-deps` 仅支持 apt-get（Debian/Ubuntu），EulerOS/HCE 上**不会自动安装系统依赖**，Chromium 启动缺库会报 `Missing libraries` 或 crash。必须手装正确包名：

```bash
# ✅ EulerOS/HCE 正确包名（与 preflight.sh ensure_playwright 一致）
yum install -y \
  atk at-spi2-atk at-spi2-core \
  alsa-lib \
  pango nss nspr cups-libs \
  libXcomposite libXdamage libXext libXfixes libXrandr libXtst libXScrnSaver \
  mesa-libgbm mesa-libGL mesa-libEGL mesa-libGLES \
  libdrm

# ❌ 错误：Ubuntu/Debian 包名在 EulerOS 上找不到（No match for argument）
# yum install -y libnspr4 libnss3 libatk1.0-0 libatspi2.0-0 libgbm1 ...
```

| 库 | HCE/EulerOS 包名 | Ubuntu/Debian 包名 |
| -- | ---------------- | ------------------ |
| NSPR | `nspr` | `libnspr4` |
| NSS | `nss` | `libnss3` |
| NSS Softoken | `nss-softokn` | — |
| NSS Util | `nss-util` | — |
| GBM | `mesa-libgbm` | `libgbm1` |
| DRM | `libdrm` | `libdrm2` |
| GL | `mesa-libGL` | `libgl1` |
| GLES | `mesa-libGLES` | `libgles2` |
| EGL | `mesa-libEGL` | `libegl1` |
| X Test | `libXtst` | `libxtst6` |
| X Fixes | `libXfixes` | `libxfixes3` |
| X Saver | `libXScrnSaver` | `libxss1` |
| X Ext | `libXext` | `libxext6` |
| Wayland | `wayland` | `libwayland-client0` |
| ATK | `atk` | `libatk1.0-0` |
| AT-SPI2 ATK | `at-spi2-atk` | `libatspi2.0-0` |
| AT-SPI2 Core | `at-spi2-core` | `at-spi2-core` |
| ALSA | `alsa-lib` | `libasound2` |
| XComposite | `libXcomposite` | `libxcomposite1` |
| XDamage | `libXdamage` | `libxdamage1` |
| XRandr | `libXrandr` | `libxrandr2` |
| Pango | `pango` | `libpango-1.0-0` |
| CUPS | `cups-libs` | `libcups2` |

> 详见 [troubleshooting.md — Chromium 依赖安装失败](troubleshooting.md#5-chromium-系统依赖安装失败euleroshce)。

---

## 安装预期警告（非错误）

```bash
python3 -m playwright install chromium # 务必用实际运行截图脚本的 Python 对应命令
```

- **"OS not officially supported" / `BEWARE: your OS is not officially supported; downloading fallback build for ubuntu24.04-arm64.`** 是**正常警告**，不要中断——Playwright 自动下载 arm64 fallback build，在 EulerOS/HCE arm64 上可正常使用。
- **Python 版本匹配陷阱：** 多 Python 并存时各自 Playwright 版本不同，可能报 `Executable doesn't exist at /root/.cache/ms-playwright/chromium_headless_shell-XXXX/...`。**始终用实际运行截图脚本的 Python 对应的命令安装**：`python3 -m playwright install chromium`，而非 `playwright install chromium`。
- **多解释器补装（`preflight.sh`）：** 系统同时存在 `python3`/`python`/`python3.x` 时 site-packages 互不可见。`ensure_deps_all_pythons` 会为每个可用解释器补装 `numpy/pillow/playwright`（真实路径去重，跳过主解释器）；**补装失败**的进 `⚠️` 日志且不写入 gate `python_bins=`（避免误报已就绪）。排查补装失败详情看 `/tmp/preflight.log`（`pip_user_install` 的 stderr 已落盘）。
- **arm64 下载慢：** Chromium 安装包 ~300MB，预估下载 >5min 时直接回退 Option 2（本地 mock + Playwright），不要等超时。若必须安装，`timeout 300 python3 -m playwright install chromium`。**arm64 国内镜像加速：** `preflight.sh` 内置 `_download_arm64_chromium_mirror` 函数，从 npmmirror 旧路径（`builds/chromium/<rev>/chromium-headless-shell-linux-arm64.zip`，~111MB）下载到 Playwright 缓存，自动重命名目录/二进制以匹配 Playwright 1.63+ 的 CFT 缓存结构，创建 `INSTALLATION_COMPLETE` 标记跳过 Playwright 自带下载。x64 架构直接设 `PLAYWRIGHT_DOWNLOAD_HOST=https://cdn.npmmirror.com/binaries/playwright` 走 CFT 镜像加速。
- **arm64 优先装系统 Chrome 跳过下载：** `browser_launch.py` 与 `preflight.sh` 已支持 Linux 复用系统 Chrome（`channel: 'chrome'`）。arm64 装 Google Chrome 后 Playwright 截图脚本自动复用，**完全跳过 ~300MB bundled Chromium 下载**。安装方式：
  - **Debian/Ubuntu arm64：** `apt-get install -y chromium-browser` 或从 [Chrome 官网](https://www.google.com/chrome/) 下载 arm64 deb
  - **EulerOS/HCE arm64：** EulerOS 官方源无 Chrome arm64 包，需从 Google 官方下载 rpm 或用第三方源；若无系统 Chrome，`preflight.sh` 自动从 npmmirror 旧路径下载 headless shell 到缓存

---

## 安装优先级：优先 $HOME 用户级（无 root / 沙箱友好）

AI DevSpace / CodeArts 沙箱等环境通常无 root 或禁止写系统目录，所有字体、Python 依赖、Playwright 浏览器应**优先安装到 `$HOME`（用户级）**，须 root 的系统级安装仅作为回退：

| 组件 | 优先（用户级） | 回退（系统级） |
| ---- | -------------- | -------------- |
| CJK 字体 | 用户字体目录 `~/.fonts` / `~/.local/share/fonts`（含下载安装的彩色 Emoji） | `sudo apt/yum`（如 `fonts-noto-cjk`、`google-noto-cjk-fonts`） |
| 彩色 Emoji 字体 | `bash <skill>/scripts/download-noto-color-emoji.sh`（**默认装到 `~/.local/share/fonts/noto-color-emoji/`**，无需 sudo） | `sudo apt install -y fonts-noto-color-emoji` / yum 包 |
| fontconfig 规则 | `~/.config/fontconfig/conf.d/`（XDG 用户目录，`preflight.sh` 自动选择） | `/etc/fonts/conf.d/` |
| numpy/pillow/playwright（Python） | `pip install --user ...`（`preflight.sh` `pip_user_install` 自动优先 `--user`） | venv / 系统 `pip` |
| Playwright Chromium 浏览器 | 默认缓存 `~/.cache/ms-playwright`（Playwright 自带，已在 $HOME） | 系统 Chrome（`channel: 'chrome'` 复用） |

> **fontconfig XDG 用户目录注意：** `resolve_fontconf_dir` 在 `~/.config/fontconfig/conf.d` 可写时优先写用户目录；`~/.fonts`/`~/.local/share/fonts` 下的字体经 `fc-cache -f` 后同样被 fontconfig 识别。无用户级可用时 `preflight.sh` 自动回退系统路径。

---

## 字体安装速查表（apt/yum 列）

CJK 与 emoji 的安装命令，按包管理器选用（**先预检已存在则跳过**）：

| 字体 | apt (Debian/Ubuntu) | yum (RHEL/CentOS/EulerOS) |
| ---- | ------------------- | ------------------------- |
| CJK 中文字体 | `sudo apt install -y fonts-noto-cjk fonts-wqy-zenhei` | `sudo yum install -y google-noto-cjk-fonts` |
| Emoji 字体 | `sudo apt install -y fonts-noto-color-emoji` | `bash <skill>/scripts/download-noto-color-emoji.sh`（**推荐**，CDN 彩色版 v2.051/Unicode 14.0+）；回退: `sudo yum install -y google-noto-emoji-fonts` |

> API `scripts/download-noto-color-emoji.sh` 从 jsDelivr CDN 下载 `NotoColorEmoji.ttf`（CBDT 彩色，Unicode 14.0+）。yum 版 `google-noto-emoji-fonts` 过旧（Unicode 10.0 单色，Chromium HarfBuzz 对 CBDT Emoji 13.0+ 渲染不稳定），仅作回退。**装完字体 → `fc-cache -f` → 再启动浏览器**（运行中进程不识别新字体）。

---

## fontconfig 中文回退配置

**背景（真实事故）：** 系统唯一 CJK 字体已装，但 `fc-match "sans-serif:lang=zh"` 仍返回 `DejaVuSans.ttf`（无 CJK）——无回退规则时 fontconfig 不把中文映射到 CJK 字体 → 中文 □□□。**仅"装字体"不够，必须确认中文命中 CJK 字体。**

**校验（通过才继续，否则写入配置）：**

```bash
match_file="$(fc-match --format='%file' 'sans-serif:lang=zh')"
case "$match_file" in
  *DejaVuSans.ttf) echo "❌ fontconfig 未把中文映射到 CJK 字体"; need_fix=1 ;;
  *) echo "✅ 中文命中 $match_file"; need_fix=0 ;;
esac
```

**写入回退规则并重建缓存（校验失败时，优先用户级 `~/.config/fontconfig/conf.d`，无 root 时不用 sudo）：**

```bash
conf_dir="${HOME}/.config/fontconfig/conf.d"
mkdir -p "$conf_dir" 2>/dev/null || conf_dir="/etc/fonts/conf.d"
cat > "$conf_dir/99-cjk-fallback.conf" <<'EOF'
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <match target="pattern">
    <test name="lang" compare="contains" qual="any"><string>zh</string></test>
    <test name="family" compare="contains" qual="any"><string>sans-serif</string></test>
    <edit name="family" mode="prepend" binding="strong"><string>Noto Sans CJK SC</string></edit>
  </match>
</fontconfig>
EOF
fc-cache -f
# 重跑上面校验，命中 CJK 字体才继续
```

> **若系统 CJK 字体名不是 `Noto Sans CJK SC`**（如只有 `Droid Sans`），把 `<string>` 换成 fontconfig 注册名（`fc-match "Droid Sans:lang=zh"` 可查）。封面/图表 HTML 里写死的字体名必须系统存在或经 `@font-face local()` 重映射，禁止随意写不存在的字体名。

---

## matplotlib `.ttc` 字体缓存问题

EulerOS 上 `google-noto-cjk-fonts` 安装的字体为 `.ttc`（TrueType Collection），matplotlib 缓存可能只索引 JP 变体，`rcParams['font.sans-serif']=['Noto Sans CJK SC']` 不生效。**回退方案：按路径加载 `.ttc`：**

```python
import matplotlib
import shutil, os
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

# 重建缓存（一次即可）
cache_dir = matplotlib.get_cachedir()
if os.path.exists(cache_dir):
    shutil.rmtree(cache_dir)

# 按路径直接加载 .ttc 字体
fp = FontProperties(fname='/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc')
# 所有 text/title/label 调用均显式传入 fontproperties=fp
ax.set_title('系统架构图', fontproperties=fp)
ax.text(x, y, label, fontproperties=fp)
```

> **含中文图表优先用 Playwright + HTML/CSS 渲染**（绕开 matplotlib `.ttc` 兼容缺陷），见 `work-preparation.md`。若确用 matplotlib：先 `pip install -U numpy pillow matplotlib`，再用多字体回退 `['Noto Sans CJK SC','DejaVu Sans']` 并监听 "Glyph missing" Warning 为硬失败。

---

## 截图有效性校验（bash）

截图生成后必须校验（**校验标准跨平台，见 `work-preparation.md`；此处为 bash 实现**）：

```bash
screenshot="/tmp/work-screenshot.png"
# 1. 文件可访问性
[ -f "$screenshot" ] || { echo "❌ 截图文件不存在，视为无效图片"; exit 1; }
# 2. 图片格式
file_type=$(file -b --mime-type "$screenshot" 2>/dev/null)
case "$file_type" in
  image/png|image/jpeg|image/webp|image/gif) ;;
  *) echo "❌ 图片格式不合法: $file_type，视为无效图片"; exit 1 ;;
esac
# 3. 文件大小
file_size=$(stat -c%s "$screenshot" 2>/dev/null || stat -f%z "$screenshot")
[ "$file_size" -lt 10240 ] && { echo "❌ 图片过小 (${file_size} bytes)，视为无效图片"; exit 1; }
# 4. 图片宽高（需 identify，可选）
if command -v identify >/dev/null 2>&1; then
  dims=$(identify -format "%w %h" "$screenshot" 2>/dev/null)
  width=$(echo "$dims" | awk '{print $1}'); height=$(echo "$dims" | awk '{print $2}')
  if [ -z "$width" ] || [ "$width" -lt 200 ] || [ "$height" -lt 200 ]; then
    echo "❌ 图片尺寸过小 (${width}x${height})，视为无效图片"; exit 1
  fi
fi
echo "✅ 截图有效性校验通过"
```

---

## 详情包 zip 打包（首选 build-detail-zip.mjs）

```bash
# 新建隔离 staging 目录（禁止复用旧目录，避免残留被打入 zip）
staging="/tmp/gallery-details-staging"
rm -rf "$staging" && mkdir -p "$staging/resources"

# 首选：打包+校验一步到位（跨平台零依赖）
node <skill>/scripts/build-detail-zip.mjs --readme "$staging/README.md" --resources "$staging/resources" --out /tmp/workDetail.zip
```

备选（仅当 build-detail-zip.mjs 不可用时）：显式指定文件打包（不要 `zip -r .`，避免打入残留）：
`cd "$staging" && zip /tmp/workDetail.zip README.md resources/*.png`，再运行 `node <skill>/scripts/validate-detail-zip.mjs <zip>` 校验。