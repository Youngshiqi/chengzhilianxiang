<!--
  城市设施运维指挥中心 — 操作审计
  面向非技术人员的可读审计日志
-->
<template>
  <div class="page">
    <div class="search-bar">
      <el-input v-model="operatorId" placeholder="操作人ID" size="large" style="width:180px" clearable />
      <el-select v-model="action" placeholder="操作类型" clearable size="large" style="width:180px">
        <el-option label="全部操作" value="" />
        <el-option v-for="a in actions" :key="a.value" :label="a.label" :value="a.value" />
      </el-select>
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        size="large"
        value-format="YYYY-MM-DD"
        style="width:280px"
      />
      <el-button type="primary" size="large" @click="fetch">查询</el-button>
    </div>

    <div class="table-wrap">
      <el-table :data="logs" v-loading="loading" row-key="_id" class="audit-table" table-layout="auto">
        <el-table-column label="操作时间" width="155">
          <template #default="{row}">
            <span class="time-text">{{ formatTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作人" min-width="140">
          <template #default="{row}">
            <div class="op-row">
              <span class="op-name">{{ row.operator_id || '系统' }}</span>
              <span class="op-role">{{ roleLabel(row.role) }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作类型" width="100">
          <template #default="{row}">
            <span class="action-badge" :class="actionClass(row.action)">{{ actionLabel(row.action) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作对象" min-width="140" show-overflow-tooltip>
          <template #default="{row}">
            <span class="target-text">{{ targetText(row) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="变更摘要" min-width="200" show-overflow-tooltip>
          <template #default="{row}">
            <span class="change-summary">{{ changeSummary(row) }}</span>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-if="total > pageSize"
        :total="total" :page-size="pageSize" :current-page="page"
        layout="prev, pager, next" @current-change="onPageChange"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getAuditLogs } from '@/api/index'
import { formatTime } from '@/utils'

const operatorId = ref(''), action = ref(''), dateRange = ref(null)

// ── 操作类型 ──
const ACTION_MAP = {
  auto_dispatch: '自动派单',
  force_dispatch: '强制指派',
  freeze_ticket: '工单冻结',
  update_config: '配置修改',
  audit_settlement: '结算审核',
  update_worker: '人员编辑',
  login: '用户登录',
  logout: '用户退出',
}

const ACTION_CLASS = {
  auto_dispatch: 'action-auto',
  force_dispatch: 'action-force',
  freeze_ticket: 'action-danger',
  update_config: 'action-config',
  audit_settlement: 'action-settle',
  update_worker: 'action-worker',
  login: 'action-info',
  logout: 'action-info',
}

const actions = Object.entries(ACTION_MAP).map(([value, label]) => ({ label, value }))

function actionLabel(code) { return ACTION_MAP[code] || code || '—' }
function actionClass(code) { return ACTION_CLASS[code] || '' }

function roleLabel(role) {
  const map = { admin: '管理员', system: '系统', worker: '维修员', citizen: '市民' }
  return map[role] || role || '—'
}

function targetText(row) {
  const type = row.target?.type || row.target_type || ''
  const id = row.target?.id || row.target_id || ''
  const typeMap = { ticket: '工单', settlement: '结算单', worker: '维修员', config: '系统配置' }
  const typeName = typeMap[type] || type || ''
  if (!typeName && !id) return '—'
  return `${typeName} ${id}`
}

// ── 变更摘要：统一处理三种不一致的 MongoDB 文档结构 ──
const FIELD_NAMES = {
  assigned_worker_id: '维修员',
  max_daily_orders: '每日上限',
  night_duty: '夜班值守',
  audit_status: '审核结果',
  status: '工单状态',
  key: '配置项',
  value: '配置值',
}

function changeSummary(row) {
  const oldVal = row.old_value || {}
  const newVal = row.new_value || {}
  const detail = row.detail || {}

  // 结构 A：old_value / new_value（来自 admin tickets.py）
  const keys = [...new Set([...Object.keys(oldVal), ...Object.keys(newVal)])]
  if (keys.length) {
    const parts = keys.map(k => {
      const label = FIELD_NAMES[k] || k
      const o = oldVal[k] !== undefined ? String(oldVal[k]) : '—'
      const n = newVal[k] !== undefined ? String(newVal[k]) : '—'
      return `${label} ${o} → ${n}`
    })
    return parts.join('；')
  }

  // 结构 B：detail.assigned_worker_id（来自 dispatch_service auto_dispatch）
  if (detail.assigned_worker_id) {
    return `系统自动分配维修员「${detail.assigned_worker_id}」`
  }

  // 结构 C：detail.result（来自 dispatch_service force_dispatch）
  if (detail.result) {
    const r = detail.result
    if (r.worker_id) return `强制指派维修员「${r.worker_id}」`
    if (r.reason) return r.reason
    return '强制指派操作'
  }

  // 结构 D：detail 中有 scores（带评分的自动派单）
  if (detail.scores) {
    return `系统综合评分派单`
  }

  // 兜底
  return actionLabel(row.action)
}

// ── 列表 ──
const logs = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(false)

async function fetch() {
  loading.value = true
  try {
    const res = await getAuditLogs({
      operator_id: operatorId.value,
      action: action.value,
      date_from: dateRange.value?.[0] || '',
      date_to: dateRange.value?.[1] || '',
      page: page.value,
      page_size: pageSize,
    })
    logs.value = res.data.items || []
    total.value = res.data.total || 0
  } catch (e) {
    console.error('审计日志加载失败:', e)
  } finally { loading.value = false }
}

function onPageChange(p) { page.value = p; fetch() }

onMounted(() => fetch())
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 16px; }
.search-bar { display: flex; gap: 10px; }
.table-wrap {
  background: var(--bg-elevated);
  border: 1px solid var(--border-dim);
  border-radius: var(--radius-lg);
  padding: 20px;
}

/* ── 表格行高统一 ── */
.audit-table :deep(.el-table__body td) { vertical-align: middle; }

/* ── 时间 ── */
.time-text { font-family: var(--font-mono); font-size: 12px; color: var(--text-secondary); }

/* ── 操作人（双行紧凑） ── */
.op-row { display: flex; flex-direction: column; gap: 2px; }
.op-name { font-size: 13px; color: var(--text-primary); line-height: 1.3; }
.op-role { font-size: 11px; color: var(--text-muted); line-height: 1.3; }

/* ── 操作徽章 ── */
.action-badge {
  font-size: 12px; font-weight: 600; padding: 3px 10px; border-radius: 3px;
  white-space: nowrap; letter-spacing: 0.3px;
}
.action-auto    { background: rgba(51,153,255,.12);  color: var(--signal-blue); }
.action-force   { background: rgba(255,106,0,.12);   color: var(--signal-amber); }
.action-danger  { background: rgba(255,59,59,.12);   color: var(--signal-red); }
.action-config  { background: rgba(255,184,0,.12);   color: var(--signal-yellow); }
.action-settle  { background: rgba(0,196,140,.12);   color: var(--signal-green); }
.action-worker  { background: rgba(255,145,77,.12);  color: var(--text-accent); }
.action-info    { background: rgba(154,157,168,.1);   color: var(--text-secondary); }

/* ── 操作对象 ── */
.target-text { font-family: var(--font-mono); font-size: 12px; color: var(--text-secondary); }

/* ── 变更摘要 ── */
.change-summary { font-size: 13px; color: var(--text-primary); line-height: 1.5; }

@media (max-width: 767px) {
  .search-bar { flex-direction: column; }
}
</style>
