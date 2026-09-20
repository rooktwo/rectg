from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import Mock

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

from crawler.storage import Store, initialize, IdentityConflict, writer_lock, ROOT
from crawler.models import Candidate, SourceResult
from crawler.http import FetchError
from crawler.pipeline import collect
from crawler.exporter import export_readme

DSN = os.environ.get("RECTG_TEST_DATABASE_URL")


@unittest.skipUnless(
    DSN, "设置 RECTG_TEST_DATABASE_URL 指向临时 PostgreSQL 才运行数据库集成测试"
)
class StorageTests(unittest.TestCase):
    def setUp(self):
        self.conn = psycopg.connect(DSN, autocommit=True, row_factory=dict_row)
        self.schema = "test_" + uuid.uuid4().hex
        self.conn.execute(
            sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema))
        )
        self.conn.execute(
            sql.SQL("SET search_path TO {}").format(sql.Identifier(self.schema))
        )
        initialize(self.conn)
        self.store = Store(self.conn)
        self.temp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.conn.execute(
            sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema))
        )
        self.conn.close()
        self.temp.cleanup()

    def target(self, name="ExampleChan", source="fixture"):
        item = Candidate(
            "https://t.me/" + name.lower(),
            name,
            "中文频道",
            page_url="https://example.com/page",
        )
        result = SourceResult(source, "https://example.com/", candidates=[item])
        self.store.save_source(result, self.store.start_run(source, result.source_url))
        return self.conn.execute(
            "SELECT * FROM crawl_targets WHERE lower(username)=lower(%s)", (name,)
        ).fetchone()

    def sample(self, target, **changes):
        return dict(
            dict(
                url=target["url"],
                username=target["username"],
                telegram_id=None,
                type="channel",
                title="中文技术频道",
                description="分享技术文章",
                count=500,
                last_active=None,
                status="available",
            ),
            **changes,
        )

    def test_idempotent_initialization_and_nullable_identity(self):
        self.conn.execute("UPDATE dict_items SET name='自定义' WHERE code='channel'")
        initialize(self.conn)
        self.assertEqual(
            self.conn.execute(
                "SELECT name FROM dict_items WHERE code='channel'"
            ).fetchone()["name"],
            "自定义",
        )
        for name in ("FirstChan", "SecondChan"):
            target = self.target(name)
            self.store.save_profile(target, self.sample(target))
        self.assertEqual(
            self.conn.execute(
                "SELECT count(*) n FROM tg_profiles WHERE telegram_id IS NULL"
            ).fetchone()["n"],
            2,
        )

    def test_source_provenance_case_dedup_and_repeat(self):
        self.target("ExampleChan", "first")
        self.target("examplechan", "second")
        self.target("ExampleChan", "first")
        self.assertEqual(
            self.conn.execute("SELECT count(*) n FROM crawl_targets").fetchone()["n"], 1
        )
        self.assertEqual(
            self.conn.execute("SELECT count(*) n FROM crawl_target_sources").fetchone()[
                "n"
            ],
            2,
        )

    def test_network_failure_preserves_profile_and_retries_before_30_days(self):
        target = self.target()
        self.store.save_profile(target, self.sample(target, telegram_id=-100123))
        before = self.conn.execute("SELECT * FROM tg_profiles").fetchone()
        fetcher = Mock()
        fetcher.get.side_effect = FetchError("rate_limited", "HTTP 429")
        # 0 天强制刷新，让刚成功采集的记录进入本轮。
        success, failed = collect(self.store, fetcher, older_days=0)
        self.assertEqual((success, failed), (0, 1))
        self.assertEqual(
            self.conn.execute("SELECT * FROM tg_profiles").fetchone(), before
        )
        self.assertEqual(self.store.due(), [])
        self.conn.execute(
            "UPDATE crawl_targets SET next_attempt_at=now()-INTERVAL '1 second'"
        )
        self.assertEqual(len(self.store.due()), 1)
        self.assertEqual(self.store.due()[0]["failure_count"], 1)

    def test_claim_interrupt_and_resume(self):
        target = self.target()
        self.store.claim(target)
        self.assertEqual(self.store.due(), [])
        self.conn.execute(
            "UPDATE crawl_targets SET next_attempt_at=now()-INTERVAL '1 second'"
        )
        self.assertEqual(len(self.store.due(new=True)), 1)
        self.store.save_profile(target, self.sample(target))
        self.store.claim(target)
        self.assertEqual(self.store.due(), [])
        self.conn.execute(
            "UPDATE crawl_targets SET next_attempt_at=now()-INTERVAL '1 second'"
        )
        self.assertEqual(len(self.store.due()), 1)
        self.assertEqual(self.store.due(new=True), [])
        run = self.store.start_run("lost", "https://example.com/")
        self.store.recover_runs()
        self.assertEqual(
            self.conn.execute(
                "SELECT status FROM crawl_source_runs WHERE id=%s", (run,)
            ).fetchone()["status"],
            "interrupted",
        )

    def test_identity_conflict_and_later_id_fill(self):
        target = self.target()
        self.store.save_profile(target, self.sample(target))
        self.store.save_profile(target, self.sample(target, telegram_id=-100123))
        with self.assertRaises(IdentityConflict):
            self.store.save_profile(target, self.sample(target, telegram_id=-100456))
        self.assertEqual(
            self.conn.execute("SELECT telegram_id FROM tg_profiles").fetchone()[
                "telegram_id"
            ],
            -100123,
        )
        second = self.target("AnotherChan")
        self.store.save_profile(second, self.sample(second, telegram_id=-100789))
        with self.assertRaises(IdentityConflict):
            self.store.save_profile(target, self.sample(target, telegram_id=-100789))
        third = self.target("ThirdChan")
        with self.assertRaises(IdentityConflict):
            self.store.save_profile(third, self.sample(third, telegram_id=-100123))
        self.assertEqual(
            self.conn.execute(
                "SELECT username FROM tg_profiles WHERE telegram_id=-100123"
            ).fetchone()["username"],
            target["username"],
        )

    def test_lists_and_private_status(self):
        target = self.target()
        self.store.save_profile(
            target, self.sample(target, count=1, title="English", description="博彩")
        )
        self.assertFalse(
            self.conn.execute("SELECT is_listed FROM tg_profiles").fetchone()[
                "is_listed"
            ]
        )
        self.conn.execute(
            "INSERT INTO whitelist (username,url,type,reason) VALUES (%s,%s,'channel','人工审核')",
            (target["username"], target["url"]),
        )
        self.store.refilter()
        self.assertTrue(
            self.conn.execute("SELECT is_listed FROM tg_profiles").fetchone()[
                "is_listed"
            ]
        )
        self.conn.execute(
            "INSERT INTO blacklist (username,url,type,reason_type,reason) VALUES (%s,%s,'channel','other','人工拉黑')",
            (target["username"], target["url"]),
        )
        self.assertEqual(self.store.export_rows(), [])
        self.store.refilter()
        self.assertFalse(
            self.conn.execute("SELECT is_listed FROM tg_profiles").fetchone()[
                "is_listed"
            ]
        )
        self.conn.execute("DELETE FROM blacklist")
        self.store.refilter()
        self.store.save_profile(
            target, self.sample(target, status="private", type=None, title=None)
        )
        row = self.conn.execute("SELECT * FROM tg_profiles").fetchone()
        self.assertEqual(row["status"], "private")
        self.assertFalse(row["is_listed"])
        self.assertEqual(row["title"], "English")

    def test_migrate_only_lists_and_preserve_manual_changes(self):
        path = Path(self.temp.name) / "legacy.db"
        with sqlite3.connect(path) as c:
            c.execute(
                "CREATE TABLE blacklist (telegram_id INTEGER,type TEXT,title TEXT,username TEXT,url TEXT,reason TEXT,reason_type TEXT)"
            )
            c.execute(
                "CREATE TABLE whitelist (telegram_id INTEGER,type TEXT,title TEXT,username TEXT,url TEXT,reason TEXT)"
            )
            c.execute(
                "INSERT INTO blacklist VALUES (123,'bot','title','ExampleBot','https://t.me/ExampleBot','reason','other')"
            )
            c.execute("CREATE TABLE tg_profiles (username TEXT)")
            c.execute("INSERT INTO tg_profiles VALUES ('DoNotMigrate')")
        self.assertEqual(
            self.store.migrate_lists(path),
            {"inserted": 1, "existing": 0, "conflicts": 0},
        )
        self.assertEqual(
            self.store.migrate_lists(path),
            {"inserted": 0, "existing": 1, "conflicts": 0},
        )
        self.conn.execute("UPDATE blacklist SET reason='人工修改'")
        self.assertEqual(self.store.migrate_lists(path)["conflicts"], 1)
        self.assertEqual(
            self.conn.execute("SELECT count(*) n FROM tg_profiles").fetchone()["n"], 0
        )
        self.assertEqual(
            self.conn.execute("SELECT reason FROM blacklist").fetchone()["reason"],
            "人工修改",
        )

    def test_atomic_export_and_empty_guard(self):
        output = Path(self.temp.name) / "README.md"
        output.write_text("old")
        with self.assertRaises(ValueError):
            export_readme(self.store, output)
        self.assertEqual(output.read_text(), "old")
        target = self.target()
        self.store.save_profile(
            target, self.sample(target, title="中文频道 <img src=x onerror=alert(1)>")
        )
        # 用白名单模拟豁免内容过滤，HTML 输出仍必须转义。
        self.conn.execute(
            "INSERT INTO whitelist (username,url,type,reason) VALUES (%s,%s,'channel','test')",
            (target["username"], target["url"]),
        )
        self.store.refilter()
        self.assertEqual(export_readme(self.store, output), 1)
        self.assertNotIn("<img", output.read_text())
        self.assertIn("https://t.me/examplechan", output.read_text())
        self.assertEqual(list(output.parent.iterdir()), [output])

    def test_writer_lock_blocks_concurrent_job(self):
        other = psycopg.connect(DSN, autocommit=True, row_factory=dict_row)
        try:
            with writer_lock(self.conn):
                with self.assertRaises(ValueError):
                    with writer_lock(other):
                        pass
        finally:
            other.close()

    def test_explicit_upgrade_of_old_schema(self):
        self.conn.execute(
            sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(self.schema))
        )
        self.conn.execute(
            sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema))
        )
        self.conn.execute(
            (Path(__file__).parent / "fixtures/legacy_schema.sql").read_text()
        )
        self.conn.execute((ROOT / "db/postgresql/02_init_dict_items.sql").read_text())
        self.conn.execute(
            "INSERT INTO tg_profiles (telegram_id,username,url,title,type) VALUES (123,'OldChan','https://t.me/oldchan','保留资料','channel')"
        )
        with self.assertRaises(ValueError):
            initialize(self.conn)
        initialize(self.conn, upgrade=True)
        initialize(self.conn, upgrade=True)
        row = self.conn.execute("SELECT * FROM tg_profiles").fetchone()
        self.assertEqual(row["title"], "保留资料")
        self.assertFalse(row["is_listed"])
        self.assertEqual(
            [target["username"] for target in self.store.due()], ["OldChan"]
        )
