// ============================================================
// 城市设施报修 · 市民端 — Axios 封装
// ============================================================
import axios from 'axios'

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 60000,  // 60秒
  headers: { 'Content-Type': 'application/json' },
})

// 请求拦截器：注入 JWT
request.interceptors.request.use((config) => {
  const token = localStorage.getItem('citizen_token')
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
      localStorage.removeItem('citizen_token')
      localStorage.removeItem('citizen_user')
      window.location.hash = '#/login'
    }
    // 后端返回的业务错误（code !== 200），抛出 msg 供页面展示
    return Promise.reject(new Error(body.msg || body.detail || '请求失败'))
  },
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('citizen_token')
      localStorage.removeItem('citizen_user')
      window.location.hash = '#/login'
    }
    // HTTP 错误：优先取后端返回的 msg，其次 HTTP 状态码描述
    const data = err.response?.data
    const msg = (data && (data.msg || data.detail)) || `网络异常 (${err.response?.status || '未知'})`
    return Promise.reject(new Error(msg))
  },
)

export default request
