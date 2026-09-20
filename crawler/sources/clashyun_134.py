"""ClashYun 推荐：本文件独立维护入口及页面解析规则。"""

from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name="ClashYun 推荐",
    url="https://clashyun.com/134.html",
    selector=".entry-content",
)


def collect(context):
    return context.collect(SOURCE)
