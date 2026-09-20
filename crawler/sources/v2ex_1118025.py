"""V2EX 1118025：本文件独立维护入口及页面解析规则。"""

from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name="V2EX 1118025",
    url="https://hk.v2ex.com/t/1118025",
    selector=".topic_content, .reply_content",
    follow=("/t/1118025\\?p=\\d+",),
)


def collect(context):
    return context.collect(SOURCE)
