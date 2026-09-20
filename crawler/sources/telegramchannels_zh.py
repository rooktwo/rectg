"""Telegram Channels 中文目录：本文件独立维护入口及页面解析规则。"""

from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name="Telegram Channels 中文目录",
    url="https://telegramchannels.me/zh",
    selector="main, .channels-list, .container",
    follow=(
        "/zh/(?:channels|groups|bots|categories)/[^?]+(?:\\?page=\\d+)?",
        "/zh\\?page=\\d+",
    ),
    browser_when_empty=True,
)


def collect(context):
    return context.collect(SOURCE)
