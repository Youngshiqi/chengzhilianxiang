<!--
  城市设施报修 · 维修工端 — 接单大厅
  重工仪表：紧急工单危险条纹 + 距离雷达 + 安全橙一键接单
-->
<template>
  <div class="queue-page">
    <!-- 顶栏 -->
    <header class="nav-bar">
      <span class="nav-title">
        <span class="title-dot"></span>
        接单大厅
      </span>
      <span class="nav-count mono" v-if="orders.length">共 {{ orders.length }} 单</span>
    </header>

    <!-- 加载中 -->
    <div v-if="loading" class="loading-state">
      <div class="load-spinner"></div>
      <span>加载工单中...</span>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!orders.length" class="empty-state">
      <div class="empty-visual">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
          <circle cx="12" cy="12" r="9" />
          <path d="M12 8v4M12 16h.01" />
        </svg>
      </div>
      <p class="empty-text">暂无可接工单</p>
      <p class="empty-hint">当前没有待受理的工单，休息一下吧</p>
    </div>

    <!-- 工单列表 -->
    <div v-else class="order-list">
      <div
        v-for="order in orders"
        :key="order.ticket_id"
        class="order-card"
        :class="{ emergency: order.emergency_level === 1 }"
      >
        <!-- 紧急工单左侧危险条纹 -->
        <div v-if="order.emergency_level === 1" class="hazard-stripe"></div>

        <div class="card-inner">
          <!-- 头部标签 -->
          <div class="card-header">
            <div class="card-tags">
              <span class="tag" :class="order.emergency_level === 1 ? 'tag-emergency' : 'tag-normal'">
                {{ order.emergency_level === 1 ? '紧急' : '普通' }}
              </span>
              <span class="tag tag-type">{{ order.facility_type }}</span>
              <span class="tag" :style="statusStyle(order)">{{ statusLabel(order) }}</span>
            </div>
            <span class="card-distance mono">
              <span class="dist-ping"></span>
              {{ formatDistance(order.distance_meters) }}
            </span>
          </div>

          <!-- 描述 -->
          <p class="card-desc">{{ order.description }}</p>

          <!-- 底部信息 -->
          <div class="card-footer">
            <span class="card-addr">📍 {{ order.address || '位置未知' }}</span>
            <span v-if="order.ai_category" class="card-ai mono">AI: {{ order.ai_category }}</span>
          </div>

          <!-- 操作按钮 -->
          <div class="card-actions">
            <button class="btn-detail" @click="$router.push(`/ticket/${order.ticket_id}`)">
              查看详情
            </button>
            <button
              class="btn-accept"
              :class="{ 'btn-accept--taken': !canAccept(order) }"
              :disabled="acceptingId === order.ticket_id || !canAccept(order)"
              @click="handleAccept(order.ticket_id)"
            >
              <span v-if="acceptingId === order.ticket_id" class="btn-spinner"></span>
              <span v-else-if="canAccept(order)">一键接单</span>
              <span v-else>已被接</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 错误提示 -->
    <div v-if="errorMsg" class="error-toast">
      <span class="error-dot"></span> {{ errorMsg }}
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getTicketQueue, acceptTicket } from '@/api/index'

const router = useRouter()
const orders = ref([])
const loading = ref(true)
const acceptingId = ref(null)
const errorMsg = ref('')

function statusLabel(order) {
  const map = { pending: '待受理', accepting: '派单中', dispatching: '已接单', repairing: '维修中', verifying: '验收中', closed: '已完结' }
  return map[order.status] || order.status || '—'
}

function statusClass(order) {
  if (order.status === 'repairing' || order.status === 'verifying') return 'tag-taken'
  if (order.status === 'dispatching' || order.status === 'accepting') return 'tag-dispatching'
  return 'tag-available'
}

function statusStyle(order) {
  const s = order.status
  if (s === 'repairing' || s === 'verifying') {
    return { background: 'rgba(255,193,7,0.1)', color: '#FFC107', border: '1px solid rgba(255,193,7,0.25)' }
  }
  if (s === 'dispatching' || s === 'accepting') {
    return { background: 'rgba(156,39,176,0.12)', color: '#9c27b0', border: '1px solid rgba(156,39,176,0.25)' }
  }
  return { background: 'rgba(41,121,255,0.12)', color: '#2979FF', border: '1px solid rgba(41,121,255,0.25)' }
}

function canAccept(order) {
  return (order.status === 'pending' || order.status === 'dispatching' || order.status === 'accepting')
}

function formatDistance(m) {
  if (m == null) return '-'
  if (m < 1000) return `${Math.round(m)}m`
  return `${(m / 1000).toFixed(1)}km`
}

async function loadOrders() {
  loading.value = true
  errorMsg.value = ''
  try {
    const data = await getTicketQueue()
    orders.value = Array.isArray(data) ? data : (data?.items || [])
  } catch (e) {
    errorMsg.value = e.message || '加载工单失败'
  } finally {
    loading.value = false
  }
}

async function handleAccept(ticketId) {
  errorMsg.value = ''
  acceptingId.value = ticketId
  try {
    await acceptTicket(ticketId)
    router.push(`/ticket/${ticketId}`)
  } catch (e) {
    errorMsg.value = e.message || '接单失败，请稍后重试'
  } finally {
    acceptingId.value = null
  }
}

onMounted(loadOrders)
</script>

<style scoped>
.queue-page {
  padding: 0 16px 24px;
  max-width: 480px;
  margin: 0 auto;
}

