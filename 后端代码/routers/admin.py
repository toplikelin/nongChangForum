"""后台管理接口：管理员登录、账户管理、发帖管理"""
from flask import Blueprint, current_app, g, request
from werkzeug.security import check_password_hash

from database import get_db
from log_store import log_operation
from security import login_required  # noqa: F401  (保留供复用思路参考)
from serializers import ZONE_KEYS
from utils import error, now_iso
import jwt
from datetime import datetime, timezone

bp = Blueprint('admin', __name__, url_prefix='/admin/api')

# 唯一管理员账号
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = '123456'
VALID_ROLES = ('user', 'vip1', 'vip2', 'vip3')
VALID_STATUS = ('active', 'disabled')


def generate_admin_token() -> str:
    now = datetime.now(timezone.utc)
    payload = {
        'sub': ADMIN_USERNAME,
        'is_admin': True,
        'iat': now,
        'exp': now + current_app.config['JWT_EXPIRATION'],
    }
    return jwt.encode(
        payload,
        current_app.config['SECRET_KEY'],
        algorithm=current_app.config['JWT_ALGORITHM'],
    )


def admin_required(view):
    """校验管理员 JWT（与普通用户 JWT 隔离，要求 is_admin=True）"""
    import functools

    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer' or not parts[1]:
            return error('未登录', 401)
        try:
            payload = jwt.decode(
                parts[1],
                current_app.config['SECRET_KEY'],
                algorithms=[current_app.config['JWT_ALGORITHM']],
            )
        except jwt.ExpiredSignatureError:
            return error('登录已过期，请重新登录', 401)
        except jwt.InvalidTokenError:
            return error('无效的登录凭证', 401)

        if not payload.get('is_admin'):
            return error('无管理员权限', 403)

        g.admin = payload.get('sub')
        return view(*args, **kwargs)

    return wrapped


# ---------------- 认证 ----------------

@bp.post('/auth/login')
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    if username != ADMIN_USERNAME or password != ADMIN_PASSWORD:
        log_operation('login', '后台登录失败：账号或密码错误',
                      target_type='系统', result='fail', operator=username or 'unknown')
        return error('账号或密码错误', 401)

    log_operation('login', '后台登录成功', target_type='系统', operator=ADMIN_USERNAME)
    return {
        'token': generate_admin_token(),
        'token_type': current_app.config['TOKEN_TYPE'],
        'user': {'username': ADMIN_USERNAME, 'role': 'admin'},
    }


@bp.get('/auth/me')
@admin_required
def me():
    return {'username': ADMIN_USERNAME, 'role': 'admin'}


# ---------------- 账户管理 ----------------

@bp.get('/users')
@admin_required
def list_users():
    db = get_db()
    rows = db.execute(
        """
        SELECT u.id, u.username, u.nickname, u.role, u.status, u.openid, u.created_at,
               (SELECT COUNT(*) FROM posts p WHERE p.author_id = u.id) AS post_count,
               (SELECT COUNT(*) FROM replies r WHERE r.author_id = u.id) AS reply_count
          FROM users u
         ORDER BY u.id ASC
        """
    ).fetchall()
    return {
        'items': [
            {
                'id': r['id'],
                'username': r['username'],
                'nickname': r['nickname'] or '',
                'role': r['role'],
                'status': r['status'],
                'openid': r['openid'],
                'created_at': r['created_at'],
                'post_count': r['post_count'],
                'reply_count': r['reply_count'],
            }
            for r in rows
        ]
    }


@bp.patch('/users/<int:user_id>/status')
@admin_required
def set_user_status(user_id):
    data = request.get_json(silent=True) or {}
    status = data.get('status')
    if status not in VALID_STATUS:
        return error('状态值不合法')

    db = get_db()
    user = db.execute('SELECT id, username FROM users WHERE id = ?', (user_id,)).fetchone()
    if user is None:
        log_operation('user_status', f'修改用户状态失败：用户 #{user_id} 不存在（目标状态：{status}）',
                      target_type='用户', target_id=user_id, result='fail')
        return error('用户不存在', 404)

    db.execute('UPDATE users SET status = ? WHERE id = ?', (status, user_id))
    db.commit()
    status_label = '启用' if status == 'active' else '禁用'
    log_operation('user_status', f'将用户「{user["username"]}」状态调整为：{status_label}',
                  target_type='用户', target_id=user_id)
    return {'id': user_id, 'status': status}


