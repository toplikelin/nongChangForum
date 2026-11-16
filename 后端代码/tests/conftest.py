"""pytest 共享夹具：独立临时数据库 + 测试客户端 + 管理员令牌"""
import os
import sys
import tempfile

import pytest

# 在导入 app 之前指向独立临时数据库，避免污染业务库
_TEST_DB = os.path.join(tempfile.mkdtemp(prefix='forum_test_'), 'test.db')
os.environ['DATABASE'] = _TEST_DB

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app  # noqa: E402
from database import get_db  # noqa: E402
from log_store import stats_cache  # noqa: E402


def _boom():
    """测试专用路由：必然抛出未处理异常，用于验证错误日志捕获"""
    raise RuntimeError('boom for test')


@pytest.fixture()
def app():
    app = create_app()
    app.config['TESTING'] = True
    # 必须在首次请求前注册测试路由
    app.add_url_rule('/admin/api/__boom__', 'boom_for_test', _boom, methods=['GET', 'POST'])
    yield app
    # 每个用例结束后清空日志表与统计缓存，保证用例间隔离
    with app.app_context():
        db = get_db()
        db.execute('DELETE FROM operation_logs')
        db.execute('DELETE FROM error_logs')
        db.commit()
    stats_cache.clear()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def admin_headers(client):
    res = client.post('/admin/api/auth/login', json={'username': 'admin', 'password': '123456'})
    token = res.get_json()['token']
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture()
def user_headers(client):
    res = client.post('/api/auth/login', json={'username': 'demo', 'password': '123456'})
    token = res.get_json()['token']
    return {'Authorization': f'Bearer {token}'}
