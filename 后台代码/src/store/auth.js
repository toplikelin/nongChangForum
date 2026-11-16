import { defineStore } from 'pinia'
import { ref } from 'vue'
import { login as apiLogin, me as apiMe } from '../api/admin'

const TOKEN_KEY = 'admin_token'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem(TOKEN_KEY) || '')
  const username = ref('')

  async function login(name, pwd) {
    const res = await apiLogin(name, pwd)
    token.value = res.token
    localStorage.setItem(TOKEN_KEY, res.token)
    username.value = res.user?.username || 'admin'
  }

  async function fetchMe() {
    try {
      const res = await apiMe()
      username.value = res.username
    } catch (e) {
      logout()
      throw e
    }
  }

  function logout() {
    token.value = ''
    username.value = ''
    localStorage.removeItem(TOKEN_KEY)
  }

  return { token, username, login, fetchMe, logout }
})
