---
name: 多源搜索
description: 统一多引擎搜索编排 skill。支持 Bing/Baidu/SearXNG/Tavily 通用引擎和 arXiv/OpenAlex/Semantic Scholar 学术引擎并行搜索，以及 webfetch/web-fetch.cmd/CloakBrowser/CDP 四级正文提取，结果合并打来源标签。不关心业务逻辑，只做搜索执行。已移除 MCP 依赖。
---

# 多源搜索

## 定位

本 skill 是**搜索编排层**，不是搜索执行层。

**职责边界**：

- 决定"调用哪个引擎、传什么参数、怎么合并结果、用哪条通道提取正文"
- 不关心"为什么搜这个"、"结果怎么用"——那是 agent 的事

## 代理基础设施

所有搜索和提取渠道**共享同一套代理配置**。

**可用代理**（按优先级排列）：

| 地址 | 协议 | 用途 |
|------|------|------|
| `socks5://<PROXY1>` | SOCKS5 | 主代理，实测最稳定 |
| `socks5://<PROXY2>` | SOCKS5 | 备用 1 |
| `socks5://<PROXY3>` | SOCKS5 | 备用 2 |

> 仅提供 SOCKS5，不假设 HTTP 代理可用。

**使用方式**：

- 直调 HTTP（webfetch/SearXNG/Tavily）：opencode 内置 webfetch 通常自动走系统代理；如未走，通过环境变量 `ALL_PROXY=socks5://<PROXY1>` 强制
- Python 脚本/requests：`pip install pysocks` 后设置 `proxies={"http": "socks5://<PROXY1>", "https": "socks5://<PROXY1>"}`
- curl：`curl.exe -x socks5://<PROXY1> <url>`
- CDP 浏览器：启动时传入 `--proxy-server=socks5://<PROXY1>`
- CloakBrowser 直调：脚本内自动读取 `CLOAK_PROXY` 环境变量或默认走 `socks5://<PROXY1>`

> 如 4040 不可用，依次尝试 4547、4545。

## 可用引擎

### 通用引擎

| 引擎 | 调用方式 | 国内可达性 | 备注 |
|------|---------|-----------|------|
| bing | CDP 浏览器 / webfetch | 可用 | 质量最高，首选 |
| baidu | CDP 浏览器 / webfetch | 可用 | 中文长尾补充 |
| searxng | 直调 HTTP | 可用 | 自建，无限量，保底/广度补充 |
| google | CDP 浏览器（Chrome，全局翻墙） | 需代理 | 国际环境首选 |
| duckduckgo | CDP 浏览器 / webfetch | 需代理 | 国际环境备用 |
| tavily | 直调 HTTP | 需代理 | 高质量+自带提取，按需启用 |

### 学术引擎

| 引擎 | 调用方式 | 国内可达性 | Key | 覆盖范围 | 备注 |
|------|---------|-----------|-----|---------|------|
| arxiv | 直调 HTTP（webfetch） | 需代理 | 无需 | 预印本（CS/物理/数学） | Atom XML，含 PDF 链接 |
| openalex | 直调 HTTP（webfetch） | 可用 | 无需（建议加 mailto） | 全学科 2.4 亿+ | JSON，覆盖最广，含引用数/OA状态 |
| semantic_scholar | 直调 HTTP（webfetch） | 需代理 | 可选（无 key 限流严） | 全学科 2 亿+ | JSON，含引用网络/影响力，限流时降频或跳过 |

> 学术引擎返回的是结构化论文元数据（标题/摘要/作者/DOI/引用数），不是网页 snippet。摘要直接作为 snippet/content，无需二次 webfetch 提取正文。arXiv 论文全文通过 PDF 链接单独下载。

**默认启用**（国内网络环境）：`bing, searxng, baidu`
**国际环境**：`google, bing, duckduckgo`
**学术调研**：`arxiv, openalex` + 通用引擎补充（Semantic Scholar 按需）
**用户指定**：通过 `project.config.md` 的 `sources` 字段覆盖

