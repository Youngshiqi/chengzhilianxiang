<!--
  城市设施报修 · 市民端 — 我的工单
  霓虹混凝土：信号灯状态指示 + 工单调度看板
-->
<template>
  <div class="tickets-page">
    <!-- 用户信息栏 -->
    <div class="user-info-bar" v-if="userInfo">
      <div class="user-avatar">
        <span class="avatar-icon">👤</span>
      </div>
      <div class="user-details">
        <div class="user-name">{{ displayName }}</div>
        <div class="user-phone mono">{{ userInfo.phone || '' }}</div>
      </div>
    </div>

    <!-- 统计条 -->
    <div class="stats-bar">
      <div class="stat-item">
        <span class="stat-num">{{ total }}</span>
        <span class="stat-label">全部工单</span>
      </div>
      <div class="stat-divider"></div>
      <div class="stat-item stat-active">
        <span class="stat-num">{{ processingCount }}</span>
        <span class="stat-label">处理中</span>
      </div>
      <div class="stat-divider"></div>
      <div class="stat-item stat-closed">
        <span class="stat-num">{{ closedCount }}</span>
        <span class="stat-label">已完结</span>
      </div>
    </div>

    <!-- 状态筛选 -->
    <div class="filter-bar">
      <button
        v-for="f in filters"
        :key="f.value"
        class="filter-chip"
        :class="{ active: statusFilter === f.value }"
        @click="switchFilter(f.value)"
      >
        <span v-if="f.dot" class="chip-dot" :style="{ background: f.dot }"></span>
        {{ f.label }}
      </button>
    </div>

    <!-- 工单列表 -->
    <div v-if="tickets.length" class="ticket-list">
      <router-link
        v-for="(t, idx) in tickets"
        :key="t.ticket_id"
        :to="`/ticket/${t.ticket_id}`"
        class="ticket-card"
        :style="{ animationDelay: idx * 0.05 + 's' }"
      >
        <!-- 左侧状态条 -->
        <div class="card-bar" :class="'bar-' + t.status"></div>

        <div class="card-body">
          <div class="card-top">
            <span class="card-id mono">#{{ t.ticket_id }}</span>
            <span v-if="needsEvaluation(t)" class="eval-badge">
              <span class="eval-star">★</span> 待评价
            </span>
            <span v-else class="card-status" :class="'cs-' + t.status">
              <span class="cs-dot"></span>
              {{ STATUS_MAP[t.status]?.label || t.status }}
            </span>
          </div>

          <p class="card-desc">{{ t.description }}</p>

          <div class="card-bottom">
            <span class="card-meta mono">{{ t.facility_type }}</span>
            <span v-if="t.ai_category" class="card-ai mono">AI: {{ t.ai_category }}</span>
            <span class="card-time mono">{{ formatTime(t.created_at) }}</span>
          </div>
        </div>
      </router-link>
    </div>

    <div v-else-if="!loading" class="empty-state">
      <div class="empty-visual">
        <span class="empty-symbol">⊡</span>
      </div>
      <p class="empty-text">暂无工单记录</p>
      <router-link to="/home" class="empty-link">去报修 →</router-link>
    </div>

    <div v-if="loading" class="loading-state">
      <span class="load-spinner"></span>
    </div>

    <!-- 分页 -->
    <div v-if="total > 0" class="pagination">
      <button
        class="page-btn"
        :disabled="page <= 1"
        @click="goPage(page - 1)"
      >
        <span class="btn-icon">←</span>
        <span class="btn-text">上一页</span>
      </button>

      <div class="page-info">
        <span class="page-current mono">{{ page }}</span>
        <span class="page-sep">/</span>
        <span class="page-total mono">{{ totalPages }}</span>
      </div>

      <button
        class="page-btn"
        :disabled="page >= totalPages"
        @click="goPage(page + 1)"
      >
        <span class="btn-text">下一页</span>
        <span class="btn-icon">→</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getMyTickets } from '@/api/index'
import { STATUS_MAP, formatTime } from '@/utils'

