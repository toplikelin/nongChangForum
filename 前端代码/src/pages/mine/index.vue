<template>
  <view class="mine-page">
    <!-- 个人信息卡 -->
    <view class="profile-card">
      <block v-if="userStore.isLogin">
        <view class="profile-main">
          <view class="avatar">{{ avatarChar }}</view>
          <view class="profile-info">
            <text class="username">{{ displayName }}</text>
            <view class="role-line">
              <role-tag :role="userStore.role" />
            </view>
          </view>
        </view>
      </block>
      <block v-else>
        <view class="profile-main">
          <view class="avatar avatar-guest">客</view>
          <view class="profile-info">
            <text class="username">未登录</text>
            <text class="login-hint">登录后体验完整论坛功能</text>
          </view>
        </view>
        <view class="guest-actions">
          <button class="guest-btn primary" @click="goLogin">微信登录</button>
        </view>
      </block>
    </view>

    <block v-if="userStore.isLogin">
      <!-- 账号信息 -->
      <view class="info-card">
        <!-- 昵称：支持 inline 编辑 -->
        <view class="info-row">
          <text class="info-label">昵称</text>
          <view class="info-value nickname-cell">
            <template v-if="!editingNickname">
              <text class="nickname-text">{{ userStore.profile?.nickname || '未设置' }}</text>
              <view class="nickname-edit-btn" @click="startEditNickname">修改</view>
            </template>
            <template v-else>
              <input
                class="nickname-input"
                v-model="nicknameDraft"
                maxlength="20"
                placeholder="最多 20 个字符"
                :focus="true"
                @confirm="saveNickname"
              />
              <view class="nickname-action save" @click="saveNickname">保存</view>
              <view class="nickname-action" @click="cancelEditNickname">取消</view>
            </template>
          </view>
        </view>
        <view class="info-row">
          <text class="info-label">账号</text>
          <text class="info-value mono">{{ userStore.profile?.username }}</text>
        </view>
        <view class="info-row">
          <text class="info-label">当前角色</text>
          <text :class="['info-value', userStore.isVip ? 'text-vip' : '']">{{ roleText(userStore.role) }}</text>
        </view>
        <view class="info-row last">
          <text class="info-label">注册时间</text>
          <text class="info-value">{{ formatTime(userStore.profile?.created_at || '') }}</text>
        </view>
      </view>

      <!-- 快捷入口：我的发帖 / 我的回复 -->
      <view class="quick-card">
        <view class="quick-item" @click="goMyActivity('posts')">
          <view class="quick-icon posts">帖</view>
          <view class="quick-info">
            <text class="quick-label">我的发帖</text>
            <text class="quick-desc">查看全部帖子</text>
          </view>
          <text class="quick-arrow">›</text>
        </view>
        <view class="quick-item" @click="goMyActivity('replies')">
          <view class="quick-icon replies">回</view>
          <view class="quick-info">
            <text class="quick-label">我的回复</text>
            <text class="quick-desc">查看全部回复</text>
          </view>
          <text class="quick-arrow">›</text>
        </view>
      </view>

      <!-- 权限说明 -->
      <view class="privilege-card">
        <text class="privilege-title">角色权限说明</text>
        <view class="privilege-row">
          <text class="privilege-dot blue">·</text>
          <text class="privilege-text">普通用户：可在「自由讨论区」发帖、回复</text>
        </view>
        <view class="privilege-row">
          <text class="privilege-dot gold">·</text>
          <text class="privilege-text">VIP1 / VIP2 / VIP3：额外可在「VIP收购区」发布收购信息</text>
        </view>
        <view class="privilege-row">
          <text class="privilege-dot gray">·</text>
          <text class="privilege-text">所有登录用户均可浏览两个分区的内容</text>
        </view>
        <view class="upgrade-tip">
          <text class="upgrade-tip-text">如需升级 VIP 角色，请联系管理员</text>
        </view>
      </view>

      <button class="logout-btn" @click="onLogout">退出登录</button>
    </block>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import Taro, { useDidShow } from '@tarojs/taro'
import { useUserStore } from '@/stores/user'
import { formatTime, roleText } from '@/utils/format'
import { wechatQuickLogin } from '@/utils/wechatAuth'
import RoleTag from '@/components/RoleTag.vue'

const userStore = useUserStore()

/** 展示名优先昵称，空则 fallback 到 username */
const displayName = computed(
  () => userStore.profile?.nickname?.trim() || userStore.profile?.username || '用户'
)

