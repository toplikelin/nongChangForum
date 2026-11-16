"""后台统计分析接口：核心指标、发帖/回复趋势、活跃用户排行、活跃度分布（带 TTL 缓存）"""
import csv
import io
import json
from datetime import date, datetime, timedelta

from flask import Blueprint, current_app, request, Response

from database import get_db
from log_store import log_operation, stats_cache
from routers.admin import admin_required
from utils import error, now_iso

bp = Blueprint('admin_stats', __name__, url_prefix='/admin/api')

VALID_DIMS = ('day', 'week', 'month')

# 活跃度分布分桶（按时间范围内发帖+回复总量）
ACTIVITY_BUCKETS = [
    ('0', 0, 0),
    ('1-5', 1, 5),
    ('6-20', 6, 20),
    ('21-50', 21, 50),
    ('50以上', 51, None),
]


# ---------------- 通用工具 ----------------


def _parse_range():
    """解析 start/end（YYYY-MM-DD）。未提供时返回 (None, None)，非法时报错"""
    start = (request.args.get('start') or '').strip()
    end = (request.args.get('end') or '').strip()
    try:
        start_date = datetime.strptime(start, '%Y-%m-%d').date() if start else None
        end_date = datetime.strptime(end, '%Y-%m-%d').date() if end else None
    except ValueError:
        return None, None, False
    if start_date and end_date and start_date > end_date:
        return None, None, False
    return start_date, end_date, True


def _range_sql(column, start_date, end_date):
    """生成时间范围 WHERE 片段"""
    where = []
    params = []
    if start_date:
        where.append(f'{column} >= ?')
        params.append(f'{start_date.isoformat()}T00:00:00')
    if end_date:
        where.append(f'{column} <= ?')
        params.append(f'{end_date.isoformat()}T23:59:59')
    return (' WHERE ' + ' AND '.join(where)) if where else '', params


def _produce(endpoint, producer):
    """执行聚合查询并走缓存"""
    ttl = current_app.config['STATS_CACHE_TTL_SECONDS']
    key = endpoint + ':' + json.dumps(request.args.to_dict(), ensure_ascii=False, sort_keys=True)
    return stats_cache.get_or_set(key, ttl, producer)


# ---------------- 核心指标 ----------------


def _overview_data(start_date, end_date):
    db = get_db()
    post_where, post_params = _range_sql('created_at', start_date, end_date)
    reply_where, reply_params = _range_sql('created_at', start_date, end_date)

    total_posts = db.execute('SELECT COUNT(*) FROM posts' + post_where, post_params).fetchone()[0]
    total_replies = db.execute('SELECT COUNT(*) FROM replies' + reply_where, reply_params).fetchone()[0]
    total_users = db.execute('SELECT COUNT(*) FROM users').fetchone()[0]

    # 活跃用户：范围内发过帖或回复过的去重用户
    active_where, active_params = _range_sql('created_at', start_date, end_date)
    active_users = db.execute(
        f"""
        SELECT COUNT(DISTINCT author_id) FROM (
            SELECT author_id, created_at FROM posts
            UNION ALL
            SELECT author_id, created_at FROM replies
        ) t{active_where}
        """,
        active_params,
    ).fetchone()[0]

    today = date.today().isoformat() + 'T00:00:00'
    today_posts = db.execute('SELECT COUNT(*) FROM posts WHERE created_at >= ?', (today,)).fetchone()[0]
    today_replies = db.execute('SELECT COUNT(*) FROM replies WHERE created_at >= ?', (today,)).fetchone()[0]

    return {
        'total_posts': total_posts,
        'total_replies': total_replies,
        'total_users': total_users,
        'active_users': active_users,
        'today_posts': today_posts,
        'today_replies': today_replies,
    }


@bp.get('/stats/overview')
@admin_required
def stats_overview():
    start_date, end_date, ok = _parse_range()
    if not ok:
        return error('时间参数不合法')
    data, cached_hit = _produce('overview', lambda: _overview_data(start_date, end_date))
    return {'data': data, 'cached': cached_hit}


# ---------------- 发帖/回复趋势 ----------------


def _bucket_expr(dim):
    if dim == 'day':
        return "substr(created_at, 1, 10)"
    if dim == 'week':
        # ISO 周标签：年-W周数
        return "strftime('%Y-W%W', created_at)"
    return "substr(created_at, 1, 7)"


