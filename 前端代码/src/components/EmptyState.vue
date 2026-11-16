<template>
  <view class="empty">
    <view v-if="icon" class="empty-icon">
      <text class="empty-icon-text">{{ icon }}</text>
    </view>
    <text class="empty-text">{{ text }}</text>
  </view>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ text?: string; icon?: string }>(), {
  text: '暂无内容',
  icon: '',
})
</script>

<style lang="scss">
@use '@/styles/variables.scss' as *;

// 全局组件样式，规则嵌套在根类 .empty 内
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 96rpx 0;

  .empty-icon {
    width: 120rpx;
    height: 120rpx;
    border-radius: $radius-round;
    background: $color-bg-hover;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: $spacing-md;
  }

  .empty-icon-text {
    font-size: 52rpx;
  }

  .empty-text {
    font-size: $font-size-md;
    color: $color-text-tertiary;
  }
}
</style>
