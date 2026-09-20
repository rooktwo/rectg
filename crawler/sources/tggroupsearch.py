"""TG Group Search：本文件独立维护入口及页面解析规则。"""

from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name="TG Group Search",
    url="https://www.tggroupsearch.com/",
    selector="main",
    follow=("/telegram[^?]*",),
    browser_when_empty=True,
)


def collect(context):
    return context.collect(SOURCE)
