from __future__ import annotations

import os
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from psycopg import sql

from .filter_rules import evaluate_entry
from .links import normalize

ROOT = Path(__file__).resolve().parent.parent


class IdentityConflict(Exception):
    pass


def connect():
    dsn = os.environ.get("RECTG_DATABASE_URL")
    if not dsn:
        raise ValueError(
            "请设置 RECTG_DATABASE_URL（PostgreSQL），SQLite 仅用于名单迁移"
        )
    try:
        return psycopg.connect(
            dsn, autocommit=True, row_factory=dict_row, connect_timeout=10
        )
    except psycopg.Error:
        raise ValueError(
            "PostgreSQL 连接失败，请检查 RECTG_DATABASE_URL 和服务器状态"
        ) from None


@contextmanager
def writer_lock(conn):
    # 同一数据库只允许一个修改任务；HTTP 请求期间不持有数据库事务。
    locked = conn.execute(
        "SELECT pg_try_advisory_lock(725043921) AS acquired"
    ).fetchone()["acquired"]
    if not locked:
        raise ValueError("已有爬虫或维护任务正在运行，请稍后重试")
    try:
        yield
    finally:
        conn.execute("SELECT pg_advisory_unlock(725043921)")


def initialize(conn, upgrade=False):
    root = ROOT / "db/postgresql"
    exists = conn.execute("SELECT to_regclass('tg_profiles') AS name").fetchone()[
        "name"
    ]
    if exists and not upgrade:
        column = conn.execute(
            "SELECT 1 FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='tg_profiles' AND column_name='is_listed'"
        ).fetchone()
        if not column:
            raise ValueError(
                "检测到旧结构，请运行 db-upgrade；db-init 不会自动迁移已有表"
            )
    if upgrade:
        conn.execute((root / "migrations/20260921_crawler.sql").read_text())
    with conn.transaction():
        conn.execute((root / "01_schema.sql").read_text())
    conn.execute((root / "02_init_dict_items.sql").read_text())


