<template>
  <view class="home-page">
    <!-- 顶部欢迎横幅 -->
    <view class="banner">
      <block v-if="userStore.isLogin">
        <view class="banner-info">
          <text class="banner-greeting">欢迎回来</text>
          <view class="banner-user">
            <text class="banner-name">{{ displayName }}</text>
            <role-tag :role="userStore.role" />
          </view>
        </view>
        <view class="banner-avatar">{{ avatarChar }}</view>
      </block>
      <block v-else>
        <view class="banner-info">
          <text class="banner-greeting">登录交易论坛</text>
          <text class="banner-desc">登录后浏览分区、参与讨论</text>
        </view>
        <view class="banner-actions">
          <button class="banner-btn primary" @click="goLogin">微信登录</button>
        </view>
      </block>
    </view>

    <!-- 两大分区入口 -->
    <view class="zone-grid">
      <view class="zone-card vip" @click="enterZone('vip')">
        <view class="zone-icon">收</view>
        <view class="zone-main">
          <text class="zone-name">VIP收购区</text>
          <text class="zone-desc">VIP 专属发布</text>
        </view>
        <text class="zone-arrow">›</text>
      </view>
      <view class="zone-card free" @click="enterZone('free')">
        <view class="zone-icon">论</view>
        <view class="zone-main">
          <text class="zone-name">自由讨论区</text>
          <text class="zone-desc">全员自由畅聊</text>
        </view>
        <text class="zone-arrow">›</text>
      </view>
    </view>

    <!-- 最新讨论 -->
    <view class="section">
      <view class="section-head">
        <text class="section-title">最新讨论</text>
        <text v-if="userStore.isLogin" class="section-more" @click="goForum">全部 ›</text>
      </view>

      <block v-if="userStore.isLogin">
        <post-card
          v-for="post in latestPosts"
          :key="post.id"
          :post="post"
          @click="openPost"
        />
        <empty-state v-if="!loading && latestPosts.length === 0" text="还没有帖子，去发第一帖吧" />
      </block>
      <view v-else class="login-mask" @click="goLogin">
        <text class="login-mask-title">登录后查看最新讨论</text>
        <text class="login-mask-btn">微信登录</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import Taro, { useDidShow } from '@tarojs/taro'
import { useUserStore } from '@/stores/user'
import { useForumStore } from '@/stores/forum'
import { postApi } from '@/services/post'
import { wechatQuickLogin } from '@/utils/wechatAuth'
import type { PostItem, ZoneKey } from '@/types'
import PostCard from '@/components/PostCard.vue'
import EmptyState from '@/components/EmptyState.vue'
import RoleTag from '@/components/RoleTag.vue'

const userStore = useUserStore()
const forumStore = useForumStore()
const latestPosts = ref<PostItem[]>([])
const loading = ref(false)

const displayName = computed(
  () => userStore.profile?.nickname?.trim() || userStore.profile?.username || '用户'
)
const avatarChar = computed(() => displayName.value.slice(0, 1).toUpperCase() || 'U')

async function loadLatest(): Promise<void> {
  loading.value = true
  try {
    const res = await postApi.list({ page: 1, size: 8 })
    latestPosts.value = res.items
  } catch (err) {
    console.error('[Home] load latest posts failed:', err)
  } finally {
    loading.value = false
  }
}

useDidShow(() => {
  userStore.hydrate()
  if (userStore.isLogin) {
    loadLatest()
    userStore.refreshMe().catch((err) => console.error('[Home] refresh me failed:', err))
  } else {
    latestPosts.value = []
  }
})

function enterZone(zone: ZoneKey): void {
  if (!userStore.isLogin) {
    wechatQuickLogin('/pages/forum/index')
    return
  }
  forumStore.setZone(zone)
  Taro.switchTab({ url: '/pages/forum/index' })
}

function openPost(post: PostItem): void {
  Taro.navigateTo({ url: `/pages/post-detail/index?id=${post.id}` })
}

function goLogin(): void {
  wechatQuickLogin()
}

function goForum(): void {
  Taro.switchTab({ url: '/pages/forum/index' })
}
</script>

<style lang="scss">
@use '@/styles/variables.scss' as *;

