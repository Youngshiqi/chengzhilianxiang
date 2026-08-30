<!--
  城市设施运维指挥中心 — 人员管理
  维修员列表 + 在线状态 + 编辑功能
-->
<template>
  <div class="page">
    <div class="search-bar">
      <el-input v-model="nameFilter" placeholder="姓名搜索" size="large" style="width:180px" clearable />
      <el-select v-model="skillsFilter" placeholder="技能标签" clearable size="large" style="width:160px">
        <el-option v-for="s in skillOptions" :key="s" :label="s" :value="s" />
      </el-select>
      <el-select v-model="districtFilter" placeholder="片区" clearable size="large" style="width:160px">
        <el-option v-for="d in districts" :key="d" :label="d" :value="d" />
      </el-select>
      <el-button type="primary" size="large" @click="search">查询</el-button>
      <el-button type="success" size="large" @click="openCreate">＋ 新增维修员</el-button>
    </div>
    <div class="table-wrap">
      <div class="table-header">
        <span class="table-title">维修员档案</span>
        <span class="mono muted">共 {{ total }} 人</span>
      </div>
      <el-table :data="workers" v-loading="loading">
        <el-table-column prop="worker_id" label="工号" width="90" />
        <el-table-column prop="name" label="姓名" width="90" />
        <el-table-column label="技能标签" width="220">
          <template #default="{row}">
            <el-tag v-for="sk in parseJsonArray(row.skills)" :key="sk" size="small" class="skill-tag">{{ sk }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="district" label="片区" width="90" />
        <el-table-column label="星级" width="100">
          <template #default="{row}">{{ '★'.repeat(Math.floor(row.star_rating)) }}{{ row.star_rating % 1 >= 0.5 ? '☆' : '' }} {{ row.star_rating }}</template>
        </el-table-column>
        <el-table-column label="今日/上限" width="100">
          <template #default="{row}">
            <span :class="{ overload: row.today_orders >= row.max_daily_orders }">{{ row.today_orders }} / {{ row.max_daily_orders }}</span>
          </template>
        </el-table-column>
        <el-table-column label="夜班" width="60">
          <template #default="{row}">
            <span class="mono" :style="{color: row.night_duty ? 'var(--signal-blue)' : 'var(--text-muted)'}">{{ row.night_duty ? 'ON' : 'OFF' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{row}">
            <span class="status-indicator" :class="{ online: row.is_active !== false }">{{ row.is_active !== false ? '在岗' : '离线' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="{row}">
            <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-if="total > pageSize"
        :total="total" :page-size="pageSize" :current-page="page"
        layout="prev, pager, next" @current-change="onPageChange"
      />
    </div>

    <!-- 编辑弹窗 -->
    <el-dialog v-model="editVisible" title="编辑维修员" width="420px">
      <el-form :model="editForm" label-width="110px" v-if="editForm.worker_id">
        <el-form-item label="工号"><span class="mono">{{ editForm.worker_id }}</span></el-form-item>
        <el-form-item label="姓名"><span>{{ editForm.name }}</span></el-form-item>
        <el-form-item label="每日上限">
          <el-input-number v-model="editForm.max_daily_orders" :min="1" :max="50" />
        </el-form-item>
        <el-form-item label="夜班">
          <el-switch v-model="editForm.night_duty" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" @click="saveEdit" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 创建弹窗 -->
    <el-dialog v-model="createVisible" title="新增维修员" width="480px">
      <el-form :model="createForm" label-width="110px" :rules="createRules" ref="createFormRef">
        <el-form-item label="登录用户名" prop="username">
          <el-input v-model="createForm.username" placeholder="用于登录，例如：zhangxiaoming" />
        </el-form-item>
        <el-form-item label="姓名" prop="name">
          <el-input v-model="createForm.name" placeholder="真实姓名" />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="createForm.phone" placeholder="联系电话" />
        </el-form-item>
        <el-form-item label="所属片区" prop="district">
          <el-select v-model="createForm.district" placeholder="请选择片区" style="width:100%">
            <el-option v-for="d in districts" :key="d" :label="d" :value="d" />
          </el-select>
        </el-form-item>
        <el-form-item label="技能标签" prop="skills">
          <el-select v-model="createForm.skills" multiple placeholder="请选择技能" style="width:100%">
            <el-option v-for="s in skillOptions" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="每日上限">
          <el-input-number v-model="createForm.max_daily_orders" :min="1" :max="50" />
        </el-form-item>
        <el-form-item label="夜班">
          <el-switch v-model="createForm.night_duty" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" @click="saveCreate" :loading="creating">创建</el-button>
      </template>
    </el-dialog>

    <!-- 创建成功提示弹窗 -->
    <el-dialog v-model="successVisible" title="🎉 创建成功" width="460px">
      <div class="success-info">
        <p class="success-desc">请将以下账号信息告知维修员：</p>
        <div class="info-card">
          <div class="info-row">
            <span class="info-label">工号</span>
            <span class="info-value mono">{{ createdInfo.worker_id }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">登录用户名</span>
            <span class="info-value mono">{{ createdInfo.username }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">初始密码</span>
            <span class="info-value mono password">{{ createdInfo.password }}</span>
            <el-button size="small" @click="copyPassword">复制</el-button>
          </div>
        </div>
        <p class="warning-text">⚠️ 此密码仅显示一次，请妥善保管！</p>
      </div>
      <template #footer>
        <el-button type="primary" @click="successVisible = false">我知道了</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getWorkers, getWorkerSkills, updateWorker, createWorker } from '@/api/index'
import { parseJsonArray } from '@/utils'

const nameFilter = ref('')
const skillsFilter = ref('')
const districtFilter = ref('')
const skillOptions = ref([])
const districts = ['芙蓉区','天心区','岳麓区','开福区','雨花区','望城区','长沙县','浏阳市','宁乡市']

const workers = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(false)

const editVisible = ref(false)
const saving = ref(false)
const editForm = reactive({ worker_id: '', name: '', max_daily_orders: 20, night_duty: false })

const createVisible = ref(false)
const creating = ref(false)
const createFormRef = ref(null)
const createForm = reactive({
  username: '',
  name: '',
  phone: '',
  district: '',
  skills: [],
  max_daily_orders: 20,
  night_duty: false,
})
const createRules = {
  username: [{ required: true, message: '请输入登录用户名', trigger: 'blur' }],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  phone: [{ required: true, message: '请输入手机号', trigger: 'blur' }],
  district: [{ required: true, message: '请选择片区', trigger: 'change' }],
}

const successVisible = ref(false)
const createdInfo = reactive({ worker_id: '', username: '', password: '' })

async function fetch() {
  loading.value = true
  try {
    const res = await getWorkers({
      page: page.value,
      page_size: pageSize,
      district: districtFilter.value,
      name: nameFilter.value,
      skills: skillsFilter.value,
    })
    workers.value = res.data.items || []
    total.value = res.data.total || 0
  } catch (e) {
    console.error('人员列表加载失败:', e)
  } finally { loading.value = false }
}

function search() { page.value = 1; fetch() }
function onPageChange(p) { page.value = p; fetch() }

function openEdit(row) {
  editForm.worker_id = row.worker_id
  editForm.name = row.name
  editForm.max_daily_orders = row.max_daily_orders
  editForm.night_duty = row.night_duty
  editVisible.value = true
}

async function saveEdit() {
  saving.value = true
  try {
    await updateWorker(editForm.worker_id, {
      max_daily_orders: editForm.max_daily_orders,
      night_duty: editForm.night_duty,
    })
    ElMessage.success('更新成功')
    editVisible.value = false
    fetch()
  } catch (e) {
    console.error('保存维修员失败:', e)
  } finally { saving.value = false }
}

function openCreate() {
  createForm.username = ''
  createForm.name = ''
  createForm.phone = ''
  createForm.district = ''
  createForm.skills = []
  createForm.max_daily_orders = 20
  createForm.night_duty = false
  createVisible.value = true
}

async function saveCreate() {
  if (!createFormRef.value) return
  try {
    await createFormRef.value.validate()
  } catch {
    return
  }

  creating.value = true
  try {
    const res = await createWorker({
      username: createForm.username,
      name: createForm.name,
      phone: createForm.phone,
      district: createForm.district,
      skills: createForm.skills,
      max_daily_orders: createForm.max_daily_orders,
      night_duty: createForm.night_duty,
    })
    createVisible.value = false

    // 显示成功信息
    createdInfo.worker_id = res.data.worker_id
    createdInfo.username = res.data.username
    createdInfo.password = res.data.password
    successVisible.value = true

    fetch()
  } catch (e) {
    console.error('创建维修员失败:', e)
    ElMessage.error(e.msg || '创建失败')
  } finally { creating.value = false }
}

function copyPassword() {
  navigator.clipboard?.writeText(createdInfo.password)
    .then(() => ElMessage.success('密码已复制'))
    .catch(() => ElMessage.info('复制失败，请手动复制'))
}

async function fetchSkills() {
  try {
    const res = await getWorkerSkills()
    skillOptions.value = res.data.skills || []
  } catch (e) {
    console.error('获取技能标签失败:', e)
  }
}

onMounted(() => { fetchSkills(); fetch() })
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 16px; }
.search-bar { display: flex; gap: 10px; }
.table-wrap { background: var(--bg-elevated); border: 1px solid var(--border-dim); border-radius: var(--radius-lg); padding: 20px; }
.table-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.table-title { font-family: var(--font-mono); font-size: 13px; letter-spacing: 1px; text-transform: uppercase; color: var(--text-secondary); }
.skill-tag { margin-right: 4px; background: rgba(255,106,0,.1) !important; border-color: rgba(255,106,0,.2) !important; color: var(--signal-amber) !important; }
.overload { color: var(--signal-red); font-weight: 700; }
.status-indicator { font-family: var(--font-mono); font-size: 11px; font-weight: 600; color: var(--text-muted); }
.status-indicator.online { color: var(--signal-green); }

/* 创建成功提示样式 */
.success-info { text-align: center; padding: 10px 0; }
.success-desc { color: var(--text-secondary); margin-bottom: 20px; }
.info-card {
  background: linear-gradient(135deg, rgba(0,230,118,.08), rgba(0,196,140,.04));
  border: 1px solid rgba(0,230,118,.25);
  border-radius: var(--radius-md);
  padding: 20px;
  margin: 0 20px;
}
.info-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid rgba(0,230,118,.15);
}
.info-row:last-child { border-bottom: none; }
.info-label { color: var(--text-muted); font-size: 13px; }
.info-value { font-size: 15px; font-weight: 600; color: var(--text-primary); }
.info-value.password { color: var(--signal-amber); letter-spacing: 2px; }
.warning-text {
  margin-top: 16px;
  color: var(--signal-red);
  font-size: 12px;
}

@media (max-width: 767px) { .search-bar { flex-direction: column; } .table-header { flex-direction: column; gap: 10px; align-items: flex-start; } }
</style>
