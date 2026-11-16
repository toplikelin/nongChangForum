import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { ZoneKey } from '@/types'

/** 论坛页跨 Tab 传参：首页点击分区卡片后切换到论坛 Tab */
export const useForumStore = defineStore('forum', () => {
  const activeZone = ref<ZoneKey>('vip')

  function setZone(zone: ZoneKey): void {
    activeZone.value = zone
  }

  return { activeZone, setZone }
})
