"""通用工具函数"""
from datetime import datetime

from flask import jsonify


def now_iso() -> str:
    """当前时间的 ISO 字符串（精确到秒），与前端解析方式兼容"""
    return datetime.now().isoformat(timespec='seconds')


def is_vip(role: str) -> bool:
    """非普通用户即视为 VIP（vip1/vip2/vip3）"""
    return bool(role) and role != 'user'


def error(message: str, status: int = 400):
    """统一错误响应，前端读取 detail 字段"""
    response = jsonify({'detail': message})
    response.status_code = status
    return response
