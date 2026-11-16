import Taro from '@tarojs/taro'
import { API_BASE_URL, TOKEN_KEY, USER_KEY } from '@/config'

export interface RequestOptions {
  url: string
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'
  data?: Record<string, unknown>
  /** 静默模式：不自动弹出错误提示 */
  silent?: boolean
}

function currentPageUrl(): string {
  const pages = Taro.getCurrentPages()
  const current = pages[pages.length - 1]
  if (!current) return ''
  let url = `/${current.route}`
  const options = current.options || {}
  const query = Object.keys(options)
    .map((k) => `${k}=${options[k]}`)
    .join('&')
  if (query) url += `?${query}`
  return url
}

/** 401 统一处理：清除登录态并跳转登录页（携带回跳地址） */
function handleUnauthorized(): void {
  Taro.removeStorageSync(TOKEN_KEY)
  Taro.removeStorageSync(USER_KEY)
  const url = currentPageUrl()
  if (url && url !== '/pages/login/index' && url !== '/pages/register/index') {
    Taro.redirectTo({ url: `/pages/login/index?redirect=${encodeURIComponent(url)}` })
  }
}

function extractError(data: unknown): string {
  if (data && typeof data === 'object') {
    const d = data as { detail?: unknown; message?: unknown }
    if (typeof d.detail === 'string') return d.detail
    if (typeof d.message === 'string') return d.message
  }
  return '请求失败，请稍后再试'
}

/** 统一请求封装（后端强制鉴权，token 由拦截器自动携带） */
export async function request<T = unknown>(options: RequestOptions): Promise<T> {
  const token = Taro.getStorageSync(TOKEN_KEY)
  const header: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) header.Authorization = `Bearer ${token}`

  let res: Taro.request.SuccessCallbackResult<{ detail?: string; message?: string }>
  try {
    res = await Taro.request({
      url: `${API_BASE_URL}${options.url}`,
      method: options.method || 'GET',
      data: options.data,
      header,
      timeout: 10000,
    })
  } catch (err) {
    console.error('[Request] network error:', options.url, err)
    if (!options.silent) {
      Taro.showToast({ title: '网络异常，请确认后端服务已启动', icon: 'none' })
    }
    throw new Error('网络异常')
  }

  if (res.statusCode >= 200 && res.statusCode < 300) {
    return res.data as T
  }

  const message = extractError(res.data)
  console.error('[Request] failed:', options.url, res.statusCode, message)

  if (res.statusCode === 401) {
    handleUnauthorized()
  } else if (!options.silent) {
    Taro.showToast({ title: message, icon: 'none' })
  }
  throw new Error(message)
}
