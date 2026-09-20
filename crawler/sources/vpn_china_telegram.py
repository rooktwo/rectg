"""VPN China 推荐：本文件独立维护入口及页面解析规则。"""

from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name="VPN China 推荐",
    url="https://www.vpn-china.org/recommended-for-the-latest-telegram-group/",
    selector=".entry-content",
)


def collect(context):
    return context.collect(SOURCE)
