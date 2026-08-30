// ============================================================
// 城市设施运维指挥中心 — 应用入口
// 设计方向：「混凝土与信号灯」暗色控制舱
// ============================================================

import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './styles/variables.css'
import App from './App.vue'

// ── 路由（懒加载，按需分包）──
const Login = () => import('./views/login/index.vue')
const Dashboard = () => import('./views/dashboard/index.vue')
const Dispatch = () => import('./views/dispatch/index.vue')
const Tickets = () => import('./views/tickets/index.vue')
const Workers = () => import('./views/workers/index.vue')
const Facilities = () => import('./views/facilities/index.vue')
const Settlements = () => import('./views/settlements/index.vue')
const Audit = () => import('./views/audit/index.vue')
const Config = () => import('./views/config/index.vue')

const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/login', component: Login, meta: { title: '登录' } },
  { path: '/dashboard', component: Dashboard, meta: { title: '数据驾驶舱', auth: true } },
  { path: '/dispatch', component: Dispatch, meta: { title: 'GIS工单调度', auth: true } },
  { path: '/tickets', component: Tickets, meta: { title: '工单检索', auth: true } },
  { path: '/workers', component: Workers, meta: { title: '人员管理', auth: true } },
  { path: '/facilities', component: Facilities, meta: { title: '设施档案', auth: true } },
  { path: '/settlements', component: Settlements, meta: { title: '结算审计', auth: true } },
  { path: '/audit', component: Audit, meta: { title: '操作审计', auth: true } },
  { path: '/config', component: Config, meta: { title: '系统配置', auth: true } },
]

const router = createRouter({ history: createWebHashHistory(), routes })

// 简易 JWT 解码（不验证签名，仅提取 payload 用于前端预检）
function decodeTokenPayload(token) {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return null
    return JSON.parse(atob(parts[1]))
  } catch { return null }
}

// 路由守卫：Token 有效性预检 + 未登录重定向
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('admin_token')
  if (to.meta.auth) {
    if (!token) {
      return next('/login')
    }
    // 预检 Token 是否过期
    const payload = decodeTokenPayload(token)
    if (!payload || !payload.exp || payload.exp * 1000 < Date.now()) {
      localStorage.removeItem('admin_token')
      localStorage.removeItem('admin_user')
      return next('/login')
    }
  }
  if (to.path === '/login' && token) {
    const payload = decodeTokenPayload(token)
    if (payload && payload.exp && payload.exp * 1000 > Date.now()) {
      return next('/dashboard')
    }
  }
  next()
})

const app = createApp(App)
app.use(router)
app.use(createPinia())
app.use(ElementPlus)
app.mount('#app')
