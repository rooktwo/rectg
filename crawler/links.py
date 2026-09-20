from __future__ import annotations

import re
from urllib.parse import parse_qs, unquote, urlsplit, urlunsplit

HOSTS = {"t.me", "www.t.me", "telegram.me", "www.telegram.me"}
RESERVED = {
    "s",
    "c",
    "joinchat",
    "addstickers",
    "addemoji",
    "addtheme",
    "addlist",
    "setlanguage",
    "share",
    "proxy",
    "socks",
    "iv",
    "login",
    "confirmphone",
    "invoice",
    "giftcode",
    "boost",
    "contact",
    "m",
    "nft",
    "a",
    "k",
}
USERNAME = re.compile(r"[A-Za-z][A-Za-z0-9_]{3,31}\Z")
MENTIONS = re.compile(r"(?<![\w@])@([A-Za-z][A-Za-z0-9_]{3,31})(?!\w)")
URLS = re.compile(
    r'https?://(?:www\.)?(?:t\.me|telegram\.me)/[^\s<>"\'\]\[()，。；]+', re.I
)


def normalize(value: str) -> tuple[str, str] | None:
    try:
        p = urlsplit(value.strip())
        if p.scheme == "tg" and p.netloc == "resolve":
            username = parse_qs(p.query).get("domain", [""])[0]
        elif p.scheme in ("http", "https") and (p.hostname or "").lower() in HOSTS:
            parts = unquote(p.path).strip("/").split("/")
            if parts[0].lower() == "s" and len(parts) > 1:
                parts = parts[1:]
            username = parts[0]
        else:
            return None
        if not USERNAME.fullmatch(username) or username.lower() in RESERVED:
            return None
        return "https://t.me/" + username.lower(), username
    except ValueError:
        return None


def page_key(url: str) -> str:
    p = urlsplit(url)
    if p.scheme not in ("http", "https") or not p.hostname or p.username or p.password:
        raise ValueError("来源必须是无用户名和密码的 HTTP(S) 地址")
    return urlunsplit(
        (p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/") or "/", p.query, "")
    )
