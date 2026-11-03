#!/usr/bin/env python3
"""把 posts/ 裡的專欄渲染成靜態頁。不抓 RSS，也不會改 posts/。"""

from __future__ import annotations

import html
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POST_NAME = re.compile(r"^(\d{2})-([a-z0-9]+(?:-[a-z0-9]+)*)$")
WEEKDAYS = "一二三四五六日"
REQUIRED = ("title", "date", "category", "summary", "image", "source_name", "source_url")


def esc(value: str) -> str:
    return html.escape(value or "", quote=True)


def site_config(root: Path) -> dict:
    settings = json.loads((root / "config" / "settings.json").read_text(encoding="utf-8"))
    return {
        "site_url": settings["site_url"].rstrip("/"),
        "site_name": settings["site_name"],
        "owner_name": settings.get("owner_name") or "許欣霈",
        "timezone": settings.get("timezone") or "Asia/Taipei",
    }


def parse_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse_front_matter(text: str) -> tuple[dict, str]:
    normalized = text.replace("\r\n", "\n")
    if not normalized.startswith("---\n"):
        raise ValueError("文章必須以 --- 開頭的 front matter 開始")
    end = normalized.find("\n---\n", 4)
    if end < 0:
        raise ValueError("找不到 front matter 的結尾 ---")
    raw = normalized[4:end]
    body = normalized[end + 5 :]
    data: dict = {}
    tags: list[str] | None = None
    collecting_tags = False
    for line in raw.splitlines():
        if not line.strip():
            continue
        if collecting_tags and re.match(r"^\s+-\s+", line):
            tags.append(parse_scalar(line.split("-", 1)[1]))
            continue
        collecting_tags = False
        if ":" not in line:
            raise ValueError(f"無法讀取 front matter：{line}")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key == "tags" and value in {"", "[]"}:
            tags = []
            collecting_tags = value == ""
            data["tags"] = tags
            continue
        if key == "tags" and value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            data["tags"] = [parse_scalar(part) for part in inner.split(",") if part.strip()]
            continue
        data[key] = parse_scalar(value)
    data.setdefault("tags", [])
    return data, body.lstrip("\n")


def inline_markdown(text: str) -> str:
    escaped = esc(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", escaped)

    def link(match: re.Match) -> str:
        label, url = match.group(1), match.group(2)
        if not url.startswith(("https://", "http://")):
            return label
        return f'<a href="{esc(url)}">{label}</a>'

    return re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", link, escaped)


def render_markdown(markdown: str) -> str:
    lines = markdown.replace("\r\n", "\n").split("\n")
    blocks: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    list_kind = ""
    quote: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            blocks.append("<p>" + inline_markdown(" ".join(paragraph)) + "</p>")
            paragraph.clear()

    def flush_list() -> None:
        nonlocal list_kind
        if list_items:
            tag = "ol" if list_kind == "ol" else "ul"
            blocks.append(f"<{tag}>" + "".join(f"<li>{inline_markdown(item)}</li>" for item in list_items) + f"</{tag}>")
            list_items.clear()
            list_kind = ""

    def flush_quote() -> None:
        if quote:
            blocks.append("<blockquote><p>" + inline_markdown(" ".join(quote)) + "</p></blockquote>")
            quote.clear()

    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            flush_paragraph()
            flush_list()
            flush_quote()
            continue
        if line.strip() == "---":
            flush_paragraph()
            flush_list()
            flush_quote()
            blocks.append("<hr>")
            continue
        heading = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading:
            flush_paragraph()
            flush_list()
            flush_quote()
            level = len(heading.group(1)) + 1
            level = min(level, 4)
            blocks.append(f"<h{level}>{inline_markdown(heading.group(2))}</h{level}>")
            continue
        if line.startswith("> "):
            flush_paragraph()
            flush_list()
            quote.append(line[2:].strip())
            continue
        unordered = re.match(r"^[-*]\s+(.+)$", line)
        ordered = re.match(r"^\d+\.\s+(.+)$", line)
        if unordered or ordered:
            flush_paragraph()
            flush_quote()
            kind = "ul" if unordered else "ol"
            if list_kind and list_kind != kind:
                flush_list()
            list_kind = kind
            list_items.append((unordered or ordered).group(1).strip())
            continue
        flush_list()
        flush_quote()
        paragraph.append(line.strip())
    flush_paragraph()
    flush_list()
    flush_quote()
    return "\n".join(blocks)


def format_date(day: str) -> str:
    year, month, date = (int(part) for part in day.split("-"))
    return f"{year}年{month}月{date}日"


def weekday_label(day: str) -> str:
    moment = datetime.fromisoformat(day)
    return "星期" + WEEKDAYS[moment.weekday()]


def load_posts(root: Path) -> list[dict]:
    folder = root / "posts"
    if not folder.exists():
        return []
    posts = []
    for path in sorted(folder.glob("*/*.md")):
        day = path.parent.name
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day):
            raise SystemExit(f"日期資料夾名稱不對：{path.parent}")
        match = POST_NAME.fullmatch(path.stem)
        if not match:
            raise SystemExit(f"檔名須為 NN-slug.md，例如 01-claim-age.md：{path.name}")
        meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
        missing = [key for key in REQUIRED if not str(meta.get(key, "")).strip()]
        if missing:
            raise SystemExit(f"{path} 缺少欄位：{', '.join(missing)}")
        if meta["date"] != day:
            raise SystemExit(f"{path} 的 date 必須等於資料夾日期 {day}")
        image_name = meta["image"]
        if not re.fullmatch(r"[\w.-]+\.(webp|png)", image_name) or Path(image_name).stem != path.stem:
            raise SystemExit(f"{path} 的 image 必須是同名的 .webp 或 .png")
        image_path = path.parent / image_name
        if not image_path.is_file():
            raise SystemExit(f"找不到圖片：{image_path}")
        if not str(meta["source_url"]).startswith(("https://", "http://")):
            raise SystemExit(f"{path} 的 source_url 必須是 http(s) 連結")
        order = int(match.group(1))
        slug = path.stem
        posts.append(
            {
                "order": order,
                "slug": slug,
                "date": day,
                "title": meta["title"].strip(),
                "category": meta["category"].strip(),
                "summary": meta["summary"].strip(),
                "image": image_name,
                "image_url": f"/posts/{day}/{image_name}",
                "source_name": meta["source_name"].strip(),
                "source_url": meta["source_url"].strip(),
                "image_credit": str(meta.get("image_credit") or "").strip() or "示意圖（AI 生成）",
                "group": str(meta.get("group") or "").strip().lower(),
                "tags": list(meta.get("tags") or []),
                "body": body.strip(),
                "html": render_markdown(body),
                "path": path,
            }
        )
    posts.sort(key=lambda post: (post["date"], post["order"], post["slug"]), reverse=True)
    return posts


