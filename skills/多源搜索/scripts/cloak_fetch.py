#!/usr/bin/env python3
"""CloakBrowser 直调提取脚本 - skill 内部使用。

职责：启动 CloakBrowser（带反检测补丁的 Chromium），渲染页面，提取正文 Markdown。
不依赖 MCP，不依赖外部 server，纯本地执行。
正文提取使用本地 defuddle（Node.js 工具），不依赖 trafilatura/selectolax/bs4。

进程泄漏防护：
- 连接池复用（默认 2 实例）
- 50 次使用后自动回收
- 5 分钟空闲超时自动关闭
- browser.close() 10s 超时 + taskkill 强制终止兜底
- atexit + 信号处理器清理残留

运行方式：
    python scripts/cloak_fetch.py <url>

依赖：
    - Python: cloakbrowser
    - Node.js: defuddle (本地已安装)
"""

import argparse
import asyncio
import atexit
import json
import logging
import os
import signal
import subprocess
import sys
import tempfile
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

# Windows 终端默认 gbk，强制 UTF-8 避免 Unicode 输出崩
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ---- 配置 ----
POOL_SIZE = int(os.getenv("CLOAK_POOL_SIZE", "2"))
MAX_USES = int(os.getenv("CLOAK_MAX_USES", "50"))
IDLE_TIMEOUT = int(os.getenv("CLOAK_IDLE_TIMEOUT", "300"))
CLOSE_TIMEOUT = int(os.getenv("CLOAK_CLOSE_TIMEOUT", "10"))
FETCH_TIMEOUT_MS = int(os.getenv("CLOAK_FETCH_TIMEOUT", "30000"))
DEFAULT_PROXY = os.getenv("CLOAK_PROXY")

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# Windows 上 defuddle 是 .cmd，Python subprocess 需显式指定后缀
DEFUDDLE_CMD = "defuddle.cmd" if os.name == "nt" else "defuddle"


