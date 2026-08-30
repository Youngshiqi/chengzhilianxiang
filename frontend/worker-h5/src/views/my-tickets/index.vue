<!--
  城市设施报修 · 维修工端 — 我的工单
  与接单大厅风格一致：紧急条纹 + 统一卡片样式
-->
<template>
  <div class="my-tickets-page">
    <!-- 顶栏 -->
    <header class="nav-bar">
      <span class="nav-title">
        <span class="title-dot"></span>
        我的工单
      </span>
      <span class="nav-count mono" v-if="total">共 {{ total }} 单</span>
    </header>

    <!-- 状态筛选 -->
    <div class="filter-bar">
      <button
        v-for="f in filters"
        :key="f.value"
        class="filter-chip"
        :class="{ active: statusFilter === f.value }"
        @click="statusFilter = f.value; page = 1; fetch()"
      >
        <span v-if="f.dot" class="chip-dot" :style="{ background: f.dot }"></span>
        {{ f.label }}
      </button>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="loading-state">
      <div class="load-spinner"></div>
      <span>加载工单中...</span>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!tickets.length" class="empty-state">
      <div class="empty-visual">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
          <circle cx="12" cy="12" r="9" />
          <path d="M12 8v4M12 16h.01" />
        </svg>
      </div>
      <p class="empty-text">暂无工单</p>
      <p class="empty-hint">当前没有相关状态的工单</p>
    </div>

    <!-- 工单列表 -->
    <div v-else class="order-list">
      <router-link
        v-for="(order, idx) in filteredTickets"
        :key="order.ticket_id"
        :to="`/ticket/${order.ticket_id}`"
        class="order-card"
        :class="{ emergency: order.emergency_level === 1 }"
        :style="{ animationDelay: idx * 0.04 + 's' }"
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
              <span class="tag" :style="statusStyle(order)">{{ STATUS_MAP[order.status]?.label || order.status }}</span>
            </div>
            <span class="card-time mono">{{ formatTime(order.created_at) }}</span>
          </div>

          <!-- 描述 -->
          <p class="card-desc">{{ order.description }}</p>

          <!-- 底部信息 -->
          <div class="card-footer">
            <span class="card-addr">📍 {{ order.address || '位置未知' }}</span>
            <span v-if="order.ai_category" class="card-ai mono">AI: {{ order.ai_category }}</span>
          </div>
        </div>
      </router-link>
    </div>

    <!-- 分页 -->
    <div v-if="total > pageSize" class="pagination">
      <button class="page-btn" :disabled="page <= 1" @click="page--; fetch()">←</button>
      <span class="page-info mono">{{ page }} / {{ Math.ceil(total / pageSize) }}</span>
      <button class="page-btn" :disabled="page >= Math.ceil(total / pageSize)" @click="page++; fetch()">→</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getMyTickets } from '@/api/index'
import { STATUS_MAP, formatTime } from '@/utils'

const filters = [
  { label: '全部', value: '' },
  { label: '维修中', value: 'repairing', dot: '#FF6B00' },
  { label: '验收中', value: 'verifying', dot: '#2979FF' },
  { label: '已完结', value: 'closed', dot: '#00E676' },
]

const tickets = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(false)
const statusFilter = ref('')

const filteredTickets = computed(() => {
  if (!statusFilter.value) return tickets.value
  return tickets.value.filter(t => t.status === statusFilter.value)
})

function statusStyle(order) {
  const s = order.status
  if (s === 'repairing' || s === 'verifying') {
    return { background: 'rgba(255,193,7,0.1)', color: '#FFC107', border: '1px solid rgba(255,193,7,0.25)' }
  }
  if (s === 'dispatching') {
    return { background: 'rgba(255,107,0,0.12)', color: '#FF6B00', border: '1px solid rgba(255,107,0,0.25)' }
  }
  if (s === 'accepting') {
    return { background: 'rgba(156,39,176,0.12)', color: '#9c27b0', border: '1px solid rgba(156,39,176,0.25)' }
  }
  if (s === 'closed') {
    return { background: 'rgba(0,230,118,0.12)', color: '#00E676', border: '1px solid rgba(0,230,118,0.25)' }
  }
  return { background: 'rgba(41,121,255,0.12)', color: '#2979FF', border: '1px solid rgba(41,121,255,0.25)' }
}

async function fetch() {
  loading.value = true
  try {
    const data = await getMyTickets({ page: page.value, page_size: pageSize })
    tickets.value = data.items || []
    total.value = data.total || 0
  } catch (e) {
    console.error('工单加载失败:', e)
  } finally {
    loading.value = false
  }
}

onMounted(fetch)
</script>

<style scoped>
.my-tickets-page {
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

/* ── 筛选芯片 ── */
.filter-bar {
  display: flex;
  gap: 8px;
  padding: 0 0 14px;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}
.filter-bar::-webkit-scrollbar { display: none; }

.filter-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  font-size: 13px;
  color: var(--color-text-dim);
  white-space: nowrap;
  flex-shrink: 0;
  transition: all var(--duration-fast);
}
.filter-chip:active {
  transform: scale(0.96);
}
.filter-chip.active {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: #fff;
}
.chip-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
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
  text-decoration: none;
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

/* 时间 */
.card-time {
  font-size: 12px;
  color: var(--color-text-dim);
  flex-shrink: 0;
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

/* ── 分页 ── */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-top: 18px;
}
.page-btn {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  font-size: 15px;
  font-family: var(--font-mono);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color var(--duration-fast), color var(--duration-fast);
}
.page-btn:active:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
.page-btn:disabled {
  opacity: 0.25;
}
.page-info {
  font-size: 13px;
  color: var(--color-text-dim);
  letter-spacing: 1px;
}
</style>
