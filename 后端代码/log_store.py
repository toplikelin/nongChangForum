"""操作日志、错误日志的写入与清理，以及统计用的内存 TTL 缓存"""
import json
import threading
import time
import traceback
from datetime import datetime, timedelta

import jwt
from flask import current_app, g, request

from database import get_db
from utils import now_iso

# 操作类型 -> 中文名（审计日志需展示中文操作名）
ACTION_NAMES = {
    'login': '后台登录',
    'user_status': '修改用户状态',
    'user_role': '修改用户角色',
    'post_delete': '删除帖子',
    'reply_delete': '删除回复',
    'export': '数据导出',
    'cleanup': '日志清理',
}

# 请求参数中的敏感字段，写日志前脱敏
SENSITIVE_KEYS = {'password', 'token', 'authorization', 'secret'}

# ---------------- 操作日志 ----------------


def log_operation(action, content, target_type=None, target_id=None,
                  result='success', operator=None):
    """记录一条管理员操作日志。任何失败都不影响主流程。"""
    try:
        if operator is None:
            operator = getattr(g, 'admin', None) or 'unknown'
        db = get_db()
        db.execute(
            """
            INSERT INTO operation_logs
                (operator, action, action_name, target_type, target_id, content, result, ip, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                operator,
                action,
                ACTION_NAMES.get(action, action),
                target_type,
                None if target_id is None else str(target_id),
                content,
                result,
                request.headers.get('X-Forwarded-For', request.remote_addr or ''),
                now_iso(),
            ),
        )
        db.commit()
    except Exception:  # noqa: BLE001 - 日志失败不阻断业务
        pass


# ---------------- 错误日志 ----------------


def _sanitize(value):
    """递归脱敏请求参数"""
    if isinstance(value, dict):
        return {
            k: ('******' if k.lower() in SENSITIVE_KEYS else _sanitize(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_sanitize(v) for v in value[:20]]
    return value


def _extract_user_context():
    """从 Authorization 头解析用户上下文（管理员或普通用户），失败返回 None"""
    auth_header = request.headers.get('Authorization', '')
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None
    try:
        payload = jwt.decode(
            parts[1],
            current_app.config['SECRET_KEY'],
            algorithms=[current_app.config['JWT_ALGORITHM']],
        )
    except jwt.InvalidTokenError:
        return None
    if payload.get('is_admin'):
        return {'type': 'admin', 'username': payload.get('sub')}
    return {
        'type': 'user',
        'id': payload.get('sub'),
        'username': payload.get('username'),
        'role': payload.get('role'),
    }


def log_error(exc):
    """捕获并持久化未处理异常。任何失败都不影响错误响应本身。"""
    try:
        params = {'query': _sanitize(request.args.to_dict())}
        body = request.get_json(silent=True)
        if body is not None:
            params['body'] = _sanitize(body)
        db = get_db()
        db.execute(
            """
            INSERT INTO error_logs (message, stack, path, method, params, user_context, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f'{type(exc).__name__}: {exc}',
                traceback.format_exc(),
                request.path,
                request.method,
                json.dumps(params, ensure_ascii=False),
                json.dumps(_extract_user_context(), ensure_ascii=False),
                now_iso(),
            ),
        )
        db.commit()
    except Exception:  # noqa: BLE001 - 日志失败不阻断错误响应
        pass


# ---------------- 过期清理 ----------------


def cleanup_expired_logs():
    """删除超过保留天数的日志，返回 (操作日志删除数, 错误日志删除数)"""
    op_days = current_app.config['OPERATION_LOG_RETENTION_DAYS']
    err_days = current_app.config['ERROR_LOG_RETENTION_DAYS']
    op_cutoff = (datetime.now() - timedelta(days=op_days)).isoformat(timespec='seconds')
    err_cutoff = (datetime.now() - timedelta(days=err_days)).isoformat(timespec='seconds')
    db = get_db()
    cur1 = db.execute('DELETE FROM operation_logs WHERE created_at < ?', (op_cutoff,))
    cur2 = db.execute('DELETE FROM error_logs WHERE created_at < ?', (err_cutoff,))
    db.commit()
    return cur1.rowcount, cur2.rowcount


# ---------------- 统计 TTL 缓存 ----------------


class StatsCache:
    """简单的进程内 TTL 缓存，降低统计聚合查询对主库的压力"""

    def __init__(self):
        self._store = {}
        self._lock = threading.Lock()

    def get_or_set(self, key, ttl, producer):
        now = time.time()
        with self._lock:
            hit = self._store.get(key)
        if hit and now - hit[0] < ttl:
            return hit[1], True
        data = producer()
        with self._lock:
            self._store[key] = (now, data)
            # 惰性清理过期项，避免无限膨胀
            expired = [k for k, (ts, _) in self._store.items() if now - ts >= ttl]
            for k in expired:
                self._store.pop(k, None)
        return data, False

    def clear(self):
        with self._lock:
            self._store.clear()


stats_cache = StatsCache()
