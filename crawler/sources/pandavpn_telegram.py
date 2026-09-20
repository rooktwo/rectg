"""PandaVPN 推荐：本文件独立维护入口及页面解析规则。"""

from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name="PandaVPN 推荐",
    url="https://pandavpnpro.com/blog/zh-cn/telegram-group-channel-bot",
    selector="#article-text",
)


def collect(context):
    return context.collect(SOURCE)