# ---- 依赖检查 ----
def _check_deps():
    missing = []
    try:
        from cloakbrowser import launch_async
    except ImportError:
        missing.append("cloakbrowser")
    try:
        subprocess.run([DEFUDDLE_CMD, "--version"], capture_output=True, check=True)
    except Exception:
        missing.append("defuddle (npm install -g defuddle)")
    if missing:
        print(f"缺少依赖: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)


# ---- URL 验证 ----
def _validate_url(url: str) -> tuple[bool, str | None]:
    if not url or not url.strip():
        return False, "URL 不能为空"
    parsed = urlparse(url.strip())
    if not parsed.scheme:
        return False, "URL 缺少协议前缀"
    if parsed.scheme not in ("http", "https"):
        return False, f"不支持的协议: {parsed.scheme}"
    if not parsed.netloc:
        return False, "URL 格式无效：缺少域名"
    return True, None


# ---- defuddle 提取 ----
def _extract_with_defuddle(html: str) -> tuple[str, str | None]:
    """使用本地 defuddle 从 HTML 提取 Markdown 和标题。

    返回: (markdown_content, title)
    """
    # 写入临时 HTML 文件
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", encoding="utf-8", delete=False) as f:
        f.write(html)
        temp_path = f.name

    try:
        # 提取 Markdown
        md_result = subprocess.run(
            [DEFUDDLE_CMD, "parse", "-m", temp_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if md_result.returncode != 0:
            raise RuntimeError(f"defuddle markdown 提取失败: {md_result.stderr}")
        content = md_result.stdout.strip()

        # 提取标题
        title_result = subprocess.run(
            [DEFUDDLE_CMD, "parse", "-j", temp_path, "-p", "title"],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        title = title_result.stdout.strip() if title_result.returncode == 0 else None
        if title == "":
            title = None

        return content, title
    finally:
        try:
            os.unlink(temp_path)
        except Exception:
            pass


# ---- 浏览器连接池 ----
@dataclass
class _PooledBrowser:
    browser: Any
    use_count: int = 0
    last_used: float = field(default_factory=time.monotonic)
    in_use: bool = False

    def touch(self) -> None:
        self.use_count += 1
        self.last_used = time.monotonic()

    @property
    def is_expired(self) -> bool:
        return self.use_count >= MAX_USES

    @property
    def is_idle(self) -> bool:
        return not self.in_use and (time.monotonic() - self.last_used > IDLE_TIMEOUT)


class BrowserPool:
    """CloakBrowser 连接池。"""

    def __init__(self, pool_size: int = POOL_SIZE, proxy: str | None = None):
        self._pool_size = pool_size
        self._proxy = proxy
        self._browsers: list[_PooledBrowser] = []
        self._semaphore = asyncio.Semaphore(pool_size)
        self._lock = asyncio.Lock()
        self._shutting_down = False
        self._idle_task: asyncio.Task | None = None

    async def _create_browser(self):
        from cloakbrowser import launch_async

        kwargs: dict = {"headless": True}
        if self._proxy:
            kwargs["proxy"] = self._proxy
        logger.info(f"新建 CloakBrowser 实例 (proxy={self._proxy})")
        return await launch_async(**kwargs)

    async def _close_browser_safe(self, browser) -> bool:
        try:
            await asyncio.wait_for(browser.close(), timeout=CLOSE_TIMEOUT)
            return True
        except asyncio.TimeoutError:
            logger.warning(f"浏览器关闭超时({CLOSE_TIMEOUT}s)，强制杀进程")
            await self._kill_browser_process(browser)
            return False
        except Exception as e:
            logger.warning(f"浏览器关闭异常: {e}")
            await self._kill_browser_process(browser)
            return False

    async def _kill_browser_process(self, browser) -> None:
        try:
            process = getattr(browser, "_process", None) or getattr(browser, "process", None)
            if process:
                pid = process.pid
                logger.info(f"强制终止浏览器进程 PID={pid}")
                try:
                    process.kill()
                except Exception:
                    pass
                try:
                    if os.name == "nt":
                        os.system(f"taskkill /F /T /PID {pid} 2>nul")
                    else:
                        os.killpg(os.getpgid(pid), signal.SIGKILL)
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"杀浏览器进程失败: {e}")

    async def _reap_idle(self) -> None:
        while not self._shutting_down:
            try:
                await asyncio.sleep(30)
                async with self._lock:
                    to_remove = []
                    for i, pb in enumerate(self._browsers):
                        if pb.is_idle or pb.is_expired:
                            logger.info(
                                f"回收浏览器 #{i} (uses={pb.use_count}, "
                                f"idle={time.monotonic() - pb.last_used:.0f}s)"
                            )
                            await self._close_browser_safe(pb.browser)
                            to_remove.append(i)
                    for i in reversed(to_remove):
                        self._browsers.pop(i)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"空闲回收异常: {e}")

    async def _get_or_create(self):
        async with self._lock:
            for pb in self._browsers:
                if not pb.in_use and not pb.is_expired:
                    pb.in_use = True
                    pb.touch()
                    return pb
            browser = await self._create_browser()
            pb = _PooledBrowser(browser=browser, use_count=1, in_use=True)
            self._browsers.append(pb)
            logger.info(f"池内共 {len(self._browsers)} 个实例")
            return pb

    async def acquire(self):
        if self._shutting_down:
            raise RuntimeError("浏览器池正在关闭")
        await self._semaphore.acquire()
        try:
            return await self._get_or_create()
        except Exception:
            self._semaphore.release()
            raise

    async def release(self, pb: _PooledBrowser) -> None:
        async with self._lock:
            pb.in_use = False
        self._semaphore.release()

    @asynccontextmanager
    async def get_browser(self):
        pb = await self.acquire()
        try:
            yield pb.browser
        finally:
            await self.release(pb)

    async def start(self) -> None:
        if self._idle_task is None:
            self._idle_task = asyncio.create_task(self._reap_idle())
            logger.info(f"浏览器连接池已启动（大小={self._pool_size}）")

    async def shutdown(self) -> None:
        if self._shutting_down:
            return
        self._shutting_down = True
        logger.info("正在关闭浏览器连接池...")
        if self._idle_task:
            self._idle_task.cancel()
            try:
                await self._idle_task
            except asyncio.CancelledError:
                pass
            self._idle_task = None
        async with self._lock:
            for i, pb in enumerate(self._browsers):
                logger.info(f"关闭浏览器 #{i} (uses={pb.use_count})")
                await self._close_browser_safe(pb.browser)
            self._browsers.clear()
        logger.info("浏览器连接池已关闭")


_pool: BrowserPool | None = None


def _get_pool(proxy: str | None = None) -> BrowserPool:
    global _pool
    if _pool is None:
        _pool = BrowserPool(proxy=proxy)
    return _pool


def _cleanup_pool() -> None:
    pool = _pool
    if pool is None:
        return
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(pool.shutdown())
        else:
            loop.run_until_complete(pool.shutdown())
    except Exception:
        pass


def _signal_handler(signum, frame) -> None:
    logger.info(f"收到信号 {signum}，开始清理...")
    _cleanup_pool()
    raise SystemExit(0)


atexit.register(_cleanup_pool)
for sig in (signal.SIGTERM, signal.SIGINT):
    try:
        signal.signal(sig, _signal_handler)
    except (ValueError, OSError):
        pass


# ---- 核心抓取 ----
async def _fetch_html_js(url: str, wait_until: str, timeout_ms: int, proxy: str | None) -> tuple[str, str]:
    pool = _get_pool(proxy)
    await pool.start()
    async with pool.get_browser() as browser:
        page = await browser.new_page(
            user_agent=DEFAULT_HEADERS["User-Agent"],
            locale="zh-CN",
            viewport={"width": 1366, "height": 900},
        )
        try:
            await page.goto(url, wait_until=wait_until, timeout=timeout_ms)
            await page.wait_for_timeout(1500)
            html = await page.content()
            final_url = page.url
            return html, final_url
        finally:
            await page.close()


async def fetch_url(
    url: str,
    wait_until: str = "networkidle",
    timeout_ms: int = FETCH_TIMEOUT_MS,
    proxy: str | None = None,
) -> str:
    is_valid, err = _validate_url(url)
    if not is_valid:
        raise ValueError(err)

    if proxy is None:
        proxy = DEFAULT_PROXY
    if proxy is None:
        raise RuntimeError(
            "CLOAK_PROXY 未配置：请通过环境变量 CLOAK_PROXY 设置 SOCKS5 代理地址"
            "（如 socks5://<PROXY_HOST>:<PROXY_PORT>），或用 --proxy 直接传入；"
            "如需无代理直连，传 --proxy ''"
        )

    timeout_ms = max(3000, min(int(timeout_ms), 120_000))
    logger.info(f"抓取: {url} (wait={wait_until}, proxy={proxy})")

    html, final_url = await _fetch_html_js(url, wait_until, timeout_ms, proxy)
    logger.info(f"渲染后 HTML 长度: {len(html)} 字符")

    content, title = _extract_with_defuddle(html)
    if not content:
        raise RuntimeError(f"defuddle 无法提取正文内容: {final_url}")

    logger.info(f"提取完成，输出长度: {len(content)} 字符")

    # 组装元数据头
    parts = []
    if title:
        parts.append(f"# {title}")
    parts.append(f"**Source:** {final_url}")
    parts.append(f"**Render mode:** js")
    parts.append("")
    parts.append("---")
    parts.append("")
    parts.append(content)
    return "\n".join(parts)


# ---- CLI ----
def main():
    _check_deps()

    parser = argparse.ArgumentParser(description="CloakBrowser 直调页面提取（defuddle 提取）")
    parser.add_argument("url", help="目标 URL")
    parser.add_argument("--proxy", default=DEFAULT_PROXY, help="SOCKS5 代理地址")
    parser.add_argument("--wait-until", default="networkidle", choices=["load", "domcontentloaded", "networkidle", "commit"])
    parser.add_argument("--timeout", type=int, default=FETCH_TIMEOUT_MS, help="超时毫秒")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    args = parser.parse_args()

    async def run():
        try:
            content = await fetch_url(
                url=args.url,
                wait_until=args.wait_until,
                timeout_ms=args.timeout,
                proxy=args.proxy,
            )
            if args.json:
                print(json.dumps({"success": True, "content": content}, ensure_ascii=False))
            else:
                print(content)
        except Exception as e:
            if args.json:
                print(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False))
            else:
                print(f"错误: {e}", file=sys.stderr)
            sys.exit(1)
        finally:
            pool = _get_pool()
            await pool.shutdown()

    asyncio.run(run())


if __name__ == "__main__":
    main()
