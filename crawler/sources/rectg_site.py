"""rectg 网站：本文件独立维护入口及页面解析规则。"""

from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name="rectg 网站",
    url="https://www.rectg.com/",
    selector="main",
    follow=("/category/[^?]+/?", "/p/[^?]+/?"),
)


def collect(context):
    return context.collect(SOURCE)
