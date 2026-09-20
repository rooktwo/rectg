"""rectg GitHub：本文件独立维护入口及页面解析规则。"""

from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name="rectg GitHub",
    url="https://github.com/jackvale/rectg",
    selector="article.markdown-body",
)


def collect(context):
    return context.collect(SOURCE)