// 小程序不支持 scoped，所有规则嵌套在页面根类内
.home-page {
  min-height: 100vh;
  padding: $spacing-md $page-padding 48rpx;

  .banner {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 40rpx $spacing-lg;
    border-radius: $radius-xl;
    background: $gradient-primary;
    box-shadow: 0 8rpx 24rpx rgba(7, 193, 96, 0.32);
  }

  .banner-info {
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .banner-greeting {
    font-size: $font-size-sm;
    color: rgba(255, 255, 255, 0.82);
  }

  .banner-user {
    display: flex;
    align-items: center;
    margin-top: $spacing-xs;
  }

  .banner-name {
    max-width: 320rpx;
    font-size: 40rpx;
    font-weight: $font-weight-bold;
    color: $color-text-white;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    margin-right: $spacing-sm;
  }

  .banner-desc {
    margin-top: $spacing-xs;
    font-size: $font-size-md;
    color: rgba(255, 255, 255, 0.85);
  }

  .banner-avatar {
    flex-shrink: 0;
    width: 96rpx;
    height: 96rpx;
    border-radius: $radius-round;
    background: rgba(255, 255, 255, 0.22);
    color: $color-text-white;
    font-size: 44rpx;
    font-weight: $font-weight-bold;
    text-align: center;
    line-height: 96rpx;
  }

  .banner-actions {
    display: flex;
    flex-direction: column;
  }

  .banner-btn + .banner-btn {
    margin-top: $spacing-md;
  }

  .banner-btn {
    height: $button-height-sm;
    line-height: $button-height-sm;
    padding: 0 40rpx;
    border-radius: $radius-button;
    font-size: $font-size-sm;
    border: none;
    transition: all $transition-fast;

    &::after {
      border: none;
    }

    &.primary {
      background: $color-text-white;
      color: $color-primary;
      font-weight: $font-weight-semibold;
      box-shadow: 0 4rpx 12rpx rgba(0, 0, 0, 0.08);

      &:active {
        opacity: 0.92;
        transform: scale(0.98);
      }
    }

    &.ghost {
      background: rgba(255, 255, 255, 0.32);
      color: $color-text-white;
      border: 1rpx solid rgba(255, 255, 255, 0.5);

      &:active {
        background: rgba(255, 255, 255, 0.42);
        transform: scale(0.98);
      }
    }
  }

  .zone-grid {
    display: flex;
    gap: $spacing-md;
    margin-top: $spacing-lg;
  }

  .zone-card {
    flex: 1;
    display: flex;
    align-items: center;
    padding: $spacing-lg $spacing-md;
    border-radius: $radius-lg;
    background: $color-bg-card;
    border: 1rpx solid $color-border-lighter;
    box-shadow: $shadow-card;
    transition: all $transition-fast;

    &:active {
      opacity: 0.92;
      transform: scale(0.98);
      box-shadow: $shadow-card-hover;
    }

    &.vip {
      border-color: rgba(230, 162, 60, 0.28);

      .zone-icon {
        background: $gradient-vip;
        box-shadow: 0 4rpx 12rpx rgba(230, 162, 60, 0.32);
      }
      .zone-name {
        color: $color-vip-dark;
      }
    }

    &.free {
      border-color: rgba(7, 193, 96, 0.28);

      .zone-icon {
        background: $gradient-free;
        box-shadow: 0 4rpx 12rpx rgba(7, 193, 96, 0.32);
      }
    }
  }

  .zone-icon {
    flex-shrink: 0;
    width: 72rpx;
    height: 72rpx;
    border-radius: $radius-md;
    color: $color-text-white;
    font-size: 36rpx;
    font-weight: $font-weight-bold;
    text-align: center;
    line-height: 72rpx;
    margin-right: $spacing-sm;
  }

  .zone-main {
    display: flex;
    flex-direction: column;
    min-width: 0;
    flex: 1;
  }

  .zone-name {
    font-size: $font-size-md;
    font-weight: $font-weight-semibold;
    color: $color-text-primary;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .zone-desc {
    margin-top: 4rpx;
    font-size: $font-size-xs;
    color: $color-text-tertiary;
  }

  .zone-arrow {
    flex-shrink: 0;
    font-size: 40rpx;
    color: $color-text-disabled;
  }

  .section {
    margin-top: $spacing-xl;
  }

  .section-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: $spacing-md;
    padding: 0 4rpx;
  }

  .section-title {
    font-size: $font-size-xl;
    font-weight: $font-weight-semibold;
    color: $color-text-primary;
  }

  .section-more {
    font-size: $font-size-sm;
    color: $color-text-tertiary;
  }

  .login-mask {
    background: $color-bg-card;
    border-radius: $radius-lg;
    border: 1rpx solid $color-border-lighter;
    padding: 64rpx $spacing-lg;
    display: flex;
    flex-direction: column;
    align-items: center;
    box-shadow: $shadow-card;
  }

  .login-mask-title {
    font-size: $font-size-md;
    color: $color-text-secondary;
  }

  .login-mask-btn {
    margin-top: $spacing-lg;
    height: $button-height-md;
    line-height: $button-height-md;
    padding: 0 64rpx;
    border-radius: $radius-button;
    background: $gradient-primary;
    color: $color-text-white;
    font-size: $font-size-md;
    font-weight: $font-weight-semibold;
    box-shadow: $shadow-primary;

    &:active {
      opacity: 0.92;
      transform: scale(0.98);
    }
  }
}
</style>
