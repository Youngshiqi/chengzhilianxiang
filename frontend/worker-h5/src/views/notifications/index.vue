<!--
  城市设施报修 · 维修工端 — 消息通知
-->
<template>
  <div class="notifications-page">
    <!-- 顶栏 -->
    <header class="nav-bar">
      <button class="btn-back" @click="goBack">
        <span class="back-icon">←</span>
      </button>
      <span class="nav-title">消息通知</span>
      <button v-if="unreadCount > 0" class="btn-read-all" @click="handleReadAll">
        全部已读
      </button>
    </header>

    <!-- 加载中 -->
    <div v-if="loading" class="loading-state">
      <div class="load-ring"></div>
      <span>加载中...</span>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!notifications.length" class="empty-state">
      <div class="empty-visual">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
      </div>
      <p class="empty-text">暂无通知</p>
      <p class="empty-desc">有新消息时会在这里显示</p>
    </div>

    <!-- 通知列表 -->
    <div v-else class="notification-list">
      <div
        v-for="item in notifications"
        :key="item._id"
        class="notification-item"
        :class="{ unread: !item.is_read }"
        @click="handleItemClick(item)"
      >
        <!-- 图标 -->
        <div class="item-icon" :class="getIconClass(item.type)">
          <svg v-if="item.type === 'dispatch'" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 11l3 3L22 4" />
            <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
          </svg>
          <svg v-else width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
            <path d="M13.73 21a2 2 0 0 1-3.46 0" />
          </svg>
        </div>

        <!-- 内容 -->
        <div class="item-content">
          <div class="item-header">
            <span class="item-title">{{ item.content?.title || '新通知' }}</span>
            <span class="item-time">{{ formatTime(item.created_at) }}</span>
          </div>
          <p class="item-body">{{ item.content?.body || '' }}</p>
          <div v-if="item.content?.address" class="item-meta">
            <span class="meta-tag">📍 {{ item.content.address }}</span>
            <span v-if="item.content?.emergency_level === 1" class="meta-tag meta-warning">⚠️ 紧急</span>
          </div>
        </div>

        <!-- 未读标识 -->
        <div v-if="!item.is_read" class="item-dot"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getNotifications, markNotificationRead, markAllNotificationsRead } from '@/api/index'

const router = useRouter()
const loading = ref(true)
const notifications = ref([])
const unreadCount = ref(0)

async function fetchNotifications() {
  loading.value = true
  try {
    const data = await getNotifications({ page: 1, page_size: 50 })
    notifications.value = data.notifications || []
    unreadCount.value = data.unread_count || 0
  } catch (e) {
    console.error('通知加载失败:', e)
  } finally {
    loading.value = false
  }
}

function formatTime(timeStr) {
  if (!timeStr) return ''
  const t = new Date(timeStr)
  const now = new Date()
  const diff = now - t

  // 1小时内
  if (diff < 3600000) {
    const mins = Math.floor(diff / 60000)
    return mins <= 1 ? '刚刚' : `${mins}分钟前`
  }
  // 24小时内
  if (diff < 86400000) {
    return `${Math.floor(diff / 3600000)}小时前`
  }
  // 显示日期
  return `${t.getMonth() + 1}/${t.getDate()} ${String(t.getHours()).padStart(2, '0')}:${String(t.getMinutes()).padStart(2, '0')}`
}

function getIconClass(type) {
  if (type === 'dispatch') return 'icon-dispatch'
  return 'icon-default'
}

async function handleItemClick(item) {
  // 标记为已读
  if (!item.is_read) {
    try {
      await markNotificationRead(item._id)
      item.is_read = true
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    } catch (e) {
      console.error('标记已读失败:', e)
    }
  }

  // 如果有关联工单，跳转到工单详情
  if (item.ticket_id) {
    router.push(`/ticket/${item.ticket_id}`)
  }
}

async function handleReadAll() {
  try {
    await markAllNotificationsRead()
    notifications.value.forEach(n => n.is_read = true)
    unreadCount.value = 0
  } catch (e) {
    console.error('全部已读失败:', e)
  }
}

function goBack() {
  router.back()
}

onMounted(fetchNotifications)
</script>

<style scoped>
.notifications-page {
  padding: 0 0 24px;
  max-width: 480px;
  margin: 0 auto;
  min-height: 100vh;
  background: var(--color-bg);
}

/* ── 顶栏 ── */
.nav-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 16px 14px;
  position: sticky;
  top: 0;
  background: var(--color-bg);
  z-index: 10;
}
.btn-back {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color var(--duration-fast), color var(--duration-fast);
}
.btn-back:active {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.back-icon {
  font-size: 20px;
  color: var(--color-text);
  font-family: var(--font-mono);
}
.nav-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--color-text);
}
.btn-read-all {
  padding: 8px 14px;
  border-radius: var(--radius-sm);
  background: var(--color-primary);
  color: #fff;
  border: none;
  font-size: 13px;
  font-weight: 500;
}

/* ── 加载 / 空状态 ── */
.loading-state,
.empty-state {
  text-align: center;
  padding: 80px 16px;
  color: var(--color-text-dim);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  font-size: 13px;
}
.load-ring {
  width: 24px;
  height: 24px;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.empty-visual {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-dim);
  margin-bottom: 8px;
}
.empty-text {
  font-size: 15px;
  color: var(--color-text-secondary);
  margin-bottom: 2px;
}
.empty-desc {
  font-size: 12px;
  color: var(--color-text-dim);
}

/* ── 通知列表 ── */
.notification-list {
  display: flex;
  flex-direction: column;
}
.notification-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px;
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  position: relative;
  transition: background var(--duration-fast);
}
.notification-item:active {
  background: var(--color-border);
}
.notification-item.unread {
  background: rgba(255, 107, 0, 0.05);
}
.notification-item.unread::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--color-primary);
}

.item-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.icon-dispatch {
  background: rgba(255, 107, 0, 0.15);
  color: var(--color-primary);
}
.icon-default {
  background: rgba(41, 121, 255, 0.15);
  color: var(--color-info);
}

.item-content {
  flex: 1;
  min-width: 0;
}
.item-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 4px;
}
.item-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text);
  flex: 1;
}
.item-time {
  font-size: 11px;
  color: var(--color-text-dim);
  flex-shrink: 0;
  font-family: var(--font-mono);
}
.item-body {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-bottom: 6px;
  line-height: 1.5;
}
.item-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.meta-tag {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 4px;
  background: var(--color-border);
  color: var(--color-text-dim);
}
.meta-warning {
  background: rgba(255, 193, 7, 0.15);
  color: var(--color-warning);
  border: 1px solid rgba(255, 193, 7, 0.25);
}

.item-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-primary);
  flex-shrink: 0;
  margin-top: 6px;
}
</style>
