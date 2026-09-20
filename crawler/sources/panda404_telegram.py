"""404Panda 推荐：本文件独立维护入口及页面解析规则。"""

from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name="404Panda 推荐",
    url="https://404panda.com/blog/telegram-group-recommendation",
    selector=".entry-content.single-content",
)


def collect(context):
    return context.collect(SOURCE)
