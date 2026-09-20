"""TGGSearch 群组目录：本文件独立维护入口及页面解析规则。"""

from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name="TGGSearch 群组目录",
    url="https://tggsearch.github.io/docs/telegram-group-index.html",
    selector="article.article-content",
)


def collect(context):
    return context.collect(SOURCE)
