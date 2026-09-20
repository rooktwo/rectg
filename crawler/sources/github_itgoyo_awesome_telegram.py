"""itgoyo awesome-telegram：本文件独立维护入口及页面解析规则。"""

from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name="itgoyo awesome-telegram",
    url="https://github.com/itgoyo/awesome-telegram",
    selector="article.markdown-body",
)


def collect(context):
    return context.collect(SOURCE)
