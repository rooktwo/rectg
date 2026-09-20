"""Sac-Y 频道合集：本文件独立维护入口及页面解析规则。"""

from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name="Sac-Y 频道合集",
    url="https://github.com/Sac-Y/awesome-tg-channel",
    selector="article.markdown-body",
)


def collect(context):
    return context.collect(SOURCE)
