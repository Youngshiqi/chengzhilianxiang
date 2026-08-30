<!--
  城市设施运维指挥中心 — 结算审计
  按维修员聚合，点击展开明细，支持多选批量审核
-->
<template>
  <div class="page">
    <!-- 搜索栏 -->
    <div class="search-bar">
      <el-input v-model="ticketId" placeholder="工单号" size="large" style="width:180px" clearable />
      <el-input v-model="workerId" placeholder="维修员ID" size="large" style="width:180px" clearable />
      <el-select v-model="auditStatus" placeholder="审核状态" clearable size="large" style="width:160px">
        <el-option label="待审核" value="pending" />
        <el-option label="已通过" value="approved" />
        <el-option label="已驳回" value="rejected" />
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
      <el-button type="primary" size="large" @click="search">查询</el-button>
      <el-button size="large" @click="exportExcel">导出 Excel</el-button>
    </div>

    <!-- 汇总栏 -->
    <div class="summary-bar" v-if="workerGroups.length">
      <span class="summary-item">维修员 <strong>{{ workerGroups.length }}</strong> 人</span>
      <span class="summary-item">结算单 <strong>{{ selectedRows.length || totalSettlements }}</strong> 条</span>
      <span class="summary-item">合计 <strong class="amount">¥{{ totalAmount.toFixed(2) }}</strong></span>
    </div>

    <!-- 批量操作 -->
    <div class="batch-bar" v-if="selectedRows.length">
      <span>已选 <strong>{{ selectedRows.length }}</strong> 条</span>
      <el-button type="success" size="small" @click="batchAudit('approved')">批量通过</el-button>
      <el-button type="danger" size="small" @click="batchAudit('rejected')">批量驳回</el-button>
    </div>

    <!-- 维修员聚合表 -->
    <div class="table-wrap" v-loading="loading">
      <el-table
        :data="workerGroups"
        row-key="worker_id"
        @expand-change="onExpandChange"
        ref="tableRef"
      >
        <el-table-column type="expand">
          <template #default="{row: group}">
            <el-table
              :data="group.settlements"
              row-key="settlement_id"
              size="small"
              @selection-change="(rows) => onChildSelect(group, rows)"
              :ref="(el) => setChildRef(group.worker_id, el)"
            >
              <el-table-column type="selection" width="40" />
              <el-table-column prop="settlement_id" label="结算单号" width="160" />
              <el-table-column prop="ticket_id" label="关联工单" width="160" />
              <el-table-column label="劳务费" width="90">
                <template #default="{row}">¥{{ Number(row.labor_cost || 0).toFixed(2) }}</template>
              </el-table-column>
              <el-table-column label="材料费" width="90">
                <template #default="{row}">¥{{ Number(row.material_cost || 0).toFixed(2) }}</template>
              </el-table-column>
              <el-table-column label="合计" width="100">
                <template #default="{row}"><strong style="color:var(--signal-amber)">¥{{ Number(row.total || 0).toFixed(2) }}</strong></template>
              </el-table-column>
              <el-table-column label="审核状态" width="90">
                <template #default="{row}">
                  <span class="audit-tag" :class="row.audit_status">{{ auditLabels[row.audit_status] }}</span>
                </template>
              </el-table-column>
              <el-table-column label="生成时间" width="170">
                <template #default="{row}">{{ row.created_at }}</template>
              </el-table-column>
              <el-table-column label="操作" width="160">
                <template #default="{row}">
                  <el-button v-if="row.audit_status === 'pending'" link type="success" size="small" @click.stop="auditOne(row.settlement_id, 'approved')">通过</el-button>
                  <el-button v-if="row.audit_status === 'pending'" link type="danger" size="small" @click.stop="auditOne(row.settlement_id, 'rejected')">驳回</el-button>
                </template>
              </el-table-column>
            </el-table>
          </template>
        </el-table-column>

        <el-table-column prop="worker_name" label="维修员" width="120">
          <template #default="{row}">
            <span class="worker-name">{{ row.worker_name || row.worker_id }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="worker_id" label="工号" width="90" />
        <el-table-column label="结算单数" width="90">
          <template #default="{row}">{{ row.settlements.length }}</template>
        </el-table-column>
        <el-table-column label="劳务费小计" width="110">
          <template #default="{row}">¥{{ row.laborSubtotal.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="材料费小计" width="110">
          <template #default="{row}">¥{{ row.materialSubtotal.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column label="合计">
          <template #default="{row}"><strong style="color:var(--signal-amber);font-size:15px">¥{{ row.totalSubtotal.toFixed(2) }}</strong></template>
        </el-table-column>
      </el-table>
      <el-pagination v-if="total > pageSize" :total="total" :page-size="pageSize" :current-page="page" layout="prev, pager, next" @current-change="onPageChange" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getSettlements, auditSettlement } from '@/api/index'

