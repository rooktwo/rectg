"""DOS-AI 中文导航：本文件独立维护入口及页面解析规则。"""

from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name="DOS-AI 中文导航",
    url="https://github.com/DOS-AI-Tech/Awesome-Telegram-Chinese-2026",
    selector="article.markdown-body",
)


def collect(context):
    return context.collect(SOURCE)
