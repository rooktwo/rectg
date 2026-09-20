from __future__ import annotations

import logging

import psycopg

from .http import FetchError
from .models import SourceResult
from .source_engine import SourceContext, load_sources
from .storage import IdentityConflict
from .telegram import collect_profile

log = logging.getLogger("crawler")


def discover(store, fetcher, source=None, max_pages=100, directory=None):
    modules, errors = load_sources() if directory is None else load_sources(directory)
    if source:
        if source not in modules and source not in errors:
            raise ValueError(f"来源不存在：{source}")
        modules = {k: v for k, v in modules.items() if k == source}
        errors = {k: v for k, v in errors.items() if k == source}
    results = []
    for source_id, error in errors.items():
        result = SourceResult(source_id, "", status="load_error", errors=[error])
        if store:
            store.save_source(result, store.start_run(source_id, ""))
        results.append(result)
        log.error("%s: %s", source_id, error)
    for source_id, module in modules.items():
        log.info("来源 %s: %s", source_id, module.SOURCE.url)
        run_id = store.start_run(source_id, module.SOURCE.url) if store else None
        context = SourceContext(source_id, fetcher, max_pages)
        try:
            result = module.collect(context)
            if not isinstance(result, SourceResult):
                raise TypeError("collect 必须返回 SourceResult")
        except Exception as exc:
            result = context.result or SourceResult(source_id, module.SOURCE.url)
            result.status = "parser_error"
            result.errors.append(f"解析器异常：{type(exc).__name__}")
        if store:
            store.save_source(result, run_id)
        results.append(result)
        log.info(
            "%s: %s，%d 页，%d 个候选",
            source_id,
            result.status,
            result.pages,
            len({x.username.lower() for x in result.candidates}),
        )
        for error in result.errors:
            log.warning("%s: %s", source_id, error)
    if not results:
        raise ValueError("没有可运行的来源文件")
    return results


def collect(store, fetcher, source=None, new=False, older_days=30, limit=0):
    targets = store.due(source, new, older_days, limit)
    success = failed = 0
    for target in targets:
        store.claim(target)
        try:
            profile = collect_profile(fetcher, target["url"])
            profile["username"] = target["username"]
            store.save_profile(target, profile)
            success += 1
            log.info("%s: %s", target["url"], profile["status"])
        except (FetchError, IdentityConflict, psycopg.IntegrityError) as exc:
            message = (
                f"{exc.kind}: {exc}"
                if isinstance(exc, FetchError)
                else "identity_conflict: 资料唯一性或身份冲突，需要人工核对"
            )
            store.fail(target, message)
            failed += 1
            log.warning("%s: %s", target["url"], message)
        except Exception as exc:
            # 避免一个页面的格式变化阻断剩余目标，错误不覆盖已有资料。
            store.fail(target, "采集异常：" + type(exc).__name__)
            failed += 1
            log.warning("%s: 采集异常 %s", target["url"], type(exc).__name__)
    log.info("资料采集完成：成功 %d，失败 %d", success, failed)
    return success, failed
