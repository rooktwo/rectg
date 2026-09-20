"""V2EX 993116：本文件独立维护入口及页面解析规则。"""

from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name="V2EX 993116",
    url="https://v2ex.com/t/993116",
    selector=".topic_content, .reply_content",
    follow=("/t/993116\\?p=\\d+",),
)


def collect(context):
    return context.collect(SOURCE)