> SearXNG 是常驻默认成员，不因"质量不高"而被降级为候补。在 Bing/Google 不可达时，它是唯一能让调研循环不中断的无限量保底通道。

## 引擎配置

### SearXNG（直调）

```
URL: http://<YOUR_SEARXNG_HOST>:<PORT>/
调用方式：webfetch 工具
端点：http://<YOUR_SEARXNG_HOST>:<PORT>/search?q={query}&format=json&categories=general
返回格式：[{title, url, content}]
```

### Tavily（直调）

```
API Keys（轮换使用，一个耗尽/限流后自动换下一个）：
  1. <YOUR_TAVILY_API_KEY_1>
  2. <YOUR_TAVILY_API_KEY_2>

调用方式：webfetch 工具（POST）
端点：https://api.tavily.com/search
请求头：Authorization: Bearer <当前key>
       Content-Type: application/json
请求体：{query: "{query}", search_depth: "advanced", max_results: 10}
返回格式：{query, follow_up_questions, answer, images, results: [{title, url, content, score, raw_content}]}
```

**轮换规则**：
- 首次调用使用 Key 1
- 收到 rate limit / quota exceeded / 401 → 切换至 Key 2，重试一次
- Key 2 也失败 → 跳过 Tavily，记录到日志

> Tavily 返回的 content 字段包含提取的正文片段，raw_content 包含完整正文，无需二次抓取。search_depth: basic | advanced，advanced 可获取更完整内容。

### arXiv（直调）

```
端点：https://export.arxiv.org/api/query?search_query={query}&start=0&max_results=10&sortBy=relevance
调用方式：webfetch 工具（format: text）
返回格式：Atom XML（需解析 <entry> 标签）
限流：3秒间隔，无 Key
```

**查询语法**：
- `all:agent+memory` - 全字段搜索
- `ti:agent+memory` - 仅标题
- `abs:agent+memory` - 仅摘要
- `cat:cs.AI` - 按分类（cs.AI/cs.CL/cs.LG/cs.DB 等）
- 组合：`ti:memory+AND+cat:cs.AI`

**结果解析**（Atom XML -> 统一格式）：

```xml
<entry>
  <id>http://arxiv.org/abs/2606.24775v1</id>
  <title>论文标题</title>
  <summary>摘要全文</summary>
  <published>2026-06-23T16:34:55Z</published>
  <author><name>作者名</name></author>
  <link href="https://arxiv.org/abs/2606.24775v1" rel="alternate" type="text/html"/>
  <link href="https://arxiv.org/pdf/2606.24775v1" rel="related" type="application/pdf" title="pdf"/>
  <arxiv:primary_category term="cs.CL"/>
</entry>
```

提取为统一格式：
- `title` <- `<title>`
- `url` <- `<link rel="alternate">` 的 href（abs 页面）
- `snippet` <- `<summary>`（摘要全文，通常 500-3000 字符）
- `content` <- `<summary>`（摘要作为 content，无需二次提取）
- `pdf_url` <- `<link title="pdf">` 的 href（可选，供 02-采集 PDF 下载用）
- `authors` <- `<author><name>` 列表
- `published_date` <- `<published>`
- `categories` <- `<category term="...">` 列表

> arXiv 摘要通常较完整，可直接作为 raw 内容的摘要部分。如需全文，下载 PDF 后用 opendataloader-pdf skill 提取。

### OpenAlex（直调）

```
端点：https://api.openalex.org/works?search={query}&per-page=10&sort=relevance_score:desc
调用方式：webfetch 工具（format: text）
返回格式：JSON
限流：无 Key（建议加 mailto 参数提高礼貌配额：&mailto=research@local）
```

**查询参数**：
- `search=agent+memory` - 全文搜索
- `filter=publication_year:2024|2025` - 按年份过滤
- `filter=type:article` - 按类型过滤（article/preprint/review）
- `filter=open_access.is_oa:true` - 仅开放获取
- `per-page=10` - 每页数量（最大 200）
- `sort=cited_by_count:desc` - 按引用数排序
- `cursor=*` - 游标分页（大量结果时用）

