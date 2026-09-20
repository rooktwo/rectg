# Telegram 爬虫

流程：`来源脚本 → 候选及来源记录 → Telegram 公开资料 → 收录规则 → PostgreSQL → export → README → Astro`。

从仓库根目录运行 `python -m crawler`。`sources/` 中现有 39 个独立 Python 文件分别对应一个入口 URL，程序自动发现；`sources.txt` 仅保留作历史参考，不参与运行、不自动改写。

## 安装与数据库

建议 Python 3.10 以上，使用独立虚拟环境：

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r crawler/requirements.txt
# 使用自己的 PostgreSQL 地址，也可通过运行环境注入变量。
export RECTG_DATABASE_URL='postgresql://USER:PASSWORD@HOST:5432/rectg'
python -m crawler db-init
```

`db-init` 初始化新库及字典，重复执行保留人工维护的字典内容。已有旧 PostgreSQL 结构必须显式执行 `python -m crawler db-upgrade`；升级脚本位于 `db/postgresql/migrations/`，不会因正常采集而自动运行。初始化和升级不会删除已有资料。日志不输出数据库连接串或密码。

从旧 SQLite 迁移时：

```sh
python -m crawler migrate-lists --sqlite db/sqlite/rectg.db
```

仅以只读方式迁移 `blacklist`、`whitelist`，原 SQLite 文件继续保留作备份，不导入历史资料。重复运行跳过相同记录；用户名、真实 ID、URL 或内容冲突会报告，并保留 PostgreSQL 已有内容。资料通过新队列重新采集。

需要浏览器的来源额外安装：

```sh
pip install -r crawler/requirements-browser.txt
python -m playwright install chromium
```

## 命令

| 命令 | 用途 |
| --- | --- |
| `sources` | 列出来源文件、名称、URL；报告重复入口及加载错误 |
| `discover` | 抓取来源，保存候选与发现页面 |
| `collect` | 采集候选和到期资料 |
| `run` | 依次执行 discover、collect |
| `refilter` | 根据当前黑白名单及规则重新判断已有资料 |
| `export` | 从 PostgreSQL 导出根目录 README |
| `migrate-lists` | 从 SQLite 只迁移黑白名单 |
| `db-init` / `db-upgrade` | 初始化新数据库 / 显式升级旧结构 |

```sh
python -m crawler sources
# 不连接数据库，只检查一个来源；不会采集 Telegram 资料。
python -m crawler discover --source github_jackvale_rectg --dry-run
python -m crawler discover --source github_jackvale_rectg
python -m crawler collect --source github_jackvale_rectg --limit 10
python -m crawler collect --new --limit 100
python -m crawler collect --older-than-days 0 --limit 10
python -m crawler run --source github_jackvale_rectg --limit 10 --log data/crawl.log
python -m crawler refilter
python -m crawler export
# 可导出到隔离路径，先检查结果。
python -m crawler export --output /tmp/rectg-preview/README.md
```

`--source` 使用文件名（不含 `.py`）。默认处理全部来源；`--limit 0` 为不限数量。资料默认刷新间隔 30 天，`--older-than-days` 可调整，`--new` 仅处理尚无成功检查的目标。`--max-pages` 可降低单来源页数限制，任何值均不会超过硬上限 100。`run --dry-run` 只验证来源。

异常来源不会阻塞其余来源；部分失败、解析为空、达到页数上限、身份冲突等会输出原因并返回非零退出码。已完成的数据保留。同一数据库同时只运行一个采集或维护写入任务。

旧入口 `crawl.py`、`parse_links.py`、`scrape_tgnav.py`、`refilter.py`、`generate_readme.py` 转调统一实现。`crawl.py --skip-sources` 对应 `collect`。旧 `--sources`、`--db`、`--clear`、`--no-resume`、`--no-active` 会给出迁移提示，不再清空结果重爬。

## 维护来源

每个文件声明 `SOURCE`，实现 `collect(context)`。相同结构复用公共解析器，特殊结构可在该文件内单独实现解析逻辑。文件名作为持久来源标识，避免无故改名。

```python
from crawler.models import SourceSpec

SOURCE = SourceSpec(
    name='中文推荐目录',
    url='https://example.com/resources/',
    selector='article',
    mentions=True,
    follow=(r'/resources/page/\d+/?',),
)


