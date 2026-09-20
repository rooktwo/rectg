"""电报中文教程推荐：本文件独立维护入口及页面解析规则。"""

from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name="电报中文教程推荐",
    url="https://www.dianbaozh.com/knowledgebase/378/",
    selector="article.article-content",
    mentions=True,
)


def collect(context):
    return context.collect(SOURCE)
