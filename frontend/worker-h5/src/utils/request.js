// ============================================================
// 城市设施报修 · 维修工端 — Axios 封装
// ============================================================
import axios from 'axios'

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

// 请求拦截器：注入 JWT
request.interceptors.request.use((config) => {
  const token = localStorage.getItem('worker_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：统一错误处理
request.interceptors.response.use(
  (res) => {
    const body = res.data
    if (body.code === 200) return body.data
    if (body.code === 401) {
      localStorage.removeItem('worker_token')
      localStorage.removeItem('worker_user')
      window.location.hash = '#/login'
    }
    return Promise.reject(new Error(body.msg || body.detail || '请求失败'))
  },
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('worker_token')
      localStorage.removeItem('worker_user')
      window.location.hash = '#/login'
    }
    const data = err.response?.data
    const msg = (data && (data.msg || data.detail)) || `网络异常 (${err.response?.status || '未知'})`
    return Promise.reject(new Error(msg))
  },
)

export default request
