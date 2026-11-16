"""后台日志管理接口：操作日志 / 错误日志的分页查询、关键词检索、CSV 导出与过期清理"""
import csv
import io
from datetime import datetime

from flask import Blueprint, current_app, request, Response

from database import get_db
from log_store import ACTION_NAMES, cleanup_expired_logs, log_operation
from routers.admin import admin_required
from utils import error

bp = Blueprint('admin_logs', __name__, url_prefix='/admin/api')


# ---------------- 通用工具 ----------------


def _page_args():
    """解析分页参数，非法值报错"""
    try:
        page = max(1, int(request.args.get('page', 1)))
        size = int(request.args.get('size', current_app.config['DEFAULT_PAGE_SIZE']))
    except ValueError:
        return None, None
    size = max(1, min(size, current_app.config['MAX_PAGE_SIZE']))
    return page, size


def _range_args():
    """解析时间范围筛选（YYYY-MM-DD），返回 (start_iso, end_iso)"""
    start = (request.args.get('start') or '').strip()
    end = (request.args.get('end') or '').strip()
    try:
        start_iso = f'{start}T00:00:00' if start else None
        end_iso = f'{end}T23:59:59' if end else None
        if start:
            datetime.strptime(start, '%Y-%m-%d')
        if end:
            datetime.strptime(end, '%Y-%m-%d')
    except ValueError:
        return None, None, False
    return start_iso, end_iso, True


