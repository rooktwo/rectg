"""itgoyo TelegramGroup：本文件独立维护入口及页面解析规则。"""

from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name="itgoyo TelegramGroup",
    url="https://github.com/itgoyo/TelegramGroup",
    selector="article.markdown-body",
)


def collect(context):
    return context.collect(SOURCE)