def _fill_labels(dim, start_date, end_date, rows):
    """补齐时间桶，保证趋势连续。rows: {label: {'posts': n, 'replies': n}}"""
    if dim == 'day':
        start_d = start_date or (date.today() - timedelta(days=13))
        end_d = end_date or date.today()
        if (end_d - start_d).days > 92:
            start_d = end_d - timedelta(days=92)
        labels = []
        d = start_d
        while d <= end_d:
            labels.append(d.isoformat())
            d += timedelta(days=1)
    elif dim == 'week':
        start_d = start_date or (date.today() - timedelta(weeks=7))
        end_d = end_date or date.today()
        if (end_d - start_d).days > 370:
            start_d = end_d - timedelta(days=370)
        labels = []
        seen = set()
        d = start_d
        while d <= end_d:
            label = d.strftime('%Y-W%W')
            if label not in seen:
                seen.add(label)
                labels.append(label)
            d += timedelta(days=1)
    else:  # month
        start_d = (start_date or (date.today() - timedelta(days=180))).replace(day=1)
        end_d = (end_date or date.today()).replace(day=1)
        if (end_d.year - start_d.year) * 12 + (end_d.month - start_d.month) > 24:
            start_d = (end_d - timedelta(days=730)).replace(day=1)
        labels = []
        y, m = start_d.year, start_d.month
        while (y, m) <= (end_d.year, end_d.month):
            labels.append(f'{y:04d}-{m:02d}')
            m += 1
            if m > 12:
                y, m = y + 1, 1
    return [
        {'label': label, 'posts': rows.get(label, {}).get('posts', 0), 'replies': rows.get(label, {}).get('replies', 0)}
        for label in labels
    ]


def _trend_data(dim, start_date, end_date):
    db = get_db()
    expr = _bucket_expr(dim)
    post_where, post_params = _range_sql('created_at', start_date, end_date)
    reply_where, reply_params = _range_sql('created_at', start_date, end_date)

    post_rows = db.execute(
        f'SELECT {expr} AS bucket, COUNT(*) AS c FROM posts{post_where} GROUP BY bucket',
        post_params,
    ).fetchall()
    reply_rows = db.execute(
        f'SELECT {expr} AS bucket, COUNT(*) AS c FROM replies{reply_where} GROUP BY bucket',
        reply_params,
    ).fetchall()

    merged = {}
    for r in post_rows:
        merged.setdefault(r['bucket'], {})['posts'] = r['c']
    for r in reply_rows:
        merged.setdefault(r['bucket'], {})['replies'] = r['c']

    # 无时间范围时以数据覆盖范围为准
    eff_start, eff_end = start_date, end_date
    if eff_start is None and merged:
        first = min(merged.keys())
        try:
            if dim == 'day':
                eff_start = datetime.strptime(first, '%Y-%m-%d').date()
            elif dim == 'month':
                eff_start = datetime.strptime(first, '%Y-%m').date()
            else:
                eff_start = datetime.strptime(first + '-1', '%Y-W%W-%w').date()
        except ValueError:
            eff_start = None
    return {'dim': dim, 'items': _fill_labels(dim, eff_start, eff_end, merged)}


@bp.get('/stats/trend')
@admin_required
def stats_trend():
    dim = request.args.get('dim', 'day')
    if dim not in VALID_DIMS:
        return error('无效的统计维度')
    start_date, end_date, ok = _parse_range()
    if not ok:
        return error('时间参数不合法')
    data, cached_hit = _produce('trend', lambda: _trend_data(dim, start_date, end_date))
    return {'data': data, 'cached': cached_hit}


# ---------------- 活跃用户排行 ----------------


