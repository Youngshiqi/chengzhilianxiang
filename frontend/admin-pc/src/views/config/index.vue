<!--
  城市设施运维指挥中心 — 系统结算配置
  单表直管 + 添加品类，即时生效
-->
<template>
  <div class="page" v-loading="loading">
    <!-- 顶部操作栏 -->
    <div class="toolbar">
      <span class="toolbar-title">结算规则配置</span>
      <el-button type="primary" @click="openAdd">+ 添加品类</el-button>
    </div>

    <!-- 搜索栏 -->
    <div class="search-bar">
      <el-input v-model="keyword" placeholder="搜索品类名称..." size="large" style="width:240px" clearable />
      <el-button type="primary" size="large" @click="search">查询</el-button>
    </div>

    <div class="config-table-wrap">
      <el-table :data="configItems" row-key="rule_id" class="config-table" empty-text="暂无结算规则，请添加品类">
        <el-table-column label="设施品类" width="130">
          <template #default="{row}">
            <span class="facility-name">{{ row.facility_type === 'other' ? '默认规则' : row.facility_type }}</span>
          </template>
        </el-table-column>
        <el-table-column label="基础单价（元）" min-width="150">
          <template #default="{row}">
            <el-input-number v-model="row.base_price" :min="5" :max="500" size="small" controls-position="right" />
          </template>
        </el-table-column>
        <el-table-column label="加班费率" min-width="140">
          <template #default="{row}">
            <el-input-number v-model="row.overtime_rate" :min="1" :max="5" :step="0.1" :precision="1" size="small" controls-position="right" />
          </template>
        </el-table-column>
        <el-table-column label="紧急倍率" min-width="140">
          <template #default="{row}">
            <el-input-number v-model="row.emergency_multiplier" :min="1" :max="5" :step="0.1" :precision="1" size="small" controls-position="right" />
          </template>
        </el-table-column>
        <el-table-column label="夜班补贴（元）" min-width="150">
          <template #default="{row}">
            <el-input-number v-model="row.night_subsidy" :min="0" :max="200" size="small" controls-position="right" />
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-if="total > pageSize"
        :total="total" :page-size="pageSize" :current-page="page"
        layout="prev, pager, next" @current-change="onPageChange"
        style="margin-top:16px;justify-content:flex-end"
      />
    </div>

    <div class="save-bar">
      <span class="hint">修改后点击保存，即时生效，无需重启服务</span>
      <el-button type="primary" size="large" :loading="saving" @click="save">保存配置</el-button>
    </div>

    <!-- 添加品类弹窗 -->
    <el-dialog v-model="addVisible" title="添加设施品类" width="420px" class="add-dialog">
      <el-form :model="addForm" label-width="100px" label-position="left">
        <el-form-item label="设施品类" required>
          <el-input v-model="addForm.facility_type" placeholder="如：路灯、井盖、信号灯…" maxlength="32" />
        </el-form-item>
        <el-form-item label="基础单价（元）">
          <el-input-number v-model="addForm.base_price" :min="5" :max="500" size="small" />
        </el-form-item>
        <el-form-item label="加班费率">
          <el-input-number v-model="addForm.overtime_rate" :min="1" :max="5" :step="0.1" :precision="1" size="small" />
        </el-form-item>
        <el-form-item label="紧急倍率">
          <el-input-number v-model="addForm.emergency_multiplier" :min="1" :max="5" :step="0.1" :precision="1" size="small" />
        </el-form-item>
        <el-form-item label="夜班补贴（元）">
          <el-input-number v-model="addForm.night_subsidy" :min="0" :max="200" size="small" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addVisible = false">取消</el-button>
        <el-button type="primary" :loading="adding" @click="doAdd">确认添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getConfig, updateConfig, createConfig } from '@/api/index'

const keyword = ref('')
const configItems = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(false)
const saving = ref(false)

// ── 添加品类 ──
const addVisible = ref(false)
const adding = ref(false)
const addForm = reactive({
  facility_type: '',
  base_price: 50,
  overtime_rate: 1.5,
  emergency_multiplier: 2.0,
  night_subsidy: 30,
})

function openAdd() {
  Object.assign(addForm, {
    facility_type: '',
    base_price: 50,
    overtime_rate: 1.5,
    emergency_multiplier: 2.0,
    night_subsidy: 30,
  })
  addVisible.value = true
}

async function doAdd() {
  if (!addForm.facility_type.trim()) {
    ElMessage.warning('请输入设施品类名称')
    return
  }
  adding.value = true
  try {
    await createConfig({ ...addForm })
    ElMessage.success(`已添加「${addForm.facility_type}」结算规则`)
    addVisible.value = false
    load()
  } catch (e) {
    console.error('添加品类失败:', e)
  } finally { adding.value = false }
}

// ── 加载 / 保存 ──
async function load() {
  loading.value = true
  try {
    const res = await getConfig({
      keyword: keyword.value,
      page: page.value,
      page_size: pageSize,
    })
    configItems.value = res.data.items || []
    total.value = res.data.total || 0
  } catch (e) {
    console.error('配置加载失败:', e)
  } finally { loading.value = false }
}

function search() { page.value = 1; load() }
function onPageChange(p) { page.value = p; load() }

async function save() {
  saving.value = true
  try {
    await updateConfig(configItems.value)
    ElMessage.success('配置已保存，即时生效')
  } catch (e) {
    console.error('配置保存失败:', e)
  } finally { saving.value = false }
}

onMounted(() => load())
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 16px; }

/* ── 搜索栏 ── */
.search-bar { display: flex; gap: 10px; }

/* ── 顶部工具栏 ── */
.toolbar {
  display: flex; justify-content: space-between; align-items: center;
}
.toolbar-title {
  font-family: var(--font-mono); font-size: 13px; font-weight: 500;
  letter-spacing: 1px; text-transform: uppercase; color: var(--text-secondary);
}

.config-table-wrap {
  background: var(--bg-elevated);
  border: 1px solid var(--border-dim);
  border-radius: var(--radius-lg);
  padding: 20px;
}
.config-table :deep(.el-table__body td) { vertical-align: middle; }
.facility-name {
  font-size: 14px; font-weight: 500; color: var(--text-primary);
}

.save-bar {
  display: flex; justify-content: flex-end; align-items: center; gap: 16px;
}
.hint { font-size: 12px; color: var(--text-muted); }

@media (max-width: 767px) {
  .toolbar { flex-direction: column; gap: 10px; align-items: flex-start; }
  .search-bar { flex-direction: column; }
  .save-bar { flex-direction: column; align-items: stretch; }
  .hint { text-align: center; }
}
</style>
