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
        @change="reload"
      />
      <el-input v-model="filters.path" placeholder="触发接口" style="width: 180px; margin-left: 12px" clearable @keyup.enter="reload" />
      <el-input v-model="filters.keyword" placeholder="关键词（错误信息/堆栈）" style="width: 220px; margin-left: 12px" clearable @keyup.enter="reload" />
      <el-button type="primary" :icon="Search" style="margin-left: 12px" @click="reload">查询</el-button>
      <el-button :icon="Refresh" :loading="loading" @click="reload">刷新</el-button>
      <el-button type="success" plain :icon="Download" @click="onExport">导出</el-button>
      <el-button type="danger" plain :icon="Delete" @click="onCleanup">清理过期</el-button>
    </div>

    <el-table :data="items" v-loading="loading" stripe border style="width: 100%">
      <el-table-column type="expand">
        <template #default="{ row }">
          <div class="detail">
            <div class="detail-block">
              <div class="detail-title">错误堆栈</div>
              <pre class="stack">{{ row.stack || '（无）' }}</pre>
            </div>
            <div class="detail-block">
              <div class="detail-title">请求参数</div>
              <pre class="stack">{{ prettyJson(row.params) }}</pre>
            </div>
            <div class="detail-block">
              <div class="detail-title">用户上下文</div>
              <pre class="stack">{{ prettyJson(row.user_context) }}</pre>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="message" label="错误信息" min-width="260" show-overflow-tooltip />
      <el-table-column label="触发接口" min-width="180">
        <template #default="{ row }">
          <el-tag size="small" effect="plain">{{ row.method }}</el-tag>
          <span style="margin-left: 6px">{{ row.path }}</span>
        </template>
      </el-table-column>
      <el-table-column label="用户" width="130">
        <template #default="{ row }">{{ contextLabel(row.user_context) }}</template>
      </el-table-column>
      <el-table-column prop="created_at" label="报错时间" min-width="170" />
    </el-table>

    <div class="pager">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="size"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        background
        @current-change="load"
        @size-change="reload"
      />
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { Search, Refresh, Download, Delete } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listErrorLogs, exportErrorLogs, cleanupLogs } from '../api/admin'

const items = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const loading = ref(false)
const dateRange = ref([])
const filters = reactive({ path: '', keyword: '' })

function buildParams() {
  const params = { page: page.value, size: size.value }
  if (filters.path.trim()) params.path = filters.path.trim()
  if (filters.keyword.trim()) params.keyword = filters.keyword.trim()
  if (dateRange.value?.[0]) params.start = dateRange.value[0]
  if (dateRange.value?.[1]) params.end = dateRange.value[1]
  return params
}

function prettyJson(text) {
  if (!text) return '（无）'
  try {
    return JSON.stringify(JSON.parse(text), null, 2)
  } catch {
    return text
  }
}

function contextLabel(text) {
  if (!text) return '匿名'
  try {
    const ctx = JSON.parse(text)
    if (!ctx) return '匿名'
    return ctx.type === 'admin' ? `管理员 ${ctx.username}` : `${ctx.username}（${ctx.role}）`
  } catch {
    return '匿名'
  }
}

async function load() {
  loading.value = true
  try {
    const res = await listErrorLogs(buildParams())
    items.value = res.items
    total.value = res.total
  } finally {
    loading.value = false
  }
}

function reload() {
  page.value = 1
  load()
}

async function onExport() {
  try {
    const blob = await exportErrorLogs(buildParams())
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `error_logs_${Date.now()}.csv`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e) {
    /* 拦截器已提示 */
  }
}

async function onCleanup() {
  try {
    await ElMessageBox.confirm('将删除超过保留天数的过期日志，确定执行吗？', '清理确认', { type: 'warning' })
    const res = await cleanupLogs()
    ElMessage.success(`已清理：操作日志 ${res.operation_logs_deleted} 条，错误日志 ${res.error_logs_deleted} 条`)
    reload()
  } catch (e) {
    if (e !== 'cancel') {/* ignore */}
  }
}

onMounted(load)
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
.pager {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
.detail {
  padding: 8px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.detail-title {
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}
.stack {
  margin: 0;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 6px;
  font-size: 12px;
  color: #606266;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 240px;
  overflow: auto;
}
</style>