def _active_users_data(start_date, end_date, limit):
    db = get_db()
    post_cond, post_params = _range_sql('p.created_at', start_date, end_date)
    reply_cond, reply_params = _range_sql('r.created_at', start_date, end_date)
    # 子查询无法直接复用 WHERE 前缀，拼接为 AND 条件
    post_and = post_cond.replace(' WHERE ', ' AND ') if post_cond else ''
    reply_and = reply_cond.replace(' WHERE ', ' AND ') if reply_cond else ''

    rows = db.execute(
        f"""
        SELECT u.id, u.username, u.role,
               (SELECT COUNT(*) FROM posts p WHERE p.author_id = u.id{post_and})   AS post_count,
               (SELECT COUNT(*) FROM replies r WHERE r.author_id = u.id{reply_and}) AS reply_count
          FROM users u
         ORDER BY (post_count + reply_count) DESC, u.id ASC
         LIMIT ?
        """,
        post_params + reply_params + [limit],
    ).fetchall()
    items = [
        {
            'id': r['id'],
            'username': r['username'],
            'role': r['role'],
            'post_count': r['post_count'],
            'reply_count': r['reply_count'],
            'total': r['post_count'] + r['reply_count'],
        }
        for r in rows
    ]
    return {'items': items}


@bp.get('/stats/active-users')
@admin_required
def stats_active_users():
    start_date, end_date, ok = _parse_range()
    if not ok:
        return error('时间参数不合法')
    try:
        limit = max(1, min(int(request.args.get('limit', 10)), 50))
    except ValueError:
        return error('limit 参数不合法')
    data, cached_hit = _produce('active-users', lambda: _active_users_data(start_date, end_date, limit))
    return {'data': data, 'cached': cached_hit}


# ---------------- 用户活跃度分布 ----------------


def _activity_distribution_data(start_date, end_date):
    db = get_db()
    post_cond, post_params = _range_sql('p.created_at', start_date, end_date)
    reply_cond, reply_params = _range_sql('r.created_at', start_date, end_date)
    post_and = post_cond.replace(' WHERE ', ' AND ') if post_cond else ''
    reply_and = reply_cond.replace(' WHERE ', ' AND ') if reply_cond else ''

    rows = db.execute(
        f"""
        SELECT (SELECT COUNT(*) FROM posts p WHERE p.author_id = u.id{post_and}) +
               (SELECT COUNT(*) FROM replies r WHERE r.author_id = u.id{reply_and}) AS total
          FROM users u
        """,
        post_params + reply_params,
    ).fetchall()

    counts = {label: 0 for label, _, _ in ACTIVITY_BUCKETS}
    for r in rows:
        total = r['total']
        for label, low, high in ACTIVITY_BUCKETS:
            if total >= low and (high is None or total <= high):
                counts[label] += 1
                break
    return {'items': [{'range': label, 'count': counts[label]} for label, _, _ in ACTIVITY_BUCKETS]}


@bp.get('/stats/activity-distribution')
@admin_required
def stats_activity_distribution():
    start_date, end_date, ok = _parse_range()
    if not ok:
        return error('时间参数不合法')
    data, cached_hit = _produce('activity-distribution',
                                lambda: _activity_distribution_data(start_date, end_date))
    return {'data': data, 'cached': cached_hit}


# ---------------- 统计导出 ----------------


@bp.get('/stats/export')
@admin_required
def stats_export():
    dim = request.args.get('dim', 'day')
    if dim not in VALID_DIMS:
        return error('无效的统计维度')
    start_date, end_date, ok = _parse_range()
    if not ok:
        return error('时间参数不合法')

    overview = _overview_data(start_date, end_date)
    trend = _trend_data(dim, start_date, end_date)

    buf = io.StringIO()
    buf.write('﻿')
    writer = csv.writer(buf)
    writer.writerow(['统计时间', now_iso()])
    writer.writerow(['时间范围', f'{start_date or "全部"} ~ {end_date or "全部"}'])
    writer.writerow([])
    writer.writerow(['核心指标'])
    writer.writerow(['发帖总量', overview['total_posts']])
    writer.writerow(['回复总量', overview['total_replies']])
    writer.writerow(['用户总数', overview['total_users']])
    writer.writerow(['活跃用户', overview['active_users']])
    writer.writerow(['今日发帖', overview['today_posts']])
    writer.writerow(['今日回复', overview['today_replies']])
    writer.writerow([])
    dim_names = {'day': '日', 'week': '周', 'month': '月'}
    writer.writerow([f'发帖/回复趋势（按{dim_names[dim]}）'])
    writer.writerow(['时间', '发帖数', '回复数'])
    for item in trend['items']:
        writer.writerow([item['label'], item['posts'], item['replies']])

    log_operation('export', f'导出统计数据（维度：{dim_names[dim]}）', target_type='统计')
    filename = f"stats_{dim}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        buf.getvalue(),
        mimetype='text/csv; charset=utf-8',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )
