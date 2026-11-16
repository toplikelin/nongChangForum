<template>
  <text :class="['role-tag', isVip ? 'role-tag-vip' : 'role-tag-user']">
    {{ text }}
  </text>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { isVipRole, roleText } from '@/utils/format'
import type { Role } from '@/types'

const props = defineProps<{ role?: Role | string }>()

const isVip = computed(() => isVipRole(props.role))
const text = computed(() => roleText(props.role))
</script>

<style lang="scss">
@use '@/styles/variables.scss' as *;

// 全局组件样式，规则嵌套在根类 .role-tag 内
.role-tag {
  display: inline-flex;
  align-items: center;
  height: 34rpx;
  padding: 0 12rpx;
  border-radius: $radius-xs;
  font-size: $font-size-xs;
  line-height: 34rpx;
  white-space: nowrap;

  &.role-tag-user {
    color: $color-text-tertiary;
    background: $color-bg-hover;
  }

  &.role-tag-vip {
    color: $color-vip-dark;
    background: $color-vip-bg;
    border: 1rpx solid rgba(201, 147, 46, 0.35);
  }
}
</style>
