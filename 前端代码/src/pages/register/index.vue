<template>
  <view class="register-page">
    <view class="header">
      <text class="header-title">创建账号</text>
      <text class="header-subtitle">注册后即可在自由讨论区发帖交流</text>
    </view>

    <view class="form-card">
      <view class="form-item">
        <text class="form-label">账号</text>
        <input
          v-model="username"
          class="form-input"
          type="text"
          maxlength="20"
          placeholder="3-20位字母、数字、下划线或中文"
          placeholder-class="placeholder"
        />
      </view>
      <view class="form-item">
        <text class="form-label">密码</text>
        <input
          v-model="password"
          class="form-input"
          :password="true"
          maxlength="64"
          placeholder="至少 6 位"
          placeholder-class="placeholder"
        />
      </view>
      <view class="form-item">
        <text class="form-label">确认密码</text>
        <input
          v-model="confirmPassword"
          class="form-input"
          :password="true"
          maxlength="64"
          placeholder="请再次输入密码"
          placeholder-class="placeholder"
          @confirm="onSubmit"
        />
      </view>

      <view class="role-notice">
        <text class="role-notice-text">注册成功默认为「普通用户」，VIP 收购区仅 VIP 用户可发帖</text>
      </view>

      <button class="submit-btn" :loading="loading" @click="onSubmit">注 册</button>

      <view class="login-entry" @click="goLogin">
        <text class="login-entry-text">已有账号？</text>
        <text class="login-entry-link">返回登录</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Taro from '@tarojs/taro'
import { authApi } from '@/services/auth'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const username = ref('')
const password = ref('')
const confirmPassword = ref('')
const loading = ref(false)

async function onSubmit(): Promise<void> {
  if (loading.value) return
  const name = username.value.trim()

  if (name.length < 3 || name.length > 20) {
    Taro.showToast({ title: '账号需 3-20 个字符', icon: 'none' })
    return
  }
  if (password.value.length < 6) {
    Taro.showToast({ title: '密码至少 6 位', icon: 'none' })
    return
  }
  if (password.value !== confirmPassword.value) {
    Taro.showToast({ title: '两次输入的密码不一致', icon: 'none' })
    return
  }

  loading.value = true
  try {
    // 注册成功后端直接签发 token，自动登录
    const res = await authApi.register(name, password.value)
    console.info('[Auth] register success:', res.user.username, res.user.role)
    userStore.setAuth(res.token, res.user)
    Taro.showToast({ title: '注册成功', icon: 'success' })
    setTimeout(() => {
      Taro.switchTab({ url: '/pages/home/index' })
    }, 500)
  } catch (err) {
    console.error('[Auth] register failed:', err)
  } finally {
    loading.value = false
  }
}

function goLogin(): void {
  Taro.navigateBack({ delta: 1 })
}
</script>

<style lang="scss">
@use '@/styles/variables.scss' as *;

// 小程序不支持 scoped，所有规则嵌套在页面根类内
.register-page {
  min-height: 100vh;
  padding: 0 $page-padding 48rpx;
  background: linear-gradient(180deg, #e8f8ee 0%, $color-bg-page 360rpx);

  .header {
    padding: 64rpx 0 40rpx;
  }

  .header-title {
    display: block;
    font-size: 44rpx;
    font-weight: $font-weight-bold;
    color: $color-text-primary;
  }

  .header-subtitle {
    display: block;
    margin-top: $spacing-xs;
    font-size: $font-size-md;
    color: $color-text-tertiary;
  }

  .form-card {
    background: $color-bg-card;
    border-radius: $radius-xl;
    border: 1rpx solid $color-border-lighter;
    padding: 48rpx $spacing-lg;
    box-shadow: $shadow-card;
  }

  .form-item {
    margin-bottom: $spacing-lg;
  }

  .form-label {
    display: block;
    font-size: $font-size-sm;
    color: $color-text-secondary;
    margin-bottom: $spacing-sm;
    font-weight: $font-weight-medium;
  }

  .form-input {
    width: 100%;
    height: 96rpx;
    padding: 0 $spacing-md;
    background: $color-bg-hover;
    border: 1rpx solid $color-border;
    border-radius: $radius-md;
    font-size: $font-size-lg;
    color: $color-text-primary;
    box-sizing: border-box;
    transition: border-color $transition-fast;
  }

  .role-notice {
    margin-top: $spacing-sm;
    padding: $spacing-md;
    background: $color-vip-bg;
    border-radius: $radius-md;
    border: 1rpx solid rgba(230, 162, 60, 0.32);
  }

  .role-notice-text {
    font-size: $font-size-sm;
    color: $color-vip-dark;
    line-height: $line-height-normal;
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

  .login-entry {
    display: flex;
    align-items: center;
    justify-content: center;
    margin-top: $spacing-lg;
    padding: $spacing-sm 0;
    border-radius: $radius-md;

    &:active {
      background: $color-bg-hover;
    }
  }

  .login-entry-text {
    font-size: $font-size-md;
    color: $color-text-tertiary;
  }

  .login-entry-link {
    font-size: $font-size-md;
    color: $color-primary;
    font-weight: $font-weight-medium;
  }
}
</style>
