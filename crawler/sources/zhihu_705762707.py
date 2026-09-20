"""知乎 Telegram 推荐：本文件独立维护入口及页面解析规则。"""

from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name="知乎 Telegram 推荐",
    url="https://zhuanlan.zhihu.com/p/705762707",
    selector=".Post-RichTextContainer, .RichText.ztext",
    browser_when_empty=True,
    browser_wait_for='.RichText a[href*="t.me"], .RichText a[href*="telegram.me"]',
)


def collect(context):
    return context.collect(SOURCE)
