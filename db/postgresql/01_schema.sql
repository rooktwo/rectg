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
    id              BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    telegram_id     BIGINT,
    username        TEXT        NOT NULL,
    url             TEXT        NOT NULL,
    type            TEXT,
    type_dict       TEXT        GENERATED ALWAYS AS ('telegram_profiles__type'::TEXT) STORED NOT NULL,
    title           TEXT,
    description     TEXT,
    user_count      BIGINT,
    status          TEXT        NOT NULL DEFAULT 'unknown',
    status_dict     TEXT        GENERATED ALWAYS AS ('telegram_profiles__status'::TEXT) STORED NOT NULL,
    is_blacklisted  BOOLEAN     NOT NULL DEFAULT FALSE,
    avatar          TEXT,
    last_active     TIMESTAMPTZ,
    last_checked_at TIMESTAMPTZ,
    is_listed       BOOLEAN     NOT NULL DEFAULT FALSE,
    filter_reason   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),


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

COMMENT ON COLUMN tg_profiles.id              IS 'ID';
COMMENT ON COLUMN tg_profiles.telegram_id     IS 'Telegram 唯一 ID，统一使用 Bot API 格式，未获取时为空';
COMMENT ON COLUMN tg_profiles.username        IS '用户名，保留原始大小写，唯一性校验不区分大小写';
COMMENT ON COLUMN tg_profiles.url             IS '链接';
COMMENT ON COLUMN tg_profiles.type            IS '类型编码，引用 telegram_profiles__type 字典';
COMMENT ON COLUMN tg_profiles.type_dict       IS '类型字典分类，固定为 telegram_profiles__type，由数据库自动生成';
COMMENT ON COLUMN tg_profiles.title           IS '名称';
COMMENT ON COLUMN tg_profiles.description     IS '简介';
COMMENT ON COLUMN tg_profiles.user_count      IS '用户人数：channel 为订阅人数，group 为成员数，bot 为月活跃用户数；未获取时为空';
COMMENT ON COLUMN tg_profiles.status          IS '状态字典项编码，引用 telegram_profiles__status 字典，默认 unknown；私有和删除须有明确证据，网络错误不改变状态';
COMMENT ON COLUMN tg_profiles.status_dict     IS '状态字典分类，固定为 telegram_profiles__status，由数据库自动生成';
COMMENT ON COLUMN tg_profiles.is_blacklisted  IS '是否被拉黑';
COMMENT ON COLUMN tg_profiles.avatar          IS '头像地址';
COMMENT ON COLUMN tg_profiles.last_active     IS '频道最近消息时间，未获取时为空';
COMMENT ON COLUMN tg_profiles.last_checked_at IS '最近成功确认资源状态的时间';
COMMENT ON COLUMN tg_profiles.is_listed       IS '是否通过收录规则并允许导出';
COMMENT ON COLUMN tg_profiles.filter_reason   IS '未收录原因或白名单说明';
COMMENT ON COLUMN tg_profiles.created_at      IS '创建时间';
COMMENT ON COLUMN tg_profiles.updated_at      IS '更新时间';


-- 唯一索引
CREATE UNIQUE INDEX IF NOT EXISTS uk__tg_profiles__username ON tg_profiles (lower(username));

------------------------------------------------------------------------------------------------------------------------

-- Telegram 黑名单表
CREATE TABLE IF NOT EXISTS blacklist (
    id               BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    telegram_id      BIGINT,
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
COMMENT ON COLUMN blacklist.telegram_id      IS 'Telegram 唯一 ID，统一使用 Bot API 格式，未获取时为空';
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

    telegram_id BIGINT,
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
COMMENT ON COLUMN whitelist.telegram_id IS 'Telegram 唯一 ID，统一使用 Bot API 格式，未获取时为空';
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

-- Telegram 采集目标
CREATE TABLE IF NOT EXISTS crawl_targets (
    id              BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    username        TEXT        NOT NULL,
    url             TEXT        NOT NULL,
    name            TEXT,
    type_hint       TEXT,
    last_attempt_at TIMESTAMPTZ,
    last_success_at TIMESTAMPTZ,
    next_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    failure_count   INTEGER     NOT NULL DEFAULT 0,
    last_error      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),


    -- 唯一约束
    CONSTRAINT uk__crawl_targets__url UNIQUE (url),

    -- 检查约束
    CONSTRAINT ck__crawl_targets__failure_count CHECK (failure_count >= 0),
    CONSTRAINT ck__crawl_targets__type_hint CHECK (type_hint IN ('channel', 'group', 'bot'))
);


-- 表与字段注释
COMMENT ON TABLE crawl_targets IS 'Telegram 采集目标';

