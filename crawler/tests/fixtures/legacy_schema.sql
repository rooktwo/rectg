------------------------------------------------------------------------------------------------------------------------

-- 通用字典表
CREATE TABLE IF NOT EXISTS dict_items (
    id          BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    dict_type   TEXT        NOT NULL,
    code        TEXT        NOT NULL,
    name        TEXT        NOT NULL,
    description TEXT,
    is_enabled  BOOLEAN     NOT NULL DEFAULT TRUE,
    sort_order  INTEGER     NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),


    -- 唯一约束
    CONSTRAINT uk__dict_items__dict_type_code UNIQUE (dict_type, code),

    -- 检查约束
    CONSTRAINT ck__dict_items__dict_type CHECK (btrim(dict_type) <> ''),
    CONSTRAINT ck__dict_items__code CHECK (btrim(code) <> ''),
    CONSTRAINT ck__dict_items__name CHECK (btrim(name) <> '')
);


-- 表与字段注释
COMMENT ON TABLE dict_items IS '通用字典表';

COMMENT ON COLUMN dict_items.id          IS 'ID';
COMMENT ON COLUMN dict_items.dict_type   IS '字典分类编码，按主要归属表名__字段名命名，如 telegram_profiles__type；相同含义的字段复用同一分类';
COMMENT ON COLUMN dict_items.code        IS '字典项编码，同一分类内唯一，供业务字段存储和引用';
COMMENT ON COLUMN dict_items.name        IS '字典项显示名称';
COMMENT ON COLUMN dict_items.description IS '字典项含义及使用说明';
COMMENT ON COLUMN dict_items.is_enabled  IS '是否启用；停用后不再供新增或变更选择，历史记录保留';
COMMENT ON COLUMN dict_items.sort_order  IS '显示顺序，数值越小越靠前';
COMMENT ON COLUMN dict_items.created_at  IS '创建时间';
COMMENT ON COLUMN dict_items.updated_at  IS '更新时间';

------------------------------------------------------------------------------------------------------------------------

-- Telegram 资料表
CREATE TABLE IF NOT EXISTS tg_profiles (
    id             BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    telegram_id    BIGINT      NOT NULL,
    username       TEXT        NOT NULL,
    url            TEXT        NOT NULL,
    type           TEXT,
    type_dict      TEXT        GENERATED ALWAYS AS ('telegram_profiles__type'::TEXT) STORED NOT NULL,
    title          TEXT,
    description    TEXT,
    user_count     BIGINT,
    status         TEXT        NOT NULL DEFAULT 'unknown',
    status_dict    TEXT        GENERATED ALWAYS AS ('telegram_profiles__status'::TEXT) STORED NOT NULL,
    is_blacklisted BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),


    -- 唯一约束
    CONSTRAINT uk__tg_profiles__telegram_id UNIQUE (telegram_id),
    CONSTRAINT uk__tg_profiles__url UNIQUE (url),

    -- 检查约束
    CONSTRAINT ck__tg_profiles__user_count CHECK (user_count >= 0),

    -- 外键约束
    CONSTRAINT fk__tg_profiles__type_dict_type FOREIGN KEY (type_dict, type) REFERENCES dict_items (dict_type, code) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT fk__tg_profiles__status_dict_status FOREIGN KEY (status_dict, status) REFERENCES dict_items (dict_type, code) ON UPDATE RESTRICT ON DELETE RESTRICT
);


-- 表与字段注释
COMMENT ON TABLE tg_profiles IS 'Telegram 资料表';

COMMENT ON COLUMN tg_profiles.id             IS 'ID';
COMMENT ON COLUMN tg_profiles.telegram_id    IS 'Telegram 唯一 ID，统一使用 Bot API 格式';
COMMENT ON COLUMN tg_profiles.username       IS '用户名，保留原始大小写，唯一性校验不区分大小写';
COMMENT ON COLUMN tg_profiles.url            IS '链接';
COMMENT ON COLUMN tg_profiles.type           IS '类型编码，引用 telegram_profiles__type 字典';
COMMENT ON COLUMN tg_profiles.type_dict      IS '类型字典分类，固定为 telegram_profiles__type，由数据库自动生成';
COMMENT ON COLUMN tg_profiles.title          IS '名称';
COMMENT ON COLUMN tg_profiles.description    IS '简介';
COMMENT ON COLUMN tg_profiles.user_count     IS '用户人数：channel 为订阅人数，group 为成员数，bot 为月活跃用户数；未获取时为空';
COMMENT ON COLUMN tg_profiles.status         IS '状态字典项编码，引用 telegram_profiles__status 字典，默认 unknown；私有和删除须有明确证据，网络错误不改变状态';
COMMENT ON COLUMN tg_profiles.status_dict    IS '状态字典分类，固定为 telegram_profiles__status，由数据库自动生成';
COMMENT ON COLUMN tg_profiles.is_blacklisted IS '是否被拉黑';
COMMENT ON COLUMN tg_profiles.created_at     IS '创建时间';
COMMENT ON COLUMN tg_profiles.updated_at     IS '更新时间';


-- 唯一索引
CREATE UNIQUE INDEX IF NOT EXISTS uk__tg_profiles__username ON tg_profiles (lower(username));

