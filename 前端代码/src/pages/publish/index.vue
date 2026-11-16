<template>
  <view class="publish-page">
    <view class="zone-bar">
      <text class="zone-label">发布到</text>
      <text :class="['zone-badge', zone === 'vip' ? 'zone-badge-vip' : 'zone-badge-free']">
        {{ zone === 'vip' ? 'VIP收购区' : '自由讨论区' }}
      </text>
      <text v-if="zone === 'vip' && userStore.isLogin && !userStore.isVip" class="zone-warn">
        （普通用户不可发布）
      </text>
    </view>

    <view class="form-card">
      <view class="form-item">
        <input
          v-model="title"
          class="title-input"
          type="text"
          maxlength="100"
          placeholder="请输入标题（2-100字）"
          placeholder-class="placeholder"
        />
        <text class="char-count">{{ title.length }}/100</text>
      </view>

      <view class="divider" />

      <textarea
        v-model="content"
        class="content-input"
        maxlength="5000"
        placeholder="请输入帖子正文，文明交流..."
        placeholder-class="placeholder"
        :auto-height="false"
      />
      <text class="char-count content-count">{{ content.length }}/5000</text>
    </view>

    <button class="submit-btn" :loading="submitting" @click="onSubmit">发布帖子</button>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Taro, { useLoad } from '@tarojs/taro'
import { useUserStore } from '@/stores/user'
import { postApi } from '@/services/post'
import { wechatQuickLogin } from '@/utils/wechatAuth'
import type { PostItem, ZoneKey } from '@/types'

const userStore = useUserStore()
const zone = ref<ZoneKey>('free')
const title = ref('')
const content = ref('')
const submitting = ref(false)

useLoad((options) => {
  userStore.hydrate()
  const target = (options?.zone === 'vip' ? 'vip' : 'free') as ZoneKey
  zone.value = target

  // 未登录：跳转登录并携带回跳（关键写操作前端守卫，后端同样强制鉴权）
  if (!userStore.isLogin) {
    const redirect = encodeURIComponent(`/pages/publish/index?zone=${target}`)
    Taro.redirectTo({ url: `/pages/login/index?redirect=${redirect}` })
    return
  }
  // 普通用户进入 VIP 发帖页：直接拦截
  if (target === 'vip' && !userStore.isVip) {
    Taro.showModal({
      title: '权限不足',
      content: '普通用户不可在 VIP 收购区发帖',
      showCancel: false,
      success: () => Taro.navigateBack({ delta: 1 }),
    })
  }
})

async function onSubmit(): Promise<void> {
  if (submitting.value) return
  if (!userStore.isLogin) {
    wechatQuickLogin(`/pages/publish/index?zone=${zone.value}`)
    return
  }
  const trimmedTitle = title.value.trim()
  const trimmedContent = content.value.trim()
  if (trimmedTitle.length < 2) {
    Taro.showToast({ title: '标题至少 2 个字', icon: 'none' })
    return
  }
  if (trimmedContent.length < 2) {
    Taro.showToast({ title: '正文至少 2 个字', icon: 'none' })
    return
  }

  submitting.value = true
  try {
    const post: PostItem = await postApi.create(zone.value, trimmedTitle, trimmedContent)
    console.info('[Publish] post created:', post.id, post.zone)
    Taro.showToast({ title: '发布成功', icon: 'success' })
    setTimeout(() => {
      Taro.redirectTo({ url: `/pages/post-detail/index?id=${post.id}` })
    }, 500)
  } catch (err) {
    console.error('[Publish] create post failed:', err)
  } finally {
    submitting.value = false
  }
}
</script>

<style lang="scss">
@use '@/styles/variables.scss' as *;

// 小程序不支持 scoped，所有规则嵌套在页面根类内
.publish-page {
  min-height: 100vh;
  padding: $spacing-md $page-padding 48rpx;

  .zone-bar {
    display: flex;
    align-items: center;
    padding: $spacing-sm 4rpx $spacing-md;
  }

  .zone-label {
    font-size: $font-size-md;
    color: $color-text-secondary;
    margin-right: $spacing-sm;
  }

  .zone-badge {
    height: 40rpx;
    padding: 0 16rpx;
    border-radius: $radius-xs;
    font-size: $font-size-sm;
    line-height: 40rpx;
  }

  .zone-badge-vip {
    color: $color-vip-dark;
    background: $color-vip-bg;
  }

  .zone-badge-free {
    color: $color-primary-dark;
    background: rgba(7, 193, 96, 0.1);
  }

  .zone-warn {
    font-size: $font-size-sm;
    color: $color-error;
    margin-left: $spacing-xs;
  }

  .form-card {
    background: $color-bg-card;
    border-radius: $radius-lg;
    border: 1rpx solid $color-border-lighter;
    padding: $spacing-md $spacing-lg;
    box-shadow: $shadow-card;
  }

  .form-item {
    position: relative;
    padding-bottom: $spacing-md;
  }

  .title-input {
    width: 100%;
    height: 80rpx;
    font-size: $font-size-lg;
    font-weight: $font-weight-semibold;
    color: $color-text-primary;
    padding: 0 0 0 0;
    padding-right: 120rpx;
    box-sizing: border-box;
    border-bottom: 1rpx solid $color-border;
    transition: border-color $transition-fast;
  }

  .char-count {
    position: absolute;
    right: 0;
    bottom: $spacing-md;
    font-size: $font-size-xs;
    color: $color-text-disabled;
  }

  .divider {
    height: 1rpx;
    background: $color-divider;
  }

  .content-input {
    width: 100%;
    height: 480rpx;
    margin-top: $spacing-md;
    padding: $spacing-sm;
    background: $color-bg-hover;
    border: 1rpx solid $color-border;
    border-radius: $radius-md;
    font-size: $font-size-md;
    line-height: $line-height-loose;
    color: $color-text-primary;
    box-sizing: border-box;
    transition: border-color $transition-fast;
  }

  .content-count {
    position: static;
    display: block;
    text-align: right;
    margin-top: $spacing-sm;
  }

  .submit-btn {
    margin-top: $spacing-xl;
    width: 100%;
    height: $button-height-lg;
    line-height: $button-height-lg;
    border-radius: $radius-button;
    background: $gradient-primary;
    color: $color-text-white;
    font-size: $font-size-lg;
    font-weight: $font-weight-semibold;
    border: none;
    box-shadow: $shadow-primary;

    &:active {
      opacity: 0.9;
      transform: scale(0.98);
    }

    &::after {
      border: none;
    }
  }
}
</style>
