// ============================================================
// 城市设施报修 · 市民端 — 路由配置
// ============================================================
import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/login',
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/index.vue'),
    meta: { title: '登录' },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/register/index.vue'),
    meta: { title: '注册' },
  },
  {
    path: '/home',
    name: 'Home',
    component: () => import('@/views/home/index.vue'),
    meta: { title: '报修' },
  },
  {
    path: '/ticket/:id',
    name: 'TicketDetail',
    component: () => import('@/views/ticket-detail/index.vue'),
    meta: { title: '工单进度' },
  },
  {
    path: '/evaluation/:id',
    name: 'Evaluation',
    component: () => import('@/views/evaluation/index.vue'),
    meta: { title: '服务评价' },
  },
  {
    path: '/my-tickets',
    name: 'MyTickets',
    component: () => import('@/views/my-tickets/index.vue'),
    meta: { title: '我的工单' },
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

// 路由守卫：未登录跳转登录页
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('citizen_token')
  if (to.name !== 'Login' && to.name !== 'Register' && !token) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if (to.name === 'Login' && token) {
    next({ name: 'Home' })
  } else {
    next()
  }
})

export default router
