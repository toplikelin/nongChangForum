<template>
  <el-container class="layout">
    <el-aside width="220px" class="aside">
      <div class="logo">论坛管理后台</div>
      <el-menu :default-active="activeMenu" router class="menu">
        <el-menu-item index="/stats">
          <el-icon><DataAnalysis /></el-icon>
          <span>数据统计</span>
        </el-menu-item>
        <el-menu-item index="/users">
          <el-icon><User /></el-icon>
          <span>账户管理</span>
        </el-menu-item>
        <el-menu-item index="/posts">
          <el-icon><Document /></el-icon>
          <span>发帖管理</span>
        </el-menu-item>
        <el-menu-item index="/logs/operation">
          <el-icon><Tickets /></el-icon>
          <span>操作日志</span>
        </el-menu-item>
        <el-menu-item index="/logs/error">
          <el-icon><WarningFilled /></el-icon>
          <span>错误日志</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <span class="page-title">{{ currentTitle }}</span>
        <div class="right">
          <el-tag type="success" size="small">管理员</el-tag>
          <span class="username">{{ auth.username || 'admin' }}</span>
          <el-button text @click="onLogout">退出</el-button>
        </div>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../store/auth'
import { User, Document, DataAnalysis, Tickets, WarningFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const activeMenu = computed(() => route.path)
const currentTitle = computed(() => route.meta.title || '')

onMounted(() => {
  auth.fetchMe().catch(() => {})
})

async function onLogout() {
  await ElMessageBox.confirm('确定退出登录吗？', '提示', { type: 'warning' })
  auth.logout()
  ElMessage.success('已退出')
  router.push({ name: 'Login' })
}
</script>

<style scoped>
.layout {
  height: 100vh;
}
.aside {
  background: #001529;
  color: #fff;
}
.logo {
  height: 60px;
  line-height: 60px;
  text-align: center;
  color: #fff;
  font-size: 18px;
  font-weight: 600;
  border-bottom: 1px solid #1f2d3d;
}
.menu {
  border-right: none;
  background: #001529;
  color: rgba(255, 255, 255, 0.75);
}
.menu :deep(.el-menu-item) {
  color: rgba(255, 255, 255, 0.75);
}
.menu :deep(.el-menu-item.is-active) {
  background: #07c160;
  color: #fff;
}
.menu :deep(.el-menu-item:hover) {
  background: #1890ff;
  color: #fff;
}
.header {
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #ebeef5;
}
.page-title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}
.right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.username {
  color: #606266;
  font-size: 14px;
}
.main {
  background: #f5f7fa;
}
</style>
