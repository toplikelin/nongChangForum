import request from './request'

// 认证
export const login = (username, password) =>
  request.post('/auth/login', { username, password })

export const me = () => request.get('/auth/me')

// 账户管理
export const listUsers = () => request.get('/users')

export const setUserStatus = (id, status) =>
  request.patch(`/users/${id}/status`, { status })

export const setUserRole = (id, role) =>
  request.patch(`/users/${id}/role`, { role })

// 发帖管理
export const listPosts = (params) => request.get('/posts', { params })

export const listReplies = (postId) => request.get(`/posts/${postId}/replies`)

export const deletePost = (id) => request.delete(`/posts/${id}`)

export const deleteReply = (id) => request.delete(`/replies/${id}`)

// 操作日志
export const listOperationLogs = (params) => request.get('/logs/operations', { params })

export const exportOperationLogs = (params) =>
  request.get('/logs/operations/export', { params, responseType: 'blob' })

// 错误日志
export const listErrorLogs = (params) => request.get('/logs/errors', { params })

export const exportErrorLogs = (params) =>
  request.get('/logs/errors/export', { params, responseType: 'blob' })

// 日志清理
export const cleanupLogs = () => request.post('/logs/cleanup')

// 数据统计
export const statsOverview = (params) => request.get('/stats/overview', { params })

export const statsTrend = (params) => request.get('/stats/trend', { params })

export const statsActiveUsers = (params) => request.get('/stats/active-users', { params })

export const statsActivityDistribution = (params) =>
  request.get('/stats/activity-distribution', { params })

export const exportStats = (params) =>
  request.get('/stats/export', { params, responseType: 'blob' })
