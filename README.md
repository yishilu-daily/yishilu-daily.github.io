# 藝世錄金融理財日報

許欣霈（Show）的每日專欄。一天兩到三則和保險、理財有關的新聞，每則是一篇文章：一張圖、用自己的話寫的說明，文末連回原媒體。網站是靜態的，放在 GitHub Pages：<https://yishilu-daily.github.io>。

不需要付費 API。RSS 只拿來選題，不會再自動把連結清單發布到首頁。

## 怎麼新增一篇

另一個工具只要把下面兩個檔案提交到 `main`，GitHub Actions 就會重畫網站。

```text
posts/2026-10-29/01-foreign-policy.webp
posts/2026-10-29/01-foreign-policy.md
posts/2026-10-29/02-claim-age.webp
posts/2026-10-29/02-claim-age.md
```

一天建議 2 到 3 篇。`01`、`02` 是當天的順序。

### 檔案格式

路徑固定是：

```text
posts/YYYY-MM-DD/NN-slug.md
posts/YYYY-MM-DD/NN-slug.webp
```

- `YYYY-MM-DD` 是台北日期。
- `NN` 是兩位數順序，例如 `01`、`02`。
- `slug` 只用小寫英文、數字和連字號，例如 `claim-age`。
- 圖片跟文章同名，放在同一層。副檔名用 `.webp` 或 `.png`。
- `date` 必須等於資料夾的日期。
- `image` 必須等於圖片檔名。

```markdown
---
title: 外幣保單賣得比較快，先問自己的現金流
date: 2026-10-29
category: 保險
summary: 銷售數字變高，不代表這張保單適合你。先看每個月出不出得來。
image: 01-foreign-policy.webp
image_credit: 示意圖（AI 生成）
source_name: 中央社
source_url: https://www.example.com/story
tags:
  - 外幣保單
  - 現金流
---

這裡用自己的話寫給客戶看，不要貼媒體全文。

## 可以放小標

- 也可以用清單
- 連結只接受 http 或 https，例如 [原文在這裡](https://www.example.com/story)

寫完把 `.md` 和圖片一起推上 `main`。
```

欄位：

| 欄位 | 必填 | 說明 |
| --- | --- | --- |
| `title` | 是 | 文章標題 |
| `date` | 是 | `YYYY-MM-DD`，要和資料夾相同 |
| `category` | 是 | 卡片上的主題標籤，例如 `稅務與傳承`、`房地產`、`保險新聞`。不決定分組 |
| `group` | 否 | 有晨報的日子，`finance` 進第三頁「理財話題」，`insurance` 進第三頁「保險新聞」。沒有晨報的日子不分組 |
| `summary` | 是 | 首頁卡片上的一兩句話 |
| `image` | 是 | 同資料夾的圖片檔名 |
| `image_credit` | 否 | 圖下的小字。沒寫時預設為 `示意圖（AI 生成）` |
| `source_name` | 是 | 原媒體名稱 |
| `source_url` | 是 | 原文章的 http(s) 連結，顯示在文末「新聞來源」 |
| `tags` | 否 | 字串清單。含 `範例` 時，頁面上會標成可替換 |

內文是 Markdown：段落、`##` 小標、`-` 清單、`1.` 清單、`**粗體**`、`*斜體*`、`[文字](https://...)`、`> 引文`。不要寫原始 HTML。

## 頁面

