"""错误日志模块：全局异常捕获 + 查询/导出接口（/admin/api/__boom__ 为 conftest 注册的必抛错测试路由）"""
import json


class TestErrorLogCapture:
    def test_unhandled_exception_persisted(self, app, client, admin_headers):
        app.config['PROPAGATE_EXCEPTIONS'] = False

        res = client.get('/admin/api/__boom__?x=1', headers=admin_headers)
        assert res.status_code == 500
        assert res.get_json()['detail'] == '服务器内部错误'

        logs = client.get('/admin/api/logs/errors', headers=admin_headers).get_json()
        assert logs['total'] == 1
        item = logs['items'][0]
        assert 'boom for test' in item['message']
        assert 'RuntimeError' in item['message']
        assert 'Traceback' in item['stack']
        assert item['path'] == '/admin/api/__boom__'
        assert item['method'] == 'GET'
        params = json.loads(item['params'])
        assert params['query'] == {'x': '1'}
        ctx = json.loads(item['user_context'])
        assert ctx['type'] == 'admin' and ctx['username'] == 'admin'

    def test_sensitive_params_masked(self, app, client):
        app.config['PROPAGATE_EXCEPTIONS'] = False
        # POST 带密码字段触发异常，验证脱敏
        res = client.post('/admin/api/__boom__', json={'password': 'secret123', 'note': 'hi'})
        assert res.status_code == 500

        # 用管理员身份查询
        login = client.post('/admin/api/auth/login', json={'username': 'admin', 'password': '123456'})
        headers = {'Authorization': f"Bearer {login.get_json()['token']}"}
        logs = client.get('/admin/api/logs/errors', headers=headers).get_json()
        body = json.loads(logs['items'][0]['params'])['body']
        assert body['password'] == '******'
        assert body['note'] == 'hi'

    def test_query_filter_and_export(self, app, client, admin_headers):
        app.config['PROPAGATE_EXCEPTIONS'] = False
        client.get('/admin/api/__boom__?x=1', headers=admin_headers)
        client.get('/admin/api/__boom__?x=2', headers=admin_headers)

        by_path = client.get('/admin/api/logs/errors?path=__boom__', headers=admin_headers).get_json()
        assert by_path['total'] == 2

        by_keyword = client.get('/admin/api/logs/errors?keyword=RuntimeError', headers=admin_headers).get_json()
        assert by_keyword['total'] == 2

        res = client.get('/admin/api/logs/errors/export', headers=admin_headers)
        assert res.status_code == 200 and res.mimetype == 'text/csv'
        text = res.get_data(as_text=True)
        assert '错误堆栈' in text and '触发接口' in text

    def test_404_not_logged_as_error(self, app, client, admin_headers):
        app.config['PROPAGATE_EXCEPTIONS'] = False
        client.get('/admin/api/nonexistent-path', headers=admin_headers)
        logs = client.get('/admin/api/logs/errors', headers=admin_headers).get_json()
        assert logs['total'] == 0
