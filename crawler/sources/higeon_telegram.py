"""Higeon Telegram 推荐：本文件独立维护入口及页面解析规则。"""

from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name="Higeon Telegram 推荐",
    url="https://higeon.wordpress.com/2017/11/10/telegram-%E4%B8%80%E4%BB%BD%E6%9B%B4%E5%AE%8C%E6%95%B4%E7%9A%84%E7%BE%A4%E7%BB%84%E6%8E%A8%E8%8D%90%EF%BC%8C%E5%8C%85%E5%90%AB%E7%A4%BE%E7%BE%A4-%E9%A2%91%E9%81%93-%E6%9C%BA%E5%99%A8%E4%BA%BA-l/",
    selector=".entry-content",
    mentions=True,
)


def collect(context):
    return context.collect(SOURCE)
