<!--
  城市设施报修 · 市民端 — 工单进度
  霓虹混凝土：地铁线路图时间轴 + 信号灯状态 + 报修照片 + 维修信息 + AI验收
-->
<template>
  <div class="detail-page">
    <div v-if="loading" class="loading-state">
      <span class="load-pulse"></span>
      加载中…
    </div>

    <template v-else-if="detail.ticket_id">
      <!-- 状态大卡 -->
      <div class="status-hero" :class="'hero-' + detail.status">
        <div class="hero-badge">
          <span class="hero-dot"></span>
          <span class="hero-status">{{ detail.status_label || STATUS_MAP[detail.status]?.label || detail.status }}</span>
        </div>
        <p class="hero-desc">{{ detail.report?.description || '' }}</p>
        <div class="hero-meta">
          <span class="meta-id mono"># {{ detail.ticket_id }}</span>
          <span class="meta-divider">·</span>
          <span class="meta-time mono">{{ formatTime(detail.created_at) }}</span>
        </div>

        <!-- 维修员卡片 -->
        <div v-if="detail.repair?.worker" class="worker-card">
          <div class="worker-avatar">
            <img v-if="detail.repair.worker.worker_avatar" :src="detail.repair.worker.worker_avatar" class="avatar-img" />
            <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="8" r="4" stroke="currentColor" stroke-width="1.5"/>
              <path d="M4 20c0-4 3.6-7 8-7s8 3 8 7" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
          </div>
          <div class="worker-info">
            <span class="worker-name">{{ detail.repair.worker.worker_name || '维修员' }}</span>
            <span class="worker-label">⭐ {{ detail.repair.worker.star_rating || '-' }} · {{ detail.repair.worker.total_orders || 0 }} 单</span>
          </div>
        </div>
      </div>

      <!-- 报修照片 -->
      <section v-if="detail.report?.image_urls?.length" class="photo-section">
        <header class="section-head">
          <span class="section-title">报修照片</span>
          <span class="section-count mono">{{ detail.report.image_urls.length }} 张</span>
        </header>
        <div class="photo-grid">
          <div v-for="(url, i) in detail.report.image_urls" :key="i" class="photo-item" @click="previewImage(url)">
            <img :src="url" :alt="'报修照片 ' + (i + 1)" />
          </div>
        </div>
      </section>

      <!-- 进度时间轴 — 地铁线路风格 -->
      <section class="timeline-section">
        <header class="section-head">
          <span class="section-title">处理进度</span>
          <span class="section-count mono">{{ timelineSteps.length }} 站</span>
        </header>

        <div class="timeline">
          <div
            v-for="(step, i) in timelineSteps"
            :key="i"
            class="tl-station"
            :class="{
              arrived: step.arrived,
              current: step.current,
              future: !step.arrived && !step.current,
            }"
          >
            <!-- 轨道线 -->
            <div v-if="i < timelineSteps.length - 1" class="tl-track">
              <div class="track-fill" :class="{ done: step.arrived }"></div>
            </div>

            <!-- 站点 -->
            <div class="tl-node">
              <div class="node-ring">
                <span class="node-dot"></span>
              </div>
              <div class="node-content">
                <div class="node-title">{{ step.title }}</div>
                <div v-if="step.desc" class="node-desc">{{ step.desc }}</div>
                <div v-if="step.time" class="node-time mono">{{ step.time }}</div>
              </div>
              <!-- 当前站动画 -->
              <div v-if="step.current" class="current-indicator"></div>
            </div>
          </div>
        </div>
      </section>

      <!-- 报修信息 -->
      <section class="info-section">
        <header class="section-head">
          <span class="section-title">报修信息</span>
        </header>
        <div class="info-list">
          <div class="info-row">
            <span class="info-k">设施类型</span>
            <span class="info-v">{{ getFacilityIcon(detail.report?.facility_type) }} {{ detail.report?.facility_type || '-' }}</span>
          </div>
          <div class="info-row">
            <span class="info-k">报修地址</span>
            <span class="info-v addr">📍 {{ detail.report?.address || '-' }}</span>
          </div>
          <div class="info-row" v-if="detail.report?.district">
            <span class="info-k">行政区</span>
            <span class="info-v">{{ detail.report.district }}</span>
          </div>
          <div class="info-row" v-if="detail.ai?.ai_category">
            <span class="info-k">AI 分类</span>
            <span class="info-v ai">{{ detail.ai.ai_category }} ({{ detail.ai.ai_confidence ? (detail.ai.ai_confidence * 100).toFixed(0) + '%' : '-' }})</span>
          </div>
        </div>
      </section>

      <!-- 维修信息（有维修记录时显示） -->
      <section v-if="detail.repair?.worker" class="info-section">
        <header class="section-head">
          <span class="section-title">维修信息</span>
        </header>
        <div class="info-list">
          <div class="info-row">
            <span class="info-k">维修工时</span>
            <span class="info-v">{{ detail.repair.labor_hours || 0 }} 小时</span>
          </div>
          <div class="info-row" v-if="detail.repair.work_notes">
            <span class="info-k">维修备注</span>
            <span class="info-v">{{ detail.repair.work_notes }}</span>
          </div>
        </div>

        <!-- 耗材清单 -->
        <div v-if="detail.repair.materials?.length" class="materials-box">
          <span class="materials-label">耗材清单</span>
          <div v-for="(m, i) in detail.repair.materials" :key="i" class="material-row">
            <span>{{ m.name }}</span>
            <span class="mono">{{ m.qty }} {{ m.unit }} × ¥{{ m.unit_cost }}</span>
          </div>
        </div>

        <!-- 完工照片 -->
        <div v-if="detail.repair.completion_photos?.length" class="completion-photos">
          <span class="photo-label">完工照片</span>
          <div class="photo-grid">
            <div v-for="(url, i) in detail.repair.completion_photos" :key="i" class="photo-item" @click="previewImage(url)">
              <img :src="url" :alt="'完工照片 ' + (i + 1)" />
            </div>
          </div>
        </div>
      </section>

      <!-- AI 验收结果 -->
      <section v-if="detail.ai?.ai_verified !== null && detail.ai?.ai_verified !== undefined" class="ai-card" :class="detail.ai.ai_verified ? 'ai-pass' : 'ai-fail'">
        <div class="ai-head">
          <span class="ai-icon">{{ detail.ai.ai_verified ? '✓' : '✗' }}</span>
          <span class="ai-result-text">AI 智能验收 — {{ detail.ai.ai_verified ? '通过' : '未通过' }}</span>
        </div>
        <span v-if="detail.ai.ai_verify_confidence" class="ai-conf mono">置信度 {{ (detail.ai.ai_verify_confidence * 100).toFixed(0) }}%</span>
        <span v-if="detail.ai.ai_verify_summary" class="ai-summary">{{ detail.ai.ai_verify_summary }}</span>
      </section>


      <!-- 撤销报修（所有状态都显示，但部分状态不可撤销） -->
      <div v-if="detail.status !== 'closed' && detail.status !== 'cancelled'" class="action-cta">
        <button class="btn-cancel" :disabled="cancelling" @click="handleCancel">
          <span v-if="cancelling" class="btn-spinner"></span>
          <span v-else>✕</span>
          <span>{{ cancelling ? '撤销中…' : '撤销报修' }}</span>
        </button>
        <p class="action-hint">撤销后将不再处理，工单归档</p>
      </div>

      <!-- 确认完结（验收中状态） -->
      <div v-if="detail.status === 'verifying'" class="action-cta">
        <button class="btn-close" :disabled="closing" @click="handleClose">
          <span v-if="closing" class="btn-spinner"></span>
          <span v-else>✓</span>
          <span>{{ closing ? '完结中…' : '确认完结' }}</span>
        </button>
        <p class="action-hint">确认维修已完成，工单将归档</p>
      </div>

      <!-- 市民评价显示（已评价） -->
      <section v-if="detail.evaluation" class="info-section evaluation-section">
        <header class="section-head">
          <span class="section-title">服务评价</span>
          <span class="section-count mono">{{ formatTime(detail.evaluation.created_at) }}</span>
        </header>
        <div class="evaluation-stars">
          <span v-for="i in 5" :key="i" class="star" :class="{ filled: i <= detail.evaluation.star }">★</span>
        </div>
        <div v-if="detail.evaluation.tags?.length" class="evaluation-tags">
          <span v-for="(tag, i) in detail.evaluation.tags" :key="i" class="eval-tag">{{ tag }}</span>
        </div>
        <div v-if="detail.evaluation.comment" class="evaluation-comment">
          {{ detail.evaluation.comment }}
        </div>
      </section>

      <!-- 评价入口（已完结但未评价） -->
      <div v-if="detail.status === 'closed' && !detail.evaluation" class="action-cta">
        <router-link :to="`/evaluation/${detail.ticket_id}`" class="btn-eval">
          <span class="eval-star">★</span>
          <span>评价本次服务</span>
        </router-link>
      </div>
    </template>

    <div v-else class="empty-state">
      <span class="empty-icon">⊘</span>
      <p>工单不存在</p>
    </div>

    <!-- 图片预览 -->
    <div v-if="previewVisible" class="preview-mask" @click="previewVisible = false">
      <img :src="previewUrl" class="preview-img" @click.stop />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getTicketDetail, closeTicket, cancelTicket } from '@/api/index'
