"""OneTelegram 导航：本文件独立维护入口及页面解析规则。"""

from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name="OneTelegram 导航",
    url="https://nav.onetelegram.com/",
    selector="main, .nav-div, .nav-main, .content",
    attributes=("onclick",),
    browser_when_empty=True,
    browser_wait_for='.nav-div [onclick], .nav-main [onclick], main a[href*="t.me/"]',
)


def collect(context):
    return context.collect(SOURCE)
