<template>
  <div class="page">
    <div class="toolbar">
      <el-select v-model="zone" placeholder="全部分区" clearable style="width: 160px" @change="loadPosts">
        <el-option label="VIP收购区" value="vip" />
        <el-option label="自由讨论区" value="free" />
      </el-select>
      <el-input
        v-model="keyword"
        placeholder="搜索标题或内容"
        style="width: 240px; margin: 0 12px"
        clearable
        @keyup.enter="loadPosts"
      />
      <el-button type="primary" :icon="Search" @click="loadPosts">搜索</el-button>
      <el-button :icon="Refresh" :loading="loading" @click="loadPosts">刷新</el-button>
    </div>

    <el-table :data="posts" v-loading="loading" stripe border style="width: 100%">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column label="分区" width="110">
        <template #default="{ row }">
          <el-tag :type="row.zone === 'vip' ? 'warning' : 'success'" effect="plain">
            {{ row.zone === 'vip' ? 'VIP区' : '讨论区' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
      <el-table-column label="作者" width="140">
        <template #default="{ row }">
          {{ row.author.username }}
          <el-tag v-if="row.author.role !== 'user'" type="warning" size="small" style="margin-left: 4px">
            {{ row.author.role }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="reply_count" label="回复数" width="90" />
      <el-table-column prop="created_at" label="发布时间" min-width="170" />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="openReplies(row)">回复 ({{ row.reply_count }})</el-button>
          <el-button size="small" type="danger" @click="removePost(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 回复管理对话框 -->
    <el-dialog v-model="replyVisible" title="回复管理" width="720px" top="8vh">
      <div v-if="currentPost" class="post-info">
        <div class="post-title">{{ currentPost.title }}</div>
        <div class="post-meta">{{ currentPost.author.username }} · {{ currentPost.created_at }}</div>
      </div>
      <el-table :data="replies" v-loading="replyLoading" border stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="content" label="内容" min-width="300" show-overflow-tooltip />
        <el-table-column label="作者" width="130">
          <template #default="{ row }">{{ row.author.username }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" min-width="150" />
        <el-table-column label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="danger" @click="removeReply(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { Search, Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listPosts, listReplies, deletePost, deleteReply } from '../api/admin'

const posts = ref([])
const loading = ref(false)
const zone = ref('')
const keyword = ref('')

const replyVisible = ref(false)
const currentPost = ref(null)
const replies = ref([])
const replyLoading = ref(false)

async function loadPosts() {
  loading.value = true
  try {
    const params = {}
    if (zone.value) params.zone = zone.value
    if (keyword.value.trim()) params.keyword = keyword.value.trim()
    const res = await listPosts(params)
    posts.value = res.items
  } finally {
    loading.value = false
  }
}

async function removePost(row) {
  try {
    await ElMessageBox.confirm(
      `确定删除帖子「${row.title}」吗？该帖子下的所有回复也将被删除。`,
      '删除确认',
      { type: 'warning' }
    )
    await deletePost(row.id)
    ElMessage.success('已删除')
    loadPosts()
  } catch (e) {
    if (e !== 'cancel') {/* ignore */}
  }
}

async function openReplies(row) {
  currentPost.value = row
  replyVisible.value = true
  replyLoading.value = true
  try {
    const res = await listReplies(row.id)
    replies.value = res.items
  } finally {
    replyLoading.value = false
  }
}

async function removeReply(row) {
  try {
    await ElMessageBox.confirm('确定删除这条回复吗？', '删除确认', { type: 'warning' })
    await deleteReply(row.id)
    ElMessage.success('已删除')
    // 更新列表与当前帖子回复数
    replies.value = replies.value.filter((r) => r.id !== row.id)
    if (currentPost.value) currentPost.value.reply_count -= 1
    const p = posts.value.find((x) => x.id === currentPost.value?.id)
    if (p) p.reply_count -= 1
  } catch (e) {
    if (e !== 'cancel') {/* ignore */}
  }
}

onMounted(loadPosts)
</script>

<style scoped>
.page {
  padding: 16px;
}
.toolbar {
  margin-bottom: 16px;
  display: flex;
  align-items: center;
}
.post-info {
  margin-bottom: 16px;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 6px;
}
.post-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}
.post-meta {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style>
