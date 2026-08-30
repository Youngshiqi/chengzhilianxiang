// ============================================================
// 城市设施报修 · 市民端 — Pinia 全局状态
// ============================================================
import { defineStore } from 'pinia'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: '',
    userId: '',
    nickname: '',
    role: 'citizen',
    points: 0,
  }),

  actions: {
    checkLogin() {
      const token = localStorage.getItem('citizen_token')
      if (token) {
        this.token = token
        const user = localStorage.getItem('citizen_user')
        if (user) {
          try {
            const data = JSON.parse(user)
            this.userId = data.user_id || ''
            this.nickname = data.nickname || ''
            this.role = data.role || 'citizen'
          } catch {}
        }
      }
    },

    setLogin(data) {
      this.token = data.token || ''
      this.userId = data.user_id || ''
      this.nickname = data.nickname || ''
      this.role = data.role || 'citizen'
      localStorage.setItem('citizen_token', this.token)
      localStorage.setItem('citizen_user', JSON.stringify(data))
    },

    logout() {
      this.token = ''
      this.userId = ''
      this.nickname = ''
      this.role = 'citizen'
      localStorage.removeItem('citizen_token')
      localStorage.removeItem('citizen_user')
      window.location.hash = '#/login'
    },
  },
})
