<!--
  城市设施运维指挥中心 — 设施档案
  1000条点位列表 + 筛选 + 分页
-->
<template>
  <div class="page">
    <div class="search-bar">
      <el-select v-model="district" placeholder="行政区" clearable size="large">
        <el-option v-for="d in districts" :key="d" :label="d" :value="d" />
      </el-select>
      <el-select v-model="fType" placeholder="设施类型" clearable size="large">
        <el-option v-for="t in types" :key="t" :label="t" :value="t" />
      </el-select>
      <el-button type="primary" size="large" @click="search">查询</el-button>
    </div>
    <div class="table-wrap">
      <el-table :data="facilities" v-loading="loading">
        <el-table-column prop="facility_code" label="设施编码" width="130" />
        <el-table-column prop="type" label="类型" width="100" />
        <el-table-column prop="address" label="地址" show-overflow-tooltip />
        <el-table-column prop="district" label="行政区" width="90" />
        <el-table-column label="状态" width="80">
          <template #default="{row}">
            <span class="fac-status" :class="row.status">{{ statusMap[row.status] || row.status }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="total_faults" label="累计故障" width="80" />
        <el-table-column label="位置" width="100">
          <template #default="{row}">{{ row.location?.lat?.toFixed(4) }}, {{ row.location?.lng?.toFixed(4) }}</template>
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
import { getFacilities } from '@/api/index'

const district = ref(''), fType = ref('')
const districts = ['芙蓉区','天心区','岳麓区','开福区','雨花区','望城区','长沙县','浏阳市','宁乡市']
const types = ['路灯','井盖','护栏','信号灯','公交站牌','消防栓','公厕','指示牌','垃圾桶','健身器材']
const statusMap = { normal: '正常', repairing: '维修中', scrapped: '已报废' }

const facilities = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(false)

async function fetch() {
  loading.value = true
  try {
    const res = await getFacilities({
      district: district.value,
      facility_type: fType.value,
      page: page.value,
      page_size: pageSize,
    })
    facilities.value = res.data.items || []
    total.value = res.data.total || 0
  } catch (e) {
    console.error('设施列表加载失败:', e)
  } finally { loading.value = false }
}

function search() { page.value = 1; fetch() }
function onPageChange(p) { page.value = p; fetch() }

onMounted(() => fetch())
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 16px; }
.search-bar { display: flex; gap: 10px; }
.table-wrap { background: var(--bg-elevated); border: 1px solid var(--border-dim); border-radius: var(--radius-lg); padding: 20px; }
.fac-status { font-family: var(--font-mono); font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 2px; }
.fac-status.normal { background: rgba(0,196,140,.1); color: var(--signal-green); }
.fac-status.repairing { background: rgba(255,184,0,.1); color: var(--signal-yellow); }
.fac-status.scrapped { background: rgba(255,59,59,.1); color: var(--signal-red); }
@media (max-width: 767px) { .search-bar { flex-direction: column; } }
</style>
