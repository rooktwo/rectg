"""V2EX 206766：本文件独立维护入口及页面解析规则。"""

from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name="V2EX 206766",
    url="https://global.v2ex.co/t/206766",
    selector=".topic_content, .reply_content",
    follow=("/t/206766\\?p=\\d+",),
)


def collect(context):
    return context.collect(SOURCE)
