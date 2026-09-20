"""TopsTip 推荐：本文件独立维护入口及页面解析规则。"""

from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name="TopsTip 推荐",
    url="https://topstip.com/telegram-channel-bot-group/",
    selector="article.article-content",
)


def collect(context):
    return context.collect(SOURCE)
