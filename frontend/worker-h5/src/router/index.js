// ============================================================
// 城市设施报修 · 维修工端 — 路由配置
// ============================================================
import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/home',
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/index.vue'),
    meta: { title: '维修工登录' },
  },
  {
    path: '/home',
    name: 'Home',
    component: () => import('@/views/home/index.vue'),
    meta: { title: '工作台' },
  },
  {
    path: '/queue',
    name: 'Queue',
    component: () => import('@/views/queue/index.vue'),
    meta: { title: '接单大厅' },
  },
  {
    path: '/ticket/:id',
    name: 'TicketDetail',
    component: () => import('@/views/ticket-detail/index.vue'),
    meta: { title: '工单详情' },
  },
  {
    path: '/complete/:id',
    name: 'Complete',
    component: () => import('@/views/complete/index.vue'),
    meta: { title: '完工闭环' },
  },
  {
    path: '/my-tickets',
    name: 'MyTickets',
    component: () => import('@/views/my-tickets/index.vue'),
    meta: { title: '我的工单' },
  },
  {
    path: '/notifications',
    name: 'Notifications',
    component: () => import('@/views/notifications/index.vue'),
    meta: { title: '消息通知' },
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

// 路由守卫：未登录跳转登录页
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('worker_token')
  if (to.name !== 'Login' && !token) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if (to.name === 'Login' && token) {
    next({ name: 'Home' })
  } else {
    next()
  }
})

export default router
