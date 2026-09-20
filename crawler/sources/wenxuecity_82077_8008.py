"""文学城 Telegram 推荐：本文件独立维护入口及页面解析规则。"""

from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name="文学城 Telegram 推荐",
    url="https://www.wenxuecity.com/blog/202409/82077/8008.html",
    selector="#articleContent",
    mentions=True,
)


def collect(context):
    return context.collect(SOURCE)
