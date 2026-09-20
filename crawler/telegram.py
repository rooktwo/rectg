from __future__ import annotations

import base64
import json
import re
from datetime import datetime

from bs4 import BeautifulSoup

from .http import FetchError
from .links import normalize


def parse_profile(html, url):
    normalized = normalize(url)
    if not normalized:
        raise ValueError("不是公开 Telegram 用户名链接")
    canonical, username = normalized
    soup = BeautifulSoup(html, "lxml")

    def meta(name):
        node = soup.find("meta", property=name)
        return node.get("content", "").strip() if node else None

    title_node = soup.select_one(".tgme_page_title")
    title = title_node.get_text(" ", strip=True) if title_node else meta("og:title")
    result = dict(
        url=canonical,
        username=username,
        telegram_id=None,
        title=title,
        description=meta("og:description"),
        avatar=meta("og:image"),
        count=None,
        type=None,
        valid=False,
        private=False,
        last_active=None,
        status="unknown",
    )
    for node in soup.select(".tgme_page_extra"):
        text = node.get_text(" ", strip=True)
        for label, kind in [
            ("subscribers?", "channel"),
            ("members?", "group"),
            ("monthly users?", None),
        ]:
            match = re.search(r"([\d\s,\xa0]+)\s*" + label, text, re.I)
            if match:
                result["type"] = kind
                result["count"] = int(re.sub(r"\D", "", match.group(1)))
                break
            if kind and re.fullmatch(label, text, re.I):
                result["type"] = kind
                break
        if result["type"]:
            break
    for action in soup.select(".tgme_page_action a.tgme_action_button_new"):
        if action.get_text(" ", strip=True).lower() == "start bot":
            result["type"] = "bot"
    if result["type"] and title and not re.match(r"^Telegram:\s*Contact", title, re.I):
        result.update(valid=True, status="available")
        return result
    text = soup.get_text(" ", strip=True).lower()
    if any(
        message in text
        for message in (
            "this channel is private",
            "this group is private",
            "this channel can't be displayed",
        )
    ):
        result.update(private=True, status="private")
    return result


def parse_preview(html):
    soup = BeautifulSoup(html, "lxml")
    info = {"telegram_id": None, "last_active": None}
    node = soup.find(attrs={"data-view": True})
    if node:
        try:
            raw = node["data-view"]
            view = json.loads(base64.b64decode(raw + "=" * (-len(raw) % 4)))
            channel_id = int(view["c"])
            info["telegram_id"] = -int("100" + str(abs(channel_id)))
        except (ValueError, KeyError, TypeError, UnicodeError):
            pass
    dates = []
    for node in soup.select("time[datetime]"):
        try:
            from datetime import timezone

            date = datetime.fromisoformat(node["datetime"].replace("Z", "+00:00"))
            dates.append(
                date.replace(tzinfo=timezone.utc) if date.tzinfo is None else date
            )
        except ValueError:
            continue
    if dates:
        info["last_active"] = max(dates)
    return info


def collect_profile(fetcher, url):
    page = fetcher.get(url)
    result = parse_profile(page.html, url)
    # 主页重定向至其他用户名时不默默覆盖身份。
    destination = normalize(page.url)
    if not destination or destination[0] != normalize(url)[0]:
        raise FetchError(
            "identity_conflict", "Telegram 主页重定向到其他地址，需要人工核对"
        )
    if result["status"] == "unknown":
        raise FetchError("unconfirmed", "页面缺少频道、群组或机器人的明确证据")
    if result["type"] == "channel" and result["valid"]:
        preview = fetcher.get("https://t.me/s/" + result["username"])
        destination = normalize(preview.url)
        if not destination or destination[0] != result["url"]:
            raise FetchError(
                "identity_conflict", "Telegram 预览页重定向到其他地址，需要人工核对"
            )
        result.update(parse_preview(preview.html))
    return result
