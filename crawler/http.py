from __future__ import annotations

import random
import time
from dataclasses import dataclass
from urllib.parse import urlsplit

import requests


class FetchError(Exception):
    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind


@dataclass
class Page:
    url: str
    html: str


class Fetcher:
    """所有来源共用按域名限流；浏览器只在来源显式申请时启动。"""

    def __init__(self, delay: float = 1.0):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (compatible; rectg/2.0)",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
        self.delay = delay
        self.last = {}
        self.playwright = self.browser = None

    def _pace(self, url):
        host = urlsplit(url).netloc
        wait = self.delay - (time.monotonic() - self.last.get(host, 0))
        if wait > 0:
            time.sleep(wait)
        self.last[host] = time.monotonic()

    def get(self, url: str, browser: bool = False, selector: str = "body") -> Page:
        if browser:
            return self._render(url, selector)
        for attempt in range(3):
            self._pace(url)
            try:
                r = self.session.get(url, timeout=(10, 30))
            except requests.RequestException:
                if attempt < 2:
                    time.sleep(2**attempt)
                    continue
                raise FetchError("network_error", "网络请求失败（已重试）") from None
            if r.status_code == 429 or r.status_code >= 500:
                if attempt < 2:
                    retry_after = r.headers.get("Retry-After", "")
                    wait = (
                        min(60, int(retry_after))
                        if retry_after.isdigit()
                        else 2 ** (attempt + 1)
                    )
                    time.sleep(wait + random.random())
                    continue
            if r.status_code != 200:
                kind = {403: "forbidden", 404: "not_found", 429: "rate_limited"}.get(
                    r.status_code, "http_error"
                )
                raise FetchError(kind, f"HTTP {r.status_code}")
            r.encoding = r.apparent_encoding or "utf-8"
            return Page(r.url, r.text)
        raise FetchError("network_error", "请求未完成")

    def _render(self, url, selector):
        self._pace(url)
        try:
            if self.browser is None:
                from playwright.sync_api import sync_playwright

                self.playwright = sync_playwright().start()
                self.browser = self.playwright.chromium.launch(headless=True)
            page = self.browser.new_page()
            try:
                response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
                status = response.status if response else 0
                if status != 200:
                    raise FetchError(
                        {403: "forbidden", 404: "not_found", 429: "rate_limited"}.get(
                            status, "http_error"
                        ),
                        f"HTTP {status}",
                    )
                page.locator(selector).first.wait_for(state="attached", timeout=15000)
                return Page(page.url, page.content())
            finally:
                page.close()
        except FetchError:
            raise
        except ImportError:
            raise FetchError(
                "browser_unavailable",
                "请安装 requirements-browser.txt 并运行 playwright install chromium",
            ) from None
        except Exception:
            raise FetchError(
                "browser_error",
                "浏览器加载失败或正文未出现；请检查浏览器安装及来源页面",
            ) from None

    def close(self):
        self.session.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