**结果解析**（JSON -> 统一格式）：

```json
{
  "results": [{
    "id": "https://openalex.org/W2126689453",
    "title": "论文标题",
    "doi": "https://doi.org/10.1007/bf01682024",
    "publication_year": 1997,
    "cited_by_count": 363,
    "authorships": [{"author": {"display_name": "Bradley Rhodes"}}],
    "abstract_inverted_index": {"The": [0], "character": [1], ...},
    "primary_location": {
      "landing_page_url": "https://doi.org/...",
      "pdf_url": "http://...",
      "source": {"display_name": "期刊名"}
    },
    "open_access": {"is_oa": true, "oa_url": "http://..."}
  }]
}
```

提取为统一格式：
- `title` <- `title`
- `url` <- `primary_location.landing_page_url` 或 `id`
- `snippet` <- 从 `abstract_inverted_index` 还原摘要（倒排索引转正序）
- `content` <- 同 snippet
- `pdf_url` <- `primary_location.pdf_url` 或 `open_access.oa_url`（可选）
- `authors` <- `authorships[].author.display_name`
- `cited_by_count` <- `cited_by_count`
- `publication_year` <- `publication_year`
- `doi` <- `doi`
- `is_oa` <- `open_access.is_oa`

> OpenAlex 摘要是倒排索引格式（`abstract_inverted_index`），需还原为正序文本。还原方法：遍历键值对，将词放到对应位置索引，拼接成完整摘要。若无 `abstract_inverted_index`，snippet 留空。

### Semantic Scholar（直调）

```
端点：https://api.semanticscholar.org/graph/v1/paper/search?query={query}&limit=10&fields=title,url,abstract,year,authors,citationCount,externalIds,openAccessPdf
调用方式：webfetch 工具（format: text）
返回格式：JSON
限流：无 Key 100 req/5min（易触发 429）；有 Key 1 req/sec
```

**申请 Key**（可选）：https://www.semanticscholar.org/product/api#api-key-form

**查询参数**：
- `query=agent+memory` - 关键词搜索
- `limit=10` - 每页数量（最大 100）
- `fields=title,url,abstract,year,authors,citationCount,externalIds,openAccessPdf` - 指定返回字段
- `year=2024-2025` - 按年份过滤

**结果解析**（JSON -> 统一格式）：

```json
{
  "data": [{
    "paperId": "abc123",
    "title": "论文标题",
    "url": "https://www.semanticscholar.org/paper/...",
    "abstract": "摘要全文",
    "year": 2024,
    "authors": [{"name": "作者名"}],
    "citationCount": 45,
    "externalIds": {"DOI": "10.1...", "ArXiv": "2401.12345"},
    "openAccessPdf": {"url": "https://..."}
  }]
}
```

提取为统一格式：
- `title` <- `title`
- `url` <- `url` 或 `https://arxiv.org/abs/{externalIds.ArXiv}`（如有 ArXiv ID）
- `snippet` <- `abstract`
- `content` <- `abstract`
- `pdf_url` <- `openAccessPdf.url`（可选）
- `authors` <- `authors[].name`
- `cited_by_count` <- `citationCount`
- `publication_year` <- `year`
- `doi` <- `externalIds.DOI`
- `arxiv_id` <- `externalIds.ArXiv`

> Semantic Scholar 的优势是引用网络和影响力数据。如需引用追溯（D1 线索），可调用 `/graph/v1/paper/{paperId}/citations` 和 `/graph/v1/paper/{paperId}/references`。但当前适配器只做搜索，引用网络作为后续增强能力。

**429 限流处理**：无 Key 时极易触发 429。收到 429 后等待 10 秒重试一次，仍失败则跳过 Semantic Scholar，不阻塞其他引擎。有 Key 时将 Key 放入请求头 `x-api-key: <key>`。

## 正文提取渠道

正文提取与搜索引擎解耦。拿到 URL 后，按以下优先级选择提取渠道：

### 渠道 1：本地直连（webfetch）