- 首頁打開最新一天的專欄。有 `data/briefing/YYYY-MM-DD.json` 的日子，這一期就是三頁財金晨報，下面不再另列文章。
- 第一頁是台股、美股、亞股、歐股。第二頁是匯率、定存利率、原物料、財經焦點。第三頁的「理財話題」是當天 `group: finance` 的文章，「保險新聞」是 `group: insurance` 的文章。有晨報的日子，這三頁是一張剛好塞進手機畫面的卡片。第三頁每一列是小圖、兩行標題、來源與日期；點下去打開該篇專欄。摘要在文章頁，不放在這張卡片上。
- `category` 只顯示在卡片上，當主題標籤。沒有晨報 JSON 的日子，文章維持同一份編號清單，不顯示分組標題。
- 每篇文章有自己的網址：`/column/YYYY-MM-DD/NN-slug/`。大圖、圖說、內文，最後是「新聞來源」。圖說來自 `image_credit`。
- 分享到 LINE / Facebook 時，用的是該篇圖片。
- `/archive/` 依日期瀏覽。
- 頁尾說明：內容僅供參考，不構成投資建議，也不是保險招攬。

## 自動發布

`.github/workflows/build-posts.yml` 會在 `main` 上有人推送 `posts/`（以及關於我、模板、樣式）時，重新產生 HTML 並提交。提交訊息帶 `[skip ci]`，避免工作流程一直自己觸發。

這個流程不再用每天早上的 RSS 排程去發布連結頁。

Pages 若已經是 **Deploy from a branch**、`main`、`/ (root)`，不用再改。倉庫維持公開。

若自動提交出現 403：Settings → Actions → General → Workflow permissions 改成 Read and write permissions。

## 圖片

文章預設使用 AI 插圖，檔名與 `.md` 相同，圖說是 `示意圖（AI 生成）`。沒有寫 `image_credit` 時，網站也會顯示這句。

若某一篇要改用新聞原圖，可以另外執行（需要 Pillow，每天發布網頁不用）：

```bash
python3 -m pip install pillow
python3 scripts/fetch_source_image.py posts/2026-10-29/01-foreign-policy.md
```

它讀 `source_url`，抓原文，依序找 `og:image`、`twitter:image`，再找文內第一張夠大的照片。會略過全站預設圖（例如中央社的 `pic_fb.jpg`）、logo，以及寬度大約不到 400 像素的圖。若連結是 Google 新聞，會先跟著轉址到原媒體。找到的話會覆蓋同名 `.webp`，並把 `image_credit` 改成 `圖片來源：` 加上 `source_name`。找不到就保留現有插圖。不會改文章內文。

## 選題（不會發布）

想看今天有哪些公開標題，可以在本機跑：

```bash
python3 scripts/fetch_candidates.py
```

它把候選標題印成 JSON，包含標題、來源、連結、時間。失敗的來源會略過。這個指令不寫首頁、也不提交。

## 本機預覽

```bash
python3 -m unittest scripts/test_site.py
python3 scripts/build_site.py
python3 -m http.server 8765
```

關於我的文字在 `data/about.md`。

`legacy/rss-2026-10-28/` 是舊的連結日報資料，網站不再使用。

## 財金晨報

每天的晨報是一個 JSON，放在 `data/briefing/YYYY-MM-DD.json`。檔名日期要和裡面的 `date` 相同。沒有這個檔案的日子，不顯示晨報，當天文章以同一份清單呈現。

推上 `main` 之後，GitHub Actions 會把晨報畫進首頁和 `/daily/?d=YYYY-MM-DD`。有這個檔案的日子，這一期就是三頁，可用 1/3、2/3、3/3 切換，手機上也可以左右滑。第一頁標題是「藝世錄股市動向」，內容是台股、美股、亞股、歐股。第二頁標題是「藝世錄每日匯率」，內容是匯率、定存利率、原物料、財經焦點。第三頁標題是「藝世錄財金日報」，不讀 JSON，改放當天文章：`group: finance` 是「理財話題」，`group: insurance` 是「保險新聞」。標題下只顯示日期和星期，例如 `2026/11/3（二）`。

漲跌用台灣習慣：上漲是紅字 `▲`，下跌是綠字 `▼`。`direction` 只能是 `up` 或 `down`。`change` 和 `pct` 是要顯示的文字，不要自己加箭頭。