import { STATUS_MAP, formatTime, getFacilityIcon } from '@/utils'

const route = useRoute()
const router = useRouter()
const detail = ref({})
const loading = ref(true)
const closing = ref(false)
const cancelling = ref(false)

// 图片预览
const previewVisible = ref(false)
const previewUrl = ref('')

function previewImage(url) {
  previewUrl.value = url
  previewVisible.value = true
}

async function handleClose() {
  if (closing.value) return
  closing.value = true
  try {
    await closeTicket(route.params.id)
    detail.value.status = 'closed'
  } catch (e) {
    console.error('完结失败:', e)
    alert(e?.response?.data?.detail || e?.message || '操作失败，请重试')
  } finally {
    closing.value = false
  }
}

async function handleCancel() {
  if (cancelling.value) return
  if (!confirm('确定要撤销此报修吗？撤销后工单将被彻底删除，无法恢复！')) return
  cancelling.value = true
  try {
    await cancelTicket(route.params.id)
    alert('工单已成功撤销并销毁')
    // 跳转回工单列表页
    router.push('/')
  } catch (e) {
    console.error('撤销失败:', e)
    alert(e?.response?.data?.detail || e?.message || '操作失败，请重试')
  } finally {
    cancelling.value = false
  }
}

const timelineSteps = computed(() => {
  const d = detail.value
  if (!d.ticket_id) return []

  const timeline = d.timeline || []
  if (timeline.length > 0) {
    return timeline.map((node, i) => {
      const isLast = i === timeline.length - 1
      return {
        title: node.label || '处理节点',
        desc: node.detail || '',
        time: formatTime(node.time),
        arrived: node.done,
        current: isLast && d.status !== 'closed' && node.done,
      }
    })
  }

  // 默认时间轴（降级）
  const STATUS_ORDER = ['pending', 'dispatching', 'accepting', 'repairing', 'verifying', 'closed']
  const STATION_NAMES = {
    pending: '市民报修',
    dispatching: 'AI 匹配派单',
    accepting: '等待维修工接单',
    repairing: '维修员到场处理',
    verifying: 'AI 智能验收',
    closed: '已完结归档',
    cancelled: '已撤销',
  }
  const currentIdx = STATUS_ORDER.indexOf(d.status)
  return STATUS_ORDER.map((status, i) => ({
    title: STATION_NAMES[status] || status,
    desc: '',
    time: status === 'pending' ? formatTime(d.created_at) : (status === 'closed' && d.closed_at ? formatTime(d.closed_at) : ''),
    arrived: i <= currentIdx,
    current: i === currentIdx && status !== 'closed',
  }))
})

