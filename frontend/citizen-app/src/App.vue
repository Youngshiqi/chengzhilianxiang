<!--
  城市设施报修 · 市民端 — 根布局
  霓虹混凝土：浮动玻璃态底栏 + 极简顶栏 + 页面过渡
-->
<template>
  <div class="app-shell">
    <!-- 极简顶栏 -->
    <header v-if="showHeader" class="app-header">
      <button v-if="showBack" class="btn-back" @click="$router.back()">
        <span class="back-arrow">←</span>
      </button>
      <div class="header-brand">
        <span class="brand-dot"></span>
        <span class="brand-name mono">CityRepair</span>
      </div>
      <button class="btn-logout" @click="handleLogout" title="退出登录">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
          <polyline points="16 17 21 12 16 7" />
          <line x1="21" y1="12" x2="9" y2="12" />
        </svg>
      </button>
    </header>

    <!-- 主内容区 -->
    <main class="app-main" :class="{ 'has-header': showHeader, 'has-tabbar': showTabbar }">
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <!-- 浮动玻璃态底栏 -->
    <nav v-if="showTabbar" class="tabbar-shell">
      <div class="tabbar">
        <router-link to="/home" class="tab" active-class="tab--active">
          <span class="tab-glyph">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><polyline points="9 22 9 12 15 12 15 22" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </span>
          <span class="tab-label">报修</span>
        </router-link>
        <router-link to="/my-tickets" class="tab" active-class="tab--active">
          <span class="tab-glyph">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><rect x="3" y="3" width="18" height="18" rx="3" stroke="currentColor" stroke-width="1.5"/><line x1="3" y1="9" x2="21" y2="9" stroke="currentColor" stroke-width="1.5"/><line x1="8" y1="3" x2="8" y2="9" stroke="currentColor" stroke-width="1.5"/><circle cx="8" cy="14" r="1.5" fill="currentColor" stroke="none"/><circle cx="13" cy="14" r="1.5" fill="currentColor" stroke="none"/></svg>
          </span>
          <span class="tab-label">工单</span>
        </router-link>
      </div>
    </nav>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useUserStore } from '@/store'

const route = useRoute()
const userStore = useUserStore()

const showHeader = computed(() =>
  !['Login', 'Register'].includes(route.name)
)
const showBack = computed(() =>
  !['Home', 'MyTickets'].includes(route.name)
)
const showTabbar = computed(() =>
  ['Home', 'MyTickets'].includes(route.name)
)

function handleLogout() {
  userStore.logout()
}
</script>

<style scoped>
/* ── 外壳 ── */
.app-shell {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  min-height: 100dvh;
  position: relative;
}

/* ── 极简顶栏 ── */
.app-header {
  height: var(--header-height);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(13, 15, 20, 0.85);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

.btn-back {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-full);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-secondary);
  transition: all var(--duration-fast);
}
.btn-back:active {
  border-color: var(--color-amber);
  color: var(--color-amber);
  background: var(--color-amber-dim);
}
.back-arrow {
  font-size: 16px;
  font-family: var(--font-mono);
}

.header-brand {
  display: flex;
  align-items: center;
  gap: 8px;
}
.brand-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-amber);
  box-shadow: var(--color-amber-glow);
  animation: breathe 2s ease-in-out infinite;
}
@keyframes breathe {
  0%, 100% { opacity: 1; box-shadow: 0 0 8px rgba(255,137,34,0.6); }
  50% { opacity: 0.5; box-shadow: 0 0 2px rgba(255,137,34,0.2); }
}
.brand-name {
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 3px;
  color: var(--color-text);
}

.btn-logout {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-full);
  background: transparent;
  border: 1px solid transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-dim);
  transition: all var(--duration-fast);
}
.btn-logout:hover {
  color: var(--color-red);
  border-color: rgba(255, 68, 68, 0.25);
  background: var(--color-red-dim);
}
.btn-logout:active {
  transform: scale(0.92);
}

/* ── 主内容 ── */
.app-main {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}
.app-main.has-header {
  padding-top: 0;
}
.app-main.has-tabbar {
  padding-bottom: calc(var(--tabbar-height) + 16px + var(--safe-bottom));
}

/* ── 浮动玻璃态底栏 ── */
.tabbar-shell {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 100;
  display: flex;
  justify-content: center;
  padding: 0 24px calc(12px + var(--safe-bottom));
  pointer-events: none;
}

.tabbar {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px;
  border-radius: var(--radius-xl);
  background: rgba(26, 29, 41, 0.85);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  border: 1px solid rgba(255, 255, 255, 0.06);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5), 0 1px 0 rgba(255, 255, 255, 0.04) inset;
  pointer-events: auto;
}

.tab {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 8px 22px;
  border-radius: var(--radius-lg);
  color: var(--color-text-dim);
  font-size: 10px;
  font-weight: 500;
  letter-spacing: 0.5px;
  transition: all var(--duration-normal) var(--ease-out-expo);
  position: relative;
}

.tab--active {
  color: var(--color-amber);
  background: var(--color-amber-dim);
}

.tab--active::after {
  content: '';
  position: absolute;
  bottom: -2px;
  width: 20px;
  height: 2px;
  border-radius: 1px;
  background: var(--color-amber);
  box-shadow: var(--color-amber-glow);
}

.tab-glyph {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform var(--duration-fast) var(--ease-spring);
}
.tab:active .tab-glyph {
  transform: scale(0.85);
}

.tab-label {
  font-family: var(--font-body);
  font-weight: 500;
}

/* ── 页面过渡 ── */
.page-enter-active {
  transition: opacity 0.3s ease, transform 0.3s var(--ease-out-expo);
}
.page-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.page-enter-from {
  opacity: 0;
  transform: translateY(10px) scale(0.98);
}
.page-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