```json
{
  "date": "2026-11-04",
  "disclaimer": "本報資訊僅供參考，不構成投資建議",
  "tw": {
    "asOf": "11/3",
    "name": "加權指數",
    "value": "0.00",
    "direction": "down",
    "change": "0.00",
    "pct": "-0.00%",
    "commentary": "一句話說明當天收盤。"
  },
  "us": {
    "asOf": "11/3 收盤",
    "rows": [
      {"name": "道瓊", "value": "0.00", "direction": "up", "change": "0.00", "pct": "+0.00%"},
      {"name": "標普500", "value": "0.00", "direction": "down", "change": "0.00", "pct": "-0.00%"},
      {"name": "那斯達克", "value": "0.00", "direction": "down", "change": "0.00", "pct": "-0.00%"},
      {"name": "費城半導體", "value": "0.00", "direction": "down", "change": "0.00", "pct": "-0.00%"}
    ]
  },
  "asia": {
    "asOf": "11/3 收盤",
    "note": "休市或特別說明寫在這裡。",
    "rows": [
      {"name": "日經225", "value": "0.00", "direction": "down", "change": "0.00", "pct": "-0.00%"},
      {"name": "韓國KOSPI", "value": "0.00", "direction": "up", "change": "0.00", "pct": "+0.00%"},
      {"name": "香港恆生", "value": "0.00", "direction": "up", "change": "0.00", "pct": "+0.00%"},
      {"name": "上證指數", "value": "0.00", "direction": "up", "change": "0.00", "pct": "+0.00%"}
    ]
  },
  "europe": {
    "asOf": "11/3 收盤",
    "rows": [
      {"name": "德國DAX", "value": "0.00", "direction": "up", "change": "0.00", "pct": "+0.00%"},
      {"name": "英國富時100", "value": "0.00", "direction": "up", "change": "0.00", "pct": "+0.00%"}
    ]
  },
  "fx": {
    "asOf": "臺銀 11/3 收盤",
    "note": "臺銀即期賣出價。▲ 表示外幣升值、新台幣貶值。",
    "rows": [
      {"name": "美元 USD", "value": "0.000", "direction": "up", "change": "0.000", "pct": "+0.00%"},
      {"name": "澳幣 AUD", "value": "0.00", "direction": "up", "change": "0.00", "pct": "+0.00%"},
      {"name": "歐元 EUR", "value": "0.00", "direction": "up", "change": "0.00", "pct": "+0.00%"},
      {"name": "日圓（100日圓）", "value": "0.00", "direction": "up", "change": "0.00", "pct": "+0.00%"}
    ]
  },
  "deposits": {
    "asOf": "牌告 11/4",
    "rows": [
      {"name": "新台幣一年期（固定）", "value": "0.000%"},
      {"name": "美元一年期", "value": "0.00%"},
      {"name": "美元一個月／三個月", "value": "0.00%"}
    ]
  },
  "commodities": {
    "asOf": "11/3",
    "rows": [
      {"name": "黃金（現貨）", "value": "0", "unit": "美元/盎司", "note": "補充說明"},
      {"name": "WTI原油", "value": "0.00", "unit": "美元/桶", "pct": "-0.00%", "direction": "down"},
      {"name": "布蘭特原油", "value": "0.00", "unit": "美元/桶", "pct": "-0.00%", "direction": "down", "note": "補充說明"}
    ]
  },
  "focus": [
    "財經焦點一，用新聞口吻，不要寫成投資建議。",
    "財經焦點二。",
    {"text": "財經焦點三。", "source": "工商時報", "date": "11/4"}
  ]
}
```

欄位都可以省略。三個分頁固定都在。某一塊沒有資料時，那一塊不畫，分頁仍保留。`focus` 可以是字串，也可以是帶 `text`、`source`、`date` 的物件，來源和日期會顯示在該則後面。第三頁的理財話題與保險新聞來自當天文章的 `group`，不要在 JSON 裡另寫。
