"""Telegram 中文知识库推荐：本文件独立维护入口及页面解析规则。"""

from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name="Telegram 中文知识库推荐",
    url="https://tg.ygjc.cc/topics/resource/channels.html",
    selector="#markdown-content",
    mentions=True,
)


def collect(context):
    return context.collect(SOURCE)
