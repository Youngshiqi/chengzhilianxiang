<!--
  城市设施报修 · 维修工端 — 工单详情
  重工仪表：状态大卡 + 工业流程时间轴 + 报修信息 + 维修记录 + AI验收
-->
<template>
  <div class="detail-page">
    <!-- 顶栏 -->
    <header class="nav-bar">
      <button class="btn-back" @click="$router.back()">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="15 18 9 12 15 6" />
        </svg>
      </button>
      <span class="nav-title mono">工单详情</span>
      <span class="nav-spacer"></span>
    </header>

    <!-- 加载中 -->
    <div v-if="loading" class="loading-state">
      <div class="load-spinner"></div>
      <span>加载中...</span>
    </div>

    <template v-if="!loading && detail.ticket_id">
      <!-- 状态大卡 -->
      <div class="status-hero" :class="'hero-' + detail.status">
        <div class="hero-top">
          <span class="hero-badge">{{ detail.status_label || STATUS_MAP[detail.status]?.label || detail.status }}</span>
          <span v-if="detail.report?.emergency_level" class="hero-emergency">紧急</span>
        </div>
        <p class="hero-id mono"># {{ detail.ticket_id }}</p>
        <p class="hero-desc">{{ detail.report?.description || detail.description }}</p>
        <div class="hero-meta mono">
          <span>{{ getFacilityIcon(detail.report?.facility_type) }} {{ detail.report?.facility_type || detail.facility_type }}</span>
          <span class="meta-sep">|</span>
          <span>📍 {{ detail.report?.address || detail.address || '位置未知' }}</span>
        </div>
      </div>

      <!-- 报修照片（市民提交的现场证据） -->
      <section v-if="detail.report?.image_urls?.length" class="photo-card">
        <header class="tl-header">
          <span class="tl-title">报修现场照片</span>
          <span class="tl-count mono">{{ detail.report.image_urls.length }} 张</span>
        </header>
        <div class="photo-grid">
          <div v-for="(url, i) in detail.report.image_urls" :key="i" class="photo-item" @click="previewImage(url)">
            <img :src="url" :alt="'报修照片 ' + (i + 1)" />
          </div>
        </div>
      </section>

      <!-- 工业流程时间轴 -->
      <section class="timeline-section">
        <header class="tl-header">
          <span class="tl-title">处理进度</span>
          <span class="tl-count mono">{{ detail.timeline?.length || 5 }} 节点</span>
        </header>

        <div class="timeline">
          <div
            v-for="(node, i) in detail.timeline"
            :key="i"
            class="tl-node"
            :class="{ done: node.done, current: isCurrent(i) }"
          >
            <!-- 连接线 -->
            <div v-if="i < detail.timeline.length - 1" class="tl-line">
              <div class="line-fill" :class="{ filled: node.done }"></div>
            </div>

            <!-- 节点 -->
            <div class="tl-dot">
              <span v-if="node.done" class="dot-check">✓</span>
              <span v-else class="dot-num mono">{{ i + 1 }}</span>
            </div>

            <!-- 内容 -->
            <div class="tl-content">
              <span class="tl-label">{{ node.label }}</span>
              <span v-if="node.time" class="tl-time mono">{{ formatTime(node.time) }}</span>
              <span v-else class="tl-time na">等待中</span>
              <span v-if="node.detail" class="tl-detail">{{ node.detail }}</span>
            </div>

            <!-- 当前节点脉冲 -->
            <div v-if="isCurrent(i)" class="tl-current-pulse"></div>
          </div>
        </div>
      </section>

      <!-- 报修信息卡 -->
      <section class="info-card">
        <header class="tl-header">
          <span class="tl-title">报修信息</span>
        </header>
        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">报修人</span>
            <span class="info-value">{{ detail.report?.reporter_name || detail.report?.reporter_id || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">联系电话</span>
            <span class="info-value mono">{{ detail.report?.reporter_phone || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">设施类型</span>
            <span class="info-value">{{ getFacilityIcon(detail.report?.facility_type) }} {{ detail.report?.facility_type }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">行政区</span>
            <span class="info-value">{{ detail.report?.district || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">AI 分类</span>
            <span class="info-value mono ai">{{ detail.ai?.ai_category || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">AI 置信度</span>
            <span class="info-value mono">{{ detail.ai?.ai_confidence ? (detail.ai.ai_confidence * 100).toFixed(0) + '%' : '-' }}</span>
          </div>
          <div class="info-item full">
            <span class="info-label">故障地址</span>
            <span class="info-value addr">📍 {{ detail.report?.address || '未知' }}</span>
          </div>
          <div class="info-item full">
            <span class="info-label">故障描述</span>
            <span class="info-value">{{ detail.report?.description || '-' }}</span>
          </div>
        </div>
      </section>

      <!-- AI 智能诊断 — 战术情报面板 -->
      <section v-if="hasAiInsights" class="ai-panel">
        <header class="tl-header">
          <span class="tl-title">AI 智能诊断</span>
          <span class="tl-badge ai-conf-badge" :class="confidenceLevel">
            {{ ((detail.ai?.ai_confidence || 0) * 100).toFixed(0) }}% 置信
          </span>
        </header>

        <!-- Row 1: 分类 + 紧急程度 -->
        <div class="ai-classify-row">
          <div class="ai-chip ai-chip-cat">
            <span class="ai-chip-icon">⊞</span>
            <span>{{ detail.ai?.issue_category || detail.ai?.ai_category || detail.ai?.category || '-' }}</span>
          </div>
          <div v-if="detail.ai?.subcategory || detail.ai?.sub_category" class="ai-chip ai-chip-sub">
            {{ detail.ai?.subcategory || detail.ai?.sub_category }}
          </div>
          <div class="ai-chip" :class="urgencyClass">
            <span class="ai-chip-dot"></span>
            {{ urgencyLabel }}
          </div>
        </div>

        <!-- Row 2: 优先级色条 -->
        <div v-if="detail.ai?.priority_score" class="ai-priority">
          <span class="ai-pri-label mono">PRIORITY</span>
          <div class="ai-pri-track">
            <div class="ai-pri-fill" :style="{ width: Math.min((detail.ai.priority_score || 0), 100) + '%' }" :class="priFillClass"></div>
          </div>
          <span class="ai-pri-val mono">{{ (detail.ai.priority_score || 0).toFixed(0) }}</span>
        </div>

        <!-- Row 3: 紧急原因 -->
        <div v-if="detail.ai?.urgency_reason" class="ai-reason">
          <span class="ai-reason-icon">⚡</span>
          <span>{{ detail.ai.urgency_reason }}</span>
        </div>

        <!-- Row 4: 关键信息 -->
        <div v-if="detail.ai?.key_info?.length" class="ai-tags-row">
          <span class="ai-tags-label">关键信息</span>
          <div class="ai-tags">
            <span v-for="(k, i) in detail.ai.key_info" :key="i" class="ai-tag ai-tag-info">{{ k }}</span>
          </div>
        </div>

        <!-- Row 5: 建议操作（高亮卡片） -->
        <div v-if="detail.ai?.suggested_action" class="ai-action-card">
          <span class="ai-action-label">建议操作</span>
          <p class="ai-action-text">{{ detail.ai.suggested_action }}</p>
        </div>

        <!-- Row 6: 维修知识 -->
        <div v-if="detail.ai?.repair_knowledge?.length" class="ai-tags-row">
          <span class="ai-tags-label">维修知识</span>
          <div class="ai-tags">
            <span v-for="(k, i) in detail.ai.repair_knowledge" :key="i" class="ai-tag ai-tag-knowledge">{{ k }}</span>
          </div>
        </div>

        <!-- Row 7: 工具 + 零件（双列） -->
        <div class="ai-resource-row" v-if="detail.ai?.tools_needed?.length || detail.ai?.parts_needed?.length">
          <div v-if="detail.ai?.tools_needed?.length" class="ai-resource-col">
            <span class="ai-tags-label">🔨 所需工具</span>
            <div class="ai-tags">
              <span v-for="(t, i) in detail.ai.tools_needed" :key="i" class="ai-tag ai-tag-tool">{{ t }}</span>
            </div>
          </div>
          <div v-if="detail.ai?.parts_needed?.length" class="ai-resource-col">
            <span class="ai-tags-label">🔩 所需零件</span>
            <div class="ai-tags">
              <span v-for="(p, i) in detail.ai.parts_needed" :key="i" class="ai-tag ai-tag-part">{{ p }}</span>
            </div>
          </div>
        </div>

        <!-- Row 8: 安全提示 -->
        <div v-if="detail.ai?.safety_tips?.length" class="ai-safety">
          <div class="ai-safety-header">
            <span class="ai-safety-icon">🛡</span>
            <span class="ai-safety-title">安全提示</span>
          </div>
          <div class="ai-safety-list">
            <div v-for="(s, i) in detail.ai.safety_tips" :key="i" class="ai-safety-item">
              <span class="ai-safety-bullet">{{ i + 1 }}</span>
              <span>{{ s }}</span>
            </div>
          </div>
        </div>
      </section>

      <!-- 维修记录（签到后显示） -->
      <section v-if="detail.repair?.worker" class="info-card">
        <header class="tl-header">
          <span class="tl-title">维修记录</span>
        </header>
        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">签到时间</span>
            <span class="info-value">{{ formatTime(detail.repair.checkin_at) }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">完工时间</span>
            <span class="info-value">{{ formatTime(detail.repair.completed_at) }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">维修工时</span>
            <span class="info-value mono">{{ detail.repair.labor_hours || 0 }} 小时</span>
          </div>
          <div class="info-item">
            <span class="info-label">维修备注</span>
            <span class="info-value">{{ detail.repair.work_notes || '-' }}</span>
          </div>
        </div>

        <!-- 耗材清单 -->
        <div v-if="detail.repair.materials?.length" class="materials-table">
          <span class="materials-title">耗材清单</span>
          <table>
            <thead><tr><th>名称</th><th>数量</th><th>单位</th><th>单价</th></tr></thead>
            <tbody>
              <tr v-for="(m, i) in detail.repair.materials" :key="i">
                <td>{{ m.name }}</td>
                <td>{{ m.qty }}</td>
                <td>{{ m.unit }}</td>
                <td>¥{{ m.unit_cost }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 完工照片 -->
        <div v-if="detail.repair.completion_photos?.length" class="photo-section">
          <span class="photo-label">完工照片</span>
          <div class="photo-grid">
            <div v-for="(url, i) in detail.repair.completion_photos" :key="i" class="photo-item" @click="previewImage(url)">
              <img :src="url" :alt="'完工照片 ' + (i + 1)" />
            </div>
          </div>
        </div>
      </section>

      <!-- AI 验收结果 -->
      <section v-if="detail.ai?.ai_verified !== null && detail.ai?.ai_verified !== undefined" class="ai-result-card" :class="detail.ai.ai_verified ? 'ai-pass' : 'ai-fail'">
        <span class="ai-icon">{{ detail.ai.ai_verified ? '✓' : '✗' }}</span>
        <div class="ai-body">
          <span class="ai-title">AI 智能验收 — {{ detail.ai.ai_verified ? '通过' : '未通过' }}</span>
          <span v-if="detail.ai.ai_verify_confidence" class="ai-conf">置信度 {{ (detail.ai.ai_verify_confidence * 100).toFixed(0) }}%</span>
          <span v-if="detail.ai.ai_verify_summary" class="ai-summary">{{ detail.ai.ai_verify_summary }}</span>
        </div>
      </section>

      <!-- 结算信息 -->
      <section v-if="detail.settlement" class="info-card settlement-card">
        <header class="tl-header">
          <span class="tl-title">费用明细</span>
          <span class="tl-badge" :class="detail.settlement.audit_status === 'approved' ? 'badge-green' : 'badge-pending'">
            {{ detail.settlement.audit_status === 'approved' ? '已审核' : '待审核' }}
          </span>
        </header>
        <div class="settlement-grid">
          <div class="sett-item">
            <span class="sett-value mono">¥{{ detail.settlement.material_cost?.toFixed(2) }}</span>
            <span class="sett-label">耗材费</span>
          </div>
          <span class="sett-op">+</span>
          <div class="sett-item">
            <span class="sett-value mono">¥{{ detail.settlement.labor_cost?.toFixed(2) }}</span>
            <span class="sett-label">劳务费</span>
          </div>
          <span class="sett-op">=</span>
          <div class="sett-item sett-total">
            <span class="sett-value mono">¥{{ detail.settlement.total_cost?.toFixed(2) }}</span>
            <span class="sett-label">合计</span>
          </div>
        </div>
      </section>

      <!-- 市民评价（已评价显示） -->
      <section v-if="detail.evaluation" class="info-card evaluation-card">
        <header class="tl-header">
          <span class="tl-title">市民评价</span>
          <span class="tl-count mono">{{ formatTime(detail.evaluation.created_at) }}</span>
        </header>
        <div class="evaluation-stars">
          <span v-for="i in 5" :key="i" class="star" :class="{ filled: i <= detail.evaluation.star }">★</span>
          <span class="star-label">{{ detail.evaluation.star }} 星</span>
        </div>
        <div v-if="detail.evaluation.tags?.length" class="evaluation-tags">
          <span v-for="(tag, i) in detail.evaluation.tags" :key="i" class="eval-tag">{{ tag }}</span>
        </div>
        <div v-if="detail.evaluation.comment" class="evaluation-comment">
          {{ detail.evaluation.comment }}
        </div>
      </section>

      <!-- 错误提示 -->
      <div v-if="errorMsg" class="error-msg">
        <span class="error-dot"></span> {{ errorMsg }}
      </div>

      <!-- 操作按钮区 -->
      <div class="action-bar" v-if="detail.status !== 'closed' && detail.status !== 'verifying'">
        <!-- 系统已指派给我：直接签到 + 完工 -->
        <template v-if="isAssignedToMe">
          <button class="btn-outline" :disabled="acting" @click="handleCheckin">
            <span v-if="acting === 'checkin'" class="btn-spinner-dark"></span>
            <span v-else>
              <span v-if="locating">📍 定位中...</span>
              <span v-else>📍 到场签到</span>
            </span>
          </button>

          <!-- 定位状态显示 -->
          <div v-if="locating || locationStatus" class="location-status">
            <span class="status-dot" :class="locationStatus"></span>
            <span class="status-text">
              <template v-if="locating">正在获取高精度位置...</template>
              <template v-else-if="locationStatus === 'good'">精度良好 ({{ currentAccuracy }}m)</template>
              <template v-else-if="locationStatus === 'low'">精度一般 ({{ currentAccuracy }}m)</template>
              <template v-else-if="locationStatus === 'failed'">定位失败，使用上次位置</template>
            </span>
          </div>

          <button class="btn-green" @click="$router.push(`/complete/${detail.ticket_id}`)">
            ✅ 完工提交
          </button>
        </template>

        <!-- 待接单：接单按钮 -->
        <button
          v-else-if="detail.status === 'pending' || detail.status === 'dispatching' || detail.status === 'accepting'"
          class="btn-orange"
          :disabled="acting"
          @click="handleAccept"
        >
          <span v-if="acting" class="btn-spinner"></span>
          <span v-else>确认接单</span>
        </button>

        <!-- 维修中：签到 + 完工 -->
        <template v-else-if="detail.status === 'repairing'">
          <button class="btn-outline" :disabled="acting" @click="handleCheckin">
            <span v-if="acting === 'checkin'" class="btn-spinner-dark"></span>
            <span v-else>
              <span v-if="locating">📍 定位中...</span>
              <span v-else>📍 到场签到</span>
            </span>
          </button>

          <!-- 定位状态显示 -->
          <div v-if="locating || locationStatus" class="location-status">
            <span class="status-dot" :class="locationStatus"></span>
            <span class="status-text">
              <template v-if="locating">正在获取高精度位置...</template>
              <template v-else-if="locationStatus === 'good'">精度良好 ({{ currentAccuracy }}m)</template>
              <template v-else-if="locationStatus === 'low'">精度一般 ({{ currentAccuracy }}m)</template>
              <template v-else-if="locationStatus === 'failed'">定位失败，使用上次位置</template>
            </span>
          </div>

          <button class="btn-green" @click="$router.push(`/complete/${detail.ticket_id}`)">
            ✅ 完工提交
          </button>
        </template>
      </div>

      <!-- 已完结/验收中：只读提示 -->
      <div v-else class="action-done">
        <div class="done-card" :class="detail.status === 'closed' ? 'done-green' : 'done-blue'">
          <span v-if="detail.status === 'closed'" class="done-icon">✓</span>
          <span v-else class="done-icon">⌛</span>
          <span>{{ detail.status === 'closed' ? '此工单已完结归档' : '市民确认中，请耐心等待' }}</span>
        </div>
      </div>
    </template>

    <!-- 不存在 -->
    <div v-if="!loading && !detail.ticket_id" class="empty-state">
      <div class="empty-visual">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
      </div>
      <p>工单不存在</p>
    </div>

    <!-- 图片预览遮罩 -->
    <div v-if="previewVisible" class="preview-mask" @click="previewVisible = false">
      <img :src="previewUrl" class="preview-img" @click.stop />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getTicketDetail, acceptTicket, checkinTicket } from '@/api/index'
import { STATUS_MAP, formatTime, getFacilityIcon } from '@/utils'
import { getHighAccuracyPosition, getLastPosition, isAccurateEnough, ACCURACY_THRESHOLD } from '@/utils/geolocation'

const route = useRoute()
const ticketId = route.params.id

const detail = ref({})
const loading = ref(true)
const acting = ref(false)
const errorMsg = ref('')

// 获取当前登录的维修员信息
const currentUser = computed(() => {
  try {
    const userStr = localStorage.getItem('worker_user')
    if (!userStr) return null
    return JSON.parse(userStr)
  } catch {
    return null
  }
})

// 判断是否是系统已指派给我的工单（dispatching 状态且 assigned_worker_id 是我）
const isAssignedToMe = computed(() => {
  if (detail.value.status !== 'dispatching') return false
  const workerId = detail.value.assigned_worker_id
  const myId = currentUser?.value?.user_id || currentUser?.value?.id
  return workerId && myId && workerId === myId
})

// 签到定位状态
const locating = ref(false)
const locationStatus = ref('') // 'searching' | 'good' | 'low' | 'failed'
const currentAccuracy = ref(null)

// 图片预览
const previewVisible = ref(false)
const previewUrl = ref('')

// ── AI 辅助信息 computed ──
const hasAiInsights = computed(() => {
  const ai = detail.value.ai || {}
  return !!(
    ai.issue_category || ai.ai_category || ai.category ||
    ai.key_info?.length || ai.suggested_action ||
    ai.repair_knowledge?.length || ai.tools_needed?.length ||
    ai.parts_needed?.length || ai.safety_tips?.length ||
    ai.urgency_reason
  )
})

const urgencyLabel = computed(() => {
  const lv = detail.value.ai?.urgency_level ?? detail.value.report?.emergency_level ?? 0
  if (lv >= 1) return '紧急'
  return '普通'
})

const urgencyClass = computed(() => {
  const lv = detail.value.ai?.urgency_level ?? detail.value.report?.emergency_level ?? 0
  if (lv >= 1) return 'chip-urgent'
  return 'chip-normal'
})

const confidenceLevel = computed(() => {
  const c = detail.value.ai?.ai_confidence || 0
  if (c >= 0.85) return 'conf-high'
  if (c >= 0.6) return 'conf-mid'
  return 'conf-low'
})

const priFillClass = computed(() => {
  const s = detail.value.ai?.priority_score || 0
  if (s >= 80) return 'pri-high'
  if (s >= 50) return 'pri-mid'
  return 'pri-low'
})

function isCurrent(i) {
  const timeline = detail.value.timeline || []
  const doneCount = timeline.filter(n => n.done).length
  return i === doneCount
}

function previewImage(url) {
  previewUrl.value = url
  previewVisible.value = true
}

async function loadDetail() {
  loading.value = true
  errorMsg.value = ''
  try {
    const data = await getTicketDetail(ticketId)
    detail.value = data || {}
  } catch (e) {
    errorMsg.value = e.message || '加载工单详情失败'
  } finally {
    loading.value = false
  }
}

async function handleAccept() {
  errorMsg.value = ''
  acting.value = true
  try {
    await acceptTicket(ticketId)
    await loadDetail()
  } catch (e) {
    errorMsg.value = e.message || '接单失败'
  } finally {
    acting.value = false
  }
}

async function handleCheckin() {
  if (!navigator.geolocation) {
    errorMsg.value = '浏览器不支持定位'
    return
  }
  errorMsg.value = ''
  acting.value = 'checkin'
  locating.value = true
  locationStatus.value = 'searching'
  currentAccuracy.value = null

  try {
    // 使用高精度定位，最多等待20秒
    const posResult = await getHighAccuracyPosition(20000)
    currentAccuracy.value = posResult.accuracy

    // 使用工具函数判断精度是否足够
    if (isAccurateEnough(posResult, ACCURACY_THRESHOLD.CHECKIN)) {
      locationStatus.value = 'good'
    } else {
      locationStatus.value = 'low'
    }

    // 进行签到
    await checkinTicket(ticketId, posResult.lng, posResult.lat)
    await loadDetail()
  } catch (e) {
    // 高精度定位失败，尝试使用最后一次有效位置
    const lastPos = getLastPosition()
    if (lastPos) {
      try {
        await checkinTicket(ticketId, lastPos.lng, lastPos.lat)
        await loadDetail()
        locationStatus.value = 'low'
      } catch (e2) {
        errorMsg.value = e2.message || '签到失败'
        locationStatus.value = 'failed'
      }
    } else {
      errorMsg.value = e.message || '签到失败'
      locationStatus.value = 'failed'
    }
  } finally {
    acting.value = false
    locating.value = false
  }
}

onMounted(loadDetail)
</script>

<style scoped>
.detail-page {
  padding: 0 16px 24px;
  max-width: 480px;
  margin: 0 auto;
}

/* ── 顶栏 ── */
.nav-bar { display: flex; align-items: center; justify-content: space-between; padding: 18px 0 14px; }
.btn-back { width: 36px; height: 36px; border-radius: 50%; background: var(--color-surface); border: 1px solid var(--color-border); display: flex; align-items: center; justify-content: center; color: var(--color-text-secondary); transition: border-color var(--duration-fast); }
.btn-back:active { border-color: var(--color-primary); }
.nav-title { font-size: 15px; font-weight: 600; color: var(--color-text); }
.nav-spacer { width: 36px; }

/* ── 加载 ── */
.loading-state { text-align: center; padding: 80px 0; color: var(--color-text-dim); display: flex; flex-direction: column; align-items: center; gap: 12px; }
.load-spinner { width: 32px; height: 32px; border: 3px solid var(--color-border); border-top-color: var(--color-primary); border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ── 状态大卡 ── */
.status-hero { border-radius: var(--radius-lg); padding: 22px 20px; margin-bottom: 14px; color: #fff; position: relative; overflow: hidden; }
.hero-pending { background: linear-gradient(135deg, #1a3a5c, #12243a); }
.hero-dispatching { background: linear-gradient(135deg, #3a2010, #1f1208); }
.hero-accepting { background: linear-gradient(135deg, #2d1b4e, #1a1030); }
.hero-repairing { background: linear-gradient(135deg, #3d2000, #1f1000); }
.hero-verifying { background: linear-gradient(135deg, #1a3a5c, #12243a); }
.hero-closed { background: linear-gradient(135deg, #0a3d1f, #051f10); }
.hero-top { display: flex; gap: 8px; margin-bottom: 10px; }
.hero-badge { font-size: 12px; padding: 3px 12px; border-radius: var(--radius-sm); background: rgba(255,255,255,0.15); font-weight: 500; }
.hero-emergency { font-size: 12px; padding: 3px 12px; border-radius: var(--radius-sm); background: rgba(255, 23, 68, 0.4); color: #ff8a80; font-weight: 500; }
.hero-id { font-size: 13px; opacity: 0.75; margin-bottom: 6px; }
.hero-desc { font-size: 15px; line-height: 1.6; margin-bottom: 10px; opacity: 0.95; }
.hero-meta { font-size: 12px; opacity: 0.6; display: flex; gap: 6px; flex-wrap: wrap; }
.meta-sep { opacity: 0.3; }

/* ── 报修照片卡 ── */
.photo-card { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-lg); padding: 18px; margin-bottom: 12px; }
.photo-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 12px; }
.photo-item { aspect-ratio: 1; border-radius: var(--radius-md); overflow: hidden; border: 1px solid var(--color-border); }
.photo-item img { width: 100%; height: 100%; object-fit: cover; display: block; }

/* ── 时间轴 ── */
.timeline-section, .info-card { background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-lg); padding: 18px; margin-bottom: 12px; }
.tl-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.tl-title { font-size: 14px; font-weight: 600; color: var(--color-text-secondary); letter-spacing: 1px; }
.tl-count { font-size: 11px; color: var(--color-text-dim); }

.timeline { display: flex; flex-direction: column; }
.tl-node { display: flex; gap: 12px; position: relative; padding-bottom: 18px; }
.tl-node:last-child { padding-bottom: 0; }

.tl-line { position: absolute; left: 11px; top: 28px; bottom: 4px; width: 2px; background: var(--color-border); }
.line-fill { width: 100%; height: 0; background: var(--color-success); transition: height 0.5s var(--ease-out-expo); }
.line-fill.filled { height: 100%; }

.tl-dot { width: 24px; height: 24px; border-radius: 50%; background: var(--color-bg); border: 2px solid var(--color-border); display: flex; align-items: center; justify-content: center; font-size: 11px; color: var(--color-text-dim); flex-shrink: 0; z-index: 1; transition: all var(--duration-normal); }
.tl-node.done .tl-dot { background: var(--color-success); border-color: var(--color-success); color: #fff; }
.tl-node.current .tl-dot { background: var(--color-primary); border-color: var(--color-primary); color: #fff; box-shadow: 0 0 12px rgba(255, 107, 0, 0.5); animation: dot-pulse 2s ease-in-out infinite; }
@keyframes dot-pulse { 0%, 100% { box-shadow: 0 0 12px rgba(255, 107, 0, 0.5); } 50% { box-shadow: 0 0 24px rgba(255, 107, 0, 0.7); } }
.dot-check { font-size: 12px; font-weight: 700; }
.dot-num { font-size: 10px; }

.tl-content { flex: 1; min-width: 0; }
.tl-label { display: block; font-size: 14px; font-weight: 600; color: var(--color-text-dim); transition: color var(--duration-normal); }
.tl-node.done .tl-label, .tl-node.current .tl-label { color: var(--color-text); }
.tl-time { display: block; font-size: 11px; color: var(--color-text-dim); margin-top: 2px; }
.tl-time.na { color: var(--color-text-dim); font-style: italic; }
.tl-detail { display: block; font-size: 11px; color: var(--color-text-dim); margin-top: 2px; font-style: italic; }

.tl-current-pulse { position: absolute; left: -1px; top: 4px; width: 32px; height: 32px; border-radius: 50%; border: 2px solid rgba(255, 107, 0, 0.2); animation: pulse-ripple 2.5s ease-out infinite; }
@keyframes pulse-ripple { 0% { transform: scale(1); opacity: 1; } 100% { transform: scale(2); opacity: 0; } }

/* ── AI 智能诊断面板 ── */
.ai-panel {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-left: 3px solid #7c4dff;
  border-radius: var(--radius-lg);
  padding: 18px;
  margin-bottom: 12px;
}

/* 置信度徽标 */
.ai-conf-badge {
  font-size: 10px;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-weight: 600;
  letter-spacing: 0.5px;
}
.conf-high { background: rgba(0,230,118,0.12); color: var(--color-success); }
.conf-mid  { background: rgba(255,184,0,0.12);  color: var(--color-warning); }
.conf-low  { background: rgba(255,23,68,0.10);  color: var(--color-danger); }

/* Row 1: 分类 + 紧急 */
.ai-classify-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.ai-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 12px;
  border-radius: var(--radius-full);
  font-size: 12px;
  font-weight: 500;
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
}
.ai-chip-icon { font-size: 14px; color: var(--color-primary); }
.ai-chip-cat { border-color: rgba(124,77,255,0.35); color: #b388ff; background: rgba(124,77,255,0.08); }
.ai-chip-sub { border-color: var(--color-border); color: var(--color-text-dim); font-size: 11px; }
.chip-urgent { border-color: rgba(255,23,68,0.4); color: #ff8a80; background: rgba(255,23,68,0.08); }
.chip-normal { border-color: rgba(0,230,118,0.25); color: var(--color-success); background: rgba(0,230,118,0.06); }
.ai-chip-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: currentColor;
}

/* Row 2: 优先级 */
.ai-priority {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
.ai-pri-label {
  font-size: 10px;
  color: var(--color-text-dim);
  letter-spacing: 2px;
  flex-shrink: 0;
}
.ai-pri-track {
  flex: 1;
  height: 6px;
  border-radius: 3px;
  background: rgba(255,255,255,0.06);
  overflow: hidden;
}
.ai-pri-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.8s var(--ease-out-expo);
}
.pri-high { background: linear-gradient(90deg, #ff6b00, #ff1744); }
.pri-mid  { background: linear-gradient(90deg, #ffb800, #ff6b00); }
.pri-low  { background: linear-gradient(90deg, #00e676, #69f0ae); }
.ai-pri-val {
  font-size: 11px;
  color: var(--color-text-dim);
  flex-shrink: 0;
}

/* Row 3: 紧急原因 */
.ai-reason {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 10px 12px;
  background: rgba(255,23,68,0.06);
  border: 1px solid rgba(255,23,68,0.15);
  border-radius: var(--radius-sm);
  margin-bottom: 12px;
  font-size: 12px;
  color: #ffcdd2;
  line-height: 1.5;
}
.ai-reason-icon { font-size: 14px; flex-shrink: 0; }

/* 标签行 */
.ai-tags-row { margin-bottom: 10px; }
.ai-tags-label {
  display: block;
  font-size: 10px;
  color: var(--color-text-dim);
  letter-spacing: 1px;
  text-transform: uppercase;
  margin-bottom: 6px;
}
.ai-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.ai-tag {
  display: inline-block;
  padding: 3px 10px;
  border-radius: var(--radius-full);
  font-size: 11px;
  font-weight: 500;
  line-height: 1.4;
}
.ai-tag-info      { background: rgba(41,121,255,0.10);  color: #82b1ff; border: 1px solid rgba(41,121,255,0.2); }
.ai-tag-knowledge { background: rgba(0,230,118,0.08);   color: #b9f6ca; border: 1px solid rgba(0,230,118,0.18); }
.ai-tag-tool      { background: rgba(255,184,0,0.08);   color: #ffe082; border: 1px solid rgba(255,184,0,0.18); }
.ai-tag-part      { background: rgba(124,77,255,0.08);  color: #b388ff; border: 1px solid rgba(124,77,255,0.18); }

/* Row 5: 建议操作 */
.ai-action-card {
  padding: 12px 14px;
  background: rgba(255,107,0,0.06);
  border: 1px solid rgba(255,107,0,0.2);
  border-radius: var(--radius-sm);
  margin-bottom: 12px;
}
.ai-action-label {
  display: block;
  font-size: 10px;
  color: var(--color-primary);
  letter-spacing: 1px;
  text-transform: uppercase;
  margin-bottom: 4px;
  font-weight: 600;
}
.ai-action-text {
  font-size: 13px;
  color: var(--color-text);
  line-height: 1.6;
  margin: 0;
}

/* Row 7: 工具 + 零件 双列 */
.ai-resource-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 10px;
}
.ai-resource-col { min-width: 0; }
.ai-resource-col .ai-tags-label { margin-bottom: 4px; }

/* Row 8: 安全提示 */
.ai-safety {
  background: rgba(255,184,0,0.05);
  border: 1px solid rgba(255,184,0,0.15);
  border-radius: var(--radius-sm);
  padding: 12px 14px;
}
.ai-safety-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
}
.ai-safety-icon { font-size: 14px; }
.ai-safety-title {
  font-size: 12px;
  font-weight: 600;
  color: #ffe082;
}
.ai-safety-list { display: flex; flex-direction: column; gap: 6px; }
.ai-safety-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 11px;
  color: var(--color-text-secondary);
  line-height: 1.5;
}
.ai-safety-bullet {
  width: 16px; height: 16px;
  border-radius: 50%;
  background: rgba(255,184,0,0.15);
  color: #ffe082;
  font-size: 10px;
  font-family: var(--font-mono);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 1px;
}

/* ── 信息卡 ── */
.info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.info-item { min-width: 0; }
.info-item.full { grid-column: 1 / -1; }
.info-label { display: block; font-size: 11px; color: var(--color-text-dim); letter-spacing: 0.5px; margin-bottom: 2px; }
.info-value { font-size: 14px; color: var(--color-text); }
.info-value.addr { font-size: 13px; color: var(--color-text-secondary); }
.info-value.ai { color: var(--color-primary); }

/* 耗材表 */
.materials-table { margin-top: 14px; }
.materials-title { display: block; font-size: 11px; color: var(--color-text-dim); margin-bottom: 8px; }
.materials-table table { width: 100%; border-collapse: collapse; font-size: 12px; }
.materials-table th, .materials-table td { padding: 6px 10px; text-align: left; border-bottom: 1px solid var(--color-border); }
.materials-table th { color: var(--color-text-dim); font-weight: 500; font-size: 11px; }
.materials-table td { color: var(--color-text); }

/* 完工照片 */
.photo-section { margin-top: 14px; }
.photo-label { display: block; font-size: 11px; color: var(--color-text-dim); margin-bottom: 8px; }

/* AI验收 */
.ai-result-card { display: flex; gap: 12px; padding: 14px; border-radius: var(--radius-md); margin-bottom: 12px; }
.ai-pass { background: rgba(0,230,118,0.06); border: 1px solid rgba(0,230,118,0.2); }
.ai-fail { background: rgba(255,23,68,0.06); border: 1px solid rgba(255,23,68,0.2); }
.ai-icon { font-size: 20px; font-weight: 700; }
.ai-pass .ai-icon { color: var(--color-success); }
.ai-fail .ai-icon { color: #ff1744; }
.ai-body { flex: 1; }
.ai-title { display: block; font-size: 13px; font-weight: 600; color: var(--color-text); }
.ai-conf, .ai-summary { display: block; font-size: 11px; color: var(--color-text-dim); margin-top: 2px; }

/* 结算 */
.settlement-card { border-left: 3px solid var(--color-primary); }
.tl-badge { font-size: 10px; padding: 2px 8px; border-radius: var(--radius-sm); font-weight: 600; }
.badge-green { background: var(--color-success-dim); color: var(--color-success); }
.badge-pending { background: var(--color-warning-dim); color: var(--color-warning); }
.settlement-grid { display: flex; align-items: center; gap: 10px; margin-top: 6px; }
.sett-item { flex: 1; text-align: center; background: var(--color-bg); border: 1px solid var(--color-border); border-radius: var(--radius-sm); padding: 12px 8px; }
.sett-total { border-color: rgba(255, 107, 0, 0.3); background: rgba(255, 107, 0, 0.06); }
.sett-value { display: block; font-size: 18px; font-weight: 700; color: var(--color-text); }
.sett-total .sett-value { color: var(--color-primary); }
.sett-label { display: block; font-size: 10px; color: var(--color-text-dim); margin-top: 2px; text-transform: uppercase; letter-spacing: 1px; }
.sett-op { font-size: 16px; color: var(--color-text-dim); font-family: var(--font-mono); flex-shrink: 0; }

/* 评价显示 */
.evaluation-card { border-left: 3px solid var(--color-warning); }
.evaluation-stars { display: flex; align-items: center; gap: 6px; margin-bottom: 10px; }
.evaluation-stars .star { font-size: 20px; color: var(--color-border); transition: color 0.2s; }
.evaluation-stars .star.filled { color: var(--color-warning); text-shadow: 0 0 8px rgba(255,184,0,0.4); }
.star-label { font-size: 13px; color: var(--color-text-dim); margin-left: 8px; font-family: var(--font-mono); }
.evaluation-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
.eval-tag { font-size: 11px; padding: 4px 10px; border-radius: var(--radius-full); background: var(--color-warning-dim); color: var(--color-warning); border: 1px solid rgba(255,184,0,0.2); }
.evaluation-comment { font-size: 13px; color: var(--color-text); line-height: 1.6; padding-top: 8px; border-top: 1px solid var(--color-border); }

/* ── 错误 ── */
.error-msg { display: flex; align-items: center; justify-content: center; gap: 8px; font-size: 13px; color: var(--color-danger); padding: 10px 16px; margin-bottom: 12px; background: var(--color-danger-dim); border: 1px solid rgba(255, 23, 68, 0.2); border-radius: var(--radius-md); }
.error-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--color-danger); box-shadow: 0 0 6px var(--color-danger); }

/* ── 操作按钮 ── */
.action-bar { display: flex; flex-direction: column; gap: 10px; margin-top: 2px; }
.btn-orange, .btn-outline, .btn-green { width: 100%; height: 50px; border-radius: var(--radius-sm); font-size: 15px; font-weight: 600; letter-spacing: 1px; display: flex; align-items: center; justify-content: center; transition: transform var(--duration-fast); }
.btn-orange { background: linear-gradient(135deg, #FF6B00, #E05500); color: #fff; box-shadow: 0 2px 14px rgba(255, 107, 0, 0.3); }
.btn-outline { background: transparent; border: 2px solid var(--color-primary); color: var(--color-primary); }
.btn-green { background: linear-gradient(135deg, #00C853, #009624); color: #fff; box-shadow: 0 2px 14px rgba(0, 230, 118, 0.3); }
.btn-orange:active, .btn-outline:active, .btn-green:active { transform: scale(0.97); }
.btn-orange:disabled, .btn-outline:disabled { opacity: 0.5; }

.btn-spinner, .btn-spinner-dark { width: 20px; height: 20px; border-radius: 50%; border: 2px solid rgba(255,255,255,0.25); border-top-color: #fff; animation: spin 0.6s linear infinite; }
.btn-spinner-dark { border-color: rgba(255, 107, 0, 0.2); border-top-color: var(--color-primary); }

/* ── 已完结 ── */
.action-done { margin-top: 2px; }
.done-card { display: flex; align-items: center; gap: 10px; padding: 16px 18px; border-radius: var(--radius-md); font-size: 14px; font-weight: 500; }
.done-green { background: var(--color-success-dim); border: 1px solid rgba(0, 230, 118, 0.2); color: var(--color-success); }
.done-blue { background: var(--color-info-dim); border: 1px solid rgba(41, 121, 255, 0.2); color: var(--color-info); }
.done-icon { font-size: 18px; font-weight: 700; }

/* ── 空状态 ── */
.empty-state { text-align: center; padding: 80px 0; color: var(--color-text-dim); }
.empty-visual { width: 72px; height: 72px; margin: 0 auto 14px; border-radius: 50%; background: var(--color-surface); border: 1px solid var(--color-border); display: flex; align-items: center; justify-content: center; }

/* ── 图片预览 ── */
.preview-mask { position: fixed; inset: 0; background: rgba(0,0,0,0.85); display: flex; align-items: center; justify-content: center; z-index: 9999; }
.preview-img { max-width: 90vw; max-height: 90vh; border-radius: var(--radius-md); }

/* ── 定位状态显示 ── */
.location-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
}
.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.status-dot.searching {
  background: var(--color-warning);
  box-shadow: 0 0 8px var(--color-warning);
  animation: pulse 1s ease-in-out infinite;
}
.status-dot.good {
  background: var(--color-success);
  box-shadow: 0 0 8px var(--color-success);
}
.status-dot.low {
  background: var(--color-warning);
  box-shadow: 0 0 8px var(--color-warning);
}
.status-dot.failed {
  background: var(--color-danger);
  box-shadow: 0 0 8px var(--color-danger);
}
.status-text {
  font-size: 12px;
  color: var(--color-text-dim);
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(1.1); }
}
</style>
