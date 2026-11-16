import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { TaroElement } from '@tarojs/runtime'
import './app.scss'
import { useUserStore } from './stores/user'

// 兼容修复：Vue 3.5 的 v-model 在 beforeUpdate 中调用 el.getRootNode()，
// 小程序环境的 Taro DOM 元素未实现该方法，会导致 v-model 输入框更新时报错
const g = globalThis as any
if (typeof g.Document === 'undefined') g.Document = class Document {}
if (typeof g.ShadowRoot === 'undefined') g.ShadowRoot = class ShadowRoot {}
if (!(TaroElement.prototype as any).getRootNode) {
  ;(TaroElement.prototype as any).getRootNode = function () {
    return null
  }
}

const App = createApp({
  onLaunch() {
    // 启动时从本地存储恢复登录态
    const userStore = useUserStore()
    userStore.hydrate()
    console.info('[App] launched, login status:', userStore.isLogin)
  },
  onShow() {},
  onHide() {},
})

App.use(createPinia())

export default App
