from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from crawler.http import FetchError, Page
from crawler.links import normalize, page_key
from crawler.models import SourceSpec
from crawler.source_engine import SourceContext, load_sources, parse_page
from crawler.pipeline import discover

FIXTURES = Path(__file__).parent / "fixtures/sources"


class FakeFetcher:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        value = self.pages[(url, True)] if kwargs.get("browser") else self.pages[url]
        if isinstance(value, Exception):
            raise value
        return Page(url, value)


class SourceTests(unittest.TestCase):
    def test_discovered_sources_have_matching_fixtures(self):
        modules, errors = load_sources()
        self.assertEqual(errors, {})
        self.assertTrue(modules)
        manifest = json.loads((FIXTURES / "manifest.json").read_text())
        self.assertTrue(set(modules) <= set(manifest))
        for name, module in modules.items():
            with self.subTest(source=name):
                self.assertEqual(
                    page_key(module.SOURCE.url), page_key(manifest[name]["url"])
                )
                html = (FIXTURES / (name + ".html")).read_text()
                found, _, matched = parse_page(html, module.SOURCE.url, module.SOURCE)
                self.assertTrue(matched)
                self.assertEqual([x.url for x in found], manifest[name]["expected"])

    def test_remove_module_and_invalid_or_duplicate_module(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)
            code = 'from crawler.models import SourceSpec\nSOURCE=SourceSpec("test","https://example.com/","main")\ndef collect(context):return context.collect(SOURCE)\n'
            (p / "a.py").write_text(code)
            (p / "b.py").write_text(code)
            (p / "broken.py").write_text("syntax !!!")
            modules, errors = load_sources(p)
            self.assertEqual(list(modules), ["a"])
            self.assertEqual(set(errors), {"b", "broken"})
            (p / "a.py").unlink()
            modules, _ = load_sources(p)
            self.assertEqual(list(modules), ["b"])

    def test_telegram_normalization(self):
        for value in [
            "https://t.me/ExampleBot?start=x",
            "http://telegram.me/examplebot/2",
            "https://t.me/s/examplebot/3",
            "tg://resolve?domain=ExampleBot",
        ]:
            self.assertEqual(normalize(value)[0], "https://t.me/examplebot")
        for value in [
            "https://t.me/+abc",
            "https://t.me/joinchat/abc",
            "https://t.me/c/123/4",
            "https://t.me/addstickers/foo",
            "https://t.me/proxy?server=x",
            "https://t.me/setlanguage/zh",
            "https://other.com/ExampleBot",
        ]:
            self.assertIsNone(normalize(value))

    def test_mentions_wrappers_routes_and_click_attributes(self):
        spec = SourceSpec(
            "test",
            "https://example.com/",
            "article",
            mentions=True,
            attributes=("onclick",),
            username_routes=(r"/detail/([A-Za-z0-9_]+)/?",),
        )
        html = """<nav>@OutsideBot</nav><article>@ExampleBot @Bad中文 mail@example.com
        <a href="/detail/SecondBot/">second</a>
        <a href="https://google.com/url?q=https%3A%2F%2Ft.me%2FThirdBot">wrapped</a>
        <li onclick="window.open('https://t.me/FourthBot','_blank')">fourth</li></article>"""
        found, _, _ = parse_page(html, spec.url, spec)
        self.assertEqual(
            {x.url for x in found},
            {
                "https://t.me/" + x
                for x in ["examplebot", "secondbot", "thirdbot", "fourthbot"]
            },
        )

    def test_pagination_cycle_cap_and_external_link(self):
        spec = SourceSpec(
            "test", "https://example.com/", "main", follow=(r"/page/\d+",)
        )
        html = '<main><a href="https://t.me/ExampleBot">bot</a><a href="/page/2">next</a><a href="https://outside.com/page/3">ad</a><a href="/login">login</a></main>'
        fetcher = FakeFetcher({spec.url: html, "https://example.com/page/2": html})
        result = SourceContext("test", fetcher, 1).collect(spec)
        self.assertEqual(result.status, "page_limit")
        self.assertEqual(result.pages, 1)
        result = SourceContext("test", fetcher, 3).collect(spec)
        self.assertEqual(result.status, "success")
        self.assertEqual(result.pages, 2)
        self.assertEqual(SourceContext("test", fetcher, 1000).max_pages, 100)
        self.assertEqual(
            {url for url, _ in fetcher.calls}, {spec.url, "https://example.com/page/2"}
        )

    def test_explicit_browser_fallback(self):
        spec = SourceSpec(
            "dynamic", "https://example.com/", "main", browser_when_empty=True
        )
        fetcher = FakeFetcher(
            {
                spec.url: "<main></main>",
                (
                    spec.url,
                    True,
                ): '<main><a href="https://t.me/ExampleBot">bot</a></main>',
            }
        )
        result = SourceContext("dynamic", fetcher).collect(spec)
        self.assertEqual(result.status, "success")
        self.assertTrue(fetcher.calls[-1][1]["browser"])

    def test_403_is_not_browser_bypassed(self):
        spec = SourceSpec(
            "test", "https://example.com/", "main", browser_when_empty=True
        )
        fetcher = FakeFetcher({spec.url: FetchError("forbidden", "HTTP 403")})
        result = SourceContext("test", fetcher).collect(spec)
        self.assertEqual(result.status, "forbidden")
        self.assertEqual(len(fetcher.calls), 1)

    def test_source_failure_does_not_stop_others(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("first", "second"):
                (root / (name + ".py")).write_text(
                    f'from crawler.models import SourceSpec\nSOURCE=SourceSpec("{name}","https://{name}.example/","main")\ndef collect(ctx):return ctx.collect(SOURCE)\n'
                )
            fetcher = FakeFetcher(
                {
                    "https://first.example/": FetchError("not_found", "HTTP 404"),
                    "https://second.example/": '<main><a href="https://t.me/ExampleBot">bot</a></main>',
                }
            )
            results = discover(None, fetcher, directory=root)
            self.assertEqual([r.status for r in results], ["not_found", "success"])

    def test_dry_run_does_not_connect_database(self):
        from crawler import cli
        from crawler.models import SourceResult

        with (
            patch.object(cli, "connect") as connect,
            patch.object(
                cli,
                "discover",
                return_value=[SourceResult("test", "https://example.com/")],
            ),
        ):
            self.assertEqual(cli.main(["discover", "--dry-run"]), 0)
        connect.assert_not_called()
