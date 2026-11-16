<template>
  <view class="detail-page">
    <view v-if="detail" class="content-wrap">
      <!-- 帖子主体 -->
      <view class="post-card">
        <view class="zone-row">
          <text :class="['zone-tag', detail.zone === 'vip' ? 'zone-tag-vip' : 'zone-tag-free']">
            {{ detail.zone === 'vip' ? 'VIP收购区' : '自由讨论区' }}
          </text>
        </view>
        <text class="title">{{ detail.title }}</text>
        <view class="author-row">
          <role-tag :role="detail.author.role" />
          <text class="author-name">{{ detail.author.nickname || detail.author.username }}</text>
          <text class="time">{{ formatTime(detail.created_at) }}</text>
        </view>
        <text class="body">{{ detail.content }}</text>
      </view>

      <!-- 回复列表 -->
      <view class="reply-card">
        <text class="reply-title">全部回复 {{ detail.replies.length }}</text>

        <view v-if="detail.replies.length === 0" class="reply-empty">
          <text class="reply-empty-text">还没有回复，来说两句吧</text>
        </view>

        <view v-for="(reply, index) in detail.replies" :key="reply.id" class="reply-item">
          <view class="reply-avatar">{{ ((reply.author.nickname || reply.author.username)).slice(0, 1).toUpperCase() }}</view>
          <view class="reply-body">
            <view class="reply-head">
              <text class="reply-name">{{ reply.author.nickname || reply.author.username }}</text>
              <role-tag :role="reply.author.role" />
            </view>
            <text class="reply-content">{{ reply.content }}</text>
            <text class="reply-time">{{ formatTime(reply.created_at) }}</text>
          </view>
        </view>
      </view>
    </view>

    <view v-else-if="!loading" class="error-wrap">
      <text class="error-text">帖子不存在或已被删除</text>
    </view>

    <!-- 底部回复栏 -->
    <view v-if="detail" class="reply-bar">
      <input
        v-if="canReply"
        v-model="replyText"
        class="reply-input"
        type="text"
        maxlength="500"
        confirm-type="send"
        placeholder="写回复..."
        placeholder-class="placeholder"
        @confirm="onSend"
      />
      <view v-else class="reply-input reply-input-mask" @click="onBlockedReply">
        <text class="reply-input-mask-text">
          {{ userStore.isLogin ? '普通用户不可在 VIP 收购区回复' : '登录后参与回复' }}
        </text>
      </view>
      <button v-if="canReply" class="send-btn" :loading="sending" @click="onSend">发送</button>
      <view v-else class="send-btn send-btn-disabled" @click="onBlockedReply">
        <text class="send-btn-text">{{ userStore.isLogin ? '仅VIP' : '微信登录' }}</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import Taro, { useLoad } from '@tarojs/taro'
import { postApi } from '@/services/post'
import { useUserStore } from '@/stores/user'
import { formatTime } from '@/utils/format'
import { wechatQuickLogin } from '@/utils/wechatAuth'
import type { PostDetail, ReplyItem } from '@/types'
import RoleTag from '@/components/RoleTag.vue'

const userStore = useUserStore()
const detail = ref<PostDetail | null>(null)
const replyText = ref('')
const sending = ref(false)
const loading = ref(true)
const postId = ref(0)

const canReply = computed(() => {
  if (!userStore.isLogin || !detail.value) return false
  if (detail.value.zone === 'vip') return userStore.isVip
  return true
})

useLoad((options) => {
  userStore.hydrate()
  postId.value = Number(options?.id || 0)
  if (postId.value) loadDetail()
})

async function loadDetail(): Promise<void> {
  loading.value = true
  try {
    detail.value = await postApi.detail(postId.value)
  } catch (err) {
    console.error('[PostDetail] load failed:', postId.value, err)
  } finally {
    loading.value = false
  }
}

async function onSend(): Promise<void> {
  if (sending.value || !detail.value) return
  const content = replyText.value.trim()
  if (!content) {
    Taro.showToast({ title: '请输入回复内容', icon: 'none' })
    return
  }
  sending.value = true
  try {
    const reply: ReplyItem = await postApi.reply(postId.value, content)
    detail.value.replies.push(reply)
    detail.value.reply_count = detail.value.replies.length
    replyText.value = ''
    Taro.showToast({ title: '回复成功', icon: 'success' })
  } catch (err) {
    console.error('[PostDetail] reply failed:', err)
  } finally {
    sending.value = false
  }
}

/** 未登录 / 无权限点击回复栏 */
function onBlockedReply(): void {
  if (!userStore.isLogin) {
    wechatQuickLogin(`/pages/post-detail/index?id=${postId.value}`)
    return
  }
  Taro.showModal({
    title: '权限不足',
    content: '普通用户不可在 VIP 收购区回复，仅 VIP 用户可发布',
    showCancel: false,
    confirmText: '我知道了',
  })
}
</script>

<style lang="scss">
@use '@/styles/variables.scss' as *;

