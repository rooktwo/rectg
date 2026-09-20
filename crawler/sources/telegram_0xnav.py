"""0xnav Telegram 导航：本文件独立维护入口及页面解析规则。"""

from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name="0xnav Telegram 导航",
    url="https://telegram.0xnav.com/",
    selector=".sites-item, .site-content",
    follow=("/sites/\\d+\\.html", "/favorites/[^?]+", "/page/\\d+/?"),
)


def collect(context):
    return context.collect(SOURCE)
