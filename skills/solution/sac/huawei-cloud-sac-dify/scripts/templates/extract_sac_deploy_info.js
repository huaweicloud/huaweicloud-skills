async (page) => {
  const timeoutMs = __TIMEOUT__;

  const clickByText = async (text) => {
    const locator = page.getByRole('button', { name: text }).first();
    if (await locator.count()) {
      try { await locator.click({ timeout: 800 }); } catch {}
    }
  };

  for (const label of ['知道了', '关闭', '我知道了', '同意', '稍后再说']) {
    await clickByText(label);
  }

  await page.waitForTimeout(Math.min(timeoutMs, 4000));
  // Best-effort scroll to trigger lazy-rendered sections (price cards may be below fold).
  try {
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(700);
    await page.evaluate(() => window.scrollTo(0, 0));
  } catch {}

  const extractFromPage = async (targetPage, collectDeployLinks) =>
    await targetPage.evaluate((collectDeployLinks) => {
      const normalize = (s) => (s || '').replace(/\s+/g, ' ').trim();
      const title = normalize(
        document.querySelector('h1')?.textContent ||
          document.querySelector('h2')?.textContent ||
          document.title ||
          ''
      );

      const rawBodyText = document.body?.innerText || '';
      const bodyText = normalize(rawBodyText);
      const priceMatches = [];
      const amountPattern =
        /([¥￥]?\s*[0-9][0-9,.]*(?:\s*(?:~|-|至|到)\s*[0-9][0-9,.]*)?\s*(?:元|人民币|USD|美元)?(?:\s*\/\s*(?:小时|天|月|年|GB|TB|次))?(?:\s*\+\s*[^。；;\n]{1,40})?)/i;
      const patterns = [
        /(?:预估价格|参考价格|价格)[^。:：]{0,40}[:：]?\s*([¥￥]?\s*[0-9][0-9,.]*(?:\s*(?:~|-|至|到)\s*[0-9][0-9,.]*)?\s*(?:元|人民币|USD|美元)?(?:\s*\/\s*(?:小时|天|月|年|GB|TB|次))?(?:\s*\+\s*[^。；;\n]{1,40})?)/g,
        /(?:预估成本|参考成本|成本|花费|费用)[^。:：]{0,40}[:：]?\s*([¥￥]?\s*[0-9][0-9,.]*(?:\s*(?:~|-|至|到)\s*[0-9][0-9,.]*)?\s*(?:元|人民币|USD|美元)?(?:\s*\/\s*(?:小时|天|月|年|GB|TB|次))?(?:\s*\+\s*[^。；;\n]{1,40})?)/g,
      ];

      for (const p of patterns) {
        let m;
        while ((m = p.exec(bodyText)) !== null) {
          if (m[0]) priceMatches.push(m[0]);
        }
      }

      // Line-based fallback: catch formats like "每月预估花费：2~4元（按需计费...）"
      const lines = rawBodyText.split('\n').map((line) => normalize(line)).filter(Boolean);
      for (const line of lines) {
        if (!/(?:预估|参考|价格|成本|花费|费用|计费)/.test(line)) continue;
        const amount = line.match(amountPattern);
        if (amount) {
          priceMatches.push(line);
        }
      }

      const allLinks = [];
      const deployLinks = [];
      for (const el of Array.from(document.querySelectorAll('a[href], button'))) {
        const text = normalize(el.textContent || '');
        const href =
          el.tagName.toLowerCase() === 'a'
            ? el.getAttribute('href') || ''
            : el.closest('a')?.getAttribute('href') || '';
        if (!href) continue;

        const abs = href.startsWith('http') ? href : new URL(href, window.location.href).toString();
        const signal = `${text} ${abs}`;
        allLinks.push({ text, url: abs });
        const isTfTemplateFile = /\.tf(?:\.json)?(?:$|[?#])/i.test(abs);
        if (collectDeployLinks && (/部署|deploy|template|模板|下载|download|terraform/i.test(signal) || isTfTemplateFile)) {
          deployLinks.push({ text, url: abs });
        }
      }

      const costDocCandidates = allLinks.filter((item) =>
        /预估成本|成本规划|资源和成本|费用说明|计费说明/i.test(`${item.text} ${item.url}`) ||
        /support\.huaweicloud\.com\/.*(_02\.html|cost|price|billing)/i.test(item.url)
      );

      const dedupe = (arr) => {
        const map = new Map();
        for (const item of arr) {
          const key = `${item.url}|${item.text}`;
          if (!map.has(key)) map.set(key, item);
        }
        return Array.from(map.values());
      };

      return {
        title,
        page_url: window.location.href,
        price_text_candidates: Array.from(new Set(priceMatches)).slice(0, 20),
        deploy_links: dedupe(deployLinks),
        cost_doc_links: dedupe(costDocCandidates),
      };
    }, collectDeployLinks);

  const data = await extractFromPage(page, true);

  if (!(data.price_text_candidates || []).length) {
    const docUrl = (data.cost_doc_links || []).find((x) => /^https?:\/\//i.test(x.url))?.url || '';
    if (docUrl) {
      const docPage = await page.context().newPage();
      try {
        await docPage.goto(docUrl, { waitUntil: 'domcontentloaded', timeout: timeoutMs });
        await docPage.waitForTimeout(800);
        const docData = await extractFromPage(docPage, false);
        data.price_text_candidates = Array.from(
          new Set([...(data.price_text_candidates || []), ...(docData.price_text_candidates || [])])
        ).slice(0, 20);
        data.price_source_url = docData.page_url || docUrl;
      } catch {
        // Ignore doc-page errors; keep primary-page result.
      } finally {
        try { await docPage.close(); } catch {}
      }
    }
  }

  return '__MARKER__' + JSON.stringify(data);
}