```
工具：opencode 内置 webfetch
参数：url, format: markdown
适用：国内可直接访问的轻量页面
限制：不翻墙，不反爬
```

### 渠道 2：远程代理提取（web-fetch.cmd）

```batch
web-fetch.cmd -m <url>
```

内部实现：

```batch
@ssh <USER>@<YOUR_SSH_SERVER> -p <PORT> defuddle parse %*
```

- 通过 SSH 连接海外服务器 `<YOUR_SSH_SERVER>:<PORT>`
- 远程执行 `defuddle parse -m <url>`，将网页解析为干净 Markdown 返回
- **优势**：海外服务器直连目标站，天然翻墙；defuddle 提取质量高
- **限制**：纯静态提取，不能处理 JS 渲染页；依赖 SSH 连接
- **适用**：被墙但无需 JS 渲染的静态页面

### 渠道 3：CloakBrowser 直调（skill 内部脚本）

```batch
python scripts/cloak_fetch.py <url>
```

**CLI 参数**：

```
--proxy        代理地址（默认 socks5://<PROXY1>）
--wait-until   等待策略：load / domcontentloaded / networkidle / commit（默认 networkidle）
--timeout      超时毫秒（默认 30000）
--json         以 JSON 格式输出
```

**依赖**：
- Python: `cloakbrowser`
- Node.js: `defuddle`（本地已安装，用于渲染后 HTML → Markdown 提取）

> 正文提取使用 defuddle，不依赖 trafilatura/selectolax/bs4，更轻量、元数据更丰富。

**进程泄漏防护**（内置在脚本中）：

- 连接池复用（默认 2 实例）
- 50 次使用后自动回收
- 5 分钟空闲超时自动关闭
- `browser.close()` 10s 超时 + `taskkill /F /T` 强制终止兜底
- `atexit` + `SIGTERM/SIGINT` 信号处理器清理残留

- **优势**：headless 完全静默后台，无窗口干扰；CloakBrowser 是源码级补丁的 Chromium，能绕过 Cloudflare Turnstile 等反爬检测；提取用 defuddle，质量高
- **限制**：每次 launch 新浏览器进程，虽然有连接池但仍比 webfetch 重
- **适用**：被墙/反爬/JS 渲染页面，日常主力提取渠道

### 渠道 4：CDP 真实浏览器（本地）

直接连接已启动的真实浏览器实例，通过 Chrome DevTools Protocol 操作。

**启动脚本与端口检查**

使用前先检查端口是否已监听，未监听则启动浏览器：

```powershell
# Edge（9020，智能路由，国内直连+按需翻墙）
$edgePort = 9020
$edgeListening = Test-NetConnection -ComputerName <LOCAL_HOST> -Port $edgePort -WarningAction SilentlyContinue | Select-Object -ExpandProperty TcpTestSucceeded
if (-not $edgeListening) {
    Start-Process -FilePath "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" -ArgumentList "--remote-debugging-port=$edgePort","--profile-directory=Default" -WindowStyle Hidden
    Start-Sleep -Seconds 3
}

# Chrome（9021，全局翻墙）
$chromePort = 9021
$chromeListening = Test-NetConnection -ComputerName <LOCAL_HOST> -Port $chromePort -WarningAction SilentlyContinue | Select-Object -ExpandProperty TcpTestSucceeded
if (-not $chromeListening) {
    Start-Process -FilePath "C:\Program Files\Google\Chrome\Application\chrome.exe" -ArgumentList "--user-data-dir=<CHROME_USER_DATA_DIR>","--remote-debugging-port=$chromePort" -WindowStyle Hidden
    Start-Sleep -Seconds 3
}
```

> **关键**：Chrome 已有一个实例运行时（不带 CDP 参数），必须指定不同的 `--user-data-dir` 才能启动第二个带 CDP 的实例。Edge 则无此限制，即使已有实例在运行，再执行带 `--remote-debugging-port` 的命令也能成功启动 CDP。

