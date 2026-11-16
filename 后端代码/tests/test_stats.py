"""统计分析模块：指标正确性、趋势分桶、排行、分布、缓存、导出"""
from datetime import datetime, timedelta

import pytest


@pytest.fixture()
def seeded(app):
    """播种可控时间的数据：3 天前 2 帖 1 回复，今天 1 帖"""
    from database import get_db

    def iso(days_ago):
        return (datetime.now() - timedelta(days=days_ago)).isoformat(timespec='seconds')

    with app.app_context():
        db = get_db()
        # 清除演示数据，保证统计确定性
        db.execute('DELETE FROM replies')
        db.execute('DELETE FROM posts')
        db.execute('DELETE FROM users')
        users = [('alice', 'user'), ('bob', 'vip1'), ('carol', 'user')]
        for name, role in users:
            db.execute(
                "INSERT INTO users (username, password_hash, role, created_at) VALUES (?, 'x', ?, ?)",
                (name, role, iso(10)),
            )
        db.commit()
        ids = {r['username']: r['id'] for r in db.execute('SELECT id, username FROM users')}
        # alice: 3 天前 2 帖 + 今天 1 帖（共 3）；bob: 3 天前 1 回复；carol: 无动态
        for _ in range(2):
            db.execute(
                "INSERT INTO posts (zone, title, content, author_id, created_at) VALUES ('free', 't', 'c', ?, ?)",
                (ids['alice'], iso(3)),
            )
        db.execute(
            "INSERT INTO posts (zone, title, content, author_id, created_at) VALUES ('free', 't', 'c', ?, ?)",
            (ids['alice'], iso(0)),
        )
        post_id = db.execute('SELECT id FROM posts LIMIT 1').fetchone()['id']
        db.execute(
            "INSERT INTO replies (post_id, content, author_id, created_at) VALUES (?, 'r', ?, ?)",
            (post_id, ids['bob'], iso(3)),
        )
        db.commit()
    return ids


class TestOverview:
    def test_totals_and_active(self, client, admin_headers, seeded):
        data = client.get('/admin/api/stats/overview', headers=admin_headers).get_json()['data']
        assert data['total_posts'] == 3
        assert data['total_replies'] == 1
        assert data['total_users'] == 3
        assert data['active_users'] == 2
        assert data['today_posts'] == 1
        assert data['today_replies'] == 0

    def test_range_filter(self, client, admin_headers, seeded):
        today = datetime.now().date().isoformat()
        data = client.get(
            f'/admin/api/stats/overview?start={today}&end={today}', headers=admin_headers
        ).get_json()['data']
        assert data['total_posts'] == 1
        assert data['total_replies'] == 0
        assert data['active_users'] == 1

    def test_bad_range_rejected(self, client, admin_headers):
        assert client.get('/admin/api/stats/overview?start=abc', headers=admin_headers).status_code == 400
        assert client.get(
            '/admin/api/stats/overview?start=2026-11-10&end=2026-11-01',
            headers=admin_headers,
        ).status_code == 400


class TestTrend:
    def test_day_dimension_and_gap_fill(self, client, admin_headers, seeded):
        start = (datetime.now() - timedelta(days=3)).date().isoformat()
        end = datetime.now().date().isoformat()
        payload = client.get(
            f'/admin/api/stats/trend?dim=day&start={start}&end={end}', headers=admin_headers
        ).get_json()
        items = payload['data']['items']
        assert len(items) == 4  # 连续 4 天，空缺补齐
        assert items[0]['posts'] == 2 and items[0]['replies'] == 1
        assert items[-1]['posts'] == 1 and items[-1]['replies'] == 0
        assert sum(i['posts'] for i in items) == 3

    def test_week_and_month_dimension(self, client, admin_headers, seeded):
        week = client.get('/admin/api/stats/trend?dim=week', headers=admin_headers).get_json()['data']
        assert all('-W' in i['label'] for i in week['items'])
        assert sum(i['posts'] for i in week['items']) == 3

        month = client.get('/admin/api/stats/trend?dim=month', headers=admin_headers).get_json()['data']
        assert sum(i['replies'] for i in month['items']) == 1

    def test_invalid_dim(self, client, admin_headers):
        assert client.get('/admin/api/stats/trend?dim=year', headers=admin_headers).status_code == 400


class TestActiveUsers:
    def test_ranking_order(self, client, admin_headers, seeded):
        items = client.get('/admin/api/stats/active-users', headers=admin_headers).get_json()['data']['items']
        assert items[0]['username'] == 'alice' and items[0]['total'] == 3
        assert items[0]['post_count'] == 3
        bob = next(i for i in items if i['username'] == 'bob')
        assert bob['reply_count'] == 1


class TestActivityDistribution:
    def test_buckets(self, client, admin_headers, seeded):
        items = client.get(
            '/admin/api/stats/activity-distribution', headers=admin_headers
        ).get_json()['data']['items']
        dist = {i['range']: i['count'] for i in items}
        assert dist['0'] == 1      # carol
        assert dist['1-5'] == 2    # alice(3) bob(1)
        assert sum(dist.values()) == 3


class TestCacheAndExport:
    def test_cache_hit_on_repeat_call(self, client, admin_headers, seeded):
        first = client.get('/admin/api/stats/overview', headers=admin_headers).get_json()
        second = client.get('/admin/api/stats/overview', headers=admin_headers).get_json()
        assert first['cached'] is False
        assert second['cached'] is True
        assert first['data'] == second['data']

    def test_export_csv(self, client, admin_headers, seeded):
        res = client.get('/admin/api/stats/export?dim=day', headers=admin_headers)
        assert res.status_code == 200 and res.mimetype == 'text/csv'
        text = res.get_data(as_text=True)
        assert '发帖总量' in text and '3' in text
        assert '发帖/回复趋势（按日）' in text

    def test_unauthorized(self, client):
        assert client.get('/admin/api/stats/overview').status_code == 401


class TestLogCleanup:
    def test_cleanup_endpoint_and_retention(self, app, client, admin_headers):
        from database import get_db
        old = (datetime.now() - timedelta(days=365)).isoformat(timespec='seconds')
        with app.app_context():
            db = get_db()
            db.execute(
                "INSERT INTO operation_logs (operator, action, action_name, content, result, created_at) "
                "VALUES ('admin', 'login', '后台登录', '旧日志', 'success', ?)",
                (old,),
            )
            db.execute(
                "INSERT INTO error_logs (message, created_at) VALUES ('old error', ?)",
                (old,),
            )
            db.commit()

        res = client.post('/admin/api/logs/cleanup', headers=admin_headers)
        body = res.get_json()
        assert res.status_code == 200
        assert body['operation_logs_deleted'] == 1
        assert body['error_logs_deleted'] == 1
