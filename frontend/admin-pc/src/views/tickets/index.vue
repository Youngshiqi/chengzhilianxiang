<!--
  城市设施运维指挥中心 — 工单全文检索
  ES全文搜索 + 多维度筛选 + 点击行查看详情弹窗
-->
<template>
  <div class="page">
    <div class="search-bar">
      <el-input v-model="keyword" placeholder="输入关键词检索工单..." size="large" class="search-input">
        <template #prefix><span style="color:var(--text-muted)">⌕</span></template>
      </el-input>
      <el-select v-model="status" placeholder="工单状态" clearable size="large" class="filter-select">
        <el-option label="全部状态" value="" />
        <el-option v-for="s in statusOptions" :key="s.value" :label="s.label" :value="s.value" />
      </el-select>
      <el-select v-model="facilityType" placeholder="设施类型" clearable size="large" class="filter-select">
        <el-option v-for="t in typeOptions" :key="t" :label="t" :value="t" />
      </el-select>
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        size="large"
        value-format="YYYY-MM-DD"
        class="date-picker"
      />
      <el-button type="primary" size="large" @click="search">检索</el-button>
    </div>

    <div class="table-wrap">
      <el-table :data="tickets" v-loading="loading" @row-click="openDetail" highlight-current-row>
        <el-table-column prop="ticket_id" label="工单号" width="160" />
        <el-table-column label="状态" width="90">
          <template #default="{row}">
            <span class="status-dot-cell" :class="row.status">{{ statusLabels[row.status] || row.status }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="facility_type" label="设施类型" width="100" />
        <el-table-column prop="address" label="地址" width="140" show-overflow-tooltip />
        <el-table-column label="故障描述" show-overflow-tooltip>
          <template #default="{row}">{{ (row.description || '').slice(0, 80) }}</template>
        </el-table-column>
        <el-table-column label="维修员" width="80">
          <template #default="{row}">{{ row.worker_name || '-' }}</template>
        </el-table-column>
        <el-table-column prop="emergency_level" label="紧急" width="60">
          <template #default="{row}">{{ row.emergency_level ? '⚠' : '-' }}</template>
        </el-table-column>
        <el-table-column label="创建时间" width="160">
          <template #default="{row}">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="{row}">
            <span @click.stop>
              <el-popover v-if="row.status === 'accepting'" placement="left" :width="200" trigger="click">
                <template #reference><el-button link type="primary" size="small">指派</el-button></template>
                <div @click.stop>
                  <el-select v-model="dispatchWorker[row.ticket_id]" placeholder="选择维修员" size="small" style="width:100%;margin-bottom:8px">
                    <el-option v-for="w in onlineWorkers" :key="w.worker_id" :label="w.name" :value="w.worker_id" />
                  </el-select>
                  <el-button type="warning" size="small" style="width:100%" @click.stop="doDispatch(row.ticket_id)">强制指派</el-button>
                </div>
              </el-popover>
              <span v-else class="no-dispatch-hint">—</span>
            </span>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination v-if="total > pageSize" :total="total" :page-size="pageSize" :current-page="page" layout="prev, pager, next" @current-change="onPageChange" />
    </div>

    <!-- ════════════════════════════════════════════════════════
         工单详情抽屉 — 指挥舱控制面板
         设计方向：深色控制舱 · 清晰信息层级 · 信号色引导视线
         ════════════════════════════════════════════════════════ -->
    <el-drawer
      v-model="drawerVisible"
      size="600px"
      :close-on-click-modal="true"
      direction="rtl"
      :with-header="false"
    >
      <!-- 加载态 -->
      <template v-if="detailLoading">
        <div class="drawer-skeleton">
          <div class="sk-hero"></div>
          <div class="sk-section">
            <div class="sk-line w-40"></div>
            <div class="sk-row"><div class="sk-box"></div><div class="sk-box"></div></div>
            <div class="sk-row"><div class="sk-box"></div><div class="sk-box"></div></div>
          </div>
          <div class="sk-section">
            <div class="sk-line w-30"></div>
            <div class="sk-row"><div class="sk-box"></div><div class="sk-box"></div></div>
          </div>
        </div>
      </template>

      <!-- 空态 -->
      <template v-else-if="!detailData.ticket_id">
        <div class="drawer-empty-state">
          <div class="empty-hexagon">!</div>
          <span class="empty-title">工单不存在</span>
          <span class="empty-subtitle">该工单可能已被删除或 ID 无效</span>
        </div>
      </template>

      <!-- 正常详情 -->
      <template v-else>
        <div class="drawer-scroll">

          <!-- ═══ 关闭按钮 ═══ -->
          <button class="drawer-close-btn" @click="drawerVisible = false" aria-label="关闭">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M4 4L12 12M12 4L4 12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          </button>

          <!-- ════════════════════════════════════════════════
               板块 1 — 状态头
               ════════════════════════════════════════════════ -->
          <div class="panel-hero" :class="'panel-hero--' + detailData.status">
            <div class="panel-hero__bg"></div>
            <div class="panel-hero__content">
              <div class="panel-hero__row1">
                <span class="status-chip" :class="'status-chip--' + detailData.status">
                  <span class="status-chip__dot"></span>
                  {{ detailData.status_label }}
                </span>
                <span v-if="detailData.report?.emergency_level" class="emergency-chip">
                  <span class="emergency-chip__pulse"></span>紧急
                </span>
              </div>
              <div class="panel-hero__id-row">
                <span class="panel-hero__ticket-id">{{ detailData.ticket_id }}</span>
                <button class="panel-hero__copy" @click="copyId(detailData.ticket_id)" title="复制工单号">
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><rect x="4" y="4" width="9" height="9" rx="1" stroke="currentColor" stroke-width="1.2"/><path d="M2 10V2h8" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>
                </button>
              </div>
              <div class="panel-hero__meta">
                <span class="panel-hero__time">{{ formatTime(detailData.created_at) }}</span>
                <span class="panel-hero__type">{{ detailData.report?.facility_type || '-' }}</span>
              </div>
            </div>
          </div>

          <!-- ════════════════════════════════════════════════
               板块 2 — 处理进度时间轴
               ════════════════════════════════════════════════ -->
          <div class="panel panel--timeline">
            <div class="panel__head">
              <div class="panel__head-left">
                <span class="panel__head-icon panel__head-icon--blue">◎</span>
                <span class="panel__head-title">处理进度</span>
              </div>
              <span class="panel__head-badge">{{ completedNodes }}/{{ detailData.timeline?.length || 0 }}</span>
            </div>
            <div class="panel__body">
              <div class="tl2">
                <div
                  v-for="(node, i) in detailData.timeline"
                  :key="i"
                  class="tl2-node"
                  :class="{
                    'tl2-node--done': node.done,
                    'tl2-node--active': isCurrentNode(node, i),
                    'tl2-node--pending': !node.done && !isCurrentNode(node, i)
                  }"
                >
                  <div class="tl2-gutter">
                    <div v-if="i < detailData.timeline.length - 1" class="tl2-line" :class="{ 'tl2-line--done': node.done }"></div>
                    <div class="tl2-dot">
                      <span v-if="node.done" class="tl2-dot__check">✓</span>
                      <span v-else-if="isCurrentNode(node, i)" class="tl2-dot__active"></span>
                      <span v-else class="tl2-dot__empty"></span>
                    </div>
                  </div>
                  <div class="tl2-body">
                    <div class="tl2-body__top">
                      <span class="tl2-body__label">{{ node.label }}</span>
                      <span v-if="node.time" class="tl2-body__time">{{ formatTime(node.time) }}</span>
                    </div>
                    <span v-if="node.detail" class="tl2-body__detail">{{ node.detail }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- ════════════════════════════════════════════════
               板块 3 — 报修信息
               ════════════════════════════════════════════════ -->
          <div class="panel panel--report">
            <div class="panel__head">
              <div class="panel__head-left">
                <span class="panel__head-icon panel__head-icon--amber">◆</span>
                <span class="panel__head-title">报修信息</span>
              </div>
            </div>
            <div class="panel__body">
              <!-- 关键字段：2 列网格 -->
              <div class="field-grid field-grid--2col">
                <div class="field">
                  <span class="field__label">报修人</span>
                  <span class="field__value">{{ detailData.report?.reporter_name || detailData.report?.reporter_id || '-' }}</span>
                </div>
                <div class="field">
                  <span class="field__label">联系电话</span>
                  <span class="field__value field__value--mono">{{ detailData.report?.reporter_phone || '-' }}</span>
                </div>
                <div class="field">
                  <span class="field__label">设施类型</span>
                  <span class="field__value">
                    <span class="tag tag--blue">{{ detailData.report?.facility_type || '-' }}</span>
                  </span>
                </div>
                <div class="field">
                  <span class="field__label">行政区</span>
                  <span class="field__value">{{ detailData.report?.district || '-' }}</span>
                </div>
                <div class="field field--wide">
                  <span class="field__label">报修地址</span>
                  <span class="field__value">{{ detailData.report?.address || '-' }}</span>
                </div>
                <div class="field">
                  <span class="field__label">报修时间</span>
                  <span class="field__value field__value--mono">{{ formatTime(detailData.report?.created_at) }}</span>
                </div>
                <div class="field">
                  <span class="field__label">AI 分类</span>
                  <span class="field__value">
                    {{ detailData.ai?.ai_category || '-' }}
                    <span v-if="detailData.ai?.ai_confidence" class="tag tag--green tag--sm">
                      {{ (detailData.ai.ai_confidence * 100).toFixed(0) }}%
                    </span>
                  </span>
                </div>
              </div>

              <!-- 故障描述面板 -->
              <div class="desc-panel">
                <div class="desc-panel__header">
                  <span class="desc-panel__icon">◈</span>
                  <span class="desc-panel__label">故障描述</span>
                </div>
                <p class="desc-panel__text">{{ detailData.report?.description || '暂无描述' }}</p>
              </div>

              <!-- 报修照片 -->
              <div v-if="detailData.report?.image_urls?.length" class="photos-section">
                <div class="photos-section__header">
                  <span>报修现场照片</span>
                  <span class="photos-section__count">{{ detailData.report.image_urls.length }}</span>
                </div>
                <div class="photos-section__grid">
                  <div
                    v-for="(url, i) in detailData.report.image_urls"
                    :key="i"
                    class="photo-item"
                    @click="previewImage(url)"
                  >
                    <img :src="url" :alt="'报修照片 ' + (i + 1)" loading="lazy" />
                    <div class="photo-item__overlay">
                      <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><circle cx="9" cy="9" r="4" stroke="white" stroke-width="1.5"/><path d="M12 12l4 4" stroke="white" stroke-width="1.5" stroke-linecap="round"/></svg>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- ════════════════════════════════════════════════
               板块 4 — 维修信息
               ════════════════════════════════════════════════ -->
          <div v-if="detailData.repair?.worker" class="panel panel--repair">
            <div class="panel__head">
              <div class="panel__head-left">
                <span class="panel__head-icon panel__head-icon--green">◈</span>
                <span class="panel__head-title">维修信息</span>
              </div>
            </div>
            <div class="panel__body">
              <!-- 维修员卡片 -->
              <div class="worker-profile">
                <div class="worker-profile__avatar">{{ (detailData.repair.worker.worker_name || '?')[0] }}</div>
                <div class="worker-profile__info">
                  <span class="worker-profile__name">{{ detailData.repair.worker.worker_name || '-' }}</span>
                  <span class="worker-profile__phone">{{ detailData.repair.worker.worker_phone || '-' }}</span>
                </div>
                <div class="worker-profile__stats">
                  <div class="worker-profile__stat">
                    <span class="worker-profile__stat-val">⭐ {{ detailData.repair.worker.star_rating || '-' }}</span>
                    <span class="worker-profile__stat-lbl">评分</span>
                  </div>
                  <div class="worker-profile__stat">
                    <span class="worker-profile__stat-val">{{ detailData.repair.worker.total_orders || 0 }}</span>
                    <span class="worker-profile__stat-lbl">工单</span>
                  </div>
                </div>
              </div>

              <!-- 维修时间轴 -->
              <div class="field-grid field-grid--2col" style="margin-top:16px">
                <div class="field">
                  <span class="field__label">签到时间</span>
                  <span class="field__value field__value--mono">{{ formatTime(detailData.repair.checkin_at) }}</span>
                </div>
                <div class="field">
                  <span class="field__label">完工时间</span>
                  <span class="field__value field__value--mono">{{ formatTime(detailData.repair.completed_at) }}</span>
                </div>
                <div class="field">
                  <span class="field__label">维修工时</span>
                  <span class="field__value field__value--highlight">{{ detailData.repair.labor_hours || 0 }}<span class="field__unit"> 小时</span></span>
                </div>
                <div class="field">
                  <span class="field__label">维修备注</span>
                  <span class="field__value">{{ detailData.repair.work_notes || '-' }}</span>
                </div>
              </div>

              <!-- 耗材清单 -->
              <div v-if="detailData.repair.materials?.length" class="sub-panel sub-panel--materials">
                <div class="sub-panel__header">
                  <span>耗材清单</span>
                  <span class="sub-panel__badge">{{ detailData.repair.materials.length }} 项</span>
                </div>
                <div class="materials-table-v2">
                  <div class="materials-table-v2__head">
                    <span class="col-name">名称</span>
                    <span class="col-qty">数量</span>
                    <span class="col-price">单价</span>
                    <span class="col-sub">小计</span>
                  </div>
                  <div class="materials-table-v2__row" v-for="(m, i) in detailData.repair.materials" :key="i">
                    <span class="col-name">{{ m.name }}</span>
                    <span class="col-qty">{{ m.qty }} <span class="unit">{{ m.unit }}</span></span>
                    <span class="col-price">¥{{ m.unit_cost?.toFixed(2) }}</span>
                    <span class="col-sub">¥{{ (m.qty * m.unit_cost).toFixed(2) }}</span>
                  </div>
                </div>
              </div>

              <!-- 完工照片 -->
              <div v-if="detailData.repair.completion_photos?.length" class="photos-section">
                <div class="photos-section__header">
                  <span>完工照片</span>
                  <span class="photos-section__count">{{ detailData.repair.completion_photos.length }}</span>
                </div>
                <div class="photos-section__grid">
                  <div
                    v-for="(url, i) in detailData.repair.completion_photos"
                    :key="i"
                    class="photo-item"
                    @click="previewImage(url)"
                  >
                    <img :src="url" :alt="'完工照片 ' + (i + 1)" loading="lazy" />
                    <div class="photo-item__overlay">
                      <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><circle cx="9" cy="9" r="4" stroke="white" stroke-width="1.5"/><path d="M12 12l4 4" stroke="white" stroke-width="1.5" stroke-linecap="round"/></svg>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- ════════════════════════════════════════════════
               板块 5 — AI 验收
               ════════════════════════════════════════════════ -->
          <div v-if="detailData.ai?.ai_verified !== null && detailData.ai?.ai_verified !== undefined" class="panel panel--ai">
            <div class="panel__head">
              <div class="panel__head-left">
                <span class="panel__head-icon" :class="detailData.ai.ai_verified ? 'panel__head-icon--green' : 'panel__head-icon--red'">◉</span>
                <span class="panel__head-title">AI 智能验收</span>
              </div>
              <span class="verdict-chip" :class="detailData.ai.ai_verified ? 'verdict-chip--pass' : 'verdict-chip--fail'">
                {{ detailData.ai.ai_verified ? '✓ 通过' : '✗ 未通过' }}
              </span>
            </div>
            <div class="panel__body">
              <div class="ai-result" :class="detailData.ai.ai_verified ? 'ai-result--pass' : 'ai-result--fail'">
                <div class="ai-result__icon">
                  <span v-if="detailData.ai.ai_verified">✓</span>
                  <span v-else>✗</span>
                </div>
                <div class="ai-result__content">
                  <div class="ai-result__row">
                    <span class="ai-result__label">验收结论</span>
                    <span class="ai-result__val" :class="detailData.ai.ai_verified ? 'text-green' : 'text-red'">
                      {{ detailData.ai.ai_verified ? '验收通过' : '验收未通过' }}
                    </span>
                  </div>
                  <div v-if="detailData.ai.ai_verify_confidence" class="ai-result__row">
                    <span class="ai-result__label">置信度</span>
                    <span class="ai-result__val">{{ (detailData.ai.ai_verify_confidence * 100).toFixed(0) }}%</span>
                  </div>
                  <div v-if="detailData.ai.ai_verify_summary" class="ai-result__summary">
                    {{ detailData.ai.ai_verify_summary }}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- ════════════════════════════════════════════════
               板块 6 — 结算信息
               ════════════════════════════════════════════════ -->
          <div v-if="detailData.settlement" class="panel panel--settlement">
            <div class="panel__head">
              <div class="panel__head-left">
                <span class="panel__head-icon panel__head-icon--amber">◎</span>
                <span class="panel__head-title">结算信息</span>
              </div>
            </div>
            <div class="panel__body">
              <div class="settlement-v2">
                <div class="settlement-v2__item">
                  <span class="settlement-v2__amount">¥{{ detailData.settlement.material_cost?.toFixed(2) }}</span>
                  <span class="settlement-v2__label">耗材费</span>
                </div>
                <span class="settlement-v2__op">+</span>
                <div class="settlement-v2__item">
                  <span class="settlement-v2__amount">¥{{ detailData.settlement.labor_cost?.toFixed(2) }}</span>
                  <span class="settlement-v2__label">劳务费</span>
                </div>
                <span class="settlement-v2__op">=</span>
                <div class="settlement-v2__item settlement-v2__item--total">
                  <span class="settlement-v2__amount settlement-v2__amount--total">¥{{ detailData.settlement.total_cost?.toFixed(2) }}</span>
                  <span class="settlement-v2__label">合计</span>
                </div>
              </div>
            </div>
          </div>

          <!-- ════════════════════════════════════════════════
               板块 7 — 市民评价
               ════════════════════════════════════════════════ -->
          <div v-if="detailData.evaluation" class="panel panel--evaluation">
            <div class="panel__head">
              <div class="panel__head-left">
                <span class="panel__head-icon panel__head-icon--green">◈</span>
                <span class="panel__head-title">市民评价</span>
              </div>
            </div>
            <div class="panel__body">
              <div class="evaluation-panel">
                <div class="evaluation-header">
                  <div class="star-display">
                    <span v-for="s in 5" :key="s" class="star" :class="{ filled: s <= detailData.evaluation.star }">★</span>
                    <span class="star-score">{{ detailData.evaluation.star }}.0</span>
                  </div>
                  <span class="eval-time">{{ formatTime(detailData.evaluation.created_at) }}</span>
                </div>
                <div v-if="detailData.evaluation.tags?.length" class="tag-row">
                  <span v-for="tag in detailData.evaluation.tags" :key="tag" class="eval-tag">{{ tag }}</span>
                </div>
                <div v-if="detailData.evaluation.comment" class="comment-text">{{ detailData.evaluation.comment }}</div>
              </div>
            </div>
          </div>

          <!-- 底部安全间距 -->
          <div class="drawer-bottom-safe"></div>
        </div>
      </template>
    </el-drawer>

    <!-- 图片预览 -->
    <el-dialog v-model="previewVisible" width="auto" :show-close="true" :close-on-click-modal="true">
      <img :src="previewUrl" style="max-width:80vw;max-height:80vh;display:block;border-radius:4px" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { searchTickets, forceDispatch, getWorkers, getTicketDetail } from '@/api/index'
import { formatTime } from '@/utils'

const keyword = ref(''), status = ref(''), facilityType = ref(''), dateRange = ref(null)
const statusOptions = [
  { label: '待受理', value: 'pending' }, { label: '派单中', value: 'accepting' }, { label: '已接单', value: 'dispatching' },
  { label: '维修中', value: 'repairing' }, { label: '验收中', value: 'verifying' }, { label: '已完结', value: 'closed' },
]
const typeOptions = ['路灯','井盖','护栏','信号灯','公交站牌','消防栓','公厕','指示牌','垃圾桶','健身器材']
const statusLabels = { pending: '待受理', accepting: '派单中', dispatching: '已接单', repairing: '维修中', verifying: '验收中', closed: '已完结' }

const tickets = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(false)
const dispatchWorker = reactive({})
const onlineWorkers = ref([])

// 详情抽屉
const drawerVisible = ref(false)
const detailLoading = ref(false)
const detailData = ref({})

// 图片预览
const previewVisible = ref(false)
const previewUrl = ref('')

// 已完成时间轴节点数
const completedNodes = computed(() => {
  if (!detailData.value.timeline) return 0
  return detailData.value.timeline.filter(n => n.done).length
})

// 判断当前正在进行的节点（第一个未完成的）
function isCurrentNode(node, index) {
  if (node.done) return false
  const timeline = detailData.value.timeline || []
  // 前面全部完成，当前就是进行中的
  return timeline.slice(0, index).every(n => n.done)
}

async function fetch() {
  loading.value = true
  try {
    const res = await searchTickets({
      keyword: keyword.value, status: status.value,
      facility_type: facilityType.value,
      date_from: dateRange.value?.[0] || '',
      date_to: dateRange.value?.[1] || '',
      page: page.value, page_size: pageSize,
    })
    tickets.value = res.data.items || []
    total.value = res.data.total || 0
  } catch (e) {
    console.error('工单检索失败:', e)
  } finally { loading.value = false }
}

async function loadWorkers() {
  try {
    const res = await getWorkers({ page_size: 100 })
    onlineWorkers.value = (res.data.items || []).filter(w => w.is_active !== false)
  } catch (e) {
    console.error('在线维修员加载失败:', e)
  }
}

function search() { page.value = 1; fetch() }
function onPageChange(p) { page.value = p; fetch() }

async function doDispatch(ticketId) {
  const wid = dispatchWorker[ticketId]
  if (!wid) { ElMessage.warning('请先选择维修员'); return }
  try {
    await forceDispatch(ticketId, wid)
    ElMessage.success('强制指派成功')
    dispatchWorker[ticketId] = ''
    fetch()
  } catch (e) {
    console.error('强制指派失败:', e)
  }
}

async function openDetail(row) {
  drawerVisible.value = true
  detailLoading.value = true
  detailData.value = {}
  try {
    const res = await getTicketDetail(row.ticket_id)
    detailData.value = res.data || {}
  } catch (e) {
    console.error('加载工单详情失败:', e)
    ElMessage.error('加载工单详情失败')
  } finally {
    detailLoading.value = false
  }
}

function previewImage(url) {
  previewUrl.value = url
  previewVisible.value = true
}

function copyId(id) {
  navigator.clipboard?.writeText(id).then(() => {
    ElMessage.success('工单号已复制')
  }).catch(() => {
    ElMessage.info('复制失败，请手动复制')
  })
}

onMounted(() => { fetch(); loadWorkers() })
</script>

<style scoped>
/* ════════════════════════════════════════════════════════
   搜索 & 表格区域（保持不变）
   ════════════════════════════════════════════════════════ */
.page { display: flex; flex-direction: column; gap: 16px; }
.search-bar { display: flex; gap: 10px; align-items: center; }
.search-input { flex: 1; }
.filter-select { width: 160px; flex-shrink: 0; }
.date-picker { width: 360px; flex-shrink: 0; }
.table-wrap { background: var(--bg-elevated); border: 1px solid var(--border-dim); border-radius: var(--radius-lg); padding: 20px; }
.status-dot-cell { font-family: var(--font-mono); font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 2px; }
.status-dot-cell.pending { background: rgba(51,153,255,.12); color: var(--signal-blue); }
.status-dot-cell.accepting { background: rgba(255,106,0,.12); color: var(--signal-amber); }
.status-dot-cell.dispatching { background: rgba(156,39,176,.12); color: #9c27b0; }
.status-dot-cell.repairing { background: rgba(255,184,0,.12); color: var(--signal-yellow); }
.status-dot-cell.verifying { background: rgba(51,153,255,.1); color: #66b3ff; }
.status-dot-cell.closed { background: rgba(0,196,140,.1); color: var(--signal-green); }
.no-dispatch-hint { color: var(--text-muted); font-size: 12px; }

/* ════════════════════════════════════════════════════════
   详情抽屉 — 全局
   设计方向：深色控制舱面板 · 板块间大分隔 · 信号色视觉引导
   ════════════════════════════════════════════════════════ */

:deep(.el-drawer__body) {
  padding: 0 !important;
  overflow: hidden;
  background: var(--bg-base);
}

/* 可滚动容器 */
.drawer-scroll {
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
}

/* ═══ 骨架屏加载态 ═══ */
.drawer-skeleton {
  padding: 0;
}
.sk-hero {
  height: 100px;
  background: var(--bg-elevated);
  animation: sk-shimmer 1.8s infinite;
}
.sk-section {
  padding: 20px 24px;
  border-bottom: 6px solid var(--bg-base);
  display: flex; flex-direction: column; gap: 12px;
}
.sk-line {
  height: 12px;
  background: var(--bg-surface);
  border-radius: 2px;
  animation: sk-shimmer 1.8s infinite;
}
.sk-line.w-40 { width: 40%; }
.sk-line.w-30 { width: 30%; }
.sk-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.sk-box {
  height: 48px;
  background: var(--bg-elevated);
  border-radius: 2px;
  animation: sk-shimmer 1.8s infinite;
}
@keyframes sk-shimmer {
  0%   { opacity: 0.4; }
  50%  { opacity: 0.7; }
  100% { opacity: 0.4; }
}

/* ═══ 空态 ═══ */
.drawer-empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 12px;
}
.empty-hexagon {
  width: 56px; height: 56px;
  display: flex; align-items: center; justify-content: center;
  font-family: var(--font-mono);
  font-size: 24px; font-weight: 700;
  color: var(--text-muted);
  border: 2px solid var(--border-dim);
  border-radius: 50%;
}
.empty-title {
  font-size: 15px; font-weight: 600;
  color: var(--text-secondary);
}
.empty-subtitle {
  font-size: 12px;
  color: var(--text-muted);
}

/* ═══ 关闭按钮 ═══ */
.drawer-close-btn {
  position: fixed;
  top: 14px; right: 14px; z-index: 20;
  width: 32px; height: 32px;
  display: flex; align-items: center; justify-content: center;
  background: rgba(15,17,23,0.85);
  backdrop-filter: blur(8px);
  border: 1px solid var(--border-dim);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  cursor: pointer;
  transition: all var(--duration-fast) var(--ease-out-expo);
}
.drawer-close-btn:hover {
  background: var(--bg-surface);
  color: var(--text-primary);
  border-color: var(--border-active);
}

/* ════════════════════════════════════════════════════════
   板块容器 — 通用
   ════════════════════════════════════════════════════════ */
.panel {
  border-bottom: 6px solid var(--bg-base);
}
.panel:last-of-type {
  border-bottom: none;
}
.panel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px 12px;
}
.panel__head-left {
  display: flex; align-items: center; gap: 8px;
}
.panel__head-icon {
  font-size: 10px;
  display: flex; align-items: center;
}
.panel__head-icon--amber { color: var(--signal-amber); }
.panel__head-icon--blue  { color: var(--signal-blue); }
.panel__head-icon--green { color: var(--signal-green); }
.panel__head-icon--red   { color: var(--signal-red); }
.panel__head-title {
  font-family: var(--font-mono);
  font-size: 11px; font-weight: 600;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--text-secondary);
}
.panel__head-badge {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-muted);
  background: var(--bg-surface);
  padding: 2px 8px;
  border-radius: 9px;
}
.panel__body {
  padding: 0 24px 20px;
}

