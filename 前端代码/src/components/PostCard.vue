<template>
  <view class="pcard" @click="onClick">
    <view class="card-top">
      <text :class="['zone-tag', post.zone === 'vip' ? 'zone-tag-vip' : 'zone-tag-free']">
        {{ post.zone === 'vip' ? 'VIP收购' : '自由讨论' }}
      </text>
      <text class="title">{{ post.title }}</text>
    </view>
    <text class="content">{{ post.content }}</text>
    <view class="card-footer">
      <view class="author">
        <role-tag :role="post.author.role" />
        <text class="author-name">{{ post.author.nickname || post.author.username }}</text>
      </view>
      <view class="meta">
        <text class="time">{{ formatTime(post.created_at) }}</text>
        <text class="reply">回复 {{ post.reply_count }}</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import type { PostItem } from '@/types'
import { formatTime } from '@/utils/format'
import RoleTag from './RoleTag.vue'

const props = defineProps<{ post: PostItem }>()
const emit = defineEmits<{ (e: 'click', post: PostItem): void }>()

function onClick() {
  emit('click', props.post)
}
</script>

<style lang="scss">
@use '@/styles/variables.scss' as *;

// 组件样式全局可用，全部规则嵌套在组件根类 .pcard 内避免污染
.pcard {
  background: $color-bg-card;
  border-radius: $radius-lg;
  border: 1rpx solid $color-border-lighter;
  padding: $spacing-lg;
  margin-bottom: $spacing-md;
  box-shadow: $shadow-card;
  transition: all $transition-fast;

  &:active {
    opacity: 0.9;
    transform: scale(0.99);
  }

  .card-top {
    display: flex;
    align-items: center;
  }

  .zone-tag {
    flex-shrink: 0;
    height: 36rpx;
    padding: 0 12rpx;
    margin-right: $spacing-sm;
    border-radius: $radius-xs;
    font-size: $font-size-xs;
    line-height: 36rpx;
    white-space: nowrap;
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
    flex: 1;
    font-size: $font-size-lg;
    font-weight: $font-weight-semibold;
    color: $color-text-primary;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .content {
    display: -webkit-box;
    margin-top: $spacing-sm;
    font-size: $font-size-md;
    color: $color-text-secondary;
    line-height: $line-height-normal;
    overflow: hidden;
    text-overflow: ellipsis;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
  }

  .card-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: $spacing-md;
  }

  .author {
    display: flex;
    align-items: center;
    min-width: 0;
  }

  .author-name {
    margin-left: $spacing-xs;
    font-size: $font-size-sm;
    color: $color-text-tertiary;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .meta {
    display: flex;
    align-items: center;
    flex-shrink: 0;
  }

  .time,
  .reply {
    font-size: $font-size-sm;
    color: $color-text-tertiary;
  }

  .reply {
    margin-left: $spacing-md;
  }
}
</style>
