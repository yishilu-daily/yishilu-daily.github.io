#!/usr/bin/env python3
"""專欄建置的離線測試。"""

from __future__ import annotations

import json
import sys
import unittest
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_site  # noqa: E402
import fetch_candidates  # noqa: E402
import fetch_source_image  # noqa: E402

SAMPLE = """---
title: 保費怎麼看
date: 2026-10-28
category: 保險
summary: 先看自己扛不扛得住。
image: 01-premium.webp
source_name: 中央社
source_url: https://example.com/story
tags:
  - 保費
  - 範例
---

先看現金流。

## 可以想的一件事

- 這筆保費每個月出不出得來
- 不是只看報酬率

詳見 [原文](https://example.com/story)。
"""


class SiteTests(unittest.TestCase):
    def test_front_matter_and_markdown(self):
        meta, body = build_site.parse_front_matter(SAMPLE)
        self.assertEqual(meta["title"], "保費怎麼看")
        self.assertEqual(meta["tags"], ["保費", "範例"])
        html_body = build_site.render_markdown(body)
        self.assertIn("<h3>可以想的一件事</h3>", html_body)
        self.assertIn("<li>這筆保費每個月出不出得來</li>", html_body)
        self.assertIn('href="https://example.com/story"', html_body)
        self.assertNotIn("<script>", build_site.render_markdown("小心 <script>alert(1)</script>"))
        self.assertIn("&lt;script&gt;", build_site.render_markdown("小心 <script>alert(1)</script>"))
        rewritten = fetch_source_image.update_front_matter(SAMPLE, "01-premium.webp", "圖片來源：中央社")
        self.assertTrue(rewritten.endswith(body))
        self.assertIn('image_credit: "圖片來源：中央社"', rewritten)
        self.assertTrue(fetch_source_image.is_generic_url("https://imgcdn.cna.com.tw/www/images/pic_fb.jpg"))
        self.assertFalse(fetch_source_image.is_generic_url("https://cdn.example.com/news/story-photo.jpg"))

    def test_today_posts_build_three_cards(self):
        posts = build_site.load_posts(ROOT)
        categories = {post["category"] for post in posts}
        self.assertTrue({"理財投資", "保險新聞"} <= categories)
        self.assertFalse(any(post["slug"] == "01-sample" for post in posts))
        build_site.build(ROOT)
        home = (ROOT / "index.html").read_text(encoding="utf-8")
        latest = max(post["date"] for post in posts)
        listed = [post for post in posts if not (ROOT / "data" / "briefing" / f"{post['date']}.json").exists()]
        self.assertEqual(home.count('class="issue-card"'), len(listed))
        self.assertIn(f'data-latest="{latest}"', home)
        self.assertIn('<meta property="og:title" content="藝世錄金融理財日報">', home)
        for post in posts:
            if post["date"] == latest:
                self.assertIn(post["title"], home)
        daily = (ROOT / "daily" / "index.html").read_text(encoding="utf-8")
        self.assertIn("/assets/daily.js", daily)
        self.assertIn("前一天", daily)
        self.assertIn("後一天", daily)
        for day in sorted({post["date"] for post in posts}):
            self.assertIn(f'data-issue="{day}"', daily)
            self.assertIn(f'data-issue="{day}"', home)
        if not (ROOT / "data" / "briefing" / f"{latest}.json").exists():
            self.assertNotIn("藝世錄財金晨報", home)
        else:
            self.assertIn("藝世錄財金晨報", home)
            self.assertIn("44,920.14", home)
            self.assertIn("工商時報", home)
            self.assertIn("11/3", home)
            self.assertIn("理財話題", home)
            self.assertNotIn("今日激勵", home)
            self.assertNotIn("台股連日震盪", home)
            self.assertNotIn("油價會跌", home)
            nov3 = home.split('data-issue="2026-11-03"', 1)[1]
            page3 = nov3.split('data-brief-page="2"', 1)[1].split('class="brief-disclaimer"', 1)[0]
            self.assertIn("理財話題", page3)
            self.assertIn("保險新聞", page3)
            self.assertNotIn("財經新聞", page3)
            self.assertEqual(page3.count('class="brief-story"'), 6)
            self.assertEqual(page3.count('class="issue-card"'), 0)
            self.assertIn('href="/column/2026-11-03/01-estate-tax-installments/"', page3)
            self.assertNotIn("分期是喘息空間", page3)
            self.assertIn("示意圖（AI 生成）", page3)
            self.assertIn("經濟日報 · 2026年11月3日", page3)
            self.assertIn('class="brief-fit"', home)
            oct28 = home.split('data-issue="2026-10-28"', 1)[1].split('data-issue="', 1)[0]
            self.assertNotIn("藝世錄財金晨報", oct28)
            self.assertNotIn("理財話題", oct28)
            self.assertNotIn("財經新聞", oct28)
            self.assertGreater(oct28.count('class="issue-card"'), 0)
        self.assertIn('property="og:image" content="https://yishilu-daily.github.io/assets/og.jpg"', home)
        self.assertIn('property="og:image:type" content="image/jpeg"', home)
        self.assertIn('property="og:image:width" content="1200"', home)
        self.assertIn('property="og:image:height" content="630"', home)
        self.assertNotIn("Show 的金融保險理財日報", home)
        self.assertNotIn(".webp", home[home.find("og:image"):home.find("twitter:card")])
        self.assertNotIn("01-sample", home)
        self.assertNotIn("台股ETF上週受益人數", home)
        self.assertNotIn("本日來源", home)
        self.assertNotIn('href="/profile/"', home)
        self.assertNotIn("認識我", home)
        tool_link = 'href="/tools/car-accident/" >車禍工具</a>'
        self.assertIn(tool_link, home)
        self.assertIn(tool_link, daily)
        self.assertNotIn("workers.dev", home)
        tool = (ROOT / "tools" / "car-accident" / "index.html").read_text(encoding="utf-8")
        self.assertIn("車損折舊試算", tool)
        self.assertIn("帶入民事求償清單", tool)
        self.assertIn("車禍民事損害賠償請求項目一覽表", tool)
        self.assertIn("/tools/car-accident/app.js", tool)
        self.assertIn('href="/tools/car-accident/" aria-current="page">車禍工具</a>', tool)
        about = (ROOT / "about" / "index.html").read_text(encoding="utf-8")
        self.assertNotIn('href="/profile/"', about)
        self.assertNotIn("認識我", about)
        self.assertIn("我是許欣霈（Show），在富邦人壽擔任保險業務，同時負責單位主管的工作，也是藝世錄團隊的團隊長。", about)
        for post in posts:
            article = (ROOT / "column" / post["date"] / post["slug"] / "index.html").read_text(encoding="utf-8")
            self.assertIn(post["image_url"], article)
            self.assertIn(f"/media/{post['date']}/{post['slug']}.jpg", article)
            self.assertIn('property="og:image:type" content="image/jpeg"', article)
            if post.get("image_credit"):
                self.assertIn(post["image_credit"], article)
            self.assertIn("新聞來源", article)
            self.assertIn(post["source_url"], article)
            self.assertIn('property="og:type" content="article"', article)
            self.assertIn("不構成投資建議", article)
            self.assertIn("也不是保險招攬", article)

    def test_groups_and_briefing_are_optional(self):
        published = build_site.load_briefing(ROOT, "2026-11-03")
        self.assertIsNotNone(published)
        self.assertEqual(published["date"], "2026-11-03")
        self.assertIn("44,920.14", json.dumps(published, ensure_ascii=False))
        self.assertEqual(build_site.render_briefing(None), "")
        sample = {
            "date": "2026-11-04",
            "edition": "晨間版",
            "tw": {"name": "加權指數", "value": "1.00", "direction": "up", "change": "1.00", "pct": "+0.01%", "commentary": "範例說明"},
            "us": {"rows": [{"name": "道瓊", "value": "1.00", "direction": "down", "change": "1.00", "pct": "-0.01%"}]},
            "focus": ["焦點範例"],
            "topics": [{"text": "這則不該出現", "source": "不該來源", "date": "11/9"}],
            "insurance": [{"text": "保險短訊不該出現"}],
            "motivation": "加油",
        }
        finance = {"title": "財經", "category": "稅務", "group": "finance", "order": 1, "tags": [], "image_url": "/a.webp", "image_credit": "示意圖（AI 生成）", "summary": "摘要", "html": "<p>內文</p>", "source_name": "中央社", "source_url": "https://example.com/a", "date": "2026-11-04", "slug": "01-a"}
        insurance = dict(finance, title="保險", group="insurance", order=2, slug="02-b", source_url="https://example.com/b", source_name="經濟日報")
        plain = dict(finance, title="舊文", group="", category="理財投資", order=1, slug="01-old", date="2026-10-28")
        html = build_site.render_briefing(sample, [finance, insurance, plain])
        self.assertIn("藝世錄財金晨報", html)
        self.assertIn("brief-up", html)
        self.assertIn("brief-down", html)
        self.assertIn("1/3", html)
        self.assertIn("3/3", html)
        self.assertIn("理財話題", html)
        self.assertIn("保險新聞", html)
        self.assertIn("示意圖（AI 生成）", html)
        self.assertIn("中央社 · 2026年11月4日", html)
        self.assertIn('class="brief-story"', html)
        self.assertIn('href="/column/2026-11-04/01-a/"', html)
        self.assertNotIn("摘要", html)
        self.assertNotIn("這則不該出現", html)
        self.assertNotIn("保險短訊不該出現", html)
        self.assertNotIn("今日激勵", html)
        self.assertNotIn("加油", html)
        self.assertNotIn("舊文", html)
        self.assertNotIn("昶勝軍", html)
        grouped = build_site.render_issue_groups([finance, insurance], latest=False)
        self.assertNotIn("財經新聞", grouped)
        self.assertNotIn("理財話題", grouped)
        self.assertNotIn("保險新聞", grouped)
        self.assertEqual(grouped.count('class="issue-no"'), 2)
        self.assertIn(">1</span>", grouped)
        default = build_site.render_issue_groups([plain, dict(plain, title="第二篇", order=2)], latest=False)
        self.assertNotIn("財經新聞", default)
        self.assertNotIn("理財話題", default)
        self.assertNotIn("保險新聞", default)
        self.assertIn(">2</span>", default)

    def test_workflow_publishes_posts_not_rss(self):
        workflow = (ROOT / ".github" / "workflows" / "build-posts.yml").read_text(encoding="utf-8")
        self.assertIn("posts/**", workflow)
        self.assertIn("[skip ci]", workflow)
        self.assertNotIn("cron:", workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn("daily", workflow)
        self.assertIn("data/briefing/**", workflow)
        self.assertFalse((ROOT / ".github" / "workflows" / "daily-news.yml").exists())

    def test_fetch_candidates_prints_json_and_skips_failures(self):
        feeds = [
            {"id": "good", "label": "好的", "url": "https://example.com/good.xml", "source": "中央社", "enabled": True},
            {"id": "bad", "label": "壞的", "url": "https://example.com/bad.xml", "source": "", "enabled": True},
        ]
        xml = """<?xml version="1.0"?><rss><channel><item>
        <title>外幣保單銷售增加</title>
        <link>https://example.com/a</link>
        <pubDate>Wed, 28 Oct 2026 07:00:00 GMT</pubDate>
        <source>中央社</source>
        </item></channel></rss>""".encode()

        def fetch(url: str) -> bytes:
            if url.endswith("bad.xml"):
                raise urllib.error.URLError("timed out")
            return xml

        report = fetch_candidates.collect(feeds, fetch)
        self.assertEqual(len(report["candidates"]), 1)
        self.assertEqual(report["candidates"][0]["title"], "外幣保單銷售增加")
        self.assertEqual(report["errors"][0]["id"], "bad")
        encoded = json.dumps(report)
        self.assertNotIn("index.html", encoded)


if __name__ == "__main__":
    unittest.main()
