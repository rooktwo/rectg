"""CodeLove 机器人推荐：本文件独立维护入口及页面解析规则。"""

from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name="CodeLove 机器人推荐",
    url="https://codelove.tw/@tony/post/37oZV3",
    selector=".post-core",
    mentions=True,
)


def collect(context):
    return context.collect(SOURCE)
