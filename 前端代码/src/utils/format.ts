import type { Role, ZoneKey } from '@/types'

/** 角色中文文案 */
export function roleText(role?: Role | string): string {
  switch (role) {
    case 'vip1':
      return 'VIP1'
    case 'vip2':
      return 'VIP2'
    case 'vip3':
      return 'VIP3'
    default:
      return '普通用户'
  }
}

/** 是否 VIP 角色 */
export function isVipRole(role?: Role | string | null): boolean {
  return !!role && role !== 'user'
}

/** 分区名称 */
export function zoneName(zone: ZoneKey | string): string {
  return zone === 'vip' ? 'VIP收购区' : '自由讨论区'
}

/** 兼容各端的时间解析（iOS 微信不支持直接解析带 T 的 ISO） */
function parseDate(iso: string): Date {
  return new Date(iso.slice(0, 19).replace('T', ' ').replace(/-/g, '/'))
}

function pad(n: number): string {
  return n < 10 ? `0${n}` : `${n}`
}

/** 相对时间 + 绝对时间兜底 */
export function formatTime(iso: string): string {
  const date = parseDate(iso)
  if (Number.isNaN(date.getTime())) return ''
  const diff = Date.now() - date.getTime()
  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour

  if (diff < minute) return '刚刚'
  if (diff < hour) return `${Math.floor(diff / minute)}分钟前`
  if (diff < day) return `${Math.floor(diff / hour)}小时前`
  if (diff < 2 * day) return '昨天'

  const now = new Date()
  const md = `${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
  if (date.getFullYear() === now.getFullYear()) {
    return diff < 7 * day ? `${Math.floor(diff / day)}天前` : md
  }
  return `${date.getFullYear()}-${md}`
}
