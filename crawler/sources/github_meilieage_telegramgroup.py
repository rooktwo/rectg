"""Meilieage 中文群合集：本文件独立维护入口及页面解析规则。"""

from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name="Meilieage 中文群合集",
    url="https://github.com/Meilieage/telegramgroup",
    selector="article.markdown-body",
)


def collect(context):
    return context.collect(SOURCE)