**连接与提取**（Python 示例）：

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://<LOCAL_HOST>:9020")

    ctx = browser.contexts[0]

    # 打开新搜索（不覆盖已有页面）
    page = ctx.new_page()
    page.goto(url)

    # 提取时按 URL 匹配目标页（避免索引错位）
    target = next(p for p in ctx.pages if "bing.com/search" in p.url)
    content = target.content()
```

> **关键**：Google 搜索触发 reCAPTCHA 后，用户点击验证通过，此时**不要**用 `page.goto()` 重新导航，否则会再次触发验证。直接用 `browser.contexts[0].pages[0]` 提取当前页面即可。

- **优势**：真实浏览器指纹、真实 cookie 池、真实用户环境，反爬能力最强；不需要每次 launch/close 进程；**遇到 reCAPTCHA 等人机验证时，用户可手动点击通过，CDP 脚本继续提取——这是 headless 浏览器做不到的**
- **限制**：非静默——浏览器进程常驻，占用用户桌面资源；页面间共享 session，需要隔离时开新 context；多实例共享一个浏览器，需要排队或限速
- **并发约束**：同一 CDP 浏览器内**同时打开的搜索页面不要超过 3 个**（含已有页面），避免触发搜索引擎的反爬/限速/reCAPTCHA
- **页面保护**：脚本**不得**对已有页面执行 `page.goto()` 重新导航，避免覆盖用户正在查看的内容。如需打开新搜索，使用 `context.new_page()` 创建新标签页
- **适用**：CloakBrowser 也搞不定的极端反爬/登录态/需要真实用户 cookie 的场景

**CDP 也能直接做搜索**

CDP 浏览器打开 `https://www.bing.com/search?q=...` 或 `https://www.google.com/search?q=...`，提取结果页中的链接列表，可作为搜索兜底。Google 搜索可能触发 reCAPTCHA，用户点击后即可继续提取。

## 提取渠道决策树

```
拿到 URL
  ├── 国内可直接访问？
  │     └── 是 → webfetch（渠道1，最轻量）
  │     └── 否 →
  │           ├── 纯静态 / 无需 JS 渲染？
  │           │     └── 是 → web-fetch.cmd（渠道2，翻墙+干净提取）
  │           │     └── 否 → CloakBrowser 直调（渠道3，headless 静默渲染）
  │           ├── CloakBrowser 也失败？
  │                 └── 是 → CDP 浏览器（渠道4，真实浏览器兜底）
```

## 搜索渠道决策树

```
需要搜索
  ├── 是学术论文/技术文献检索？（strategy_tags 含 academic 或 research_type 为技术调研且需论文溯源）
  │     └── 是 -> 并行：arXiv + OpenAlex + 通用引擎(bing/searxng)补充
  │              └── Semantic Scholar 按需启用（有 Key 或需引用网络时）
  ├── 国内网络环境？
  │     └── 是 -> 并行：Bing(webfetch/CloakBrowser) + SearXNG + Baidu(webfetch/CloakBrowser)
  │     └── 否 -> 并行：Google(CloakBrowser/CDP) + Bing + DuckDuckGo
  ├── 需要深度内容/自带提取？
  │     └── 是 -> Tavily（按需启用）
```

**学术引擎与通用引擎的关系**：学术引擎返回论文元数据（标题/摘要/作者/引用数），通用引擎返回网页结果。两者互补：学术引擎覆盖正式发表的论文，通用引擎覆盖博客/GitHub/技术文章/社区讨论。学术调研时应两者并行，不要只用学术引擎。

## 使用方式

### 单引擎搜索

**Bing/Google/Baidu（通过 CloakBrowser 或 webfetch）**：

```python
# 首选：webfetch 直接访问搜索引擎结果页（国内可用时）
content = webfetch(f"https://www.bing.com/search?q={query}", format=markdown)
# 然后正则/CSS 提取链接列表

# 备选：CloakBrowser 直调（反爬/被墙时）
import subprocess
result = subprocess.run(
    ["python", "scripts/cloak_fetch.py", f"https://www.bing.com/search?q={query}", "--json"],
    capture_output=True, text=True
)

# 兜底：CDP 浏览器（CloakBrowser 也失败时）
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://<LOCAL_HOST>:9020")
    page = browser.new_page()
    page.goto(f"https://www.bing.com/search?q={query}")
    links = page.query_selector_all("li.b_algo h2 a")
    results = [{"title": link.inner_text(), "url": link.get_attribute("href")} for link in links]
```

