import { computed, ref } from 'vue'
import Taro from '@tarojs/taro'
import { defineStore } from 'pinia'
import { TOKEN_KEY, USER_KEY } from '@/config'
import type { UserInfo } from '@/types'
import { isVipRole } from '@/utils/format'
import { authApi } from '@/services/auth'

export const useUserStore = defineStore('user', () => {
  // 登录态以可鉴权的 token 为准（不能只依赖用户信息对象）
  const token = ref('')
  const profile = ref<UserInfo | null>(null)

  const isLogin = computed(() => !!token.value)
  const isVip = computed(() => isLogin.value && isVipRole(profile.value?.role))
  const role = computed(() => profile.value?.role || 'user')

  /** 从本地存储恢复登录态 */
  function hydrate(): void {
    token.value = Taro.getStorageSync(TOKEN_KEY) || ''
    const cached = Taro.getStorageSync(USER_KEY)
    profile.value = cached || null
  }

  function setAuth(newToken: string, user: UserInfo): void {
    token.value = newToken
    profile.value = user
    Taro.setStorageSync(TOKEN_KEY, newToken)
    Taro.setStorageSync(USER_KEY, user)
  }

  function logout(): void {
    token.value = ''
    profile.value = null
    Taro.removeStorageSync(TOKEN_KEY)
    Taro.removeStorageSync(USER_KEY)
  }

  /** 拉取最新用户信息（角色可能被后台调整） */
  async function refreshMe(): Promise<void> {
    if (!token.value) return
    const user = await authApi.me()
    profile.value = user
    Taro.setStorageSync(USER_KEY, user)
  }

  /** 更新昵称 */
  async function updateNickname(nickname: string): Promise<void> {
    if (!token.value) return
    const user = await authApi.updateNickname(nickname)
    profile.value = user
    Taro.setStorageSync(USER_KEY, user)
  }

  return {
    token,
    profile,
    isLogin,
    isVip,
    role,
    hydrate,
    setAuth,
    logout,
    refreshMe,
    updateNickname,
  }
})
