import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../store/auth'
import router from '../router'

const request = axios.create({
  baseURL: '/admin/api',
  timeout: 10000,
})

request.interceptors.request.use((config) => {
  const auth = useAuthStore()
  if (auth.token) {
    config.headers.Authorization = `Bearer ${auth.token}`
  }
  return config
})

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const status = error.response?.status
    const detail = error.response?.data?.detail || '请求失败'

    if (status === 401) {
      const auth = useAuthStore()
      auth.logout()
      ElMessage.error('登录已失效，请重新登录')
      router.push({ name: 'Login' })
    } else {
      ElMessage.error(detail)
    }
    return Promise.reject(error)
  }
)

export default request
