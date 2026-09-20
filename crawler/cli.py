from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import psycopg

from .exporter import export_readme
from .http import Fetcher
from .pipeline import collect, discover
from .source_engine import load_sources
from .storage import ROOT, Store, connect, initialize, writer_lock


def nonnegative(value):
    value = int(value)
    if value < 0:
        raise argparse.ArgumentTypeError("必须大于或等于 0")
    return value


def positive(value):
    value = nonnegative(value)
    if value == 0:
        raise argparse.ArgumentTypeError("必须大于 0")
    return value


def parser():
    p = argparse.ArgumentParser(description="Telegram 来源发现与 PostgreSQL 采集")
    commands = p.add_subparsers(dest="command", required=True)
    commands.add_parser("sources", help="列出来源模块及加载错误")
    for name in ("discover", "collect", "run"):
        sub = commands.add_parser(name)
        sub.add_argument("--source", help="来源文件名，不含 .py")
        sub.add_argument("--log", type=Path, help="同时输出到指定日志文件")
        if name in ("discover", "run"):
            sub.add_argument("--max-pages", type=positive, default=100)
            sub.add_argument(
                "--dry-run",
                action="store_true",
                help="只验证来源，不写数据库，不采集 Telegram 资料",
            )
        if name in ("collect", "run"):
            sub.add_argument("--limit", type=nonnegative, default=0)
            sub.add_argument("--new", action="store_true")
            sub.add_argument("--older-than-days", type=nonnegative, default=30)
    commands.add_parser("refilter")
    export = commands.add_parser("export")
    export.add_argument("--output", type=Path, default=ROOT / "README.md")
    export.add_argument("--allow-empty", action="store_true")
    migrate = commands.add_parser("migrate-lists")
    migrate.add_argument("--sqlite", type=Path, default=ROOT / "db/sqlite/rectg.db")
    commands.add_parser("db-init", help="初始化新数据库和字典")
    commands.add_parser("db-upgrade", help="显式升级已存在的旧表结构")
    return p


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    retired = {
        "--sources": "来源改由 crawler/sources/ 独立模块自动发现，请使用 --source",
        "--db": "运行数据库改为 RECTG_DATABASE_URL；迁移名单使用 migrate-lists --sqlite",
        "--no-resume": "不再提供清空资料重爬；使用 --older-than-days 0 重新检查",
        "--clear": "不再自动清空候选或资料",
        "--no-active": "频道活跃度纳入统一采集，不再跳过预览页",
    }
    p = parser()
    for arg in argv:
        if arg.split("=", 1)[0] in retired:
            p.error(retired[arg.split("=", 1)[0]])
    args = p.parse_args(argv)
    handlers = [logging.StreamHandler(sys.stdout)]
    if getattr(args, "log", None):
        args.log.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(args.log, encoding="utf-8"))
    logging.basicConfig(
        level=logging.INFO, format="%(message)s", handlers=handlers, force=True
    )
    try:
        if args.command == "sources":
            modules, errors = load_sources()
            for name, module in modules.items():
                print(f"{name}\t{module.SOURCE.name}\t{module.SOURCE.url}")
            for name, error in errors.items():
                print(f"{name}\t{error}", file=sys.stderr)
            return 1 if errors else 0
        if getattr(args, "dry_run", False):
            with Fetcher() as fetcher:
                results = discover(None, fetcher, args.source, args.max_pages)
            return int(any(r.status != "success" for r in results))
        with connect() as conn, writer_lock(conn):
            if args.command in ("db-init", "db-upgrade"):
                initialize(conn, upgrade=args.command == "db-upgrade")
                print("PostgreSQL 结构与字典已就绪")
                return 0
            store = Store(conn)
            if args.command in ("run", "discover", "collect"):
                if args.source:
                    modules, errors = load_sources()
                    if args.source not in modules and args.source not in errors:
                        raise ValueError("来源不存在：" + args.source)
                store.recover_runs()
                code = 0
                if args.command in ("run", "discover"):
                    with Fetcher() as fetcher:
                        results = discover(store, fetcher, args.source, args.max_pages)
                    code = int(any(r.status != "success" for r in results))
                if args.command in ("run", "collect"):
                    with Fetcher(delay=3.0) as fetcher:
                        _, failed = collect(
                            store,
                            fetcher,
                            args.source,
                            args.new,
                            args.older_than_days,
                            args.limit,
                        )
                    code = code or int(failed > 0)
                return code
            if args.command == "refilter":
                print("已重新评估资料：", store.refilter())
            elif args.command == "export":
                print(
                    "已导出资料：", export_readme(store, args.output, args.allow_empty)
                )
            elif args.command == "migrate-lists":
                stats = store.migrate_lists(args.sqlite)
                print("名单迁移：", stats, "；未导入历史资料")
                return int(stats["conflicts"] > 0)
        return 0
    except KeyboardInterrupt:
        print(
            "已中断；已提交的数据保留，未完成目标将在恢复等待期后重试", file=sys.stderr
        )
        return 130
    except psycopg.Error as exc:
        # 不输出数据库异常详情，避免连接串、参数或查询中的敏感内容进入日志。
        print(
            f"数据库操作失败：{type(exc).__name__}；请确认结构已初始化/升级",
            file=sys.stderr,
        )
        return 1
    except (ValueError, OSError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
