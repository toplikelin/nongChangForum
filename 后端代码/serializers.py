"""响应序列化：字段与前端 src/types/index.ts 严格对齐"""

# 分区固定信息
ZONES = [
    {
        'key': 'vip',
        'name': 'VIP收购区',
        'description': '仅限 VIP 角色发帖与回复',
        'post_only_vip': True,
    },
    {
        'key': 'free',
        'name': '自由讨论区',
        'description': '所有登录用户均可参与',
        'post_only_vip': False,
    },
]
ZONE_KEYS = {z['key'] for z in ZONES}


def user_info(user) -> dict:
    nickname = (user['nickname'] or '').strip() or user['username']
    return {
        'id': user['id'],
        'username': user['username'],
        'nickname': nickname,
        'role': user['role'],
        'created_at': user['created_at'],
    }


def author(user) -> dict:
    nickname = (user['nickname'] or '').strip() or user['username']
    return {
        'id': user['id'],
        'username': user['username'],
        'nickname': nickname,
        'role': user['role'],
    }


def reply(item) -> dict:
    """item 为 replies JOIN users (+ 可选 posts) 的 sqlite3.Row"""
    row = dict(item)
    author_nickname = (row.get('author_nickname') or '').strip() or row['author_username']
    result = {
        'id': row['reply_id'],
        'content': row['content'],
        'author': {
            'id': row['author_id'],
            'username': row['author_username'],
            'nickname': author_nickname,
            'role': row['author_role'],
        },
        'created_at': row['created_at'],
    }
    # 如果 JOIN 了 posts（查"我的回复"场景），附带帖子信息方便前端跳回
    if row.get('post_id') is not None:
        result['post'] = {
            'id': row['post_id'],
            'title': row['post_title'],
            'zone': row['post_zone'],
        }
    return result


def post_item(item) -> dict:
    """item 为 posts JOIN users + reply_count 的 sqlite3.Row"""
    row = dict(item)
    author_nickname = (row.get('author_nickname') or '').strip() or row['author_username']
    return {
        'id': row['id'],
        'zone': row['zone'],
        'title': row['title'],
        'content': row['content'],
        'author': {
            'id': row['author_id'],
            'username': row['author_username'],
            'nickname': author_nickname,
            'role': row['author_role'],
        },
        'reply_count': row['reply_count'],
        'created_at': row['created_at'],
    }


def post_detail(item, reply_items) -> dict:
    data = post_item(item)
    data['replies'] = [reply(r) for r in reply_items]
    return data
