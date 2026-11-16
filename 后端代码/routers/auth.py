"""认证相关接口：注册 / 登录 / 当前用户 / 微信一键登录"""
import hashlib
import time
from urllib.parse import urlencode

from flask import Blueprint, current_app, g, request
from werkzeug.security import check_password_hash, generate_password_hash

from database import get_db
from security import generate_token, login_required
from serializers import user_info
from utils import error, now_iso

try:
    import requests
except ImportError:  # pragma: no cover - requests 未安装时降级到 mock
    requests = None  # type: ignore[assignment]

bp = Blueprint('auth', __name__, url_prefix='/api/auth')


def _auth_payload(user) -> dict:
    return {
        'token': generate_token(user),
        'token_type': current_app.config['TOKEN_TYPE'],
        'user': user_info(user),
    }


def _get_credentials():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    return username, password


@bp.post('/register')
def register():
    username, password = _get_credentials()

    if not username:
        return error('请输入账号')
    if len(username) < 3 or len(username) > 20:
        return error('账号长度需为 3-20 个字符')
    if not password:
        return error('请输入密码')
    if len(password) < 6 or len(password) > 64:
        return error('密码长度需为 6-64 个字符')

    db = get_db()
    exists = db.execute(
        'SELECT id FROM users WHERE username = ?', (username,)
    ).fetchone()
    if exists:
        return error('该账号已被注册')

    # 注册默认赋予普通用户角色，默认昵称 = 账号
    cur = db.execute(
        'INSERT INTO users (username, nickname, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)',
        (username, username, generate_password_hash(password), 'user', now_iso()),
    )
    db.commit()

    user = db.execute(
        'SELECT * FROM users WHERE id = ?',
        (cur.lastrowid,),
    ).fetchone()
    return _auth_payload(user)


@bp.post('/login')
def login():
    username, password = _get_credentials()

    if not username or not password:
        return error('请输入账号和密码')

    db = get_db()
    user = db.execute(
        'SELECT * FROM users WHERE username = ?',
        (username,),
    ).fetchone()

    if user is None or not check_password_hash(user['password_hash'], password):
        return error('账号或密码错误', 401)

    safe_user = db.execute(
        'SELECT * FROM users WHERE id = ?',
        (user['id'],),
    ).fetchone()
    return _auth_payload(safe_user)


@bp.get('/me')
@login_required
def me():
    return user_info(g.current_user)


@bp.route('/me', methods=['PATCH', 'PUT'])
@login_required
def update_me():
    """当前用户修改自己的昵称（账号 username 不可改，唯一约束）
    同时支持 PATCH 和 PUT：微信小程序 wx.request 不支持 PATCH，前端用 PUT。"""
    data = request.get_json(silent=True) or {}
    nickname = (data.get('nickname') or '').strip()
    print(f"[update_me] uid={g.current_user['id']} username={g.current_user['username']} new_nickname={nickname!r}", flush=True)

    # 允许清空（用户可以把昵称删掉回到默认）；非空则校验长度
    if nickname and len(nickname) > 20:
        return error('昵称最多 20 个字符')

    db = get_db()
    db.execute('UPDATE users SET nickname = ? WHERE id = ?', (nickname or None, g.current_user['id']))
    db.commit()

    user = db.execute('SELECT * FROM users WHERE id = ?', (g.current_user['id'],)).fetchone()
    return user_info(user)


# ---------------- 微信小程序登录 ----------------


def _mock_openid_from_code(code: str) -> tuple[str, str | None]:
    """开发模式：code 以 'mock_' 开头则直接生成稳定 openid，否则用哈希派生命中率固定
    返回 (openid, unionid)"""
    if code.startswith('mock_'):
        openid = code  # mock_001 / mock_demo 等直接返回
        return openid, None
    # 用 code + 盐哈希作为稳定 openid（生产环境不用走这里）
    digest = hashlib.sha256(('salt:' + code).encode()).hexdigest()[:28]
    return f'dev_{digest}', None


def _exchange_code(code: str) -> tuple[str, str | None]:
    """真实环境走微信 jscode2session 接口，开发环境走 mock"""
    if current_app.config['WECHAT_DEV_MOCK']:
        return _mock_openid_from_code(code)

    appid = current_app.config['WECHAT_APPID']
    secret = current_app.config['WECHAT_SECRET']
    if not appid or not secret:
        raise RuntimeError('后端未配置 WECHAT_APPID / WECHAT_SECRET')

    url = 'https://api.weixin.qq.com/sns/jscode2session?' + urlencode({
        'appid': appid, 'secret': secret, 'js_code': code, 'grant_type': 'authorization_code',
    })
    if requests is None:
        raise RuntimeError('Python requests 库未安装，请先 pip install requests')
    try:
        resp = requests.get(url, timeout=8)
        payload = resp.json()
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f'调用微信 jscode2session 失败：{exc}')

    if 'openid' not in payload:
        msg = payload.get('errmsg', '微信返回异常')
        raise RuntimeError(f'微信登录失败：{msg}')
    return payload['openid'], payload.get('unionid')


def _wechat_auth_payload(user, is_new_user: bool) -> dict:
    payload = _auth_payload(user)
    payload['is_new_user'] = is_new_user
    return payload


@bp.post('/wechat-login')
def wechat_login():
    """微信一键登录：接收 code → 换 openid → 自动创建或登录对应用户"""
    data = request.get_json(silent=True) or {}
    code = (data.get('code') or '').strip()
    nickname = (data.get('nickname') or '').strip()
    avatar = (data.get('avatar') or '').strip()

    if not code:
        return error('缺少 code 参数')

    try:
        openid, unionid = _exchange_code(code)
    except RuntimeError as exc:
        return error(str(exc), 502)

    db = get_db()
    user = db.execute('SELECT * FROM users WHERE openid = ?', (openid,)).fetchone()

    if user is None:
        # 自动注册：生成随机用户名（以 wx_ 前缀区分）
        rand = hashlib.md5(f'{openid}{time.time()}'.encode()).hexdigest()[:8]
        base_username = nickname or f'wx_{rand}'
        username = base_username
        suffix = 1
        while db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone() is not None:
            username = f'{base_username}_{suffix}'
            suffix += 1

        # openid 登录不设密码（后续绑定账号时再设置），默认昵称 = username
        cur = db.execute(
            """INSERT INTO users (username, nickname, password_hash, role, openid, unionid, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (username, username, generate_password_hash(openid), 'user', openid, unionid, now_iso()),
        )
        db.commit()
        user = db.execute('SELECT * FROM users WHERE id = ?', (cur.lastrowid,)).fetchone()
        return _wechat_auth_payload(user, is_new_user=True)

    # 已存在用户：若此次拿到 unionid 则顺便更新
    if unionid and not user['unionid']:
        db.execute('UPDATE users SET unionid = ? WHERE id = ?', (unionid, user['id']))
        db.commit()

    safe_user = db.execute(
        'SELECT * FROM users WHERE id = ?',
        (user['id'],),
    ).fetchone()
    return _wechat_auth_payload(safe_user, is_new_user=False)
