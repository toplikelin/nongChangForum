"""Flask 应用入口"""
from flask import Flask
from werkzeug.exceptions import HTTPException

from config import Config
from database import close_db, init_db
from log_store import cleanup_expired_logs, log_error
from routers import auth as auth_router
from routers import posts as posts_router
from routers import admin as admin_router
from routers import logs as logs_router
from routers import stats as stats_router
from utils import error


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    # 注册路由
    app.register_blueprint(auth_router.bp)
    app.register_blueprint(posts_router.bp)
    app.register_blueprint(admin_router.bp)
    app.register_blueprint(logs_router.bp)
    app.register_blueprint(stats_router.bp)

    # 全局异常捕获：未处理异常落库到错误日志，HTTP 异常原样返回
    @app.errorhandler(Exception)
    def handle_exception(exc):
        if isinstance(exc, HTTPException):
            if exc.code is not None and exc.code >= 500:
                log_error(exc)
            return exc
        log_error(exc)
        return error('服务器内部错误', 500)

    # 请求结束释放数据库连接
    app.teardown_appcontext(close_db)

    # 跨域支持（小程序本身不受限，这里方便 H5/浏览器调试）
    @app.after_request
    def add_cors_headers(response):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
        return response

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>', methods=['OPTIONS'])
    def handle_options(path):
        return '', 204

    # 初始化数据库（建表 + 演示数据）并清理过期日志
    with app.app_context():
        init_db()
        cleanup_expired_logs()

    return app


app = create_app()

if __name__ == '__main__':
    # 端口与前端 config 中的 API_BASE_URL 保持一致
    app.run(host='0.0.0.0', port=8000, debug=True)
