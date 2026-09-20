"""Ccino 群组汇总：本文件独立维护入口及页面解析规则。"""

from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name="Ccino 群组汇总",
    url="https://www.ccino.net/telegram-group-summary.html",
    selector="#lightgallery",
)


def collect(context):
    return context.collect(SOURCE)
