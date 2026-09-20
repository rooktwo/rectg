"""印记 Telegram 推荐：本文件独立维护入口及页面解析规则。"""

from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name="印记 Telegram 推荐",
    url="https://yinji.org/telegram-channel-and-bot-recommendations.html/",
    selector="main",
    mentions=True,
)


def collect(context):
    return context.collect(SOURCE)