onMounted(async () => {
  try {
    const data = await getTicketDetail(route.params.id)
    // 请求拦截器已解包 body.data，直接拿到详情对象
    detail.value = data || {}
  } catch (e) {
    console.error('加载工单失败:', e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.detail-page {
  padding: 0 16px 40px;
  max-width: 480px;
  margin: 0 auto;
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 100px 0;
  color: var(--color-text-dim);
  gap: 12px;
}
.empty-icon { font-size: 48px; }
.load-pulse {
  width: 16px; height: 16px; border-radius: 50%;
  background: var(--color-amber);
  animation: breathe 1.5s ease-in-out infinite;
}
@keyframes breathe {
  0%, 100% { opacity: 1; box-shadow: 0 0 8px rgba(255,137,34,0.6); }
  50% { opacity: 0.3; box-shadow: 0 0 2px rgba(255,137,34,0.2); }
}

/* ── 状态大卡 ── */
.status-hero {
  position: relative;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: 24px 20px;
  margin-bottom: 20px;
  overflow: hidden;
}
.status-hero::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
}
.hero-pending::before { background: var(--color-blue); }
.hero-dispatching::before { background: var(--color-amber); }
.hero-accepting::before { background: var(--color-yellow); }
.hero-repairing::before { background: var(--color-yellow); }
.hero-verifying::before { background: var(--color-blue); }
.hero-closed::before { background: var(--color-green); }
.hero-cancelled::before { background: #999; }

.hero-badge {
  display: inline-flex; align-items: center; gap: 6px;
  margin-bottom: 12px; padding: 4px 12px;
  border-radius: var(--radius-full);
  font-size: 12px; font-weight: 600; letter-spacing: 1px;
}
.hero-pending .hero-badge { background: rgba(68,138,255,0.12); color: var(--color-blue); }
.hero-dispatching .hero-badge { background: rgba(255,137,34,0.12); color: var(--color-amber); }
.hero-accepting .hero-badge { background: rgba(255,184,0,0.12); color: var(--color-yellow); }
.hero-repairing .hero-badge { background: rgba(255,184,0,0.12); color: var(--color-yellow); }
.hero-verifying .hero-badge { background: rgba(68,138,255,0.12); color: var(--color-blue); }
.hero-closed .hero-badge { background: rgba(0,230,118,0.12); color: var(--color-green); }
.hero-cancelled .hero-badge { background: rgba(153,153,153,0.12); color: #999; }

.hero-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: currentColor;
  box-shadow: 0 0 6px currentColor;
}

.hero-desc { font-size: 15px; color: var(--color-text); line-height: 1.7; margin-bottom: 10px; }
.hero-meta { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--color-text-dim); }
.meta-divider { color: var(--color-border); }

/* 维修员卡片 */
.worker-card { display: flex; align-items: center; gap: 12px; margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--color-border); }
.worker-avatar { width: 40px; height: 40px; border-radius: 50%; background: var(--color-amber-dim); border: 1px solid rgba(255, 137, 34, 0.2); display: flex; align-items: center; justify-content: center; color: var(--color-amber); overflow: hidden; }
.avatar-img { width: 100%; height: 100%; object-fit: cover; }
.worker-info { display: flex; flex-direction: column; gap: 2px; }
.worker-name { font-size: 14px; font-weight: 600; color: var(--color-text); }
.worker-label { font-size: 12px; color: var(--color-text-dim); }

/* ── 通用区块 ── */
.section-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.section-title { font-size: 13px; font-weight: 600; color: var(--color-text-secondary); letter-spacing: 1px; }
.section-count { font-size: 11px; color: var(--color-text-dim); }

/* ── 照片 ── */
.photo-section, .completion-photos { margin-bottom: 20px; }
.photo-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 10px; }
.photo-item { aspect-ratio: 1; border-radius: var(--radius-md); overflow: hidden; border: 1px solid var(--color-border); }
.photo-item img { width: 100%; height: 100%; object-fit: cover; display: block; }
.photo-label { display: block; font-size: 11px; color: var(--color-text-dim); margin-bottom: 8px; }

/* ── 时间轴 ── */
.timeline-section {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: 20px;
  margin-bottom: 20px;
}

.timeline { display: flex; flex-direction: column; position: relative; }
.tl-station { position: relative; padding-left: 40px; }
.tl-station:not(:last-child) { padding-bottom: 24px; }

.tl-track { position: absolute; left: 17px; top: 28px; bottom: 4px; width: 2px; background: var(--color-border); }
.track-fill { width: 100%; height: 0; background: var(--color-amber); transition: height 0.6s var(--ease-out-expo); }
.track-fill.done { height: 100%; }

.tl-node { display: flex; gap: 14px; position: relative; }
.node-ring { position: absolute; left: -28px; top: 2px; width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 2px solid var(--color-border); background: var(--color-surface); transition: all var(--duration-normal); z-index: 2; }
.arrived .node-ring { border-color: var(--color-amber); background: var(--color-amber-dim); }
.current .node-ring { border-color: var(--color-amber); box-shadow: 0 0 12px rgba(255, 137, 34, 0.4); animation: node-pulse 2s infinite; }
@keyframes node-pulse {
  0%, 100% { box-shadow: 0 0 12px rgba(255, 137, 34, 0.4); }
  50% { box-shadow: 0 0 24px rgba(255, 137, 34, 0.6); }
}

.node-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--color-border); transition: all var(--duration-normal); }
.arrived .node-dot { background: var(--color-amber); }
.current .node-dot { background: var(--color-amber); box-shadow: 0 0 8px var(--color-amber); }