const ticketId = ref('')
const workerId = ref('')
const auditStatus = ref('')
const dateRange = ref(null)
const auditLabels = { pending: '待审核', approved: '已通过', rejected: '已驳回' }
const loading = ref(false)
const page = ref(1)
const pageSize = 100
const total = ref(0)
const rawItems = ref([])
const tableRef = ref(null)
const childRefs = {}
const selectedRows = ref([])
const expandedWorkers = ref(new Set())

function setChildRef(workerId, el) {
  if (el) childRefs[workerId] = el
}

// 按维修员聚合
const workerGroups = computed(() => {
  const map = {}
  for (const it of rawItems.value) {
    const wid = it.worker_id
    if (!map[wid]) {
      map[wid] = {
        worker_id: wid,
        worker_name: it.worker_name || '',
        settlements: [],
        laborSubtotal: 0,
        materialSubtotal: 0,
        totalSubtotal: 0,
      }
    }
    map[wid].settlements.push(it)
    map[wid].laborSubtotal += Number(it.labor_cost || 0)
    map[wid].materialSubtotal += Number(it.material_cost || 0)
    map[wid].totalSubtotal += Number(it.total || 0)
  }
  return Object.values(map)
})

const totalSettlements = computed(() => rawItems.value.length)
const totalAmount = computed(() => rawItems.value.reduce((s, it) => s + Number(it.total || 0), 0))

async function fetch() {
  loading.value = true
  try {
    const res = await getSettlements({
      audit_status: auditStatus.value,
      ticket_id: ticketId.value,
      worker_id: workerId.value,
      date_from: dateRange.value?.[0] || '',
      date_to: dateRange.value?.[1] || '',
      page: page.value,
      page_size: pageSize,
    })
    rawItems.value = res.data.items || []
    total.value = res.data.total || 0
    selectedRows.value = []
  } catch (e) {
    console.error('结算列表加载失败:', e)
  } finally {
    loading.value = false
  }
}

function search() { page.value = 1; fetch() }
function onPageChange(p) { page.value = p; fetch() }

function onExpandChange(row, expandedRows) {
  if (expandedRows.some(r => r.worker_id === row.worker_id)) {
    expandedWorkers.value.add(row.worker_id)
  } else {
    expandedWorkers.value.delete(row.worker_id)
  }
}

function onChildSelect(group, rows) {
  // 移除该 group 之前的选中
  selectedRows.value = selectedRows.value.filter(r => r.worker_id !== group.worker_id)
  // 加入新的
  for (const row of rows) {
    selectedRows.value.push({ ...row, worker_id: group.worker_id })
  }
}

async function auditOne(id, action) {
  try {
    await auditSettlement(id, action)
    ElMessage.success(action === 'approved' ? '已通过' : '已驳回')
    fetch()
  } catch (e) {
    console.error('审核失败:', e)
  }
}

async function batchAudit(action) {
  const pending = selectedRows.value.filter(r => r.audit_status === 'pending')
  if (!pending.length) {
    ElMessage.warning('没有待审核的结算单')
    return
  }
  try {
    for (const row of pending) {
      await auditSettlement(row.settlement_id, action)
    }
    ElMessage.success(`已批量${action === 'approved' ? '通过' : '驳回'} ${pending.length} 条`)
    selectedRows.value = []
    fetch()
  } catch (e) {
    console.error('批量审核失败:', e)
  }
}

function exportExcel() {
  ElMessage.info('导出功能开发中')
}

onMounted(() => fetch())
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 16px; }
.search-bar { display: flex; gap: 10px; flex-wrap: wrap; }

.summary-bar {
  display: flex; gap: 24px;
  background: var(--bg-elevated); border: 1px solid var(--border-dim);
  border-radius: var(--radius-lg); padding: 14px 20px;
}
.summary-item { font-size: 13px; color: var(--text-secondary); }
.summary-item strong { font-family: var(--font-mono); color: var(--text-primary); }
.amount { color: var(--signal-amber) !important; font-size: 16px; }

.batch-bar {
  display: flex; align-items: center; gap: 12px;
  background: rgba(255,184,0,.08); border: 1px solid rgba(255,184,0,.25);
  border-radius: var(--radius-md); padding: 10px 16px;
  font-size: 13px; color: var(--text-secondary);
}

.table-wrap {
  background: var(--bg-elevated); border: 1px solid var(--border-dim);
  border-radius: var(--radius-lg); padding: 20px;
}

.worker-name {
  font-weight: 600; color: var(--text-primary);
}

.audit-tag {
  font-family: var(--font-mono); font-size: 11px; font-weight: 600;
  padding: 2px 8px; border-radius: 2px;
}
.audit-tag.pending  { background: rgba(255,184,0,.12); color: var(--signal-yellow); }
.audit-tag.approved { background: rgba(0,196,140,.1);  color: var(--signal-green); }
.audit-tag.rejected { background: rgba(255,59,59,.1);  color: var(--signal-red); }

@media (max-width: 767px) { .search-bar { flex-direction: column; } .summary-bar { flex-wrap: wrap; gap: 12px; } }
</style>
