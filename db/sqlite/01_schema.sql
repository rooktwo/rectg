PRAGMA foreign_keys = ON;

------------------------------------------------------------------------------------------------------------------------

-- 通用字典表
CREATE TABLE IF NOT EXISTS dict_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,

    dict_type   TEXT    NOT NULL,
    code        TEXT    NOT NULL,
    name        TEXT    NOT NULL,
    description TEXT,
    is_enabled  INTEGER NOT NULL DEFAULT TRUE CHECK (is_enabled IN (0, 1)),
    sort_order  INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,


    -- 唯一约束
    CONSTRAINT uk__dict_items__dict_type_code UNIQUE (dict_type, code),

    -- 检查约束
    CONSTRAINT ck__dict_items__dict_type CHECK (trim(dict_type) <> ''),
    CONSTRAINT ck__dict_items__code CHECK (trim(code) <> ''),
    CONSTRAINT ck__dict_items__name CHECK (trim(name) <> '')
);


-- 表与字段注释
-- dict_items: 通用字典表

-- dict_items.id: ID
-- dict_items.dict_type: 字典分类编码，按主要归属表名__字段名命名，如 telegram_profiles__type；相同含义的字段复用同一分类
-- dict_items.code: 字典项编码，同一分类内唯一，供业务字段存储和引用
-- dict_items.name: 字典项显示名称
-- dict_items.description: 字典项含义及使用说明
-- dict_items.is_enabled: 是否启用；停用后不再供新增或变更选择，历史记录保留
-- dict_items.sort_order: 显示顺序，数值越小越靠前
-- dict_items.created_at: 创建时间
-- dict_items.updated_at: 更新时间

------------------------------------------------------------------------------------------------------------------------

