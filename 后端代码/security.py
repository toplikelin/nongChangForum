"""JWT 生成/校验与登录态装饰器"""
import functools
from datetime import datetime, timezone

import jwt
from flask import current_app, g, request

from database import get_db
from utils import error


def generate_token(user) -> str:
    """根据用户记录（sqlite3.Row）生成 JWT"""
    now = datetime.now(timezone.utc)
    payload = {
        'sub': str(user['id']),
        'username': user['username'],
        'role': user['role'],
        'iat': now,
        'exp': now + current_app.config['JWT_EXPIRATION'],
    }
    return jwt.encode(
        payload,
        current_app.config['SECRET_KEY'],
        algorithm=current_app.config['JWT_ALGORITHM'],
    )


def _decode_token(token: str) -> dict:
    return jwt.decode(
        token,
        current_app.config['SECRET_KEY'],
        algorithms=[current_app.config['JWT_ALGORITHM']],
    )


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer' or not parts[1]:
            return error('未登录或登录已失效', 401)

        try:
            payload = _decode_token(parts[1])
        except jwt.ExpiredSignatureError:
            return error('登录已过期，请重新登录', 401)
        except jwt.InvalidTokenError:
            return error('无效的登录凭证', 401)

        try:
            user_id = int(payload.get('sub'))
        except (TypeError, ValueError):
            return error('无效的登录凭证', 401)

        user = get_db().execute(
            'SELECT * FROM users WHERE id = ?',
            (user_id,),
        ).fetchone()
        if user is None:
            return error('用户不存在', 401)

        g.current_user = user
        return view(*args, **kwargs)

    return wrapped
