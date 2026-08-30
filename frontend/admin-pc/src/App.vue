<!--
  城市设施运维指挥中心 — 根布局（响应式）
  断点：≥1200px 完整布局 / <1200px 浮层侧栏 + 汉堡菜单
-->
<template>
  <div class="command-shell" :class="{ 'sidebar-collapsed': collapsed }">
    <!-- 窄屏遮罩：侧栏展开时显示 -->
    <div v-if="!collapsed" class="sidebar-overlay" @click="closeSidebar"></div>

    <!-- 侧边栏 -->
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-icon"><span class="icon-grid">▦</span></div>
        <div class="brand-text">
          <span class="brand-title">CityRepair</span>
          <span class="brand-sub">城市设施运维指挥中心</span>
        </div>
      </div>

      <div class="system-status">
        <div class="status-row">
          <span class="status-dot online"></span>
          <span class="status-label">系统在线</span>
        </div>
        <div class="status-row">
          <span class="status-value mono">{{ nowString }}</span>
        </div>
      </div>

      <nav class="nav-menu">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: isActive(item.path) }"
          @click="onNavClick"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span class="nav-label">{{ item.label }}</span>
          <span v-if="item.badge" class="nav-badge">{{ item.badge }}</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <div class="footer-line mono">CTRL v3.0</div>
        <div class="footer-line mono">{{ workerCount }} ACTIVE</div>
      </div>
    </aside>

    <!-- 主面板 -->
    <main class="main-panel">
      <div class="topbar">
        <div class="topbar-left">
          <button class="hamburger" @click="toggleSidebar" :title="collapsed ? '展开菜单' : '折叠菜单'">
            <span></span><span></span><span></span>
          </button>
          <span class="page-title">{{ currentTitle }}</span>
        </div>
        <div class="topbar-actions">
          <span class="mono muted topbar-info">{{ workerCount }} 名在岗 · 今日 {{ todayCount }} 单</span>
          <button class="logout-btn mono" @click="handleLogout" title="退出登录">退出</button>
        </div>
      </div>
      <div class="content-area">
        <router-view />
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getDashboardRealtime } from '@/api/index'

const route = useRoute()
const router = useRouter()
const nowString = ref('')
const workerCount = ref(0)
const todayCount = ref(0)
const collapsed = ref(window.innerWidth < 1200)
let timer = null
let statusTimer = null
let wasWide = window.innerWidth >= 1200

const onResize = () => {
  const w = window.innerWidth
  const wide = w >= 1200
  if (wide && !wasWide) collapsed.value = false  // 从小屏切回宽屏，展开侧栏
  if (!wide && wasWide) collapsed.value = true   // 从宽屏切到小屏，收起侧栏
  wasWide = wide
}

async function fetchStatus() {
  const token = localStorage.getItem('admin_token')
  if (!token) return
  try {
    const res = await getDashboardRealtime()
    workerCount.value = res.data.online_workers || 0
    todayCount.value = res.data.today_new || 0
  } catch (e) {
    console.error('状态刷新失败:', e)
  }
}

function handleLogout() {
  localStorage.removeItem('admin_token')
  localStorage.removeItem('admin_user')
  router.replace('/login')
}

onMounted(() => {
  updateTime()
  timer = setInterval(updateTime, 1000)
  window.addEventListener('resize', onResize)
  fetchStatus()
  statusTimer = setInterval(fetchStatus, 30000) // 30秒轮询
})
onUnmounted(() => {
  clearInterval(timer)
  clearInterval(statusTimer)
  window.removeEventListener('resize', onResize)
})

const updateTime = () => {
  const d = new Date()
  nowString.value = d.toISOString().replace('T', ' ').slice(0, 19) + ' UTC'
}

const toggleSidebar = () => { collapsed.value = !collapsed.value }
const closeSidebar = () => { collapsed.value = true }
const onNavClick = () => { if (window.innerWidth < 768) collapsed.value = true }

const navItems = [
  { path: '/dashboard', icon: '◈', label: '数据驾驶舱' },
  { path: '/dispatch', icon: '◉', label: 'GIS 调度台', badge: 'LIVE' },
  { path: '/tickets', icon: '▦', label: '工单检索' },
  { path: '/workers', icon: '▤', label: '人员管理' },
  { path: '/facilities', icon: '▥', label: '设施档案' },
  { path: '/settlements', icon: '◎', label: '结算审计' },
  { path: '/audit', icon: '◷', label: '操作审计' },
  { path: '/config', icon: '⚙', label: '系统配置' },
]

const isActive = (path) => route.path.startsWith(path)
const currentTitle = computed(() => {
  const item = navItems.find(i => route.path.startsWith(i.path))
  return item ? item.label : '指挥中心'
})
</script>

<style>
/* ── 断点变量 ── */
:root {
  --bp-md: 768px;
  --bp-lg: 1200px;
}

/* ── 指挥舱外壳 ── */
.command-shell {
  display: flex;
  height: 100vh;
  background: var(--bg-base);
  overflow: hidden;
}

