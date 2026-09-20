from __future__ import annotations

import importlib.util
import re
from collections import deque
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlsplit

from bs4 import BeautifulSoup

from .http import FetchError
from .links import MENTIONS, URLS, normalize, page_key
from .models import Candidate, SourceResult, SourceSpec

SOURCE_DIR = Path(__file__).parent / "sources"


def load_sources(directory=SOURCE_DIR):
    """每次重新扫描，只加载普通 .py 文件，不需要维护注册表。"""
    modules, errors, seen = {}, {}, set()
    for path in sorted(Path(directory).glob("*.py")):
        if path.name.startswith("_"):
            continue
        try:
            spec = importlib.util.spec_from_file_location(
                "rectg_source_" + path.stem, path
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            if not isinstance(module.SOURCE, SourceSpec) or not callable(
                module.collect
            ):
                raise ValueError("必须定义 SOURCE 和 collect(context)")
            key = page_key(module.SOURCE.url)
            if key in seen:
                raise ValueError("重复来源 URL")
            seen.add(key)
            modules[path.stem] = module
        except Exception as exc:
            errors[path.stem] = f"加载失败：{type(exc).__name__}: {exc}"
    return modules, errors


def parse_page(html: str, page_url: str, spec: SourceSpec):
    soup = BeautifulSoup(html, "lxml")
    scopes = soup.select(spec.selector)
    if not scopes:
        return [], [], False
    found, follow = {}, []

    def add(value, name="", hint=None):
        normalized = normalize(value)
        if normalized:
            url, username = normalized
            found.setdefault(
                username.lower(),
                Candidate(url, username, name.strip() or username, hint, page_url),
            )

    for scope in scopes:
        for node in scope.select(
            "script, style, noscript, nav, .advertisement, .adsbygoogle"
        ):
            node.decompose()
        for anchor in scope.select("a[href]"):
            value = urljoin(page_url, anchor["href"])
            parsed = urlsplit(value)
            add(value, anchor.get_text(" ", strip=True))
            # 跳转包装只解析明确指向 Telegram 的参数，不执行跳转代码。
            for key in ("url", "q", "target", "to"):
                for target in parse_qs(parsed.query).get(key, []):
                    add(target, anchor.get_text(" ", strip=True))
            if parsed.netloc == urlsplit(spec.url).netloc:
                for pattern in spec.username_routes:
                    match = re.fullmatch(pattern, parsed.path)
                    if match:
                        add(
                            "https://t.me/" + match.group(1),
                            anchor.get_text(" ", strip=True),
                        )
                if parsed.path.rstrip("/") == "/go":
                    username = parse_qs(parsed.query).get("username", [""])[0]
                    add("https://t.me/" + username)
            for attr in spec.attributes:
                if anchor.has_attr(attr):
                    for match in URLS.finditer(str(anchor[attr])):
                        add(match.group(0))
        for attr in spec.attributes:
            for node in scope.select(f"[{attr}]"):
                for match in URLS.finditer(str(node[attr])):
                    add(match.group(0), node.get_text(" ", strip=True))
        text = scope.get_text(" ", strip=True)
        for match in URLS.finditer(text):
            add(match.group(0))
        if spec.mentions:
            for match in MENTIONS.finditer(text):
                add("https://t.me/" + match.group(1))
    # 导航可位于正文之外，但必须命中该来源声明的同站路径白名单。
    host = urlsplit(spec.url).netloc
    for anchor in soup.select("a[href]"):
        url = urljoin(page_url, anchor["href"])
        p = urlsplit(url)
        if (
            p.scheme in ("http", "https")
            and p.netloc == host
            and any(
                re.fullmatch(rule, p.path + ("?" + p.query if p.query else ""))
                for rule in spec.follow
            )
        ):
            follow.append(url)
    return list(found.values()), follow, True


class SourceContext:
    def __init__(self, source_id, fetcher, max_pages=100):
        self.source_id = source_id
        self.fetcher = fetcher
        self.max_pages = min(100, max_pages)
        self.result = None

    def collect(self, spec: SourceSpec):
        result = self.result = SourceResult(self.source_id, spec.url)
        pending, visited, evidence = deque([spec.url]), set(), set()
        while pending:
            url = pending.popleft()
            key = page_key(url)
            if key in visited:
                continue
            if result.pages >= self.max_pages:
                result.status = "page_limit"
                result.errors.append(f"达到 {self.max_pages} 页上限，来源未完成")
                break
            visited.add(key)
            result.pages += 1
            try:
                page = self.fetcher.get(url)
                visited.add(page_key(page.url))
                candidates, next_pages, matched = parse_page(page.html, page.url, spec)
                if (
                    not matched or not candidates and not next_pages
                ) and spec.browser_when_empty:
                    page = self.fetcher.get(
                        url,
                        browser=True,
                        selector=spec.browser_wait_for or spec.selector,
                    )
                    candidates, next_pages, matched = parse_page(
                        page.html, page.url, spec
                    )
                if not matched:
                    raise FetchError(
                        "parse_empty", "正文选择器未匹配，页面结构可能变化"
                    )
                for item in candidates:
                    k = (item.username.lower(), page_key(item.page_url))
                    if k not in evidence:
                        evidence.add(k)
                        result.candidates.append(item)
                pending.extend(next_pages)
            except FetchError as exc:
                if result.status == "success":
                    result.status = exc.kind
                result.errors.append(f"{url}: {exc}")
        if result.status == "success" and not result.candidates:
            result.status = "parse_empty"
            result.errors.append("未提取到 Telegram 链接")
        return result
