<template>
  <view class="login-page">
    <view class="hero">
      <text class="hero-logo">论</text>
      <text class="hero-title">交易论坛</text>
      <text class="hero-subtitle">登录后畅聊两大分区</text>
    </view>

    <view class="form-card">
      <view class="form-item">
        <text class="form-label">账号</text>
        <input
          v-model="username"
          class="form-input"
          type="text"
          maxlength="20"
          placeholder="请输入账号"
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
          placeholder="请输入密码"
          placeholder-class="placeholder"
          @confirm="onSubmit"
        />
      </view>

      <button class="submit-btn" :loading="loading" @click="onSubmit">登 录</button>

      <view class="divider">
        <view class="divider-line"></view>
        <text class="divider-text">或</text>
        <view class="divider-line"></view>
      </view>

      <view class="wechat-btn" :class="{ loading: wechatLoading }" @click="onWechatLogin">
        <text class="wechat-icon">微</text>
        <text>微信一键登录</text>
      </view>
    </view>

    <view class="tips">
      <text class="tips-text">微信一键登录通过 openid 识别身份；也可使用账号密码直接登录</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Taro, { useLoad } from '@tarojs/taro'
import { authApi } from '@/services/auth'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const username = ref('')
const password = ref('')
const loading = ref(false)
const wechatLoading = ref(false)
const redirect = ref('')

useLoad((options) => {
  redirect.value = options?.redirect ? decodeURIComponent(options.redirect) : ''
})

const TAB_PATHS = ['/pages/home/index', '/pages/forum/index', '/pages/mine/index']

function navigateAfterAuth(): void {
  const target = redirect.value
  if (target) {
    if (TAB_PATHS.includes(target.split('?')[0])) {
      Taro.switchTab({ url: target.split('?')[0] })
    } else {
      Taro.redirectTo({ url: target })
    }
    return
  }
  Taro.switchTab({ url: '/pages/home/index' })
}

async function onSubmit(): Promise<void> {
  if (loading.value) return
  const name = username.value.trim()
  const pwd = password.value
  if (!name) {
    Taro.showToast({ title: '请输入账号', icon: 'none' })
    return
  }
  if (!pwd) {
    Taro.showToast({ title: '请输入密码', icon: 'none' })
    return
  }

  loading.value = true
  try {
    const res = await authApi.login(name, pwd)
    console.info('[Auth] login success:', res.user.username, res.user.role)
    userStore.setAuth(res.token, res.user)
    Taro.showToast({ title: '登录成功', icon: 'success' })
    setTimeout(navigateAfterAuth, 400)
  } catch (err) {
    console.error('[Auth] login failed:', err)
  } finally {
    loading.value = false
  }
}

/** 微信一键登录流程：
 * 1. 先弹出自定义的用户须知+免责声明弹窗（微信最新隐私规则下的标准做法）
 * 2. 用户确认后，静默调 wx.login() 拿 code
 * 3. 用 code 换 openid → 后端自动登录/注册
 * 注：wx.login() 本身是静默的，不触发任何原生授权弹窗。
 */
async function onWechatLogin(): Promise<void> {
  if (wechatLoading.value) return
  console.info('[Login] wechat login button clicked')

  // 第一步：用户须知 + 免责声明弹窗
  try {
    const content = [
      '1. 点击「同意并登录」即表示您已阅读并同意平台服务协议与隐私政策。',
      '',
      '2. 平台仅作为信息发布载体，用户在交流中产生的纠纷、交易风险及法律责任由当事人自行承担。',
      '',
      '3. 严禁发布违法违规内容，违者平台有权封禁账号并移交相关部门。',
      '',
      '4. 本平台提供的信息仅供参考，不构成任何投资、交易或履约承诺。',
    ].join('\n')
    const modal = await Taro.showModal({
      title: '用户须知与免责声明',
      content,
      confirmText: '同意',
      cancelText: '拒绝',
    })
    console.info('[Login] modal result:', modal)
    if (!modal.confirm) {
      return
    }
  } catch (e) {
    console.error('[Login] showModal failed:', e)
    return
  }

  wechatLoading.value = true
  try {
    // 第二步：wx.login 静默拿 code（这一步不触发任何微信原生弹窗）
    const loginRes = await Taro.login()
    if (!loginRes.code) {
      Taro.showToast({ title: '登录失败，请重试', icon: 'none' })
      return
    }

    // 第三步：后端换 openid + 自动登录/注册
    const res = await authApi.wechatLogin(loginRes.code)
    userStore.setAuth(res.token, res.user)
    Taro.showToast({
      title: res.is_new_user ? '登录成功，欢迎加入！' : '登录成功',
      icon: 'success',
    })
    setTimeout(navigateAfterAuth, 400)
  } catch (err) {
    console.error('[Auth] wechat login failed:', err)
  } finally {
    wechatLoading.value = false
  }
}
</script>

<style lang="scss">
@use '@/styles/variables.scss' as *;

// 小程序不支持 scoped，所有规则嵌套在页面根类内做命名空间隔离
.login-page {
  min-height: 100vh;
  padding: 0 $page-padding 48rpx;
  background: linear-gradient(180deg, #e8f8ee 0%, $color-bg-page 420rpx);

  .hero {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 96rpx 0 56rpx;
  }

  .hero-logo {
    width: 128rpx;
    height: 128rpx;
    border-radius: $radius-xl;
    background: $gradient-primary;
    color: $color-text-white;
    font-size: 64rpx;
    font-weight: $font-weight-bold;
    text-align: center;
    line-height: 128rpx;
    box-shadow: 0 8rpx 24rpx rgba(7, 193, 96, 0.4);
  }

  .hero-title {
    margin-top: $spacing-lg;
    font-size: 44rpx;
    font-weight: $font-weight-bold;
    color: $color-text-primary;
  }

  .hero-subtitle {
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

  .divider {
    margin-top: $spacing-lg;
    margin-bottom: $spacing-md;
    display: flex;
    align-items: center;
    gap: $spacing-md;
  }

  .divider-line {
    flex: 1;
    height: 1rpx;
    background: $color-border;
  }

  .divider-text {
    font-size: $font-size-sm;
    color: $color-text-tertiary;
  }

  .wechat-btn {
    width: 100%;
    height: $button-height-lg;
    border-radius: $radius-button;
    background: #07c160;
    color: $color-text-white;
    font-size: $font-size-lg;
    font-weight: $font-weight-semibold;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12rpx;
    box-sizing: border-box;

    &:active {
      opacity: 0.9;
    }

    &.loading {
      opacity: 0.7;
      pointer-events: none;
    }
  }

  .wechat-icon {
    width: 44rpx;
    height: 44rpx;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.25);
    font-size: 26rpx;
    line-height: 44rpx;
    text-align: center;
    font-weight: $font-weight-bold;
  }

  .register-entry {
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

  .register-entry-text {
    font-size: $font-size-md;
    color: $color-text-tertiary;
  }

  .register-entry-link {
    font-size: $font-size-md;
    color: $color-primary;
    font-weight: $font-weight-medium;
  }

  .tips {
    margin-top: $spacing-xl;
    padding: $spacing-md $spacing-sm;
    background: $color-primary-bg;
    border-radius: $radius-md;
  }

  .tips-text {
    font-size: $font-size-sm;
    color: $color-primary-dark;
    text-align: center;
    line-height: $line-height-normal;
  }
}
</style>