def _csv_response(filename, header, rows):
    """生成带 BOM 的 CSV 下载响应（Excel 兼容中文）"""
    buf = io.StringIO()
    buf.write('﻿')  # UTF-8 BOM
    writer = csv.writer(buf)
    writer.writerow(header)
    writer.writerows(rows)
    return Response(
        buf.getvalue(),
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


def _export_name(prefix):
    return f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"


# ---------------- 操作日志 ----------------

OP_LOG_COLUMNS = 'id, operator, action, action_name, target_type, target_id, content, result, ip, created_at'


def _build_op_where():
    """组装操作日志筛选条件"""
    where = []
    params = []
    operator = (request.args.get('operator') or '').strip()
    action = (request.args.get('action') or '').strip()
    keyword = (request.args.get('keyword') or '').strip()
    start_iso, end_iso, ok = _range_args()
    if not ok:
        return None, None
    if operator:
        where.append('operator LIKE ?')
        params.append(f'%{operator}%')
    if action:
        if action not in ACTION_NAMES:
            return None, None
        where.append('action = ?')
        params.append(action)
    if keyword:
        where.append('(content LIKE ? OR target_id LIKE ? OR ip LIKE ?)')
        params.extend([f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'])
    if start_iso:
        where.append('created_at >= ?')
        params.append(start_iso)
    if end_iso:
        where.append('created_at <= ?')
        params.append(end_iso)
    where_sql = (' WHERE ' + ' AND '.join(where)) if where else ''
    return where_sql, params


@bp.get('/logs/operations')
@admin_required
def list_operation_logs():
    page, size = _page_args()
    if page is None:
        return error('分页参数不合法')
    where_sql, params = _build_op_where()
    if where_sql is None:
        return error('筛选参数不合法')

    db = get_db()
    total = db.execute('SELECT COUNT(*) FROM operation_logs' + where_sql, params).fetchone()[0]
    rows = db.execute(
        f'SELECT {OP_LOG_COLUMNS} FROM operation_logs{where_sql}'
        ' ORDER BY id DESC LIMIT ? OFFSET ?',
        params + [size, (page - 1) * size],
    ).fetchall()
    return {
        'items': [dict(r) for r in rows],
        'total': total,
        'page': page,
        'size': size,
        'actions': [{'key': k, 'name': v} for k, v in ACTION_NAMES.items()],
    }


@bp.get('/logs/operations/export')
@admin_required
def export_operation_logs():
    where_sql, params = _build_op_where()
    if where_sql is None:
        return error('筛选参数不合法')

    db = get_db()
    rows = db.execute(
        f'SELECT {OP_LOG_COLUMNS} FROM operation_logs{where_sql} ORDER BY id DESC LIMIT ?',
        params + [current_app.config['LOG_EXPORT_MAX_ROWS']],
    ).fetchall()

    log_operation('export', f'导出操作日志 {len(rows)} 条', target_type='日志')
    return _csv_response(
        _export_name('operation_logs'),
        ['ID', '操作人', '操作类型', '操作名称', '目标类型', '目标ID', '操作内容', '操作结果', 'IP', '操作时间'],
        [
            [
                r['id'], r['operator'], r['action'], r['action_name'],
                r['target_type'] or '', r['target_id'] or '', r['content'] or '',
                '成功' if r['result'] == 'success' else '失败',
                r['ip'] or '', r['created_at'],
            ]
            for r in rows
        ],
    )


# ---------------- 错误日志 ----------------

ERR_LOG_COLUMNS = 'id, message, stack, path, method, params, user_context, created_at'


def _build_err_where():
    where = []
    params = []
    keyword = (request.args.get('keyword') or '').strip()
    path = (request.args.get('path') or '').strip()
    start_iso, end_iso, ok = _range_args()
    if not ok:
        return None, None
    if keyword:
        where.append('(message LIKE ? OR stack LIKE ?)')
        params.extend([f'%{keyword}%', f'%{keyword}%'])
    if path:
        where.append('path LIKE ?')
        params.append(f'%{path}%')
    if start_iso:
        where.append('created_at >= ?')
        params.append(start_iso)
    if end_iso:
        where.append('created_at <= ?')
        params.append(end_iso)
    where_sql = (' WHERE ' + ' AND '.join(where)) if where else ''
    return where_sql, params


@bp.get('/logs/errors')
@admin_required
def list_error_logs():
    page, size = _page_args()
    if page is None:
        return error('分页参数不合法')
    where_sql, params = _build_err_where()
    if where_sql is None:
        return error('筛选参数不合法')

    db = get_db()
    total = db.execute('SELECT COUNT(*) FROM error_logs' + where_sql, params).fetchone()[0]
    rows = db.execute(
        f'SELECT {ERR_LOG_COLUMNS} FROM error_logs{where_sql}'
        ' ORDER BY id DESC LIMIT ? OFFSET ?',
        params + [size, (page - 1) * size],
    ).fetchall()
    return {
        'items': [dict(r) for r in rows],
        'total': total,
        'page': page,
        'size': size,
    }


@bp.get('/logs/errors/export')
@admin_required
def export_error_logs():
    where_sql, params = _build_err_where()
    if where_sql is None:
        return error('筛选参数不合法')

    db = get_db()
    rows = db.execute(
        f'SELECT {ERR_LOG_COLUMNS} FROM error_logs{where_sql} ORDER BY id DESC LIMIT ?',
        params + [current_app.config['LOG_EXPORT_MAX_ROWS']],
    ).fetchall()

    log_operation('export', f'导出错误日志 {len(rows)} 条', target_type='日志')
    return _csv_response(
        _export_name('error_logs'),
        ['ID', '错误信息', '错误堆栈', '触发接口', '请求方法', '请求参数', '用户上下文', '报错时间'],
        [
            [
                r['id'], r['message'], r['stack'] or '', r['path'] or '',
                r['method'] or '', r['params'] or '', r['user_context'] or '',
                r['created_at'],
            ]
            for r in rows
        ],
    )


# ---------------- 过期清理 ----------------


@bp.post('/logs/cleanup')
@admin_required
def cleanup_logs():
    op_deleted, err_deleted = cleanup_expired_logs()
    log_operation(
        'cleanup',
        f'清理过期日志：操作日志 {op_deleted} 条，错误日志 {err_deleted} 条',
        target_type='日志',
    )
    return {
        'operation_logs_deleted': op_deleted,
        'error_logs_deleted': err_deleted,
    }
