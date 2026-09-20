"""Mobile01 6069913：本文件独立维护入口及页面解析规则。"""

from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name="Mobile01 6069913",
    url="https://www.mobile01.com/topicdetail.php?f=18&t=6069913",
    selector=".uarticle, .c-article",
    follow=("/topicdetail\\.php\\?f=18&t=6069913&p=\\d+",),
)


def collect(context):
    return context.collect(SOURCE)
