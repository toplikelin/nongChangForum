import { request } from '@/utils/request'
import type {
  PostDetail,
  PostItem,
  PostList,
  ReplyItem,
  ZoneInfo,
  ZoneKey,
} from '@/types'

export interface PostListParams {
  zone?: ZoneKey
  page?: number
  size?: number
}

export const postApi = {
  /** 分区列表 */
  zones(): Promise<ZoneInfo[]> {
    return request<ZoneInfo[]>({ url: '/api/zones' })
  },

  /** 帖子列表（不传 zone 查全部） */
  list(params: PostListParams = {}): Promise<PostList> {
    const query = Object.keys(params)
      .filter((k) => params[k as keyof PostListParams] !== undefined)
      .map((k) => `${k}=${encodeURIComponent(String(params[k as keyof PostListParams]))}`)
      .join('&')
    return request<PostList>({ url: `/api/posts${query ? `?${query}` : ''}` })
  },

  /** 帖子详情 */
  detail(id: number): Promise<PostDetail> {
    return request<PostDetail>({ url: `/api/posts/${id}` })
  },

  /** 发帖（VIP 收购区仅 VIP 角色，由后端强制校验） */
  create(zone: ZoneKey, title: string, content: string): Promise<PostItem> {
    return request<PostItem>({
      url: '/api/posts',
      method: 'POST',
      data: { zone, title, content },
    })
  },

  /** 回复帖子 */
  reply(postId: number, content: string): Promise<ReplyItem> {
    return request<ReplyItem>({
      url: `/api/posts/${postId}/replies`,
      method: 'POST',
      data: { content },
    })
  },

  /** 当前登录用户自己的发帖 */
  myPosts(page = 1, size = 20): Promise<PostList> {
    return request<PostList>({ url: `/api/posts/my?page=${page}&size=${size}` })
  },

  /** 当前登录用户自己的回复 */
  myReplies(page = 1, size = 20): Promise<{ items: ReplyItem[]; total: number; page: number; size: number }> {
    return request<{ items: ReplyItem[]; total: number; page: number; size: number }>({
      url: `/api/replies/my?page=${page}&size=${size}`,
    })
  },
}
