"""全局配置"""
import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # JWT 签名密钥（生产环境请通过环境变量覆盖）
    SECRET_KEY = os.environ.get('SECRET_KEY', 'forum-miniapp-secret-key-change-me')

    # SQLite 数据库文件
    DATABASE = os.environ.get('DATABASE', os.path.join(BASE_DIR, 'forum.db'))

    # JWT 有效期
    JWT_EXPIRATION = timedelta(days=7)
    JWT_ALGORITHM = 'HS256'
    TOKEN_TYPE = 'Bearer'

    # 分页
    DEFAULT_PAGE_SIZE = 10
    MAX_PAGE_SIZE = 50

    # 日志保留天数（过期自动清理）
    OPERATION_LOG_RETENTION_DAYS = int(os.environ.get('OPERATION_LOG_RETENTION_DAYS', 90))
    ERROR_LOG_RETENTION_DAYS = int(os.environ.get('ERROR_LOG_RETENTION_DAYS', 90))

    # 统计数据缓存秒数（避免聚合查询频繁冲击主库）
    STATS_CACHE_TTL_SECONDS = int(os.environ.get('STATS_CACHE_TTL_SECONDS', 60))

    # 日志导出单批次最大行数
    LOG_EXPORT_MAX_ROWS = int(os.environ.get('LOG_EXPORT_MAX_ROWS', 5000))

    # 微信小程序登录（不配置时使用 dev mock 模式）
    WECHAT_APPID = os.environ.get('WECHAT_APPID', '')
    WECHAT_SECRET = os.environ.get('WECHAT_SECRET', '')
    # 是否开启 mock（开发/测试环境设为 True），mock 下 code 前缀决定生成的 openid
    WECHAT_DEV_MOCK = os.environ.get('WECHAT_DEV_MOCK', '1') == '1'