class Store:
    def __init__(self, conn):
        self.conn = conn

    def start_run(self, source_id, url):
        return self.conn.execute(
            "INSERT INTO crawl_source_runs (source_id, source_url) VALUES (%s,%s) RETURNING id",
            (source_id, url),
        ).fetchone()["id"]

    def save_source(self, result, run_id):
        with self.conn.transaction():
            for item in result.candidates:
                row = self.conn.execute(
                    """INSERT INTO crawl_targets (username,url,name,type_hint)
                    VALUES (%s,%s,%s,%s) ON CONFLICT (lower(username)) DO UPDATE
                    SET name=EXCLUDED.name, type_hint=COALESCE(EXCLUDED.type_hint,crawl_targets.type_hint), updated_at=now()
                    RETURNING id""",
                    (item.username, item.url, item.name, item.type_hint),
                ).fetchone()
                self.conn.execute(
                    """INSERT INTO crawl_target_sources (target_id,source_id,source_url,page_url)
                    VALUES (%s,%s,%s,%s) ON CONFLICT (target_id,source_id,page_url)
                    DO UPDATE SET source_url=EXCLUDED.source_url, updated_at=now()""",
                    (row["id"], result.source_id, result.source_url, item.page_url),
                )
            self.conn.execute(
                """UPDATE crawl_source_runs SET status=%s,page_count=%s,candidate_count=%s,error=%s,
                finished_at=now(),updated_at=now() WHERE id=%s""",
                (
                    result.status,
                    result.pages,
                    len({x.username.lower() for x in result.candidates}),
                    "\n".join(result.errors) or None,
                    run_id,
                ),
            )

    def recover_runs(self):
        # 调用者已持有全局写锁；遗留 running 记录属于上次中断。
        self.conn.execute(
            "UPDATE crawl_source_runs SET status='interrupted',error='上次运行中断',finished_at=now(),updated_at=now() WHERE status='running'"
        )

    def due(self, source=None, new=False, older_days=30, limit=0):
        # 已有 PostgreSQL 资料也进入刷新队列；不依赖来源再次发现它们。
        self.conn.execute("""INSERT INTO crawl_targets (username,url,name,type_hint,last_success_at)
            SELECT username,'https://t.me/' || lower(username),title,type,last_checked_at FROM tg_profiles
            WHERE username ~ '^[A-Za-z][A-Za-z0-9_]{3,31}$'
            ON CONFLICT DO NOTHING""")
        return self.conn.execute(
            """SELECT t.* FROM crawl_targets t
            WHERE t.next_attempt_at <= now()
              AND (%s = FALSE OR t.last_success_at IS NULL)
              AND (t.failure_count > 0 OR t.last_success_at IS NULL OR t.last_attempt_at > t.last_success_at
                   OR t.last_success_at < now() - %s * INTERVAL '1 day')
              AND (%s::TEXT IS NULL OR EXISTS (SELECT 1 FROM crawl_target_sources s WHERE s.target_id=t.id AND s.source_id=%s))
            ORDER BY t.next_attempt_at,t.id LIMIT %s""",
            (new, older_days, source, source, limit or None),
        ).fetchall()

    def claim(self, target):
        self.conn.execute(
            "UPDATE crawl_targets SET last_attempt_at=now(),next_attempt_at=now()+INTERVAL '15 minutes',updated_at=now() WHERE id=%s",
            (target["id"],),
        )

    def fail(self, target, message):
        count = target["failure_count"] + 1
        seconds = min(86400, 300 * 2 ** min(count - 1, 9))
        self.conn.execute(
            "UPDATE crawl_targets SET failure_count=%s,last_error=%s,next_attempt_at=now()+%s*INTERVAL '1 second',updated_at=now() WHERE id=%s",
            (count, message, seconds, target["id"]),
        )

    def listed_match(self, table, profile):
        return bool(
            self.conn.execute(
                sql.SQL(
                    "SELECT 1 FROM {} WHERE lower(username)=lower(%s) OR url=%s OR (telegram_id IS NOT NULL AND telegram_id=%s) LIMIT 1"
                ).format(sql.Identifier(table)),
                (profile["username"], profile["url"], profile.get("telegram_id")),
            ).fetchone()
        )

    def decision(self, profile):
        entry = {
            **profile,
            "valid": profile.get("status") == "available",
            "private": profile.get("status") == "private",
            "count": profile.get("user_count", profile.get("count")),
        }
        return evaluate_entry(
            entry,
            blacklisted=self.listed_match("blacklist", profile),
            whitelisted=self.listed_match("whitelist", profile),
        )

    def save_profile(self, target, profile):
        with self.conn.transaction():
            matches = self.conn.execute(
                """SELECT * FROM tg_profiles WHERE lower(username)=lower(%s) OR url=%s
                OR (telegram_id IS NOT NULL AND telegram_id=%s) FOR UPDATE""",
                (profile["username"], profile["url"], profile.get("telegram_id")),
            ).fetchall()
            if len(matches) > 1:
                raise IdentityConflict("用户名、URL 与 Telegram ID 指向不同资料")
            old = matches[0] if matches else None
            if old and old["username"].lower() != profile["username"].lower():
                raise IdentityConflict("同一 Telegram ID 对应不同用户名，需要人工核对")
            if (
                old
                and old["telegram_id"] is not None
                and profile.get("telegram_id") is not None
                and old["telegram_id"] != profile["telegram_id"]
            ):
                raise IdentityConflict("同一用户名的 Telegram ID 已改变")
            if profile["status"] == "private":
                if old:
                    self.conn.execute(
                        "UPDATE tg_profiles SET status='private',is_listed=FALSE,filter_reason='已确认私有',last_checked_at=now(),updated_at=now() WHERE id=%s",
                        (old["id"],),
                    )
            else:
                data = dict(profile)
                if old:
                    data["is_blacklisted"] = old["is_blacklisted"]
                    for key in ("telegram_id", "last_active"):
                        if data.get(key) is None:
                            data[key] = old[key]
                keep, reason = self.decision(data)
                values = (
                    data.get("telegram_id"),
                    data["username"],
                    data["url"],
                    data["type"],
                    data["title"],
                    data.get("description"),
                    data.get("avatar"),
                    data.get("count"),
                    data.get("last_active"),
                    bool(keep),
                    reason,
                )
                if old:
                    self.conn.execute(
                        """UPDATE tg_profiles SET telegram_id=%s,username=%s,url=%s,type=%s,title=%s,description=%s,
                        avatar=%s,user_count=%s,last_active=%s,is_listed=%s,filter_reason=%s,status='available',last_checked_at=now(),updated_at=now() WHERE id=%s""",
                        values + (old["id"],),
                    )
                else:
                    self.conn.execute(
                        """INSERT INTO tg_profiles (telegram_id,username,url,type,title,description,avatar,user_count,last_active,is_listed,filter_reason,status,last_checked_at)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'available',now())""",
                        values,
                    )
            self.conn.execute(
                """UPDATE crawl_targets SET last_success_at=now(),failure_count=0,last_error=NULL,
                next_attempt_at=now(),updated_at=now() WHERE id=%s""",
                (target["id"],),
            )

    def refilter(self):
        count = 0
        for profile in self.conn.execute(
            "SELECT * FROM tg_profiles ORDER BY id"
        ).fetchall():
            keep, reason = self.decision(profile)
            self.conn.execute(
                "UPDATE tg_profiles SET is_listed=%s,filter_reason=%s,updated_at=now() WHERE id=%s",
                (bool(keep), reason, profile["id"]),
            )
            count += 1
        return count

    def export_rows(self):
        return self.conn.execute("""SELECT p.*,p.user_count AS count FROM tg_profiles p
            WHERE p.is_listed AND NOT p.is_blacklisted AND p.status='available'
              AND NOT EXISTS (SELECT 1 FROM blacklist b WHERE lower(b.username)=lower(p.username) OR b.url=p.url OR b.telegram_id=p.telegram_id)
            ORDER BY p.user_count DESC NULLS LAST,lower(p.username),p.id""").fetchall()

    def migrate_lists(self, path):
        counts = {"inserted": 0, "existing": 0, "conflicts": 0}
        # 只读 SQLite，不导入 tg_profiles 或采集队列。
        with sqlite3.connect(
            Path(path).resolve().as_uri() + "?mode=ro", uri=True
        ) as old:
            old.row_factory = sqlite3.Row
            for table in ("blacklist", "whitelist"):
                fields = ["telegram_id", "type", "title", "username", "url", "reason"]
                if table == "blacklist":
                    fields += ["reason_type"]
                for row in old.execute("SELECT * FROM " + table):
                    data = dict(row)
                    normalized = normalize(data["url"])
                    if (
                        not normalized
                        or normalized[1].lower() != data["username"].lower()
                    ):
                        counts["conflicts"] += 1
                        logging.warning(
                            "%s / %s：无法规范化地址，未迁移", table, data["username"]
                        )
                        continue
                    data["url"] = normalized[0]
                    matches = self.conn.execute(
                        sql.SQL(
                            "SELECT * FROM {} WHERE lower(username)=lower(%s) OR url=%s OR telegram_id=%s"
                        ).format(sql.Identifier(table)),
                        (data["username"], data["url"], data["telegram_id"]),
                    ).fetchall()
                    if matches:
                        identical = len(matches) == 1 and all(
                            matches[0][k] == data[k] for k in fields
                        )
                        counts["existing" if identical else "conflicts"] += 1
                        if not identical:
                            logging.warning(
                                "%s / %s：身份或内容冲突，保留 PostgreSQL 现有值",
                                table,
                                data["username"],
                            )
                        continue
                    try:
                        with self.conn.transaction():
                            self.conn.execute(
                                sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
                                    sql.Identifier(table),
                                    sql.SQL(",").join(map(sql.Identifier, fields)),
                                    sql.SQL(",").join(
                                        sql.Placeholder() for _ in fields
                                    ),
                                ),
                                tuple(data[k] for k in fields),
                            )
                    except psycopg.IntegrityError:
                        counts["conflicts"] += 1
                        logging.warning(
                            "%s / %s：不满足资料约束，未迁移", table, data["username"]
                        )
                        continue
                    counts["inserted"] += 1
        return counts
