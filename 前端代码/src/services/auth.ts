import { request } from '@/utils/request'
import type { AuthResult, UserInfo } from '@/types'

export const authApi = {
  /** 注册（后端默认赋予普通用户角色） */
  register(username: string, password: string): Promise<AuthResult> {
    return request<AuthResult>({
      url: '/api/auth/register',
      method: 'POST',
      data: { username, password },
    })
  },

  /** 登录（仅账户 + 密码） */
  login(username: string, password: string): Promise<AuthResult> {
    return request<AuthResult>({
      url: '/api/auth/login',
      method: 'POST',
      data: { username, password },
    })
  },

  /** 微信一键登录：后端根据 code 换 openid，自动登录或注册 */
  wechatLogin(code: string, nickname?: string, avatar?: string): Promise<AuthResult & { is_new_user?: boolean }> {
    return request<AuthResult & { is_new_user?: boolean }>({
      url: '/api/auth/wechat-login',
      method: 'POST',
      data: { code, nickname, avatar },
    })
  },

  /** 当前登录用户 */
  me(): Promise<UserInfo> {
    return request<UserInfo>({ url: '/api/auth/me' })
  },

  /** 修改当前用户昵称（小程序 wx.request 不支持 PATCH，用 PUT 替代） */
  updateNickname(nickname: string): Promise<UserInfo> {
    return request<UserInfo>({
      url: '/api/auth/me',
      method: 'PUT',
      data: { nickname },
    })
  },
}