/* ════════════════════════════════════════════════════════
   板块 1 — 状态英雄头
   ════════════════════════════════════════════════════════ */
.panel-hero {
  position: relative;
  overflow: hidden;
  padding: 24px;
}
.panel-hero__bg {
  position: absolute; inset: 0;
  opacity: 0.5;
}
/* 各状态背景渐变 */
.panel-hero--pending     { background: linear-gradient(160deg, #0d2137 0%, #0a1624 40%, var(--bg-base) 100%); }
.panel-hero--accepting   { background: linear-gradient(160deg, #26160a 0%, #1a0f06 40%, var(--bg-base) 100%); }
.panel-hero--dispatching { background: linear-gradient(160deg, #1a0a26 0%, #11061a 40%, var(--bg-base) 100%); }
.panel-hero--repairing   { background: linear-gradient(160deg, #241a00 0%, #181000 40%, var(--bg-base) 100%); }
.panel-hero--verifying   { background: linear-gradient(160deg, #0d2137 0%, #0a1624 40%, var(--bg-base) 100%); }
.panel-hero--closed      { background: linear-gradient(160deg, #082418 0%, #04160c 40%, var(--bg-base) 100%); }

.panel-hero__content {
  position: relative; z-index: 1;
  display: flex; flex-direction: column; gap: 12px;
}
.panel-hero__row1 {
  display: flex; align-items: center; gap: 10px;
}
.panel-hero__id-row {
  display: flex; align-items: center; gap: 8px;
}
.panel-hero__ticket-id {
  font-family: var(--font-mono);
  font-size: 22px; font-weight: 600;
  color: #fff;
  letter-spacing: 1px;
  line-height: 1;
}
.panel-hero__copy {
  width: 28px; height: 28px;
  display: flex; align-items: center; justify-content: center;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: var(--radius-sm);
  color: rgba(255,255,255,0.4);
  cursor: pointer;
  transition: all var(--duration-fast);
  flex-shrink: 0;
}
.panel-hero__copy:hover {
  background: rgba(255,255,255,0.12);
  color: rgba(255,255,255,0.8);
  border-color: rgba(255,255,255,0.2);
}
.panel-hero__meta {
  display: flex; align-items: center; gap: 14px;
}
.panel-hero__time {
  font-family: var(--font-mono);
  font-size: 12px;
  color: rgba(255,255,255,0.45);
}
.panel-hero__type {
  font-size: 11px;
  color: rgba(255,255,255,0.4);
  padding: 2px 8px;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 2px;
}

/* 状态 chip */
.status-chip {
  display: inline-flex; align-items: center; gap: 6px;
  font-family: var(--font-mono);
  font-size: 11px; font-weight: 700;
  letter-spacing: 2px;
  text-transform: uppercase;
  padding: 5px 14px;
  border-radius: var(--radius-sm);
}
.status-chip__dot {
  width: 6px; height: 6px;
  border-radius: 50%;
}
.status-chip--pending {
  background: rgba(51,153,255,0.18);
  color: var(--signal-blue);
}
.status-chip--pending .status-chip__dot { background: var(--signal-blue); box-shadow: 0 0 6px rgba(51,153,255,0.5); }

.status-chip--accepting {
  background: rgba(255,106,0,0.18);
  color: var(--signal-amber);
}
.status-chip--accepting .status-chip__dot { background: var(--signal-amber); box-shadow: 0 0 6px rgba(255,106,0,0.5); }

.status-chip--dispatching {
  background: rgba(156,39,176,0.18);
  color: #9c27b0;
}
.status-chip--dispatching .status-chip__dot { background: #9c27b0; box-shadow: 0 0 6px rgba(156,39,176,0.5); }

.status-chip--repairing {
  background: rgba(255,184,0,0.18);
  color: var(--signal-yellow);
}
.status-chip--repairing .status-chip__dot { background: var(--signal-yellow); box-shadow: 0 0 6px rgba(255,184,0,0.5); }

.status-chip--verifying {
  background: rgba(51,153,255,0.15);
  color: #66b3ff;
}
.status-chip--verifying .status-chip__dot { background: #66b3ff; box-shadow: 0 0 6px rgba(102,179,255,0.5); }

.status-chip--closed {
  background: rgba(0,196,140,0.15);
  color: var(--signal-green);
}
.status-chip--closed .status-chip__dot { background: var(--signal-green); box-shadow: 0 0 6px rgba(0,196,140,0.5); }

/* 紧急 chip */
.emergency-chip {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 11px; font-weight: 600;
  padding: 5px 10px;
  border-radius: var(--radius-sm);
  background: rgba(255,23,68,0.2);
  color: #ff8a80;
  border: 1px solid rgba(255,23,68,0.25);
}
.emergency-chip__pulse {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: #ff1744;
  box-shadow: 0 0 8px rgba(255,23,68,0.6);
  animation: emergency-pulse 1.5s infinite;
}
@keyframes emergency-pulse { 0%,100%{opacity:1} 50%{opacity:.3} }

/* ════════════════════════════════════════════════════════
   板块 2 — 时间轴 v2
   ════════════════════════════════════════════════════════ */
.tl2 {
  display: flex;
  flex-direction: column;
}
.tl2-node {
  display: flex;
  gap: 12px;
}
.tl2-gutter {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 24px;
  flex-shrink: 0;
  position: relative;
}
.tl2-line {
  position: absolute;
  top: 26px;
  bottom: -4px;
  width: 1.5px;
  background: var(--border-dim);
  border-radius: 1px;
}
.tl2-line--done {
  background: var(--signal-green);
}
.tl2-node:last-child .tl2-line {
  display: none;
}
.tl2-dot {
  width: 24px; height: 24px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  z-index: 1;
  transition: all 0.35s var(--ease-out-expo);
}
.tl2-node--done .tl2-dot {
  background: var(--signal-green);
  box-shadow: 0 0 10px rgba(0,196,140,0.35);
}
.tl2-node--active .tl2-dot {
  border: 2px solid var(--signal-amber);
  background: var(--bg-base);
  box-shadow: 0 0 14px rgba(255,106,0,0.45);
  animation: tl-active-glow 2s infinite;
}
@keyframes tl-active-glow {
  0%,100% { box-shadow: 0 0 8px rgba(255,106,0,0.3); }
  50%     { box-shadow: 0 0 18px rgba(255,106,0,0.6); }
}
.tl2-node--pending .tl2-dot {
  border: 2px solid var(--border-dim);
  background: var(--bg-base);
}
.tl2-dot__check {
  font-size: 11px; color: #fff; font-weight: 700; line-height: 1;
}
.tl2-dot__active {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--signal-amber);
}
.tl2-dot__empty {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--border-dim);
}

.tl2-body {
  flex: 1; min-width: 0;
  padding-bottom: 18px;
}
.tl2-body__top {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}
.tl2-body__label {
  font-size: 13px; font-weight: 600;
  color: var(--text-muted);
  letter-spacing: 0.3px;
  transition: color 0.3s;
  white-space: nowrap;
}
.tl2-node--done .tl2-body__label   { color: var(--text-secondary); }
.tl2-node--active .tl2-body__label { color: var(--text-primary); }

.tl2-body__time {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--text-muted);
  white-space: nowrap;
  flex-shrink: 0;
}
.tl2-body__detail {
  display: block;
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 4px;
  line-height: 1.6;
  font-style: italic;
}

/* ════════════════════════════════════════════════════════
   板块 3 — 报修信息 · 字段网格
   ════════════════════════════════════════════════════════ */
.field-grid {
  display: grid;
  gap: 6px;
}
.field-grid--2col {
  grid-template-columns: 1fr 1fr;
}

.field {
  background: var(--bg-elevated);
  border: 1px solid var(--border-dim);
  border-radius: var(--radius-sm);
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.field--wide {
  grid-column: 1 / -1;
}
.field__label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--text-muted);
}
.field__value {
  font-size: 13px;
  color: var(--text-primary);
  line-height: 1.5;
}
.field__value--mono {
  font-family: var(--font-mono);
  font-size: 12px;
}
.field__value--highlight {
  color: var(--signal-amber);
  font-weight: 600;
  font-size: 15px;
}
.field__unit {
  font-size: 11px;
  font-weight: 400;
  color: var(--text-muted);
}

/* 标签 */
.tag {
  display: inline-block;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 2px;
}
.tag--blue {
  background: rgba(51,153,255,0.12);
  color: var(--signal-blue);
}
.tag--green {
  background: rgba(0,196,140,0.12);
  color: var(--signal-green);
}
.tag--sm {
  font-size: 10px;
  padding: 1px 6px;
  margin-left: 6px;
}

/* 故障描述面板 */
.desc-panel {
  margin-top: 8px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-dim);
  border-radius: var(--radius-sm);
  padding: 14px;
}
.desc-panel__header {
  display: flex; align-items: center; gap: 6px;
  margin-bottom: 8px;
}
.desc-panel__icon {
  font-size: 10px;
  color: var(--signal-amber);
}
.desc-panel__label {
  font-size: 10px; font-weight: 600;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--text-muted);
}
.desc-panel__text {
  font-size: 13px;
  color: var(--text-primary);
  line-height: 1.8;
  margin: 0;
}

/* 照片区域 */
.photos-section {
  margin-top: 14px;
}
.photos-section__header {
  display: flex; align-items: center; gap: 8px;
  font-size: 10px; font-weight: 600;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--text-muted);
  margin-bottom: 10px;
}
.photos-section__count {
  font-family: var(--font-mono);
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 9px;
  background: var(--bg-surface);
  color: var(--text-muted);
}
.photos-section__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.photo-item {
  aspect-ratio: 1;
  border-radius: var(--radius-md);
  overflow: hidden;
  cursor: pointer;
  border: 1px solid var(--border-dim);
  position: relative;
  transition: border-color 0.2s;
  background: var(--bg-surface);
}
.photo-item:hover {
  border-color: var(--signal-amber);
}
.photo-item img {
  width: 100%; height: 100%;
  object-fit: cover;
  transition: transform 0.35s var(--ease-out-expo);
}
.photo-item:hover img {
  transform: scale(1.06);
}
.photo-item__overlay {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  background: rgba(0,0,0,0.55);
  opacity: 0;
  transition: opacity 0.2s;
}
.photo-item:hover .photo-item__overlay {
  opacity: 1;
}

/* ════════════════════════════════════════════════════════
   板块 4 — 维修信息
   ════════════════════════════════════════════════════════ */

/* 维修员卡片 */
.worker-profile {
  display: flex; align-items: center; gap: 14px;
  background: var(--bg-elevated);
  border: 1px solid var(--border-dim);
  border-radius: var(--radius-md);
  padding: 14px 16px;
}
.worker-profile__avatar {
  width: 44px; height: 44px;
  border-radius: 50%;
  background: linear-gradient(135deg, #e65c00, #993d00);
  display: flex; align-items: center; justify-content: center;
  font-size: 20px; font-weight: 700;
  color: #fff;
  flex-shrink: 0;
}
.worker-profile__info {
  flex: 1; min-width: 0;
  display: flex; flex-direction: column; gap: 3px;
}
.worker-profile__name {
  font-size: 14px; font-weight: 600; color: var(--text-primary);
}
.worker-profile__phone {
  font-family: var(--font-mono);
  font-size: 11px; color: var(--text-muted);
}
.worker-profile__stats {
  display: flex; gap: 18px;
}
.worker-profile__stat {
  display: flex; flex-direction: column; align-items: center; gap: 2px;
}
.worker-profile__stat-val {
  font-family: var(--font-mono);
  font-size: 13px; font-weight: 600;
  color: var(--text-primary);
}
.worker-profile__stat-lbl {
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--text-muted);
}

/* 子面板（耗材清单） */
.sub-panel {
  margin-top: 14px;
}
.sub-panel__header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 8px;
  font-size: 10px; font-weight: 600;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--text-muted);
}
.sub-panel__badge {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 500;
  color: var(--text-muted);
}

/* 耗材表格 v2 */
.materials-table-v2 {
  border: 1px solid var(--border-dim);
  border-radius: var(--radius-sm);
  overflow: hidden;
}
.materials-table-v2__head {
  display: grid;
  grid-template-columns: 1fr 80px 80px 80px;
  gap: 0;
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-dim);
  padding: 9px 12px;
  font-size: 10px; font-weight: 600;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--text-muted);
}
.materials-table-v2__row {
  display: grid;
  grid-template-columns: 1fr 80px 80px 80px;
  gap: 0;
  padding: 10px 12px;
  font-size: 12px;
  color: var(--text-primary);
  border-bottom: 1px solid rgba(46,49,58,0.4);
  transition: background 0.15s;
}
.materials-table-v2__row:last-child {
  border-bottom: none;
}
.materials-table-v2__row:hover {
  background: rgba(255,106,0,0.04);
}
.materials-table-v2 .col-name { text-align: left; }
.materials-table-v2 .col-qty  { text-align: right; font-family: var(--font-mono); }
.materials-table-v2 .col-price { text-align: right; font-family: var(--font-mono); }
.materials-table-v2 .col-sub  { text-align: right; font-family: var(--font-mono); font-weight: 600; }
.materials-table-v2 .unit {
  font-size: 10px;
  color: var(--text-muted);
  margin-left: 2px;
}

/* ════════════════════════════════════════════════════════
   板块 5 — AI 验收
   ════════════════════════════════════════════════════════ */
.verdict-chip {
  font-family: var(--font-mono);
  font-size: 11px; font-weight: 600;
  padding: 3px 10px;
  border-radius: var(--radius-sm);
}
.verdict-chip--pass {
  background: rgba(0,196,140,0.12);
  color: var(--signal-green);
}
.verdict-chip--fail {
  background: rgba(255,23,68,0.12);
  color: #ff5252;
}

.ai-result {
  display: flex; gap: 14px;
  padding: 16px;
  border-radius: var(--radius-md);
  border: 1px solid;
}
.ai-result--pass {
  background: rgba(0,196,140,0.05);
  border-color: rgba(0,196,140,0.18);
}
.ai-result--fail {
  background: rgba(255,23,68,0.05);
  border-color: rgba(255,23,68,0.18);
}
.ai-result__icon {
  width: 42px; height: 42px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  font-size: 20px; font-weight: 700;
}
.ai-result--pass .ai-result__icon {
  background: rgba(0,196,140,0.12);
  color: var(--signal-green);
}
.ai-result--fail .ai-result__icon {
  background: rgba(255,23,68,0.12);
  color: #ff5252;
}
.ai-result__content {
  flex: 1;
  display: flex; flex-direction: column; gap: 6px;
}
.ai-result__row {
  display: flex; align-items: baseline; gap: 12px;
}
.ai-result__label {
  font-size: 11px;
  color: var(--text-muted);
  min-width: 56px;
}
.ai-result__val {
  font-size: 13px; font-weight: 600;
  color: var(--text-primary);
}
.ai-result__val.text-green { color: var(--signal-green); }
.ai-result__val.text-red   { color: #ff5252; }

.ai-result__summary {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.7;
  font-style: italic;
  margin-top: 2px;
  padding-top: 8px;
  border-top: 1px solid var(--border-dim);
}

/* ════════════════════════════════════════════════════════
   板块 6 — 结算
   ════════════════════════════════════════════════════════ */
.settlement-v2 {
  display: flex;
  align-items: center;
  gap: 12px;
}
.settlement-v2__item {
  flex: 1;
  background: var(--bg-elevated);
  border: 1px solid var(--border-dim);
  border-radius: var(--radius-sm);
  padding: 16px 14px;
  display: flex; flex-direction: column; align-items: center; gap: 4px;
}
.settlement-v2__item--total {
  border-color: rgba(255,106,0,0.35);
  background: rgba(255,106,0,0.08);
  box-shadow: 0 0 20px rgba(255,106,0,0.06);
}
.settlement-v2__amount {
  font-family: var(--font-mono);
  font-size: 18px; font-weight: 700;
  color: var(--text-primary);
}
.settlement-v2__amount--total {
  color: var(--signal-amber);
  font-size: 20px;
}
.settlement-v2__label {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: var(--text-muted);
}
.settlement-v2__op {
  font-family: var(--font-mono);
  font-size: 18px;
  color: var(--text-muted);
  flex-shrink: 0;
}

/* ════════════════════════════════════════════════════════
   板块 7 — 市民评价
   ════════════════════════════════════════════════════════ */
.evaluation-panel {
  background: var(--bg-elevated);
  border: 1px solid var(--border-dim);
  border-radius: var(--radius-md);
  padding: 16px;
}
.evaluation-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}
.star-display {
  display: flex;
  align-items: center;
  gap: 8px;
}
.star {
  font-size: 20px;
  color: var(--border-dim);
  transition: color 0.2s;
}
.star.filled {
  color: var(--signal-amber);
  text-shadow: 0 0 8px rgba(255,106,0,0.3);
}
.star-score {
  font-family: var(--font-mono);
  font-size: 18px;
  font-weight: 700;
  color: var(--signal-amber);
}
.eval-time {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-muted);
}
.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}
.eval-tag {
  font-size: 11px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 12px;
  background: rgba(0,196,140,0.12);
  color: var(--signal-green);
  border: 1px solid rgba(0,196,140,0.25);
}
.comment-text {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.7;
  padding-top: 12px;
  border-top: 1px solid var(--border-dim);
}

/* ════════════════════════════════════════════════════════
   底部
   ════════════════════════════════════════════════════════ */
.drawer-bottom-safe {
  height: 32px;
}

/* ════════════════════════════════════════════════════════
   响应式
   ════════════════════════════════════════════════════════ */
@media (max-width: 767px) {
  .search-bar { flex-direction: column; }
  .search-input { width: 100%; }
  .filter-select, .date-picker, .search-bar .el-button { width: 100%; }

  .panel__head  { padding: 14px 16px 10px; }
  .panel__body  { padding: 0 16px 16px; }
  .panel-hero   { padding: 20px 16px; }
  .panel-hero__ticket-id { font-size: 16px; }

  .field-grid--2col { grid-template-columns: 1fr; }
  .photos-section__grid { grid-template-columns: repeat(2, 1fr); }

  .settlement-v2 { flex-direction: column; gap: 8px; }
  .settlement-v2__op { transform: rotate(90deg); }

  .materials-table-v2__head,
  .materials-table-v2__row {
    grid-template-columns: 1fr 60px 60px 60px;
  }
}
</style>