**SearXNG**：

```python
import json
response = webfetch("http://<YOUR_SEARXNG_HOST>:<PORT>/search?q={query}&format=json&categories=general", format=text)
data = json.loads(response)
results = data["results"]
```

**Tavily**：

```python
response = webfetch("https://api.tavily.com/search", format=text)
# POST headers: {"Authorization": "Bearer <key>", "Content-Type": "application/json"}
# POST body: {"query": "{query}", "search_depth": "advanced", "max_results": 10}
```

### 多引擎并行

对同一个 query，**并行调用所有已启用的引擎**：

```
从 project.config.md 读取 sources 列表
parallel:
  -> 对 sources 中的 bing/baidu/google/duckduckgo：
      通过 CloakBrowser 直调或 webfetch 打开搜索结果页并提取链接
  -> 对 sources 中的 searxng：
      webfetch 调用 SearXNG API
  -> 对 sources 中的 tavily：
      webfetch POST 调用 Tavily API
  -> 对 sources 中的 arxiv：
      webfetch 调用 arXiv API（HTTPS，Atom XML 解析）
  -> 对 sources 中的 openalex：
      webfetch 调用 OpenAlex API（JSON 解析）
  -> 对 sources 中的 semantic_scholar：
      webfetch 调用 Semantic Scholar API（JSON 解析，429 降频）
-> 合并所有结果，去重（按 URL/DOI/arXiv ID），打 source_engine 标签
-> 返回统一格式的结果
```

**关键**：所有引擎必须在同一轮次中并行发出，不等一个引擎返回再发下一个。

**学术引擎去重**：同一篇论文可能同时被 arXiv、OpenAlex、Semantic Scholar 返回。去重依据优先级：arXiv ID > DOI > 标题相似度。若多篇结果指向同一论文，保留引用数最多或来源最权威的，其余合并为 `duplicate_of` 字段。

### 正文提取

按"提取渠道决策树"自动选择渠道，或显式指定：

```python
# 渠道1：本地直连
content = webfetch(url, format=markdown)

# 渠道2：远程代理提取
import subprocess
result = subprocess.run(["web-fetch.cmd", "-m", url], capture_output=True, text=True)
content = result.stdout

# 渠道3：CloakBrowser 直调
import subprocess
result = subprocess.run(
    ["python", "scripts/cloak_fetch.py", url, "--json"],
    capture_output=True, text=True
)
data = json.loads(result.stdout)
content = data["content"]

# 渠道4：CDP 浏览器
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://<LOCAL_HOST>:9020")
    page = browser.new_page()
    page.goto(url)
    content = page.content()
```

## 输入输出

**输入**：

- 搜索词列表 `[{query, intent_context?}]`
- 引擎配置 `{sources: [bing, baidu, searxng, ...]}`（从 project.config.md 读取）
- 提取渠道偏好（可选，默认按决策树自动选择）

**输出**：

```
{
  results: [
    {
      title: string,
      url: string,
      snippet: string,
      content?: string,
      source_engine: "google" | "baidu" | "bing" | "duckduckgo" | "searxng" | "tavily" | "arxiv" | "openalex" | "semantic_scholar",
      fetch_channel?: "webfetch" | "web-fetch.cmd" | "cdp" | "cloakbrowser" | "api",
      fetch_time: ISO datetime,
      trigger_query: string,
      // 以下字段仅学术引擎结果包含
      pdf_url?: string,
      authors?: [string],
      published_date?: string,
      doi?: string,
      arxiv_id?: string,
      cited_by_count?: int,
      publication_year?: int,
      is_oa?: bool,
      categories?: [string],        // arXiv 分类
      duplicate_of?: string         // 去重后指向的主结果 URL
    }
  ]
}
```

