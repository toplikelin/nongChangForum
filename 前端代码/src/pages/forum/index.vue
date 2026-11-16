<template>
  <view class="forum-page">
    <!-- 分区切换 -->
    <view class="segment">
      <view
        :class="['segment-item', zone === 'vip' && 'segment-item-active-vip']"
        @click="switchZone('vip')"
      >
        <text class="segment-text">VIP收购区</text>
      </view>
      <view
        :class="['segment-item', zone === 'free' && 'segment-item-active-free']"
        @click="switchZone('free')"
      >
        <text class="segment-text">自由讨论区</text>
      </view>
    </view>

    <block v-if="userStore.isLogin">
      <!-- 权限提示：普通用户在 VIP 收购区 -->
      <view v-if="zone === 'vip' && !userStore.isVip" class="permission-tip">
        <text class="permission-tip-text">您当前为普通用户，可浏览 VIP 收购区内容，但不可在此发帖</text>
      </view>

      <view class="list">
        <post-card
          v-for="post in posts"
          :key="post.id"
          :post="post"
          @click="openPost"
        />
        <empty-state
          v-if="!loading && posts.length === 0"
          :text="zone === 'vip' ? 'VIP 收购区暂无帖子' : '自由讨论区暂无帖子，快来抢沙发'"
        />
        <view v-if="loading" class="loading-tip"><text>加载中...</text></view>
        <view v-else-if="posts.length > 0 && posts.length >= total" class="loading-tip">
          <text>没有更多了</text>
        </view>
      </view>
    </block>

    <view v-else class="login-mask" @click="goLogin">
      <text class="login-mask-title">登录后查看分区帖子</text>
      <text class="login-mask-btn">微信登录</text>
    </view>

    <!-- 发帖悬浮按钮 -->
    <view class="fab" @click="onPublish">
      <text class="fab-plus">+</text>
      <text class="fab-text">发帖</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import Taro, { useDidShow, usePullDownRefresh, useReachBottom } from '@tarojs/taro'
import { useUserStore } from '@/stores/user'
import { useForumStore } from '@/stores/forum'
import { postApi } from '@/services/post'
import { wechatQuickLogin } from '@/utils/wechatAuth'
import type { PostItem, ZoneKey } from '@/types'
import PostCard from '@/components/PostCard.vue'
import EmptyState from '@/components/EmptyState.vue'

const userStore = useUserStore()
const forumStore = useForumStore()

const zone = ref<ZoneKey>(forumStore.activeZone)
const posts = ref<PostItem[]>([])
const page = ref(1)
const total = ref(0)
const loading = ref(false)
const loadingMore = ref(false)

async function loadList(reset = false): Promise<void> {
  if (!userStore.isLogin) {
    posts.value = []
    return
  }
  if (reset) {
    page.value = 1
    loading.value = true
  } else {
    if (loadingMore.value || posts.value.length >= total.value) return
    loadingMore.value = true
  }

  try {
    const res = await postApi.list({ zone: zone.value, page: page.value, size: 10 })
    total.value = res.total
    posts.value = reset ? res.items : posts.value.concat(res.items)
  } catch (err) {
    console.error('[Forum] load posts failed:', zone.value, err)
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

function switchZone(target: ZoneKey): void {
  if (zone.value === target) return
  zone.value = target
  forumStore.setZone(target)
}

watch(zone, () => {
  if (userStore.isLogin) loadList(true)
})

useDidShow(() => {
  userStore.hydrate()
  // 从首页分区卡片进入时同步选中分区
  if (forumStore.activeZone !== zone.value) {
    zone.value = forumStore.activeZone
  }
  if (userStore.isLogin) {
    loadList(true)
    userStore.refreshMe().catch((err) => console.error('[Forum] refresh me failed:', err))
  } else {
    posts.value = []
  }
})

usePullDownRefresh(async () => {
  try {
    if (userStore.isLogin) await loadList(true)
  } finally {
    Taro.stopPullDownRefresh()
  }
})

useReachBottom(() => {
  if (!userStore.isLogin || posts.value.length >= total.value) return
  page.value += 1
  loadList(false)
})

/** 关键写操作前的登录态 / 角色强校验（后端接口同样强制鉴权） */
function onPublish(): void {
  if (!userStore.isLogin) {
    wechatQuickLogin(`/pages/publish/index?zone=${zone.value}`)
    return
  }
  if (zone.value === 'vip' && !userStore.isVip) {
    Taro.showModal({
      title: '权限不足',
      content: '普通用户不可在 VIP 收购区发帖，仅 VIP1 / VIP2 / VIP3 用户可发布',
      showCancel: false,
      confirmText: '我知道了',
    })
    return
  }
  Taro.navigateTo({ url: `/pages/publish/index?zone=${zone.value}` })
}

function openPost(post: PostItem): void {
  Taro.navigateTo({ url: `/pages/post-detail/index?id=${post.id}` })
}

function goLogin(): void {
  wechatQuickLogin('/pages/forum/index')
}
</script>

<style lang="scss">
@use '@/styles/variables.scss' as *;

// 小程序不支持 scoped，所有规则嵌套在页面根类内
.forum-page {
  min-height: 100vh;
  padding: $spacing-md $page-padding 160rpx;

  .segment {
    display: flex;
    background: $color-bg-hover;
    border-radius: $radius-button;
    padding: 6rpx;
  }

  .segment-item {
    flex: 1;
    height: 72rpx;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: $radius-button;
    transition: all $transition-base;
  }

  .segment-item-active-vip {
    background: $gradient-vip;
    box-shadow: 0 4rpx 12rpx rgba(230, 162, 60, 0.4);

    .segment-text {
      color: $color-text-white;
      font-weight: $font-weight-semibold;
    }
  }

  .segment-item-active-free {
    background: $gradient-free;
    box-shadow: 0 4rpx 12rpx rgba(7, 193, 96, 0.32);

    .segment-text {
      color: $color-text-white;
      font-weight: $font-weight-semibold;
    }
  }

  .segment-text {
    font-size: $font-size-md;
    color: $color-text-secondary;
  }

  .permission-tip {
    margin-top: $spacing-md;
    padding: $spacing-md $spacing-lg;
    background: $color-vip-bg;
    border-radius: $radius-md;
    border: 1rpx solid rgba(201, 147, 46, 0.25);
  }

  .permission-tip-text {
    font-size: $font-size-sm;
    color: $color-vip-dark;
    line-height: $line-height-normal;
  }

  .list {
    margin-top: $spacing-md;
  }

  .loading-tip {
    padding: $spacing-lg 0;
    text-align: center;
    font-size: $font-size-sm;
    color: $color-text-disabled;
  }

  .login-mask {
    margin-top: 96rpx;
    background: $color-bg-card;
    border-radius: $radius-lg;
    border: 1rpx solid $color-border-lighter;
    padding: 80rpx $spacing-lg;
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
  }

  .fab {
    position: fixed;
    right: 40rpx;
    bottom: 64rpx;
    height: 88rpx;
    padding: 0 36rpx;
    border-radius: $radius-button;
    background: $gradient-primary;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 8rpx 24rpx rgba(7, 193, 96, 0.42);
    z-index: 20;
    transition: all $transition-fast;

    &:active {
      opacity: 0.92;
      transform: scale(0.96);
    }
  }

  .fab-plus {
    color: $color-text-white;
    font-size: 40rpx;
    font-weight: $font-weight-light;
    margin-right: 4rpx;
  }

  .fab-text {
    color: $color-text-white;
    font-size: $font-size-md;
    font-weight: $font-weight-semibold;
  }
}
</style>