-- Telegram 资料表
CREATE TABLE IF NOT EXISTS tg_profiles (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,

    telegram_id    INTEGER NOT NULL,
    username       TEXT    NOT NULL,
    url            TEXT    NOT NULL,
    type           TEXT,
    type_dict      TEXT    GENERATED ALWAYS AS ('telegram_profiles__type') STORED NOT NULL,
    title          TEXT,
    description    TEXT,
    user_count     INTEGER,
    status         TEXT    NOT NULL DEFAULT 'unknown',
    status_dict    TEXT    GENERATED ALWAYS AS ('telegram_profiles__status') STORED NOT NULL,
    is_blacklisted INTEGER NOT NULL DEFAULT FALSE CHECK (is_blacklisted IN (0, 1)),
    created_at     TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,


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
-- tg_profiles: Telegram 资料表

-- tg_profiles.id: ID
-- tg_profiles.telegram_id: Telegram 唯一 ID，统一使用 Bot API 格式
-- tg_profiles.username: 用户名，保留原始大小写，唯一性校验不区分大小写
-- tg_profiles.url: 链接
-- tg_profiles.type: 类型编码，引用 telegram_profiles__type 字典
-- tg_profiles.type_dict: 类型字典分类，固定为 telegram_profiles__type，由数据库自动生成
-- tg_profiles.title: 名称
-- tg_profiles.description: 简介
-- tg_profiles.user_count: 用户人数：channel 为订阅人数，group 为成员数，bot 为月活跃用户数；未获取时为空
-- tg_profiles.status: 状态字典项编码，引用 telegram_profiles__status 字典，默认 unknown；私有和删除须有明确证据，网络错误不改变状态
-- tg_profiles.status_dict: 状态字典分类，固定为 telegram_profiles__status，由数据库自动生成
-- tg_profiles.is_blacklisted: 是否被拉黑
-- tg_profiles.created_at: 创建时间
-- tg_profiles.updated_at: 更新时间


-- 唯一索引
CREATE UNIQUE INDEX IF NOT EXISTS uk__tg_profiles__username ON tg_profiles (lower(username));

------------------------------------------------------------------------------------------------------------------------

-- Telegram 黑名单表
CREATE TABLE IF NOT EXISTS blacklist (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,

    telegram_id      INTEGER NOT NULL,
    type             TEXT    NOT NULL,
    type_dict        TEXT    GENERATED ALWAYS AS ('telegram_profiles__type') STORED NOT NULL,
    title            TEXT,
    username         TEXT    NOT NULL,
    url              TEXT    NOT NULL,
    reason_type      TEXT    NOT NULL,
    reason_type_dict TEXT    GENERATED ALWAYS AS ('blacklist__reason_type') STORED NOT NULL,
    reason           TEXT    NOT NULL,
    created_at       TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,


    -- 唯一约束
    CONSTRAINT uk__blacklist__telegram_id UNIQUE (telegram_id),
    CONSTRAINT uk__blacklist__url UNIQUE (url),

    -- 检查约束
    CONSTRAINT ck__blacklist__reason CHECK (trim(reason, char(9, 10, 11, 12, 13, 32)) <> ''),

    -- 外键约束
    CONSTRAINT fk__blacklist__type_dict_type FOREIGN KEY (type_dict, type) REFERENCES dict_items (dict_type, code) ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT fk__blacklist__reason_type_dict_reason_type FOREIGN KEY (reason_type_dict, reason_type) REFERENCES dict_items (dict_type, code) ON UPDATE RESTRICT ON DELETE RESTRICT
);


-- 表与字段注释
-- blacklist: Telegram 黑名单表

-- blacklist.id: ID
-- blacklist.telegram_id: Telegram 唯一 ID，统一使用 Bot API 格式
-- blacklist.type: 类型编码，引用 telegram_profiles__type 字典
-- blacklist.type_dict: 类型字典分类，固定为 telegram_profiles__type，由数据库自动生成
-- blacklist.title: 名称
-- blacklist.username: 用户名，保留原始大小写，唯一性校验不区分大小写
-- blacklist.url: 链接
-- blacklist.reason_type: 黑名单原因分类编码，引用 blacklist__reason_type 字典
-- blacklist.reason_type_dict: 黑名单原因字典分类，固定为 blacklist__reason_type，由数据库自动生成
-- blacklist.reason: 黑名单原因说明，必须包含非空白内容
-- blacklist.created_at: 创建时间
-- blacklist.updated_at: 更新时间


-- 唯一索引
CREATE UNIQUE INDEX IF NOT EXISTS uk__blacklist__username ON blacklist (lower(username));

------------------------------------------------------------------------------------------------------------------------

-- Telegram 白名单表
CREATE TABLE IF NOT EXISTS whitelist (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,

    telegram_id INTEGER NOT NULL,
    type        TEXT    NOT NULL,
    type_dict   TEXT    GENERATED ALWAYS AS ('telegram_profiles__type') STORED NOT NULL,
    title       TEXT,
    username    TEXT    NOT NULL,
    url         TEXT    NOT NULL,
    reason      TEXT    NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,


    -- 唯一约束
    CONSTRAINT uk__whitelist__telegram_id UNIQUE (telegram_id),
    CONSTRAINT uk__whitelist__url UNIQUE (url),

    -- 检查约束
    CONSTRAINT ck__whitelist__reason CHECK (trim(reason, char(9, 10, 11, 12, 13, 32)) <> ''),

    -- 外键约束
    CONSTRAINT fk__whitelist__type_dict_type FOREIGN KEY (type_dict, type) REFERENCES dict_items (dict_type, code) ON UPDATE RESTRICT ON DELETE RESTRICT
);


-- 表与字段注释
-- whitelist: Telegram 白名单表

-- whitelist.id: ID
-- whitelist.telegram_id: Telegram 唯一 ID，统一使用 Bot API 格式
-- whitelist.type: 类型编码，引用 telegram_profiles__type 字典
-- whitelist.type_dict: 类型字典分类，固定为 telegram_profiles__type，由数据库自动生成
-- whitelist.title: 名称
-- whitelist.username: 用户名，保留原始大小写，唯一性校验不区分大小写
-- whitelist.url: 链接
-- whitelist.reason: 加入白名单的原因说明，必须包含非空白内容
-- whitelist.created_at: 创建时间
-- whitelist.updated_at: 更新时间


-- 唯一索引
CREATE UNIQUE INDEX IF NOT EXISTS uk__whitelist__username ON whitelist (lower(username));

------------------------------------------------------------------------------------------------------------------------
