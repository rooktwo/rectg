from __future__ import annotations

import base64
import json
import unittest
from datetime import datetime, timedelta, timezone

from crawler.filter_rules import evaluate_entry
from crawler.telegram import parse_profile, parse_preview, collect_profile
from crawler.http import Page, FetchError
from unittest.mock import Mock


def profile(kind="channel", count=500):
    return dict(
        type=kind,
        count=count,
        title="中文技术工具",
        description="分享编程技术",
        valid=True,
        private=False,
        last_active=None,
    )


class TelegramTests(unittest.TestCase):
    def test_thresholds(self):
        for kind, count, expected in [
            ("channel", 499, 0),
            ("channel", 500, 1),
            ("group", 199, 0),
            ("group", 200, 1),
            ("bot", None, 1),
            ("bot", 0, 1),
            ("channel", None, 0),
            ("group", None, 0),
        ]:
            with self.subTest(kind=kind, count=count):
                self.assertEqual(evaluate_entry(profile(kind, count))[0], expected)

    def test_lists_priority_and_quality_exemption(self):
        entry = {
            **profile(count=1),
            "title": "English",
            "description": "博彩",
            "last_active": datetime.now(timezone.utc) - timedelta(days=100),
        }
        self.assertEqual(evaluate_entry(entry, whitelisted=True), (1, "白名单"))
        self.assertEqual(
            evaluate_entry(entry, blacklisted=True, whitelisted=True), (0, "黑名单")
        )
        for changes in ({"valid": False}, {"private": True}, {"type": None}):
            self.assertEqual(
                evaluate_entry({**entry, **changes}, whitelisted=True)[0], 0
            )
        self.assertEqual(
            evaluate_entry({**profile(), "is_blacklisted": True}, whitelisted=True)[0],
            0,
        )

    def test_activity_timezone_and_unknown(self):
        self.assertEqual(evaluate_entry(profile())[0], 1)
        for value in [
            (datetime.now(timezone.utc) - timedelta(days=91)).isoformat(),
            datetime.now(timezone.utc) - timedelta(days=91),
        ]:
            self.assertEqual(evaluate_entry({**profile(), "last_active": value})[0], 0)

    def test_bot_type_without_monthly_count(self):
        html = '<meta property="og:title" content="中文翻译"><div class="tgme_page_extra">@ExampleBot</div><div class="tgme_page_action"><a class="tgme_action_button_new">Start Bot</a></div>'
        result = parse_profile(html, "https://t.me/ExampleBot")
        self.assertEqual(
            (result["type"], result["count"], result["valid"]), ("bot", None, True)
        )
        self.assertEqual(evaluate_entry(result)[0], 1)
        result = parse_profile(
            html.replace("Start Bot", "Send Message"), "https://t.me/ExampleBot"
        )
        self.assertEqual(result["status"], "unknown")

    def test_multiple_extra_blocks_and_fake_http200(self):
        html = '<meta property="og:title" content="中文工具"><div class="tgme_page_extra">@ExampleBot</div><div class="tgme_page_extra">1 234 monthly users</div>'
        result = parse_profile(html, "https://t.me/ExampleBot")
        self.assertFalse(result["valid"])
        html += '<div class="tgme_page_action"><a class="tgme_action_button_new">Start Bot</a></div>'
        result = parse_profile(html, "https://t.me/ExampleBot")
        self.assertEqual((result["type"], result["count"]), ("bot", 1234))
        self.assertFalse(
            parse_profile(
                '<meta property="og:title" content="Telegram: Contact @ExampleBot">',
                "https://t.me/ExampleBot",
            )["valid"]
        )
        result = parse_profile(
            '<meta property="og:title" content="中文频道"><div class="tgme_page_extra">subscribers</div>',
            "https://t.me/ExampleChan",
        )
        self.assertEqual(
            (result["type"], result["count"], result["valid"]), ("channel", None, True)
        )
        self.assertEqual(evaluate_entry(result)[0], 0)

    def test_private_evidence_and_public_description(self):
        self.assertEqual(
            parse_profile(
                "<div>This channel is private</div>", "https://t.me/ExampleChan"
            )["status"],
            "private",
        )
        html = '<meta property="og:title" content="中文频道"><div class="tgme_page_extra">600 subscribers</div><p>This channel is private</p>'
        self.assertEqual(
            parse_profile(html, "https://t.me/ExampleChan")["status"], "available"
        )

    def test_preview_and_transient_failure(self):
        value = (
            base64.b64encode(json.dumps({"c": 123456}).encode()).decode().rstrip("=")
        )
        result = parse_preview(
            f'<div data-view="{value}"></div><time datetime="2026-09-20T12:00:00Z"></time>'
        )
        self.assertEqual(result["telegram_id"], -100123456)
        self.assertIsNotNone(result["last_active"])
        fetcher = Mock()
        fetcher.get.side_effect = [
            Page(
                "https://t.me/examplechan",
                '<meta property="og:title" content="中文频道"><div class="tgme_page_extra">600 subscribers</div>',
            ),
            FetchError("rate_limited", "HTTP 429"),
        ]
        with self.assertRaises(FetchError):
            collect_profile(fetcher, "https://t.me/examplechan")

    def test_identity_redirect(self):
        fetcher = Mock()
        fetcher.get.return_value = Page(
            "https://t.me/OtherBot",
            '<meta property="og:title" content="工具"><div class="tgme_page_action"><a class="tgme_action_button_new">Start Bot</a></div>',
        )
        with self.assertRaises(FetchError):
            collect_profile(fetcher, "https://t.me/ExampleBot")