/* ── 侧边栏 ── */
.sidebar {
  width: var(--sidebar-width);
  flex-shrink: 0;
  background: linear-gradient(180deg, #14161c 0%, var(--bg-elevated) 100%);
  border-right: 1px solid var(--border-dim);
  display: flex;
  flex-direction: column;
  z-index: 20;
  transition: transform 0.3s var(--ease-out-expo);
}
.sidebar-overlay {
  display: none;
}
@media (max-width: 1199px) {
  .sidebar-overlay {
    display: block;
    position: fixed; inset: 0; background: rgba(0,0,0,.5); z-index: 19;
  }
}

/* 窄屏：侧栏默认隐藏，汉堡按钮切换浮层显隐 */
@media (max-width: 1199px) {
  .sidebar {
    position: fixed; top: 0; left: 0; bottom: 0; z-index: 20;
    transition: transform 0.3s var(--ease-out-expo);
    box-shadow: var(--shadow-elevated);
  }
  .sidebar-collapsed .sidebar {
    transform: translateX(-100%);
    box-shadow: none;
  }
}

.brand {
  display: flex; align-items: center; gap: 12px;
  padding: 20px 20px 16px;
}
.brand-icon {
  width: 42px; height: 42px;
  background: linear-gradient(135deg, var(--signal-amber), #cc5500);
  border-radius: var(--radius-md);
  display: flex; align-items: center; justify-content: center;
  font-size: 22px; color: #fff;
  flex-shrink: 0;
}
.brand-text { display: flex; flex-direction: column; min-width: 0; }
.brand-title {
  font-family: var(--font-mono); font-size: 15px;
  font-weight: 600; color: var(--text-primary); letter-spacing: 1px;
}
.brand-sub {
  font-size: 10px; color: var(--text-muted);
  letter-spacing: 0.5px; margin-top: 2px;
}

.system-status {
  margin: 0 20px 8px; padding: 10px 12px;
  background: var(--bg-base); border-radius: var(--radius-sm);
  border: 1px solid var(--border-dim);
}
.status-row { display: flex; align-items: center; gap: 8px; margin: 2px 0; }
.status-dot { width: 6px; height: 6px; border-radius: 50%; }
.status-dot.online { background: var(--signal-green); box-shadow: 0 0 6px var(--signal-green); }
.status-label { font-size: 12px; color: var(--text-secondary); }
.status-value { font-size: 11px; color: var(--text-muted); }

.nav-menu {
  flex: 1; padding: 8px 10px;
  display: flex; flex-direction: column; gap: 1px;
  overflow-y: auto;
}
.nav-item {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px; border-radius: var(--radius-sm);
  color: var(--text-secondary); text-decoration: none;
  font-size: 13px; transition: all var(--duration-fast) var(--ease-out-expo);
}
.nav-item:hover { background: var(--bg-surface); color: var(--text-primary); }
.nav-item.active {
  background: linear-gradient(90deg, rgba(255,106,0,.12), transparent);
  color: var(--signal-amber); box-shadow: inset 2px 0 0 var(--signal-amber);
}
.nav-icon { font-size: 16px; width: 20px; text-align: center; flex-shrink: 0; }
.nav-label { flex: 1; }
.nav-badge {
  font-family: var(--font-mono); font-size: 9px; font-weight: 700;
  color: var(--bg-base); background: var(--signal-amber);
  padding: 2px 6px; border-radius: 2px;
  letter-spacing: 1px; animation: pulse-badge 2s infinite;
}
@keyframes pulse-badge { 0%,100%{opacity:1} 50%{opacity:.6} }

.sidebar-footer {
  padding: 14px 20px; border-top: 1px solid var(--border-dim);
}
.footer-line { font-size: 10px; color: var(--text-muted); letter-spacing: 1px; }

/* ── 主面板 ── */
.main-panel { flex: 1; display: flex; flex-direction: column; min-width: 0; }

.topbar {
  height: var(--header-height); flex-shrink: 0;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 20px; background: var(--bg-elevated);
  border-bottom: 1px solid var(--border-dim);
}
.topbar-left { display: flex; align-items: center; gap: 14px; }
.page-title {
  font-family: var(--font-mono); font-size: 18px;
  font-weight: 500; letter-spacing: 2px; color: var(--text-primary);
  white-space: nowrap;
}

/* 汉堡按钮 */
.hamburger {
  display: none;
  flex-direction: column; gap: 4px;
  background: none; border: none; cursor: pointer;
  padding: 4px; width: 28px;
}
.hamburger span {
  display: block; height: 2px; background: var(--text-secondary);
  border-radius: 1px; transition: all .2s;
}

.mono { font-family: var(--font-mono); }
.muted { color: var(--text-muted); font-size: 12px; }
.logout-btn {
  margin-left: 16px;
  padding: 4px 14px;
  background: transparent;
  color: var(--text-muted);
  border: 1px solid var(--border-dim);
  border-radius: var(--radius-sm);
  font-size: 11px;
  cursor: pointer;
  transition: all var(--duration-fast);
}
.logout-btn:hover {
  color: var(--signal-red);
  border-color: rgba(255,59,59,.3);
  background: rgba(255,59,59,.08);
}

.content-area {
  flex: 1; overflow-y: auto; overflow-x: hidden;
  padding: 20px;
}

/* ── 响应式 ── */
@media (max-width: 1199px) {
  .hamburger { display: flex; }
  .page-title { font-size: 15px; letter-spacing: 1px; }
  .content-area { padding: 14px; }
  .topbar-info { display: none; }
}
@media (max-width: 767px) {
  .topbar { padding: 0 12px; }
  .content-area { padding: 10px; }
  .page-title { font-size: 14px; }
}
</style>
