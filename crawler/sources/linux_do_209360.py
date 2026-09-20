"""Linux DO 209360：本文件独立维护入口及页面解析规则。"""

from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name="Linux DO 209360",
    url="https://linux.do/t/topic/209360",
    selector=".cooked",
    browser_when_empty=True,
    browser_wait_for='.cooked a[href*="t.me/"], .cooked a[href*="telegram.me/"]',
)


def collect(context):
    return context.collect(SOURCE)