const filters = [
  { label: '全部', value: '' },
  { label: '已接单', value: 'dispatching', dot: '#ff8522' },
  { label: '维修中', value: 'repairing', dot: '#ffb800' },
  { label: '已完结', value: 'closed', dot: '#00e676' },
  { label: '待评价', value: 'needs_evaluation', dot: '#ff5722' },
]

const tickets = ref([])
const total = ref(0)
const closedCount = ref(0)
const processingCount = ref(0)
const userInfo = ref(null)
const page = ref(1)
const pageSize = 10

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

const displayName = computed(() => {
  if (!userInfo.value) return '市民用户'
  const name = userInfo.value.name
  if (!name || name === '????' || name.includes('?')) {
    return '市民用户'
  }
  return name
})
const loading = ref(false)
const statusFilter = ref('')

function needsEvaluation(ticket) {
  return ticket.status === 'closed' && ticket.has_evaluation !== true
}

async function fetch() {
  loading.value = true
  try {
    const params = { page: page.value, page_size: pageSize }
    if (statusFilter.value) {
      params.status = statusFilter.value
    }
    const data = await getMyTickets(params)
    tickets.value = data.items || []
    total.value = data.total || 0
    closedCount.value = data.closed_count || 0
    processingCount.value = data.processing_count || 0
    userInfo.value = data.user_info || null
  } catch (e) {
    console.error('加载工单失败:', e)
  } finally {
    loading.value = false
  }
}

function switchFilter(value) {
  statusFilter.value = value
  page.value = 1
  fetch()
}

function goPage(p) {
  page.value = p
  fetch()
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

onMounted(() => fetch())
</script>

<style scoped>
.tickets-page {
  padding: 0 16px 40px;
  max-width: 480px;
  margin: 0 auto;
}

/* ── 用户信息栏 ── */
.user-info-bar {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 18px;
  margin-bottom: 14px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}
.user-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: var(--color-amber-dim);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.avatar-icon {
  font-size: 24px;
}
.user-details {
  flex: 1;
  min-width: 0;
}
.user-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 4px;
}
.user-phone {
  font-size: 12px;
  color: var(--color-text-dim);
  letter-spacing: 1px;
}

/* ── 统计条 ── */
.stats-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 24px;
  padding: 18px 20px;
  margin-bottom: 14px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}
.stat-item {
  text-align: center;
}
.stat-num {
  display: block;
  font-family: var(--font-mono);
  font-size: 24px;
  font-weight: 600;
  color: var(--color-text);
  letter-spacing: 2px;
}
.stat-active .stat-num {
  color: var(--color-yellow);
}
.stat-closed .stat-num {
  color: var(--color-green);
}
.stat-label {
  font-size: 11px;
  color: var(--color-text-dim);
  letter-spacing: 1px;
}
.stat-divider {
  width: 1px;
  height: 28px;
  background: var(--color-border);
}

/* ── 筛选 ── */
.filter-bar {
  display: flex;
  gap: 8px;
  padding: 4px 0 16px;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}
.filter-bar::-webkit-scrollbar { display: none; }

.filter-chip {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: var(--radius-full);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  font-size: 13px;
  color: var(--color-text-dim);
  white-space: nowrap;
  flex-shrink: 0;
  transition: all var(--duration-fast) var(--ease-out-expo);
}
.filter-chip:active {
  transform: scale(0.96);
}
.filter-chip.active {
  background: var(--color-amber-dim);
  border-color: rgba(255, 137, 34, 0.3);
  color: var(--color-amber);
}
.chip-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

