# Mock Server + Screenshot Template（Option 2 专用）

进程内 Node http server + mock API + 同进程 Playwright 截图。适用于项目起不来、需 mock 后端数据后本地截图的场景。

> **何时读本文件**：仅 Option 2（`work-preparation.md#option-2-local-playwright-with-mock-data`）场景需要。Option 1（项目可运行直接截图）不需要。

## Mock 数据铁律

1. **No `undefined` or missing fields** — every field the frontend reads must be present with a valid value. Inspect the frontend source code to determine the exact response shape.
2. **No empty lists** — all array fields must contain at least one realistic sample item so the rendered page shows actual content.
3. **Correct data types** — match the types the frontend expects: strings for names, numbers for counts, ISO 8601 strings for dates, booleans for flags, proper nested objects.
4. **Response results cannot be empty** — every mock response must contain meaningful data.

## 完整脚本模板

```javascript
import { chromium } from "playwright"
import http from "http", fs from "fs", path from "path"

const PUBLIC_DIR = "path/to/frontend"
const OUTPUT = "/tmp/work-screenshot.png"  // Windows: path.join(os.tmpdir(), "work-screenshot.png")

// Mock data — fully populated, no undefined, no empty arrays, correct types
// 按前端实际调用的端点补充，以下为完整示例
const MOCK_API = {
  "/api/health": { status: "ok" },
  "/api/dashboard": {
    assetTotal: 42,
    pendingTasks: 3,
    overdueTasks: 1,
    completionTrend: [
      { month: "2026-05", completed: 12 },
      { month: "2026-06", completed: 18 },
      { month: "2026-07", completed: 25 },
    ],
    recentActivity: [{ id: 1, action: "发布新版本 v2.1.0", timestamp: "2026-07-29T10:30:00Z" }],
  },
  "/api/assets": { items: [{ id: 1, name: "应用实例", status: "running", region: "华北-北京" }] },
  "/api/tasks": { items: [{ id: "T-101", title: "完成版本发布", assignee: "张三", status: "进行中", dueDate: "2026-08-15" }] },
  "/api/settings": { theme: "dark", language: "zh-CN", notifications: { email: true, sms: false } },
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, "http://localhost")
  if (MOCK_API[url.pathname]) {
    res.writeHead(200, { "Content-Type": "application/json" })
    return res.end(JSON.stringify(MOCK_API[url.pathname]))
  }
  const filePath = path.join(PUBLIC_DIR, url.pathname === "/" ? "/index.html" : url.pathname)
  const mime = { ".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "application/javascript; charset=utf-8", ".png": "image/png", ".jpg": "image/jpeg", ".svg": "image/svg+xml" }
  fs.existsSync(filePath)
    ? (res.writeHead(200, { "Content-Type": mime[path.extname(filePath)] || "application/octet-stream" }),
       res.end(fs.readFileSync(filePath)))
    : (res.writeHead(404, { "Content-Type": "application/json" }), res.end('{"error":"Not Found"}'))
})

server.listen(0, async () => {
  const port = server.address().port
  const browser = await chromium.launch({ headless: true })
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } })
  page.on("pageerror", (err) => console.log("Page error:", err.message))
  await page.goto(`http://127.0.0.1:${port}/index.html`, { waitUntil: "domcontentloaded", timeout: 30000 })
  await page.evaluate(() => document.fonts.ready)
  await new Promise(r => setTimeout(r, 2000))
  await page.screenshot({ path: OUTPUT, fullPage: false })
  await browser.close(); server.close()
})
```

> **Python 替代方案：** 上述模板为 Node 版本。Python Playwright 等价方案可用 `http.server` + `playwright.sync_api` 实现同等功能（进程内启动 HTTP server + 同进程截图 + `server.shutdown()`），或直接用 `screenshot_guard.py`（已含字形自检 + 兜底注入），无需手动编写 mock server。

> Node 自写脚本须放 `scripts/` 下运行以解析 `node_modules/playwright`（见 [windows-setup.md](windows-setup.md)）。Python 版 `screenshot_guard.py` 经 `pip install playwright` 全局可用，无此目录限制。