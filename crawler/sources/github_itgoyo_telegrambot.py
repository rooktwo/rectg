"""itgoyo 机器人合集：本文件独立维护入口及页面解析规则。"""

from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name="itgoyo 机器人合集",
    url="https://github.com/itgoyo/TelegramBot",
    selector="article.markdown-body",
)


def collect(context):
    return context.collect(SOURCE)
