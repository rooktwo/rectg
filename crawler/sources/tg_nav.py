"""tg-nav 导航：本文件独立维护入口及页面解析规则。"""

from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name="tg-nav 导航",
    url="https://tg-nav.github.io/",
    selector=".main-content",
    username_routes=("/detail/([A-Za-z0-9_]+)/?",),
    follow=("/group/?", "/channel/?"),
)


def collect(context):
    return context.collect(SOURCE)
