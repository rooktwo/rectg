INSERT INTO dict_items (dict_type, code, name, description, is_enabled, sort_order)
VALUES
    ('telegram_profiles__type', 'channel', '频道', 'Telegram 公开频道', TRUE, 10),
    ('telegram_profiles__type', 'group', '群组', 'Telegram 公开群组', TRUE, 20),
    ('telegram_profiles__type', 'bot', '机器人', 'Telegram 机器人', TRUE, 30)
ON CONFLICT (dict_type, code) DO NOTHING;

INSERT INTO dict_items (dict_type, code, name, description, is_enabled, sort_order)
VALUES
    ('telegram_profiles__status', 'unknown', '未知', '尚未确认资源状态', TRUE, 10),
    ('telegram_profiles__status', 'available', '正常可访问', '已确认资源存在且公开可访问，不能仅凭 HTTP 200 判定', TRUE, 20),
    ('telegram_profiles__status', 'private', '已确认私有', '有明确证据表明资源已转为私有，停止公开采集和展示', TRUE, 30),
    ('telegram_profiles__status', 'inaccessible', '不可访问', '资源不可访问但原因尚未明确，不包括单次网络错误或限流', TRUE, 40),
    ('telegram_profiles__status', 'deleted', '已确认删除', '有明确证据表明资源已删除，不能仅凭用户名无法解析或页面无法访问判定', TRUE, 50)
ON CONFLICT (dict_type, code) DO NOTHING;

INSERT INTO dict_items (dict_type, code, name, description, is_enabled, sort_order)
VALUES
    ('blacklist__reason_type', 'spam', '垃圾广告', '大量发布垃圾广告、重复推广或无关引流内容', TRUE, 10),
    ('blacklist__reason_type', 'scam', '诈骗欺诈', '涉及诈骗、钓鱼或冒充身份骗取财物和信息', TRUE, 20),
    ('blacklist__reason_type', 'gambling', '赌博博彩', '涉及赌博、博彩或相关推广内容', TRUE, 30),
    ('blacklist__reason_type', 'adult_content', '色情内容', '涉及不符合本站收录规则的色情内容', TRUE, 40),
    ('blacklist__reason_type', 'harmful_content', '其他有害内容', '涉及恶意软件、隐私泄露等未被上述分类覆盖的有害内容', TRUE, 50),
    ('blacklist__reason_type', 'other', '其他原因', '其他需要拉黑的情况，具体依据必须填写在 reason 中', TRUE, 90)
ON CONFLICT (dict_type, code) DO NOTHING;
