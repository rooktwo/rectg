"""老大博客 Telegram 推荐：本文件独立维护入口及页面解析规则。"""

from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name="老大博客 Telegram 推荐",
    url="https://blog.laoda.de/archives/telegram#--%E6%9C%BA%E5%99%A8%E4%BA%BA%E6%8E%A8%E8%8D%90",
    selector="article.joe_detail__article",
    mentions=True,
)


def collect(context):
    return context.collect(SOURCE)
