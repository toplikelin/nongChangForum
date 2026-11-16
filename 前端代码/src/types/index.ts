/** 业务类型定义 */

export type Role = 'user' | 'vip1' | 'vip2' | 'vip3'

export type ZoneKey = 'vip' | 'free'

export interface UserInfo {
  id: number
  username: string
  /** 昵称（可空，展示优先用昵称，空则 fallback 到 username） */
  nickname: string
  role: Role
  created_at: string
}

export interface AuthResult {
  token: string
  token_type: string
  user: UserInfo
}

export interface ZoneInfo {
  key: ZoneKey
  name: string
  description: string
  /** 是否仅 VIP 可发帖 */
  post_only_vip: boolean
}

export interface PostAuthor {
  id: number
  username: string
  nickname: string
  role: Role
}

export interface PostItem {
  id: number
  zone: ZoneKey
  title: string
  content: string
  author: PostAuthor
  reply_count: number
  created_at: string
}

export interface PostList {
  items: PostItem[]
  total: number
  page: number
  size: number
}

export interface ReplyItem {
  id: number
  content: string
  author: PostAuthor
  created_at: string
  /** 仅查"我的回复"时有值，指向被回复的帖子 */
  post?: {
    id: number
    title: string
    zone: ZoneKey
  }
}

export interface PostDetail extends PostItem {
  replies: ReplyItem[]
}