// 小程序不支持 scoped，所有规则嵌套在页面根类内
.detail-page {
  min-height: 100vh;
  padding: $spacing-md $page-padding 160rpx;

  .post-card {
    background: $color-bg-card;
    border-radius: $radius-lg;
    border: 1rpx solid $color-border-lighter;
    padding: $spacing-lg;
    box-shadow: $shadow-card;
  }

  .zone-row {
    margin-bottom: $spacing-sm;
  }

  .zone-tag {
    height: 40rpx;
    padding: 0 16rpx;
    border-radius: $radius-xs;
    font-size: $font-size-sm;
    line-height: 40rpx;
  }

  .zone-tag-vip {
    color: $color-vip-dark;
    background: $color-vip-bg;
  }

  .zone-tag-free {
    color: $color-primary-dark;
    background: rgba(7, 193, 96, 0.1);
  }

  .title {
    display: block;
    font-size: $font-size-xxl;
    font-weight: $font-weight-bold;
    color: $color-text-primary;
    line-height: $line-height-tight;
  }

  .author-row {
    display: flex;
    align-items: center;
    margin-top: $spacing-md;
    padding-bottom: $spacing-md;
    border-bottom: 1rpx solid $color-divider;
  }

  .author-name {
    margin-left: $spacing-xs;
    font-size: $font-size-sm;
    color: $color-text-secondary;
  }

  .time {
    margin-left: auto;
    font-size: $font-size-sm;
    color: $color-text-tertiary;
  }

  .body {
    display: block;
    margin-top: $spacing-md;
    font-size: $font-size-md;
    line-height: $line-height-loose;
    color: $color-text-primary;
    white-space: pre-wrap;
    word-break: break-word;
  }

  .reply-card {
    margin-top: $spacing-md;
    background: $color-bg-card;
    border-radius: $radius-lg;
    border: 1rpx solid $color-border-lighter;
    padding: $spacing-lg;
    box-shadow: $shadow-card;
  }

  .reply-title {
    font-size: $font-size-lg;
    font-weight: $font-weight-semibold;
    color: $color-text-primary;
  }

  .reply-empty {
    padding: $spacing-xl 0;
    text-align: center;
  }

  .reply-empty-text {
    font-size: $font-size-sm;
    color: $color-text-disabled;
  }

  .reply-item {
    display: flex;
    padding: $spacing-md 0;
    border-bottom: 1rpx solid $color-divider;

    &:last-child {
      border-bottom: none;
    }
  }

  .reply-avatar {
    flex-shrink: 0;
    width: 64rpx;
    height: 64rpx;
    border-radius: $radius-round;
    background: $gradient-primary;
    color: $color-text-white;
    font-size: 28rpx;
    text-align: center;
    line-height: 64rpx;
    margin-right: $spacing-sm;
  }

  .reply-body {
    flex: 1;
    min-width: 0;
  }

  .reply-head {
    display: flex;
    align-items: center;
  }

  .reply-name {
    font-size: $font-size-sm;
    color: $color-text-secondary;
    margin-right: $spacing-xs;
    font-weight: $font-weight-medium;
  }

  .reply-content {
    display: block;
    margin-top: 8rpx;
    font-size: $font-size-md;
    color: $color-text-primary;
    line-height: $line-height-normal;
    word-break: break-word;
  }

  .reply-time {
    display: block;
    margin-top: 8rpx;
    font-size: $font-size-xs;
    color: $color-text-disabled;
  }

  .error-wrap {
    padding: 160rpx 0;
    text-align: center;
  }

  .error-text {
    font-size: $font-size-md;
    color: $color-text-tertiary;
  }

  .reply-bar {
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    display: flex;
    align-items: center;
    padding: $spacing-sm $page-padding;
    padding-bottom: calc(#{$spacing-sm} + constant(safe-area-inset-bottom));
    padding-bottom: calc(#{$spacing-sm} + env(safe-area-inset-bottom));
    background: $color-bg-card;
    box-shadow: $shadow-float;
    z-index: 20;
  }

  .reply-input {
    flex: 1;
    height: 72rpx;
    padding: 0 $spacing-md;
    background: $color-bg-hover;
    border: 1rpx solid $color-border;
    border-radius: $radius-button;
    font-size: $font-size-md;
    color: $color-text-primary;
    box-sizing: border-box;
    transition: border-color $transition-fast;
  }

  .reply-input-mask {
    display: flex;
    align-items: center;
    background: $color-bg-hover;
    border: 1rpx solid $color-border-lighter;
  }

  .reply-input-mask-text {
    font-size: $font-size-sm;
    color: $color-text-disabled;
  }

  .send-btn {
    flex-shrink: 0;
    margin-left: $spacing-sm;
    min-width: 128rpx;
    height: 72rpx;
    line-height: 72rpx;
    padding: 0 $spacing-md;
    border-radius: $radius-button;
    background: $gradient-primary;
    color: $color-text-white;
    font-size: $font-size-md;
    font-weight: $font-weight-semibold;
    border: none;
    box-shadow: 0 4rpx 12rpx rgba(7, 193, 96, 0.28);

    &::after {
      border: none;
    }

    &:active {
      opacity: 0.9;
      transform: scale(0.98);
    }
  }

  .send-btn-disabled {
    background: $color-text-disabled;
    box-shadow: none;
  }

  .send-btn-text {
    color: $color-text-white;
    font-size: $font-size-sm;
  }
}
</style>