const avatarChar = computed(
  () => displayName.value.slice(0, 1).toUpperCase() || 'U'
)

// ---- 昵称 inline 编辑 ----
const editingNickname = ref(false)
const nicknameDraft = ref('')

function startEditNickname(): void {
  nicknameDraft.value = userStore.profile?.nickname || ''
  editingNickname.value = true
}

function cancelEditNickname(): void {
  editingNickname.value = false
  nicknameDraft.value = ''
}

async function saveNickname(): Promise<void> {
  const trimmed = nicknameDraft.value.trim()
  console.info('[Mine] saveNickname called, draft=', nicknameDraft.value, 'trimmed=', trimmed)
  if (trimmed.length > 20) {
    Taro.showToast({ title: '昵称最多 20 个字符', icon: 'none' })
    return
  }
  try {
    Taro.showLoading({ title: '保存中', mask: true })
    console.info('[Mine] calling userStore.updateNickname...')
    const before = userStore.profile?.nickname
    await userStore.updateNickname(trimmed)
    console.info('[Mine] after update, nickname:', userStore.profile?.nickname, 'before:', before)
    Taro.hideLoading()
    Taro.showToast({ title: '已更新', icon: 'success' })
    cancelEditNickname()
  } catch (err) {
    Taro.hideLoading()
    console.error('[Mine] update nickname failed:', err)
    Taro.showToast({ title: `保存失败：${(err as Error).message || '未知错误'}`, icon: 'none' })
  }
}

useDidShow(() => {
  userStore.hydrate()
  if (userStore.isLogin) {
    userStore.refreshMe().catch((err) => console.error('[Mine] refresh me failed:', err))
  }
})

function goLogin(): void {
  wechatQuickLogin('/pages/mine/index')
}

function goMyActivity(tab: 'posts' | 'replies'): void {
  Taro.navigateTo({ url: `/pages/my-activity/index?tab=${tab}` })
}

function onLogout(): void {
  Taro.showModal({
    title: '提示',
    content: '确定要退出登录吗？',
    success: (res) => {
      if (res.confirm) {
        userStore.logout()
        Taro.showToast({ title: '已退出登录', icon: 'success' })
      }
    },
  })
}
</script>

<style lang="scss">
@use '@/styles/variables.scss' as *;

