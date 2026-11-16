<template>
  <div class="page">
    <div class="toolbar">
      <el-button type="primary" :icon="Refresh" :loading="loading" @click="loadUsers">刷新</el-button>
    </div>

    <el-table :data="users" v-loading="loading" stripe border style="width: 100%">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="username" label="账号" min-width="140" />
      <el-table-column label="昵称" min-width="140">
        <template #default="{ row }">
          <span v-if="row.nickname" class="nickname">{{ row.nickname }}</span>
          <span v-else class="muted">-</span>
        </template>
      </el-table-column>
      <el-table-column label="角色" width="140">
        <template #default="{ row }">
          <el-tag :type="roleTagType(row.role)" effect="dark">{{ roleText(row.role) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="row.status === 'active' ? 'success' : 'danger'" effect="plain">
            {{ row.status === 'active' ? '正常' : '已失效' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="微信 openid" min-width="220" show-overflow-tooltip>
        <template #default="{ row }">
          <span v-if="row.openid" class="mono">{{ row.openid }}</span>
          <span v-else class="muted">-</span>
        </template>
      </el-table-column>
      <el-table-column prop="post_count" label="发帖数" width="90" />
      <el-table-column prop="reply_count" label="回复数" width="90" />
      <el-table-column prop="created_at" label="注册时间" min-width="170" />
      <el-table-column label="操作" width="360" fixed="right">
        <template #default="{ row }">
          <el-button
            :type="row.status === 'active' ? 'warning' : 'success'"
            size="small"
            @click="toggleStatus(row)"
          >
            {{ row.status === 'active' ? '失效' : '启用' }}
          </el-button>
          <el-select
            v-model="row.role"
            size="small"
            style="width: 120px; margin-left: 8px"
            @change="(val) => changeRole(row, val)"
          >
            <el-option label="普通用户" value="user" />
            <el-option label="VIP 1" value="vip1" />
            <el-option label="VIP 2" value="vip2" />
            <el-option label="VIP 3" value="vip3" />
          </el-select>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listUsers, setUserStatus, setUserRole } from '../api/admin'

const users = ref([])
const loading = ref(false)

async function loadUsers() {
  loading.value = true
  try {
    const res = await listUsers()
    users.value = res.items
  } finally {
    loading.value = false
  }
}

function roleText(role) {
  return { user: '普通用户', vip1: 'VIP 1', vip2: 'VIP 2', vip3: 'VIP 3' }[role] || role
}

function roleTagType(role) {
  if (role === 'user') return 'info'
  return 'warning'
}

async function toggleStatus(row) {
  const next = row.status === 'active' ? 'disabled' : 'active'
  const text = next === 'disabled' ? '失效' : '启用'
  try {
    await ElMessageBox.confirm(`确定将账号「${row.username}」设为${text}吗？`, '提示', {
      type: 'warning',
    })
    await setUserStatus(row.id, next)
    row.status = next
    ElMessage.success(`已${text}`)
  } catch (e) {
    if (e !== 'cancel') {/* 用户取消无需处理 */}
  }
}

async function changeRole(row, role) {
  try {
    await setUserRole(row.id, role)
    ElMessage.success('角色已更新')
  } catch (e) {
    // 回滚
    loadUsers()
  }
}

onMounted(loadUsers)
</script>

<style scoped>
.page {
  padding: 16px;
}
.toolbar {
  margin-bottom: 16px;
}
.mono {
  font-family: Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  color: #606266;
}
.nickname {
  color: #303133;
}
.muted {
  color: #c0c4cc;
}
</style>
