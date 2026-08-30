<!--
  城市设施报修 · 维修工端 — 根组件
  重工仪表：工业风底部导航 — 厚钢板 + 铆钉装饰 + 安全橙激活
-->
<template>
  <div class="app-shell">
    <!-- 页面区 -->
    <main class="page-container">
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <!-- 底部 TabBar（非登录页展示） -->
    <nav v-if="showTabbar" class="tabbar">
      <router-link to="/queue" class="tab-item" active-class="tab-active">
        <span class="tab-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <rect x="3" y="3" width="7" height="7" rx="1" />
            <rect x="14" y="3" width="7" height="7" rx="1" />
            <rect x="3" y="14" width="7" height="7" rx="1" />
            <rect x="14" y="14" width="7" height="7" rx="1" />
          </svg>
        </span>
        <span class="tab-label">接单大厅</span>
      </router-link>
      <router-link to="/my-tickets" class="tab-item" active-class="tab-active">
        <span class="tab-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
            <line x1="16" y1="13" x2="8" y2="13" />
            <line x1="16" y1="17" x2="8" y2="17" />
          </svg>
        </span>
        <span class="tab-label">我的工单</span>
      </router-link>
      <router-link to="/home" class="tab-item" active-class="tab-active">
        <span class="tab-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
        </span>
        <span class="tab-label">工作台</span>
      </router-link>
    </nav>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { updateLocation } from '@/api/index'
import { getCurrentPosition, startWatchPosition, stopWatchPosition, getLastPosition } from '@/utils/geolocation'

const route = useRoute()
const showTabbar = computed(() => route.name !== 'Login')

// 维修员实时位置心跳
let heartbeatTimer = null
let watcher = null

// 上报位置
async function reportLocation() {
  if (!localStorage.getItem('worker_token')) return

  try {
    // 优先使用最新定位
    const pos = await getCurrentPosition({
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 5000,
    })
    updateLocation(pos.lng, pos.lat).catch(() => {})
  } catch (e) {
    // 失败时尝试使用最后一次有效位置
    const lastPos = getLastPosition()
    if (lastPos) {
      updateLocation(lastPos.lng, lastPos.lat).catch(() => {})
    }
  }
}

onMounted(() => {
  // 立即定位一次
  reportLocation()

  // 开始持续监听位置变化（更省电，推送式）
  watcher = startWatchPosition((pos) => {
    updateLocation(pos.lng, pos.lat).catch(() => {})
  })

  // 保底：30秒定时上报一次（防止watch失效）
  heartbeatTimer = setInterval(reportLocation, 30000)
})

onUnmounted(() => {
  if (heartbeatTimer) clearInterval(heartbeatTimer)
  if (watcher !== null) stopWatchPosition()
})
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  background: var(--color-bg);
}

.page-container {
  flex: 1;
  padding-bottom: calc(env(safe-area-inset-bottom, 12px) + 72px);
}

/* ── 工业风底部导航 ── */
.tabbar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: var(--z-nav);
  display: flex;
  justify-content: space-around;
  background: var(--color-surface);
  border-top: 2px solid var(--color-border-active);
  padding: 6px 0 calc(env(safe-area-inset-bottom, 0px) + 4px);
  box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.5);
  /* 铆钉装饰 — 左上角 + 右上角 */
  position: relative;
}
.tabbar::before,
.tabbar::after {
  content: '';
  position: absolute;
  top: -3px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-border-active);
  border: 1px solid var(--color-text-dim);
  z-index: 1;
}
.tabbar::before { left: 12px; }
.tabbar::after { right: 12px; }

.tab-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 6px 20px;
  font-size: 11px;
  color: var(--color-text-dim);
  transition: color var(--duration-fast);
  position: relative;
}
.tab-item::after {
  content: '';
  position: absolute;
  top: -8px;
  left: 50%;
  transform: translateX(-50%);
  width: 0;
  height: 2px;
  background: var(--color-primary);
  transition: width var(--duration-normal) var(--ease-out-expo);
}
.tab-active {
  color: var(--color-primary);
}
.tab-active::after {
  width: 24px;
}
.tab-icon {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: color var(--duration-fast);
}
.tab-active .tab-icon {
  filter: drop-shadow(0 0 6px rgba(255, 107, 0, 0.5));
}
.tab-label {
  font-weight: 500;
  letter-spacing: 0.5px;
}

/* ── 页面过渡 ── */
.page-enter-active,
.page-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.page-enter-from {
  opacity: 0;
  transform: translateY(10px);
}
.page-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