def collect(context):
    return context.collect(SOURCE)
```

- `selector` 限定正文；`mentions` 控制是否提取纯文本用户名。默认识别正文中的 Telegram 链接及明确的跳转参数。
- `username_routes` 用正则提取站内详情路径中的用户名；`attributes` 可声明含链接的 `onclick` 等属性，解析文本而不执行其中代码。
- `follow` 为可跟进的同域完整路径正则，可包含查询参数；只允许明确的分类、详情、分页，默认不递归。
- `browser_when_empty=True` 显式允许 HTTP 正文为空时使用无头浏览器；`browser_wait_for` 可指定必须出现的动态内容选择器。没有安装浏览器会报错。不会自动登录或处理验证码，HTTP 403 不用浏览器绕过。
- 每来源每轮最多访问 100 页，请求前去重；分页循环会终止。达到上限记为 `page_limit`（未完成），部分候选仍保存。
- 来源失效时手动删除对应文件即可。程序不会自动删除、停用文件。历史资料、候选和来源记录保留；默认资料采集仍可刷新此前发现的目标。

新增或调整来源时，在 `tests/fixtures/sources/` 保存最小解析样本，并更新 `manifest.json`。当前样本中 35 个来自真实 HTML，Mobile01、Linux.do、知乎、TelegramChannels 四个来源曾返回 403，使用明确标记为 `http_403_unverified` 的契约样本，尚未完成线上解析验证。样本验证不代表所有分类和分页均已全量抓取。

## 数据与规则

- `crawl_targets`：忽略大小写去重的用户名、候选 URL、尝试时间、成功时间、下次尝试、失败次数及错误。
- `crawl_target_sources`：一个候选对应的来源文件、入口 URL、发现页面。同一资源可保留多个来源。
- `crawl_source_runs`：每轮来源状态、页数、候选数、错误和完成时间；中断后记录为 `interrupted`。
- `tg_profiles`：公开资料、头像、人数、最近活跃时间、成功检查时间、状态、收录标记及过滤原因。未达门槛但公开有效的资料同样保存。
- `blacklist`、`whitelist`：人工维护名单。资料及名单均允许未知 Telegram ID，保留真实 ID 唯一约束，后续取得 ID 再补齐；身份冲突留待人工处理。

判断顺序是公开有效性、黑名单或人工拉黑标记、白名单、普通规则。白名单豁免人数、语言、内容和活跃度过滤，不能让私有或无法确认类型的资源公开展示。

普通频道至少 500 位订阅者，群组至少 200 位成员；人数未知时暂不收录。机器人通过页面明确的启动标识确认，不凭用户名后缀，也不要求公开月活。继续执行现有中文、繁体、内容关键词和频道 90 天活跃度规则；缺少活跃时间不据此判为不活跃。

网络异常、限流或证据不足只记录失败，不清空成功资料、不判为删除。失败按 5 分钟起的指数退避重试，最长 24 小时，不等待 30 天。目标领取后有 15 分钟恢复等待期，中断的检查到期可重试。确认私有后停止展示，历史资料继续保留。

黑白名单变更后执行 `refilter`，再 `export` 即可让静态目录使用新结果，不需要重新请求 Telegram。

## 网站衔接

```sh
python -m crawler export
cd site
npm ci
npm run build
npm run check
```

导出仅包含已收录、公开有效且未拉黑的资源，按现有规则分类。先写临时文件并校验，最后原子替换 README；空结果默认拒绝覆盖，确需空目录时显式使用 `--allow-empty`。网站构建只读取 README，无需数据库连接。采集不会自动导出或发布网站。

## 验证

```sh
python -m unittest discover -s crawler/tests -v
# 数据库集成测试在指定测试库中创建随机独立 schema，结束后仅删除该 schema。
RECTG_TEST_DATABASE_URL='postgresql://USER:PASSWORD@HOST:5432/rectg_test' \
  python -m unittest discover -s crawler/tests -v
```

未设置测试连接时跳过 PostgreSQL 集成测试。覆盖来源映射、正文/用户名/跳转/分页/浏览器路径、跨来源去重、阈值、名单顺序、身份冲突、失败保留资料、升级和名单迁移重复执行、中断恢复与导出保护。
