// ============================================================
// 城市设施运维指挥中心 — Axios 请求实例
// JWT 拦截器 + 统一错误处理
// ============================================================

import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
})

// 请求拦截：自动附加 JWT Token
request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('admin_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截：统一错误处理
request.interceptors.response.use(
  (response) => {
    const data = response.data
    if (data.code !== 200) {
      ElMessage.error(data.msg || '请求失败')
      if (data.code === 401) {
        localStorage.removeItem('admin_token')
        window.location.hash = '#/login'
      }
      return Promise.reject(new Error(data.msg))
    }
    return data
  },
  (error) => {
    ElMessage.error(error.message || '网络异常')
    return Promise.reject(error)
  }
)

export default request