// 小程序不支持 scoped，所有规则嵌套在页面根类内
.mine-page {
  min-height: 100vh;
  padding: $spacing-md $page-padding 48rpx;

  .profile-card {
    border-radius: $radius-xl;
    padding: 40rpx $spacing-lg;
    background: $gradient-primary;
    box-shadow: 0 8rpx 24rpx rgba(7, 193, 96, 0.32);
  }

  .profile-main {
    display: flex;
    align-items: center;
  }

  .avatar {
    flex-shrink: 0;
    width: 112rpx;
    height: 112rpx;
    border-radius: $radius-round;
    background: rgba(255, 255, 255, 0.24);
    color: $color-text-white;
    font-size: 48rpx;
    font-weight: $font-weight-bold;
    text-align: center;
    line-height: 112rpx;
  }

  .avatar-guest {
    background: rgba(255, 255, 255, 0.16);
  }

  .profile-info {
    margin-left: $spacing-lg;
    display: flex;
    flex-direction: column;
    min-width: 0;
  }

  .username {
    font-size: 40rpx;
    font-weight: $font-weight-bold;
    color: $color-text-white;
  }

  .role-line {
    margin-top: $spacing-sm;
  }

  .login-hint {
    margin-top: $spacing-xs;
    font-size: $font-size-sm;
    color: rgba(255, 255, 255, 0.82);
  }

  .guest-actions {
    display: flex;
    margin-top: $spacing-lg;
    gap: $spacing-lg;
  }

  .guest-btn {
    flex: 1;
    height: $button-height-md;
    line-height: $button-height-md;
    border-radius: $radius-button;
    font-size: $font-size-md;
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

  .info-card {
    margin-top: $spacing-lg;
    background: $color-bg-card;
    border-radius: $radius-lg;
    border: 1rpx solid $color-border-lighter;
    padding: 0 $spacing-lg;
    box-shadow: $shadow-card;
  }

  .quick-card {
    margin-top: $spacing-lg;
    background: $color-bg-card;
    border-radius: $radius-lg;
    border: 1rpx solid $color-border-lighter;
    padding: $spacing-sm $spacing-lg;
    box-shadow: $shadow-card;
  }

  .quick-item {
    display: flex;
    align-items: center;
    padding: 28rpx 0;
    border-bottom: 1rpx solid $color-divider;

    &:last-child {
      border-bottom: none;
    }

    &:active {
      opacity: 0.7;
    }
  }

  .quick-icon {
    flex-shrink: 0;
    width: 72rpx;
    height: 72rpx;
    border-radius: $radius-md;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: $font-size-lg;
    font-weight: $font-weight-bold;
    color: $color-text-white;
    margin-right: $spacing-md;

    &.posts {
      background: $color-primary;
    }
    &.replies {
      background: $color-vip;
    }
  }

  .quick-info {
    flex: 1;
    display: flex;
    flex-direction: column;
  }

  .quick-label {
    font-size: $font-size-md;
    color: $color-text-primary;
    font-weight: $font-weight-medium;
  }

  .quick-desc {
    font-size: $font-size-xs;
    color: $color-text-tertiary;
    margin-top: 4rpx;
  }

  .quick-arrow {
    font-size: 40rpx;
    color: $color-text-tertiary;
  }

  .info-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 104rpx;
    border-bottom: 1rpx solid $color-divider;

    &.last {
      border-bottom: none;
    }
  }

  .info-label {
    font-size: $font-size-md;
    color: $color-text-secondary;
  }

  .info-value {
    font-size: $font-size-md;
    color: $color-text-primary;
    max-width: 420rpx;
    text-align: right;
  }

  .nickname-cell {
    display: flex;
    align-items: center;
    gap: 16rpx;
    max-width: 480rpx;
  }

  .nickname-text {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .nickname-edit-btn {
    flex-shrink: 0;
    font-size: $font-size-sm;
    color: $color-primary;
  }

  .nickname-input {
    flex: 1;
    height: 56rpx;
    padding: 0 16rpx;
    border: 1rpx solid $color-border;
    border-radius: $radius-sm;
    background: $color-bg-page;
    font-size: $font-size-md;
    text-align: right;
  }

  .nickname-action {
    flex-shrink: 0;
    font-size: $font-size-sm;
    color: $color-text-secondary;

    &.save {
      color: $color-primary;
    }
  }

  .mono {
    font-family: Menlo, Monaco, Consolas, monospace;
    font-size: $font-size-sm;
    color: $color-text-secondary;
  }

  .text-vip {
    color: $color-vip-dark;
    font-weight: $font-weight-semibold;
  }

  .privilege-card {
    margin-top: $spacing-lg;
    background: $color-bg-card;
    border-radius: $radius-lg;
    border: 1rpx solid $color-border-lighter;
    padding: $spacing-lg;
    box-shadow: $shadow-card;
  }

  .privilege-title {
    font-size: $font-size-lg;
    font-weight: $font-weight-semibold;
    color: $color-text-primary;
  }

  .privilege-row {
    display: flex;
    align-items: flex-start;
    margin-top: $spacing-md;
  }

  .privilege-dot {
    font-size: $font-size-lg;
    font-weight: $font-weight-bold;
    margin-right: $spacing-sm;
    line-height: $line-height-normal;

    &.blue {
      color: $color-primary;
    }
    &.gold {
      color: $color-vip;
    }
    &.gray {
      color: $color-text-tertiary;
    }
  }

  .privilege-text {
    flex: 1;
    font-size: $font-size-sm;
    color: $color-text-secondary;
    line-height: $line-height-normal;
  }

  .upgrade-tip {
    margin-top: $spacing-md;
    padding: $spacing-sm $spacing-md;
    background: $color-vip-bg;
    border-radius: $radius-sm;
  }

  .upgrade-tip-text {
    font-size: $font-size-sm;
    color: $color-vip-dark;
  }

  .logout-btn {
    margin-top: 48rpx;
    width: 100%;
    height: $button-height-lg;
    line-height: $button-height-lg;
    border-radius: $radius-button;
    background: rgba(245, 108, 108, 0.08);
    color: $color-error;
    font-size: $font-size-lg;
    font-weight: $font-weight-medium;
    border: 1rpx solid rgba(245, 108, 108, 0.4);
    box-shadow: none;
    transition: all $transition-fast;

    &::after {
      border: none;
    }

    &:active {
      background: rgba(245, 108, 108, 0.18);
      transform: scale(0.98);
    }
  }
}
</style>