/* ── 工单列表 ── */
.ticket-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.ticket-card {
  display: flex;
  min-height: 88px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition: border-color var(--duration-fast), transform var(--duration-fast);
  animation: card-in 0.4s var(--ease-out-expo) backwards;
}
.ticket-card:active {
  transform: scale(0.99);
  border-color: var(--color-border-glow);
}
@keyframes card-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 左侧状态条 */
.card-bar {
  width: 3px;
  flex-shrink: 0;
}
.bar-pending { background: var(--color-blue); }
.bar-dispatching { background: var(--color-amber); }
.bar-accepting { background: var(--color-yellow); }
.bar-repairing { background: var(--color-yellow); }
.bar-verifying { background: var(--color-blue); }
.bar-closed { background: var(--color-green); }
.bar-cancelled { background: #999; }

.card-body {
  flex: 1;
  padding: 14px 16px;
  min-width: 0;
  position: relative;
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.card-id {
  font-size: 11px;
  color: var(--color-text-dim);
}
.card-status {
  font-size: 11px;
  font-weight: 500;
  padding: 2px 10px;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  gap: 4px;
}
.cs-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
}
.cs-pending { background: rgba(68,138,255,0.12); color: var(--color-blue); }
.cs-pending .cs-dot { background: var(--color-blue); }
.cs-dispatching { background: rgba(255,137,34,0.12); color: var(--color-amber); }
.cs-dispatching .cs-dot { background: var(--color-amber); }
.cs-accepting { background: rgba(255,184,0,0.12); color: var(--color-yellow); }
.cs-accepting .cs-dot { background: var(--color-yellow); }
.cs-repairing { background: rgba(255,184,0,0.12); color: var(--color-yellow); }
.cs-repairing .cs-dot { background: var(--color-yellow); }
.cs-verifying { background: rgba(68,138,255,0.12); color: var(--color-blue); }
.cs-verifying .cs-dot { background: var(--color-blue); }
.cs-closed { background: rgba(0,230,118,0.12); color: var(--color-green); }
.cs-closed .cs-dot { background: var(--color-green); }
.cs-cancelled { background: rgba(153,153,153,0.12); color: #999; }
.cs-cancelled .cs-dot { background: #999; }

.card-desc {
  font-size: 14px;
  color: var(--color-text);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 8px;
}

.card-bottom {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.card-meta {
  font-size: 11px;
  color: var(--color-text-dim);
}
.card-ai {
  font-size: 10px;
  color: var(--color-amber);
  background: var(--color-amber-dim);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
}
.card-time {
  font-size: 11px;
  color: var(--color-text-dim);
  margin-left: auto;
}

/* 评价徽标 */
.eval-badge {
  font-size: 11px;
  color: var(--color-amber);
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 2px 10px;
  border-radius: var(--radius-full);
  background: rgba(255,137,34,0.12);
  flex-shrink: 0;
}
.eval-star { color: var(--color-yellow); }

/* ── 空状态 ── */
.empty-state {
  text-align: center;
  padding: 60px 0;
}
.empty-visual {
  width: 72px;
  height: 72px;
  margin: 0 auto 16px;
  border-radius: 50%;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
}
.empty-symbol {
  font-size: 32px;
  color: var(--color-text-dim);
}
.empty-text {
  font-size: 14px;
  color: var(--color-text-dim);
  margin-bottom: 12px;
}
.empty-link {
  font-size: 14px;
  color: var(--color-amber);
  font-weight: 500;
}

.loading-state {
  display: flex;
  justify-content: center;
  padding: 60px 0;
}
.load-spinner {
  width: 28px;
  height: 28px;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-amber);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── 分页 ── */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 20px;
  padding: 12px 16px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}

.page-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: var(--radius-md);
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-text);
  font-size: 13px;
  font-weight: 500;
  transition: all var(--duration-fast);
}
.page-btn:active:not(:disabled) {
  border-color: var(--color-amber);
  color: var(--color-amber);
  transform: scale(0.96);
}
.page-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
.btn-icon {
  font-family: var(--font-mono);
  font-size: 12px;
}
.btn-text {
  font-size: 13px;
}

.page-info {
  display: flex;
  align-items: baseline;
  gap: 4px;
  font-size: 13px;
  color: var(--color-text-dim);
}
.page-current {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-amber);
}
.page-sep {
  color: var(--color-text-dim);
}
.page-total {
  font-size: 14px;
}

@media (max-width: 360px) {
  .btn-text {
    display: none;
  }
  .page-btn {
    padding-inline: 12px;
  }
}
</style>
