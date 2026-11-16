<template>
  <view class="activity-page">
    <view class="tabs">
      <view :class="['tab-item', activeTab === 'posts' ? 'active' : '']" @click="activeTab = 'posts'">
        <text>我的发帖{{ postsTotal > 0 ? ` (${postsTotal})` : '' }}</text>
      </view>
      <view :class="['tab-item', activeTab === 'replies' ? 'active' : '']" @click="activeTab = 'replies'">
        <text>我的回复{{ repliesTotal > 0 ? ` (${repliesTotal})` : '' }}</text>
      </view>
    </view>

    <!-- 发帖列表 -->
    <block v-if="activeTab === 'posts'">
      <view v-if="postsLoading" class="loading">加载中...</view>
      <view v-else-if="posts.length === 0" class="empty">还没有发过帖子</view>
      <view v-else>
        <view v-for="p in posts" :key="p.id" class="pcard" @click="openPost(p.id)">
          <view class="card-top">
            <text :class="['zone-tag', p.zone === 'vip' ? 'zone-tag-vip' : 'zone-tag-free']">
              {{ p.zone === 'vip' ? 'VIP' : '自由' }}
            </text>
            <text class="title">{{ p.title }}</text>
          </view>
          <text class="content">{{ p.content }}</text>
          <view class="card-footer">
            <text class="author">{{ p.author.nickname || p.author.username }}</text>
            <text class="meta">回复 {{ p.reply_count }} · {{ formatTime(p.created_at) }}</text>
          </view>
        </view>
      </view>
    </block>

    <!-- 回复列表 -->
    <block v-if="activeTab === 'replies'">
      <view v-if="repliesLoading" class="loading">加载中...</view>
      <view v-else-if="replies.length === 0" class="empty">还没有回过帖</view>
      <view v-else>
        <view v-for="r in replies" :key="r.id" class="reply-card" @click="openPost(r.post?.id)">
          <view v-if="r.post" class="reply-post-row">
            <text :class="['zone-tag', r.post.zone === 'vip' ? 'zone-tag-vip' : 'zone-tag-free']">
              {{ r.post.zone === 'vip' ? 'VIP' : '自由' }}
            </text>
            <text class="reply-post-title">{{ r.post.title }}</text>
          </view>
          <text class="reply-content">{{ r.content }}</text>
          <view class="reply-meta">
            <text class="reply-time">{{ formatTime(r.created_at) }}</text>
            <text class="reply-open">查看帖子 ›</text>
          </view>
        </view>
      </view>
    </block>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Taro, { useDidShow, useLoad } from '@tarojs/taro'
import { postApi } from '@/services/post'
import { formatTime } from '@/utils/format'
import { useUserStore } from '@/stores/user'
import type { PostItem, ReplyItem } from '@/types'

type TabKey = 'posts' | 'replies'

const userStore = useUserStore()
const activeTab = ref<TabKey>('posts')

const posts = ref<PostItem[]>([])
const postsTotal = ref(0)
const postsLoading = ref(false)

const replies = ref<ReplyItem[]>([])
const repliesTotal = ref(0)
const repliesLoading = ref(false)

useLoad((options) => {
  if (options?.tab === 'replies') activeTab.value = 'replies'
})

async function loadAll(): Promise<void> {
  if (!userStore.isLogin) return
  postsLoading.value = true
  repliesLoading.value = true
  try {
    const [postsRes, repliesRes] = await Promise.all([
      postApi.myPosts(1, 50),
      postApi.myReplies(1, 50),
    ])
    postsTotal.value = postsRes.total
    posts.value = postsRes.items
    repliesTotal.value = repliesRes.total
    replies.value = repliesRes.items
  } catch (err) {
    console.error('[MyActivity] load all failed:', err)
  } finally {
    postsLoading.value = false
    repliesLoading.value = false
  }
}

function openPost(postId?: number): void {
  if (!postId) return
  Taro.navigateTo({ url: `/pages/post-detail/index?id=${postId}` })
}

useDidShow(() => {
  userStore.hydrate()
  if (!userStore.isLogin) return
  if (posts.value.length === 0 && replies.value.length === 0) loadAll()
})
</script>

<style lang="scss">
@use '@/styles/variables.scss' as *;

.activity-page { min-height: 100vh; padding: 0 $page-padding 48rpx; }

.tabs {
  display: flex; background: $color-bg-card; border-radius: $radius-lg;
  padding: 6rpx; margin: $spacing-md 0; border: 1rpx solid $color-border-lighter;
}
.tab-item {
  flex: 1; height: 72rpx; display: flex; align-items: center; justify-content: center;
  font-size: $font-size-md; color: $color-text-secondary; border-radius: $radius-button;
  &.active { color: $color-primary; font-weight: $font-weight-semibold; background: rgba(7,193,96,0.08); }
}
.loading, .empty { text-align: center; padding: 80rpx 0; color: $color-text-tertiary; font-size: $font-size-sm; }

.pcard, .reply-card {
  background: $color-bg-card; border-radius: $radius-lg; border: 1rpx solid $color-border-lighter;
  padding: $spacing-lg; margin-bottom: $spacing-md; box-shadow: $shadow-card;
}
.card-top { display: flex; align-items: center; }
.zone-tag {
  flex-shrink: 0; height: 36rpx; padding: 0 12rpx; margin-right: $spacing-sm;
  border-radius: $radius-xs; font-size: $font-size-xs; line-height: 36rpx;
  &.zone-tag-vip { color: $color-vip-dark; background: $color-vip-bg; }
  &.zone-tag-free { color: $color-primary-dark; background: rgba(7,193,96,0.1); }
}
.title { flex: 1; font-size: $font-size-lg; font-weight: $font-weight-semibold; color: $color-text-primary; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.content { display: block; margin-top: $spacing-sm; font-size: $font-size-md; color: $color-text-secondary; line-height: $line-height-normal; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
.card-footer { display: flex; align-items: center; justify-content: space-between; margin-top: $spacing-md; }
.author, .meta { font-size: $font-size-sm; color: $color-text-tertiary; }

.reply-post-row { display: flex; align-items: center; gap: $spacing-sm; margin-bottom: $spacing-sm; padding-bottom: $spacing-sm; border-bottom: 1rpx dashed $color-divider; }
.reply-post-title { flex: 1; font-size: $font-size-sm; color: $color-text-secondary; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.reply-content { display: block; font-size: $font-size-md; color: $color-text-primary; line-height: $line-height-normal; }
.reply-meta { display: flex; align-items: center; justify-content: space-between; margin-top: $spacing-md; }
.reply-time { font-size: $font-size-xs; color: $color-text-tertiary; }
.reply-open { font-size: $font-size-xs; color: $color-primary; }
</style>
