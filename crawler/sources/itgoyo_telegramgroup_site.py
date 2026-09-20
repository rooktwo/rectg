"""itgoyo 中文导航网站：本文件独立维护入口及页面解析规则。"""

from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name="itgoyo 中文导航网站",
    url="https://itgoyo.github.io/telegramgroup/",
    selector="#article-container",
)


def collect(context):
    return context.collect(SOURCE)
