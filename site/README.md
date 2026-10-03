# rectg 网站

基于 Astro 的静态目录。数据从仓库根目录的 `README.md` 生成，不需要后端服务。

资料源为 PostgreSQL 的 `tg_profiles` 表。按 `crawler/README.md` 配置 `RECTG_DATABASE_URL` 并完成采集后，在仓库根目录执行：

```sh
python3 -m pip install -r crawler/requirements.txt
python3 -m crawler export
cd site
npm run build
npm run check
```

生成器只导出已收录、未拉黑且状态为 `available` 的频道、群组和机器人，按现有关键词规则生成主题分类和短简介。空结果默认不覆盖 README，导出成功后才原子替换文件。构建同步更新 `public/data.json`、`sitemap.xml` 和 `llms.txt`；构建本身不连接数据库，采集不自动发布网站。

## 精选资源增量更新

网站目录也接受经公开内容抽查后的人工增量收录。筛选记录保存在根目录 `reviews/`：`included` 已加入 README，`pending` 仅待复核，`excluded` 为本批明确不加入的资源。2026-10-02 三轮合计收录 26 个频道，保留 16 个待复核项，并排除 `lanmaoshare` 和 `fanyi_bot`。第三轮从全库 6,074 个用户名的公开页筛查中加入 5 个经用户确认的候选；全库筛查中的另外 12 个暂缓项未加入网站。这些记录不是处理器的模型审核结果，也不修改数据库业务名单。

人工维护后直接运行 `npm run build` 和 `npm run check`，由 README 统一生成网站数据、分类页、详情页和站点地图。数据库的 `is_listed` 是基础规则结果，不代表正文审核通过；全量 `crawler export` 不读取人工筛选记录，会覆盖精选目录。需要重新导出时先使用 `--output` 输出到单独文件，对照 `reviews/` 和当前 README 审查差异，再合并，避免重新加入已排除或待复核的资源。人数沿用采集时记录或公开页近似显示值，具体来源见筛选记录，不表示实时人数。

```sh
cd site
npm ci
npm run dev
```

开发地址以终端输出为准，默认是 `http://localhost:4321`。

## 构建与检查

```sh
npm run build
npm run check
npm run preview
```

`check` 检查资源唯一性、站点地图、结构化数据和样式约定，需要先完成构建。

## Cloudflare 部署

使用 Cloudflare Workers Static Assets，配置文件为 `site/wrangler.jsonc`，静态目录为 `dist`，不存在的路径返回自定义 404 页面。无需 Astro 服务端适配器或数据库连接。

在 Workers Builds 中连接 `rooktwo/rectg` 的 `main` 分支，根目录设置为 `site`，构建命令为 `npm run build && npm run check`，部署命令为 `npx wrangler deploy`。正式网址保持 `https://www.rectg.com`，裸域名跳转到同一路径的 www 域名。

访问量与页面性能使用 Cloudflare Web Analytics，在账号中选择手动安装 JS Snippet，脚本由公共布局统一加载。页面中的 token 是公开的站点统计标识，不是 API 密钥。原 Vercel Analytics、Speed Insights 和自定义事件上报已移除；Cloudflare Web Analytics 不提供搜索、复制或 Telegram 点击的自定义事件统计，历史 Vercel 数据不会迁入。

## 界面与交互

- 首页和分类页共用 `Directory.astro`；卡片的静态渲染和动态更新共用 `Card.astro` 模板。
- 搜索支持名称、简介、主题、拼音和 Telegram 地址。在分类页搜索当前分类，可切换到全站搜索。
- 分类、搜索词、资源类型和排序写入网址，支持刷新、分享以及浏览器前进和后退。
- 卡片 / 列表视图、主题和收藏保存在 `localStorage`；收藏只在当前浏览器有效。
- 每次展示 24 条结果，按需加载更多。进入详情后返回，恢复筛选条件、已加载数量和浏览位置。
- 按 `/` 或 `⌘/Ctrl + K` 聚焦搜索，按 Esc 清空搜索或关闭手机菜单。
- 样式集中在 `src/styles/style.css`，主题颜色使用同一组 CSS 变量。

本地回归重点：桌面与 320px / 390px 手机布局、主题切换、搜索无结果恢复、收藏 / 取消收藏、复制、加载更多、详情返回和键盘操作。
