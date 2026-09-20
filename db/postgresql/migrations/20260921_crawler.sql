------------------------------------------------------------------------------------------------------------------------

-- 将旧版资料与黑白名单表升级为可运行爬虫的结构。随后执行 01_schema.sql 和 02_init_dict_items.sql。
BEGIN;

ALTER TABLE tg_profiles ALTER COLUMN telegram_id DROP NOT NULL;
ALTER TABLE blacklist ALTER COLUMN telegram_id DROP NOT NULL;
ALTER TABLE whitelist ALTER COLUMN telegram_id DROP NOT NULL;
ALTER TABLE tg_profiles ADD COLUMN IF NOT EXISTS avatar TEXT;
ALTER TABLE tg_profiles ADD COLUMN IF NOT EXISTS last_active TIMESTAMPTZ;
ALTER TABLE tg_profiles ADD COLUMN IF NOT EXISTS last_checked_at TIMESTAMPTZ;
ALTER TABLE tg_profiles ADD COLUMN IF NOT EXISTS is_listed BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE tg_profiles ADD COLUMN IF NOT EXISTS filter_reason TEXT;

COMMIT;

------------------------------------------------------------------------------------------------------------------------
