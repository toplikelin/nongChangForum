"""操作日志模块：单元测试（写入逻辑）+ 集成测试（接口行为）"""


class TestLogOperationUnit:
    """log_operation 写入逻辑"""

    def test_write_row_with_chinese_action_name(self, app):
        from log_store import log_operation
        with app.test_request_context('/admin/api/users'):
            log_operation('post_delete', '删除帖子「测试」', target_type='帖子', target_id=7,
                          operator='admin')
        with app.app_context():
            from database import get_db
            row = get_db().execute('SELECT * FROM operation_logs').fetchone()
        assert row['operator'] == 'admin'
        assert row['action'] == 'post_delete'
        assert row['action_name'] == '删除帖子'
        assert row['target_type'] == '帖子'
        assert row['target_id'] == '7'
        assert row['result'] == 'success'

    def test_write_fail_result(self, app):
        from log_store import log_operation
        with app.test_request_context('/admin/api/users'):
            log_operation('user_status', '目标不存在', result='fail', operator='admin')
        with app.app_context():
            from database import get_db
            row = get_db().execute('SELECT * FROM operation_logs').fetchone()
        assert row['result'] == 'fail'


class TestOperationLogIntegration:
    """管理员操作自动落日志 + 查询/筛选/导出接口"""

    def test_login_success_and_failure_logged(self, client):
        client.post('/admin/api/auth/login', json={'username': 'admin', 'password': '123456'})
        client.post('/admin/api/auth/login', json={'username': 'admin', 'password': 'wrong'})

        res = client.post('/admin/api/auth/login', json={'username': 'admin', 'password': '123456'})
        headers = {'Authorization': f"Bearer {res.get_json()['token']}"}
        logs = client.get('/admin/api/logs/operations?action=login', headers=headers).get_json()

        results = sorted(item['result'] for item in logs['items'])
        assert 'success' in results and 'fail' in results
        assert all(item['action_name'] == '后台登录' for item in logs['items'])

    def test_admin_mutation_creates_log(self, client, admin_headers):
        client.patch('/admin/api/users/1/status', json={'status': 'disabled'}, headers=admin_headers)
        client.patch('/admin/api/users/1/role', json={'role': 'vip2'}, headers=admin_headers)
        client.delete('/admin/api/posts/1', headers=admin_headers)
        client.delete('/admin/api/posts/99999', headers=admin_headers)  # 失败操作

        logs = client.get('/admin/api/logs/operations?size=50', headers=admin_headers).get_json()
        actions = {item['action']: item['result'] for item in logs['items']}
        assert actions['user_status'] == 'success'
        assert actions['user_role'] == 'success'
        assert 'post_delete' in actions
        fails = [i for i in logs['items'] if i['action'] == 'post_delete' and i['result'] == 'fail']
        assert len(fails) == 1  # 不存在的帖子删除尝试被记录为失败

    def test_pagination_and_filters(self, client, admin_headers):
        for uid in (1, 2):
            client.patch(f'/admin/api/users/{uid}/role', json={'role': 'vip1'}, headers=admin_headers)

        page1 = client.get('/admin/api/logs/operations?page=1&size=2', headers=admin_headers).get_json()
        assert page1['page'] == 1 and len(page1['items']) == 2
        assert page1['total'] >= 3

        by_action = client.get('/admin/api/logs/operations?action=user_role', headers=admin_headers).get_json()
        assert all(i['action'] == 'user_role' for i in by_action['items'])

        by_operator = client.get(
            '/admin/api/logs/operations?operator=nobody', headers=admin_headers).get_json()
        assert by_operator['total'] == 0

        by_keyword = client.get('/admin/api/logs/operations?keyword=vip1', headers=admin_headers).get_json()
        assert by_keyword['total'] >= 2

        bad_range = client.get('/admin/api/logs/operations?start=2026-13-99', headers=admin_headers)
        assert bad_range.status_code == 400

    def test_export_csv(self, client, admin_headers):
        client.patch('/admin/api/users/1/status', json={'status': 'active'}, headers=admin_headers)
        res = client.get('/admin/api/logs/operations/export', headers=admin_headers)
        assert res.status_code == 200
        assert res.mimetype == 'text/csv'
        text = res.get_data(as_text=True)
        assert '操作人' in text and '操作内容' in text
        assert 'admin' in text
        # 导出行为本身也被记录
        logs = client.get('/admin/api/logs/operations?action=export', headers=admin_headers).get_json()
        assert logs['total'] >= 1

    def test_unauthorized(self, client):
        assert client.get('/admin/api/logs/operations').status_code == 401
