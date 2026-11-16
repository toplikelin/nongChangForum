"""帖子相关接口：分区 / 列表 / 详情 / 发帖 / 回复"""
from flask import Blueprint, g, request

from database import get_db
from security import login_required
from serializers import ZONES, ZONE_KEYS, post_detail, post_item, reply
from utils import error, is_vip, now_iso

bp = Blueprint('posts', __name__, url_prefix='/api')

POST_COLUMNS = """
    SELECT p.id, p.zone, p.title, p.content, p.author_id, p.created_at,
           u.username AS author_username, u.nickname AS author_nickname, u.role AS author_role,
           (SELECT COUNT(*) FROM replies r WHERE r.post_id = p.id) AS reply_count
      FROM posts p
      JOIN users u ON u.id = p.author_id
"""

REPLY_COLUMNS = """
    SELECT r.id AS reply_id, r.content, r.author_id, r.created_at,
           u.username AS author_username, u.nickname AS author_nickname, u.role AS author_role,
           p.id AS post_id, p.title AS post_title, p.zone AS post_zone
      FROM replies r
      JOIN users u ON u.id = r.author_id
      JOIN posts p ON p.id = r.post_id
"""


def _get_post(db, post_id):
    return db.execute(
        POST_COLUMNS + ' WHERE p.id = ?', (post_id,)
    ).fetchone()


@bp.get('/zones')
def list_zones():
    return {'items': ZONES}


@bp.get('/posts')
def list_posts():
    zone = request.args.get('zone')
    if zone is not None and zone not in ZONE_KEYS:
        return error('无效的分区')

    try:
        page = max(1, int(request.args.get('page', 1)))
        size = int(request.args.get('size', 10))
    except ValueError:
        return error('分页参数不合法')
    size = max(1, min(size, 50))

    db = get_db()
    where = ''
    params = []
    if zone:
        where = ' WHERE p.zone = ?'
        params.append(zone)

    total = db.execute(
        'SELECT COUNT(*) FROM posts p' + where, params
    ).fetchone()[0]

    rows = db.execute(
        POST_COLUMNS + where +
        ' ORDER BY p.created_at DESC, p.id DESC LIMIT ? OFFSET ?',
        params + [size, (page - 1) * size],
    ).fetchall()

    return {
        'items': [post_item(r) for r in rows],
        'total': total,
        'page': page,
        'size': size,
    }


@bp.get('/posts/<int:post_id>')
def get_post(post_id):
    db = get_db()
    post = _get_post(db, post_id)
    if post is None:
        return error('帖子不存在或已被删除', 404)

    replies = db.execute(
        REPLY_COLUMNS + ' WHERE r.post_id = ? ORDER BY r.created_at ASC, r.id ASC',
        (post_id,),
    ).fetchall()
    return post_detail(post, replies)


@bp.post('/posts')
@login_required
def create_post():
    data = request.get_json(silent=True) or {}
    zone = data.get('zone')
    title = (data.get('title') or '').strip()
    content = (data.get('content') or '').strip()

    if zone not in ZONE_KEYS:
        return error('请选择有效的分区')
    if not title:
        return error('请输入标题')
    if len(title) > 100:
        return error('标题不能超过 100 个字符')
    if not content:
        return error('请输入正文内容')
    if len(content) > 5000:
        return error('正文不能超过 5000 个字符')

    user = g.current_user
    if zone == 'vip' and not is_vip(user['role']):
        return error('VIP 收购区仅限 VIP 用户发帖', 403)

    db = get_db()
    cur = db.execute(
        'INSERT INTO posts (zone, title, content, author_id, created_at) VALUES (?, ?, ?, ?, ?)',
        (zone, title, content, user['id'], now_iso()),
    )
    db.commit()

    created = _get_post(db, cur.lastrowid)
    return post_item(created)


@bp.post('/posts/<int:post_id>/replies')
@login_required
def create_reply(post_id):
    data = request.get_json(silent=True) or {}
    content = (data.get('content') or '').strip()

    if not content:
        return error('请输入回复内容')
    if len(content) > 5000:
        return error('回复不能超过 5000 个字符')

    db = get_db()
    post = db.execute('SELECT zone FROM posts WHERE id = ?', (post_id,)).fetchone()
    if post is None:
        return error('帖子不存在或已被删除', 404)

    user = g.current_user
    if post['zone'] == 'vip' and not is_vip(user['role']):
        return error('VIP 收购区仅限 VIP 用户回复', 403)

    cur = db.execute(
        'INSERT INTO replies (post_id, content, author_id, created_at) VALUES (?, ?, ?, ?)',
        (post_id, content, user['id'], now_iso()),
    )
    db.commit()

    row = db.execute(
        REPLY_COLUMNS + ' WHERE r.id = ?', (cur.lastrowid,)
    ).fetchone()
    return reply(row)


# ---------------- 当前用户自己的发帖 / 回复 ----------------


@bp.get('/posts/my')
@login_required
def my_posts():
    """当前登录用户自己发的帖子"""
    try:
        page = max(1, int(request.args.get('page', 1)))
        size = int(request.args.get('size', 10))
    except ValueError:
        return error('分页参数不合法')
    size = max(1, min(size, 50))

    db = get_db()
    user_id = g.current_user['id']
    total = db.execute(
        'SELECT COUNT(*) FROM posts WHERE author_id = ?', (user_id,)
    ).fetchone()[0]

    rows = db.execute(
        POST_COLUMNS + ' WHERE p.author_id = ? ORDER BY p.created_at DESC, p.id DESC LIMIT ? OFFSET ?',
        (user_id, size, (page - 1) * size),
    ).fetchall()

    return {
        'items': [post_item(r) for r in rows],
        'total': total,
        'page': page,
        'size': size,
    }


@bp.get('/replies/my')
@login_required
def my_replies():
    """当前登录用户自己的回复（附带所属帖子信息）"""
    try:
        page = max(1, int(request.args.get('page', 1)))
        size = int(request.args.get('size', 10))
    except ValueError:
        return error('分页参数不合法')
    size = max(1, min(size, 50))

    db = get_db()
    user_id = g.current_user['id']
    total = db.execute(
        'SELECT COUNT(*) FROM replies WHERE author_id = ?', (user_id,)
    ).fetchone()[0]

    rows = db.execute(
        REPLY_COLUMNS + ' WHERE r.author_id = ? ORDER BY r.created_at DESC, r.id DESC LIMIT ? OFFSET ?',
        (user_id, size, (page - 1) * size),
    ).fetchall()

    return {
        'items': [reply(r) for r in rows],
        'total': total,
        'page': page,
        'size': size,
    }
