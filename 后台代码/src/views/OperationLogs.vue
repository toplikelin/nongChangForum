<template>
  <div class="page">
    <div class="toolbar">
      <el-input v-model="filters.operator" placeholder="操作人" style="width: 140px" clearable @keyup.enter="reload" />
      <el-select v-model="filters.action" placeholder="操作类型" clearable style="width: 150px; margin-left: 12px" @change="reload">
        <el-option v-for="a in actionOptions" :key="a.key" :label="a.name" :value="a.key" />
      </el-select>
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        value-format="YYYY-MM-DD"
        style="margin-left: 12px"
        @change="reload"
      />
      <el-input v-model="filters.keyword" placeholder="关键词（内容/目标/IP）" style="width: 220px; margin-left: 12px" clearable @keyup.enter="reload" />
      <el-button type="primary" :icon="Search" style="margin-left: 12px" @click="reload">查询</el-button>
      <el-button :icon="Refresh" :loading="loading" @click="reload">刷新</el-button>
      <el-button type="success" plain :icon="Download" @click="onExport">导出</el-button>
    </div>

    <el-table :data="items" v-loading="loading" stripe border style="width: 100%">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="operator" label="操作人" width="110" />
      <el-table-column label="操作类型" width="130">
        <template #default="{ row }">
          <el-tag effect="plain">{{ row.action_name }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="目标" width="130">
        <template #default="{ row }">
          <span v-if="row.target_type">{{ row.target_type }} #{{ row.target_id }}</span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column prop="content" label="操作内容" min-width="280" show-overflow-tooltip />
      <el-table-column label="结果" width="90">
        <template #default="{ row }">
          <el-tag :type="row.result === 'success' ? 'success' : 'danger'" size="small">
            {{ row.result === 'success' ? '成功' : '失败' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="ip" label="IP" width="130" show-overflow-tooltip />
      <el-table-column prop="created_at" label="操作时间" min-width="170" />
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
import { Search, Refresh, Download } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { listOperationLogs, exportOperationLogs } from '../api/admin'

const items = ref([])
const actionOptions = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const loading = ref(false)
const dateRange = ref([])
const filters = reactive({ operator: '', action: '', keyword: '' })

function buildParams() {
  const params = { page: page.value, size: size.value }
  if (filters.operator.trim()) params.operator = filters.operator.trim()
  if (filters.action) params.action = filters.action
  if (filters.keyword.trim()) params.keyword = filters.keyword.trim()
  if (dateRange.value?.[0]) params.start = dateRange.value[0]
  if (dateRange.value?.[1]) params.end = dateRange.value[1]
  return params
}

async function load() {
  loading.value = true
  try {
    const res = await listOperationLogs(buildParams())
    items.value = res.items
    total.value = res.total
    actionOptions.value = res.actions
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
    const blob = await exportOperationLogs(buildParams())
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `operation_logs_${Date.now()}.csv`
    a.click()
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e) {
    /* 拦截器已提示 */
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
</style>