/* ── 顶栏 ── */
.nav-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 0 14px;
}
.nav-title {
  font-size: 17px;
  font-weight: 700;
  color: var(--color-text);
  display: flex;
  align-items: center;
  gap: 10px;
}
.title-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-primary);
  box-shadow: 0 0 8px var(--color-primary);
  animation: dot-pulse 2s ease-in-out infinite;
}
@keyframes dot-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
.nav-count {
  font-size: 13px;
  color: var(--color-text-dim);
}

/* ── 加载 ── */
.loading-state {
  text-align: center;
  padding: 80px 0;
  color: var(--color-text-dim);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}
.load-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── 空状态 ── */
.empty-state {
  text-align: center;
  padding: 80px 0;
  color: var(--color-text-dim);
}
.empty-visual {
  width: 80px;
  height: 80px;
  margin: 0 auto 16px;
  border-radius: 50%;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-dim);
}
.empty-text {
  font-size: 15px;
  color: var(--color-text-secondary);
  margin-bottom: 6px;
}
.empty-hint {
  font-size: 12px;
}

/* ── 工单列表 ── */
.order-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.order-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  overflow: hidden;
  display: flex;
  transition: border-color var(--duration-fast);
  animation: card-in 0.35s var(--ease-out-expo) backwards;
}
.order-card:active {
  border-color: var(--color-border-active);
}
@keyframes card-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 紧急工单 — 左侧危险条纹 */
.order-card.emergency {
  border-color: rgba(255, 193, 7, 0.25);
}
.hazard-stripe {
  width: 8px;
  flex-shrink: 0;
  background: repeating-linear-gradient(
    -45deg,
    var(--color-warning),
    var(--color-warning) 6px,
    #111 6px,
    #111 12px
  );
}

.card-inner {
  flex: 1;
  padding: 16px;
  min-width: 0;
}
.emergency .card-inner {
  padding-left: 12px;
}

/* ── 卡片头部 ── */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.card-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-weight: 500;
}
.tag-emergency {
  background: var(--color-danger-dim);
  color: var(--color-danger);
  border: 1px solid rgba(255, 23, 68, 0.25);
}
.tag-normal {
  background: var(--color-info-dim);
  color: var(--color-info);
  border: 1px solid rgba(41, 121, 255, 0.25);
}
.tag-type {
  background: transparent;
  color: var(--color-text-dim);
  border: 1px solid var(--color-border);
}

/* 工单状态标签 */
.tag-status.tag-available {
  background: var(--color-info-dim);
  color: var(--color-info);
  border: 1px solid rgba(41, 121, 255, 0.25);
}
.tag-status.tag-dispatching {
  background: var(--color-primary-dim);
  color: var(--color-primary);
  border: 1px solid rgba(255, 107, 0, 0.25);
}
.tag-status.tag-taken {
  background: rgba(255, 193, 7, 0.1);
  color: var(--color-warning);
  border: 1px solid rgba(255, 193, 7, 0.25);
}

/* 距离 */
.card-distance {
  font-size: 13px;
  color: var(--color-primary);
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}
.dist-ping {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-primary);
  position: relative;
}
.dist-ping::after {
  content: '';
  position: absolute;
  inset: -4px;
  border-radius: 50%;
  border: 1px solid rgba(255, 107, 0, 0.3);
  animation: radar-ping 2s ease-out infinite;
}
@keyframes radar-ping {
  0% { transform: scale(1); opacity: 1; }
  100% { transform: scale(3); opacity: 0; }
}

/* ── 描述 ── */
.card-desc {
  font-size: 14px;
  color: var(--color-text);
  line-height: 1.55;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 8px;
}

/* ── 底部信息 ── */
.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  margin-bottom: 12px;
}
.card-addr {
  color: var(--color-text-dim);
}
.card-ai {
  color: var(--color-primary);
  background: var(--color-primary-dim);
  padding: 2px 8px;
  border-radius: var(--radius-xs);
  font-size: 11px;
}

/* ── 操作按钮 ── */
.card-actions {
  display: flex;
  gap: 8px;
}
.btn-detail {
  flex: 1;
  height: 42px;
  border-radius: var(--radius-sm);
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  font-size: 14px;
  color: var(--color-text-secondary);
  transition: border-color var(--duration-fast);
}
.btn-detail:active {
  border-color: var(--color-border-active);
}

.btn-accept {
  flex: 1;
  height: 42px;
  border-radius: var(--radius-sm);
  background: linear-gradient(135deg, #FF6B00, #E05500);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 1px;
  box-shadow: 0 2px 12px rgba(255, 107, 0, 0.3);
  transition: transform var(--duration-fast), opacity var(--duration-fast);
  display: flex;
  align-items: center;
  justify-content: center;
}
.btn-accept:active:not(:disabled) {
  transform: scale(0.96);
}
.btn-accept:disabled {
  opacity: 0.5;
}
.btn-accept--taken {
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  color: var(--color-text-dim);
  font-weight: 500;
  box-shadow: none;
}

.btn-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.25);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}

/* ── 错误 Toast ── */
.error-toast {
  position: fixed;
  bottom: 80px;
  left: 16px;
  right: 16px;
  z-index: var(--z-toast);
  background: var(--color-surface);
  border: 1px solid rgba(255, 23, 68, 0.4);
  color: var(--color-danger);
  font-size: 13px;
  text-align: center;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  max-width: 448px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}
.error-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-danger);
  box-shadow: 0 0 6px var(--color-danger);
}
</style>