COMMENT ON COLUMN crawl_targets.id              IS 'ID';
COMMENT ON COLUMN crawl_targets.username        IS '用户名，唯一性忽略大小写';
COMMENT ON COLUMN crawl_targets.url             IS '规范化的 Telegram 公开主页地址';
COMMENT ON COLUMN crawl_targets.name            IS '来源提供的名称';
COMMENT ON COLUMN crawl_targets.type_hint       IS '来源提供的类型提示，不作为有效性证据';
COMMENT ON COLUMN crawl_targets.last_attempt_at IS '最近尝试采集的时间';
COMMENT ON COLUMN crawl_targets.last_success_at IS '最近成功确认状态的时间';
COMMENT ON COLUMN crawl_targets.next_attempt_at IS '下次允许采集的时间，包含失败退避和中断恢复';
COMMENT ON COLUMN crawl_targets.failure_count   IS '连续失败次数';
COMMENT ON COLUMN crawl_targets.last_error      IS '最近失败原因，成功后清空';
COMMENT ON COLUMN crawl_targets.created_at      IS '创建时间';
COMMENT ON COLUMN crawl_targets.updated_at      IS '更新时间';


-- 唯一索引
CREATE UNIQUE INDEX IF NOT EXISTS uk__crawl_targets__username ON crawl_targets (lower(username));


-- 普通索引
CREATE INDEX IF NOT EXISTS idx__crawl_targets__next_attempt_at ON crawl_targets (next_attempt_at);

------------------------------------------------------------------------------------------------------------------------

-- Telegram 采集目标来源
CREATE TABLE IF NOT EXISTS crawl_target_sources (
    id         BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    target_id  BIGINT      NOT NULL,
    source_id  TEXT        NOT NULL,
    source_url TEXT        NOT NULL,
    page_url   TEXT        NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),


    -- 唯一约束
    CONSTRAINT uk__crawl_target_sources__target_id_source_id_page_url UNIQUE (target_id, source_id, page_url),

    -- 外键约束
    CONSTRAINT fk__crawl_target_sources__target_id FOREIGN KEY (target_id) REFERENCES crawl_targets (id) ON UPDATE RESTRICT ON DELETE RESTRICT
);


-- 表与字段注释
COMMENT ON TABLE crawl_target_sources IS 'Telegram 采集目标来源';

COMMENT ON COLUMN crawl_target_sources.id         IS 'ID';
COMMENT ON COLUMN crawl_target_sources.target_id  IS '采集目标 ID';
COMMENT ON COLUMN crawl_target_sources.source_id  IS '独立来源文件名，不含扩展名';
COMMENT ON COLUMN crawl_target_sources.source_url IS '来源入口 URL';
COMMENT ON COLUMN crawl_target_sources.page_url   IS '实际发现链接的页面 URL';
COMMENT ON COLUMN crawl_target_sources.created_at IS '创建时间';
COMMENT ON COLUMN crawl_target_sources.updated_at IS '更新时间';

------------------------------------------------------------------------------------------------------------------------

-- 来源采集运行记录
CREATE TABLE IF NOT EXISTS crawl_source_runs (
    id              BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    source_id       TEXT        NOT NULL,
    source_url      TEXT        NOT NULL,
    status          TEXT        NOT NULL DEFAULT 'running',
    page_count      INTEGER     NOT NULL DEFAULT 0,
    candidate_count INTEGER     NOT NULL DEFAULT 0,
    error           TEXT,
    finished_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),


    -- 检查约束
    CONSTRAINT ck__crawl_source_runs__page_count CHECK (page_count >= 0),
    CONSTRAINT ck__crawl_source_runs__candidate_count CHECK (candidate_count >= 0)
);


-- 表与字段注释
COMMENT ON TABLE crawl_source_runs IS '来源采集运行记录';

COMMENT ON COLUMN crawl_source_runs.id              IS 'ID';
COMMENT ON COLUMN crawl_source_runs.source_id       IS '来源文件名，不含扩展名';
COMMENT ON COLUMN crawl_source_runs.source_url      IS '来源入口 URL，加载失败时为空字符串';
COMMENT ON COLUMN crawl_source_runs.status          IS '运行状态，包含成功、访问失败、解析为空、页数上限和中断';
COMMENT ON COLUMN crawl_source_runs.page_count      IS '已尝试访问的页面数';
COMMENT ON COLUMN crawl_source_runs.candidate_count IS '去重后的候选资源数';
COMMENT ON COLUMN crawl_source_runs.error           IS '来源失败或部分完成原因';
COMMENT ON COLUMN crawl_source_runs.finished_at     IS '运行结束时间';
COMMENT ON COLUMN crawl_source_runs.created_at      IS '创建时间';
COMMENT ON COLUMN crawl_source_runs.updated_at      IS '更新时间';


-- 普通索引
CREATE INDEX IF NOT EXISTS idx__crawl_source_runs__source_id ON crawl_source_runs (source_id);

------------------------------------------------------------------------------------------------------------------------