.node-content { flex: 1; min-width: 0; }
.node-title { font-size: 14px; font-weight: 600; color: var(--color-text-dim); transition: color var(--duration-normal); }
.arrived .node-title, .current .node-title { color: var(--color-text); }
.node-desc { font-size: 12px; color: var(--color-text-dim); margin-top: 2px; }
.node-time { font-size: 11px; color: var(--color-text-dim); margin-top: 2px; }

.current-indicator { position: absolute; left: -34px; top: -2px; width: 36px; height: 36px; border-radius: 50%; border: 2px solid rgba(255, 137, 34, 0.2); animation: indicator-ripple 2.5s infinite; }
@keyframes indicator-ripple {
  0% { transform: scale(1); opacity: 1; }
  100% { transform: scale(1.8); opacity: 0; }
}

.future .node-ring { border-color: var(--color-border); }
.future .node-dot { background: transparent; }

/* ── 信息区 ── */
.info-section {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: 20px;
  margin-bottom: 20px;
}
.info-list { display: flex; flex-direction: column; gap: 10px; }
.info-row { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.info-k { font-size: 12px; color: var(--color-text-dim); flex-shrink: 0; }
.info-v { font-size: 13px; color: var(--color-text); text-align: right; }
.info-v.addr { color: var(--color-text-secondary); }
.info-v.ai { color: var(--color-amber); }

/* 耗材 */
.materials-box { margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--color-border); }
.materials-label { display: block; font-size: 11px; color: var(--color-text-dim); margin-bottom: 8px; }
.material-row { display: flex; justify-content: space-between; font-size: 12px; color: var(--color-text); padding: 4px 0; }

