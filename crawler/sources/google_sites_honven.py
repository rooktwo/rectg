"""Honven Telegram 推荐：本文件独立维护入口及页面解析规则。"""

from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name="Honven Telegram 推荐",
    url="https://sites.google.com/view/honven/%E9%A6%96%E9%A1%B5/telegram%E7%BE%A4%E7%BB%84%E6%8E%A8%E8%8D%90%E9%A2%91%E9%81%93%E6%8E%A8%E8%8D%90%E5%BC%80%E8%BD%A6%E6%8A%80%E6%9C%AF%E7%A7%91%E5%AD%A6%E4%B8%8A%E7%BD%91%E5%90%88%E7%A7%9F%E7%BE%8A%E6%AF%9B",
    selector=".tyJCtd",
    mentions=True,
)


def collect(context):
    return context.collect(SOURCE)