def prose_to_html(text: str) -> str:
    stripped = re.sub(r"<!--.*?-->", "", text or "", flags=re.S).strip()
    if not stripped:
        return ""
    return render_markdown(stripped)


def apply_template(template: str, mapping: dict[str, str]) -> str:
    page = template
    for key, value in mapping.items():
        page = page.replace(f"@@{key}@@", value)
    leftover = re.findall(r"@@[A-Z_]+@@", page)
    if leftover:
        raise RuntimeError(f"模板還有未替換的標記：{', '.join(leftover)}")
    return page


def json_ld(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")


def page(template: str, settings: dict, *, title: str, description: str, canonical: str, image: str, main: str, current: str, og_type: str = "website", og_title: str = "", body_class: str = "") -> str:
    nav = {"TODAY": "", "ARCHIVE": "", "ABOUT": ""}
    if current in nav:
        nav[current] = 'aria-current="page"'
    year = str(datetime.now().year)
    return apply_template(
        template,
        {
            "TITLE": esc(title),
            "DESCRIPTION": esc(description),
            "CANONICAL": esc(canonical),
            "OG_TYPE": esc(og_type),
            "OG_TITLE": esc(og_title or title),
            "OG_IMAGE": esc(image),
            "OG_IMAGE_ALT": esc(title),
            "EXTRA_HEAD": "",
            "JSONLD": json_ld(
                {
                    "@context": "https://schema.org",
                    "@type": "Article" if og_type == "article" else "WebPage",
                    ("headline" if og_type == "article" else "name"): title,
                    "url": canonical,
                    "description": description,
                    "image": image,
                    "inLanguage": "zh-Hant",
                    "author": {"@type": "Person", "name": settings["owner_name"]},
                }
            ),
            "NAV_TODAY": nav["TODAY"],
            "NAV_ARCHIVE": nav["ARCHIVE"],
            "NAV_ABOUT": nav["ABOUT"],
            "NAV_TOOLS": 'aria-current="page"' if current == "TOOLS" else "",
            "MAIN": main,
            "YEAR": year,
            "BODY_CLASS": body_class,
        },
    )


def cover_jpg(source: Path, dest: Path, width: int = 1200, height: int = 630) -> None:
    from PIL import Image

    image = Image.open(source).convert("RGB")
    scale = max(width / image.width, height / image.height)
    resized = image.resize((max(width, round(image.width * scale)), max(height, round(image.height * scale))), Image.Resampling.LANCZOS)
    left = max(0, (resized.width - width) // 2)
    top = max(0, (resized.height - height) // 2)
    cropped = resized.crop((left, top, left + width, top + height))
    dest.parent.mkdir(parents=True, exist_ok=True)
    cropped.save(dest, "JPEG", quality=85, optimize=False, progressive=False)


def about_lead(about_md: str) -> str:
    text = re.sub(r"<!--.*?-->", "", about_md or "", flags=re.S).strip()
    paragraphs = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip() and not block.strip().startswith("#")]
    if not paragraphs:
        return "藝世錄金融理財日報。"
    first = paragraphs[0].split("\n", 1)[0].strip()
    if "。" in first:
        return first.split("。", 1)[0] + "。"
    return first


def absolute_image(settings: dict, image_url: str) -> str:
    if image_url.startswith("http"):
        return image_url
    return settings["site_url"] + image_url


GROUP_TITLES = {"finance": "財經新聞", "insurance": "保險新聞"}


def post_group(post: dict) -> str:
    raw = str(post.get("group") or "").strip().lower()
    if raw in GROUP_TITLES:
        return raw
    category = str(post.get("category") or "").strip().lower()
    if category in GROUP_TITLES:
        return category
    return ""


def issue_dates(posts: list[dict]) -> list[str]:
    return sorted({post["date"] for post in posts})


def issue_card(post: dict, index: int, *, eager: bool) -> str:
    loading = 'fetchpriority="high"' if eager else 'loading="lazy" decoding="async"'
    flag = ""
    if "範例" in post["tags"]:
        flag = '<p class="sample-flag">範例，可替換</p>'
    credit = ""
    if post.get("image_credit"):
        credit = f'<span class="image-credit">{esc(post["image_credit"])}</span>'
    permalink = f'/column/{esc(post["date"])}/{esc(post["slug"])}/'
    return (
        "<li>"
        '<details class="issue-card">'
        "<summary>"
        '<span class="issue-media">'
        f'<img src="{esc(post["image_url"])}" alt="" width="1200" height="675" {loading}>'
        f"{credit}</span>"
        '<span class="issue-copy">'
        f'<span class="issue-kicker"><span class="issue-no">{index}</span>'
        + ("" if str(post["category"]).strip().lower() in GROUP_TITLES else f'<span class="tag">{esc(post["category"])}</span>')
        + "</span>"
        f'<span class="issue-title">{esc(post["title"])}</span>'
        f'<span class="summary">{esc(post["summary"])}</span>'
        f'<span class="issue-source">{esc(post["source_name"])} · {esc(format_date(post["date"]))}</span>'
        f"{flag}</span>"
        '<span class="hint"></span>'
        "</summary>"
        '<div class="issue-body">'
        f'<div class="prose">{post["html"]}</div>'
        '<section class="source-box"><h2>新聞來源</h2>'
        f'<p><a href="{esc(post["source_url"])}" target="_blank" rel="noopener noreferrer">{esc(post["source_name"])}</a></p>'
        "</section>"
        f'<p class="share-row"><a href="{permalink}">開啟這篇的獨立頁面</a></p>'
        "</div></details></li>"
    )


def load_briefing(root: Path, day: str) -> dict | None:
    path = root / "data" / "briefing" / f"{day}.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"{path} 必須是 JSON 物件")
    stated = str(data.get("date") or "").strip()
    if stated and stated != day:
        raise SystemExit(f"{path} 的 date 必須是 {day}")
    data["date"] = day
    return data


def _rows(data: dict, key: str) -> list[dict]:
    block = data.get(key) or {}
    if isinstance(block, dict):
        rows = block.get("rows") or []
    elif isinstance(block, list):
        rows = block
    else:
        rows = []
    return [row for row in rows if isinstance(row, dict)]


def _as_of(data: dict, key: str) -> str:
    block = data.get(key) or {}
    if isinstance(block, dict):
        return str(block.get("asOf") or "").strip()
    return ""


def _note(data: dict, key: str) -> str:
    block = data.get(key) or {}
    if isinstance(block, dict):
        return str(block.get("note") or "").strip()
    return ""


def quote_move(row: dict) -> str:
    direction = str(row.get("direction") or "").strip().lower()
    change = str(row.get("change") or "").strip()
    pct = str(row.get("pct") or "").strip()
    if direction not in {"up", "down"} and not change and not pct:
        return ""
    arrow = {"up": "▲", "down": "▼"}.get(direction, "")
    delta = f"{arrow}{change}".strip()
    pct_html = ""
    if pct:
        shown = pct if pct.startswith("(") else f"({pct})"
        pct_html = f'<span class="brief-pct">{esc(shown)}</span>'
    klass = f" brief-{direction}" if direction in {"up", "down"} else ""
    return f'<span class="brief-move{klass}"><span class="brief-delta">{esc(delta)}</span>{pct_html}</span>'


def quote_row(row: dict, *, featured: bool = False) -> str:
    unit = str(row.get("unit") or "").strip()
    value = str(row.get("value") or "").strip()
    direction = str(row.get("direction") or "").strip().lower()
    note = str(row.get("note") or "").strip()
    # Long methodology notes stay on the row as a tooltip so the one-screen card keeps a single line.
    visible_note = note if note and len(note) <= 42 else ""
    extra = f'<span class="brief-note" title="{esc(note)}">{esc(visible_note)}</span>' if visible_note else ""
    row_title = f' title="{esc(note)}"' if note and not visible_note else ""
    name = str(row.get("name") or "")
    value_klass = "brief-value"
    if direction in {"up", "down"}:
        value_klass += f" brief-{direction}"
    unit_html = f'<span class="brief-unit">{esc(unit)}</span>' if unit else ""
    klass = "brief-quote featured" if featured else "brief-quote"
    return (
        f'<div class="{klass}"{row_title}><span class="brief-name" title="{esc(name)}">{esc(name)}</span>'
        f'<span class="{value_klass}">{esc(value)}{unit_html}</span>{quote_move(row)}{extra}</div>'
    )


def brief_icon(kind: str) -> str:
    shapes = {
        "chart": '<path d="M4 16V9M8 16V5M12 16v-6M16 16V7"/>',
        "flag": '<path d="M4 3v14M4 4h10l-2 3 2 3H4"/>',
        "globe": '<circle cx="10" cy="10" r="6.5"/><path d="M3.5 10h13M10 3.5c1.8 2 1.8 11 0 13M10 3.5c-1.8 2-1.8 11 0 13"/>',
        "coins": '<ellipse cx="10" cy="6" rx="6" ry="2.2"/><path d="M4 6v3.5c0 1.2 2.7 2.2 6 2.2s6-1 6-2.2V6M4 9.5V13c0 1.2 2.7 2.2 6 2.2s6-1 6-2.2V9.5"/>',
        "bank": '<path d="M3 8.5 10 4l7 4.5M4.5 8.5V15M8 8.5V15M12 8.5V15M15.5 8.5V15M3 16h14"/>',
        "drop": '<path d="M10 3.5s4.5 4.6 4.5 7.4a4.5 4.5 0 0 1-9 0C5.5 8.1 10 3.5 10 3.5z"/>',
        "news": '<path d="M5 4h7.5v12H5zM12.5 7H15v8.2A1.8 1.8 0 0 1 13.2 17M7 7.5h4M7 10h4M7 12.5h2.5"/>',
        "coin": '<circle cx="10" cy="10" r="6.5"/><path d="M10 6.5v7M8.2 8.2h2.6a1.4 1.4 0 0 1 0 2.8H8.2"/>',
        "shield": '<path d="M10 3.2 16 5.2v4.6c0 3.2-2.4 5.6-6 6.6-3.6-1-6-3.4-6-6.6V5.2z"/>',
    }
    return (
        '<svg class="brief-icon" viewBox="0 0 20 20" aria-hidden="true" focusable="false">'
        f'{shapes.get(kind, shapes["chart"])}</svg>'
    )


SECTION_ICONS = {
    "台股": "chart",
    "美股": "flag",
    "亞股": "globe",
    "歐股": "globe",
    "匯率（兌新台幣）": "coins",
    "定存利率（臺灣銀行牌告）": "bank",
    "原物料": "drop",
    "財經焦點": "news",
    "理財話題": "coin",
    "保險新聞": "shield",
}

PAGE_TITLES = ("藝世錄股市動向", "藝世錄每日匯率", "藝世錄財金日報")


def bracket(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    if text.startswith("〔") and text.endswith("〕"):
        return text
    return f"〔{text}〕"


def short_md(day: str) -> str:
    parts = day.split("-")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        return day
    return f"{int(parts[1])}/{int(parts[2])}"


def quote_block(title: str, rows: list[dict], *, as_of: str = "", note: str = "", commentary: str = "", featured: bool = False) -> str:
    if not rows and not note and not commentary:
        return ""
    body = "".join(quote_row(row, featured=featured and index == 0) for index, row in enumerate(rows))
    comment = f'<p class="brief-commentary">{esc(commentary)}</p>' if commentary else ""
    aside = f'<p class="brief-aside">{esc(note)}</p>' if note else ""
    stamp = f'<span class="brief-asof">{esc(bracket(as_of))}</span>' if as_of else ""
    icon = brief_icon(SECTION_ICONS.get(title, "chart"))
    return f'<section class="brief-card"><header><h3>{icon}{esc(title)}</h3>{stamp}</header>{body}{comment}{aside}</section>'


def numbered_block(title: str, items: list) -> str:
    rows = []
    for index, item in enumerate(items, start=1):
        if isinstance(item, str):
            text, source, when = item, "", ""
        elif isinstance(item, dict):
            text = str(item.get("text") or "").strip()
            source = str(item.get("source") or "").strip()
            when = str(item.get("date") or "").strip()
        else:
            continue
        if not text:
            continue
        credit = " ".join(part for part in (source, when) if part)
        source_html = f'<span class="brief-source">{esc(bracket(credit))}</span>' if credit else ""
        rows.append(
            f'<li><span class="brief-index">{index}</span><p>'
            f'<span class="brief-point-text" title="{esc(text)}">{esc(text)}</span>{source_html}</p></li>'
        )
    if not rows:
        return ""
    return f'<section class="brief-card"><h3>{esc(title)}</h3><ol class="brief-points">{"".join(rows)}</ol></section>'


def render_briefing(data: dict | None, posts: list[dict] | None = None) -> str:
    if not data:
        return ""
    day = str(data.get("date") or "")
    label = ""
    if day:
        year, month, date = (int(part) for part in day.split("-"))
        weekday = "一二三四五六日"[datetime.fromisoformat(day).weekday()]
        label = f"{year}/{month}/{date}（{weekday}）"
    tw = data.get("tw") if isinstance(data.get("tw"), dict) else {}
    page1 = "".join(
        [
            quote_block(
                "台股",
                [tw] if tw.get("name") or tw.get("value") else [],
                as_of=_as_of(data, "tw"),
                commentary=str(tw.get("commentary") or "").strip(),
                note=_note(data, "tw"),
                featured=True,
            ),
            quote_block("美股", _rows(data, "us"), as_of=_as_of(data, "us")),
            quote_block("亞股", _rows(data, "asia"), as_of=_as_of(data, "asia"), note=_note(data, "asia")),
            quote_block("歐股", _rows(data, "europe"), as_of=_as_of(data, "europe")),
        ]
    )
    page2 = "".join(
        [
            quote_block("匯率（兌新台幣）", _rows(data, "fx"), as_of=_as_of(data, "fx"), note=_note(data, "fx")),
            quote_block("定存利率（臺灣銀行牌告）", _rows(data, "deposits"), as_of=_as_of(data, "deposits")),
            quote_block("原物料", _rows(data, "commodities"), as_of=_as_of(data, "commodities")),
            numbered_block("財經焦點", data.get("focus") or []),
        ]
    )
    page3 = render_post_groups(
        posts or [],
        latest=False,
        titles={"finance": "理財話題", "insurance": "保險新聞"},
        include_default=False,
        compact=True,
    )
    pages = [page1, page2, page3]
    if not pages:
        return ""
    tabs = "".join(
        f'<button type="button" class="brief-tab" data-brief-tab="{index}" aria-selected="{"true" if index == 0 else "false"}">{index + 1}/{len(pages)}</button>'
        for index in range(len(pages))
    )
    sheets = "".join(
        f'<div class="brief-page" data-brief-page="{index}" data-brief-name="{esc(PAGE_TITLES[index])}"{" hidden" if index else ""}>{html}</div>'
        for index, html in enumerate(pages)
    )
    disclaimer = str(data.get("disclaimer") or "本報資訊僅供參考，不構成投資建議").strip()
    if disclaimer and not disclaimer.startswith("※"):
        disclaimer = f"※{disclaimer}"
    opener = PAGE_TITLES[0]
    return (
        '<section class="briefing brief-lead" data-briefing>'
        '<header class="brief-head">'
        '<div class="brief-brand">'
        '<span class="brief-logo"><img src="/assets/logo.png" alt="" width="64" height="64"></span>'
        f'<h2 data-brief-title>{esc(opener)}</h2></div>'
        f'<div class="brief-tabs" role="tablist" aria-label="晨報頁面">{tabs}</div>'
        '<p class="brief-rule" aria-hidden="true"><span></span></p>'
        f'<p class="brief-edition">{esc(label)}</p></header>'
        f'<div class="brief-viewport">{sheets}</div>'
        '<footer class="brief-foot">'
        f'<p class="brief-disclaimer">{esc(disclaimer)}</p>'
        f'<p class="brief-pager" data-brief-pager>{esc(opener)} · 1/{len(pages)}</p></footer></section>'
    )


def brief_story(post: dict, index: int, *, eager: bool) -> str:
    loading = 'fetchpriority="high"' if eager else 'decoding="async"'
    credit = post.get("image_credit") or "示意圖（AI 生成）"
    permalink = f'/column/{esc(post["date"])}/{esc(post["slug"])}/'
    tag = bracket(f'{post["source_name"]} {short_md(post["date"])}'.strip())
    return (
        "<li>"
        f'<a class="brief-story" href="{permalink}">'
        '<span class="brief-thumb">'
        f'<img src="{esc(post["image_url"])}" alt="" width="128" height="72" {loading} title="{esc(credit)}"></span>'
        f'<span class="brief-story-no">{index}</span>'
        '<span class="brief-story-copy">'
        f'<span class="brief-story-title">{esc(post["title"])}</span>'
        f'<span class="thumb-credit">{esc(credit)}</span>'
        f'<span class="brief-story-source">{esc(tag)}</span></span>'
        "</a></li>"
    )


def render_post_groups(posts: list[dict], *, latest: bool, titles: dict[str, str] | None = None, include_default: bool = True, compact: bool = False) -> str:
    buckets: dict[str, list[dict]] = {"finance": [], "insurance": [], "": []}
    for post in posts:
        buckets[post_group(post)].append(post)
    if titles is None:
        cards = []
        for index, post in enumerate(posts, start=1):
            cards.append(issue_card(post, index, eager=latest and index == 1))
        return f'<ol class="issue-list">{"".join(cards)}</ol>'
    parts: list[str] = []
    eager_used = False
    keys = ["finance", "insurance"] + ([""] if include_default else [])
    for key in keys:
        chosen = buckets[key]
        if not chosen:
            continue
        label = titles.get(key) or ""
        cards = []
        for index, post in enumerate(chosen, start=1):
            eager = latest and not eager_used
            eager_used = eager_used or eager
            if compact:
                cards.append(brief_story(post, index, eager=eager))
            else:
                cards.append(issue_card(post, index, eager=eager))
        if compact:
            icon = brief_icon(SECTION_ICONS.get(label, "coin")) if label else ""
            heading = f"<header><h3>{icon}{esc(label)}</h3></header>" if label else ""
            parts.append(f'<section class="brief-card">{heading}<ol class="brief-stories">{"".join(cards)}</ol></section>')
        else:
            heading = f'<h2 class="issue-group">{esc(label)}</h2>' if label else ""
            parts.append(f'{heading}<ol class="issue-list">{"".join(cards)}</ol>')
    return "".join(parts)


def render_issue_groups(posts: list[dict], *, latest: bool) -> str:
    return render_post_groups(posts, latest=latest, titles=None)


def render_issues(posts: list[dict]) -> str:
    if not posts:
        return (
            '<div class="issue-app" data-issue-app data-dates="[]" data-latest="">'
            '<p class="eyebrow">Daily Column</p><h1>藝世錄金融理財日報</h1>'
            '<p class="lead">還沒有文章。新的一篇放進 posts/ 之後就會出現在這裡。</p></div>'
        )
    grouped: dict[str, list[dict]] = {}
    for post in posts:
        grouped.setdefault(post["date"], []).append(post)
    dates = sorted(grouped)
    latest = dates[-1]
    sections = []
    for day in dates:
        chosen = sorted(grouped[day], key=lambda post: post["order"])
        briefing_data = load_briefing(ROOT, day)
        if briefing_data:
            body = render_briefing(briefing_data, chosen)
        else:
            body = render_issue_groups(chosen, latest=day == latest)
        hidden = "" if day == latest else " hidden"
        sections.append(
            f'<section class="issue" data-issue="{esc(day)}"{hidden}>'
            '<p class="eyebrow">Daily Column</p>'
            f"<h1>{esc(format_date(day))}</h1>"
            f'<p class="edition-meta">{weekday_label(day)} · {len(chosen)} 篇</p>'
            f"{body}</section>"
        )
    prev_day = dates[-2] if len(dates) > 1 else ""
    if prev_day:
        prev_html = f'<a class="day-nav" data-issue-prev href="/daily/?d={esc(prev_day)}">前一天</a>'
    else:
        prev_html = '<a class="day-nav" data-issue-prev aria-disabled="true">前一天</a>'
    next_html = '<a class="day-nav" data-issue-next aria-disabled="true">後一天</a>'
    dates_attr = esc(json.dumps(dates, ensure_ascii=False))
    return (
        f'<div class="issue-app" data-issue-app data-dates="{dates_attr}" data-latest="{esc(latest)}">'
        '<form class="day-switch" action="/daily/" method="get">'
        f"{prev_html}"
        '<label class="day-field">'
        f'<input data-issue-date id="issue-date" type="date" name="d" min="{esc(dates[0])}" max="{esc(latest)}" value="{esc(latest)}" aria-label="選擇日期" required>'
        "</label>"
        f"{next_html}</form>"
        '<p class="issue-empty" data-issue-empty hidden><span data-empty-label></span>這一天還沒有專欄。用前一天或後一天，跳到最近有文章的日子。</p>'
        + "".join(sections)
        + '<script src="/assets/daily.js?v=3" defer></script>'
        '<script src="/assets/briefing.js?v=3" defer></script></div>'
    )


def card(post: dict, *, eager: bool) -> str:
    loading = 'fetchpriority="high"' if eager else 'loading="lazy" decoding="async"'
    flag = ""
    if "範例" in post["tags"]:
        flag = '<p class="sample-flag">範例，可替換</p>'
    credit = ""
    if post.get("image_credit"):
        credit = f'<span class="image-credit">{esc(post["image_credit"])}</span>'
    return (
        f'<a class="feature-card" href="/column/{esc(post["date"])}/{esc(post["slug"])}/">'
        '<span class="feature-media">'
        f'<img src="{esc(post["image_url"])}" alt="" width="1200" height="675" {loading}>'
        f"{credit}</span>"
        '<span class="feature-body">'
        f'<p class="tag">{esc(post["category"])}</p>'
        f'<h2>{esc(post["title"])}</h2>'
        f'<p class="summary">{esc(post["summary"])}</p>'
        f'<p class="meta"><time datetime="{esc(post["date"])}">{esc(format_date(post["date"]))}</time></p>'
        f"{flag}</span></a>"
    )


def render_home(posts: list[dict], about_html: str) -> str:
    del about_html
    return render_issues(posts)


def render_article(post: dict) -> str:
    flag = ""
    if "範例" in post["tags"]:
        flag = '<p class="sample-flag">這是範例文章，正式專欄會整組替換。</p>'
    credit = ""
    if post.get("image_credit"):
        credit = f'<figcaption class="image-credit">{esc(post["image_credit"])}</figcaption>'
    figure = (
        '<figure class="article-figure">'
        f'<img class="article-cover" src="{esc(post["image_url"])}" alt="{esc(post["title"])}" width="1200" height="675">'
        f"{credit}</figure>"
    )
    return (
        "<article>"
        f"{figure}"
        '<p class="eyebrow">Column</p>'
        f'<p class="tag">{esc(post["category"])}</p>'
        f'<h1>{esc(post["title"])}</h1>'
        f'<p class="edition-meta"><time datetime="{esc(post["date"])}">{esc(format_date(post["date"]))}</time> · {weekday_label(post["date"])}</p>'
        f"{flag}<div class=\"prose\">{post['html']}</div>"
        '<section class="source-box"><h2>新聞來源</h2>'
        f'<p><a href="{esc(post["source_url"])}" target="_blank" rel="noopener noreferrer">{esc(post["source_name"])}</a></p>'
        "</section></article>"
    )


def render_archive(posts: list[dict]) -> str:
    dates = []
    for post in posts:
        if post["date"] not in dates:
            dates.append(post["date"])
    rows = []
    for day in dates:
        count = sum(1 for post in posts if post["date"] == day)
        rows.append(
            f'<li><a href="/daily/?d={esc(day)}"><time datetime="{esc(day)}">{esc(format_date(day))}</time>'
            f'<span>{weekday_label(day)} · {count} 篇</span></a></li>'
        )
    body = "".join(rows) or '<p class="empty">還沒有文章。</p>'
    return (
        '<article class="archive-block"><p class="eyebrow">Archive</p><h1>專欄彙整</h1>'
        '<p class="lead">每一天的文章都留在這裡。</p>'
        f'<ol class="archive-list">{body}</ol></article>'
    )


def render_day(day: str, posts: list[dict]) -> str:
    chosen = [post for post in posts if post["date"] == day]
    chosen.sort(key=lambda post: post["order"])
    cards = "".join(card(post, eager=index == 0) for index, post in enumerate(chosen))
    dates = sorted({post["date"] for post in posts})
    index = dates.index(day)
    links = []
    if index > 0:
        links.append(f'<a href="/daily/?d={dates[index - 1]}">前一天</a>')
    else:
        links.append("<span></span>")
    if index < len(dates) - 1:
        links.append(f'<a href="/daily/?d={dates[index + 1]}">後一天</a>')
    else:
        links.append("<span></span>")
    return (
        '<article class="day-lead">'
        '<p class="eyebrow">Daily Column</p>'
        f'<p class="kicker">當日專欄</p><h1>{esc(format_date(day))}</h1>'
        f'<p class="edition-meta">{weekday_label(day)} · {len(chosen)} 篇</p>'
        f'<div class="feature-list">{cards}</div>'
        f'<p class="pager">{"".join(links)}</p></article>'
    )


def render_about(about_html: str) -> str:
    return (
        '<article class="about"><p class="eyebrow">About</p><h1>關於 藝世錄</h1>'
        f'<div class="prose">{about_html}</div>'
        '<p class="share-row"><a href="/">回到今天的專欄</a></p></article>'
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def remove_stale(root: Path, posts: list[dict]) -> None:
    keep_days = {post["date"] for post in posts}
    keep_slugs = {(post["date"], post["slug"]) for post in posts}
    archive = root / "archive"
    if archive.exists():
        for child in archive.iterdir():
            if child.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", child.name) and child.name not in keep_days:
                shutil.rmtree(child)
    media = root / "media"
    keep_media = {post["date"] + "/" + post["slug"] + ".jpg" for post in posts}
    if media.exists():
        parents = set()
        for jpg in list(media.glob("*/*.jpg")):
            key = f"{jpg.parent.name}/{jpg.name}"
            parents.add(jpg.parent)
            if key not in keep_media:
                jpg.unlink()
        for parent in parents:
            if parent.exists() and not any(parent.iterdir()):
                parent.rmdir()
    column = root / "column"
    if column.exists():
        for day_dir in column.iterdir():
            if not day_dir.is_dir():
                continue
            if day_dir.name not in keep_days:
                shutil.rmtree(day_dir)
                continue
            for slug_dir in day_dir.iterdir():
                if slug_dir.is_dir() and (day_dir.name, slug_dir.name) not in keep_slugs:
                    shutil.rmtree(slug_dir)


def build(root: Path) -> list[dict]:
    settings = site_config(root)
    posts = load_posts(root)
    template = (root / "templates" / "layout.html").read_text(encoding="utf-8")
    about_html = prose_to_html((root / "data" / "about.md").read_text(encoding="utf-8")) if (root / "data" / "about.md").exists() else ""
    site = settings["site_url"]
    about_md = (root / "data" / "about.md").read_text(encoding="utf-8") if (root / "data" / "about.md").exists() else ""
    site_description = about_lead(about_md)
    cover_jpg(root / "assets" / "og.png", root / "assets" / "og.jpg")
    brand_image = site + "/assets/og.jpg"
    share_images = {}
    for post in posts:
        dest = root / "media" / post["date"] / f"{post['slug']}.jpg"
        cover_jpg(root / "posts" / post["date"] / post["image"], dest)
        share_images[post["slug"]] = absolute_image(settings, f"/media/{post['date']}/{post['slug']}.jpg")
    lead = None
    latest_day = ""
    if posts:
        latest_day = max(post["date"] for post in posts)
        lead = min((post for post in posts if post["date"] == latest_day), key=lambda post: post["order"])
    fit = "brief-fit" if latest_day and load_briefing(root, latest_day) else ""
    home_title = f"{format_date(lead['date'])}｜{settings['site_name']}" if lead else settings["site_name"]
    write_text(
        root / "index.html",
        page(
            template,
            settings,
            title=home_title,
            og_title=settings["site_name"],
            description=site_description,
            canonical=site + "/",
            image=brand_image,
            main=render_home(posts, about_html),
            current="TODAY",
            body_class=fit,
        ),
    )
    write_text(
        root / "daily" / "index.html",
        page(
            template,
            settings,
            title=f"每日專欄｜{settings['site_name']}",
            og_title=settings["site_name"],
            description=site_description,
            canonical=site + "/daily/",
            image=brand_image,
            main=render_issues(posts),
            current="TODAY",
            body_class=fit,
        ),
    )
    remove_stale(root, posts)
    for day in sorted({post["date"] for post in posts}):
        write_text(
            root / "archive" / day / "index.html",
            page(
                template,
                settings,
                title=f"{format_date(day)}｜{settings['site_name']}",
                description=f"{format_date(day)}的專欄。",
                canonical=f"{site}/archive/{day}/",
                image=share_images[min((post for post in posts if post["date"] == day), key=lambda post: post["order"])["slug"]],
                main=render_day(day, posts),
                current="ARCHIVE",
            ),
        )
    for post in posts:
        canonical = f"{site}/column/{post['date']}/{post['slug']}/"
        write_text(
            root / "column" / post["date"] / post["slug"] / "index.html",
            page(
                template,
                settings,
                title=f"{post['title']}｜{settings['site_name']}",
                description=post["summary"],
                canonical=canonical,
                image=share_images[post["slug"]],
                main=render_article(post),
                current="",
                og_type="article",
            ),
        )
    write_text(
        root / "archive" / "index.html",
        page(
            template,
            settings,
            title=f"專欄彙整｜{settings['site_name']}",
            description="過去每一天的專欄。",
            canonical=site + "/archive/",
            image=brand_image,
            main=render_archive(posts),
            current="ARCHIVE",
        ),
    )
    tool_main = (root / "templates" / "car-tool.html").read_text(encoding="utf-8")
    write_text(
        root / "tools" / "car-accident" / "index.html",
        page(
            template,
            settings,
            title="藝世錄｜車禍求償整合工具",
            og_title="藝世錄｜車禍求償整合工具",
            description="車損折舊與民事求償整合工具",
            canonical=site + "/tools/car-accident/",
            image=brand_image,
            main=tool_main,
            current="TOOLS",
        ),
    )
    write_text(
        root / "about" / "index.html",
        page(
            template,
            settings,
            title=f"關於 藝世錄｜{settings['site_name']}",
            description=f"{settings['owner_name']}（Show）的{settings['site_name']}。",
            canonical=site + "/about/",
            image=brand_image,
            main=render_about(about_html),
            current="ABOUT",
        ),
    )
    urls = [site + "/", site + "/daily/", site + "/archive/", site + "/about/", site + "/tools/car-accident/"]
    urls.extend(f"{site}/archive/{day}/" for day in sorted({post["date"] for post in posts}))
    urls.extend(f"{site}/column/{post['date']}/{post['slug']}/" for post in posts)
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    lines.extend(f"  <url><loc>{esc(url)}</loc></url>" for url in urls)
    lines.append("</urlset>")
    write_text(root / "sitemap.xml", "\n".join(lines) + "\n")
    print(f"完成：{len(posts)} 篇文章")
    for post in sorted(posts, key=lambda item: (item["date"], item["order"])):
        print(f"  {post['date']} {post['slug']} {post['title']}")
    return posts


def main() -> int:
    build(ROOT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