@bp.patch('/users/<int:user_id>/role')
@admin_required
def set_user_role(user_id):
    data = request.get_json(silent=True) or {}
    role = data.get('role')
    if role not in VALID_ROLES:
        return error('角色值不合法')

    db = get_db()
    user = db.execute('SELECT id, username FROM users WHERE id = ?', (user_id,)).fetchone()
    if user is None:
        log_operation('user_role', f'修改用户角色失败：用户 #{user_id} 不存在（目标角色：{role}）',
                      target_type='用户', target_id=user_id, result='fail')
        return error('用户不存在', 404)

    db.execute('UPDATE users SET role = ? WHERE id = ?', (role, user_id))
    db.commit()
    log_operation('user_role', f'将用户「{user["username"]}」角色调整为：{role}',
                  target_type='用户', target_id=user_id)
    return {'id': user_id, 'role': role}


# ---------------- 发帖管理 ----------------

@bp.get('/posts')
@admin_required
def list_posts():
    zone = request.args.get('zone')
    keyword = (request.args.get('keyword') or '').strip()
    db = get_db()

    where = []
    params = []
    if zone:
        if zone not in ZONE_KEYS:
            return error('无效的分区')
        where.append('p.zone = ?')
        params.append(zone)
    if keyword:
        where.append('(p.title LIKE ? OR p.content LIKE ?)')
        params.extend([f'%{keyword}%', f'%{keyword}%'])

    where_sql = (' WHERE ' + ' AND '.join(where)) if where else ''

    rows = db.execute(
        f"""
        SELECT p.id, p.zone, p.title, p.content, p.author_id, p.created_at,
               u.username AS author_username, u.role AS author_role,
               (SELECT COUNT(*) FROM replies r WHERE r.post_id = p.id) AS reply_count
          FROM posts p
          JOIN users u ON u.id = p.author_id
        {where_sql}
         ORDER BY p.created_at DESC, p.id DESC
        """,
        params,
    ).fetchall()

    return {
        'items': [
            {
                'id': r['id'],
                'zone': r['zone'],
                'title': r['title'],
                'content': r['content'],
                'author': {
                    'id': r['author_id'],
                    'username': r['author_username'],
                    'role': r['author_role'],
                },
                'reply_count': r['reply_count'],
                'created_at': r['created_at'],
            }
            for r in rows
        ]
    }


@bp.get('/posts/<int:post_id>/replies')
@admin_required
def list_replies(post_id):
    db = get_db()
    post = db.execute('SELECT id FROM posts WHERE id = ?', (post_id,)).fetchone()
    if post is None:
        return error('帖子不存在', 404)

    rows = db.execute(
        """
        SELECT r.id, r.content, r.author_id, r.created_at,
               u.username AS author_username, u.role AS author_role
          FROM replies r
          JOIN users u ON u.id = r.author_id
         WHERE r.post_id = ?
         ORDER BY r.created_at ASC, r.id ASC
        """,
        (post_id,),
    ).fetchall()
    return {
        'items': [
            {
                'id': r['id'],
                'content': r['content'],
                'author': {
                    'id': r['author_id'],
                    'username': r['author_username'],
                    'role': r['author_role'],
                },
                'created_at': r['created_at'],
            }
            for r in rows
        ]
    }


@bp.delete('/posts/<int:post_id>')
@admin_required
def delete_post(post_id):
    db = get_db()
    post = db.execute('SELECT id, title FROM posts WHERE id = ?', (post_id,)).fetchone()
    if post is None:
        log_operation('post_delete', f'删除帖子失败：帖子 #{post_id} 不存在',
                      target_type='帖子', target_id=post_id, result='fail')
        return error('帖子不存在', 404)

    # 手动级联删除回复（外键未设 ON DELETE CASCADE）
    db.execute('DELETE FROM replies WHERE post_id = ?', (post_id,))
    db.execute('DELETE FROM posts WHERE id = ?', (post_id,))
    db.commit()
    log_operation('post_delete', f'删除帖子「{post["title"]}」及其全部回复',
                  target_type='帖子', target_id=post_id)
    return {'deleted': True, 'id': post_id}


@bp.delete('/replies/<int:reply_id>')
@admin_required
def delete_reply(reply_id):
    db = get_db()
    reply = db.execute('SELECT id, content FROM replies WHERE id = ?', (reply_id,)).fetchone()
    if reply is None:
        log_operation('reply_delete', f'删除回复失败：回复 #{reply_id} 不存在',
                      target_type='回复', target_id=reply_id, result='fail')
        return error('回复不存在', 404)

    db.execute('DELETE FROM replies WHERE id = ?', (reply_id,))
    db.commit()
    preview = reply['content'][:50]
    log_operation('reply_delete', f'删除回复：{preview}',
                  target_type='回复', target_id=reply_id)
    return {'deleted': True, 'id': reply_id}
