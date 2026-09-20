"""Shared filtering rules for rectg crawler and maintenance scripts."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Mapping, Any

import opencc


MIN_CHANNEL_SUBSCRIBERS = 500
MIN_GROUP_MEMBERS = 200
INACTIVE_DAYS_THRESHOLD = 90
TRADITIONAL_RATIO_THRESHOLD = 0.10

CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]")
T2S_CONVERTER = opencc.OpenCC("t2s")

# Keep this list to clearly illegal/high-risk terms and public-site unsafe
# content. The context filters below remove common "禁止/请勿 ..." rule text
# before these terms are checked.
HARMFUL_KEYWORDS = [
    "博彩", "赌场", "资金盘", "跑分", "枪支", "迷药", "催情", "迷幻",
    "洗钱", "提现", "查档", "开房记录", "社工库", "呼死你", "轰炸机",
    "菠菜", "嫩模", "外围", "约炮", "迷奸", "代开发票", "黑产", "网赚",
    "色流", "彩票", "赌博", "百家乐", "六合彩", "棋牌", "网赌",
    "破解盗刷", "莞式", "全套", "品茶", "修车", "同城群", "约妹",
    "福利吃瓜", "吃瓜搜索", "福利视频", "里番", "h动漫", "成人资源",
    "制服诱惑", "丝袜", "白丝", "黑丝", "私房", "性感", "绅士",
    "破解软件", "破解版", "付费软件破解", "破解vip", "ios破解",
    "安卓破解", "破解群", "破解版源码", "旧版软件抓包下载", "破解",
    "老司机",
    "黑卡", "免流", "ddos", "压力测试", "暗网", "开盒", "钓鱼",
    "免费节点", "免费高速节点", "免费翻墙", "机场测压", "机场订阅",
    "机场推荐", "全中转节点", "流量均价",
    "空投", "撸毛", "推送新币", "vip群",
]

INJECTION_RE = re.compile(
    r"(<\s*script\b|<\s*img\b|onerror\s*=|javascript\s*:)",
    re.IGNORECASE,
)

PROHIBITED_CONTEXT_RE = re.compile(
    r"(禁止|严禁|不准|不允许|拒绝|谢绝|请勿|不得|不发|不开|请不要|不要|莫开|限正版)"
    r"[^。！？；\n]{0,120}?"
    r"(黑产|灰产|暗网|广告|博彩|赌博|色情|低俗|黄赌毒|政治|违法犯罪|"
    r"盗版|破解|黑卡|免流|钓鱼|开盒|社工|nsfw|18\+|r18|开车)"
    r"[^。！？；\n]{0,160}",
    re.IGNORECASE,
)

VIOLATION_CONTEXT_RE = re.compile(
    r"(群规|如有违反|违者|封禁|立ban|踢出)"
    r"[^。！？；\n]{0,160}?"
    r"(黑产|灰产|暗网|广告|博彩|赌博|色情|低俗|黄赌毒|政治|违法犯罪|"
    r"盗版|破解|黑卡|免流|钓鱼|开盒|社工|nsfw|18\+|r18|开车)"
    r"[^。！？；\n]{0,160}",
    re.IGNORECASE,
)


def contains_chinese(text: str) -> bool:
    return bool(CJK_RE.search(text)) if text else False


def is_traditional_chinese(text: str) -> bool:
    if not text:
        return False

    cjk_chars = CJK_RE.findall(text)
    if len(cjk_chars) < 5:
        return False

    simplified = T2S_CONVERTER.convert(text)
    diff_count = sum(1 for before, after in zip(text, simplified) if before != after)
    return diff_count / max(len(text), 1) >= TRADITIONAL_RATIO_THRESHOLD


def is_harmful(text: str) -> bool:
    if not text:
        return False

    if INJECTION_RE.search(text):
        return True

    text_to_check = PROHIBITED_CONTEXT_RE.sub("", text.lower())
    text_to_check = VIOLATION_CONTEXT_RE.sub("", text_to_check)
    return any(keyword in text_to_check for keyword in HARMFUL_KEYWORDS)


def inactive_days(last_active: str | None) -> int:
    if not last_active:
        return 0

    try:
        last_dt = last_active if isinstance(last_active, datetime) else datetime.fromisoformat(last_active.replace("Z", "+00:00"))
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - last_dt).days
    except (ValueError, TypeError):
        return 0


def evaluate_entry(entry: Mapping[str, Any], *, blacklisted=False, whitelisted=False) -> tuple[int, str]:
    """Return (keep, reason) for a crawled Telegram entry."""
    if not entry.get("valid"):
        return 0, "链接无效"
    if entry.get("private"):
        return 0, "私密频道/群组"

    entry_type = entry.get("type")
    if entry_type not in ('channel', 'group', 'bot'):
        return 0, "无法识别类型"

    if blacklisted or entry.get("is_blacklisted"):
        return 0, "黑名单"
    if whitelisted:
        return 1, "白名单"

    text = f"{entry.get('title') or ''} {entry.get('description') or ''}"
    if not contains_chinese(text):
        return 0, "非中文内容"
    if is_traditional_chinese(text):
        return 0, "繁体中文内容"
    if is_harmful(text):
        return 0, "有害内容"

    count = entry.get("count") or 0
    if entry_type == "channel":
        if count < MIN_CHANNEL_SUBSCRIBERS:
            return 0, f"订阅数不足 ({count} < {MIN_CHANNEL_SUBSCRIBERS})"

        days = inactive_days(entry.get("last_active"))
        if days > INACTIVE_DAYS_THRESHOLD:
            return 0, f"频道不活跃 ({days}天未更新)"
    elif entry_type == "group":
        if count < MIN_GROUP_MEMBERS:
            return 0, f"成员数不足 ({count} < {MIN_GROUP_MEMBERS})"
    # 机器人不限制人数，未公开月活也可收录。

    return 1, ""