> 学术引擎结果的 `fetch_channel` 为 `"api"`，`snippet` 和 `content` 均为论文摘要（无需二次 webfetch 提取）。如需全文，使用 `pdf_url` 下载 PDF 后通过 opendataloader-pdf skill 提取。

## 质量要求

- 每个搜索结果必须正确标注来源引擎和提取渠道
- 无法连接的引擎不阻塞其他引擎（超时跳过）
- 不修改搜索结果原文内容
- SearXNG 返回为空或超时 → 静默跳过，不报错
- Tavily 返回 rate limit → 降频重试一次（换 Key），仍失败则跳过
- CloakBrowser 直调失败（launch 超时/渲染超时/提取为空）→ 跳过，记录错误，清理残留进程
- web-fetch.cmd SSH 失败时 → 跳过该渠道，尝试下一渠道
- CDP 浏览器未启动时 → 跳过该渠道，尝试启动备用实例，仍失败则记录到日志
- arXiv API 超时或返回空 → 跳过，不报错（可能是关键词不匹配 arXiv 覆盖范围）
- OpenAlex API 返回空 results → 正常情况（非所有主题都有学术论文），跳过
- OpenAlex 摘要为 null（abstract_inverted_index 缺失）→ snippet 留空，不报错，仍保留标题/作者/引用数
- Semantic Scholar 返回 429 → 等待 10 秒重试一次，仍失败则跳过，不阻塞其他引擎
- 学术引擎 XML/JSON 解析失败 → 跳过该条结果，记录原始响应片段到日志，不丢弃整批

## 架构说明

### 为何移除 MCP？

原 search-engine-mcp 提供的两个功能：
1. `search`：通过 CloakBrowser 访问搜索引擎结果页
2. `web_fetch`：通过 CloakBrowser 抓取目标 URL

两者均有更简洁的替代方案：
- **搜索**：CDP 浏览器（Edge/Chrome）直接打开结果页提取，反爬能力更强，无进程泄漏
- **提取**：webfetch（直连）→ web-fetch.cmd（远程 defuddle）→ CloakBrowser 直调（headless 静默）→ CDP（真实浏览器兜底），四级覆盖，无需 MCP 中介

MCP 层的移除带来的收益：
- 无 server 进程生命周期管理负担
- 无 stdio/SSE 序列化开销
- 无 browser pool 在 MCP 进程内的泄漏风险（泄漏的 node 进程直接可见、可杀）
- 搜索/提取逻辑完全透明，故障排查不依赖 MCP server 日志

### 进程泄漏处理

当前系统可能存在历史遗留的 node.js/Chromium 进程。清理方式：

```powershell
# 查看残留
Get-Process -Name node, chrome, msedge, chromium -ErrorAction SilentlyContinue | Select-Object Id, Name, Path

# 强制清理（谨慎使用）
Get-Process -Name node -ErrorAction SilentlyContinue | Stop-Process -Force
```

CloakBrowser 直调脚本内置了多层防护：
- 连接池复用减少 launch 次数
- 50 次使用后主动回收
- 5 分钟空闲自动关闭
- close 超时 10s 后 taskkill 兜底
- 脚本退出时 atexit 强制 shutdown

### 为何保留四种提取渠道？

| 渠道 | 重量 | 静默 | 翻墙 | 反爬 | JS 渲染 | 适用场景 |
|------|------|------|------|------|---------|---------|
| webfetch | 最轻 | 是 | 否 | 否 | 否 | 国内轻量页 |
| web-fetch.cmd | 轻 | 是 | 是（SSH） | 否 | 否 | 被墙静态页 |
| CloakBrowser | 中 | 是（headless） | 是（launch 参数） | 强 | 是 | 被墙/反爬/JS 渲染，日常主力 |
| CDP | 中 | 否（浏览器进程常驻） | 是（浏览器代理） | 最强 | 是 | CloakBrowser 搞不定的极端反爬/登录态 |

四级覆盖确保：任何 URL 至少有一条渠道能成功提取。
