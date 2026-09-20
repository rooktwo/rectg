"""TGNAV 导航：本文件独立维护入口及页面解析规则。"""

from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name="TGNAV 导航",
    url="https://www.tgnav.org/",
    selector="main",
    username_routes=("/detail/([A-Za-z0-9_]+)/?",),
    follow=("/(?:channel|group|robot)(?:/[^?]*)?(?:\\?page=\\d+)?",),
)


def collect(context):
    return context.collect(SOURCE)
