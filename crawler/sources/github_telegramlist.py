"""Telegram 中文群索引：本文件独立维护入口及页面解析规则。"""

from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name="Telegram 中文群索引",
    url="https://github.com/telegramlist/telegramlist",
    selector="article.markdown-body",
)


def collect(context):
    return context.collect(SOURCE)