------------------------------------------------------------------------------------------------------------------------

-- Telegram 黑名单表
CREATE TABLE IF NOT EXISTS blacklist (
    id               BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    telegram_id      BIGINT      NOT NULL,
    type             TEXT        NOT NULL,
    type_dict        TEXT        GENERATED ALWAYS AS ('telegram_profiles__type'::TEXT) STORED NOT NULL,
    title            TEXT,
    username         TEXT        NOT NULL,
    url              TEXT        NOT NULL,
    reason_type      TEXT        NOT NULL,
    reason_type_dict TEXT        GENERATED ALWAYS AS ('blacklist__reason_type'::TEXT) STORED NOT NULL,
    reason           TEXT        NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),


    -- 唯一约束
    CONSTRAINT uk__blacklist__telegram_id UNIQUE (telegram_id),
    CONSTRAINT uk__blacklist__url UNIQUE (url),

    -- 检查约束
    CONSTRAINT ck__blacklist__reason CHECK (reason ~ '[^[:space:]]'),

    -- 外键约束
    CONSTRAINT fk__blacklist__type_dict_type FOREIGN KEY (type_dict, type) REFERENCES dict_items (dict_type, code) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT fk__blacklist__reason_type_dict_reason_type FOREIGN KEY (reason_type_dict, reason_type) REFERENCES dict_items (dict_type, code) ON UPDATE RESTRICT ON DELETE RESTRICT
);


-- 表与字段注释
COMMENT ON TABLE blacklist IS 'Telegram 黑名单表';

COMMENT ON COLUMN blacklist.id               IS 'ID';
COMMENT ON COLUMN blacklist.telegram_id      IS 'Telegram 唯一 ID，统一使用 Bot API 格式';
COMMENT ON COLUMN blacklist.type             IS '类型编码，引用 telegram_profiles__type 字典';
COMMENT ON COLUMN blacklist.type_dict        IS '类型字典分类，固定为 telegram_profiles__type，由数据库自动生成';
COMMENT ON COLUMN blacklist.title            IS '名称';
COMMENT ON COLUMN blacklist.username         IS '用户名，保留原始大小写，唯一性校验不区分大小写';
COMMENT ON COLUMN blacklist.url              IS '链接';
COMMENT ON COLUMN blacklist.reason_type      IS '黑名单原因分类编码，引用 blacklist__reason_type 字典';
COMMENT ON COLUMN blacklist.reason_type_dict IS '黑名单原因字典分类，固定为 blacklist__reason_type，由数据库自动生成';
COMMENT ON COLUMN blacklist.reason           IS '黑名单原因说明，必须包含非空白内容';
COMMENT ON COLUMN blacklist.created_at       IS '创建时间';
COMMENT ON COLUMN blacklist.updated_at       IS '更新时间';


-- 唯一索引
CREATE UNIQUE INDEX IF NOT EXISTS uk__blacklist__username ON blacklist (lower(username));

------------------------------------------------------------------------------------------------------------------------

-- Telegram 白名单表
CREATE TABLE IF NOT EXISTS whitelist (
    id          BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    telegram_id BIGINT      NOT NULL,
    type        TEXT        NOT NULL,
    type_dict   TEXT        GENERATED ALWAYS AS ('telegram_profiles__type'::TEXT) STORED NOT NULL,
    title       TEXT,
    username    TEXT        NOT NULL,
    url         TEXT        NOT NULL,
    reason      TEXT        NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),


    -- 唯一约束
    CONSTRAINT uk__whitelist__telegram_id UNIQUE (telegram_id),
    CONSTRAINT uk__whitelist__url UNIQUE (url),

    -- 检查约束
    CONSTRAINT ck__whitelist__reason CHECK (reason ~ '[^[:space:]]'),

    -- 外键约束
    CONSTRAINT fk__whitelist__type_dict_type FOREIGN KEY (type_dict, type) REFERENCES dict_items (dict_type, code) ON UPDATE RESTRICT ON DELETE RESTRICT
);


-- 表与字段注释
COMMENT ON TABLE whitelist IS 'Telegram 白名单表';

COMMENT ON COLUMN whitelist.id          IS 'ID';
COMMENT ON COLUMN whitelist.telegram_id IS 'Telegram 唯一 ID，统一使用 Bot API 格式';
COMMENT ON COLUMN whitelist.type        IS '类型编码，引用 telegram_profiles__type 字典';
COMMENT ON COLUMN whitelist.type_dict   IS '类型字典分类，固定为 telegram_profiles__type，由数据库自动生成';
COMMENT ON COLUMN whitelist.title       IS '名称';
COMMENT ON COLUMN whitelist.username    IS '用户名，保留原始大小写，唯一性校验不区分大小写';
COMMENT ON COLUMN whitelist.url         IS '链接';
COMMENT ON COLUMN whitelist.reason      IS '加入白名单的原因说明，必须包含非空白内容';
COMMENT ON COLUMN whitelist.created_at  IS '创建时间';
COMMENT ON COLUMN whitelist.updated_at  IS '更新时间';


-- 唯一索引
CREATE UNIQUE INDEX IF NOT EXISTS uk__whitelist__username ON whitelist (lower(username));

------------------------------------------------------------------------------------------------------------------------
