"""SQLite 数据库连接与初始化（原生 sqlite3，无需额外 ORM 依赖）"""
import sqlite3

from flask import current_app, g
from werkzeug.security import generate_password_hash

from utils import now_iso

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,
    nickname      TEXT,
    password_hash TEXT    NOT NULL,
    role          TEXT    NOT NULL DEFAULT 'user',
    status        TEXT    NOT NULL DEFAULT 'active',
    openid        TEXT,
    unionid       TEXT,
    created_at    TEXT    NOT NULL,
    UNIQUE (openid)
);

CREATE TABLE IF NOT EXISTS posts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    zone       TEXT    NOT NULL,
    title      TEXT    NOT NULL,
    content    TEXT    NOT NULL,
    author_id  INTEGER NOT NULL,
    created_at TEXT    NOT NULL,
    FOREIGN KEY (author_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS replies (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id    INTEGER NOT NULL,
    content    TEXT    NOT NULL,
    author_id  INTEGER NOT NULL,
    created_at TEXT    NOT NULL,
    FOREIGN KEY (post_id)   REFERENCES posts (id),
    FOREIGN KEY (author_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS operation_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    operator    TEXT    NOT NULL,                -- 操作人
    action      TEXT    NOT NULL,                -- 操作类型 key
    action_name TEXT    NOT NULL,                -- 操作类型中文名
    target_type TEXT,                            -- 目标类型（中文）
    target_id   TEXT,                            -- 目标标识
    content     TEXT,                            -- 操作内容/详情
    result      TEXT    NOT NULL DEFAULT 'success',  -- success / fail
    ip          TEXT,                            -- 来源 IP
    created_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS error_logs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    message      TEXT    NOT NULL,               -- 错误信息
    stack        TEXT,                           -- 错误堆栈
    path         TEXT,                           -- 触发接口
    method       TEXT,                           -- 请求方法
    params       TEXT,                           -- 请求参数（JSON，敏感字段脱敏）
    user_context TEXT,                           -- 用户上下文（JSON）
    created_at   TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_posts_zone      ON posts (zone);
CREATE INDEX IF NOT EXISTS idx_posts_created   ON posts (created_at);
CREATE INDEX IF NOT EXISTS idx_replies_post_id ON replies (post_id);
CREATE INDEX IF NOT EXISTS idx_replies_created ON replies (created_at);
CREATE INDEX IF NOT EXISTS idx_op_logs_created   ON operation_logs (created_at);
CREATE INDEX IF NOT EXISTS idx_op_logs_operator  ON operation_logs (operator);
CREATE INDEX IF NOT EXISTS idx_op_logs_action    ON operation_logs (action);
CREATE INDEX IF NOT EXISTS idx_err_logs_created  ON error_logs (created_at);
"""


def get_db() -> sqlite3.Connection:
    """每个请求复用一个连接"""
    if 'db' not in g:
        conn = sqlite3.connect(current_app.config['DATABASE'])
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        g.db = conn
    return g.db


def close_db(exc=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """建表、迁移并写入演示数据（仅首次）"""
    db = get_db()
    db.executescript(SCHEMA)
    db.commit()

    # 迁移：旧库 users 表可能没有 status / openid / unionid / nickname 列，补齐
    cols = {row['name'] for row in db.execute('PRAGMA table_info(users)').fetchall()}
    for col, defval in (('status', "NOT NULL DEFAULT 'active'"),
                        ('openid', ''),
                        ('unionid', ''),
                        ('nickname', '')):
        if col not in cols:
            db.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT {defval}")
    # 补数据：旧用户 nickname 为空时默认取 username
    db.execute("UPDATE users SET nickname = username WHERE nickname IS NULL OR nickname = ''")
    db.commit()

    if db.execute('SELECT COUNT(*) FROM users').fetchone()[0] > 0:
        return

    # 演示账号（与前端登录页提示一致）
    users = [
        ('demo', '123456', 'user'),
        ('vip1', '123456', 'vip1'),
    ]
    user_ids = {}
    for username, password, role in users:
        cur = db.execute(
            'INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)',
            (username, generate_password_hash(password), role, now_iso()),
        )
        user_ids[username] = cur.lastrowid

    # 示例帖子，方便首页/论坛直接有内容
    demo_id = user_ids['demo']
    vip_id = user_ids['vip1']
    posts = [
        ('vip', '长期收购有机玉米，量大从优', '要求品质优良、供货稳定，月需求量 5 吨以上，欢迎有货源的老板联系。', vip_id),
        ('vip', '求购散养土鸡蛋，每日 200 斤', '优先合作周边农场，支持现场考察，价格私聊。', vip_id),
        ('free', '今年玉米行情大家怎么看？', '最近价格波动有点大，想听听各位同行的判断和建议。', demo_id),
        ('free', '新手报道，请教几个种植问题', '刚入行不久，想问下春播的时间和施肥需要注意什么？', demo_id),
    ]
    post_ids = []
    for zone, title, content, author_id in posts:
        cur = db.execute(
            'INSERT INTO posts (zone, title, content, author_id, created_at) VALUES (?, ?, ?, ?, ?)',
            (zone, title, content, author_id, now_iso()),
        )
        post_ids.append(cur.lastrowid)

    # 给第一条帖子加一条回复
    db.execute(
        'INSERT INTO replies (post_id, content, author_id, created_at) VALUES (?, ?, ?, ?)',
        (post_ids[0], '我们农场可以供货，稍后私信您具体报价。', demo_id, now_iso()),
    )
    db.commit()
