from __future__ import annotations

import html
import re
from typing import Optional
from .categorize import clean_text_advanced, clean_title_advanced, determine_category

README_DESC_LIMIT = 16

# 一级大类
TYPE_ORDER = [
    {"id": "channel", "name": "频道"},
    {"id": "group", "name": "群组"},
    {"id": "bot", "name": "机器人"},
]

# 二级分类排序规则（按照这个顺序输出二级分类）
CATEGORY_ORDER = [
    "📰 新闻快讯",
    "💻 数码科技",
    "👨‍💻 开发运维",
    "🔒 信息安全",
    "🧰 软件工具",
    "☁️ 网盘资源",
    "🎬 影视剧集",
    "🎵 音乐音频",
    "🎐 动漫次元",
    "🎮 游戏娱乐",
    "✈️ 科学上网",
    "🪙 加密货币",
    "📚 学习阅读",
    "🎨 创意设计",
    "📡 社媒搬运",
    "🏀 体育运动",
    "👗 生活消费",
    "🌍 地区社群",
    "💬 闲聊交友",
    "🗂️ 综合导航",
    "🌐 综合其他",
]


def make_anchor(section: str, category_index: Optional[int] = None) -> str:
    """生成稳定锚点，避免依赖 GitHub 对中文/emoji 标题的默认锚点规则。"""
    if category_index is None:
        return f"section-{section}"
    return f"section-{section}-{category_index}"


def format_count(count) -> str:
    """格式化数字为精确数字字符串，带千分位逗号。"""
    if count is None:
        return "-"
    return f"{int(count):,}"


def escape_table_text(text: str) -> str:
    """转义 Markdown 表格中的特殊字符。"""
    if not text:
        return ""
    return (
        html.escape(text, quote=False)
        .replace("|", " / ")
        .replace("\n", " ")
        .replace("[", "\\[")
        .replace("]", "\\]")
        .strip()
    )


def compact_text(text: str) -> str:
    """压缩多余空白，适合表格单元格。"""
    if not text:
        return ""
    return " ".join(text.split())


def canonical_url_key(url: str) -> str:
    """生成 Telegram URL 去重键，忽略用户名大小写和末尾斜杠。"""
    value = (url or "").strip()
    match = re.match(
        r"^(?:https?://)?(?:www\.)?(?:t\.me|telegram\.me)/([^?#]+)",
        value,
        re.IGNORECASE,
    )
    if not match:
        return value.lower().rstrip("/")

    parts = [part for part in match.group(1).split("/") if part]
    if (
        parts
        and parts[0].lower() not in {"joinchat", "c"}
        and not parts[0].startswith("+")
    ):
        parts[0] = parts[0].lower()
    return "t.me/" + "/".join(parts)


def rewrite_description(text: str, limit: int = README_DESC_LIMIT) -> str:
    """将原始简介整理为一句短说明，去掉链接和多余分句。"""
    text = re.sub(r"https?://\S+|www\.\S+", "", text)
    text = text.replace("|", "，")
    if text.strip().lower().rstrip(".") == "you can view and join right away":
        return "Telegram 资源入口。"
    clauses = [
        part.strip(" ，,、:：")
        for part in re.split(r"[。！？；;]+", text)
        if part.strip(" ，,、:：")
    ]
    if not clauses:
        return ""

    pieces = [
        piece.strip(" ，,、:：")
        for piece in re.split(r"[，,、]+", clauses[0])
        if piece.strip(" ，,、:：")
    ]
    sentence_parts = []
    content_limit = max(1, limit - 1)
    for piece in pieces:
        candidate = "，".join(sentence_parts + [piece])
        if sentence_parts and len(candidate) > content_limit:
            break
        sentence_parts.append(piece)
    sentence = "，".join(sentence_parts) or clauses[0]
    if len(sentence) > content_limit:
        sentence = sentence[:content_limit].rstrip(" ，,、")
    return sentence.rstrip(" ，,、") + "。"


def render_desc_cell(text: str) -> str:
    """渲染 README 简介单元格，保持表格原文干净。"""
    full_text = compact_text(text)
    if not full_text:
        return "-"

    return escape_table_text(rewrite_description(full_text)) or "-"


def render_link_cell(url: str) -> str:
    """将 Telegram 地址显示为简洁的 @用户名链接。"""
    value = (url or "").strip()
    match = re.match(
        r"^(?:https?://)?(?:www\.)?(?:t\.me|telegram\.me)/([^/?#]+)",
        value,
        re.IGNORECASE,
    )
    label = (
        f"@{match.group(1)}"
        if match
        and match.group(1) not in {"joinchat", "c"}
        and not match.group(1).startswith("+")
        else value
    )
    return f"[{escape_table_text(label)}]({value})" if value else "-"


def sorted_categories(categories: dict[str, list[dict]]) -> list[str]:
    """按照预设顺序输出分类，其余分类稳定追加到最后。"""
    existing_cats = set(categories.keys())
    result = [c for c in CATEGORY_ORDER if c in existing_cats]
    result += sorted(list(existing_cats - set(CATEGORY_ORDER)))
    return result


def render_readme(rows) -> str:
    """将已验证的资料渲染为网站输入目录。"""
    # 结构: stats[type_id][cat_name] = [item1, item2, ...]
    tree = {"channel": {}, "group": {}, "bot": {}}

    seen_url_keys = set()
    for row in rows:
        t = row["type"]
        if t not in tree:
            continue

        if canonical_url_key(row["url"]) in seen_url_keys:
            continue

        seen_url_keys.add(canonical_url_key(row["url"]))

        title = row["title"] or ""
        description = row["description"] or ""
        cat = determine_category(title, description)
        if cat not in tree[t]:
            tree[t][cat] = []
        tree[t][cat].append(
            {
                **dict(row),
                "clean_title": clean_title_advanced(title) or title,
                "clean_desc": clean_text_advanced(description, title),
            }
        )

    lines = [
        "> 📣 **Telegram 频道群组推荐**：[关注 @tgtuijian](https://t.me/tgtuijian)<br>",
        "> 持续发现值得加入的频道与群组，附推荐理由、内容方向和活跃情况。",
        "",
    ]

    # 生成各版块
    for t_info in TYPE_ORDER:
        t_id = t_info["id"]
        t_name = t_info["name"]

        categories = tree[t_id]
        if not categories:
            continue

        lines.append(f'<a id="{make_anchor(t_id)}"></a>')
        lines.append(f"## {t_name}")
        lines.append("")

        # 按照预定义的 category 顺序遍历，如果不在预定义里则放到最后
        ordered_cats = sorted_categories(categories)

        for idx, cat in enumerate(ordered_cats, start=1):
            items = categories[cat]
            if not items:
                continue

            lines.append(f'<a id="{make_anchor(t_id, idx)}"></a>')
            lines.append("### " + cat)
            lines.append("")
            lines.append("| 名称 | 链接 | 人数 | 简介 |")
            lines.append("| --- | --- | ---: | --- |")

            for item in items:
                title = (
                    escape_table_text(
                        compact_text(item.get("clean_title") or item.get("title") or "")
                    )
                    or "-"
                )
                desc = render_desc_cell(
                    item.get("clean_desc") or item.get("description") or ""
                )
                url = item.get("url", "")
                count = format_count(item.get("count"))
                lines.append(
                    f"| {title} | {render_link_cell(url)} | {count} | {desc} |"
                )

            lines.append("")

    return "\n".join(lines).strip() + "\n"
