import { createRouter, createWebHashHistory } from 'vue-router'
import { useAuthStore } from '../store/auth'

const routes = [
  { path: '/login', name: 'Login', component: () => import('../views/Login.vue') },
  {
    path: '/',
    component: () => import('../views/Layout.vue'),
    redirect: '/users',
    children: [
      { path: 'users', name: 'Users', component: () => import('../views/Users.vue'), meta: { title: '账户管理' } },
      { path: 'posts', name: 'Posts', component: () => import('../views/Posts.vue'), meta: { title: '发帖管理' } },
      { path: 'stats', name: 'Stats', component: () => import('../views/Stats.vue'), meta: { title: '数据统计' } },
      { path: 'logs/operation', name: 'OperationLogs', component: () => import('../views/OperationLogs.vue'), meta: { title: '操作日志' } },
      { path: 'logs/error', name: 'ErrorLogs', component: () => import('../views/ErrorLogs.vue'), meta: { title: '错误日志' } },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.name !== 'Login' && !auth.token) {
    return { name: 'Login' }
  }
  if (to.name === 'Login' && auth.token) {
    return { name: 'Users' }
  }
  return true
})

export default router