/* AI验收 */
.ai-card { padding: 14px; border-radius: var(--radius-md); margin-bottom: 20px; }
.ai-pass { background: rgba(0,230,118,0.06); border: 1px solid rgba(0,230,118,0.2); }
.ai-fail { background: rgba(255,23,68,0.06); border: 1px solid rgba(255,23,68,0.2); }
.ai-head { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.ai-icon { font-size: 20px; font-weight: 700; }
.ai-pass .ai-icon { color: var(--color-green); }
.ai-fail .ai-icon { color: #ff1744; }
.ai-result-text { font-size: 13px; font-weight: 600; color: var(--color-text); }
.ai-conf, .ai-summary { display: block; font-size: 11px; color: var(--color-text-dim); margin-top: 2px; }

/* 评价显示 */
.evaluation-section { }
.evaluation-stars { display: flex; gap: 4px; margin-bottom: 10px; }
.evaluation-stars .star { font-size: 20px; color: var(--color-border); transition: color 0.2s; }
.evaluation-stars .star.filled { color: var(--color-amber); text-shadow: 0 0 8px rgba(255,137,34,0.4); }
.evaluation-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
.eval-tag { font-size: 11px; padding: 4px 10px; border-radius: var(--radius-full); background: var(--color-amber-dim); color: var(--color-amber); border: 1px solid rgba(255,137,34,0.2); }
.evaluation-comment { font-size: 13px; color: var(--color-text); line-height: 1.6; padding-top: 8px; border-top: 1px solid var(--color-border); }


/* ── 操作按钮区 ── */
.action-cta {
  margin-top: 4px;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

/* 确认完结按钮 */
.btn-close {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 14px 36px; border-radius: var(--radius-full);
  background: linear-gradient(135deg, #00c48c, #008a5e);
  color: #fff; font-size: 15px; font-weight: 600; letter-spacing: 2px;
  box-shadow: 0 0 20px rgba(0,196,140,0.3);
  border: none;
  cursor: pointer;
  transition: all var(--duration-fast);
}
.btn-close:active { transform: scale(0.97); }
.btn-close:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 撤销报修按钮 */
.btn-cancel {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 16px 48px; border-radius: var(--radius-full);
  background: linear-gradient(135deg, #ff4d4f, #d32f2f);
  color: #fff; font-size: 16px; font-weight: 700; letter-spacing: 2px;
  box-shadow: 0 8px 24px rgba(255,77,79,0.4), 0 2px 8px rgba(211,47,47,0.3);
  border: 2px solid rgba(255,255,255,0.3);
  cursor: pointer;
  transition: all var(--duration-fast);
  animation: btn-pulse 2s ease-in-out infinite;
}
.btn-cancel:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 32px rgba(255,77,79,0.5), 0 4px 12px rgba(211,47,47,0.4);
}
.btn-cancel:active { transform: scale(0.97); }
.btn-cancel:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  animation: none;
}
@keyframes btn-pulse {
  0%, 100% {
    box-shadow: 0 8px 24px rgba(255,77,79,0.4), 0 2px 8px rgba(211,47,47,0.3);
  }
  50% {
    box-shadow: 0 8px 32px rgba(255,77,79,0.6), 0 2px 12px rgba(211,47,47,0.5);
  }
}

.btn-spinner {
  width: 16px; height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: btn-spin 0.6s linear infinite;
}
@keyframes btn-spin { to { transform: rotate(360deg); } }

.action-hint {
  font-size: 12px;
  color: var(--color-text-dim);
  margin: 0;
}

/* 评价按钮 */
.btn-eval {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 14px 36px; border-radius: var(--radius-full);
  background: linear-gradient(135deg, #e67a1e, #cc6000);
  color: #fff; font-size: 15px; font-weight: 600; letter-spacing: 2px;
  box-shadow: var(--shadow-glow-amber);
  transition: transform var(--duration-fast);
  text-decoration: none;
}
.btn-eval:active { transform: scale(0.97); }
.eval-star { font-size: 18px; }

/* ── 图片预览 ── */
.preview-mask { position: fixed; inset: 0; background: rgba(0,0,0,0.85); display: flex; align-items: center; justify-content: center; z-index: 9999; }
.preview-img { max-width: 90vw; max-height: 90vh; border-radius: var(--radius-md); }
</style>
