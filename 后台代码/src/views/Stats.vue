<template>
  <div class="page">
    <div class="toolbar">
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        value-format="YYYY-MM-DD"
        @change="loadAll"
      />
      <el-radio-group v-model="dim" style="margin-left: 12px" @change="loadAll">
        <el-radio-button value="day">按日</el-radio-button>
        <el-radio-button value="week">按周</el-radio-button>
        <el-radio-button value="month">按月</el-radio-button>
      </el-radio-group>
      <el-button type="primary" :icon="Refresh" :loading="loading" style="margin-left: 12px" @click="loadAll">刷新</el-button>
      <el-button type="success" plain :icon="Download" @click="onExport">导出</el-button>
    </div>

    <!-- 核心指标卡片 -->
    <div class="cards" v-loading="loading">
      <div class="card">
        <div class="card-label">发帖总量</div>
        <div class="card-value">{{ overview.total_posts ?? '-' }}</div>
        <div class="card-sub">今日 +{{ overview.today_posts ?? 0 }}</div>
      </div>
      <div class="card">
        <div class="card-label">回复总量</div>
        <div class="card-value green">{{ overview.total_replies ?? '-' }}</div>
        <div class="card-sub">今日 +{{ overview.today_replies ?? 0 }}</div>
      </div>
      <div class="card">
        <div class="card-label">用户总数</div>
        <div class="card-value blue">{{ overview.total_users ?? '-' }}</div>
        <div class="card-sub">全量注册用户</div>
      </div>
      <div class="card">
        <div class="card-label">活跃用户</div>
        <div class="card-value orange">{{ overview.active_users ?? '-' }}</div>
        <div class="card-sub">范围内有发帖/回复</div>
      </div>
    </div>

    <!-- 趋势图 -->
    <div class="panel">
      <div class="panel-title">
        发帖/回复趋势
        <span class="legend">
          <i class="dot" style="background: #07c160"></i>发帖
          <i class="dot" style="background: #1890ff"></i>回复
        </span>
      </div>
      <div v-if="trendItems.length" class="chart-wrap">
        <svg :viewBox="`0 0 ${chartW} ${chartH}`" class="chart" preserveAspectRatio="none">
          <line v-for="i in 4" :key="'g' + i" :x1="padL" :x2="chartW - padR" :y1="gridY(i)" :y2="gridY(i)" stroke="#ebeef5" />
          <polyline :points="linePoints('posts')" fill="none" stroke="#07c160" stroke-width="2" />
          <polyline :points="linePoints('replies')" fill="none" stroke="#1890ff" stroke-width="2" />
          <circle v-for="(p, i) in dotPoints('posts')" :key="'p' + i" :cx="p[0]" :cy="p[1]" r="3" fill="#07c160" />
          <circle v-for="(p, i) in dotPoints('replies')" :key="'r' + i" :cx="p[0]" :cy="p[1]" r="3" fill="#1890ff" />
        </svg>
        <div class="x-labels">
          <span v-for="(item, i) in trendItems" :key="i" v-show="labelVisible(i)" class="x-label">{{ shortLabel(item.label) }}</span>
        </div>
      </div>
      <el-empty v-else description="暂无数据" :image-size="80" />
    </div>

    <div class="two-col">
      <!-- 活跃用户排行 -->
      <div class="panel">
        <div class="panel-title">活跃用户排行</div>
        <div v-if="activeUsers.length" class="rank-list">
          <div v-for="(u, i) in activeUsers" :key="u.id" class="rank-item">
            <span class="rank-no" :class="{ top: i < 3 }">{{ i + 1 }}</span>
            <span class="rank-name">
              {{ u.username }}
              <el-tag v-if="u.role !== 'user'" type="warning" size="small">{{ u.role }}</el-tag>
            </span>
            <div class="rank-bar">
              <div class="rank-bar-inner" :style="{ width: barWidth(u.total) }"></div>
            </div>
            <span class="rank-num">{{ u.total }}</span>
          </div>
        </div>
        <el-empty v-else description="暂无数据" :image-size="80" />
      </div>

      <!-- 活跃度分布 -->
      <div class="panel">
        <div class="panel-title">用户活跃度分布（发帖+回复次数）</div>
        <div class="dist-list">
          <div v-for="d in distribution" :key="d.range" class="dist-item">
            <span class="dist-range">{{ d.range }} 次</span>
            <div class="rank-bar">
              <div class="rank-bar-inner dist" :style="{ width: distWidth(d.count) }"></div>
            </div>
            <span class="rank-num">{{ d.count }} 人</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { Refresh, Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { statsOverview, statsTrend, statsActiveUsers, statsActivityDistribution, exportStats } from '../api/admin'

const loading = ref(false)
const dateRange = ref([])
const dim = ref('day')

const overview = ref({})
const trendItems = ref([])
const activeUsers = ref([])
const distribution = ref([])

const chartW = 800
const chartH = 240
const padL = 40
const padR = 20
const padT = 16
const padB = 16

const maxValue = computed(() =>
  Math.max(1, ...trendItems.value.map((t) => Math.max(t.posts, t.replies)))
)

function gridY(i) {
  return padT + ((chartH - padT - padB) / 4) * i
}

function xAt(i) {
  const n = Math.max(1, trendItems.value.length - 1)
  return padL + ((chartW - padL - padR) / n) * i
}

function yAt(v) {
  return chartH - padB - ((chartH - padT - padB) * v) / maxValue.value
}

function dotPoints(key) {
  return trendItems.value.map((t, i) => [xAt(i), yAt(t[key])])
}

function linePoints(key) {
  return dotPoints(key).map((p) => p.join(',')).join(' ')
}

function labelVisible(i) {
  const n = trendItems.value.length
  if (n <= 12) return true
  return i % Math.ceil(n / 12) === 0
}

function shortLabel(label) {
  // 周标签 2026-W45 → W45，日标签取月-日，月标签取月
  if (label.includes('-W')) return label.split('-')[1]
  const parts = label.split('-')
  return parts.length === 3 ? `${parts[1]}-${parts[2]}` : label
}

function barWidth(total) {
  const max = Math.max(1, ...activeUsers.value.map((u) => u.total))
  return `${Math.round((total / max) * 100)}%`
}

function distWidth(count) {
  const max = Math.max(1, ...distribution.value.map((d) => d.count))
  return `${Math.round((count / max) * 100)}%`
}

function rangeParams() {
  const params = {}
  if (dateRange.value?.[0]) params.start = dateRange.value[0]
  if (dateRange.value?.[1]) params.end = dateRange.value[1]
  return params
}

async function loadAll() {
  loading.value = true
  try {
    const params = rangeParams()
    const [ov, tr, au, dist] = await Promise.all([
      statsOverview(params),
      statsTrend({ ...params, dim: dim.value }),
      statsActiveUsers({ ...params, limit: 10 }),
      statsActivityDistribution(params),
    ])
    overview.value = ov.data
    trendItems.value = tr.data.items
    activeUsers.value = au.data.items
    distribution.value = dist.data.items
  } finally {
    loading.value = false
  }
}

async function onExport() {
  try {
    const blob = await exportStats({ ...rangeParams(), dim: dim.value })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `stats_${dim.value}_${Date.now()}.csv`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e) {
    /* 拦截器已提示 */
  }
}

onMounted(loadAll)
</script>

<style scoped>
.page {
  padding: 16px;
}
.toolbar {
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 0;
}
.cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}
.card {
  background: #fff;
  border-radius: 8px;
  padding: 18px 20px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
}
.card-label {
  font-size: 13px;
  color: #909399;
}
.card-value {
  font-size: 30px;
  font-weight: 700;
  color: #303133;
  margin-top: 6px;
}
.card-value.green {
  color: #07c160;
}
.card-value.blue {
  color: #1890ff;
}
.card-value.orange {
  color: #e6a23c;
}
.card-sub {
  font-size: 12px;
  color: #c0c4cc;
  margin-top: 6px;
}
.panel {
  background: #fff;
  border-radius: 8px;
  padding: 16px 20px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  margin-bottom: 16px;
}
.panel-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.legend {
  font-size: 12px;
  font-weight: 400;
  color: #909399;
  display: flex;
  align-items: center;
  gap: 6px;
}
.dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-left: 10px;
}
.chart-wrap {
  width: 100%;
}
.chart {
  width: 100%;
  height: 240px;
  display: block;
}
.x-labels {
  display: flex;
  justify-content: space-between;
  padding: 4px 20px 0 40px;
}
.x-label {
  font-size: 11px;
  color: #909399;
}
.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.rank-list,
.dist-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.rank-item,
.dist-item {
  display: flex;
  align-items: center;
  gap: 10px;
}
.rank-no {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #f0f2f5;
  color: #909399;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.rank-no.top {
  background: #07c160;
  color: #fff;
}
.rank-name {
  width: 110px;
  font-size: 13px;
  color: #303133;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 4px;
}
.dist-range {
  width: 70px;
  font-size: 13px;
  color: #303133;
  flex-shrink: 0;
}
.rank-bar {
  flex: 1;
  height: 14px;
  background: #f0f2f5;
  border-radius: 7px;
  overflow: hidden;
}
.rank-bar-inner {
  height: 100%;
  background: linear-gradient(90deg, #07c160, #35d07f);
  border-radius: 7px;
  transition: width 0.4s;
}
.rank-bar-inner.dist {
  background: linear-gradient(90deg, #1890ff, #69b1ff);
}
.rank-num {
  width: 48px;
  text-align: right;
  font-size: 13px;
  color: #606266;
  flex-shrink: 0;
}
@media (max-width: 1100px) {
  .cards {
    grid-template-columns: repeat(2, 1fr);
  }
  .two-col {
    grid-template-columns: 1fr;
  }
}
</style>
