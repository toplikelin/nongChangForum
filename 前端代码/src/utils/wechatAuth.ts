/**
 * 微信一键登录公共方法。
 * 所有需要登录的页面（首页、论坛、我的、帖子详情、发布页等）都调用这里。
 * 流程：弹用户须知 → 同意 → 静默 wx.login → 后端换 openid → 自动登录/注册
 */
import Taro from '@tarojs/taro'
import { authApi } from '@/services/auth'
import { useUserStore } from '@/stores/user'

const CONTENT_LINES = [
  '1. 点击「同意并登录」即表示您已阅读并同意平台服务协议与隐私政策。',
  '',
  '2. 平台仅作为信息发布载体，用户在交流中产生的纠纷、交易风险及法律责任由当事人自行承担。',
  '',
  '3. 严禁发布违法违规内容，违者平台有权封禁账号并移交相关部门。',
  '',
  '4. 本平台提供的信息仅供参考，不构成任何投资、交易或履约承诺。',
].join('\n')

/**
 * 执行一次微信一键登录。不抛错，失败内部处理 Toast。
 * @param redirect 登录成功后如果需要回跳，传过来
 */
export async function wechatQuickLogin(redirect?: string): Promise<boolean> {
  const userStore = useUserStore()
  if (userStore.isLogin) return true

  // 1) 用户须知 + 免责声明弹窗
  try {
    const modal = await Taro.showModal({
      title: '用户须知与免责声明',
      content: CONTENT_LINES,
      confirmText: '同意',
      cancelText: '拒绝',
    })
    if (!modal.confirm) return false
  } catch (e) {
    console.error('[WechatLogin] showModal failed:', e)
    return false
  }

  // 2) 静默 wx.login 拿 code
  let code = ''
  try {
    const loginRes = await Taro.login()
    code = loginRes.code || ''
  } catch (e) {
    console.error('[WechatLogin] Taro.login failed:', e)
  }
  if (!code) {
    Taro.showToast({ title: '获取登录凭证失败，请重试', icon: 'none' })
    return false
  }

  // 3) 后端换 openid → 自动登录/注册
  try {
    const res = await authApi.wechatLogin(code)
    userStore.setAuth(res.token, res.user)
    Taro.showToast({
      title: res.is_new_user ? '登录成功，欢迎加入！' : '登录成功',
      icon: 'success',
    })

    // 4) 回跳
    if (redirect) {
      // Taro.login 成功需要一点时间等待 store / tab 切换稳定，稍延迟
      setTimeout(() => {
        if (redirect!.startsWith('/pages/home')) {
          Taro.switchTab({ url: redirect! })
        } else if (redirect!.startsWith('/pages/forum')) {
          Taro.switchTab({ url: redirect! })
        } else if (redirect!.startsWith('/pages/mine')) {
          Taro.switchTab({ url: redirect! })
        } else {
          Taro.redirectTo({ url: redirect! })
        }
      }, 300)
    }
    return true
  } catch (err) {
    console.error('[WechatLogin] wechatLogin api failed:', err)
    return false
  }
}
